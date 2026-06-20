"""
Source citations for extracted BRSR values.

For every extracted field, look back at the parsed Document and find the
chunk most likely to be the source. Output:

    citations[section][field] = {
        "source_page": int,
        "source_chunk_id": str,
        "snippet": str,            # ~160 chars around the match
        "match_kind": "exact" | "numeric" | "fuzzy",
    }

Deterministic, no LLM call — runs in milliseconds and lets the dashboard
render "View source on page 47" next to every cell.

Design decisions:
  - We never mutate the extracted dict. Citations live in a sibling
    `citations` key so the frontend can opt in.
  - Very short / generic values ("Yes", "No", "NA", "0") are skipped —
    citing them is misleading (they appear hundreds of times).
  - Numeric values are searched with thousand-separator variants
    ("1234", "1,234", "12,34" Indian numbering) so 4,500.23 matches both
    "4500.23" and "4,500.23".
  - When multiple chunks match, we score on: (a) does the chunk also
    contain a token from the field name? (b) is the chunk a table?
    Tables almost always beat narrative chunks because BRSR numbers live
    in tables. (c) shorter chunks win — they're more specific.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from app.pdf_parser import Chunk, Document

logger = logging.getLogger("filebrsr")

# Values too generic to cite usefully.
_SKIP_VALUES = {"yes", "no", "na", "n/a", "none", "nil", "true", "false", "0", "-", ""}

# Field-name token splitter; "median_salary_male" → {"median", "salary", "male"}.
_FIELD_SPLIT_RE = re.compile(r"[_\-\s]+")

# Strip everything except digits, dot, and minus for numeric matching.
_NUM_NORMALISE_RE = re.compile(r"[^\d.\-]")


@dataclass
class Citation:
    """One source citation for one extracted field."""

    source_page: int
    source_chunk_id: str
    snippet: str
    match_kind: str  # "exact" | "numeric" | "fuzzy"


# ─── Value preparation ─────────────────────────────────────────────


def _value_to_search_strings(value: Any) -> list[str]:
    """
    Produce a small set of canonical strings to look for in chunk text.

    For numbers we generate both bare ("1234") and Indian-comma-separated
    ("12,34" / "1,23,456") variants. For raw strings we use the original
    plus a digits-only stripped version (so "₹ 450 Cr" still matches a
    table cell that just says "450").
    """
    if value is None:
        return []
    if isinstance(value, bool):
        return []  # always skip — too generic
    if isinstance(value, (int, float)):
        # 0 is too generic to cite (appears in every empty table cell)
        if value == 0:
            return []
        return _numeric_variants(value)

    s = str(value).strip()
    if not s or s.lower() in _SKIP_VALUES:
        return []

    variants: list[str] = [s]

    # Strip unit / currency markers and try the numeric core too
    digits_only = _NUM_NORMALISE_RE.sub("", s)
    if digits_only and digits_only not in {"-", "."}:
        try:
            num = float(digits_only)
            variants.extend(_numeric_variants(num))
        except ValueError:
            pass

    return variants


def _numeric_variants(num: float | int) -> list[str]:
    """
    "4500.23" → ["4500.23", "4,500.23", "4500", "4,500"] plus Indian
    lakh/crore comma format ("12,34,567").
    """
    if isinstance(num, float) and num.is_integer():
        num = int(num)
    out: list[str] = [str(num)]
    if isinstance(num, float):
        out.append(f"{num:,.2f}")
        out.append(f"{int(num):,}")
    else:
        out.append(f"{num:,}")
    out.append(_indian_format(int(num) if isinstance(num, (int, float)) else num))
    # De-dup while preserving order
    seen: set[str] = set()
    return [v for v in out if v and not (v in seen or seen.add(v))]


def _indian_format(n: int) -> str:
    """1234567 → '12,34,567' (lakh/crore grouping)."""
    if n < 0:
        return "-" + _indian_format(-n)
    s = str(n)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    # Group the remainder in pairs from the right
    groups: list[str] = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ",".join(groups) + "," + last3


# ─── Chunk search ──────────────────────────────────────────────────


def _field_tokens(field_name: str) -> set[str]:
    """`median_salary_male` → {'median', 'salary', 'male'} (length ≥ 3)."""
    return {t.lower() for t in _FIELD_SPLIT_RE.split(field_name) if len(t) >= 3}


def _make_snippet(content: str, needle: str, *, radius: int = 80) -> str:
    """Return a ~160-char window around `needle` in `content`."""
    lower = content.lower()
    pos = lower.find(needle.lower())
    if pos < 0:
        return content[: radius * 2].replace("\n", " ").strip()
    start = max(0, pos - radius)
    end = min(len(content), pos + len(needle) + radius)
    snippet = content[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(content):
        snippet = snippet + "…"
    return snippet


def find_citation(
    value: Any,
    field_name: str,
    chunks: Iterable[Chunk],
) -> Citation | None:
    """
    Find the best chunk-level citation for `value` (under `field_name`).

    Returns None when:
      - value is empty / generic ("Yes", "No", 0)
      - no chunk contains any variant of the value
    """
    search_strings = _value_to_search_strings(value)
    if not search_strings:
        return None

    field_toks = _field_tokens(field_name)
    candidates: list[tuple[int, Chunk, str, str]] = []  # (score, chunk, matched_string, match_kind)

    for chunk in chunks:
        lower = chunk.content.lower()
        for s in search_strings:
            if s.lower() not in lower:
                continue

            # Score: prefer tables, prefer chunks mentioning a field-name
            # token, prefer shorter chunks (more specific).
            score = 0
            if chunk.kind == "table":
                score += 10
            if any(t in lower for t in field_toks):
                score += 20
            # Length penalty: -1 for every 200 chars (so shorter beats
            # longer when other signals tie).
            score -= len(chunk.content) // 200

            # Classify match: numeric for any value that's a number or whose
            # original raw form is dominated by digits; "exact" only for
            # textual matches; "fuzzy" never hits today but reserved for
            # later embedding-based fallback.
            if isinstance(value, (int, float)) or s.replace(",", "").replace(".", "").replace("-", "").isdigit():
                match_kind = "numeric"
            elif s == str(value):
                match_kind = "exact"
            else:
                match_kind = "fuzzy"
            candidates.append((score, chunk, s, match_kind))
            break  # one match per chunk is enough

    if not candidates:
        return None

    # Highest score wins; tie-break by earliest page (auditors expect the
    # first occurrence).
    candidates.sort(key=lambda x: (-x[0], x[1].page_number))
    score, best_chunk, matched, kind = candidates[0]
    return Citation(
        source_page=best_chunk.page_number,
        source_chunk_id=best_chunk.chunk_id,
        snippet=_make_snippet(best_chunk.content, matched),
        match_kind=kind,
    )


# ─── Top-level orchestration ───────────────────────────────────────


def attach_citations(extracted: dict[str, Any], document: Document) -> dict[str, dict[str, dict[str, Any]]]:
    """
    Walk `extracted` (the merged section_a / section_b / section_c dict),
    look up each leaf field in `document.chunks`, and return a parallel
    citations dict.

    Output shape:
        {
          "section_a": {
              "turnover": {"source_page": 12, "source_chunk_id": "p12-t2",
                           "snippet": "...", "match_kind": "numeric"},
              ...
          },
          "section_b": {...},
          "section_c": {...},
        }

    Sections / fields with no citation are omitted (not nullified) so the
    dict is small enough to ship in every extract response.
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    chunks = document.chunks

    for section_name, section_data in extracted.items():
        if section_name not in {"section_a", "section_b", "section_c"}:
            continue
        if not isinstance(section_data, dict):
            continue

        section_citations: dict[str, dict[str, Any]] = {}
        for field_name, value in section_data.items():
            cite = find_citation(value, field_name, chunks)
            if cite is not None:
                section_citations[field_name] = asdict(cite)

        if section_citations:
            out[section_name] = section_citations

    return out
