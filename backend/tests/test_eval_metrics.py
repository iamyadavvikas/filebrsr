"""Tests for app/eval_metrics.py — TP/FP/FN scoring and aggregation."""

from __future__ import annotations

import math

from app.eval_metrics import (
    SectionStats,
    evaluate,
    merge_reports,
    most_extraneous_fields,
    worst_precision_fields,
    worst_recall_fields,
)
from app.eval_silver import SilverLabel


def _silver(items: list[tuple[str, str, str | float, str | float]]) -> dict[str, SilverLabel]:
    """Build a silver dict from (section, field, raw, normalised) tuples."""
    out = {}
    for sec, fid, raw, norm in items:
        out[f"{sec}.{fid}"] = SilverLabel(
            section=sec, field_id=fid, value=raw,
            normalised=norm, agreement=2, sources=("regex", "ai"),
        )
    return out


def _candidate(**sections):
    """Build a {section_a/b/c: {field: value}} dict; sections via kwargs."""
    base = {"section_a": {}, "section_b": {}, "section_c": {}}
    base.update({k: v for k, v in sections.items()})
    return base


# ─── SectionStats math ───────────────────────────────────────────────────


def test_section_stats_perfect_extractor():
    s = SectionStats("section_a", tp=10, fp=0, fn=0, silver_total=10)
    assert s.precision == 1.0
    assert s.recall == 1.0
    assert s.f1 == 1.0


def test_section_stats_zero_division_is_zero():
    s = SectionStats("section_a")
    assert s.precision == 0.0
    assert s.recall == 0.0
    assert s.f1 == 0.0


def test_section_stats_f1_formula():
    s = SectionStats("section_a", tp=8, fp=2, fn=2, silver_total=10)
    assert s.precision == 0.8
    assert s.recall == 0.8
    assert math.isclose(s.f1, 0.8)


def test_section_stats_asymmetric():
    # P=1.0, R=0.5 → F1 = 2*1*0.5 / 1.5 = 0.667
    s = SectionStats("section_a", tp=5, fp=0, fn=5, silver_total=10)
    assert s.precision == 1.0
    assert s.recall == 0.5
    assert math.isclose(s.f1, 2 / 3, abs_tol=1e-6)


# ─── evaluate() — happy path ─────────────────────────────────────────────


def test_perfect_extractor():
    silver = _silver([
        ("section_a", "name", "Acme", "acme"),
        ("section_a", "rev", "100", 100.0),
    ])
    cand = _candidate(section_a={"name": "Acme", "rev": "100"})
    rep = evaluate(candidate=cand, silver=silver, extractor_name="perfect")
    assert rep.overall.tp == 2
    assert rep.overall.fp == 0
    assert rep.overall.fn == 0
    assert rep.overall.extraneous == 0
    assert rep.overall.precision == 1.0
    assert rep.overall.recall == 1.0
    assert rep.overall.f1 == 1.0


def test_extractor_misses_half():
    silver = _silver([
        ("section_a", "f1", "x", "x"),
        ("section_a", "f2", "y", "y"),
        ("section_a", "f3", "z", "z"),
        ("section_a", "f4", "w", "w"),
    ])
    cand = _candidate(section_a={"f1": "x", "f2": "y"})
    rep = evaluate(candidate=cand, silver=silver)
    assert rep.overall.tp == 2
    assert rep.overall.fn == 2
    assert rep.overall.precision == 1.0
    assert rep.overall.recall == 0.5


def test_extractor_wrong_values_become_fp():
    silver = _silver([
        ("section_a", "rev", "100", 100.0),
        ("section_a", "emp", "50", 50.0),
    ])
    cand = _candidate(section_a={"rev": "200", "emp": "50"})
    rep = evaluate(candidate=cand, silver=silver)
    assert rep.overall.tp == 1
    assert rep.overall.fp == 1
    assert rep.overall.fn == 0


def test_extractor_extra_fields_are_extraneous_not_fp():
    """Fields the candidate has but silver doesn't shouldn't hurt precision."""
    silver = _silver([("section_a", "f1", "x", "x")])
    cand = _candidate(
        section_a={"f1": "x", "extra1": "1", "extra2": "2"},
    )
    rep = evaluate(candidate=cand, silver=silver)
    assert rep.overall.tp == 1
    assert rep.overall.fp == 0
    assert rep.overall.extraneous == 2
    assert rep.overall.precision == 1.0  # extraneous don't enter precision


