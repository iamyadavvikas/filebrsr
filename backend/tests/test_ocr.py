"""Tests for the OCR fallback (Phase 2.1).

Network is fully mocked — these tests run offline. We assert the
orchestration logic (which pages get OCR'd, how results merge into
the Document, rate-limit cap, no-op paths) without spending any
free-tier quota.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ocr import ocr_document, ocr_pages
from app.pdf_parser import Chunk, Document

# ─── Fixtures ─────────────────────────────────────────────────────


def _doc_with_empty_pages(empty: list[int], num_pages: int = 5) -> Document:
    """Build a Document already populated with text chunks for the non-empty pages."""
    chunks = [
        Chunk(page_number=p, kind="text", content=f"existing page {p} text")
        for p in range(1, num_pages + 1)
        if p not in empty
    ]
    return Document(
        chunks=chunks,
        num_pages=num_pages,
        num_tables=0,
        total_chars=sum(len(c.content) for c in chunks),
        empty_pages=list(empty),
    )


# ─── ocr_document orchestration ───────────────────────────────────


@pytest.mark.asyncio
async def test_ocr_document_noop_when_no_empty_pages():
    doc = _doc_with_empty_pages([])
    before = doc.total_chars
    out = await ocr_document(doc, b"%PDF-1.4", api_key="fake")
    assert out is doc
    assert doc.total_chars == before  # unchanged


@pytest.mark.asyncio
async def test_ocr_document_noop_when_no_api_key():
    doc = _doc_with_empty_pages([2, 4])
    before_chunks = len(doc.chunks)
    out = await ocr_document(doc, b"%PDF-1.4", api_key="")
    assert out is doc
    assert len(doc.chunks) == before_chunks  # no chunks added


@pytest.mark.asyncio
async def test_ocr_document_merges_text_into_chunks():
    doc = _doc_with_empty_pages([2, 4])
    with patch("app.ocr.ocr_pages", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = {2: "scanned page 2 content", 4: "scanned page 4 content"}
        await ocr_document(doc, b"%PDF-1.4", api_key="test-key")

    # Two new chunks added, one per OCR'd page
    page_2_chunks = [c for c in doc.chunks if c.page_number == 2]
    page_4_chunks = [c for c in doc.chunks if c.page_number == 4]
    assert any(c.content == "scanned page 2 content" for c in page_2_chunks)
    assert any(c.content == "scanned page 4 content" for c in page_4_chunks)


@pytest.mark.asyncio
async def test_ocr_document_skips_empty_results():
    """OCR returning '' (blank page / failure) must not add a chunk."""
    doc = _doc_with_empty_pages([2, 4])
    initial_chunks = len(doc.chunks)
    with patch("app.ocr.ocr_pages", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = {2: "good text", 4: ""}
        await ocr_document(doc, b"%PDF-1.4", api_key="test-key")
    # Only one chunk added (page 2's), not two
    assert len(doc.chunks) == initial_chunks + 1


@pytest.mark.asyncio
async def test_ocr_document_keeps_chunks_in_page_order():
    """to_text() relies on chunks being in ascending page order."""
    doc = _doc_with_empty_pages([2, 4])
    with patch("app.ocr.ocr_pages", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = {2: "two", 4: "four"}
        await ocr_document(doc, b"%PDF-1.4", api_key="test-key")
    page_order = [c.page_number for c in doc.chunks]
    assert page_order == sorted(page_order)


@pytest.mark.asyncio
async def test_ocr_document_respects_max_pages_cap():
    """When more empty pages than max_pages, only the first N are OCR'd."""
    doc = _doc_with_empty_pages([2, 3, 4, 5], num_pages=6)
    with patch("app.ocr.ocr_pages", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = {}
        await ocr_document(doc, b"%PDF-1.4", api_key="test-key", max_pages=2)
    # ocr_pages was called with only the first 2 empty pages
    called_pages = mock_ocr.call_args.args[1]
    assert called_pages == [2, 3]


@pytest.mark.asyncio
async def test_ocr_document_updates_total_chars():
    doc = _doc_with_empty_pages([2])
    before = doc.total_chars
    with patch("app.ocr.ocr_pages", new_callable=AsyncMock) as mock_ocr:
        mock_ocr.return_value = {2: "x" * 1000}
        await ocr_document(doc, b"%PDF-1.4", api_key="test-key")
    assert doc.total_chars == before + 1000


# ─── ocr_pages low-level ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_ocr_pages_empty_input_returns_empty_dict():
    result = await ocr_pages(b"%PDF-1.4", [], api_key="fake")
    assert result == {}


@pytest.mark.asyncio
async def test_ocr_pages_no_api_key_returns_blanks():
    result = await ocr_pages(b"%PDF-1.4", [1, 2, 3], api_key="")
    assert result == {1: "", 2: "", 3: ""}


@pytest.mark.asyncio
async def test_ocr_pages_handles_blank_sentinel():
    """Model returning 'BLANK' must be converted to empty string."""
    with patch("app.ocr._render_page_png", return_value=b"\x89PNG"):
        with patch("app.ocr.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "BLANK"
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await ocr_pages(b"%PDF-1.4", [1], api_key="test-key")
            assert result == {1: ""}


@pytest.mark.asyncio
async def test_ocr_pages_returns_model_text():
    with patch("app.ocr._render_page_png", return_value=b"\x89PNG"):
        with patch("app.ocr.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "  | A | B |\n|---|---|\n| 1 | 2 |  "
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await ocr_pages(b"%PDF-1.4", [1], api_key="test-key")
            assert result[1] == "| A | B |\n|---|---|\n| 1 | 2 |"


@pytest.mark.asyncio
async def test_ocr_pages_render_failure_returns_empty():
    """A page that fails to render must not break the whole call."""
    with patch("app.ocr._render_page_png", side_effect=IndexError("page out of range")):
        result = await ocr_pages(b"%PDF-1.4", [999], api_key="test-key")
        assert result == {999: ""}


@pytest.mark.asyncio
async def test_ocr_pages_model_failure_returns_empty():
    with patch("app.ocr._render_page_png", return_value=b"\x89PNG"):
        with patch("app.ocr.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = RuntimeError("429 quota")
            mock_client_class.return_value = mock_client
            result = await ocr_pages(b"%PDF-1.4", [1], api_key="test-key")
            assert result == {1: ""}
