"""
PDF parsing for BRSR extraction.

Combines pdfplumber's text and table extraction so that tabular BRSR data
(which is most of it) survives into the LLM prompt as readable markdown
instead of being flattened into space-mangled junk by extract_text() alone.

Produces both:
  - `text_with_tables(content)`: a single string suitable for legacy callers
    (regex/enhanced/agent extractors), tables rendered as pipe-format markdown
    inline between page text.
  - `parse_pdf(content)`: structured Document with per-page chunks of kind
    "text" or "table", each with page_number, chunk_id, and optional
    heading so downstream layers (Phase 2.3 citations, Phase 3 retrieval)
    can address them.

Pure-Python, no extra deps beyond pdfplumber.
"""
from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

import pdfplumber

logger = logging.getLogger("filebrsr")

ChunkKind = Literal["text", "table"]


# Heading detectors tuned for SEBI BRSR / annual-report layouts. Kept narrow
# on purpose so we don't over-split ordinary paragraphs that happen to start
# with a capital letter. Each regex is anchored to start-of-line.
_HEADING_PATTERNS = [
    re.compile(r"^\s*SECTION\s+[A-C]\b", re.IGNORECASE),
    re.compile(r"^\s*PRINCIPLE\s+\d\b", re.IGNORECASE),
    re.compile(r"^\s*(Essential|Leadership)\s+Indicators?\b", re.IGNORECASE),
    # Roman-numeral list item: "I. Details...", "II. Products/Services"
    re.compile(r"^\s*[IVX]{1,4}\.\s+[A-Z]"),
    # ALL CAPS short line (5–80 chars, no terminal punctuation)
    re.compile(r"^\s*[A-Z][A-Z0-9 ,&/\-]{4,79}$"),
]


def _is_heading(line: str) -> bool:
    """True if `line` looks like a BRSR section / principle / indicator heading."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    return any(p.search(stripped) for p in _HEADING_PATTERNS)


def _split_text_by_headings(text: str) -> list[tuple[str | None, str]]:
    """
    Split a block of text into [(heading, body), ...] pairs.

    The text before the first heading (if any) is returned with heading=None
    so a caller can still surface it. Adjacent headings with no body produce
    an empty-body entry, which the caller is free to drop.
    """
    lines = text.splitlines()
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in lines:
        if _is_heading(line):
            sections.append((line.strip(), []))
        else:
            sections[-1][1].append(line)
    return [(h, "\n".join(body).strip()) for h, body in sections if (h or any(b.strip() for b in body))]


@dataclass
class Chunk:
    """One piece of a parsed PDF — either a text block or a rendered table."""

    page_number: int
    kind: ChunkKind
    content: str  # markdown for tables, plain text for text
    table_index: int | None = None  # 0-based position of table within its page
    chunk_id: str = ""  # stable per-document id, e.g. "p3-c1" or "p3-t0"
    heading: str | None = None  # nearest preceding heading for text chunks


@dataclass
class Document:
    """A parsed PDF as an ordered sequence of chunks plus aggregate metrics."""

    chunks: list[Chunk] = field(default_factory=list)
    num_pages: int = 0
    num_tables: int = 0
    total_chars: int = 0
    empty_pages: list[int] = field(default_factory=list)  # 1-indexed pages with <500 chars

    def to_text(self) -> str:
        """Flatten back to a single string with page markers and inline markdown tables."""
        parts: list[str] = []
        current_page: int | None = None
        for chunk in self.chunks:
            if chunk.page_number != current_page:
                parts.append(f"\n--- Page {chunk.page_number} ---")
                current_page = chunk.page_number
            parts.append(chunk.content)
        return "\n".join(parts).strip()


def _render_table_as_markdown(rows: list[list[str | None]]) -> str:
    """
    Render a pdfplumber table (list of rows of cells) as a pipe-format markdown
    table. Multi-line cells are collapsed to single lines. Empty trailing rows
    and columns are dropped.
    """
    if not rows:
        return ""

    # Normalise: stringify, strip, collapse newlines, drop fully empty rows
    cleaned: list[list[str]] = []
    for row in rows:
        normalised = [
            (cell or "").replace("\n", " ").replace("|", "/").strip() for cell in row
        ]
        if any(normalised):
            cleaned.append(normalised)

    if not cleaned:
        return ""

    # Pad to uniform width
    width = max(len(r) for r in cleaned)
    for r in cleaned:
        r.extend([""] * (width - len(r)))

    # Drop columns that are entirely empty (right-most ones from pdfplumber artefacts)
    keep_cols = [i for i in range(width) if any(r[i] for r in cleaned)]
    if not keep_cols:
        return ""
    cleaned = [[r[i] for i in keep_cols] for r in cleaned]
    width = len(cleaned[0])

    # First non-empty row → header
    header = cleaned[0]
    body = cleaned[1:]

    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * width) + "|",
    ]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def parse_pdf(content: bytes, *, min_page_chars: int = 500, max_pages: int | None = None) -> Document:
    """
    Parse a PDF into structured chunks.

    For each page:
      1. Extract all tables → rendered as markdown chunks
      2. Extract text → kept as text chunk (un-deduped; this is fine, LLMs are robust)

    Pages whose total character output is below `min_page_chars` are recorded
    in `empty_pages` so a future OCR pass (Phase 2.1) can target them.

    `max_pages`, if set, caps how many pages are parsed (callers on free-tier
    LLM quotas use this to keep prompts under context limits).
    """
    doc = Document()

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        doc.num_pages = len(pages)

        for page_idx, page in enumerate(pages, start=1):
            page_chars = 0

            # Tables first so they're positioned before the text dump (and
            # because they're the higher-value signal for BRSR).
            try:
                tables = page.extract_tables() or []
            except Exception as e:
                logger.warning("table extraction failed on page %d: %s", page_idx, e)
                tables = []

            for tbl_idx, rows in enumerate(tables):
                rendered = _render_table_as_markdown(rows)
                if rendered:
                    doc.chunks.append(
                        Chunk(
                            page_number=page_idx,
                            kind="table",
                            content=rendered,
                            table_index=tbl_idx,
                            chunk_id=f"p{page_idx}-t{tbl_idx}",
                        )
                    )
                    page_chars += len(rendered)
                    doc.num_tables += 1

            # Text after tables, split by BRSR section / principle headings
            # so each chunk is small enough to be addressable + retrievable
            # (Phase 3) without breaking the LLM prompt down the middle of a
            # disclosure.
            try:
                text = page.extract_text() or ""
            except Exception as e:
                logger.warning("text extraction failed on page %d: %s", page_idx, e)
                text = ""

            if text.strip():
                sub_sections = _split_text_by_headings(text)
                for sub_idx, (heading, body) in enumerate(sub_sections):
                    block = (heading + "\n" + body).strip() if heading else body
                    if not block:
                        continue
                    doc.chunks.append(
                        Chunk(
                            page_number=page_idx,
                            kind="text",
                            content=block,
                            chunk_id=f"p{page_idx}-c{sub_idx}",
                            heading=heading,
                        )
                    )
                    page_chars += len(block)

            if page_chars < min_page_chars:
                doc.empty_pages.append(page_idx)

            doc.total_chars += page_chars

    return doc


def text_with_tables(content: bytes) -> str:
    """
    Convenience: parse and flatten to a single string for legacy callers
    (regex / enhanced / agent extractors all accept plain text today).
    """
    return parse_pdf(content).to_text()
