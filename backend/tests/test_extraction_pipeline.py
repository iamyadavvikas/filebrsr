"""Tests for app/extraction_pipeline.py — unified pipeline (Phase 5.1).

Heavy stages (parse_pdf, OCR, all extractors, retrieval) are mocked so
the tests run in milliseconds and don't need a real PDF or API key.
What's verified:

  - merge precedence (enhanced → regex → ai)
  - AI fallback chain (agent → single-shot → empty)
  - normalise + citations + retrieval are called as sidecars and their
    failures don't fail the overall extraction
  - retrieval sub-pipeline persistence gating (guest vs real)
  - max_pages plumbing
  - return-shape contract
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import extraction_pipeline as ep
from app.extraction_pipeline import (
    EMPTY_SECTIONS,
    _merge_extractor_outputs,
    _run_ai_with_fallback,
    run_full_extraction,
    run_retrieval_extraction,
)


def _settings(**overrides) -> SimpleNamespace:
    """Build a duck-typed settings object covering the keys the pipeline reads."""
    base = {
        "GEMINI_API_KEY": "g-key",
        "GROQ_API_KEY": "groq-key",
        "ANTHROPIC_API_KEY": "anth-key",
        "ENABLE_RETRIEVAL_EXTRACTION": False,
        "RETRIEVAL_MAX_DATAPOINTS": 40,
        "RETRIEVAL_BATCH_SIZE": 5,
        "RETRIEVAL_TOP_K": 3,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _doc(text: str = "Some BRSR text", pages: int = 10) -> MagicMock:
    """Stand-in for the parse_pdf return — duck-types ParsedDocument enough
    for the pipeline's logging + to_text() call."""
    doc = MagicMock()
    doc.to_text.return_value = text
    doc.num_pages = pages
    doc.num_tables = 2
    doc.total_chars = len(text)
    doc.empty_pages = []
    return doc


def _sec(**kw):
    return {"section_a": kw, "section_b": {}, "section_c": {}}


# ─── _merge_extractor_outputs ────────────────────────────────────────────


def test_merge_precedence_ai_wins():
    rx = _sec(company_name="REGEX")
    en = _sec(company_name="ENHANCED")
    ai = _sec(company_name="AI")
    merged = _merge_extractor_outputs(regex=rx, enhanced=en, ai=ai)
    assert merged["section_a"]["company_name"] == "AI"


def test_merge_regex_fills_when_ai_missing():
    rx = _sec(turnover="100 Cr")
    en = _sec()
    ai = _sec()
    merged = _merge_extractor_outputs(regex=rx, enhanced=en, ai=ai)
    assert merged["section_a"]["turnover"] == "100 Cr"


def test_merge_enhanced_is_base():
    rx = _sec()
    en = _sec(only_enhanced="hello")
    ai = _sec()
    merged = _merge_extractor_outputs(regex=rx, enhanced=en, ai=ai)
    assert merged["section_a"]["only_enhanced"] == "hello"


def test_merge_returns_all_three_sections_even_when_empty():
    merged = _merge_extractor_outputs(regex={}, enhanced={}, ai={})
    assert set(merged) == {"section_a", "section_b", "section_c"}
    assert all(v == {} for v in merged.values())


# ─── _run_ai_with_fallback ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_fallback_returns_agent_output_when_rich():
    """Agent emitting ≥10 fields skips the single-shot supplement."""
    agent_out = {
        "section_a": {f"f{i}": "x" for i in range(11)},
        "section_b": {},
        "section_c": {},
    }
    with patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=agent_out)), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(side_effect=AssertionError("must not call"))):
        result = await _run_ai_with_fallback("text", settings=_settings())
    assert result == agent_out


@pytest.mark.asyncio
async def test_ai_fallback_supplements_when_agent_sparse():
    agent_out = _sec(only_agent="a")  # 1 field → triggers supplement
    single_shot = _sec(only_agent="a-DIFFERENT", new_field="ss")
    with patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=agent_out)), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=single_shot)):
        result = await _run_ai_with_fallback("text", settings=_settings())
    # Agent value preserved (supplement only fills gaps)
    assert result["section_a"]["only_agent"] == "a"
    # New field added
    assert result["section_a"]["new_field"] == "ss"


