"""Tests for the table-aware PDF parser."""
from __future__ import annotations

import pytest

from app.pdf_parser import (
    _is_heading,
    _render_table_as_markdown,
    _split_text_by_headings,
    parse_pdf,
    text_with_tables,
)

# ─── Markdown rendering (pure) ─────────────────────────────────────


def test_render_table_basic():
    rows = [["Metric", "FY23", "FY24"], ["Energy", "100", "120"]]
    out = _render_table_as_markdown(rows)
    assert out.splitlines()[0] == "| Metric | FY23 | FY24 |"
    assert "|---|---|---|" == out.splitlines()[1]
    assert "Energy | 100 | 120" in out


def test_render_table_empty():
    assert _render_table_as_markdown([]) == ""
    assert _render_table_as_markdown([[None, None]]) == ""


def test_render_table_strips_empty_columns():
    rows = [["A", "", "B"], ["1", "", "2"]]
    out = _render_table_as_markdown(rows)
    assert "| A | B |" in out
    # column count should be 2, not 3
    assert out.count("|") < len(rows) * 5  # heuristic — no empty middle col


def test_render_table_escapes_pipes_in_cells():
    rows = [["a|b"], ["c"]]
    out = _render_table_as_markdown(rows)
    assert "a/b" in out  # pipes replaced so markdown isn't broken


def test_render_table_collapses_newlines():
    rows = [["Two\nLines"], ["x"]]
    out = _render_table_as_markdown(rows)
    assert "Two Lines" in out
    assert "\nLines" not in out


# ─── PDF parsing (with mocked pdfplumber) ──────────────────────────


class _FakePage:
    def __init__(self, text: str, tables: list[list[list[str]]] | None = None):
        self._text = text
        self._tables = tables or []

    def extract_text(self):
        return self._text

    def extract_tables(self):
        return self._tables


class _FakePDF:
    def __init__(self, pages: list[_FakePage]):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_pdfplumber(monkeypatch, pages: list[_FakePage]):
    import app.pdf_parser as pp

    def fake_open(_buf):
        return _FakePDF(pages)

    monkeypatch.setattr(pp.pdfplumber, "open", fake_open)


def test_parse_pdf_text_only(monkeypatch):
    _patch_pdfplumber(monkeypatch, [_FakePage("Hello world", [])])
    doc = parse_pdf(b"fake")
    assert doc.num_pages == 1
    assert doc.num_tables == 0
    assert len(doc.chunks) == 1
    assert doc.chunks[0].kind == "text"
    assert doc.chunks[0].content == "Hello world"


def test_parse_pdf_tables_emitted_before_text(monkeypatch):
    table = [["Metric", "Value"], ["Scope1", "1000"]]
    _patch_pdfplumber(monkeypatch, [_FakePage("Some narrative text.", [table])])
    doc = parse_pdf(b"fake")
    assert doc.num_tables == 1
    assert [c.kind for c in doc.chunks] == ["table", "text"]
    assert "Metric" in doc.chunks[0].content
    assert doc.chunks[0].table_index == 0


def test_parse_pdf_empty_pages_recorded(monkeypatch):
    # Page with only short text (< 500 chars default threshold)
    _patch_pdfplumber(monkeypatch, [_FakePage("Hi", [])])
    doc = parse_pdf(b"fake", min_page_chars=500)
    assert doc.empty_pages == [1]


def test_parse_pdf_max_pages(monkeypatch):
    _patch_pdfplumber(
        monkeypatch,
        [_FakePage(f"page {i}" * 200, []) for i in range(5)],
    )
    doc = parse_pdf(b"fake", max_pages=2)
    assert doc.num_pages == 2
    assert len({c.page_number for c in doc.chunks}) == 2


def test_parse_pdf_survives_table_extraction_error(monkeypatch):
    class Boom(_FakePage):
        def extract_tables(self):
            raise RuntimeError("pdfplumber bug")

    _patch_pdfplumber(monkeypatch, [Boom("Body text here.")])
    doc = parse_pdf(b"fake")
    # Text chunk still emitted; no crash
    assert len(doc.chunks) == 1
    assert doc.chunks[0].kind == "text"


def test_to_text_inserts_page_markers(monkeypatch):
    _patch_pdfplumber(
        monkeypatch,
        [_FakePage("p1 body", []), _FakePage("p2 body", [])],
    )
    out = parse_pdf(b"fake").to_text()
    assert "--- Page 1 ---" in out
    assert "--- Page 2 ---" in out
    assert out.index("p1 body") < out.index("p2 body")


