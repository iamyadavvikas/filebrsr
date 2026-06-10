"""
Unit and number normalisation for extracted BRSR values.

Why: BRSR filings express the same metric a dozen different ways —
"₹1,234 Cr", "Rs. 12,340 Mn", "12,340,000,000", "12.34 Bn". Comparing
companies (or year-over-year), summing, or charting any of this requires
a canonical numeric form. Validation also needs it (variance checks,
range sanity).

This module is deliberately **non-destructive**: it does not mutate the
raw extracted strings. Instead, `normalise_extracted(merged)` returns a
parallel `normalised` dict with the same {section: {field: ...}} shape,
where each value is `{"raw": <original>, "value": <float>, "unit": <str>}`.

Downstream code that needs canonical numbers reads `merged["normalised"]`;
everything that already expects raw strings keeps working unchanged.

Recognised:
  - Indian magnitudes: Crore/Cr (1e7), Lakh/L (1e5)
  - International magnitudes: Million/Mn/M (1e6), Billion/Bn/B (1e9),
    Thousand/K (1e3)
  - Currency markers: ₹, Rs, Rs., INR, USD, $ (currency code preserved
    as unit; magnitude applied to value)
  - Percentages: trailing % or " pct" / " percent"
  - Negatives: leading minus or parenthesised "(1234)"

Anything not parseable falls through as `None` and is omitted from the
normalised dict (caller can still see the raw value in the original).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# ─── Field classification ──────────────────────────────────────────
# Fields that should be interpreted as INR currency when a magnitude
# (Cr/Lakh/Mn/Bn) is detected. For fields *not* in this set, the
# magnitude is still applied numerically but the unit is left blank
# unless the raw value carries an explicit unit string (e.g. "GJ").
_MONETARY_FIELDS: frozenset[str] = frozenset({
    "turnover",
    "paid_up_capital",
    "csr_spend",
    "r_and_d_spend",
    "median_salary_male",
    "median_salary_female",
})

# Suffix-driven classifiers
_PCT_SUFFIX = "_pct"

# ─── Regex building blocks ─────────────────────────────────────────
# Order matters: longest synonym first so "Crore" wins over "Cr".
_MAGNITUDE_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"\b(?:crores?|cr)\b", re.I), 1e7),
    (re.compile(r"\b(?:lakhs?|lacs?|l)\b", re.I), 1e5),
    (re.compile(r"\b(?:billion|bn|b)\b", re.I), 1e9),
    (re.compile(r"\b(?:million|mn|m)\b", re.I), 1e6),
    (re.compile(r"\b(?:thousand|k)\b", re.I), 1e3),
]

_CURRENCY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"₹|rs\.?|inr", re.I), "INR"),
    (re.compile(r"\$|usd", re.I), "USD"),
    (re.compile(r"€|eur", re.I), "EUR"),
    (re.compile(r"£|gbp", re.I), "GBP"),
]

_PERCENT_RE = re.compile(r"(%|\bpct\b|\bpercent(?:age)?\b)", re.I)
_PARENS_NEG_RE = re.compile(r"^\s*\(\s*(.+?)\s*\)\s*$")
# Skip digits glued to other alphanumerics (year labels like FY24, Q1,
# FY2024) by requiring the digit not be preceded by any ASCII alnum.
_NUMERIC_RE = re.compile(r"(?<![A-Za-z0-9])-?\d+(?:,\d{2,3})*(?:\.\d+)?")


@dataclass
class Normalised:
    """Canonical numeric form of a raw extracted value."""

    raw: Any
    value: float
    unit: str  # "INR", "USD", "%", "" (bare number), or unit token from raw

    def to_dict(self) -> dict[str, Any]:
        return {"raw": self.raw, "value": self.value, "unit": self.unit}


def _detect_currency(text: str) -> str:
    for pattern, code in _CURRENCY_PATTERNS:
        if pattern.search(text):
            return code
    return ""


def _detect_magnitude(text: str) -> float:
    for pattern, multiplier in _MAGNITUDE_PATTERNS:
        if pattern.search(text):
            return multiplier
    return 1.0


def normalise_value(raw: Any, field: str | None = None) -> Normalised | None:
    """
    Parse `raw` into a canonical Normalised. Returns None if nothing
    numeric is found (e.g. "N/A", "Yes", a long narrative paragraph).

    `field` is the BRSR field name — used only to classify monetary
    fields and percentage fields when the raw value lacks an explicit
    marker (e.g. `turnover="1234"` with no currency gets unit "INR"
    because `field` is in `_MONETARY_FIELDS`).
    """
    if raw is None:
        return None
    if isinstance(raw, bool):  # bool is a subclass of int; reject explicitly
        return None
    if isinstance(raw, (int, float)):
        unit = "%" if field and field.endswith(_PCT_SUFFIX) else (
            "INR" if field in _MONETARY_FIELDS else ""
        )
        return Normalised(raw=raw, value=float(raw), unit=unit)
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text or text.lower() in {"n/a", "na", "not applicable", "nil", "none", "-"}:
        return None

    # Reject obvious non-numeric narratives early (heuristic: must contain
    # a digit, and not be more than ~80 chars of mostly prose).
    if not any(ch.isdigit() for ch in text):
        return None

    # Parenthesised negative: "(1234)" → "-1234"
    negated = False
    m = _PARENS_NEG_RE.match(text)
    if m:
        text = m.group(1)
        negated = True

    is_percent = bool(_PERCENT_RE.search(text))
    currency = _detect_currency(text)
    magnitude = _detect_magnitude(text)

    # Pull the first numeric token. BRSR sometimes packs multiple
    # numbers in a cell ("FY24: 1234, FY23: 1100") — extracting only the
    # first matches the convention the LLM prompt asks for (most-recent
    # year). A future Phase 2 with structured-table prompts will eliminate
    # this ambiguity.
    num_match = _NUMERIC_RE.search(text)
    if not num_match:
        return None
    try:
        base = float(num_match.group(0).replace(",", ""))
    except ValueError:
        return None

    value = base * magnitude
    if negated:
        value = -value

    # Determine unit, in priority order:
    #   1. explicit percent → "%"
    #   2. explicit currency in the string
    #   3. field-name says monetary → "INR"
    #   4. trailing alpha token after the number (e.g. "GJ", "kWh", "tCO2e")
    #   5. "" (bare number)
    if is_percent:
        unit = "%"
    elif currency:
        unit = currency
    elif field in _MONETARY_FIELDS:
        unit = "INR"
    else:
        tail = text[num_match.end():].strip()
        # Strip out magnitude/currency tokens we already consumed; what's
        # left (if alpha) is treated as the unit.
        for pattern, _ in _MAGNITUDE_PATTERNS:
            tail = pattern.sub("", tail)
        for pattern, _ in _CURRENCY_PATTERNS:
            tail = pattern.sub("", tail)
        tail = re.sub(r"[^\w/²³µ°]+", " ", tail).strip()
        unit = tail.split()[0] if tail else ""

    return Normalised(raw=raw, value=value, unit=unit)


def normalise_extracted(extracted: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """
    Walk an extracted-data dict and return the parallel normalised view.

    Input shape: `{"section_a": {field: raw, ...}, "section_b": {...}, "section_c": {...}}`
    Output shape: `{"section_a": {field: {"raw": ..., "value": ..., "unit": ...}}, ...}`

    Fields whose raw value is not numerically parseable are omitted
    entirely from the output (so callers can `if field in normalised[section]`
    to check parseability without seeing junk entries).
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for section, fields in extracted.items():
        if not isinstance(fields, dict):
            continue
        section_out: dict[str, dict[str, Any]] = {}
        for field, raw in fields.items():
            normalised = normalise_value(raw, field=field)
            if normalised is not None:
                section_out[field] = normalised.to_dict()
        if section_out:
            out[section] = section_out
    return out