@pytest.mark.asyncio
async def test_ai_fallback_uses_single_shot_when_agent_raises():
    single_shot = _sec(f="ss")
    with patch.object(ep, "extract_with_agent",
                      new=AsyncMock(side_effect=RuntimeError("groq down"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=single_shot)):
        result = await _run_ai_with_fallback("text", settings=_settings())
    assert result["section_a"]["f"] == "ss"


@pytest.mark.asyncio
async def test_ai_fallback_returns_empty_when_all_fail():
    with patch.object(ep, "extract_with_agent",
                      new=AsyncMock(side_effect=RuntimeError("groq"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(side_effect=RuntimeError("gemini"))):
        result = await _run_ai_with_fallback("text", settings=_settings())
    assert result == EMPTY_SECTIONS


# ─── run_retrieval_extraction ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieval_disabled_returns_empty():
    s = _settings(ENABLE_RETRIEVAL_EXTRACTION=False)
    out = await run_retrieval_extraction(_doc(), settings=s)
    assert out == EMPTY_SECTIONS


@pytest.mark.asyncio
async def test_retrieval_no_key_returns_empty():
    s = _settings(ENABLE_RETRIEVAL_EXTRACTION=True, GEMINI_API_KEY="")
    out = await run_retrieval_extraction(_doc(), settings=s)
    assert out == EMPTY_SECTIONS


@pytest.mark.asyncio
async def test_retrieval_persists_for_real_report():
    s = _settings(ENABLE_RETRIEVAL_EXTRACTION=True)
    fake_index = MagicMock()
    fake_store = MagicMock()
    fake_store.persist_from_index = AsyncMock(return_value=7)

    extracted = _sec(R1="value")
    with patch.object(ep, "build_in_memory_index",
                      new=AsyncMock(return_value=fake_index)), \
         patch.object(ep, "SupabaseChunkIndex", return_value=fake_store), \
         patch.object(ep, "extract_with_retrieval",
                      new=AsyncMock(return_value=extracted)), \
         patch.object(ep, "select_retrievable_datapoints",
                      return_value=[]):
        out = await run_retrieval_extraction(
            _doc(), settings=s,
            user_id="u1", report_id="r1", supabase_client=MagicMock(),
        )
    fake_store.persist_from_index.assert_awaited_once_with(fake_index)
    assert out == extracted


@pytest.mark.asyncio
async def test_retrieval_skips_persistence_for_guest():
    s = _settings(ENABLE_RETRIEVAL_EXTRACTION=True)
    fake_index = MagicMock()
    with patch.object(ep, "build_in_memory_index",
                      new=AsyncMock(return_value=fake_index)), \
         patch.object(ep, "SupabaseChunkIndex",
                      side_effect=AssertionError("must not construct")), \
         patch.object(ep, "extract_with_retrieval",
                      new=AsyncMock(return_value=EMPTY_SECTIONS)), \
         patch.object(ep, "select_retrievable_datapoints",
                      return_value=[]):
        await run_retrieval_extraction(
            _doc(), settings=s,
            user_id="u1", report_id="guest", supabase_client=MagicMock(),
        )
    # No exception ⇒ SupabaseChunkIndex was indeed not constructed


@pytest.mark.asyncio
async def test_retrieval_persistence_failure_is_swallowed():
    s = _settings(ENABLE_RETRIEVAL_EXTRACTION=True)
    fake_store = MagicMock()
    fake_store.persist_from_index = AsyncMock(side_effect=RuntimeError("boom"))
    extracted = _sec(R="ok")
    with patch.object(ep, "build_in_memory_index",
                      new=AsyncMock(return_value=MagicMock())), \
         patch.object(ep, "SupabaseChunkIndex", return_value=fake_store), \
         patch.object(ep, "extract_with_retrieval",
                      new=AsyncMock(return_value=extracted)), \
         patch.object(ep, "select_retrievable_datapoints",
                      return_value=[]):
        out = await run_retrieval_extraction(
            _doc(), settings=s,
            user_id="u1", report_id="r1", supabase_client=MagicMock(),
        )
    # Persistence raised but the extraction itself still succeeded
    assert out == extracted


@pytest.mark.asyncio
async def test_retrieval_extraction_failure_returns_empty():
    s = _settings(ENABLE_RETRIEVAL_EXTRACTION=True)
    with patch.object(ep, "build_in_memory_index",
                      new=AsyncMock(side_effect=RuntimeError("embed down"))):
        out = await run_retrieval_extraction(_doc(), settings=s)
    assert out == EMPTY_SECTIONS


# ─── run_full_extraction ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_extraction_parse_failure_returns_failed():
    s = _settings()
    with patch.object(ep, "parse_pdf", side_effect=RuntimeError("bad pdf")):
        result = await run_full_extraction(file_bytes=b"x", settings=s)
    assert result["status"] == "failed"
    assert "PDF parse failed" in result["error"]
    assert result["extracted_data"] is None


@pytest.mark.asyncio
async def test_full_extraction_empty_text_returns_failed():
    s = _settings(GEMINI_API_KEY="")  # skip OCR
    doc = _doc(text="   ")
    with patch.object(ep, "parse_pdf", return_value=doc):
        result = await run_full_extraction(file_bytes=b"x", settings=s)
    assert result["status"] == "failed"
    assert "No text" in result["error"]


@pytest.mark.asyncio
async def test_full_extraction_happy_path_shape():
    s = _settings(GEMINI_API_KEY="")  # skip OCR + retrieval
    doc = _doc(text="lots of text")
    with patch.object(ep, "parse_pdf", return_value=doc), \
         patch.object(ep, "extract_with_regex", return_value=_sec(rx="r")), \
         patch.object(ep, "extract_enhanced", return_value=_sec(en="e")), \
         patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=_sec(company_name="ACME"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=_sec())), \
         patch.object(ep, "normalise_extracted", return_value={"x": 1}), \
         patch.object(ep, "attach_citations", return_value={"y": 2}):
        result = await run_full_extraction(file_bytes=b"x", settings=s)
    assert result["status"] == "completed"
    assert result["error"] is None
    ed = result["extracted_data"]
    assert ed["section_a"]["rx"] == "r"      # regex contribution
    assert ed["section_a"]["en"] == "e"      # enhanced contribution
    assert ed["section_a"]["company_name"] == "ACME"  # ai wins
    assert ed["normalised"] == {"x": 1}
    assert ed["citations"] == {"y": 2}
    assert ed["retrieved"] == EMPTY_SECTIONS  # retrieval disabled
    assert result["company_name"] == "ACME"


@pytest.mark.asyncio
async def test_full_extraction_normalise_failure_is_isolated():
    """A normalise crash must not fail the whole extraction."""
    s = _settings(GEMINI_API_KEY="")
    doc = _doc()
    with patch.object(ep, "parse_pdf", return_value=doc), \
         patch.object(ep, "extract_with_regex", return_value=_sec()), \
         patch.object(ep, "extract_enhanced", return_value=_sec()), \
         patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=_sec(f="v"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=_sec())), \
         patch.object(ep, "normalise_extracted",
                      side_effect=RuntimeError("normalise bug")), \
         patch.object(ep, "attach_citations", return_value={}):
        result = await run_full_extraction(file_bytes=b"x", settings=s)
    assert result["status"] == "completed"
    assert result["extracted_data"]["normalised"] == {}
    assert result["extracted_data"]["section_a"]["f"] == "v"


@pytest.mark.asyncio
async def test_full_extraction_citations_failure_is_isolated():
    s = _settings(GEMINI_API_KEY="")
    doc = _doc()
    with patch.object(ep, "parse_pdf", return_value=doc), \
         patch.object(ep, "extract_with_regex", return_value=_sec()), \
         patch.object(ep, "extract_enhanced", return_value=_sec()), \
         patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=_sec(f="v"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=_sec())), \
         patch.object(ep, "normalise_extracted", return_value={}), \
         patch.object(ep, "attach_citations",
                      side_effect=RuntimeError("citations bug")):
        result = await run_full_extraction(file_bytes=b"x", settings=s)
    assert result["status"] == "completed"
    assert result["extracted_data"]["citations"] == {}


