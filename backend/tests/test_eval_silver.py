"""Tests for app/eval_silver.py — silver-label builder."""

from __future__ import annotations

import pytest

from app.eval_silver import (
    SilverLabel,
    build_silver_labels,
    normalise_value,
    silver_summary,
)

# ─── normalise_value ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        (0, 0.0),
        (0.0, 0.0),
        (123, 123.0),
        (123.45, 123.45),
        ("123", 123.0),
        ("  123  ", 123.0),
        ("1,234,567", 1_234_567.0),
        ("1,00,00,000", 10_000_000.0),
        ("Rs. 1,000", 1000.0),
        ("INR 500", 500.0),
        ("₹100", 100.0),
        ("10 Cr", 10 * 1e7),
        ("10 crore", 10 * 1e7),
        ("5.5 Lakh", 5.5 * 1e5),
        ("2 Mn", 2 * 1e6),
        ("1.5 Billion", 1.5 * 1e9),
        ("3 thousand", 3000.0),
        ("yes", "yes"),
        ("Yes", "yes"),
        ("Acme Corp", "acme corp"),
        (True, True),
        (False, False),
    ],
)
def test_normalise_value(raw, expected):
    assert normalise_value(raw) == expected


def test_normalise_value_unknown_unit_falls_back_to_string():
    # "10 widgets" — we don't know "widgets" as a multiplier, so don't
    # silently drop the unit; compare as string.
    assert normalise_value("10 widgets") == "10 widgets"


def test_normalise_value_dict_stringifies():
    assert normalise_value({"a": 1}) == "{'a': 1}"


# ─── build_silver_labels — happy paths ───────────────────────────────────


def _sec(**kwargs):
    """Convenience: build a section dict with section_a defaulting to kwargs."""
    return {"section_a": kwargs, "section_b": {}, "section_c": {}}


def test_three_extractors_full_agreement():
    a = _sec(company_name="Acme")
    silver = build_silver_labels(regex=a, enhanced=a, ai=a)
    assert "section_a.company_name" in silver
    label = silver["section_a.company_name"]
    assert label.agreement == 3
    assert set(label.sources) == {"regex", "enhanced", "ai"}
    assert label.value == "Acme"
    assert label.normalised == "acme"


def test_two_of_three_agreement_becomes_silver():
    silver = build_silver_labels(
        regex=_sec(turnover="100 Cr"),
        enhanced=_sec(turnover="1,00,00,00,000"),  # same value, different format
        ai=_sec(turnover="200 Cr"),                 # outlier
    )
    label = silver["section_a.turnover"]
    assert label.agreement == 2
    assert set(label.sources) == {"regex", "enhanced"}
    assert label.normalised == pytest.approx(1e9)


def test_solo_extraction_not_silver():
    silver = build_silver_labels(
        regex=_sec(only_regex_has_this="42"),
        enhanced=_sec(),
        ai=_sec(),
    )
    assert silver == {}


def test_all_three_disagree_not_silver():
    silver = build_silver_labels(
        regex=_sec(employees="100"),
        enhanced=_sec(employees="200"),
        ai=_sec(employees="300"),
    )
    assert "section_a.employees" not in silver


def test_numeric_tolerance_treats_close_values_as_agreement():
    # 1% tolerance — two values within 1% should agree
    silver = build_silver_labels(
        regex=_sec(revenue="1000000"),
        enhanced=_sec(revenue="1005000"),  # 0.5% off
        ai=_sec(revenue="500000"),
    )
    label = silver["section_a.revenue"]
    assert label.agreement == 2
    assert set(label.sources) == {"regex", "enhanced"}


def test_numeric_tolerance_excludes_distant_values():
    silver = build_silver_labels(
        regex=_sec(revenue="1000000"),
        enhanced=_sec(revenue="1500000"),  # 50% off — not agreement
        ai=_sec(revenue="2000000"),
    )
    assert silver == {}


def test_zero_values_compare_correctly():
    """Zero is a meaningful value — must not be treated as 'missing'."""
    silver = build_silver_labels(
        regex=_sec(grievances="0"),
        enhanced=_sec(grievances="0"),
        ai=_sec(grievances="5"),
    )
    label = silver["section_a.grievances"]
    assert label.agreement == 2
    assert label.normalised == 0.0


def test_none_and_empty_treated_as_missing():
    """Don't count empty extractions toward agreement."""
    silver = build_silver_labels(
        regex=_sec(field_x=None),
        enhanced=_sec(field_x=""),
        ai=_sec(field_x="real value"),
    )
    assert silver == {}


# ─── build_silver_labels — mixed sections ────────────────────────────────


