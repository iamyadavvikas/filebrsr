"""Tests for the canonical BRSR Core registry (brsr_core.py)."""

from __future__ import annotations

import pytest

from app.brsr_core import (
    ASSURANCE_PHASEIN,
    BRSC,
    DATAPOINT_TO_BRSC,
    NON_CORE_LEGACY_KPI_CODES,
    VALUE_CHAIN_ASSURANCE,
    assurance_mode_for,
    catalog_gaps,
    core_kpi_codes,
    get_attributes,
    get_core_kpis,
    kpi_required_mode,
    legacy_mismatches,
    tier_for_reporting_category,
)
from app.brsr_datapoints import BRSR_DATAPOINTS


def test_nine_attributes():
    attrs = get_attributes()
    assert len(attrs) == 9
    assert [a["sr"] for a in attrs] == [str(i) for i in range(1, 10)]
    names = [a["name"] for a in attrs]
    for expected in (
        "GHG footprint",
        "Water footprint",
        "Energy footprint",
        "Embracing circularity",
        "Enhancing employee wellbeing and safety",
        "Enabling gender diversity",
        "Enabling inclusive development",
        "Fairness in engaging with customers and suppliers",
        "Open-ness of business",
    ):
        assert any(expected in n for n in names)


def test_kpi_codes_unique_and_attribution():
    codes = core_kpi_codes()
    assert len(codes) == len(BRSC) == 43
    for k in BRSC:
        assert k["code"].startswith(f"BRSC-{k['attribute']}.")
        assert k["mandatory"] is True
        assert k["core"] is True


def test_cross_refs_resolve_to_catalog():
    catalog_ids = {d["id"] for d in BRSR_DATAPOINTS}
    for k in BRSC:
        for dp in k["cross_ref_datapoints"]:
            assert dp in catalog_ids, f"{k['code']} references unknown datapoint {dp}"


def test_ppp_intensity_flags():
    ppp = {k["code"] for k in BRSC if k["ppp_adjusted"]}
    # Exactly the revenue-intensity KPIs the annexure makes PPP-dependent.
    assert ppp == {
        "BRSC-1.3", "BRSC-2.2", "BRSC-3.3", "BRSC-4.10",
    }
    for code in ppp:
        k = next(k for k in BRSC if k["code"] == code)
        assert k["output_denominator"] is True
        assert k["data_type"] == "intensity"


def test_ghg_mass_balance_definition():
    s1 = next(k for k in BRSC if k["code"] == "BRSC-1.1")
    assert "carbon capture" in s1["measurement"]
    assert "fugitive" in s1["measurement"].lower()


def test_catalog_gaps_are_real():
    # Parameters the annexure names that must each be backed by a catalog
    # datapoint. BRSC-5.2 (permanent disabilities) and BRSC-9.3 (top-10 trading
    # houses) were the last two gaps — closed by C.P3.E.32 / C.P1.E.24.
    assert catalog_gaps() == []
    assert {"BRSC-5.2", "BRSC-9.3"} <= {k["code"] for k in BRSC}


def test_runtime_core_flags_match_canonical_registry():
    # The catalog's `core: True` flags are canonicalized at import time to the
    # DATAPOINT_TO_BRSC set — nothing outside the nine attributes may be Core.
    flagged = {d["id"] for d in BRSR_DATAPOINTS if d["core"]}
    assert flagged == set(DATAPOINT_TO_BRSC)
    assert len(flagged) >= 43
    # References count: every Core datapoint backs at least one BRSC KPI.
    assert len(DATAPOINT_TO_BRSC) >= len(BRSC)


def test_legacy_codes_not_core():
    legacy = legacy_mismatches()
    assert legacy == NON_CORE_LEGACY_KPI_CODES
    assert "gender_diversity_board_pct" in legacy
    assert "csr_spend_pct_of_pat" in legacy


def test_datapoint_inverse_map_consistent():
    for k in BRSC:
        for dp in k["cross_ref_datapoints"]:
            assert k["code"] in DATAPOINT_TO_BRSC[dp]


def test_assurance_phasein_monotonic():
    # Reasonable assurance reaches deeper tiers in later years.
    for tier in ("top_150", "top_250", "top_500", "top_1000"):
        assert tier in ASSURANCE_PHASEIN["reasonable"]
    assert ASSURANCE_PHASEIN["reasonable"]["top_150"] < ASSURANCE_PHASEIN["reasonable"]["top_1000"]


@pytest.mark.parametrize(
    ("tier", "fy", "expected"),
    [
        ("top_150", "FY2023-24", ""),        # outside universe
        ("top_150", "FY2024-25", "reasonable"),
        ("top_1000", "FY2024-25", "limited"),
        ("top_1000", "FY2027-28", "reasonable"),
    ],
)
def test_assurance_mode_for(tier, fy, expected):
    assert assurance_mode_for(tier, fy) == expected


def test_value_chain_surface_reference():
    # Top-250 value-chain surface per CIR 2023/122: reporting from FY24-25,
    # limited assurance FY25-26 (comply-or-explain). Informational only.
    assert VALUE_CHAIN_ASSURANCE["reporting"] == "FY2024-25"
    assert VALUE_CHAIN_ASSURANCE["limited"] == "FY2025-26"


def test_value_chain_kpi_subset():
    vc = get_core_kpis(value_chain_only=True)
    vc_codes = {k["code"] for k in vc}
    # All environmental flow-through KPIs are value-chain-reportable.
    assert {"BRSC-1.1", "BRSC-1.2", "BRSC-1.3", "BRSC-2.1", "BRSC-3.1", "BRSC-4.9"} <= vc_codes


def test_kpi_required_mode_gates_all_kpis_at_entity_level():
    vc = next(k for k in get_core_kpis() if k["value_chain_kpi"])
    plain = next(k for k in get_core_kpis() if not k["value_chain_kpi"])
    # Entity-level: value-chain KPIs are gated like all 43 KPIs (no deferral).
    # top_1000 outside the universe -> no obligation.
    assert kpi_required_mode(vc, "top_150", "FY2023-24") == ""
    assert kpi_required_mode(vc, "top_1000", "FY2024-25") == "limited"
    assert kpi_required_mode(vc, "top_150", "FY2027-28") == "reasonable"
    # in-scope KPIs follow the tier phase-in unchanged
    assert kpi_required_mode(plain, "top_1000", "FY2024-25") == "limited"
    assert kpi_required_mode(plain, "top_150", "FY2024-25") == "reasonable"


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("Top 150 (BRSR Core mandatory)", "top_150"),
        ("Top 250 (BRSR Core + Full)", "top_250"),
        ("Top 250 (BRSR Core mandatory from FY25)", "top_250"),
        ("Top 500 (BRSR Full)", "top_500"),
        ("Top 1000 (BRSR Full)", "top_1000"),
        ("Below Top 1000 (Voluntary)", None),
        ("SME", None),
        (None, None),
        ("", None),
    ],
)
def test_tier_for_reporting_category(category, expected):
    assert tier_for_reporting_category(category) == expected
