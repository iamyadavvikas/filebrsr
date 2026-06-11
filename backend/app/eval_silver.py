"""Silver-label builder for self-supervised extraction evaluation (Phase 4.1).

We don't have manually labelled golden data — and shouldn't need it. Instead,
we exploit the fact that the pipeline already runs **three independent
extractors** (regex, enhanced, ai/agent). When ≥2 of them agree on a
*normalised* value for a field, that consensus is a high-confidence
**silver label** suitable for scoring any new extractor against.

This module is pure (no I/O, no model calls) — it operates on the three
extractor output dicts already produced upstream.

Typical use::

    from app.eval_silver import build_silver_labels

    silver = build_silver_labels(
        regex=extract_with_regex(text),
        enhanced=extract_enhanced(text),
        ai=extract_with_ai(text, ...),     # or extract_with_agent(...)
    )
    # silver: dict[str, SilverLabel] keyed by "<section>.<field_id>"
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

SECTION_KEYS = ("section_a", "section_b", "section_c")

# Indian-numbering multipliers commonly seen in BRSR filings. Values
# normalise to *rupees*. We deliberately keep this small — Phase 1.3 has a
# fuller normaliser that we can swap in later without changing the silver
# algorithm.
_UNIT_MULTIPLIERS: dict[str, float] = {
    "cr": 1e7,
    "crore": 1e7,
    "crores": 1e7,
    "lakh": 1e5,
    "lakhs": 1e5,
    "lac": 1e5,
    "lacs": 1e5,
    "mn": 1e6,
    "million": 1e6,
    "millions": 1e6,
    "bn": 1e9,
    "billion": 1e9,
    "billions": 1e9,
    "k": 1e3,
    "thousand": 1e3,
    "thousands": 1e3,
}

# Currency prefixes/symbols we strip before number parsing.
_CURRENCY_RE = re.compile(r"(?:rs\.?|inr|₹|usd|\$)", re.IGNORECASE)

# Numeric tolerance for silver-label equality (1%). Two extractors can
# legitimately disagree on the last rupee due to rounding; we don't want
# that to break consensus.
_NUMERIC_TOL = 0.01


# ─── Public types ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SilverLabel:
    """A consensus-derived label for one (section, field_id) pair."""

    section: str
    field_id: str
    value: Any                  # the canonical raw value (taken from majority)
    normalised: Any             # normalised form (number or lowercased string)
    agreement: int              # 2 or 3 — how many extractors agreed
    sources: tuple[str, ...]    # which extractor names contributed


# ─── Normalisation ───────────────────────────────────────────────────────


def normalise_value(value: Any) -> Any:
    """Coerce a raw extracted value to a comparable form.

    - ``None`` / empty strings → ``None``
    - Booleans pass through
    - Numbers pass through as ``float``
    - Strings:
        - strip whitespace, currency markers, commas
        - if numeric (optionally followed by Cr/Lakh/Mn/etc.), parse to float
        - otherwise return ``str.lower()``
    - Anything else: best-effort ``str().lower()``

    The return value is what gets compared for "agreement".
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Strip currency markers + commas
        cleaned = _CURRENCY_RE.sub("", s).replace(",", "").strip()
        if not cleaned:
            return s.lower()
        # Try: <number><optional unit>
        m = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)(?:\s*([a-zA-Z]+))?", cleaned)
        if m:
            num = float(m.group(1))
            unit = (m.group(2) or "").lower()
            if unit and unit in _UNIT_MULTIPLIERS:
                num *= _UNIT_MULTIPLIERS[unit]
            elif unit:
                # Unknown unit suffix: fall back to string compare so we
                # don't silently lose information
                return cleaned.lower()
            return num
        return s.lower()
    # dict / list / other — stringify as a last resort
    return str(value).lower()


def _values_equal(a: Any, b: Any) -> bool:
    """Equality check that tolerates floating-point and case noise."""
    if a is None or b is None:
        return a is b
    if isinstance(a, float) and isinstance(b, float):
        if a == 0 and b == 0:
            return True
        denom = max(abs(a), abs(b))
        return abs(a - b) / denom <= _NUMERIC_TOL
    # Mixed int/float covered above (normalise always returns float for nums)
    return a == b


# ─── Flatten extractor outputs ────────────────────────────────────────────


@dataclass
class _FieldVotes:
    """Internal scratch: votes for one (section, field_id)."""

    section: str
    field_id: str
    raw: dict[str, Any] = field(default_factory=dict)        # source -> raw
    normalised: dict[str, Any] = field(default_factory=dict)  # source -> norm


