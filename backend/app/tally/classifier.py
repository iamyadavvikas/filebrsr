"""
HSN/SAC → GHG scope + Scope-3 category classifier.

Slice 0 uses a static prefix-match lookup loaded from
``lookups/hsn_scope3_v1.json`` (repo root) at import time. Any HSN that
doesn't match the longest available prefix is returned as ``unmapped`` and
routed to a human review queue (the ``raw_records.classification_confidence
= 'unmapped'`` index in migration v13).

Future slices add:
  * a Sarvam-M (Hindi narration) + GPT-4o-mini (English narration) classifier
    that fires only on ``unmapped`` rows
  * a confidence-scoring step that demotes loose 2-digit prefix matches to
    ``low`` / ``medium``
  * a feedback loop that turns curator-confirmed unmapped rows into new
    JSON seed entries
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Repo root: backend/app/tally/classifier.py → ../../../
_REPO_ROOT = Path(__file__).resolve().parents[3]
LOOKUPS_DIR = _REPO_ROOT / "lookups"
DEFAULT_SOURCE = LOOKUPS_DIR / "hsn_scope3_v1.json"


@dataclass(frozen=True)
class Classification:
    """Result of one HSN classification."""

    scope: int | None                          # 1, 2, 3, or None when unmapped
    scope3_category: str | None
    emission_basis: str | None                 # "quantity" | "spend"
    description: str | None
    matched_prefix: str | None                 # which lookup row hit
    version: str                               # source file version
    confidence: str                            # "high" | "medium" | "low" | "unmapped"


_UNMAPPED = Classification(
    scope=None, scope3_category=None, emission_basis=None,
    description=None, matched_prefix=None, version="hsn_scope3_v1",
    confidence="unmapped",
)


@dataclass(frozen=True)
class _LookupEntry:
    hsn_prefix: str
    description: str
    scope: int
    scope3_category: str | None
    emission_basis: str


@lru_cache(maxsize=1)
def _load_lookup(path: str | None = None) -> tuple[tuple[_LookupEntry, ...], str]:
    """Load and cache the HSN lookup table. Returns ``(entries, version)``;
    entries are sorted by prefix length DESC so we can prefix-match longest
    first without re-sorting per lookup."""
    src = Path(path) if path else DEFAULT_SOURCE
    if not src.is_file():
        logger.warning("tally classifier: lookup file missing at %s", src)
        return (), "missing"

    payload = json.loads(src.read_text(encoding="utf-8"))
    meta = payload.get("metadata", {})
    version = meta.get("version", "unknown")
    entries = tuple(
        sorted(
            (
                _LookupEntry(
                    hsn_prefix=str(row["hsn_prefix"]).strip(),
                    description=str(row["description"]),
                    scope=int(row["scope"]),
                    scope3_category=row.get("scope3_category"),
                    emission_basis=str(row["emission_basis"]),
                )
                for row in payload.get("entries", [])
            ),
            key=lambda e: -len(e.hsn_prefix),
        )
    )
    logger.info(
        "tally classifier: loaded %d HSN entries (%s)", len(entries), version
    )
    return entries, version


def reset_cache() -> None:
    """Test helper — drop the cached lookup."""
    _load_lookup.cache_clear()


def _normalise_hsn(hsn: str | None) -> str | None:
    """Tally permits HSN with separators (``2710.19.20``) and partial codes
    (``2710``). Strip everything non-digit and keep the leading 8 digits —
    the prefix match below handles short codes."""
    if not hsn:
        return None
    digits = "".join(ch for ch in hsn if ch.isdigit())
    return digits[:8] or None


def classify_hsn(hsn: str | None) -> Classification:
    """Look up an HSN code and return its scope / Scope-3 category.

    Match rule: longest-prefix wins. A ledger HSN of ``"27101920"`` matches
    the ``"2710"`` entry; an unrecognised HSN like ``"99999999"`` returns
    :data:`_UNMAPPED`.

    Confidence (slice 0 heuristic — refined in slice 1 with the LLM
    classifier):
      * prefix length ≥ 4 → "high"
      * prefix length == 2 → "medium"        (none today; future-proof)
      * no match           → "unmapped"
    """
    code = _normalise_hsn(hsn)
    if code is None:
        return _UNMAPPED

    entries, version = _load_lookup()
    if not entries:
        return _UNMAPPED

    for entry in entries:
        if code.startswith(entry.hsn_prefix):
            confidence = "high" if len(entry.hsn_prefix) >= 4 else "medium"
            return Classification(
                scope=entry.scope,
                scope3_category=entry.scope3_category,
                emission_basis=entry.emission_basis,
                description=entry.description,
                matched_prefix=entry.hsn_prefix,
                version=version,
                confidence=confidence,
            )
    return _UNMAPPED


def classify_with_llm_fallback(
    hsn: str | None,
    *,
    narration: str | None = None,
    vendor_name: str | None = None,
    ledger_name: str | None = None,
) -> Classification:
    """Like :func:`classify_hsn`, but on an ``unmapped`` result consult the
    configured LLM backend (Sarvam / OpenAI / mock / disabled).

    The LLM result is always stamped ``confidence == "medium"`` — never
    ``"high"``. ``"high"`` stays reserved for deterministic JSON-seed
    matches, so analysts can filter on confidence to separate auditable
    from model-derived rows.

    If the LLM backend is disabled or returns ``None``, the original
    ``_UNMAPPED`` result is returned unchanged.
    """
    # Lazy import: keeps classifier.py importable in environments where
    # llm_classifier's own optional deps haven't been touched yet.
    base = classify_hsn(hsn)
    if base.confidence != "unmapped":
        return base

    from app.tally.llm_classifier import get_llm_classifier  # noqa: PLC0415

    classifier = get_llm_classifier()
    llm_result = classifier.classify(
        narration=narration,
        vendor_name=vendor_name,
        ledger_name=ledger_name,
        hsn_code=hsn,
    )
    if llm_result is None:
        return base

    _, version = _load_lookup()
    return Classification(
        scope=llm_result.scope,
        scope3_category=llm_result.scope3_category,
        emission_basis=llm_result.emission_basis,
        description=llm_result.description,
        matched_prefix=llm_result.suggested_hsn_prefix,
        version=f"{version}+llm:{classifier.name}",
        confidence="medium",
    )
