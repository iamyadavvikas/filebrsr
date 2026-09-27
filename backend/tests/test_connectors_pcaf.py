"""Utility-bill connector + PCAF financed emissions tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app import energy_bill, pcaf


@pytest.fixture
def client():
    from app.main import app

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


BILL = """
MAHARASHTRA STATE ELECTRICITY DISTRIBUTION CO. LTD.
Consumer No: 123456789012   Meter No: MH-AB-0042
Billing Period: 01-Jan-2025 to 31-Jan-2025
Previous Reading: 10200   Current Reading: 10445
Total Consumption : 245 kWh @ Rs 6.20/unit
Amount Payable: Rs 1,519.00
"""


def test_bill_parse_extracts_kwh_period_meter():
    parsed = energy_bill.parse_bill_text(BILL)
    assert parsed["kwh"] == 245.0
    assert parsed["unit"] == "kWh"
    assert parsed["period_start"] == "2025-01-01"
    assert parsed["period_end"] == "2025-01-31"
    assert parsed["meter_no"] == "MH-AB-0042"
    assert parsed["confidence"] == "high"


def test_bill_parse_empty_text_is_low_confidence():
    parsed = energy_bill.parse_bill_text("no readable content here")
    assert parsed["kwh"] is None
    assert parsed["confidence"] == "low"
    assert parsed["notes"]


def test_bill_to_scope2_uses_versioned_cea_factor():
    parsed = energy_bill.parse_bill_text(BILL)
    out = energy_bill.bill_to_scope2(parsed)
    assert out["emissions_tco2e"] > 0
    assert out["factor"]["id"]
    assert out["factor"]["version"]
    with pytest.raises(ValueError):
        energy_bill.bill_to_scope2({"kwh": None})


def test_pcaf_attribution_and_weighted_dq():
    line = pcaf.financed_line("corporate_loans", 10_000_000, 100_000_000, 50_000)
    assert line["attribution_factor"] == 0.1
    assert line["financed_emissions_tco2e"] == 5_000.0
    assert line["data_quality"] == 3  # default for corporate loans
    port = pcaf.financed_portfolio([
        {"asset_class": "corporate_loans", "outstanding": 10_000_000, "denominator": 100_000_000,
         "borrower_emissions_tco2e": 50_000, "data_quality": 2},
        {"asset_class": "mortgages", "outstanding": 5_000_000, "denominator": 10_000_000,
         "borrower_emissions_tco2e": 1_000},
    ])
    assert port["total_financed_emissions_tco2e"] == 5_000.0 + 500.0
    # (5000*2 + 500*4) / 5500 = 2.18
    assert port["weighted_data_quality"] == 2.18
    assert set(port["by_asset_class"]) == {"corporate_loans", "mortgages"}
    with pytest.raises(ValueError):
        pcaf.financed_line("spaceships", 1, 2, 3)
    with pytest.raises(ValueError):
        pcaf.financed_line("mortgages", 1, 0, 3)


@pytest.mark.asyncio
async def test_connector_endpoint_parses_and_prices(client):
    resp = await client.post(
        "/api/connectors/utility-bill",
        json={"text": BILL, "jurisdiction": "IN"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["parsed"]["kwh"] == 245.0
    assert body["scope2"]["emissions_tco2e"] > 0
    assert body["scope2"]["factor"]["id"]

    resp = await client.post(
        "/api/connectors/utility-bill",
        json={"text": "nothing parseable", "jurisdiction": "IN"},
    )
    assert resp.status_code == 200
    assert resp.json()["scope2"] is None


@pytest.mark.asyncio
async def test_pcaf_endpoints(client):
    resp = await client.get("/api/climate/pcaf/method")
    assert resp.status_code == 200
    assert "listed_equity" in resp.json()["asset_classes"]

    resp = await client.post(
        "/api/climate/pcaf",
        json={"lines": [
            {"asset_class": "listed_equity", "outstanding": 2_000_000, "denominator": 20_000_000,
             "borrower_emissions_tco2e": 100_000, "data_quality": 1},
        ]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_financed_emissions_tco2e"] == 10_000.0

    resp = await client.post(
        "/api/climate/pcaf",
        json={"lines": [{"asset_class": "nope", "outstanding": 1, "denominator": 2, "borrower_emissions_tco2e": 3}]},
    )
    assert resp.status_code == 400
