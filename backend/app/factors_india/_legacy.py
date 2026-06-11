"""
Back-compat shim — rebuilds the legacy module-level dicts that
``app.carbon_calculator`` used to define inline, from the new JSON-backed
factor registry.

The legacy dicts are imported (and re-exported) by ``app.carbon_calculator``
and from there by ``app.router_platform``. Preserving these names means
slice 1 lands without forcing any caller to change imports or response
shapes.

Only Scope-2 electricity is registry-backed today; the other dicts
(STATIONARY_COMBUSTION_FACTORS, MOBILE_COMBUSTION_FACTORS, SCOPE_3_FACTORS,
REFRIGERANT_GWP, STEAM_EMISSION_FACTORS, PAT_SECTOR_BENCHMARKS) stay as
literals in ``carbon_calculator.py`` until their respective future slices
land.
"""

from __future__ import annotations

from app.factors_india import FactorNotFound, get_india_factor

# Slice 1: only CEA v20 is loaded (vintage = FY2024-25). Historical FY keys
# (FY2018-19 → FY2023-24) that the previous literal dict carried were never
# sourced — all pinned to v19's 0.716 with one-off tweaks — so they are
# dropped here. If a real caller turns out to need them, the test suite
# will surface it and slice 1.5 can backfill from a v19 companion JSON.
try:
    _national = get_india_factor(
        scope=2,
        category="electricity_purchased",
        method="location_based",
    )
    _NATIONAL_VALUE = _national.value
except FactorNotFound:  # pragma: no cover — registry empty in tests with no data
    _NATIONAL_VALUE = 0.716  # last-resort fallback so imports never explode

# Keyed by the same FY strings the previous literal used so any caller that
# does ``CEA_GRID_EMISSION_FACTORS.get(fy, ...)`` keeps working.
CEA_GRID_EMISSION_FACTORS: dict[str, float] = {
    "FY2024-25": _NATIONAL_VALUE,
    "default": _NATIONAL_VALUE,
}

# Slice 1 has no SLDC overrides; only the national fallback is exposed. The
# previous hard-coded state floats (karnataka/maharashtra/etc.) were not
# sourced from SLDC publications, so dropping them removes fake precision.
# Slice 2 will repopulate this dict from real MSLDC / TNSLDC / GSLDC data.
STATE_GRID_FACTORS: dict[str, float] = {
    "national": _NATIONAL_VALUE,
}
