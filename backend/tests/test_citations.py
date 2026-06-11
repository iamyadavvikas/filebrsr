"""Tests for source-citation attachment (Phase 2.3)."""
from __future__ import annotations

import pytest

from app.citations import (
    _indian_format,
    _numeric_variants,
    _value_to_search_strings,
    attach_citations,
    find_citation,
)
from app.pdf_parser import Chunk, Document

# ─── Helpers ──────────────────────────────────────────────────────


def _chunks(*items: tuple[int, str, str, str | None]) -> list[Chunk]:
    """items = (page, kind, content, chunk_id_or_None)."""
    out: list[Chunk] = []
    for page, kind, content, chunk_id in items:
        out.append(Chunk(
            page_number=page,
            kind=kind,
            content=content,
            chunk_id=chunk_id or f"p{page}-c0",
        ))
    return out


# ─── Numeric formatting helpers ───────────────────────────────────


@pytest.mark.parametrize("n,expected", [
    (1234, "1,234"),
    (123456, "1,23,456"),
    (12345678, "1,23,45,678"),
    (100, "100"),
    (0, "0"),
])
def test_indian_format(n, expected):
    assert _indian_format(n) == expected


def test_numeric_variants_includes_indian_and_western():
    out = _numeric_variants(123456)
    assert "123456" in out
    assert "123,456" in out      # western thousands
    assert "1,23,456" in out     # Indian lakh
    # No duplicates
    assert len(out) == len(set(out))


def test_numeric_variants_floats():
    out = _numeric_variants(4500.23)
    assert "4500.23" in out
    assert "4,500.23" in out


# ─── Search-string preparation ────────────────────────────────────


@pytest.mark.parametrize("value", [None, True, False, "", "Yes", "No", "NA", 0, "0"])
def test_value_to_search_strings_skips_generic(value):
    assert _value_to_search_strings(value) == []


def test_value_to_search_strings_currency_string():
    out = _value_to_search_strings("₹ 450 Cr")
    assert "₹ 450 Cr" in out
    assert "450" in out


def test_value_to_search_strings_indian_lakh_format():
    """An extracted value of '12,34,567' should be searched both ways."""
    out = _value_to_search_strings("12,34,567")
    assert "12,34,567" in out
    assert "1234567" in out or "12,34,567" in out


# ─── find_citation: core matching ─────────────────────────────────


def test_find_citation_returns_none_when_no_match():
    chunks = _chunks((1, "text", "no numbers here", None))
    assert find_citation("12345", "turnover", chunks) is None


def test_find_citation_returns_none_for_skip_values():
    chunks = _chunks((1, "text", "Yes No yes", None))
    assert find_citation("Yes", "csr_applicable", chunks) is None


def test_find_citation_prefers_table_over_text():
    chunks = _chunks(
        (1, "text", "turnover was 1234 crore", None),
        (2, "table", "| Metric | Value |\n| turnover | 1234 |", "p2-t0"),
    )
    cite = find_citation("1234", "turnover", chunks)
    assert cite is not None
    assert cite.source_chunk_id == "p2-t0"
    assert cite.source_page == 2


def test_find_citation_prefers_chunk_with_field_token():
    """Same kind on both pages — the one that also mentions the field name wins."""
    chunks = _chunks(
        (1, "text", "the number 4500 appeared somewhere", None),
        (3, "text", "Total turnover for the year was 4500", "p3-c0"),
    )
    cite = find_citation("4500", "turnover", chunks)
    assert cite is not None
    assert cite.source_chunk_id == "p3-c0"


def test_find_citation_includes_snippet():
    long_content = "a" * 200 + " turnover was 4500 crore " + "b" * 200
    chunks = _chunks((5, "text", long_content, "p5-c0"))
    cite = find_citation("4500", "turnover", chunks)
    assert cite is not None
    assert "4500" in cite.snippet
    assert len(cite.snippet) < 400


