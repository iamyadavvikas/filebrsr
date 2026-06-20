"""
Per-datapoint retrieval-based extraction (Phase 3.2).

Replaces the giant 6-pass agent for the subset of BRSR datapoints whose
labels embed-search reliably (i.e. scalar fields with distinctive wording).
Workflow per filing:

  1. Caller provides a built `ChunkIndex` (in-memory or Supabase-backed).
  2. We pick a curated subset of BRSR datapoints — by default the
     mandatory-core scalar/narrative/numeric fields (skip data_type == 'table'
     because those need column-aware extraction we'll do separately).
  3. For each datapoint, retrieve top-k chunks by embedding similarity over
     the field's label.
  4. Batch ~5 fields per Gemini call, feeding only those chunks as context.
  5. Gemini returns one JSON object per batch with `{<datapoint_id>: value}`.
  6. Merge into the conventional {section_a, section_b, section_c} shape
     keyed by datapoint_id (e.g. "A.I.1"). Frontend renders via the
     BRSR_DATAPOINTS catalog.

Why datapoint_id keys instead of fuzzy snake-case names? Stability — IDs are
authoritative; they will not collide with the legacy keys (`cin`, `turnover`)
emitted by regex/enhanced/agent layers, so callers can merge both without
loss.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.brsr_datapoints import BRSR_DATAPOINTS
from app.retrieval import ChunkIndex, RetrievalHit

logger = logging.getLogger(__name__)


# ─── Datapoint selection ──────────────────────────────────────────────────


SCALAR_DATA_TYPES = {
    "narrative", "integer", "monetary", "percent", "decimal",
    "gyear", "date", "enumeration", "boolean", "string",
}


def select_retrievable_datapoints(
    datapoints: list[dict] | None = None,
    *,
    mandatory_only: bool = True,
    core_only: bool = False,
    max_count: int | None = 100,
) -> list[dict]:
    """
    Filter the BRSR catalog down to the subset worth running through
    retrieval. Defaults are conservative to stay inside the Gemini free
    tier — bump `max_count` once we're on a paid plan.
    """
    src = datapoints if datapoints is not None else BRSR_DATAPOINTS
    out: list[dict] = []
    for dp in src:
        if dp.get("data_type") not in SCALAR_DATA_TYPES:
            continue
        if mandatory_only and not dp.get("mandatory", False):
            continue
        if core_only and not dp.get("core", False):
            continue
        out.append(dp)
        if max_count is not None and len(out) >= max_count:
            break
    return out


# ─── Prompt building ──────────────────────────────────────────────────────


_PROMPT_HEADER = """You are extracting Indian BRSR (SEBI) disclosures from a company report.

For EACH field below, return the value EXACTLY as stated in the context.
Rules:
- If the context does not contain the value, return null for that field.
- Do not invent or paraphrase. Numeric values keep their original units
  (e.g. "INR 450 Cr", "12,34,567"). Yes/No questions return "Yes" or "No".
- Return only valid JSON matching the requested schema. No prose."""


def _format_context(hits_by_field: dict[str, list[RetrievalHit]]) -> str:
    """Union the unique chunks across all fields in the batch into one
    context block. Keeps the prompt small while letting the model see
    everything that *might* be relevant."""
    seen: set[str] = set()
    parts: list[str] = []
    for hits in hits_by_field.values():
        for hit in hits:
            cid = hit.chunk.chunk_id or f"p{hit.chunk.page_number}"
            if cid in seen:
                continue
            seen.add(cid)
            heading = f" — {hit.chunk.heading}" if hit.chunk.heading else ""
            parts.append(
                f"[{cid} p.{hit.chunk.page_number}{heading}]\n{hit.chunk.content}"
            )
    return "\n\n".join(parts)


def _build_prompt(
    batch: list[dict],
    hits_by_field: dict[str, list[RetrievalHit]],
) -> str:
    fields_block = "\n".join(
        f"- {dp['id']}: {dp['label']}"
        for dp in batch
    )
    context = _format_context(hits_by_field)
    return (
        f"{_PROMPT_HEADER}\n\n"
        f"FIELDS TO EXTRACT:\n{fields_block}\n\n"
        f"CONTEXT (relevant excerpts from the report):\n{context}"
    )


def _build_schema(batch: list[dict]) -> dict[str, Any]:
    """Return a JSON-schema describing one nullable string per datapoint id.
    We coerce everything to string to keep the model honest (numeric parsing
    happens later in normalise.py)."""
    return {
        "type": "object",
        "properties": {
            dp["id"]: {"type": ["string", "null"]}
            for dp in batch
        },
        "required": [dp["id"] for dp in batch],
    }


# ─── Gemini call (one batch) ──────────────────────────────────────────────


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _parse_json_lenient(text: str) -> dict[str, Any]:
    """Gemini structured output usually returns clean JSON, but fall back
    to fence-stripping in case the safety system wraps the response."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_FENCE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return {}