def test_multiple_sections():
    silver = build_silver_labels(
        regex={
            "section_a": {"company_name": "Acme"},
            "section_b": {"policy_count": "9"},
            "section_c": {"emissions": "100"},
        },
        enhanced={
            "section_a": {"company_name": "Acme"},
            "section_b": {"policy_count": "9"},
            "section_c": {"emissions": "200"},  # disagree
        },
        ai={
            "section_a": {},
            "section_b": {},
            "section_c": {"emissions": "100"},
        },
    )
    assert "section_a.company_name" in silver
    assert "section_b.policy_count" in silver
    assert "section_c.emissions" in silver
    # section_c emissions: regex(100) + ai(100) agree, enhanced(200) doesn't
    assert silver["section_c.emissions"].agreement == 2
    assert set(silver["section_c.emissions"].sources) == {"regex", "ai"}


def test_unknown_section_ignored():
    silver = build_silver_labels(
        regex={"section_z": {"x": "1"}},
        enhanced={"section_z": {"x": "1"}},
        ai={"section_z": {"x": "1"}},
    )
    assert silver == {}


def test_non_dict_section_tolerated():
    """Malformed extractor output mustn't crash the builder."""
    silver = build_silver_labels(
        regex={"section_a": "not a dict"},
        enhanced=_sec(x="1"),
        ai=_sec(x="1"),
    )
    assert "section_a.x" in silver


# ─── build_silver_labels — only-two extractors ───────────────────────────


def test_two_extractors_must_both_agree():
    """With only 2 extractors, both must agree (min_agreement=2)."""
    silver = build_silver_labels(
        regex=_sec(x="1"),
        enhanced=_sec(x="1"),
    )
    assert silver["section_a.x"].agreement == 2

    silver = build_silver_labels(
        regex=_sec(x="1"),
        enhanced=_sec(x="2"),
    )
    assert silver == {}


def test_one_extractor_yields_nothing():
    silver = build_silver_labels(regex=_sec(x="1"))
    assert silver == {}


def test_min_agreement_can_be_lowered():
    """Lowering min_agreement to 1 turns every field into silver."""
    silver = build_silver_labels(
        regex=_sec(x="1"),
        min_agreement=1,
    )
    assert silver["section_a.x"].agreement == 1


def test_min_agreement_validates():
    with pytest.raises(ValueError):
        build_silver_labels(regex=_sec(x="1"), min_agreement=0)


# ─── build_silver_labels — tie-breaking ──────────────────────────────────


def test_tie_breaks_in_extractor_priority_order():
    """Three extractors split 1-1-1 → no silver. But if two groups of two…
    can't happen with 3 votes. Test with explicit min_agreement=1 instead."""
    # With min_agreement=1 and 3 disagreeing extractors, the FIRST source
    # (regex, since it was passed first) wins via dict-insertion order.
    silver = build_silver_labels(
        regex=_sec(x="A"),
        enhanced=_sec(x="B"),
        ai=_sec(x="C"),
        min_agreement=1,
    )
    label = silver["section_a.x"]
    assert label.sources == ("regex",)
    assert label.value == "A"


# ─── Determinism ─────────────────────────────────────────────────────────


def test_output_is_sorted_by_key():
    silver = build_silver_labels(
        regex={
            "section_c": {"z": "1"},
            "section_a": {"a": "1"},
            "section_b": {"m": "1"},
        },
        enhanced={
            "section_c": {"z": "1"},
            "section_a": {"a": "1"},
            "section_b": {"m": "1"},
        },
    )
    keys = list(silver.keys())
    assert keys == sorted(keys)


def test_silver_label_is_frozen():
    label = SilverLabel(
        section="section_a", field_id="x", value="1",
        normalised=1.0, agreement=2, sources=("regex", "ai"),
    )
    with pytest.raises(Exception):
        label.value = "mutated"  # type: ignore[misc]


# ─── silver_summary ──────────────────────────────────────────────────────


def test_silver_summary_empty():
    assert silver_summary({}) == {
        "total": 0,
        "by_section": {"section_a": 0, "section_b": 0, "section_c": 0},
        "by_agreement": {},
    }


def test_silver_summary_counts_correctly():
    silver = build_silver_labels(
        regex={
            "section_a": {"a1": "1", "a2": "2"},
            "section_b": {"b1": "x"},
            "section_c": {},
        },
        enhanced={
            "section_a": {"a1": "1", "a2": "2"},
            "section_b": {"b1": "x"},
            "section_c": {},
        },
        ai={
            "section_a": {"a1": "1"},  # third vote on a1 only
            "section_b": {},
            "section_c": {},
        },
    )
    summary = silver_summary(silver)
    assert summary["total"] == 3
    assert summary["by_section"] == {
        "section_a": 2, "section_b": 1, "section_c": 0,
    }
    assert summary["by_agreement"] == {2: 2, 3: 1}