def test_normalisation_applied_to_candidate():
    """Candidate raw value should be normalised the same way as silver."""
    silver = _silver([("section_a", "rev", "100 Cr", 100 * 1e7)])
    cand = _candidate(section_a={"rev": "1,00,00,00,000"})  # same value
    rep = evaluate(candidate=cand, silver=silver)
    assert rep.overall.tp == 1
    assert rep.overall.fp == 0


def test_numeric_tolerance_on_candidate():
    silver = _silver([("section_a", "rev", "100", 100.0)])
    cand = _candidate(section_a={"rev": "100.5"})  # 0.5% off
    rep = evaluate(candidate=cand, silver=silver)
    assert rep.overall.tp == 1


def test_zero_values_compared_correctly():
    silver = _silver([("section_a", "grievances", "0", 0.0)])
    cand = _candidate(section_a={"grievances": 0})
    rep = evaluate(candidate=cand, silver=silver)
    assert rep.overall.tp == 1


def test_empty_candidate_is_all_fn():
    silver = _silver([
        ("section_a", "f1", "x", "x"),
        ("section_b", "f2", "y", "y"),
    ])
    rep = evaluate(candidate={}, silver=silver)
    assert rep.overall.tp == 0
    assert rep.overall.fn == 2
    assert rep.overall.recall == 0.0


def test_empty_silver_yields_zero_metrics():
    cand = _candidate(section_a={"f1": "x"})
    rep = evaluate(candidate=cand, silver={})
    assert rep.overall.tp == 0
    assert rep.overall.silver_total == 0
    assert rep.overall.extraneous == 1
    assert rep.overall.precision == 0.0
    assert rep.overall.recall == 0.0


def test_malformed_candidate_does_not_crash():
    """A None section value mustn't break the comparison."""
    silver = _silver([("section_a", "f1", "x", "x")])
    rep = evaluate(candidate={"section_a": None}, silver=silver)
    assert rep.overall.fn == 1


# ─── evaluate() — per-section split ──────────────────────────────────────


def test_per_section_stats_split():
    silver = _silver([
        ("section_a", "a1", "1", 1.0),
        ("section_a", "a2", "1", 1.0),
        ("section_b", "b1", "1", 1.0),
        ("section_c", "c1", "1", 1.0),
    ])
    cand = _candidate(
        section_a={"a1": "1", "a2": "wrong"},
        section_b={"b1": "1"},
        # section_c missing entirely → fn
    )
    rep = evaluate(candidate=cand, silver=silver)
    assert rep.by_section["section_a"].tp == 1
    assert rep.by_section["section_a"].fp == 1
    assert rep.by_section["section_b"].tp == 1
    assert rep.by_section["section_c"].fn == 1
    assert rep.by_section["section_c"].recall == 0.0


# ─── per_field results ───────────────────────────────────────────────────


def test_per_field_includes_all_statuses():
    silver = _silver([
        ("section_a", "tp1", "x", "x"),
        ("section_a", "fp1", "y", "y"),
        ("section_a", "fn1", "z", "z"),
    ])
    cand = _candidate(section_a={
        "tp1": "x",       # match
        "fp1": "WRONG",   # mismatch
        # fn1 missing
        "extra": "extra value",
    })
    rep = evaluate(candidate=cand, silver=silver)
    statuses = {r.field_id: r.status for r in rep.per_field}
    assert statuses == {
        "tp1": "tp",
        "fp1": "fp",
        "fn1": "fn",
        "extra": "extraneous",
    }


def test_per_field_can_be_disabled():
    silver = _silver([("section_a", "f", "x", "x")])
    cand = _candidate(section_a={"f": "x"})
    rep = evaluate(candidate=cand, silver=silver, keep_per_field=False)
    assert rep.per_field == []
    assert rep.overall.tp == 1  # aggregates still computed


def test_per_field_is_sorted():
    silver = _silver([
        ("section_c", "z", "1", 1.0),
        ("section_a", "a", "1", 1.0),
        ("section_b", "m", "1", 1.0),
    ])
    cand = _candidate(
        section_a={"a": "1"},
        section_b={"m": "1"},
        section_c={"z": "1"},
    )
    rep = evaluate(candidate=cand, silver=silver)
    keys = [(r.section, r.field_id) for r in rep.per_field]
    assert keys == sorted(keys)