async def _extract_batch(
    batch: list[dict],
    *,
    index: ChunkIndex,
    client: Any,
    model: str,
    top_k: int,
    timeout: float,
) -> dict[str, Any]:
    """Retrieve + call Gemini for one ~5-field batch. Always returns a dict
    with one key per datapoint in `batch` (null if not found / on error)."""
    # Retrieval is cheap (vector ops). Do it in parallel.
    retrieve_tasks = [
        index.retrieve(dp["label"], top_k=top_k) for dp in batch
    ]
    hits_lists = await asyncio.gather(*retrieve_tasks, return_exceptions=True)

    hits_by_field: dict[str, list[RetrievalHit]] = {}
    for dp, hits in zip(batch, hits_lists):
        if isinstance(hits, Exception):
            logger.warning("retrieve failed for %s: %s", dp["id"], hits)
            hits_by_field[dp["id"]] = []
        else:
            hits_by_field[dp["id"]] = hits

    if not any(hits_by_field.values()):
        return {dp["id"]: None for dp in batch}

    prompt = _build_prompt(batch, hits_by_field)
    schema = _build_schema(batch)

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.0,
                ),
            ),
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini extraction call failed for batch %s: %s",
                       [dp["id"] for dp in batch], exc)
        return {dp["id"]: None for dp in batch}

    payload = _parse_json_lenient(getattr(response, "text", "") or "")
    out: dict[str, Any] = {}
    for dp in batch:
        v = payload.get(dp["id"])
        if isinstance(v, str) and v.strip().lower() in {"", "null", "none", "n/a"}:
            v = None
        out[dp["id"]] = v
    return out


# ─── Public entry point ───────────────────────────────────────────────────


async def extract_with_retrieval(
    *,
    index: ChunkIndex,
    datapoints: list[dict] | None = None,
    api_key: str,
    model: str = "gemini-2.0-flash",
    batch_size: int = 5,
    top_k: int = 3,
    concurrency: int = 3,
    timeout: float = 30.0,
) -> dict[str, dict[str, Any]]:
    """
    Run retrieval-based extraction over a ChunkIndex. Returns

      {"section_a": {"A.I.1": "L12345...", ...},
       "section_b": {...},
       "section_c": {...}}

    Only includes non-null values so the caller can `.update()` over an
    existing merged dict without overwriting earlier wins with null.

    Concurrency capped at `concurrency` to stay under Gemini Flash 15 RPM.
    """
    if not api_key:
        logger.info("extract_with_retrieval skipped — no Gemini API key")
        return {"section_a": {}, "section_b": {}, "section_c": {}}

    selected = (
        datapoints
        if datapoints is not None
        else select_retrievable_datapoints()
    )
    if not selected:
        return {"section_a": {}, "section_b": {}, "section_c": {}}

    client = genai.Client(api_key=api_key)
    sem = asyncio.Semaphore(concurrency)

    batches: list[list[dict]] = [
        selected[i : i + batch_size]
        for i in range(0, len(selected), batch_size)
    ]

    async def _bounded(batch: list[dict]) -> dict[str, Any]:
        async with sem:
            return await _extract_batch(
                batch, index=index, client=client, model=model,
                top_k=top_k, timeout=timeout,
            )

    batch_results = await asyncio.gather(*[_bounded(b) for b in batches])

    # Stitch back into section-keyed buckets, omitting nulls.
    out: dict[str, dict[str, Any]] = {
        "section_a": {}, "section_b": {}, "section_c": {},
    }
    id_to_section: dict[str, str] = {
        dp["id"]: dp.get("section", "section_a") for dp in selected
    }
    for batch_result in batch_results:
        for dp_id, value in batch_result.items():
            if value is None:
                continue
            section = id_to_section.get(dp_id, "section_a")
            out.setdefault(section, {})[dp_id] = value
    return out
