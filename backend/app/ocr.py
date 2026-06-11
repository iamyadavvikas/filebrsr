"""
OCR fallback for PDF pages that pdfplumber returns as empty.

Scanned annual reports — especially older filings or those generated as
print-to-PDF from non-text-bearing scans — produce empty pages when run
through `pdfplumber.extract_text()`. `parse_pdf()` flags those pages in
`Document.empty_pages`. This module renders each flagged page back to a
PNG via pypdfium2 and asks Gemini 2.0 Flash (Vision) to transcribe the
page as markdown.

Stays on the free tier:
  - Gemini 2.0 Flash: 1500 RPD, 15 RPM, multimodal in the same quota
  - pypdfium2: pure-Python wheel, no Poppler / ImageMagick dep
  - Rendering at 150 DPI keeps payload under ~500 KB per page

Graceful degradation: if rendering or the model call fails for a page,
that page is silently skipped (empty string returned) so a single bad
page never breaks a whole document.
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

import pypdfium2 as pdfium
from google import genai
from google.genai import types as genai_types

from app.pdf_parser import Chunk, Document

logger = logging.getLogger("filebrsr")

# Prompt is intentionally short — Vision models behave better with terse
# instructions, and most of the signal is in the page image.
_OCR_PROMPT = (
    "Transcribe every word, number and table on this page exactly as it "
    "appears. Render tables in pipe-format markdown. Preserve the reading "
    "order. Do not summarise, comment, or add anything that is not on the "
    "page. If the page is blank, reply with the single word: BLANK."
)


def _render_page_png(content: bytes, page_number: int, *, dpi: int = 150) -> bytes:
    """
    Render a single PDF page (1-indexed) to PNG bytes via pypdfium2.

    Raises IndexError if page_number is out of range.
    """
    pdf = pdfium.PdfDocument(content)
    try:
        if page_number < 1 or page_number > len(pdf):
            raise IndexError(f"page {page_number} out of range (1..{len(pdf)})")
        # pypdfium2 uses 0-indexed page access
        page = pdf[page_number - 1]
        # scale = DPI / 72 (PDF default)
        bitmap = page.render(scale=dpi / 72)
        pil_image = bitmap.to_pil()
        buf = io.BytesIO()
        # PNG keeps text crisp; quality matters more than file size here
        pil_image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    finally:
        pdf.close()


async def _ocr_single_page(
    content: bytes,
    page_number: int,
    *,
    client: Any,
    model: str,
    timeout: float,
) -> str:
    """Render + transcribe one page. Returns "" on any failure."""
    try:
        png_bytes = await asyncio.to_thread(_render_page_png, content, page_number)
    except Exception as e:
        logger.warning("OCR render failed for page %d: %s", page_number, e)
        return ""

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=[
                    _OCR_PROMPT,
                    genai_types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                ],
                config=genai_types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=4096,
                ),
            ),
            timeout=timeout,
        )
    except Exception as e:
        logger.warning("OCR model call failed for page %d: %s", page_number, e)
        return ""

    text = (response.text or "").strip()
    # Treat the model's own BLANK sentinel as empty so callers can decide
    # whether to skip the page or carry the placeholder.
    if text.upper() == "BLANK":
        return ""
    return text


async def ocr_pages(
    content: bytes,
    pages: list[int],
    *,
    api_key: str,
    model: str = "gemini-2.0-flash",
    concurrency: int = 4,
    timeout: float = 30.0,
) -> dict[int, str]:
    """
    OCR a list of PDF pages and return {page_number: markdown_text}.

    - `pages` is 1-indexed and may be empty (returns {} immediately).
    - Pages that fail to render or transcribe are returned with "" so the
      caller can distinguish "tried and got nothing" from "never tried".
    - Concurrency bounded by semaphore to stay under Gemini Flash's 15 RPM
      free-tier limit (4 in-flight + ~30s round-trip ≈ comfortable).
    """
    if not pages:
        return {}
    if not api_key:
        logger.info("OCR skipped — no Gemini API key configured")
        return {p: "" for p in pages}

    client = genai.Client(api_key=api_key)
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(page: int) -> tuple[int, str]:
        async with sem:
            text = await _ocr_single_page(
                content, page, client=client, model=model, timeout=timeout
            )
            return page, text

    results = await asyncio.gather(*[_bounded(p) for p in pages])
    return dict(results)


async def ocr_document(
    doc: Document,
    content: bytes,
    *,
    api_key: str,
    model: str = "gemini-2.0-flash",
    concurrency: int = 4,
    timeout: float = 30.0,
    max_pages: int | None = 20,
) -> Document:
    """
    Fill in OCR text for `doc.empty_pages` and return the same Document.

    - Mutates `doc` by appending one `Chunk(kind="text", ...)` per OCR'd page,
      keyed to that page_number. `to_text()` will then surface the OCR text
      under the existing `--- Page N ---` marker.
    - `max_pages` caps how many empty pages we'll OCR per document to stay
      under free-tier rate limits when someone uploads a fully scanned 200-
      page report (default 20 pages ≈ 80 KB of extra prompt).
    - No-op if `doc.empty_pages` is empty or `api_key` is falsy.
    """
    if not doc.empty_pages:
        return doc
    if not api_key:
        logger.info("OCR skipped — no API key")
        return doc

    pages_to_ocr = doc.empty_pages
    if max_pages is not None and len(pages_to_ocr) > max_pages:
        logger.info(
            "OCR truncated: %d empty pages, capping at %d",
            len(pages_to_ocr), max_pages,
        )
        pages_to_ocr = pages_to_ocr[:max_pages]

    ocr_results = await ocr_pages(
        content, pages_to_ocr,
        api_key=api_key, model=model,
        concurrency=concurrency, timeout=timeout,
    )

    added_chars = 0
    for page_number, text in ocr_results.items():
        if not text:
            continue
        doc.chunks.append(Chunk(
            page_number=page_number,
            kind="text",
            content=text,
            chunk_id=f"p{page_number}-ocr",
            heading="(OCR)",
        ))
        added_chars += len(text)

    # Keep chunks ordered by page number so to_text() emits a clean stream
    # instead of jumping back to OCR'd pages at the end.
    doc.chunks.sort(key=lambda c: (c.page_number, c.kind != "text"))
    doc.total_chars += added_chars
    logger.info(
        "OCR added %d chars across %d pages",
        added_chars, sum(1 for v in ocr_results.values() if v),
    )
    return doc
