"""Tests for the BRSR Core value-chain partner module (brsr_value_chain.py)."""

from __future__ import annotations

import pytest

from app.brsr_value_chain import (
    COVERAGE_CAP_PCT,
    DIRECTIONS,
    PARTNER_THRESHOLD_PCT,
    coverage_status,
    cumulative_coverage,
    disclosed_coverage,
    in_scope_partner,
    partner_report,
    validate_direction,
    value_chain_kpi_codes,
    value_chain_kpis,
)


def test_threshold_constants():
    assert PARTNER_THRESHOLD_PCT == 2.0
    assert COVERAGE_CAP_PCT == 75.0
    assert DIRECTIONS == ("upstream", "downstream")


def test_validate_direction():
    assert validate_direction("upstream") == "upstream"
    assert validate_direction("downstream") == "downstream"
    with pytest.raises(ValueError):
        validate_direction("lateral")


def test_in_scope_partner_threshold():
    assert in_scope_partner(purchases_pct=2) is True
    assert in_scope_partner(purchases_pct=1.9, sales_pct=0) is False
    assert in_scope_partner(purchases_pct=0, sales_pct=5) is True
    assert in_scope_partner(None, None) is False
    with pytest.raises(ValueError):
        in_scope_partner(purchases_pct=101)
    with pytest.raises(ValueError):
        in_scope_partner(purchases_pct="lots")


def test_cumulative_coverage_uses_direction_basis():
    partners = [
        {"purchases_pct": 30, "sales_pct": 0},
        {"purchases_pct": 4, "sales_pct": 0},
        {"purchases_pct": 1.5, "sales_pct": 0},  # below threshold
        {"purchases_pct": 0, "sales_pct": 20},
    ]
    assert cumulative_coverage(partners, "upstream") == 34.0
    assert cumulative_coverage(partners, "downstream") == 20.0


def test_cumulative_coverage_caps_at_75():
    partners = [
        {"purchases_pct": 40},
        {"purchases_pct": 40},
        {"purchases_pct": 40},
    ]
    assert cumulative_coverage(partners, "upstream") == 75.0


def test_coverage_status_reports_disclosed_and_pending():
    partners = [
        {"purchases_pct": 30, "disclosed": True},
        {"purchases_pct": 25, "disclosed": False},
        {"purchases_pct": 1, "disclosed": True},  # out of scope
    ]
    status = coverage_status(partners)
    up = status["upstream"]
    assert up["in_scope_partners"] == 2
    assert up["cumulative_pct"] == 55.0
    assert up["disclosed_pct"] == 30.0
    assert up["shortfall_to_cap_pct"] == 45.0
    assert up["disclosures_required"] is True
    assert up["pending_partners"] == 1
    assert status["downstream"]["in_scope_partners"] == 0


def test_disclosed_coverage_respects_disclosed_flag():
    partners = [
        {"sales_pct": 50, "disclosed": True},
        {"sales_pct": 30, "disclosed": False},
    ]
    assert disclosed_coverage(partners, "downstream") == 50.0


def test_value_chain_kpis_match_core_catalog():
    kpis = value_chain_kpis()
    codes = value_chain_kpi_codes()
    assert len(kpis) >= 20
    assert all(k["value_chain_kpi"] for k in kpis)
    assert {"BRSC-1.1", "BRSC-2.1", "BRSC-3.1"} <= codes
    assert all(k["code"].startswith("BRSC-") for k in kpis)


def test_partner_report_scope_and_attribution():
    partner = {"purchases_pct": 10, "sales_pct": 0, "direction": "upstream",
               "disclosed": True}
    report = partner_report(partner)
    assert report["in_scope"] is True
    assert report["direction"] == "upstream"
    assert report["purchases_pct"] == 10.0

    attributed = {k["code"]: "reasonable" for k in value_chain_kpis()[:5]}
    attributed_report = partner_report(partner, attributed)
    assert attributed_report["kpis_assured"] == 5
    assert attributed_report["kpis_total"] == len(value_chain_kpis())
    assert attributed_report["kpis"][0]["state"] == "reasonable"

    below = partner_report({"purchases_pct": 1, "sales_pct": 0})
    assert below["in_scope"] is False