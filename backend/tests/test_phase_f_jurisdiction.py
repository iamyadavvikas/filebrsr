"""
Phase F — jurisdiction-aware factor sets (India + Australia).

Acceptance:
- ``get_factor`` resolves CEA factors for IN and NGA placeholders for AU.
- The calculator engine computes Scope 2 with the AU grid factor.
- ``jurisdiction_frameworks`` maps datapoints to AASB S2 / NGER (AU) and
  BRSR Core / CCTS (IN).
- ``sign_result(..., jurisdiction=...)`` stamps the jurisdiction and resolved
  framework tags into the signed PROV-O graph (and still verifies).
- ``persist_calculation`` writes ``jurisdiction`` + ``framework_tags`` columns.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.calculator import scope2_location_based, sign_result
from app.calculator.provenance import persist_calculation
from app.factors_india import FactorNotFound, get_factor, get_india_factor, reset_cache
from app.jurisdiction_frameworks import (
    FrameworkNotFound,
    framework_tags,
    get_frameworks,
    list_datapoints,
)
from app.prov import verify_signed_provenance


@pytest.fixture(autouse=True)
def _fresh_factor_cache():
    reset_cache()
    yield
    reset_cache()


# ─── get_factor: jurisdiction routing ──────────────────────────────────────

def test_get_factor_au_state_returns_nga_placeholder():
    f = get_factor(
        jurisdiction="AU",
        scope=2,
        category="electricity_purchased",
        method="location_based",
        state="NSW",
    )
    assert f.jurisdiction == "AU"
    assert f.unit == "tCO2-e/MWh"
    assert f.is_placeholder is True
    assert "NGA" in f.source or "National Greenhouse" in f.source


def test_get_factor_au_national_fallback():
    f = get_factor(
        jurisdiction="AU",
        scope=2,
        category="electricity_purchased",
        method="location_based",
    )
    assert f.jurisdiction == "AU"
    assert f.regional_specificity == "national"


def test_get_factor_in_uses_cea():
    f = get_factor(
        jurisdiction="IN",
        scope=2,
        category="electricity_purchased",
        method="location_based",
        grid_region="WR",
    )
    assert f.jurisdiction == "IN"
    assert f.unit == "tCO2/MWh"


def test_get_india_factor_shim_equivalent_to_get_factor_in():
    a = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based"
    )
    b = get_factor(
        jurisdiction="IN",
        scope=2,
        category="electricity_purchased",
        method="location_based",
    )
    assert (a.value, a.unit, a.jurisdiction) == (b.value, b.unit, b.jurisdiction)


def test_get_factor_unsupported_jurisdiction_combo_raises():
    with pytest.raises(FactorNotFound, match="unsupported factor request"):
        get_factor(
            jurisdiction="AU",
            scope=1,
            category="electricity_purchased",
            method="location_based",
        )


def test_au_and_in_factors_are_isolated():
    """An AU lookup must never return an IN row and vice versa."""
    au = get_factor(
        jurisdiction="AU", scope=2, category="electricity_purchased",
        method="location_based",
    )
    inf = get_factor(
        jurisdiction="IN", scope=2, category="electricity_purchased",
        method="location_based",
    )
    assert au.source != inf.source
    assert au.unit != inf.unit  # tCO2-e/MWh vs tCO2/MWh


# ─── engine: Scope 2 with AU grid factor ───────────────────────────────────

def test_engine_scope2_au_state():
    r = scope2_location_based(150_000, jurisdiction="AU", state="NSW")
    # 150,000 kWh = 150 MWh × 0.68 tCO2-e/MWh = 102 tCO2e
    assert r.value == Decimal("102.000000")
    assert r.factor_id == "nga/nsw"
    assert r.factor_version == "NGA-2024-08"


def test_engine_scope2_in_grid_region_unchanged():
    r = scope2_location_based(150_000, jurisdiction="IN", grid_region="WR")
    assert r.factor_id == "cea/wr"
    assert r.factor_version == "CEA-2025-06"


def test_engine_scope2_default_jurisdiction_is_india():
    r = scope2_location_based(1000, grid_region="NR")
    assert r.factor_id.startswith("cea/")


# ─── jurisdiction_frameworks ───────────────────────────────────────────────

def test_framework_tags_au_scope2():
    tags = framework_tags("scope2_location_based", "AU")
    joined = " ".join(tags)
    assert "AASB S2" in joined
    assert "NGER" in joined


def test_framework_tags_in_scope2():
    tags = framework_tags("scope2_location_based", "IN")
    joined = " ".join(tags)
    assert "BRSR Core" in joined
    assert "CCTS" in joined


def test_get_frameworks_unknown_datapoint_raises():
    with pytest.raises(FrameworkNotFound):
        get_frameworks("nonexistent_datapoint", "AU")


def test_get_frameworks_unsupported_jurisdiction_raises():
    with pytest.raises(FrameworkNotFound):
        get_frameworks("scope2_location_based", "ZZ")


def test_list_datapoints_covers_all_scopes():
    dps = list_datapoints()
    assert "scope1_stationary_combustion" in dps
    assert "scope2_location_based" in dps
    assert "scope3_category" in dps


# ─── sign_result: jurisdiction + tags into the signed graph ────────────────

def test_sign_result_stamps_jurisdiction_and_tags_au():
    r = scope2_location_based(150_000, jurisdiction="AU", state="NSW")
    _, signed = sign_result(r, org_id="org-au", jurisdiction="AU")
    output = signed.graph["@graph"][0]
    assert output["fbrsr:jurisdiction"] == "AU"
    tags = output["fbrsr:frameworkTags"]
    assert any("AASB S2" in t for t in tags)
    assert verify_signed_provenance(signed) is True


def test_sign_result_without_jurisdiction_omits_tags():
    r = scope2_location_based(1000, grid_region="NR")
    _, signed = sign_result(r, org_id="org-x")
    output = signed.graph["@graph"][0]
    assert "fbrsr:jurisdiction" not in output
    assert "fbrsr:frameworkTags" not in output
    assert verify_signed_provenance(signed) is True


# ─── persist_calculation: jurisdiction + framework_tags columns ────────────

def test_persist_calculation_writes_jurisdiction_columns():
    r = scope2_location_based(150_000, jurisdiction="AU", state="NSW")
    _, signed = sign_result(r, org_id="org-au", jurisdiction="AU")

    captured: dict = {}
    sb = MagicMock()

    def _insert(row):
        # First insert is the calculations row.
        if "scope" in row and "jurisdiction" not in captured:
            captured.update(row)
        m = MagicMock()
        m.execute.return_value = MagicMock(data=[])
        return m

    sb.table.return_value.insert.side_effect = _insert

    ok = persist_calculation(
        sb,
        result=r,
        signed=signed,
        calculation_id="calc-au-1",
        org_id="org-au",
        user_id=None,
        jurisdiction="AU",
        framework_tags=framework_tags("scope2_location_based", "AU"),
    )
    assert ok is True
    assert captured["jurisdiction"] == "AU"
    assert any("AASB S2" in t for t in captured["framework_tags"])
