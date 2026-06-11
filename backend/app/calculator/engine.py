"""
Deterministic Scope 1 / 2 / 3 emission calculations (pure Python, NO LLMs).

Principle #1: LLMs never compute numbers.
Principle #2: factors are sacred — a missing factor raises
:class:`FactorNotFoundError`; we never substitute a default.

Scope 2 location-based reads the **versioned CEA factor** from
:mod:`app.factors_india` (which itself raises on miss). Scope 1 / 3 currently
read the IPCC/DEFRA literal tables in :mod:`app.carbon_calculator` but with
strict lookup (no silent fallback) and Decimal arithmetic; these migrate into
``factors-india`` JSON slices over time with no signature change here.
"""

from __future__ import annotations

from decimal import Decimal

from app.calculator.results import (
    DEFAULT_GWP_SET,
    GWP_SETS,
    CalculationResult,
    FactorNotFoundError,
    quantize_emissions,
    require_non_negative,
    to_decimal,
)

# Literal Scope 1 / 3 tables (IPCC 2006 / DEFRA) — strict lookup only.
from app.carbon_calculator import (
    MOBILE_COMBUSTION_FACTORS,
    SCOPE_3_FACTORS,
    STATIONARY_COMBUSTION_FACTORS,
)
from app.factors_india import FactorNotFound, get_india_factor

# Valid CEA grid regions. An unknown region must NOT silently fall back to the
# national factor (principle #2: never substitute) — it raises instead.
_VALID_GRID_REGIONS = {"NR", "ER", "WR", "SR", "NER"}


def scope2_location_based(
    kwh,
    *,
    grid_region: str | None = None,
    state: str | None = None,
    reporting_period: tuple[str, str] | None = None,
    input_record_ids: list[str] | None = None,
    agent_run_id: str | None = None,
) -> CalculationResult:
    """Scope 2 location-based emissions from purchased electricity (kWh).

    Uses the versioned CEA factor (tCO2/MWh). Raises
    :class:`FactorNotFoundError` if no factor matches — never substitutes.
    """
    qty = require_non_negative(to_decimal(kwh, field_name="kwh"), field_name="kwh")
    if grid_region is not None and grid_region not in _VALID_GRID_REGIONS:
        raise FactorNotFoundError(
            f"Unknown grid_region '{grid_region}'; expected one of "
            f"{sorted(_VALID_GRID_REGIONS)} or None for national"
        )
    try:
        factor = get_india_factor(
            scope=2,
            category="electricity_purchased",
            method="location_based",
            grid_region=grid_region,
            state=state,
            reporting_period=reporting_period,
        )
    except FactorNotFound as exc:
        raise FactorNotFoundError(str(exc)) from exc

    # CEA factor is tCO2/MWh; inputs are kWh.
    mwh = qty / Decimal("1000")
    value = quantize_emissions(mwh * to_decimal(factor.value, field_name="factor"))
    region_key = (grid_region or state or "national").lower()

    return CalculationResult(
        scope=2,
        category="electricity_purchased",
        method="location_based",
        value=value,
        unit="tCO2e",
        factor_id=f"cea/{region_key}",
        factor_version=factor.version,
        factor_source=factor.source,
        factor_citation=factor.citation_url,
        input_record_ids=list(input_record_ids or []),
        uncertainty=factor.uncertainty,
        agent_run_id=agent_run_id,
    )


def scope1_stationary_combustion(
    fuel_type: str,
    quantity,
    *,
    gwp_set: str = DEFAULT_GWP_SET,
    input_record_ids: list[str] | None = None,
    agent_run_id: str | None = None,
) -> CalculationResult:
    """Scope 1 stationary/mobile combustion emissions in tCO2e."""
    factor = STATIONARY_COMBUSTION_FACTORS.get(fuel_type) or MOBILE_COMBUSTION_FACTORS.get(
        fuel_type
    )
    if factor is None:
        raise FactorNotFoundError(f"No Scope 1 combustion factor for fuel '{fuel_type}'")
    gwp = _gwp(gwp_set)

    qty = require_non_negative(to_decimal(quantity), field_name="quantity")
    co2 = qty * to_decimal(factor["co2"], field_name="co2_factor")
    ch4 = qty * to_decimal(factor["ch4"], field_name="ch4_factor") * gwp["CH4"]
    n2o = qty * to_decimal(factor["n2o"], field_name="n2o_factor") * gwp["N2O"]
    value = quantize_emissions(co2 + ch4 + n2o)

    return CalculationResult(
        scope=1,
        category=f"stationary_combustion:{fuel_type}",
        method="ipcc_tier1",
        value=value,
        unit="tCO2e",
        factor_id=f"ipcc-2006/combustion/{fuel_type}",
        factor_version=str(factor.get("source", "IPCC 2006")),
        factor_source=str(factor.get("source", "IPCC 2006")),
        input_record_ids=list(input_record_ids or []),
        uncertainty={"gwp_set": gwp_set},
        agent_run_id=agent_run_id,
    )


def scope3_category(
    category: str,
    quantity,
    *,
    input_record_ids: list[str] | None = None,
    agent_run_id: str | None = None,
) -> CalculationResult:
    """Scope 3 emissions for one category in tCO2e."""
    factor = SCOPE_3_FACTORS.get(category)
    if factor is None:
        raise FactorNotFoundError(f"No Scope 3 factor for category '{category}'")

    qty = require_non_negative(to_decimal(quantity), field_name="quantity")
    value = quantize_emissions(qty * to_decimal(factor["factor"], field_name="factor"))

    return CalculationResult(
        scope=3,
        category=category,
        method="spend_or_activity_based",
        value=value,
        unit="tCO2e",
        factor_id=f"scope3/{category}",
        factor_version=str(factor.get("source", "unknown")),
        factor_source=str(factor.get("source", "unknown")),
        input_record_ids=list(input_record_ids or []),
        agent_run_id=agent_run_id,
    )


def _gwp(gwp_set: str) -> dict[str, Decimal]:
    try:
        return GWP_SETS[gwp_set]
    except KeyError as exc:
        raise ValueError(
            f"Unknown GWP set '{gwp_set}'; choose from {sorted(GWP_SETS)}"
        ) from exc