# ─── Diagnostic helpers ──────────────────────────────────────────────────


def test_worst_recall_returns_fns_only():
    silver = _silver([
        ("section_a", "a", "1", 1.0),
        ("section_a", "b", "1", 1.0),
        ("section_a", "c", "1", 1.0),
    ])
    cand = _candidate(section_a={"a": "1"})
    rep = evaluate(candidate=cand, silver=silver)
    misses = worst_recall_fields(rep)
    assert {m.field_id for m in misses} == {"b", "c"}
    assert all(m.status == "fn" for m in misses)


def test_worst_precision_returns_fps_only():
    silver = _silver([("section_a", "a", "1", 1.0)])
    cand = _candidate(section_a={"a": "wrong"})
    rep = evaluate(candidate=cand, silver=silver)
    fps = worst_precision_fields(rep)
    assert len(fps) == 1
    assert fps[0].status == "fp"


def test_most_extraneous_returns_extraneous_only():
    silver = _silver([("section_a", "a", "1", 1.0)])
    cand = _candidate(section_a={"a": "1", "x": "1", "y": "1"})
    rep = evaluate(candidate=cand, silver=silver)
    extras = most_extraneous_fields(rep)
    assert {e.field_id for e in extras} == {"x", "y"}


def test_limit_is_respected():
    silver = _silver([
        ("section_a", f"f{i}", "1", 1.0) for i in range(20)
    ])
    rep = evaluate(candidate={}, silver=silver)
    assert len(worst_recall_fields(rep, limit=5)) == 5


# ─── merge_reports ───────────────────────────────────────────────────────


def test_merge_empty_returns_zero_report():
    rep = merge_reports([])
    assert rep.overall.tp == 0
    assert rep.extractor_name == "empty"


def test_merge_sums_across_reports():
    silver = _silver([
        ("section_a", "a", "1", 1.0),
        ("section_a", "b", "1", 1.0),
    ])
    r1 = evaluate(
        candidate=_candidate(section_a={"a": "1", "b": "1"}),
        silver=silver,
        extractor_name="retrieval",
    )
    r2 = evaluate(
        candidate=_candidate(section_a={"a": "1"}),
        silver=silver,
        extractor_name="retrieval",
    )
    merged = merge_reports([r1, r2])
    assert merged.overall.tp == 3   # 2 + 1
    assert merged.overall.fn == 1   # 0 + 1
    assert merged.overall.silver_total == 4
    assert merged.extractor_name == "retrieval"
    # merged drops per_field (documented)
    assert merged.per_field == []


# ─── to_dict serialisation ───────────────────────────────────────────────


def test_to_dict_round_trip():
    silver = _silver([("section_a", "a", "1", 1.0)])
    cand = _candidate(section_a={"a": "1"})
    rep = evaluate(candidate=cand, silver=silver, extractor_name="x")
    d = rep.to_dict()
    assert d["extractor"] == "x"
    assert d["overall"]["tp"] == 1
    assert d["overall"]["precision"] == 1.0
    assert d["by_section"]["section_a"]["tp"] == 1
    assert d["per_field"][0]["status"] == "tp"


def test_to_dict_coerces_unserialisable_values():
    silver = _silver([("section_a", "a", "1", 1.0)])
    # Candidate has a non-jsonable value (a set)
    cand = {
        "section_a": {"a": "1", "weird": {"nested"}},
        "section_b": {},
        "section_c": {},
    }
    rep = evaluate(candidate=cand, silver=silver)
    d = rep.to_dict()
    import json
    # Should not raise
    json.dumps(d)


# ─── Field-result type ───────────────────────────────────────────────────


def test_eval_report_overall_section_is_overall():
    silver = _silver([("section_a", "a", "1", 1.0)])
    rep = evaluate(candidate={}, silver=silver)
    assert rep.overall.section == "overall"


def test_silver_label_section_drives_classification():
    """A silver label's section determines which per-section bucket it
    contributes to."""
    silver = {
        "custom.x": SilverLabel(
            section="section_b", field_id="x", value="1",
            normalised=1.0, agreement=2, sources=("a", "b"),
        ),
    }
    rep = evaluate(candidate={}, silver=silver)
    assert rep.by_section["section_b"].fn == 1
    assert rep.by_section["section_a"].fn == 0