def test_text_with_tables_convenience(monkeypatch):
    table = [["k", "v"], ["a", "1"]]
    _patch_pdfplumber(monkeypatch, [_FakePage("narrative", [table])])
    out = text_with_tables(b"fake")
    assert "narrative" in out
    assert "| k | v |" in out


# ─── Heading detection (Phase 2.2) ─────────────────────────────────


@pytest.mark.parametrize(
    "line",
    [
        "SECTION A: GENERAL DISCLOSURES",
        "Section B - Management & Process",
        "PRINCIPLE 1: Businesses should conduct...",
        "Principle 6",
        "Essential Indicators",
        "Leadership Indicator",
        "I. Details of the listed entity",
        "II. Products/Services",
        "EMPLOYEES AND WORKERS",
        "HUMAN RESOURCES & DEVELOPMENT",
    ],
)
def test_is_heading_recognises_brsr_patterns(line):
    assert _is_heading(line) is True


@pytest.mark.parametrize(
    "line",
    [
        "",
        "The company believes in sustainable growth.",
        "Total revenue for the year was Rs. 450 crore.",
        "a. Sub-item",
        # Long all-caps blocks are usually copy-pasted from headers — caller
        # decides; we cap at 120 chars to avoid those.
        "X" * 200,
    ],
)
def test_is_heading_rejects_non_headings(line):
    assert _is_heading(line) is False


def test_split_text_by_headings_basic():
    text = (
        "preamble text\n"
        "SECTION A: GENERAL DISCLOSURES\n"
        "body of section A\n"
        "more body\n"
        "PRINCIPLE 1: Ethics\n"
        "ethics body"
    )
    sections = _split_text_by_headings(text)
    assert len(sections) == 3
    assert sections[0] == (None, "preamble text")
    assert sections[1][0] == "SECTION A: GENERAL DISCLOSURES"
    assert "body of section A" in sections[1][1]
    assert sections[2][0] == "PRINCIPLE 1: Ethics"
    assert sections[2][1] == "ethics body"


def test_split_text_by_headings_no_preamble():
    text = "SECTION A\nbody"
    sections = _split_text_by_headings(text)
    # No preamble — first entry should be the heading itself
    assert sections[0][0] == "SECTION A"


# ─── parse_pdf with headings + chunk IDs ──────────────────────────


def test_parse_pdf_splits_text_by_headings(monkeypatch):
    text = (
        "intro paragraph\n"
        "SECTION A: GENERAL DISCLOSURES\n"
        "details about the entity\n"
        "PRINCIPLE 1\n"
        "ethics content"
    )
    _patch_pdfplumber(monkeypatch, [_FakePage(text, [])])
    doc = parse_pdf(b"fake")
    text_chunks = [c for c in doc.chunks if c.kind == "text"]
    assert len(text_chunks) == 3
    assert text_chunks[0].heading is None
    assert text_chunks[1].heading == "SECTION A: GENERAL DISCLOSURES"
    assert text_chunks[2].heading == "PRINCIPLE 1"


def test_parse_pdf_assigns_chunk_ids(monkeypatch):
    table = [["k", "v"], ["a", "1"]]
    _patch_pdfplumber(monkeypatch, [_FakePage("body", [table])])
    doc = parse_pdf(b"fake")
    ids = [c.chunk_id for c in doc.chunks]
    # Table first (kind == "table"), then text
    assert "p1-t0" in ids
    assert "p1-c0" in ids


def test_parse_pdf_chunk_ids_unique_across_pages(monkeypatch):
    _patch_pdfplumber(
        monkeypatch,
        [_FakePage("page one body", []), _FakePage("page two body", [])],
    )
    doc = parse_pdf(b"fake")
    ids = [c.chunk_id for c in doc.chunks]
    assert len(ids) == len(set(ids))
    assert {"p1-c0", "p2-c0"} == set(ids)


def test_parse_pdf_heading_chunk_content_includes_heading(monkeypatch):
    text = "PRINCIPLE 6\nenvironment disclosures here"
    _patch_pdfplumber(monkeypatch, [_FakePage(text, [])])
    doc = parse_pdf(b"fake")
    text_chunks = [c for c in doc.chunks if c.kind == "text"]
    # The heading line should be preserved at the top of its chunk so the LLM
    # sees the context even when this single chunk is sent in isolation.
    assert text_chunks[0].content.startswith("PRINCIPLE 6")
    assert "environment disclosures here" in text_chunks[0].content
