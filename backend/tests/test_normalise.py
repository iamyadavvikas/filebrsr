"""Tests for unit/number normalisation."""
from __future__ import annotations

import pytest

from app.normalise import Normalised, normalise_extracted, normalise_value


# ─── normalise_value: basics ───────────────────────────────────────


def test_none_returns_none():
    assert normalise_value(None) is None


def test_empty_string_returns_none():
    assert normalise_value("") is None
    assert normalise_value("   ") is None


def test_na_markers_return_none():
    for raw in ["N/A", "n/a", "NA", "Not Applicable", "Nil", "-"]:
        assert normalise_value(raw) is None, f"{raw!r} should not parse"


def test_pure_narrative_returns_none():
    assert normalise_value("Our policy is approved by the board") is None


def test_bool_is_rejected():
    # bool is an int subclass; we don't want True → 1.0
    assert normalise_value(True) is None
    assert normalise_value(False) is None


def test_plain_int_passes_through():
    n = normalise_value(1234)
    assert n is not None
    assert n.value == 1234.0
    assert n.unit == ""


def test_plain_float_passes_through():
    n = normalise_value(12.5)
    assert n is not None
    assert n.value == 12.5


# ─── Indian magnitudes ──────────────────────────────────────────────


@pytest.mark.parametrize("raw,expected", [
    ("1234 Cr", 1234 * 1e7),
    ("1,234 Crore", 1234 * 1e7),
    ("1234 crores", 1234 * 1e7),
    ("1234 Lakh", 1234 * 1e5),
    ("1234 Lakhs", 1234 * 1e5),
    ("1234 Lacs", 1234 * 1e5),
])
def test_indian_magnitudes(raw, expected):
    n = normalise_value(raw)
    assert n is not None
    assert n.value == expected


# ─── International magnitudes ──────────────────────────────────────


@pytest.mark.parametrize("raw,expected", [
    ("1234 Mn", 1234 * 1e6),
    ("1234 Million", 1234 * 1e6),
    ("12.5 Bn", 12.5 * 1e9),
    ("12.5 Billion", 12.5 * 1e9),
    ("500 Thousand", 500 * 1e3),
])
def test_international_magnitudes(raw, expected):
    n = normalise_value(raw)
    assert n is not None
    assert n.value == expected


# ─── Currency markers ──────────────────────────────────────────────


def test_inr_symbol():
    n = normalise_value("₹1,234")
    assert n is not None
    assert n.value == 1234
    assert n.unit == "INR"


def test_rs_prefix():
    n = normalise_value("Rs. 1,234 Cr")
    assert n is not None
    assert n.value == 1234 * 1e7
    assert n.unit == "INR"


def test_inr_word():
    n = normalise_value("INR 12.5 Mn")
    assert n is not None
    assert n.value == 12.5 * 1e6
    assert n.unit == "INR"


def test_usd_symbol():
    n = normalise_value("$1,234")
    assert n is not None
    assert n.unit == "USD"


# ─── Percentages ───────────────────────────────────────────────────


@pytest.mark.parametrize("raw,expected", [
    ("45%", 45.0),
    ("45 %", 45.0),
    ("45 pct", 45.0),
    ("45 percent", 45.0),
    ("45.5 percentage", 45.5),
])
def test_percent_variants(raw, expected):
    n = normalise_value(raw)
    assert n is not None
    assert n.value == expected
    assert n.unit == "%"


def test_field_suffix_pct_sets_unit_for_bare_number():
    n = normalise_value(45, field="renewable_energy_pct")
    assert n is not None
    assert n.unit == "%"


# ─── Negatives ─────────────────────────────────────────────────────


def test_leading_minus():
    n = normalise_value("-1234")
    assert n is not None
    assert n.value == -1234.0


def test_parenthesised_negative():
    n = normalise_value("(1,234 Cr)")
    assert n is not None
    assert n.value == -1234 * 1e7


# ─── Field-aware classification ────────────────────────────────────


def test_monetary_field_defaults_to_inr():
    # No explicit currency, but field is monetary → assume INR
    n = normalise_value("1234", field="turnover")
    assert n is not None
    assert n.unit == "INR"


def test_non_monetary_field_no_default_currency():
    n = normalise_value("1234", field="employees_permanent")
    assert n is not None
    assert n.unit == ""


# ─── Trailing unit token (energy/emissions) ────────────────────────


def test_trailing_unit_token():
    n = normalise_value("1234 GJ")
    assert n is not None
    assert n.value == 1234.0
    assert n.unit == "GJ"


def test_trailing_unit_kwh():
    n = normalise_value("567 kWh")
    assert n is not None
    assert n.unit == "kWh"


# ─── First-number-wins on multi-value cells ────────────────────────


def test_first_number_in_multi_value_cell():
    # Mimics LLM dumping both years; prompt asks for most-recent.
    n = normalise_value("FY24: 1234, FY23: 1100")
    assert n is not None
    assert n.value == 1234.0


# ─── normalise_extracted: dict walker ──────────────────────────────


def test_normalise_extracted_basic():
    merged = {
        "section_a": {
            "company_name": "Acme Ltd",
            "turnover": "₹1,234 Cr",
            "employees_permanent": "5000",
        },
        "section_b": {},
        "section_c": {
            "renewable_energy_pct": "45%",
            "ghg_scope1": "1234 tCO2e",
            "code_of_conduct": "Yes, see annexure",  # not parseable → omitted
        },
    }
    out = normalise_extracted(merged)
    assert out["section_a"]["turnover"]["value"] == 1234 * 1e7
    assert out["section_a"]["turnover"]["unit"] == "INR"
    assert out["section_a"]["turnover"]["raw"] == "₹1,234 Cr"
    assert out["section_a"]["employees_permanent"]["value"] == 5000.0
    assert "company_name" not in out["section_a"]  # narrative skipped
    assert "section_b" not in out  # empty section omitted
    assert out["section_c"]["renewable_energy_pct"]["unit"] == "%"
    assert out["section_c"]["ghg_scope1"]["unit"] == "tCO2e"
    assert "code_of_conduct" not in out["section_c"]


def test_normalise_extracted_handles_non_dict_sections():
    # Malformed input shouldn't crash.
    merged = {"section_a": {"turnover": "1000 Cr"}, "garbage": "not a dict"}
    out = normalise_extracted(merged)
    assert "section_a" in out
    assert "garbage" not in out
