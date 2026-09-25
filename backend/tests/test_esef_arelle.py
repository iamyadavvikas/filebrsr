"""Arelle conformance-authority wrapper tests.

``run_arelle_validation`` shells out to ``arelleCmdLine``; every branch that
touches the subprocess is unit-tested with a mocked ``subprocess.run`` so the
suite never requires Arelle on PATH. One opt-in integration test shells out to
the real binary when it is actually installed.
"""

from __future__ import annotations

import subprocess

import pytest

from app.esef_arelle import (
    apply_arelle,
    arelle_available,
    merge_arelle_into,
    run_arelle_validation,
)
from app.esrs_validate import ValidationResult


def build_statement(ids, in_scope_ids, values) -> bytes:
    from app.esrs_esef import build_esef_statement

    return build_esef_statement(
        financial_year="FY2025",
        org_id="org-test",
        org_name="Acme",
        entity_identifier="529900T8BM49AURSDO55",
        entries=[
            {
                "datapoint_id": i,
                "status": "reported",
                "value": v,
                "evidence": "",
                "notes": "",
            }
            for i, v in zip(ids, values)
        ],
        in_scope_ids=in_scope_ids,
        coverage_pct=80.0,
        assurance={"status": "limited", "firm": "B4", "date": "2026-03-15", "statement": "ok"},
    )


def _sample() -> bytes:
    ids = ["E1.E1-6.44", "ESRS2.GOV-1.21"]
    return build_statement(ids, ids, [2480.0, "Text"])


def _fake_proc(output: str):
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=output)


def test_merge_errors_block_submission():
    res = ValidationResult()
    merge_arelle_into(
        res,
        {
            "errors": [{"severity": "error", "code": "xbrl.4.6.3", "message": "missing precision/decimals"}],
            "warnings": [],
            "elapsed_ms": 120,
        },
    )
    assert not res.passed
    assert any(i.code == "xbrl.4.6.3" for i in res.issues)
    assert any(i.severity == "info" and i.code == "arelle" for i in res.issues)


def test_formula_warnings_are_advisory_not_blocking():
    res = ValidationResult()
    merge_arelle_into(
        res,
        {
            "errors": [],
            "warnings": [
                {
                    "severity": "warning",
                    "code": "message:ea_eu_tags_outside_MA_9",
                    "message": "No tag found for 'Revenue from coal'",
                }
            ],
            "elapsed_ms": 120,
        },
    )
    assert res.passed
    assert any(i.code == "message:ea_eu_tags_outside_MA_9" for i in res.issues)


def test_merge_deduplicates_existing_issues():
    res = ValidationResult()
    res.error("xbrl.4.6.3", "missing precision/decimals")
    merge_arelle_into(
        res,
        {"errors": [{"severity": "error", "code": "xbrl.4.6.3", "message": "missing precision/decimals"}], "warnings": []},
    )
    assert sum(1 for i in res.issues if i.code == "xbrl.4.6.3") == 1


def test_merge_clean_run_reports_all_clear():
    res = ValidationResult()
    merge_arelle_into(res, {"errors": [], "warnings": [], "elapsed_ms": 400})
    assert res.passed
    assert any(i.code == "arelle" and "no issues found" in i.message for i in res.issues)


def test_warnings_capped():
    res = ValidationResult()
    many = [{"severity": "warning", "code": f"w{i}", "message": f"m{i}"} for i in range(150)]
    merge_arelle_into(res, {"errors": [], "warnings": many})
    assert sum(1 for i in res.issues if i.severity == "warning") == 100


def test_apply_arelle_disabled_is_a_noop():
    res = ValidationResult()
    apply_arelle(res, _sample(), enabled=False)
    assert res.as_dict()["errors"] == []
    assert res.as_dict()["warnings"] == []


def test_apply_arelle_records_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.esef_arelle.run_arelle_validation", lambda *a, **k: None
    )
    res = ValidationResult()
    apply_arelle(res, _sample(), enabled=True)
    assert res.passed
    assert any(i.code == "arelle_unavailable" for i in res.issues)


def test_run_arelle_validation_parses_output(monkeypatch):
    monkeypatch.setattr("app.esef_arelle.arelle_available", lambda cmdline=True: True)
    out = (
        "INFO\txbrl.loader\tLoading taxonomy\n"
        "WARNING\tmessage:ea_eu_tags_outside_MA_2\tNo tag found for 'x'\n"
        "ERROR\txbrl.4.6.3\tmissing precision/decimals\n"
        "garbage line without tabs\n"
        "boss\tlines\tlike\tthis\n"
    )
    monkeypatch.setattr("app.esef_arelle.subprocess.run", lambda *a, **k: _fake_proc(out))
    parsed = run_arelle_validation(_sample(), timeout=5, cmdline="arelleCmdLine")
    assert parsed is not None
    assert parsed["available"] is True
    assert [e["code"] for e in parsed["errors"]] == ["xbrl.4.6.3"]
    assert len(parsed["warnings"]) == 1
    assert parsed["warnings"][0]["source"] == "arelle"
    assert parsed["elapsed_ms"] >= 0


def test_run_arelle_validation_missing_binary_returns_none():
    parsed = run_arelle_validation(_sample(), cmdline="definitely-not-arelle-cmd")
    assert parsed is None


def test_run_arelle_validation_timeout_returns_none(monkeypatch):
    monkeypatch.setattr("app.esef_arelle.arelle_available", lambda cmdline=True: True)

    def _slow(*a, **k):
        raise subprocess.TimeoutExpired(cmd="arelleCmdLine", timeout=1)

    monkeypatch.setattr("app.esef_arelle.subprocess.run", _slow)
    assert run_arelle_validation(_sample(), timeout=1) is None


@pytest.mark.skipif(not arelle_available(), reason="arelleCmdLine not installed")
def test_real_arelle_structurally_clean_file_has_zero_errors():
    ids = ["E1.E1-6.44", "ESRS2.BP-1.3"]
    content = build_statement(
        ids,
        ["E1.E1-6.44", "ESRS2.BP-1.3"],
        [2480, "Basis of preparation text"],
    )
    out = run_arelle_validation(content, timeout=300)
    assert out is not None
    assert out["errors"] == []
    assert out["warnings"]  # ESRS mandatory-tag completeness advisories remain visible
