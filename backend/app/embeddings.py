"""
Gemini text-embedding-004 wrapper (Phase 3.1).

Provides a tiny async surface that:
  * batches input strings into chunks of EMBED_BATCH_SIZE (Gemini accepts
    up to 100 inputs per `embed_content` call)
  * truncates each input to EMBED_MAX_CHARS so a single oversize chunk
    doesn't blow the model's 2048-token limit
  * returns vectors as plain `list[float]` so callers don't take a hard
    dependency on numpy

Free-tier budget (as of 2026-06):
  text-embedding-004 → 1500 RPM, 1M tokens/min, 1500 RPD — generous enough
  that we do not bother with per-tenant rate limiting at this layer.

Tests mock `app.embeddings.genai.Client` so they run offline.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

EMBED_MODEL_DEFAULT = "text-embedding-004"
EMBED_DIM = 768                  # text-embedding-004 native dim
EMBED_BATCH_SIZE = 100           # Gemini API hard cap
EMBED_MAX_CHARS = 8000           # ~2000 tokens — well under model limit


def _truncate(text: str) -> str:
    if len(text) <= EMBED_MAX_CHARS:
        return text
    return text[:EMBED_MAX_CHARS]


def _chunked(seq: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


async def embed_texts(
    texts: list[str],
    *,
    api_key: str,
    model: str = EMBED_MODEL_DEFAULT,
    task_type: str = "RETRIEVAL_DOCUMENT",
    timeout: float = 30.0,
) -> list[list[float]]:
    """
    Embed `texts` and return one 768-d vector per input, in the same order.

    `task_type` should be RETRIEVAL_DOCUMENT for chunks being indexed and
    RETRIEVAL_QUERY for the field-label queries at search time — Gemini
    asymmetric embeddings give a measurable quality bump when distinguished.

    Returns [[0.0] * EMBED_DIM] for every input if `api_key` is empty,
    so callers can degrade gracefully to no-retrieval without exceptions.
    """
    if not texts:
        return []
    if not api_key:
        logger.info("embed_texts skipped — no Gemini API key")
        return [[0.0] * EMBED_DIM for _ in texts]

    client = genai.Client(api_key=api_key)
    prepared = [_truncate(t) for t in texts]
    out: list[list[float]] = []

    for batch in _chunked(prepared, EMBED_BATCH_SIZE):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.embed_content,
                    model=model,
                    contents=batch,
                    config=genai_types.EmbedContentConfig(task_type=task_type),
                ),
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 — log and degrade
            logger.warning("Gemini embed_content failed for batch of %d: %s",
                           len(batch), exc)
            out.extend([[0.0] * EMBED_DIM for _ in batch])
            continue

        for emb in response.embeddings or []:
            # google-genai returns objects with .values; fall back to dict for
            # mock-friendly tests. (dicts also have a .values method, so check
            # dict membership first.)
            if isinstance(emb, dict):
                values = emb.get("values")
            else:
                values = getattr(emb, "values", None)
            if values is None:
                values = [0.0] * EMBED_DIM
            out.append(list(values))

    # Defensive: pad/trim so caller always gets len(texts) results back even
    # if the API returned a short response.
    while len(out) < len(texts):
        out.append([0.0] * EMBED_DIM)
    return out[: len(texts)]


async def embed_query(
    query: str,
    *,
    api_key: str,
    model: str = EMBED_MODEL_DEFAULT,
    timeout: float = 30.0,
) -> list[float]:
    """Convenience wrapper for single-query embedding at retrieval time."""
    vectors = await embed_texts(
        [query],
        api_key=api_key,
        model=model,
        task_type="RETRIEVAL_QUERY",
        timeout=timeout,
    )
    return vectors[0] if vectors else [0.0] * EMBED_DIM