def _flatten(
    extractor_outputs: dict[str, dict[str, dict[str, Any]]],
) -> dict[tuple[str, str], _FieldVotes]:
    """Transform ``{source: {section: {field_id: value}}}`` to a per-field map."""
    out: dict[tuple[str, str], _FieldVotes] = {}
    for source, sections in extractor_outputs.items():
        if not isinstance(sections, dict):
            continue
        for section, fields in sections.items():
            if section not in SECTION_KEYS or not isinstance(fields, dict):
                continue
            for field_id, raw in fields.items():
                norm = normalise_value(raw)
                if norm is None:
                    continue  # treat empty/None as "did not extract"
                key = (section, field_id)
                votes = out.setdefault(key, _FieldVotes(section, field_id))
                votes.raw[source] = raw
                votes.normalised[source] = norm
    return out


# ─── Silver-label builder ────────────────────────────────────────────────


def build_silver_labels(
    *,
    regex: dict[str, Any] | None = None,
    enhanced: dict[str, Any] | None = None,
    ai: dict[str, Any] | None = None,
    min_agreement: int = 2,
) -> dict[str, SilverLabel]:
    """Build silver labels from 2-of-3 extractor consensus.

    Args:
        regex / enhanced / ai: extractor outputs in the canonical
            ``{section_a, section_b, section_c}`` shape. Missing extractors
            are tolerated (the function then needs all remaining ones to
            agree, since ``min_agreement`` defaults to 2).
        min_agreement: minimum number of extractors that must produce the
            same normalised value for the field to become a silver label.
            Defaults to 2 (sweet spot for free-tier extractors).

    Returns:
        Mapping ``"<section>.<field_id>" -> SilverLabel`` covering only
        fields that reached the agreement threshold. Order is deterministic
        (sorted by key) so callers can rely on it in test snapshots.
    """
    if min_agreement < 1:
        raise ValueError("min_agreement must be ≥ 1")

    sources: dict[str, dict[str, Any]] = {}
    if regex is not None:
        sources["regex"] = regex
    if enhanced is not None:
        sources["enhanced"] = enhanced
    if ai is not None:
        sources["ai"] = ai

    flat = _flatten(sources)
    silver: dict[str, SilverLabel] = {}

    for (section, field_id), votes in flat.items():
        if len(votes.normalised) < min_agreement:
            continue

        # Cluster by normalised equality. We can't put floats with tolerance
        # into a Counter directly, so do an O(n²) bucket pass — n ≤ 3 here.
        buckets: list[list[str]] = []  # each bucket = list of source names
        bucket_norms: list[Any] = []
        for src, norm in votes.normalised.items():
            placed = False
            for i, existing in enumerate(bucket_norms):
                if _values_equal(norm, existing):
                    buckets[i].append(src)
                    placed = True
                    break
            if not placed:
                buckets.append([src])
                bucket_norms.append(norm)

        # Largest bucket wins; ties broken by order extractors appeared
        # (regex > enhanced > ai). Counter preserves insertion order so the
        # earlier-added bucket wins ties naturally.
        best_idx = max(range(len(buckets)), key=lambda i: len(buckets[i]))
        if len(buckets[best_idx]) < min_agreement:
            continue

        winning_sources = tuple(buckets[best_idx])
        # Take the raw value from the first winning source (deterministic).
        canonical_src = winning_sources[0]
        silver[f"{section}.{field_id}"] = SilverLabel(
            section=section,
            field_id=field_id,
            value=votes.raw[canonical_src],
            normalised=bucket_norms[best_idx],
            agreement=len(buckets[best_idx]),
            sources=winning_sources,
        )

    # Stable ordering for snapshot tests / human readability
    return dict(sorted(silver.items()))


# ─── Convenience: agreement summary ──────────────────────────────────────


def silver_summary(silver: dict[str, SilverLabel]) -> dict[str, Any]:
    """Return a small dict describing the silver-label set.

    Useful for the eval CLI banner. Pure function, no I/O.
    """
    if not silver:
        return {
            "total": 0,
            "by_section": {s: 0 for s in SECTION_KEYS},
            "by_agreement": {},
        }
    by_section = Counter(lbl.section for lbl in silver.values())
    by_agreement = Counter(lbl.agreement for lbl in silver.values())
    return {
        "total": len(silver),
        "by_section": {s: by_section.get(s, 0) for s in SECTION_KEYS},
        "by_agreement": dict(sorted(by_agreement.items())),
    }
