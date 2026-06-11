"""Tests for the deterministic calculator (``app.calculator``).

Covers the charter's calculator acceptance: zero inputs, negative → raise,
unknown factor → FactorNotFoundError (never substituted), Decimal precision,
GWP-set selection, and a signed-provenance roundtrip for Scope 2.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.calculator import (
    FactorNotFoundError,
    scope1_stationary_combustion,
    scope2_location_based,
    scope3_category,
    sign_result,
)
from app.prov import reset_signer, verify_signed_provenance

# ─── Scope 2 (versioned CEA factor) ────────────────────────────────────────

def test_scope2_zero_returns_zero_with_factor():
    r = scope2_location_based(0)
    assert r.value == Decimal("0.000000")
    assert r.scope == 2
    assert r.factor_citation and "cea.nic.in" in r.factor_citation


def test_scope2_negative_raises():
    with pytest.raises(ValueError):
        scope2_location_based(-1)


def test_scope2_unknown_region_raises_factor_not_found():
    with pytest.raises(FactorNotFoundError):
        scope2_location_based(1000, grid_region="ZZ")


def test_scope2_value_is_mwh_times_factor():
    # CEA placeholder national factor is 0.716 tCO2/MWh; 1000 kWh = 1 MWh.
    r = scope2_location_based(1000)
    assert r.value == Decimal("0.716000")
    assert r.unit == "tCO2e"
    assert r.factor_id == "cea/national"


def test_scope2_regional_lookup():
    r = scope2_location_based(2000, grid_region="WR")
    assert r.factor_id == "cea/wr"
    assert r.value == Decimal("1.432000")  # 2 MWh * 0.716


# ─── Scope 1 (strict literal lookup, Decimal, GWP) ─────────────────────────

def test_scope1_unknown_fuel_raises():
    with pytest.raises(FactorNotFoundError):
        scope1_stationary_combustion("plutonium", 10)


def test_scope1_negative_raises():
    with pytest.raises(ValueError):
        scope1_stationary_combustion("coal", -5)


def test_scope1_coal_is_deterministic():
    r = scope1_stationary_combustion("coal", 100)
    # 100 * (2.4569 + 0.0001*28 + 0.00004*265) = 100 * 2.4703 = 247.03
    assert r.value == Decimal("247.030000")
    assert r.scope == 1


def test_scope1_ar6_differs_from_ar5():
    ar5 = scope1_stationary_combustion("coal", 100, gwp_set="AR5")
    ar6 = scope1_stationary_combustion("coal", 100, gwp_set="AR6")
    assert ar5.value != ar6.value


def test_scope1_unknown_gwp_set_raises():
    with pytest.raises(ValueError):
        scope1_stationary_combustion("coal", 10, gwp_set="AR99")


# ─── Scope 3 ───────────────────────────────────────────────────────────────

def test_scope3_unknown_category_raises():
    with pytest.raises(FactorNotFoundError):
        scope3_category("teleportation", 10)


def test_scope3_waste_landfill():
    r = scope3_category("waste_landfill", 10)
    assert r.value == Decimal("5.800000")  # 10 * 0.580
    assert r.scope == 3


# ─── Provenance integration ────────────────────────────────────────────────

def test_sign_result_roundtrip_verifies():
    reset_signer()
    r = scope2_location_based(1500, grid_region="SR", input_record_ids=["1", "2"])
    calc_id, signed = sign_result(r, org_id="org-1")
    assert calc_id
    assert verify_signed_provenance(signed) is True
    nodes = {n["@id"]: n for n in signed.graph["@graph"]}
    output = nodes[f"fbrsr:calculation/{calc_id}"]
    assert output["fbrsr:value"] == str(r.value)
    assert output["used"].startswith("fbrsr:factor/cea/sr@")


# ─── Property-based ────────────────────────────────────────────────────────

@given(kwh=st.integers(min_value=0, max_value=10_000_000))
def test_scope2_roundtrips_and_signs(kwh):
    reset_signer()
    r = scope2_location_based(kwh)
    expected = (Decimal(kwh) / Decimal("1000") * Decimal("0.716")).quantize(
        Decimal("0.000001")
    )
    assert r.value == expected
    _, signed = sign_result(r, org_id="org-x")
    assert verify_signed_provenance(signed) is True


@given(qty=st.integers(min_value=0, max_value=1_000_000))
def test_scope1_non_negative_never_raises(qty):
    r = scope1_stationary_combustion("diesel", qty)
    assert r.value >= 0
