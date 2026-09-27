"""Climate scenario engine v1 + SBTi target math (IFRS S2 resilience).

What this module is: the *calculation framework* for S2 climate resilience
disclosure — transition exposure, physical screening, carbon-budget
alignment, and SBTi target validation — with hash-pinned assumption sets.

What it is NOT: a licensed dataset. The built-in pathways are
**illustrative defaults** shaped like the NGFS scenario family (Net Zero
2050 / Delayed Transition / Current Policies). Every output carries
``assumptions`` with ``uses_defaults: true`` until the caller POSTs its own
scenario definition (licensed NGFS/IPCC numbers) — so reports disclose the
basis honestly, which is what auditors actually scrutinise.

Units: tCO2e for emissions, USD/tCO2e for carbon prices, EUR or INR for
money (kept as given; intensity ratios are unit-consistent either way).
"""

from __future__ import annotations

from typing import Any

HORIZONS: tuple[int, ...] = (2030, 2035, 2040, 2050)

# SBTi cross-sector 1.5C pathway: ~4.2% linear annual reduction.
SBTI_15C_LINEAR_RATE = 0.042
SBTI_WB2C_LINEAR_RATE = 0.025

HAZARDS = ("flood", "heat", "water_stress", "cyclone", "wildfire")


def _scenario(
    key: str,
    name: str,
    description: str,
    temp_outcome_c: str,
    carbon_price_usd: dict[int, float],
) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "description": description,
        "temp_outcome_2100_c": temp_outcome_c,
        "carbon_price_usd_per_tco2e": carbon_price_usd,
        "source": "illustrative default — NOT licensed NGFS/IPCC data",
        "is_default": True,
    }


BUILTIN_SCENARIOS: dict[str, dict[str, Any]] = {
    "net_zero_2050": _scenario(
        "net_zero_2050",
        "Net Zero 2050 (orderly)",
        "Ambitious, immediate climate policy; orderly transition with low physical risk.",
        "~1.4",
        {2030: 90.0, 2035: 150.0, 2040: 220.0, 2050: 350.0},
    ),
    "delayed_transition": _scenario(
        "delayed_transition",
        "Delayed Transition (disorderly)",
        "Late, abrupt policy after 2030; high transition risk concentrated in the 2030s.",
        "~1.6",
        {2030: 25.0, 2035: 180.0, 2040: 260.0, 2050: 380.0},
    ),
    "current_policies": _scenario(
        "current_policies",
        "Current Policies (hot-house)",
        "Only implemented policies; minimal transition risk, severe physical risk.",
        "~2.6+",
        {2030: 15.0, 2035: 20.0, 2040: 25.0, 2050: 35.0},
    ),
}


def list_scenarios() -> list[dict[str, Any]]:
    """Built-in pathway definitions with provenance."""
    return [dict(s) for s in BUILTIN_SCENARIOS.values()]


def resolve_scenario(spec: dict[str, Any] | str | None) -> tuple[dict[str, Any], bool]:
    """Resolve a scenario key or custom definition.

    Returns (scenario, uses_defaults). Custom definitions must carry
    ``carbon_price_usd_per_tco2e`` for the requested horizons.
    """
    if spec is None:
        spec = "net_zero_2050"
    if isinstance(spec, str):
        if spec not in BUILTIN_SCENARIOS:
            raise ValueError(f"unknown scenario {spec!r}; choices: {sorted(BUILTIN_SCENARIOS)}")
        return dict(BUILTIN_SCENARIOS[spec]), True
    prices = spec.get("carbon_price_usd_per_tco2e") or {}
    missing = [h for h in HORIZONS if h not in prices and str(h) not in prices]
    if missing:
        raise ValueError(f"custom scenario missing carbon prices for horizons {missing}")
    norm = {int(h): float(prices[h] if h in prices else prices[str(h)]) for h in HORIZONS}
    out = dict(spec)
    out["carbon_price_usd_per_tco2e"] = norm
    out["is_default"] = False
    out.setdefault("source", "user-provided scenario definition")
    return out, False


