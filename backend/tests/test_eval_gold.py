"""Tests for app/eval_gold.py — user-correction → gold promotion."""

from __future__ import annotations

import pytest

from app.eval_gold import (
    DEFAULT_MIN_USERS,
    GoldLabel,
    build_gold_labels,
    gold_summary,
    merge_gold_into_silver,
)
from app.eval_silver import SilverLabel

# ─── Helpers ─────────────────────────────────────────────────────────────


def _row(section, field_path, corrected_value, user_id, **extra):
    return {
        "section": section,
        "field_path": field_path,
        "corrected_value": corrected_value,
        "user_id": user_id,
        **extra,
    }


def _rows_for_field(field, value, n_users, *, prefix="u"):
    """Generate n_users rows, each from a distinct user, all with same value."""
    return [_row("section_a", field, value, f"{prefix}{i}") for i in range(n_users)]


# ─── build_gold_labels ───────────────────────────────────────────────────


def test_promotion_requires_min_users():
    # 19 distinct users → no promotion (default threshold = 20)
    rows = _rows_for_field("turnover", "100 Cr", 19)
    assert build_gold_labels(rows) == {}


def test_promotion_at_exactly_min_users():
    rows = _rows_for_field("turnover", "100 Cr", 20)
    gold = build_gold_labels(rows)
    assert "section_a.turnover" in gold
    label = gold["section_a.turnover"]
    assert label.distinct_users == 20
    assert label.total_corrections == 20
    assert label.value == "100 Cr"


def test_promotion_lowered_threshold():
    rows = _rows_for_field("turnover", "100 Cr", 5)
    gold = build_gold_labels(rows, min_users=5)
    assert "section_a.turnover" in gold


def test_min_users_validates():
    with pytest.raises(ValueError):
        build_gold_labels([], min_users=0)


def test_same_user_repeated_does_not_count():
    """One user correcting 50 times is still 1 distinct user."""
    rows = [_row("section_a", "turnover", "100 Cr", "u1") for _ in range(50)]
    gold = build_gold_labels(rows, min_users=2)
    assert gold == {}  # only 1 distinct user


def test_normalisation_clusters_equivalent_values():
    """'100 Cr' and '1,00,00,00,000' and '1000000000' must cluster together."""
    rows = (
        [_row("section_a", "turnover", "100 Cr", f"u{i}") for i in range(7)]
        + [_row("section_a", "turnover", "1,00,00,00,000", f"u{i}") for i in range(7, 14)]
        + [_row("section_a", "turnover", "1000000000", f"u{i}") for i in range(14, 20)]
    )
    gold = build_gold_labels(rows)
    assert "section_a.turnover" in gold
    label = gold["section_a.turnover"]
    assert label.distinct_users == 20
    assert label.normalised == pytest.approx(1e9)


def test_disagreement_splits_into_clusters():
    """Two groups of users correcting to different values: largest wins."""
    rows = (
        _rows_for_field("turnover", "100 Cr", 22, prefix="g1_")
        + _rows_for_field("turnover", "200 Cr", 15, prefix="g2_")
    )
    gold = build_gold_labels(rows)
    # 22-user cluster wins
    assert gold["section_a.turnover"].distinct_users == 22
    assert "100" in gold["section_a.turnover"].value


def test_disagreement_neither_above_threshold():
    """If no cluster reaches min_users, no gold emitted even if total > threshold."""
    rows = (
        _rows_for_field("turnover", "100 Cr", 11, prefix="g1_")
        + _rows_for_field("turnover", "200 Cr", 11, prefix="g2_")
    )
    gold = build_gold_labels(rows)
    assert gold == {}