@pytest.mark.asyncio
async def test_full_extraction_ocr_failure_is_isolated():
    """OCR failure shouldn't kill the run — text from pdfplumber still works."""
    s = _settings()  # gemini key set, so OCR is attempted
    doc = _doc()
    with patch.object(ep, "parse_pdf", return_value=doc), \
         patch.object(ep, "ocr_document",
                      new=AsyncMock(side_effect=RuntimeError("ocr down"))), \
         patch.object(ep, "extract_with_regex", return_value=_sec()), \
         patch.object(ep, "extract_enhanced", return_value=_sec()), \
         patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=_sec(f="v"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=_sec())), \
         patch.object(ep, "normalise_extracted", return_value={}), \
         patch.object(ep, "attach_citations", return_value={}), \
         patch.object(ep, "build_in_memory_index",
                      new=AsyncMock(return_value=MagicMock())), \
         patch.object(ep, "extract_with_retrieval",
                      new=AsyncMock(return_value=EMPTY_SECTIONS)), \
         patch.object(ep, "select_retrievable_datapoints", return_value=[]):
        result = await run_full_extraction(file_bytes=b"x", settings=s)
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_full_extraction_max_pages_forwarded():
    s = _settings(GEMINI_API_KEY="")
    doc = _doc()
    with patch.object(ep, "parse_pdf", return_value=doc) as mock_parse, \
         patch.object(ep, "extract_with_regex", return_value=_sec()), \
         patch.object(ep, "extract_enhanced", return_value=_sec()), \
         patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=_sec(f="v"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=_sec())), \
         patch.object(ep, "normalise_extracted", return_value={}), \
         patch.object(ep, "attach_citations", return_value={}):
        await run_full_extraction(
            file_bytes=b"x", settings=s, max_pages=80,
        )
    mock_parse.assert_called_once_with(b"x", max_pages=80)


