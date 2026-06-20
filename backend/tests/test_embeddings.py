"""Tests for app/embeddings.py (Phase 3.1)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app import embeddings as emb

# ─── Helpers ──────────────────────────────────────────────────────────────


def _fake_response(vectors: list[list[float]]):
    return SimpleNamespace(
        embeddings=[SimpleNamespace(values=v) for v in vectors]
    )


# ─── Pure helpers ─────────────────────────────────────────────────────────


def test_truncate_no_op_under_limit():
    assert emb._truncate("hello") == "hello"


def test_truncate_caps_at_max_chars():
    text = "x" * (emb.EMBED_MAX_CHARS + 10)
    out = emb._truncate(text)
    assert len(out) == emb.EMBED_MAX_CHARS


def test_chunked_yields_correct_sizes():
    out = list(emb._chunked(list(range(7)), 3))
    assert out == [[0, 1, 2], [3, 4, 5], [6]]


# ─── embed_texts ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_embed_texts_empty_input():
    assert await emb.embed_texts([], api_key="k") == []


@pytest.mark.asyncio
async def test_embed_texts_no_key_returns_zero_vectors():
    out = await emb.embed_texts(["a", "b"], api_key="")
    assert len(out) == 2
    assert all(len(v) == emb.EMBED_DIM for v in out)
    assert all(all(x == 0.0 for x in v) for v in out)


@pytest.mark.asyncio
async def test_embed_texts_single_batch():
    client = MagicMock()
    client.models.embed_content.return_value = _fake_response(
        [[0.1] * emb.EMBED_DIM, [0.2] * emb.EMBED_DIM]
    )
    with patch.object(emb.genai, "Client", return_value=client):
        out = await emb.embed_texts(["foo", "bar"], api_key="k")
    assert len(out) == 2
    assert out[0][0] == pytest.approx(0.1)
    assert out[1][0] == pytest.approx(0.2)
    client.models.embed_content.assert_called_once()


@pytest.mark.asyncio
async def test_embed_texts_multi_batch():
    # 250 inputs → batches of 100, 100, 50
    client = MagicMock()
    client.models.embed_content.side_effect = [
        _fake_response([[float(i)] * emb.EMBED_DIM for i in range(100)]),
        _fake_response([[float(i)] * emb.EMBED_DIM for i in range(100, 200)]),
        _fake_response([[float(i)] * emb.EMBED_DIM for i in range(200, 250)]),
    ]
    with patch.object(emb.genai, "Client", return_value=client):
        out = await emb.embed_texts(["t"] * 250, api_key="k")
    assert len(out) == 250
    assert out[0][0] == 0.0
    assert out[150][0] == 150.0
    assert out[249][0] == 249.0
    assert client.models.embed_content.call_count == 3


@pytest.mark.asyncio
async def test_embed_texts_truncates_oversize_input():
    client = MagicMock()
    captured = {}

    def _capture(model, contents, config):
        captured["contents"] = contents
        return _fake_response([[0.0] * emb.EMBED_DIM])

    client.models.embed_content.side_effect = _capture
    with patch.object(emb.genai, "Client", return_value=client):
        await emb.embed_texts(["x" * (emb.EMBED_MAX_CHARS + 5000)], api_key="k")
    assert len(captured["contents"][0]) == emb.EMBED_MAX_CHARS


@pytest.mark.asyncio
async def test_embed_texts_handles_api_failure_with_zero_vectors():
    client = MagicMock()
    client.models.embed_content.side_effect = RuntimeError("boom")
    with patch.object(emb.genai, "Client", return_value=client):
        out = await emb.embed_texts(["a", "b"], api_key="k")
    assert len(out) == 2
    assert all(all(x == 0.0 for x in v) for v in out)


@pytest.mark.asyncio
async def test_embed_texts_pads_short_response():
    client = MagicMock()
    client.models.embed_content.return_value = _fake_response(
        [[0.5] * emb.EMBED_DIM]  # only 1 vector for 3 inputs
    )
    with patch.object(emb.genai, "Client", return_value=client):
        out = await emb.embed_texts(["a", "b", "c"], api_key="k")
    assert len(out) == 3
    assert out[0][0] == pytest.approx(0.5)
    assert out[1] == [0.0] * emb.EMBED_DIM
    assert out[2] == [0.0] * emb.EMBED_DIM


@pytest.mark.asyncio
async def test_embed_texts_handles_dict_response_objects():
    """The mock-friendly dict-shaped embedding fallback path."""
    client = MagicMock()
    client.models.embed_content.return_value = SimpleNamespace(
        embeddings=[{"values": [0.7] * emb.EMBED_DIM}]
    )
    with patch.object(emb.genai, "Client", return_value=client):
        out = await emb.embed_texts(["a"], api_key="k")
    assert out[0][0] == pytest.approx(0.7)


# ─── embed_query ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_embed_query_uses_retrieval_query_task_type():
    client = MagicMock()
    captured = {}

    def _capture(model, contents, config):
        captured["config"] = config
        return _fake_response([[0.3] * emb.EMBED_DIM])

    client.models.embed_content.side_effect = _capture
    with patch.object(emb.genai, "Client", return_value=client):
        await emb.embed_query("turnover", api_key="k")
    assert captured["config"].task_type == "RETRIEVAL_QUERY"


@pytest.mark.asyncio
async def test_embed_query_no_key_returns_zero_vector():
    out = await emb.embed_query("q", api_key="")
    assert out == [0.0] * emb.EMBED_DIM
