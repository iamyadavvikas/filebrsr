"""Unified extraction pipeline (Phase 5.1).

Three call sites previously had their own near-identical extraction logic:

  - main.py  /api/extract        (sync upload from authenticated frontend)
  - main.py  /api/extract-async  (fire-and-forget; downloads from storage)
  - worker.py:process_job        (polls extraction_jobs; was using the
                                 legacy text-only pipeline — drifted)

This module collapses all three onto one ``run_full_extraction()``
function. All call sites now share:

  - table-aware ``parse_pdf`` (preserves columns + table markdown)
  - OCR fallback (Gemini Vision) for blank pages
  - regex + enhanced + ai/agent triple extraction with deterministic merge
  - canonical-numeric normalisation (Cr/Lakh/Mn → INR)
  - source citations (page + chunk_id per field)
  - opt-in retrieval extraction (Phase 3) with chunk persistence

DB writes are kept *out* of this function — callers decide whether to
persist (e.g. guest extractions don't, sync uploads do). This keeps the
pipeline pure-ish and trivially testable.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent_extraction import extract_with_agent
from app.ai_extraction import extract_with_ai
from app.citations import attach_citations
from app.config import Settings
from app.extract_retrieval import (
    extract_with_retrieval,
    select_retrievable_datapoints,
)
from app.extraction import calculate_confidence, extract_with_regex
from app.extraction_enhanced import extract_enhanced
from app.normalise import normalise_extracted
from app.ocr import ocr_document
from app.pdf_parser import parse_pdf
from app.retrieval import SupabaseChunkIndex, build_in_memory_index

logger = logging.getLogger("app.extraction_pipeline")


EMPTY_SECTIONS: dict[str, dict[str, Any]] = {
    "section_a": {},
    "section_b": {},
    "section_c": {},
}


# ─── Retrieval sub-pipeline (was main._run_retrieval_extraction) ────────


async def run_retrieval_extraction(
    doc,
    *,
    settings: Settings,
    user_id: str | None = None,
    report_id: str | None = None,
    supabase_client=None,
) -> dict[str, dict[str, Any]]:
    """Build an in-memory chunk index and run per-datapoint extraction.

    Always returns the empty 3-section shape on any failure or when
    disabled so callers can blindly assign it under ``merged["retrieved"]``.

    If ``user_id`` + ``report_id`` (non-"guest") + ``supabase_client`` are
    all provided, the embedded chunks are also persisted to
    ``public.extraction_chunks`` (v12). Best-effort — persistence failures
    never fail the extraction.
    """
    if not settings.ENABLE_RETRIEVAL_EXTRACTION:
        return {k: {} for k in EMPTY_SECTIONS}
    if not settings.GEMINI_API_KEY:
        return {k: {} for k in EMPTY_SECTIONS}
    try:
        index = await build_in_memory_index(doc, api_key=settings.GEMINI_API_KEY)
        if (
            user_id
            and report_id
            and report_id != "guest"
            and supabase_client is not None
        ):
            try:
                store = SupabaseChunkIndex(
                    supabase=supabase_client,
                    user_id=user_id,
                    report_id=report_id,
                    api_key=settings.GEMINI_API_KEY,
                )
                n = await store.persist_from_index(index)
                logger.info(
                    "Persisted %d chunks to extraction_chunks (report=%s)",
                    n, report_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "chunk persist failed for report=%s: %s",
                    report_id, exc,
                )
        datapoints = select_retrievable_datapoints(
            max_count=settings.RETRIEVAL_MAX_DATAPOINTS,
        )
        return await extract_with_retrieval(
            index=index,
            datapoints=datapoints,
            api_key=settings.GEMINI_API_KEY,
            batch_size=settings.RETRIEVAL_BATCH_SIZE,
            top_k=settings.RETRIEVAL_TOP_K,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("retrieval extraction failed: %s", exc)
        return {k: {} for k in EMPTY_SECTIONS}


# ─── Triple-extractor stage ──────────────────────────────────────────────


async def _run_ai_with_fallback(
    text: str, *, settings: Settings,
) -> dict[str, Any]:
    """Run the multi-pass agent (Groq) with single-shot AI fallback.

    Mirrors the heuristic used in the three legacy call sites: if the
    agent emits fewer than 10 fields, supplement with a single-shot pass
    that fills in any keys the agent missed. AI takes precedence within
    its own dict but never overwrites itself.

    Returns the empty 3-section shape if every attempt fails.
    """
    try:
        ai_results = await extract_with_agent(text, settings.GROQ_API_KEY)
        agent_fields = sum(
            len(v) for v in ai_results.values() if isinstance(v, dict)
        )
        logger.info("Agent extraction: %d fields", agent_fields)
        if agent_fields < 10:
            logger.info(
                "Agent got few fields, supplementing with single-shot…",
            )
            single_shot = await extract_with_ai(
                text,
                settings.GEMINI_API_KEY,
                settings.GROQ_API_KEY,
                settings.ANTHROPIC_API_KEY,
            )
            for section in EMPTY_SECTIONS:
                for k, v in single_shot.get(section, {}).items():
                    if k not in ai_results.get(section, {}):
                        ai_results.setdefault(section, {})[k] = v
        return ai_results
    except Exception as agent_err:  # noqa: BLE001
        logger.warning(
            "Agent extraction failed, falling back to single-shot: %s",
            agent_err,
        )
        try:
            return await extract_with_ai(
                text,
                settings.GEMINI_API_KEY,
                settings.GROQ_API_KEY,
                settings.ANTHROPIC_API_KEY,
            )
        except Exception as ai_err:  # noqa: BLE001
            logger.error("All AI extraction failed: %s", ai_err)
            return {k: {} for k in EMPTY_SECTIONS}


def _merge_extractor_outputs(
    *,
    regex: dict[str, Any],
    enhanced: dict[str, Any],
    ai: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic precedence: enhanced base → regex fills → AI wins.

    AI taking precedence is intentional: the legacy extractors are
    high-precision/low-recall (regex) or section-split fuzzy (enhanced),
    while AI sees the whole document. When AI extracts a value, prefer
    it.
    """
    merged: dict[str, Any] = {k: {} for k in EMPTY_SECTIONS}
    for section in EMPTY_SECTIONS:
        merged[section] = {**enhanced.get(section, {})}
        merged[section].update(regex.get(section, {}))
        merged[section].update(ai.get(section, {}))
    return merged


