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
    "get_india_factor",
    "reset_cache",
]


# Slice 1 only supports this exact combination. Adding new combos means
# dropping a JSON file under factors/ AND adding it here — the explicit
# allow-list catches typos in caller arguments and gives clean error messages.
_SUPPORTED_COMBOS: frozenset[tuple[int, str, str]] = frozenset({
    (2, "electricity_purchased", "location_based"),
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
    """Look up the most-specific Indian emission factor for the request.

    Selection (most-specific first):

    1. ``state`` provided AND a state-level row exists → return state factor.
       (Slice 1 has no state rows; ready for SLDCs in slice 2.)
    2. ``grid_region`` ∈ {NR, ER, WR, SR, NER} AND a regional row exists →
       return regional factor.
    3. National (all-India weighted) row.

    Parameters
    ----------
    scope, category, method
        GHG Protocol scope (1/2/3), stable category key, and method.
        Slice 1 only supports ``(2, "electricity_purchased", "location_based")``;
        anything else raises :class:`FactorNotFound`.
    grid_region
        Indian electricity grid region per CEA convention: ``NR``, ``ER``,
        ``WR``, ``SR``, ``NER``. ``None`` falls back to all-India.
    state
        ISO 3166-2:IN state code (e.g. ``"MH"``). ``None`` falls back to
        grid region / national. Slice 1 has no state overrides.
    reporting_period
        ``(from_iso, to_iso)`` pair. Pick the loaded edition whose
        ``vintage`` covers ``from_iso``. Slice 1 only loads CEA v20
        (vintage = FY2024-25); periods outside that range raise
        :class:`FactorNotFound`.

    Raises
    ------
    FactorNotFound
        If no row matches, or the requested combo is outside the slice's
        supported set.
    """
    combo = (scope, category, method)
    if combo not in _SUPPORTED_COMBOS:
        raise FactorNotFound(
            f"factors-india slice 1 does not support "
            f"scope={scope!r}, category={category!r}, method={method!r}. "
            f"Supported: {sorted(_SUPPORTED_COMBOS)}. "
            f"Future slices will add Scope 1 (IPCC AR6), Scope 3 (DEFRA), "
            f"market-based Scope 2 (CEA portfolio), and BEE PAT sector benchmarks."
        )

    records = load_all_factors()
    candidates = [
        r for r in records
        if r.scope == scope and r.category == category and r.method == method
    ]
    if not candidates:
        raise FactorNotFound(
            f"no factors loaded for scope={scope}, category={category!r}, "
            f"method={method!r} — is factors/ populated?"
        )

    # Vintage filter (slice 1: single edition, but written so multi-edition
    # files Just Work in slice 2). Use the period start to choose; an edition
    # covers the period if start ∈ [vintage_from, vintage_to].
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
        f"no national fallback for scope={scope}, category={category!r}, "
        f"method={method!r} after region/state filters "
        f"(grid_region={grid_region!r}, state={state!r})"
    )