def test_tie_break_prefers_more_rows():
    """Two clusters with the same distinct-user count: pick the one with
    more total correction rows (proxy for 'more confident')."""
    # Cluster A: 5 users, 1 row each = 5 total
    cluster_a = _rows_for_field("x", "A", 5, prefix="a")
    # Cluster B: 5 users, but each makes 3 corrections = 15 total rows
    cluster_b = []
    for i in range(5):
        for _ in range(3):
            cluster_b.append(_row("section_a", "x", "B", f"b{i}"))
    gold = build_gold_labels(cluster_a + cluster_b, min_users=5)
    assert gold["section_a.x"].value == "B"
    assert gold["section_a.x"].total_corrections == 15


def test_numeric_tolerance_clusters_close_values():
    """1% tolerance: 1,000,000 and 1,005,000 are the same value."""
    rows = (
        [_row("section_a", "f", "1000000", f"u{i}") for i in range(10)]
        + [_row("section_a", "f", "1005000", f"u{i}") for i in range(10, 20)]
    )
    gold = build_gold_labels(rows)
    # Both clusters merge → 20 users, promoted
    assert gold["section_a.f"].distinct_users == 20


def test_multiple_fields_independent():
    rows = (
        _rows_for_field("turnover", "100 Cr", 25, prefix="t_")
        + _rows_for_field("employees", "500", 5, prefix="e_")
    )
    gold = build_gold_labels(rows)
    assert "section_a.turnover" in gold
    assert "section_a.employees" not in gold  # only 5 users


def test_multiple_sections():
    rows = (
        [_row("section_a", "f", "1", f"a{i}") for i in range(20)]
        + [_row("section_b", "f", "1", f"b{i}") for i in range(20)]
        + [_row("section_c", "f", "1", f"c{i}") for i in range(20)]
    )
    gold = build_gold_labels(rows)
    assert set(gold.keys()) == {"section_a.f", "section_b.f", "section_c.f"}


# ─── Defensive against malformed rows ────────────────────────────────────


def test_rows_missing_section_skipped():
    rows = [
        {"field_path": "x", "corrected_value": "1", "user_id": f"u{i}"}
        for i in range(25)
    ]
    assert build_gold_labels(rows) == {}


def test_rows_missing_field_path_skipped():
    rows = [
        {"section": "section_a", "corrected_value": "1", "user_id": f"u{i}"}
        for i in range(25)
    ]
    assert build_gold_labels(rows) == {}


def test_rows_missing_corrected_value_skipped():
    rows = [
        {"section": "section_a", "field_path": "x", "user_id": f"u{i}"}
        for i in range(25)
    ]
    assert build_gold_labels(rows) == {}


def test_rows_missing_user_id_skipped():
    rows = [
        {"section": "section_a", "field_path": "x", "corrected_value": "1"}
        for _ in range(25)
    ]
    assert build_gold_labels(rows) == {}


def test_mixed_valid_and_invalid_rows():
    """Bad rows shouldn't poison good ones."""
    rows = _rows_for_field("good", "1", 20) + [
        {"corrupt": "row"},
        {"section": "section_a", "field_path": "x"},  # missing value
    ]
    gold = build_gold_labels(rows)
    assert "section_a.good" in gold


def test_corrected_value_none_skipped():
    rows = [
        _row("section_a", "x", None, f"u{i}") for i in range(25)
    ] + _rows_for_field("y", "1", 20)
    gold = build_gold_labels(rows)
    assert "section_a.x" not in gold
    assert "section_a.y" in gold


# ─── Determinism ─────────────────────────────────────────────────────────


def test_output_sorted_by_key():
    rows = (
        _rows_for_field("zebra", "1", 20)
        + [_row("section_b", "alpha", "1", f"a{i}") for i in range(20)]
        + [_row("section_c", "middle", "1", f"m{i}") for i in range(20)]
    )
    gold = build_gold_labels(rows)
    assert list(gold.keys()) == sorted(gold.keys())


def test_gold_label_frozen():
    label = GoldLabel(
        section="section_a", field_id="x", value="1",
        normalised=1.0, distinct_users=20, total_corrections=20,
    )
    with pytest.raises(Exception):
        label.value = "mutated"  # type: ignore[misc]


