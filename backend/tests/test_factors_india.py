"""Tests for the factors-india slice 1 registry + public API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import carbon_calculator
from app.factors_india import (
    FactorNotFound,
    IndiaFactor,
    get_india_factor,
    reset_cache,
)
from app.factors_india._registry import (
    FACTORS_DIR,
    FactorFileError,
    _load_file,
    load_all_factors,
)


@pytest.fixture(autouse=True)
def _reset_registry_cache():
    """Make sure cross-test state doesn't leak through the lru_cache."""
    reset_cache()
    yield
    reset_cache()


# ─── Loader / validator ───────────────────────────────────────────────────


def test_factors_dir_exists():
    assert FACTORS_DIR.is_dir(), f"factors/ data dir missing at {FACTORS_DIR}"


def test_every_factor_file_validates():
    """Every shipped factors/*.json (except files starting with _) must
    pass the hand-rolled validator. This catches schema-drift PRs."""
    data_files = [
        p for p in FACTORS_DIR.rglob("*.json") if not p.name.startswith("_")
    ]
    assert data_files, "no factor data files found"
    for path in data_files:
        records = _load_file(path)
        assert records, f"{path} produced zero records"


def test_validator_rejects_missing_metadata(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"factors": []}))
    with pytest.raises(FactorFileError, match="missing 'metadata'"):
        _load_file(bad)


def test_validator_rejects_bad_scope(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({
        "metadata": {
            "source": "x", "version": "v1",
            "vintage": ["2024-04-01", "2025-03-31"],
            "citation_url": "https://example.com",
            "published_on": "2025-06-01",
        },
        "factors": [{
            "scope": 99,  # invalid
            "category": "x", "method": "default", "unit": "tCO2",
            "regional_specificity": "national", "value": 1.0,
        }],
    }))
    with pytest.raises(FactorFileError, match="scope must be in"):
        _load_file(bad)


def test_validator_rejects_regional_without_grid_region(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({
        "metadata": {
            "source": "x", "version": "v1",
            "vintage": ["2024-04-01", "2025-03-31"],
            "citation_url": "https://example.com",
            "published_on": "2025-06-01",
        },
        "factors": [{
            "scope": 2, "category": "electricity_purchased",
            "method": "location_based", "unit": "tCO2/MWh",
            "regional_specificity": "regional",  # claims regional...
            "grid_region": None,                   # ...but no region
            "value": 0.7,
        }],
    }))
    with pytest.raises(FactorFileError, match="requires non-null grid_region"):
        _load_file(bad)


def test_load_all_factors_is_cached():
    first = load_all_factors()
    second = load_all_factors()
    assert first is second  # tuple identity confirms cache hit


# ─── get_india_factor — happy paths ───────────────────────────────────────


def test_get_factor_national_default():
    f = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based",
    )
    assert isinstance(f, IndiaFactor)
    assert f.regional_specificity == "national"
    assert f.version == "CEA-2025-06"
    assert f.unit == "tCO2/MWh"
    assert f.value > 0
    assert f.citation_url.startswith("https://cea.nic.in")


def test_get_factor_regional_wr():
    f = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based",
        grid_region="WR",
    )
    assert f.regional_specificity == "regional"
    assert f.version == "CEA-2025-06"


@pytest.mark.parametrize("region", ["NR", "ER", "WR", "SR", "NER"])
def test_get_factor_all_grid_regions(region: str):
    f = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based",
        grid_region=region,
    )
    assert f.regional_specificity == "regional"


def test_state_unknown_falls_through_to_grid_region():
    """Slice 1 has no state rows — passing state= should fall through to
    the grid-region row when both are supplied."""
    f = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based",
        grid_region="WR", state="MH",
    )
    assert f.regional_specificity == "regional"


def test_state_only_falls_through_to_national():
    f = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based",
        state="MH",
    )
    assert f.regional_specificity == "national"


# ─── get_india_factor — error paths ───────────────────────────────────────


def test_unknown_scope_raises():
    with pytest.raises(FactorNotFound, match="slice 1 does not support"):
        get_india_factor(
            scope=1, category="electricity_purchased", method="location_based",
        )


def test_unknown_method_raises():
    with pytest.raises(FactorNotFound, match="slice 1 does not support"):
        get_india_factor(
            scope=2, category="electricity_purchased", method="market_based",
        )


def test_reporting_period_outside_vintage_raises():
    with pytest.raises(FactorNotFound, match="no loaded edition covers"):
        get_india_factor(
            scope=2, category="electricity_purchased", method="location_based",
            reporting_period=("2018-04-01", "2019-03-31"),
        )


def test_reporting_period_inside_vintage_ok():
    f = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based",
        reporting_period=("2024-04-01", "2025-03-31"),
    )
    assert f.version == "CEA-2025-06"


# ─── Back-compat shim ─────────────────────────────────────────────────────


def test_legacy_shim_matches_registry():
    expected = get_india_factor(
        scope=2, category="electricity_purchased", method="location_based",
    ).value
    assert carbon_calculator.CEA_GRID_EMISSION_FACTORS["default"] == expected
    assert carbon_calculator.CEA_GRID_EMISSION_FACTORS["FY2024-25"] == expected
    assert carbon_calculator.STATE_GRID_FACTORS["national"] == expected


def test_calculate_scope2_unchanged_shape():
    """Public function signature + return shape must not regress."""
    result = carbon_calculator.calculate_scope2_emissions(1000)
    assert set(result.keys()) == {
        "electricity_mwh",
        "grid_emission_factor",
        "state_factor",
        "total_tco2e",
        "source",
        "method",
    }
    assert result["electricity_mwh"] == 1000
    assert result["method"] == "location_based"
    assert result["total_tco2e"] == round(1000 * result["grid_emission_factor"], 4)


def test_calculate_scope2_unknown_fy_falls_back_to_default():
    """Historical FY keys were dropped in slice 1; unknown FY must use the
    'default' key without crashing — matching old behaviour."""
    result = carbon_calculator.calculate_scope2_emissions(500, fy="FY2018-19")
    assert result["grid_emission_factor"] == carbon_calculator.CEA_GRID_EMISSION_FACTORS["default"]


def test_calculate_scope2_unknown_state_falls_back_to_national():
    result = carbon_calculator.calculate_scope2_emissions(500, state="karnataka")
    assert result["state_factor"] == carbon_calculator.STATE_GRID_FACTORS["national"]


# ─── Visible-debt guard ───────────────────────────────────────────────────


@pytest.mark.xfail(
    reason="CEA v20 placeholders pending real values from CEA June 2025 PDF; "
           "this test flips to pass automatically once _placeholder=true rows "
           "are replaced with verified numbers.",
    strict=True,
)
def test_no_placeholder_values_remain():
    """When this test passes (xpass), the CI run will FAIL because of
    strict=True — that forces us to remove the xfail marker (and the debt)
    in the same PR that lands the real numbers."""
    records = load_all_factors()
    placeholders = [r for r in records if r.is_placeholder]
    assert not placeholders, (
        f"{len(placeholders)} placeholder factor(s) still loaded: "
        f"{[(r.version, r.grid_region, r.state) for r in placeholders]}"
    )
