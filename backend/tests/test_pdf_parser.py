"""Tests for the table-aware PDF parser."""
from __future__ import annotations

import io

import pytest

from app.pdf_parser import (
    Chunk,
    Document,
    _render_table_as_markdown,
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