# ─── merge_gold_into_silver ──────────────────────────────────────────────


def _silver_label(section, field_id, value, normalised):
    return SilverLabel(
        section=section, field_id=field_id, value=value,
        normalised=normalised, agreement=2, sources=("regex", "ai"),
    )


def test_merge_empty_inputs():
    assert merge_gold_into_silver({}, {}) == {}


def test_merge_gold_only():
    gold = {
        "section_a.x": GoldLabel(
            section="section_a", field_id="x", value="100",
            normalised=100.0, distinct_users=20, total_corrections=30,
        )
    }
    merged = merge_gold_into_silver({}, gold)
    assert merged["section_a.x"].value == "100"
    # Gold-derived silvers carry the sentinel agreement
    assert merged["section_a.x"].agreement == 999
    assert merged["section_a.x"].sources == ("gold",)


def test_merge_silver_only_passes_through():
    silver = {"section_a.x": _silver_label("section_a", "x", "1", 1.0)}
    merged = merge_gold_into_silver(silver, {})
    assert merged["section_a.x"].value == "1"
    assert merged["section_a.x"].agreement == 2  # original silver


def test_gold_overrides_silver_on_conflict():
    silver = {"section_a.x": _silver_label("section_a", "x", "wrong", "wrong")}
    gold = {
        "section_a.x": GoldLabel(
            section="section_a", field_id="x", value="right",
            normalised="right", distinct_users=25, total_corrections=25,
        )
    }
    merged = merge_gold_into_silver(silver, gold)
    assert merged["section_a.x"].value == "right"
    assert merged["section_a.x"].agreement == 999  # gold wins


def test_merge_does_not_mutate_inputs():
    silver = {"section_a.x": _silver_label("section_a", "x", "1", 1.0)}
    gold = {
        "section_a.y": GoldLabel(
            section="section_a", field_id="y", value="2",
            normalised=2.0, distinct_users=20, total_corrections=20,
        )
    }
    silver_before = dict(silver)
    gold_before = dict(gold)
    _ = merge_gold_into_silver(silver, gold)
    assert silver == silver_before
    assert gold == gold_before


def test_merge_output_sorted():
    silver = {
        "section_c.z": _silver_label("section_c", "z", "1", 1.0),
        "section_a.a": _silver_label("section_a", "a", "1", 1.0),
    }
    gold = {
        "section_b.m": GoldLabel(
            section="section_b", field_id="m", value="1",
            normalised=1.0, distinct_users=20, total_corrections=20,
        )
    }
    merged = merge_gold_into_silver(silver, gold)
    assert list(merged.keys()) == sorted(merged.keys())


# ─── gold_summary ────────────────────────────────────────────────────────


def test_gold_summary_empty():
    assert gold_summary({}) == {
        "total": 0, "by_section": {}, "min_users": 0, "max_users": 0,
    }


def test_gold_summary_counts():
    gold = {
        "section_a.x": GoldLabel(
            section="section_a", field_id="x", value="1",
            normalised=1.0, distinct_users=22, total_corrections=22,
        ),
        "section_a.y": GoldLabel(
            section="section_a", field_id="y", value="1",
            normalised=1.0, distinct_users=50, total_corrections=70,
        ),
        "section_b.z": GoldLabel(
            section="section_b", field_id="z", value="1",
            normalised=1.0, distinct_users=20, total_corrections=20,
        ),
    }
    summary = gold_summary(gold)
    assert summary == {
        "total": 3,
        "by_section": {"section_a": 2, "section_b": 1},
        "min_users": 20,
        "max_users": 50,
    }


def test_default_threshold_is_20():
    """Document the chosen default — changing it should require updating
    this test and the comment in eval_gold.py together."""
    assert DEFAULT_MIN_USERS == 20