# ─── Public driver ───────────────────────────────────────────────────────


async def run_full_extraction(
    *,
    file_bytes: bytes,
    settings: Settings,
    report_id: str = "guest",
    user_id: str | None = None,
    supabase_client=None,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """Run the full BRSR extraction pipeline on a PDF byte string.

    Returns a dict shaped::

        {
            "status": "completed" | "failed",
            "error": str | None,
            "extracted_data": {
                "section_a": {...},
                "section_b": {...},
                "section_c": {...},
                "normalised": {...},
                "citations": {...},
                "retrieved": {...},
            },
            "confidence_scores": {...},
            "company_name": str | None,
            "financial_year": str | None,
            # Sub-extractor outputs (for callers that compute their own
            # confidence, gap analysis, etc.):
            "_raw": {"regex": ..., "enhanced": ..., "ai": ...},
        }

    No DB writes happen here — callers persist the result as needed.

    Args:
        file_bytes: raw PDF bytes.
        settings: app settings (api keys + retrieval tunables).
        report_id: report row id; "guest" disables chunk persistence.
        user_id: profile id; required (with report_id) for chunk persistence.
        supabase_client: required for chunk persistence; passed through to
            the retrieval sub-pipeline.
        max_pages: when set, pdfplumber stops after N pages (used by the
            worker / async endpoint to cap LLM cost on huge filings).
    """
    # 1. Parse
    try:
        doc = parse_pdf(file_bytes, max_pages=max_pages) if max_pages \
            else parse_pdf(file_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.error("parse_pdf failed: %s", exc)
        return {
            "status": "failed",
            "error": f"PDF parse failed: {exc}",
            "extracted_data": None,
            "confidence_scores": {},
            "company_name": None,
            "financial_year": None,
            "_raw": {},
        }

    # 2. OCR fallback for blank pages (no-op if no key or no empty pages)
    if settings.GEMINI_API_KEY:
        try:
            await ocr_document(doc, file_bytes, api_key=settings.GEMINI_API_KEY)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OCR failed (continuing without it): %s", exc)

    text = doc.to_text()
    logger.info(
        "PDF parsed: pages=%d tables=%d chars=%d empty_pages=%d",
        doc.num_pages, doc.num_tables, doc.total_chars, len(doc.empty_pages),
    )
    if not text.strip():
        return {
            "status": "failed",
            "error": "No text could be extracted from PDF",
            "extracted_data": None,
            "confidence_scores": {},
            "company_name": None,
            "financial_year": None,
            "_raw": {},
        }

    # 3. Triple extraction
    regex_results = extract_with_regex(text)
    enhanced_results = extract_enhanced(text)
    ai_results = await _run_ai_with_fallback(text, settings=settings)

    # 4. Merge
    merged = _merge_extractor_outputs(
        regex=regex_results, enhanced=enhanced_results, ai=ai_results,
    )

    # 5. Normalise + citations + retrieval (sidecars; never raise)
    try:
        merged["normalised"] = normalise_extracted(merged)
    except Exception as exc:  # noqa: BLE001
        logger.warning("normalise_extracted failed: %s", exc)
        merged["normalised"] = {}

    try:
        merged["citations"] = attach_citations(merged, doc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("attach_citations failed: %s", exc)
        merged["citations"] = {}

    merged["retrieved"] = await run_retrieval_extraction(
        doc,
        settings=settings,
        user_id=user_id,
        report_id=report_id,
        supabase_client=supabase_client,
    )

    # 6. Confidence + headline fields
    confidence = calculate_confidence(regex_results, ai_results)
    company_name = merged.get("section_a", {}).get("company_name")
    financial_year = merged.get("section_a", {}).get("financial_year")

    return {
        "status": "completed",
        "error": None,
        "extracted_data": merged,
        "confidence_scores": confidence,
        "company_name": company_name,
        "financial_year": financial_year,
        "_raw": {
            "regex": regex_results,
            "enhanced": enhanced_results,
            "ai": ai_results,
        },
    }
