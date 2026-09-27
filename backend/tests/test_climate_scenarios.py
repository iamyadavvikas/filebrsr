"""Climate scenario engine + SBTi target tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app import climate_scenarios as cs


@pytest.fixture
def client():
    from app.main import app

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def test_three_named_scenarios_all_flagged_defaults():
    scen = cs.list_scenarios()
    assert {s["key"] for s in scen} == {"net_zero_2050", "delayed_transition", "current_policies"}
    assert all(s["is_default"] for s in scen)
    # Orderly < disorderly < hot-house pricing in 2030.
    prices = {s["key"]: s["carbon_price_usd_per_tco2e"][2030] for s in scen}
    assert prices["current_policies"] < prices["delayed_transition"] < prices["net_zero_2050"]


def test_unknown_scenario_rejected():
    with pytest.raises(ValueError):
        cs.resolve_scenario("mad_max")


def test_transition_exposure_math_and_bands():
    # 10,000 tCO2e x $90 (NZE 2030 default) = $900k.
    out = cs.transition_exposure(10_000, 100_000_000, 2030, "net_zero_2050")
    assert out["carbon_cost_usd"] == 900_000
    assert out["cost_to_revenue_pct"] == 0.9
    assert out["band"] == "low"
    assert out["assumptions"]["uses_defaults"] is True
    severe = cs.transition_exposure(1_000_000, 100_000_000, 2050, "net_zero_2050")
    assert severe["band"] == "severe"
    with pytest.raises(ValueError):
        cs.transition_exposure(100, 0, 2030)


def test_custom_scenario_clears_defaults_flag():
    custom = {"key": "mine", "name": "Mine",
              "carbon_price_usd_per_tco2e": {2030: 50, 2035: 60, 2040: 70, 2050: 80}}
    out = cs.transition_exposure(1_000, 10_000_000, 2030, custom)
    assert out["carbon_cost_usd"] == 50_000
    assert out["assumptions"]["uses_defaults"] is False
    with pytest.raises(ValueError):
        cs.transition_exposure(1_000, 10_000_000, 2030, {"key": "x", "carbon_price_usd_per_tco2e": {}})


def test_physical_screen_aggregation_and_validation():
    assets = [
        {"name": "Plant A", "value": 70, "hazards": {"flood": 4, "heat": 2, "water_stress": 2, "cyclone": 1, "wildfire": 1}},
        {"name": "Plant B", "value": 30, "hazards": {"flood": 1, "heat": 2, "water_stress": 5, "cyclone": 1, "wildfire": 1}},
    ]
    out = cs.physical_screen(assets)
    assert out["assets"] == 2
    assert out["value_weighted_score"] == round((4 * 70 + 5 * 30) / 100, 2)
    assert out["high_exposure_value_share"] == 1.0
    assert out["by_asset"][0]["band"] == "high"
    with pytest.raises(ValueError):
        cs.physical_screen([{"name": "X", "hazards": {"aliens": 3}}])
    with pytest.raises(ValueError):
        cs.physical_screen([{"name": "X", "hazards": {"flood": 9}}])
    assert cs.physical_screen([])["assets"] == 0


def test_budget_alignment_and_overshoot():
    out = cs.budget_alignment(100_000, 90_000, 2020, 2025, 2050, remaining_budget_tco2e=1_000_000)
    assert out["budget_overshoot_year"] == 2025 + 11  # 1Mt / 90kt
    assert out["verdict"] == "misaligned"
    aligned = cs.budget_alignment(100_000, 90_000, 2020, 2025, 2050, remaining_budget_tco2e=90_000 * 30)
    assert aligned["verdict"] == "aligned"
    track = cs.budget_alignment(100_000, 50_000, 2020, 2025, 2050)
    assert track["on_track"] is True


def test_sbti_target_math():
    # 1.5C cross-sector: 4.2%/yr x 10y = 42% by 2030.
    t = cs.sbti_target(100_000, 2020, 2030, "1.5C", stated_target_pct=45.0)
    assert t["required_reduction_pct"] == 42.0
    assert t["target_emissions_tco2e"] == 58_000
    assert t["meets_sbti"] is True
    weak = cs.sbti_target(100_000, 2020, 2030, "1.5C", stated_target_pct=20.0)
    assert weak["meets_sbti"] is False
    with pytest.raises(ValueError):
        cs.sbti_target(100_000, 2020, 2030, "2C")


@pytest.mark.asyncio
async def test_climate_endpoints(client):
    resp = await client.get("/api/climate/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()["scenarios"]) == 3

    resp = await client.post("/api/climate/transition-exposure",
                             json={"emissions_tco2e": 10_000, "revenue": 100_000_000, "year": 2030})
    assert resp.status_code == 200
    assert resp.json()["carbon_cost_usd"] == 900_000

    resp = await client.post("/api/climate/sbti-target",
                             json={"base_emissions": 100_000, "base_year": 2020, "stated_target_pct": 50})
    assert resp.json()["meets_sbti"] is True

    resp = await client.post("/api/climate/resilience",
                             json={"emissions_tco2e": 10_000, "revenue": 100_000_000,
                                    "assets": [{"name": "HQ", "value": 10, "hazards": {"flood": 2}}]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["uses_defaults"] is True
    assert body["methodology_disclaimers"]

    resp = await client.post("/api/climate/transition-exposure",
                             json={"emissions_tco2e": 10_000, "revenue": 0, "year": 2030})
    assert resp.status_code == 422  # pydantic: revenue must be > 0
