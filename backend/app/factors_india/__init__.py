"""
Indian emission factors — versioned, source-attributed.

Public API for the ``factors-india`` slice. Reads JSON-backed factor files
under ``factors/`` (repo root) via :mod:`app.factors_india._registry` and
returns typed, immutable :class:`IndiaFactor` records with full provenance
(source, version, citation URL, vintage, uncertainty).

Slice 1 supports only ``(scope=2, category="electricity_purchased",
method="location_based")`` — Indian electricity grid factors for GHG-Protocol
Scope 2 location-based reporting from the CEA CO2 Baseline Database. Other
combinations raise :class:`FactorNotFound`.

Future slices add IPCC AR6 fuel factors (Scope 1), DEFRA / India-Railways
Scope 3, SLDC state overrides, BEE PAT benchmarks, and NIC→SASB sector
mapping. Each ships as a new JSON file under ``factors/`` plus a tiny
allow-list update here — no API changes.

Example::

    from app.factors_india import get_india_factor

    f = get_india_factor(
        scope=2,
        category="electricity_purchased",
        method="location_based",
        grid_region="WR",
    )
    print(f.value, f.unit, f.source)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.factors_india._registry import (
    FactorFileError,
    FactorRecord,
    load_all_factors,
    reset_cache,
)

__all__ = [
    "IndiaFactor",
    "FactorNotFound",
    "FactorFileError",
    "get_factor",
    "get_india_factor",
    "reset_cache",
]


# Supported (jurisdiction, scope, category, method) combinations. Adding a new
# combo means dropping a JSON file under factors/ AND adding it here — the
# explicit allow-list catches typos in caller arguments and gives clean errors.
_SUPPORTED_COMBOS: frozenset[tuple[str, int, str, str]] = frozenset({
    ("IN", 2, "electricity_purchased", "location_based"),
    ("AU", 2, "electricity_purchased", "location_based"),
})


@dataclass(frozen=True)
class IndiaFactor:
    """One emission factor with full provenance.

    Returned by :func:`get_india_factor`. Frozen so consumers can safely
    cache / hash. ``is_placeholder`` is True when the underlying JSON row
    is tagged ``_placeholder: true`` — i.e. the curator has not yet verified
    the number against the cited source. Slice 1 returns placeholder values
    rather than refusing; downstream strict-mode callers can inspect the
    flag and bail.
    """

    value: float
    unit: str
    source: str
    citation_url: str
    regional_specificity: str  # "national" | "regional" | "state"
    version: str
    vintage: tuple[str, str]
    uncertainty: dict[str, Any] | None
    is_placeholder: bool
    jurisdiction: str = "IN"


class FactorNotFound(LookupError):
    """No factor matches the requested (scope, category, method, region, state)."""


def _from_record(rec: FactorRecord) -> IndiaFactor:
    return IndiaFactor(
        value=rec.value,
        unit=rec.unit,
        source=rec.source,
        citation_url=rec.citation_url,
        regional_specificity=rec.regional_specificity,
        version=rec.version,
        vintage=rec.vintage,
        uncertainty=rec.uncertainty,
        is_placeholder=rec.is_placeholder,
        jurisdiction=rec.jurisdiction,
    )


def get_india_factor(
    *,
    scope: int,
    category: str,
    method: str,
    grid_region: str | None = None,
    state: str | None = None,
    reporting_period: tuple[str, str] | None = None,
) -> IndiaFactor:
    """Back-compat shim: India-only lookup (``get_factor("IN", ...)``)."""
    return get_factor(
        jurisdiction="IN",
        scope=scope,
        category=category,
        method=method,
        grid_region=grid_region,
        state=state,
        reporting_period=reporting_period,
    )


def get_factor(
    *,
    jurisdiction: str = "IN",
    scope: int,
    category: str,
    method: str,
    grid_region: str | None = None,
    state: str | None = None,
    reporting_period: tuple[str, str] | None = None,
) -> IndiaFactor:
    """Look up the most-specific emission factor for the request.

    Selection (most-specific first): ``state`` → ``grid_region`` (IN grids) →
    national, within the requested ``jurisdiction`` (``"IN"`` or ``"AU"``).

    Parameters
    ----------
    jurisdiction
        ISO 3166-1 alpha-2 country. ``"IN"`` (India / CEA) or ``"AU"``
        (Australia / NGA). Defaults to ``"IN"``.
    scope, category, method
        GHG Protocol scope (1/2/3), stable category key, and method. Only
        ``(jurisdiction, 2, "electricity_purchased", "location_based")`` is
        supported today; anything else raises :class:`FactorNotFound`.
    grid_region
        Indian electricity grid region (``NR``/``ER``/``WR``/``SR``/``NER``);
        ignored for AU which uses state-level rows.
    state
        Sub-national code: ISO 3166-2:IN (e.g. ``"MH"``) or an Australian
        state/territory (``"NSW"``, ``"VIC"``, ``"QLD"``, …).
    reporting_period
        ``(from_iso, to_iso)``; the edition whose ``vintage`` covers
        ``from_iso`` is selected.

    Raises
    ------
    FactorNotFound
        If no row matches, or the combo is outside the supported set.
    """
    combo = (jurisdiction, scope, category, method)
    if combo not in _SUPPORTED_COMBOS:
        raise FactorNotFound(
            f"unsupported factor request jurisdiction={jurisdiction!r}, "
            f"scope={scope!r}, category={category!r}, method={method!r}. "
            f"Supported: {sorted(_SUPPORTED_COMBOS)}."
        )

    records = load_all_factors()
    candidates = [
        r for r in records
        if r.jurisdiction == jurisdiction
        and r.scope == scope
        and r.category == category
        and r.method == method
    ]
    if not candidates:
        raise FactorNotFound(
            f"no factors loaded for jurisdiction={jurisdiction}, scope={scope}, "
            f"category={category!r}, method={method!r} — is factors/ populated?"
        )

    # Vintage filter (multi-edition aware). An edition covers the period if
    # period start ∈ [vintage_from, vintage_to].
    if reporting_period is not None:
        start = reporting_period[0]
        in_vintage = [
            r for r in candidates if r.vintage[0] <= start <= r.vintage[1]
        ]
        if not in_vintage:
            loaded = sorted({r.vintage for r in candidates})
            raise FactorNotFound(
                f"no loaded edition covers reporting period start {start!r}. "
                f"Loaded vintages: {loaded}"
            )
        candidates = in_vintage

    # Specificity ladder: state → regional → national.
    if state:
        state_rows = [r for r in candidates if r.state == state]
        if state_rows:
            return _from_record(state_rows[0])

    if grid_region:
        regional_rows = [
            r for r in candidates
            if r.regional_specificity == "regional" and r.grid_region == grid_region
        ]
        if regional_rows:
            return _from_record(regional_rows[0])

    national_rows = [r for r in candidates if r.regional_specificity == "national"]
    if national_rows:
        return _from_record(national_rows[0])

    raise FactorNotFound(
        f"no national fallback for jurisdiction={jurisdiction}, scope={scope}, "
        f"category={category!r}, method={method!r} after region/state filters "
        f"(grid_region={grid_region!r}, state={state!r})"
    )