@pytest.mark.asyncio
async def test_full_extraction_no_max_pages_omits_kwarg():
    """When max_pages is None, parse_pdf is called positionally (legacy
    behavior for callers that never passed it)."""
    s = _settings(GEMINI_API_KEY="")
    doc = _doc()
    with patch.object(ep, "parse_pdf", return_value=doc) as mock_parse, \
         patch.object(ep, "extract_with_regex", return_value=_sec()), \
         patch.object(ep, "extract_enhanced", return_value=_sec()), \
         patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=_sec(f="v"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=_sec())), \
         patch.object(ep, "normalise_extracted", return_value={}), \
         patch.object(ep, "attach_citations", return_value={}):
        await run_full_extraction(file_bytes=b"x", settings=s)
    mock_parse.assert_called_once_with(b"x")


@pytest.mark.asyncio
async def test_full_extraction_includes_raw_subextractor_outputs():
    """Callers need _raw for downstream confidence/gap-analysis logic."""
    s = _settings(GEMINI_API_KEY="")
    doc = _doc()
    with patch.object(ep, "parse_pdf", return_value=doc), \
         patch.object(ep, "extract_with_regex",
                      return_value=_sec(rx_only="r1")), \
         patch.object(ep, "extract_enhanced",
                      return_value=_sec(en_only="e1")), \
         patch.object(ep, "extract_with_agent",
                      new=AsyncMock(return_value=_sec(ai_only="a1"))), \
         patch.object(ep, "extract_with_ai",
                      new=AsyncMock(return_value=_sec())), \
         patch.object(ep, "normalise_extracted", return_value={}), \
         patch.object(ep, "attach_citations", return_value={}):
        result = await run_full_extraction(file_bytes=b"x", settings=s)
    raw = result["_raw"]
    assert raw["regex"]["section_a"]["rx_only"] == "r1"
    assert raw["enhanced"]["section_a"]["en_only"] == "e1"
    assert raw["ai"]["section_a"]["ai_only"] == "a1"
