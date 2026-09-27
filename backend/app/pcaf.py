"""PCAF financed emissions (Partnership for Carbon Accounting Financials).

Implements the public PCAF Global GHG Standard attribution method:
financed emissions = attribution factor x borrower emissions, with
asset-class data-quality scores 1 (best) to 5 (lowest). Scores here follow
the PCAF hierarchy: verified company data (1), unverified reported (2),
physical-activity estimates (3), economic-activity estimates (4-5).
"""

from __future__ import annotations

from typing import Any

ASSET_CLASSES = (
    "listed_equity",
    "corporate_loans",
    "project_finance",
    "commercial_real_estate",
    "mortgages",
    "motor_loans",
    "sovereign_debt",
)

# Default DQ when the caller does not justify better data.
DEFAULT_DQ: dict[str, int] = {
    "listed_equity": 2,
    "corporate_loans": 3,
    "project_finance": 3,
    "commercial_real_estate": 4,
    "mortgages": 4,
    "motor_loans": 5,
    "sovereign_debt": 2,
}


def attribution_factor(
    outstanding: float,
    denominator: float,
    asset_class: str,
) -> float:
    """Outstanding / EVIC (or project cost / property value / GDP proxy).

    ``denominator`` semantics per asset class: EVIC for listed equity and
    corporate loans, total project cost for project finance, property value
    at origination for mortgages/CRE/motor, GDP for sovereign debt.
    """
    if asset_class not in ASSET_CLASSES:
        raise ValueError(f"unknown asset class {asset_class!r}; choices: {ASSET_CLASSES}")
    if outstanding < 0 or denominator <= 0:
        raise ValueError("outstanding must be >= 0 and denominator must be > 0")
    return outstanding / denominator


def financed_line(
    asset_class: str,
    outstanding: float,
    denominator: float,
    borrower_emissions_tco2e: float,
    data_quality: int | None = None,
) -> dict[str, Any]:
    """One PCAF line: attribution, financed emissions, DQ score."""
    if borrower_emissions_tco2e < 0:
        raise ValueError("borrower emissions must be >= 0")
    if data_quality is not None and data_quality not in (1, 2, 3, 4, 5):
        raise ValueError("data_quality must be 1-5")
    factor = attribution_factor(outstanding, denominator, asset_class)
    dq = data_quality if data_quality is not None else DEFAULT_DQ[asset_class]
    return {
        "asset_class": asset_class,
        "outstanding": outstanding,
        "denominator": denominator,
        "attribution_factor": round(factor, 6),
        "borrower_emissions_tco2e": borrower_emissions_tco2e,
        "financed_emissions_tco2e": round(factor * borrower_emissions_tco2e, 2),
        "data_quality": dq,
    }


def financed_portfolio(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate a portfolio; DQ score is financed-emissions-weighted."""
    computed = [
        financed_line(
            ln["asset_class"], float(ln["outstanding"]), float(ln["denominator"]),
            float(ln["borrower_emissions_tco2e"]), ln.get("data_quality"),
        )
        for ln in (lines or [])
    ]
    total_financed = round(sum(c["financed_emissions_tco2e"] for c in computed), 2)
    total_outstanding = round(sum(c["outstanding"] for c in computed), 2)
    if total_financed > 0:
        weighted_dq = round(
            sum(c["financed_emissions_tco2e"] * c["data_quality"] for c in computed) / total_financed, 2
        )
    else:
        weighted_dq = 0.0
    by_class: dict[str, dict[str, float]] = {}
    for c in computed:
        slot = by_class.setdefault(c["asset_class"], {"financed_emissions_tco2e": 0.0, "outstanding": 0.0})
        slot["financed_emissions_tco2e"] = round(slot["financed_emissions_tco2e"] + c["financed_emissions_tco2e"], 2)
        slot["outstanding"] = round(slot["outstanding"] + c["outstanding"], 2)
    return {
        "lines": computed,
        "total_financed_emissions_tco2e": total_financed,
        "total_outstanding": total_outstanding,
        "weighted_data_quality": weighted_dq,
        "by_asset_class": by_class,
        "method": "PCAF Global GHG Standard attribution (outstanding/denominator x borrower emissions)",
    }
