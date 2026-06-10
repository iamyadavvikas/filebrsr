"""
Chunk index + retrieval for per-datapoint extraction (Phase 3.1/3.2).

Two backends:

  * InMemoryChunkIndex
      - Built once per extraction request: embeds every chunk via Gemini,
        keeps vectors in a numpy array, scores with cosine similarity.
      - Lifetime = lifetime of the extraction request. Cheap, no DB.

  * SupabaseChunkIndex
      - Persists chunks + embeddings to public.extraction_chunks (v12 SQL)
        and queries them via the match_extraction_chunks RPC.
      - Lifetime = forever. Powers re-extraction (Phase 5.2) and the
        future "chat with your filing" experience.

Both expose the same async `retrieve(query, top_k)` contract so callers can
swap implementations transparently.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.embeddings import EMBED_DIM, embed_query, embed_texts
from app.pdf_parser import Chunk, Document

logger = logging.getLogger(__name__)


# ─── Result type ──────────────────────────────────────────────────────────


@dataclass
class RetrievalHit:
    chunk: Chunk
    similarity: float


# ─── Protocol ─────────────────────────────────────────────────────────────


class ChunkIndex(Protocol):
    async def retrieve(self, query: str, *, top_k: int = 3) -> list[RetrievalHit]:
        ...


# ─── Cosine helper (avoids numpy hard dep) ────────────────────────────────


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


# ─── In-memory backend ────────────────────────────────────────────────────


def _chunk_to_embed_text(c: Chunk) -> str:
    """
    What we actually feed to the embedding model. Prepending the heading
    gives the vector enough context to disambiguate tables that look alike
    in isolation (e.g. multiple 'Male / Female / Total' grids).
    """
    if c.heading:
        return f"{c.heading}\n{c.content}"
    return c.content


@dataclass
class InMemoryChunkIndex:
    chunks: list[Chunk]
    embeddings: list[list[float]] = field(default_factory=list)
    api_key: str = ""
    model: str = "text-embedding-004"

    async def retrieve(self, query: str, *, top_k: int = 3) -> list[RetrievalHit]:
        if not self.chunks or not self.embeddings:
            return []
        if not self.api_key:
            # No embeddings available — fall back to keyword scan so we still
            # return *something* useful. Score is a crude term-overlap ratio.
            return _keyword_fallback(self.chunks, query, top_k)

        qvec = await embed_query(query, api_key=self.api_key, model=self.model)
        if not qvec or all(v == 0.0 for v in qvec):
            return _keyword_fallback(self.chunks, query, top_k)

        scored: list[tuple[float, Chunk]] = []
        for chunk, vec in zip(self.chunks, self.embeddings):
            scored.append((_cosine(qvec, vec), chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [RetrievalHit(chunk=c, similarity=s) for s, c in scored[:top_k]]


async def build_in_memory_index(
    doc: Document,
    *,
    api_key: str,
    model: str = "text-embedding-004",
) -> InMemoryChunkIndex:
    """
    Embed every chunk in `doc` once and return a ready-to-query index.

    When `api_key` is missing, vectors come back as all-zero placeholders;
    retrieve() then falls back to keyword overlap so the pipeline still runs
    end-to-end (handy for local dev and CI).
    """
    chunks = list(doc.chunks)
    if not chunks:
        return InMemoryChunkIndex(chunks=[], embeddings=[], api_key=api_key, model=model)

    embed_inputs = [_chunk_to_embed_text(c) for c in chunks]
    vectors = await embed_texts(
        embed_inputs,
        api_key=api_key,
        model=model,
        task_type="RETRIEVAL_DOCUMENT",
    )
    if len(vectors) != len(chunks):
        # embed_texts already pads/trims but double-check so we never zip
        # mismatched lists.
        vectors = (vectors + [[0.0] * EMBED_DIM] * len(chunks))[: len(chunks)]
    return InMemoryChunkIndex(
        chunks=chunks, embeddings=vectors, api_key=api_key, model=model
    )


def _keyword_fallback(
    chunks: list[Chunk], query: str, top_k: int
) -> list[RetrievalHit]:
    """Last-resort lexical scoring when embeddings are unavailable."""
    q_tokens = {t.lower() for t in query.split() if len(t) >= 3}
    if not q_tokens:
        return []
    scored: list[tuple[float, Chunk]] = []
    for c in chunks:
        text_tokens = {t.lower() for t in c.content.split() if len(t) >= 3}
        if not text_tokens:
            continue
        overlap = len(q_tokens & text_tokens) / len(q_tokens)
        if overlap > 0:
            scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [RetrievalHit(chunk=c, similarity=s) for s, c in scored[:top_k]]


# ─── Supabase-backed backend ──────────────────────────────────────────────


@dataclass
class SupabaseChunkIndex:
    """
    Persists chunks + embeddings via supabase-py and queries them via the
    match_extraction_chunks RPC defined in migration_v12_chunks_pgvector.sql.

    Constructed with an *already-authenticated* supabase client (the same
    one the rest of main.py uses), the user_id of the caller, and the
    report_id this chunk set belongs to.
    """
    supabase: Any
    user_id: str
    report_id: str
    api_key: str
    model: str = "text-embedding-004"

    async def persist(self, doc: Document) -> int:
        """
        Embed every chunk in `doc` and insert rows into extraction_chunks.
        Returns the number of rows actually written.
        Idempotent via the (report_id, chunk_id) unique constraint:
        re-running will raise — callers should delete the report's rows
        first if they want to re-index.
        """
        if not doc.chunks:
            return 0

        embed_inputs = [_chunk_to_embed_text(c) for c in doc.chunks]
        vectors = await embed_texts(
            embed_inputs,
            api_key=self.api_key,
            model=self.model,
            task_type="RETRIEVAL_DOCUMENT",
        )
        return self._insert_rows(doc.chunks, vectors)

    async def persist_from_index(self, index: "InMemoryChunkIndex") -> int:
        """
        Cheaper sibling of persist(): reuses the embeddings already computed
        by build_in_memory_index() so we don't pay for Gemini embed twice
        in the same request. Returns the number of rows written.
        """
        if not index.chunks:
            return 0
        # Defensive: align lengths if the index was built incrementally.
        vectors = list(index.embeddings)
        while len(vectors) < len(index.chunks):
            vectors.append([0.0] * len(vectors[0]) if vectors else [])
        return self._insert_rows(index.chunks, vectors[: len(index.chunks)])

    def _insert_rows(
        self, chunks: list[Chunk], vectors: list[list[float]],
    ) -> int:
        rows = []
        for chunk, vec in zip(chunks, vectors):
            rows.append({
                "report_id": self.report_id,
                "user_id": self.user_id,
                "chunk_id": chunk.chunk_id,
                "page_number": chunk.page_number,
                "kind": chunk.kind,
                "heading": chunk.heading,
                "content": chunk.content,
                "total_chars": len(chunk.content),
                "embedding": vec if any(v != 0.0 for v in vec) else None,
                "embedding_model": self.model,
            })

        try:
            self.supabase.table("extraction_chunks").insert(rows).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SupabaseChunkIndex insert failed for report=%s: %s",
                self.report_id, exc,
            )
            return 0
        return len(rows)

    async def retrieve(self, query: str, *, top_k: int = 3) -> list[RetrievalHit]:
        qvec = await embed_query(query, api_key=self.api_key, model=self.model)
        if not qvec or all(v == 0.0 for v in qvec):
            return []
        try:
            resp = self.supabase.rpc(
                "match_extraction_chunks",
                {
                    "query_embedding": qvec,
                    "match_report_id": self.report_id,
                    "match_count": top_k,
                },
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "match_extraction_chunks RPC failed for report=%s: %s",
                self.report_id, exc,
            )
            return []

        rows = getattr(resp, "data", None) or []
        hits: list[RetrievalHit] = []
        for r in rows:
            hits.append(RetrievalHit(
                chunk=Chunk(
                    page_number=int(r.get("page_number", 0)),
                    kind=str(r.get("kind", "text")),
                    content=str(r.get("content", "")),
                    chunk_id=str(r.get("chunk_id", "")),
                    heading=r.get("heading"),
                ),
                similarity=float(r.get("similarity", 0.0)),
            ))
        return hits
