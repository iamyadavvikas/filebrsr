"""ESEF pre-flight validator unit tests (migration v26).

Covers the checks that gate submission: well-formedness, taxonomy version,
known concepts, context/unit resolution, decimals, duplicate facts, and the
assurance precondition. Mirrors the acceptance intent of the endpoint tests in
``test_csrd.py`` at the module level.
"""

from __future__ import annotations

from app.esrs_validate import validate_esef_statement


def _sample(assurance_status="limited") -> bytes:
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "esdp", "app/esrs_datapoints.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sys.modules["app.esrs_datapoints"] = m
    from app import esrs_esef

    ids = ["E1.E1-6.44", "E1.E1-6.48", "ESRS2.GOV-1.21", "ESRS2.BP-1.3"]
    entries = [
        {
            "datapoint_id": i,
            "status": "reported",
            "value": 2480.0 if "E1-6" in i else f"Text re {i}",
            "evidence": "",
            "notes": "",
        }
        for i in ids
    ]
    return esrs_esef.build_esef_statement(
        financial_year="FY2025",
        org_id="org-test",
        org_name="Acme",
        entity_identifier="529900T8BM49AURSDO55",
        entries=entries,
        in_scope_ids=ids,
        coverage_pct=83.2,
        assurance={"status": assurance_status, "firm": "B4", "date": "2026-03-15", "statement": "ok"},
    )


def test_clean_statement_passes():
    res = validate_esef_statement(
        _sample(), financial_year="FY2025", coverage_pct=83.2, assurance={"status": "limited"}
    )
    assert res.passed
    assert res.errors == []
    assert any(i.code == "schema_ref" for i in res.issues)


def test_unknown_concept_is_an_error():
    res = validate_esef_statement(
        _sample().replace(
            b'name="esrs:GrossGreenhouseGasEmissions"',
            b'name="esrs:MadeUpElementThatDoesNotExist"',
        ),
        financial_year="FY2025",
        assurance={"status": "limited"},
    )
    assert not res.passed
    assert any(i.code == "unknown_concept" for i in res.issues)


def test_missing_assurance_is_an_error():
    res = validate_esef_statement(_sample(), financial_year="FY2025", assurance={"status": "none"})
    assert not res.passed
    assert any(i.code == "assurance_missing" for i in res.issues)


def test_duplicate_fact_is_an_error():
    content = _sample()
    marker = b"<ix:nonFraction"
    idx = content.index(marker)
    end = content.index(b"</ix:nonFraction>", idx) + len(b"</ix:nonFraction>")
    duplicate = content[idx:end]
    tampered = content[:end] + duplicate + content[end:]
    res = validate_esef_statement(tampered, financial_year="FY2025", assurance={"status": "limited"})
    assert not res.passed
    assert any(i.code == "duplicate_fact" for i in res.issues)


def test_bad_decimals_is_an_error():
    res = validate_esef_statement(
        _sample().replace(b'decimals="0"', b'decimals="abc"'),
        financial_year="FY2025",
        assurance={"status": "limited"},
    )
    assert any(i.code == "bad_decimals" for i in res.issues)


def test_non_xml_is_an_error():
    res = validate_esef_statement(b"<html><b>not closed", financial_year="FY2025")
    assert not res.passed
    assert any(i.code == "well_formed" for i in res.issues)


def test_unknown_context_ref_is_an_error():
    res = validate_esef_statement(
        _sample().replace(b'contextRef="cfy_fy2025"', b'contextRef="cfy_fy9999"'),
        financial_year="FY2025",
        assurance={"status": "limited"},
    )
    assert not res.passed
    assert any(i.code == "unknown_context" for i in res.issues)