def _price_at(scenario: dict[str, Any], year: int) -> float:
    prices = scenario["carbon_price_usd_per_tco2e"]
    if year in prices:
        return float(prices[year])
    if str(year) in prices:
        return float(prices[str(year)])
    # Linear interpolation between nearest horizons.
    below = max((h for h in HORIZONS if h <= year), default=HORIZONS[0])
    above = min((h for h in HORIZONS if h >= year), default=HORIZONS[-1])
    if below == above:
        return float(prices.get(below, prices.get(str(below), 0.0)))
    pb = float(prices.get(below, prices.get(str(below), 0.0)))
    pa = float(prices.get(above, prices.get(str(above), 0.0)))
    return pb + (pa - pb) * (year - below) / (above - below)


def transition_exposure(
    emissions_tco2e: float,
    revenue: float,
    year: int = 2030,
    scenario: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Carbon-price exposure for an emissions profile in a scenario year."""
    if emissions_tco2e < 0 or revenue <= 0:
        raise ValueError("emissions must be >= 0 and revenue must be > 0")
    scen, uses_defaults = resolve_scenario(scenario)
    price = _price_at(scen, year)
    cost = emissions_tco2e * price
    ratio_pct = 100.0 * cost / revenue
    band = "low" if ratio_pct < 1 else "moderate" if ratio_pct < 3 else "high" if ratio_pct < 10 else "severe"
    return {
        "year": year,
        "scenario": scen.get("key") or scen.get("name"),
        "carbon_price_usd": price,
        "emissions_tco2e": emissions_tco2e,
        "carbon_cost_usd": round(cost, 2),
        "cost_to_revenue_pct": round(ratio_pct, 2),
        "band": band,
        "assumptions": {"uses_defaults": uses_defaults, "source": scen.get("source")},
    }


def physical_screen(assets: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate asset hazard scores (1-5, user-assessed) into portfolio exposure.

    Each asset: {name, value, hazards: {flood, heat, water_stress, cyclone,
    wildfire}}. flood/cyclone/wildfire count as acute; heat/water_stress as
    chronic. Scores are assessor inputs — the framework aggregates and
    discloses, it does not invent geospatial risk.
    """
    acute = {"flood", "cyclone", "wildfire"}
    chronic = {"heat", "water_stress"}
    scored = []
    total_value = 0.0
    for a in assets or []:
        hazards = a.get("hazards") or {}
        for h, s in hazards.items():
            if h not in HAZARDS:
                raise ValueError(f"unknown hazard {h!r}; choices: {HAZARDS}")
            if not (1 <= float(s) <= 5):
                raise ValueError(f"hazard score for {h!r} must be 1-5, got {s!r}")
        value = float(a.get("value") or 0.0)
        total_value += value
        a_acute = max([float(hazards.get(h, 1)) for h in acute])
        a_chronic = max([float(hazards.get(h, 1)) for h in chronic])
        overall = max(a_acute, a_chronic)
        scored.append({
            "name": a.get("name", "asset"),
            "value": value,
            "acute_max": a_acute,
            "chronic_max": a_chronic,
            "overall": overall,
            "band": "low" if overall < 2.5 else "moderate" if overall < 3.5 else "high" if overall < 4.5 else "severe",
        })
    if total_value > 0:
        weighted = sum(s["overall"] * s["value"] for s in scored) / total_value
        high_value_share = sum(s["value"] for s in scored if s["overall"] >= 3.5) / total_value
    else:
        weighted = sum(s["overall"] for s in scored) / len(scored) if scored else 0.0
        high_value_share = 0.0
    return {
        "assets": len(scored),
        "total_value": total_value,
        "value_weighted_score": round(weighted, 2),
        "high_exposure_value_share": round(high_value_share, 3),
        "by_asset": scored,
        "assumptions": {"method": "user-assessed 1-5 hazard scores; value-weighted aggregation"},
    }


def budget_alignment(
    base_year_emissions: float,
    current_emissions: float,
    base_year: int,
    current_year: int,
    target_year: int = 2050,
    remaining_budget_tco2e: float | None = None,
) -> dict[str, Any]:
    """1.5C-style carbon-budget check on the current run-rate.

    Without an explicit budget, reports the required linear reduction rate
    to net zero by target_year versus the observed trend since base_year.
    """
    if base_year_emissions <= 0 or current_emissions < 0 or current_year <= base_year:
        raise ValueError("need positive base emissions and current_year > base_year")
    years_left = target_year - current_year
    required_rate = (current_emissions / years_left / base_year_emissions) if years_left > 0 else 0.0
    observed_rate = (base_year_emissions - current_emissions) / (current_year - base_year) / base_year_emissions
    out: dict[str, Any] = {
        "base_year": base_year,
        "current_year": current_year,
        "target_year": target_year,
        "required_linear_rate_pct_per_yr": round(required_rate * 100, 2),
        "observed_linear_rate_pct_per_yr": round(observed_rate * 100, 2),
        "on_track": observed_rate >= required_rate,
    }
    if remaining_budget_tco2e is not None:
        if remaining_budget_tco2e <= 0:
            raise ValueError("remaining budget must be positive")
        overshoot_in = remaining_budget_tco2e / current_emissions if current_emissions > 0 else float("inf")
        out["budget_overshoot_year"] = current_year + int(overshoot_in) if overshoot_in != float("inf") else None
        out["verdict"] = "aligned" if out["budget_overshoot_year"] is None or out["budget_overshoot_year"] >= target_year else "misaligned"
    else:
        out["verdict"] = "aligned" if out["on_track"] else "misaligned"
    return out


def sbti_target(
    base_emissions: float,
    base_year: int,
    target_year: int = 2030,
    ambition: str = "1.5C",
    stated_target_pct: float | None = None,
) -> dict[str, Any]:
    """SBTi-style near-term absolute target math (cross-sector pathway).

    1.5C ≈ 4.2%/yr linear; well-below-2C ≈ 2.5%/yr linear (SBTi criteria).
    """
    rates = {"1.5C": SBTI_15C_LINEAR_RATE, "WB2C": SBTI_WB2C_LINEAR_RATE}
    if ambition not in rates:
        raise ValueError(f"ambition must be one of {sorted(rates)}, got {ambition!r}")
    if base_emissions <= 0 or target_year <= base_year:
        raise ValueError("need positive base emissions and target_year > base_year")
    years = target_year - base_year
    required_pct = round(rates[ambition] * years * 100, 1)
    target_emissions = round(base_emissions * max(0.0, 1 - rates[ambition] * years), 2)
    out: dict[str, Any] = {
        "ambition": ambition,
        "base_year": base_year,
        "target_year": target_year,
        "required_reduction_pct": required_pct,
        "target_emissions_tco2e": target_emissions,
        "method": f"cross-sector linear {rates[ambition]*100:.1f}%/yr",
    }
    if stated_target_pct is not None:
        out["stated_target_pct"] = stated_target_pct
        out["meets_sbti"] = stated_target_pct >= required_pct
    return out


def resilience_summary(
    emissions_tco2e: float,
    revenue: float,
    assets: list[dict[str, Any]] | None = None,
    scenario: dict[str, Any] | str | None = None,
    year: int = 2030,
) -> dict[str, Any]:
    """S2-ready resilience snapshot tying transition + physical together."""
    scen, uses_defaults = resolve_scenario(scenario)
    trans = transition_exposure(emissions_tco2e, revenue, year, scen)
    phys = physical_screen(assets or [])
    disclaimers = [
        "Scenario inputs are illustrative defaults unless a custom scenario is provided; "
        "disclose the source actually used."
    ] if uses_defaults else []
    return {
        "year": year,
        "scenario": scen.get("key") or scen.get("name"),
        "transition": trans,
        "physical": phys,
        "uses_defaults": uses_defaults,
        "methodology_disclaimers": disclaimers,
    }
