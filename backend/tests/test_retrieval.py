"""Tests for app/retrieval.py (Phase 3.1)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import retrieval as ret
from app.embeddings import EMBED_DIM
from app.pdf_parser import Chunk, Document

# ─── Helpers ──────────────────────────────────────────────────────────────


def _chunk(page: int, content: str, *, chunk_id: str = "", heading: str | None = None,
           kind: str = "text") -> Chunk:
    return Chunk(
        page_number=page,
        kind=kind,
        content=content,
        chunk_id=chunk_id or f"p{page}-c0",
        heading=heading,
    )


def _doc(*chunks: Chunk) -> Document:
    return Document(
        chunks=list(chunks),
        num_pages=max((c.page_number for c in chunks), default=0),
    )


def _unit_vec(dim: int, slot: int) -> list[float]:
    v = [0.0] * dim
    v[slot % dim] = 1.0
    return v


# ─── _cosine ──────────────────────────────────────────────────────────────


def test_cosine_identical_vectors_is_one():
    assert ret._cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero():
    assert ret._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_handles_zero_vector():
    assert ret._cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_handles_mismatched_length():
    assert ret._cosine([1.0], [1.0, 0.0]) == 0.0


# ─── _chunk_to_embed_text ─────────────────────────────────────────────────


def test_chunk_to_embed_text_prepends_heading():
    c = _chunk(1, "body", heading="SECTION A")
    assert ret._chunk_to_embed_text(c) == "SECTION A\nbody"


def test_chunk_to_embed_text_omits_missing_heading():
    c = _chunk(1, "body")
    assert ret._chunk_to_embed_text(c) == "body"


# ─── _keyword_fallback ────────────────────────────────────────────────────


def test_keyword_fallback_returns_best_overlap():
    chunks = [
        _chunk(1, "alpha beta gamma"),
        _chunk(2, "totally different text"),
        _chunk(3, "alpha delta epsilon"),
    ]
    hits = ret._keyword_fallback(chunks, "alpha beta", top_k=2)
    assert hits[0].chunk.page_number == 1
    assert hits[1].chunk.page_number == 3


def test_keyword_fallback_short_query_returns_empty():
    chunks = [_chunk(1, "alpha beta gamma")]
    assert ret._keyword_fallback(chunks, "a b c", top_k=3) == []


# ─── build_in_memory_index ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_in_memory_index_empty_doc():
    idx = await ret.build_in_memory_index(_doc(), api_key="k")
    assert idx.chunks == []
    assert idx.embeddings == []


@pytest.mark.asyncio
async def test_build_in_memory_index_embeds_every_chunk():
    doc = _doc(_chunk(1, "alpha"), _chunk(2, "beta"))
    vecs = [_unit_vec(EMBED_DIM, 0), _unit_vec(EMBED_DIM, 1)]
    with patch.object(ret, "embed_texts", new=AsyncMock(return_value=vecs)) as mock:
        idx = await ret.build_in_memory_index(doc, api_key="k")
    mock.assert_awaited_once()
    assert len(idx.embeddings) == 2
    assert idx.embeddings[0][0] == 1.0


@pytest.mark.asyncio
async def test_build_in_memory_index_pads_short_vector_list():
    doc = _doc(_chunk(1, "alpha"), _chunk(2, "beta"), _chunk(3, "gamma"))
    with patch.object(ret, "embed_texts",
                      new=AsyncMock(return_value=[_unit_vec(EMBED_DIM, 0)])):
        idx = await ret.build_in_memory_index(doc, api_key="k")
    assert len(idx.embeddings) == 3


# ─── InMemoryChunkIndex.retrieve ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_in_memory_retrieve_empty_index_returns_empty():
    idx = ret.InMemoryChunkIndex(chunks=[], embeddings=[], api_key="k")
    assert await idx.retrieve("turnover") == []


@pytest.mark.asyncio
async def test_in_memory_retrieve_returns_top_k_by_cosine():
    chunks = [_chunk(i, f"c{i}") for i in range(1, 5)]
    embeddings = [
        _unit_vec(EMBED_DIM, 0),  # closest to qvec
        _unit_vec(EMBED_DIM, 1),
        _unit_vec(EMBED_DIM, 2),
        _unit_vec(EMBED_DIM, 0),  # also closest — tie
    ]
    idx = ret.InMemoryChunkIndex(
        chunks=chunks, embeddings=embeddings, api_key="k"
    )
    qvec = _unit_vec(EMBED_DIM, 0)
    with patch.object(ret, "embed_query", new=AsyncMock(return_value=qvec)):
        hits = await idx.retrieve("turnover", top_k=2)
    assert len(hits) == 2
    pages = {h.chunk.page_number for h in hits}
    assert pages == {1, 4}  # the two perfect-match chunks
    assert hits[0].similarity == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_in_memory_retrieve_no_api_key_uses_keyword_fallback():
    chunks = [
        _chunk(1, "the turnover figure was high"),
        _chunk(2, "completely unrelated content"),
    ]
    embeddings = [[0.0] * EMBED_DIM, [0.0] * EMBED_DIM]
    idx = ret.InMemoryChunkIndex(
        chunks=chunks, embeddings=embeddings, api_key=""
    )
    hits = await idx.retrieve("turnover figure", top_k=2)
    assert hits[0].chunk.page_number == 1


@pytest.mark.asyncio
async def test_in_memory_retrieve_zero_query_vector_falls_back_to_keywords():
    chunks = [_chunk(1, "turnover revenue 4500")]
    embeddings = [_unit_vec(EMBED_DIM, 5)]
    idx = ret.InMemoryChunkIndex(
        chunks=chunks, embeddings=embeddings, api_key="k"
    )
    with patch.object(ret, "embed_query",
                      new=AsyncMock(return_value=[0.0] * EMBED_DIM)):
        hits = await idx.retrieve("turnover revenue", top_k=1)
    assert hits and hits[0].chunk.page_number == 1


# ─── SupabaseChunkIndex.retrieve ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_supabase_retrieve_passes_qvec_and_returns_hits():
    rpc_response = SimpleNamespace(data=[
        {"chunk_id": "p3-c0", "page_number": 3, "kind": "text",
         "heading": "SECTION A", "content": "turnover...", "similarity": 0.91},
        {"chunk_id": "p5-t0", "page_number": 5, "kind": "table",
         "heading": None, "content": "| turnover | 4500 |", "similarity": 0.87},
    ])
    supabase = MagicMock()
    rpc_obj = MagicMock()
    rpc_obj.execute.return_value = rpc_response
    supabase.rpc.return_value = rpc_obj

    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    qvec = _unit_vec(EMBED_DIM, 0)
    with patch.object(ret, "embed_query", new=AsyncMock(return_value=qvec)):
        hits = await idx.retrieve("turnover", top_k=2)

    supabase.rpc.assert_called_once()
    name, payload = supabase.rpc.call_args[0]
    assert name == "match_extraction_chunks"
    assert payload["match_report_id"] == "r1"
    assert payload["match_count"] == 2
    assert payload["query_embedding"] == qvec
    assert len(hits) == 2
    assert hits[0].chunk.chunk_id == "p3-c0"
    assert hits[0].similarity == pytest.approx(0.91)


@pytest.mark.asyncio
async def test_supabase_retrieve_rpc_failure_returns_empty():
    supabase = MagicMock()
    supabase.rpc.return_value.execute.side_effect = RuntimeError("connection refused")
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    with patch.object(ret, "embed_query",
                      new=AsyncMock(return_value=_unit_vec(EMBED_DIM, 0))):
        hits = await idx.retrieve("x")
    assert hits == []


@pytest.mark.asyncio
async def test_supabase_retrieve_zero_qvec_short_circuits():
    supabase = MagicMock()
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    with patch.object(ret, "embed_query",
                      new=AsyncMock(return_value=[0.0] * EMBED_DIM)):
        hits = await idx.retrieve("x")
    assert hits == []
    supabase.rpc.assert_not_called()


# ─── SupabaseChunkIndex.persist ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_supabase_persist_writes_one_row_per_chunk():
    doc = _doc(
        _chunk(1, "alpha", chunk_id="p1-c0", heading="SECTION A"),
        _chunk(2, "beta", chunk_id="p2-t0", kind="table"),
    )
    supabase = MagicMock()
    insert_obj = MagicMock()
    supabase.table.return_value.insert.return_value = insert_obj

    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    vecs = [_unit_vec(EMBED_DIM, 0), _unit_vec(EMBED_DIM, 1)]
    with patch.object(ret, "embed_texts", new=AsyncMock(return_value=vecs)):
        n = await idx.persist(doc)

    assert n == 2
    supabase.table.assert_called_once_with("extraction_chunks")
    rows = supabase.table.return_value.insert.call_args[0][0]
    assert rows[0]["chunk_id"] == "p1-c0"
    assert rows[0]["report_id"] == "r1"
    assert rows[0]["user_id"] == "u1"
    assert rows[0]["embedding"] is not None
    assert rows[1]["kind"] == "table"


@pytest.mark.asyncio
async def test_supabase_persist_empty_doc_is_noop():
    supabase = MagicMock()
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    assert await idx.persist(_doc()) == 0
    supabase.table.assert_not_called()


@pytest.mark.asyncio
async def test_supabase_persist_stores_null_embedding_when_all_zero():
    """If Gemini key was missing during embed, vectors come back all-zero;
    we should store NULL rather than a zero vector to avoid corrupting the
    ivfflat centroids."""
    doc = _doc(_chunk(1, "alpha", chunk_id="p1-c0"))
    supabase = MagicMock()
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="",
    )
    with patch.object(ret, "embed_texts",
                      new=AsyncMock(return_value=[[0.0] * EMBED_DIM])):
        await idx.persist(doc)
    rows = supabase.table.return_value.insert.call_args[0][0]
    assert rows[0]["embedding"] is None


@pytest.mark.asyncio
async def test_supabase_persist_swallows_insert_errors():
    doc = _doc(_chunk(1, "alpha", chunk_id="p1-c0"))
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.side_effect = \
        RuntimeError("duplicate key")
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    with patch.object(ret, "embed_texts",
                      new=AsyncMock(return_value=[_unit_vec(EMBED_DIM, 0)])):
        n = await idx.persist(doc)
    assert n == 0


# ─── SupabaseChunkIndex.persist_from_index ────────────────────────────────


@pytest.mark.asyncio
async def test_persist_from_index_reuses_embeddings_no_gemini_call():
    """persist_from_index() must NOT re-embed — it should reuse the vectors
    already on the InMemoryChunkIndex."""
    chunks = [_chunk(1, "alpha", chunk_id="p1-c0"),
              _chunk(2, "beta", chunk_id="p2-c0")]
    vecs = [_unit_vec(EMBED_DIM, 0), _unit_vec(EMBED_DIM, 1)]
    in_mem = ret.InMemoryChunkIndex(
        chunks=chunks, embeddings=vecs, api_key="k",
    )
    supabase = MagicMock()
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )

    with patch.object(ret, "embed_texts",
                      new=AsyncMock(side_effect=AssertionError("must not embed"))):
        n = await idx.persist_from_index(in_mem)

    assert n == 2
    rows = supabase.table.return_value.insert.call_args[0][0]
    assert rows[0]["chunk_id"] == "p1-c0"
    assert rows[1]["chunk_id"] == "p2-c0"
    # Embeddings carried through, not re-computed
    assert rows[0]["embedding"][0] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_persist_from_index_empty_index_is_noop():
    supabase = MagicMock()
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    in_mem = ret.InMemoryChunkIndex(chunks=[], embeddings=[], api_key="k")
    assert await idx.persist_from_index(in_mem) == 0
    supabase.table.assert_not_called()


@pytest.mark.asyncio
async def test_persist_from_index_stores_null_for_zero_vectors():
    chunks = [_chunk(1, "alpha", chunk_id="p1-c0")]
    in_mem = ret.InMemoryChunkIndex(
        chunks=chunks, embeddings=[[0.0] * EMBED_DIM], api_key="",
    )
    supabase = MagicMock()
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="",
    )
    await idx.persist_from_index(in_mem)
    rows = supabase.table.return_value.insert.call_args[0][0]
    assert rows[0]["embedding"] is None


@pytest.mark.asyncio
async def test_persist_from_index_swallows_insert_errors():
    chunks = [_chunk(1, "alpha", chunk_id="p1-c0")]
    in_mem = ret.InMemoryChunkIndex(
        chunks=chunks, embeddings=[_unit_vec(EMBED_DIM, 0)], api_key="k",
    )
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.side_effect = \
        RuntimeError("connection refused")
    idx = ret.SupabaseChunkIndex(
        supabase=supabase, user_id="u1", report_id="r1", api_key="k",
    )
    assert await idx.persist_from_index(in_mem) == 0
