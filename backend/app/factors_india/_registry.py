"""
Versioned emission-factor registry — internal loader.

Walks ``factors/**/*.json`` (repo root, sibling of ``backend/``), validates
each file against the contract documented in ``factors/_schema.json``, and
exposes a single cached list of :class:`FactorRecord` objects keyed by
``(scope, category, method, grid_region, state)``.

The validator is hand-rolled rather than using the ``jsonschema`` package
to avoid adding a runtime dependency for a single 100-line shape. Keep the
checks here in lock-step with ``factors/_schema.json``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ─── Paths ────────────────────────────────────────────────────────────────

# This file lives at backend/app/factors_india/_registry.py.
# The factors/ data directory lives at repo root, two levels above backend/.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
FACTORS_DIR = _REPO_ROOT / "factors"


# ─── Validation primitives ────────────────────────────────────────────────

_ALLOWED_SCOPES = {1, 2, 3}
_ALLOWED_METHODS = {"location_based", "market_based", "default"}
_ALLOWED_REGIONS = {"NR", "ER", "WR", "SR", "NER"}
_ALLOWED_SPECIFICITY = {"national", "regional", "state"}
_ALLOWED_JURISDICTIONS = {"IN", "AU"}
_REQUIRED_METADATA_KEYS = (
    "source", "version", "vintage", "citation_url", "published_on",
)
_REQUIRED_FACTOR_KEYS = (
    "scope", "category", "method", "unit", "regional_specificity", "value",
)


class FactorFileError(ValueError):
    """Raised when a factor-data file is structurally invalid."""


def _validate_metadata(meta: dict[str, Any], *, file: Path) -> None:
    missing = [k for k in _REQUIRED_METADATA_KEYS if k not in meta]
    if missing:
        raise FactorFileError(
            f"{file}: metadata missing required keys: {missing}"
        )
    vintage = meta["vintage"]
    if not (isinstance(vintage, list) and len(vintage) == 2):
        raise FactorFileError(
            f"{file}: metadata.vintage must be a [from, to] pair, got {vintage!r}"
        )
    try:
        date.fromisoformat(vintage[0])
        date.fromisoformat(vintage[1])
        date.fromisoformat(meta["published_on"])
    except (TypeError, ValueError) as exc:
        raise FactorFileError(f"{file}: invalid ISO date: {exc}") from exc
    jurisdiction = meta.get("jurisdiction", "IN")
    if jurisdiction not in _ALLOWED_JURISDICTIONS:
        raise FactorFileError(
            f"{file}: metadata.jurisdiction must be in {_ALLOWED_JURISDICTIONS}, "
            f"got {jurisdiction!r}"
        )


def _validate_factor(row: dict[str, Any], *, file: Path, idx: int) -> None:
    missing = [k for k in _REQUIRED_FACTOR_KEYS if k not in row]
    if missing:
        raise FactorFileError(
            f"{file}: factors[{idx}] missing required keys: {missing}"
        )
    if row["scope"] not in _ALLOWED_SCOPES:
        raise FactorFileError(
            f"{file}: factors[{idx}].scope must be in {_ALLOWED_SCOPES}, got {row['scope']!r}"
        )
    if row["method"] not in _ALLOWED_METHODS:
        raise FactorFileError(
            f"{file}: factors[{idx}].method must be in {_ALLOWED_METHODS}, got {row['method']!r}"
        )
    if row["regional_specificity"] not in _ALLOWED_SPECIFICITY:
        raise FactorFileError(
            f"{file}: factors[{idx}].regional_specificity must be in "
            f"{_ALLOWED_SPECIFICITY}, got {row['regional_specificity']!r}"
        )
    region = row.get("grid_region")
    if region is not None and region not in _ALLOWED_REGIONS:
        raise FactorFileError(
            f"{file}: factors[{idx}].grid_region must be one of {_ALLOWED_REGIONS} or null, "
            f"got {region!r}"
        )
    # Specificity consistency: 'regional' MUST carry a grid_region, 'state' MUST
    # carry a state, 'national' MUST carry neither. Catches curator typos.
    spec = row["regional_specificity"]
    state = row.get("state")
    if spec == "regional" and region is None:
        raise FactorFileError(
            f"{file}: factors[{idx}] regional specificity requires non-null grid_region"
        )
    if spec == "state" and not state:
        raise FactorFileError(
            f"{file}: factors[{idx}] state specificity requires non-null state"
        )
    if spec == "national" and (region is not None or state):
        raise FactorFileError(
            f"{file}: factors[{idx}] national specificity must have null grid_region and state"
        )
    if not isinstance(row["value"], (int, float)):
        raise FactorFileError(
            f"{file}: factors[{idx}].value must be numeric, got {type(row['value']).__name__}"
        )


# ─── Internal record ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class FactorRecord:
    """One parsed row from a factors/*.json file plus its file-level metadata.

    Public callers should not import this directly — use the IndiaFactor
    dataclass exposed by :mod:`app.factors_india`.
    """

    scope: int
    category: str
    method: str
    grid_region: str | None
    state: str | None
    regional_specificity: str
    unit: str
    value: float
    uncertainty: dict[str, Any] | None
    is_placeholder: bool
    # File-level metadata copied onto every row for cheap lookup
    jurisdiction: str
    source: str
    version: str
    vintage: tuple[str, str]
    citation_url: str


# ─── Loader ───────────────────────────────────────────────────────────────


def _load_file(path: Path) -> list[FactorRecord]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FactorFileError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise FactorFileError(f"{path}: top-level must be an object")
    if "metadata" not in payload or "factors" not in payload:
        raise FactorFileError(f"{path}: missing 'metadata' or 'factors' key")

    meta = payload["metadata"]
    _validate_metadata(meta, file=path)

    raw_factors = payload["factors"]
    if not isinstance(raw_factors, list) or not raw_factors:
        raise FactorFileError(f"{path}: 'factors' must be a non-empty list")

    out: list[FactorRecord] = []
    for idx, row in enumerate(raw_factors):
        if not isinstance(row, dict):
            raise FactorFileError(f"{path}: factors[{idx}] must be an object")
        _validate_factor(row, file=path, idx=idx)
        out.append(FactorRecord(
            scope=int(row["scope"]),
            category=str(row["category"]),
            method=str(row["method"]),
            grid_region=row.get("grid_region"),
            state=row.get("state"),
            regional_specificity=str(row["regional_specificity"]),
            unit=str(row["unit"]),
            value=float(row["value"]),
            uncertainty=row.get("uncertainty"),
            is_placeholder=bool(row.get("_placeholder", False)),
            jurisdiction=str(meta.get("jurisdiction", "IN")),
            source=str(meta["source"]),
            version=str(meta["version"]),
            vintage=(str(meta["vintage"][0]), str(meta["vintage"][1])),
            citation_url=str(meta["citation_url"]),
        ))
    return out


@lru_cache(maxsize=1)
def load_all_factors() -> tuple[FactorRecord, ...]:
    """Discover + validate every ``factors/**/*.json`` file. Cached for life
    of the process. Files whose name starts with ``_`` (e.g. ``_schema.json``)
    are skipped — they are documentation, not data.
    """
    if not FACTORS_DIR.is_dir():
        logger.warning("factors_india: no factors/ directory at %s", FACTORS_DIR)
        return ()
    records: list[FactorRecord] = []
    for path in sorted(FACTORS_DIR.rglob("*.json")):
        if path.name.startswith("_"):
            continue
        records.extend(_load_file(path))
    logger.info(
        "factors_india: loaded %d records from %d file(s)",
        len(records),
        len({r.version for r in records}),
    )
    return tuple(records)


def reset_cache() -> None:
    """Test helper — drop the cached load so the next call re-reads disk."""
    load_all_factors.cache_clear()