def test_find_citation_match_kind_exact_vs_numeric():
    chunks = _chunks((1, "text", "Reliance Industries Limited operates...", "p1-c0"))
    cite = find_citation("Reliance Industries Limited", "company_name", chunks)
    assert cite is not None
    assert cite.match_kind == "exact"

    chunks2 = _chunks((1, "table", "| turnover | 9500 |", "p1-t0"))
    cite2 = find_citation(9500, "turnover", chunks2)
    assert cite2 is not None
    assert cite2.match_kind == "numeric"


def test_find_citation_earliest_page_wins_on_tie():
    chunks = _chunks(
        (7, "text", "turnover 1234 mentioned again", "p7-c0"),
        (3, "text", "turnover 1234 first mentioned", "p3-c0"),
    )
    cite = find_citation("1234", "turnover", chunks)
    assert cite is not None
    assert cite.source_page == 3


def test_find_citation_numeric_value_via_indian_format():
    """Value stored as int 123456 should find a chunk with Indian-format '1,23,456'."""
    chunks = _chunks((4, "table", "| Revenue | 1,23,456 |", "p4-t0"))
    cite = find_citation(123456, "revenue", chunks)
    assert cite is not None
    assert cite.source_page == 4


# ─── attach_citations: orchestration ──────────────────────────────


def _doc(*chunks: Chunk) -> Document:
    return Document(chunks=list(chunks), num_pages=max(c.page_number for c in chunks))


def test_attach_citations_skips_unknown_sections():
    extracted = {"section_a": {"foo": "bar"}, "metadata": {"file": "x.pdf"}}
    doc = _doc(Chunk(page_number=1, kind="text", content="bar", chunk_id="p1-c0"))
    out = attach_citations(extracted, doc)
    assert "metadata" not in out


def test_attach_citations_emits_only_matched_fields():
    extracted = {
        "section_a": {
            "company_name": "Acme Steel Ltd",
            "turnover": "4500",
            "csr_applicable": "Yes",      # generic — should be skipped
            "ghost_field": "9999999999",  # not in doc
        },
    }
    chunks = [
        Chunk(page_number=1, kind="text",
              content="Acme Steel Ltd reports turnover of 4500",
              chunk_id="p1-c0"),
    ]
    out = attach_citations(extracted, _doc(*chunks))
    assert "company_name" in out["section_a"]
    assert "turnover" in out["section_a"]
    assert "csr_applicable" not in out["section_a"]
    assert "ghost_field" not in out["section_a"]


def test_attach_citations_omits_empty_sections():
    extracted = {"section_a": {"company_name": "Unknown Co"}, "section_b": {}}
    doc = _doc(Chunk(page_number=1, kind="text",
                     content="totally unrelated text",
                     chunk_id="p1-c0"))
    out = attach_citations(extracted, doc)
    assert "section_a" not in out
    assert "section_b" not in out


def test_attach_citations_full_shape():
    extracted = {
        "section_a": {"turnover": "4500"},
        "section_c": {"scope_1_emissions": "12345"},
    }
    chunks = [
        Chunk(page_number=3, kind="table",
              content="| Metric | Value |\n| turnover | 4500 |",
              chunk_id="p3-t0"),
        Chunk(page_number=47, kind="table",
              content="| Scope | tCO2e |\n| 1 emissions | 12,345 |",
              chunk_id="p47-t1"),
    ]
    out = attach_citations(extracted, _doc(*chunks))
    assert out["section_a"]["turnover"]["source_page"] == 3
    assert out["section_a"]["turnover"]["source_chunk_id"] == "p3-t0"
    assert out["section_c"]["scope_1_emissions"]["source_page"] == 47
    assert "match_kind" in out["section_c"]["scope_1_emissions"]


def test_attach_citations_handles_non_dict_section_values():
    """If a section is accidentally a list/None, we must not crash."""
    extracted = {"section_a": None, "section_b": [1, 2, 3]}
    out = attach_citations(extracted, _doc(
        Chunk(page_number=1, kind="text", content="x", chunk_id="p1-c0"),
    ))
    assert out == {}
