"""ESRS Upload & Extract bridge tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.esrs_extract import brsr_fields_to_esrs_candidates, parse_esrs_ref
from tests.test_guest_csrd import GUEST_A, _FakeDB, mint

FY = "FY2025"


@pytest.fixture
def db():
    return _FakeDB()


@pytest.fixture
def settings(db, monkeypatch):
    import app.router_csrd as csrd
    from app.config import Settings

    cfg = Settings(
        SUPABASE_URL="http://fake",
        SUPABASE_SERVICE_KEY="k",
        CSRD_GUEST_ENABLED=True,
        CSRD_GUEST_TTL_HOURS=72,
        CSRD_GUEST_RATE_MINUTE=20,
        CSRD_GUEST_MAX_REPORTS=5,
        ENVIRONMENT="development",
    )
    monkeypatch.setattr(csrd, "get_supabase_admin", lambda: db)
    monkeypatch.setattr(csrd, "get_settings", lambda: cfg)
    return cfg


@pytest.fixture
def client(db, settings):
    from app.main import app

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _auth(token=GUEST_A) -> dict:
    return {"authorization": f"Bearer {token}"}


def test_headcount_grids_parse_without_cross_contamination():
    from app.extraction_enhanced import extract_tables

    out = extract_tables(
        "Particulars Male Female Total\n"
        "Permanent Employees 800 320 1120\n"
        "Other than Permanent Employees 100 50 150\n"
        "Permanent Workers 150 30 180\n"
        "Other than Permanent Workers 60 20 80\n"
    )["section_a"]
    assert out["wf_perm_emp_m"] == "800"
    assert out["wf_perm_emp_f"] == "320"
    assert out["wf_perm_emp_t"] == "1120"
    assert out["wf_other_emp_m"] == "100"
    assert out["wf_perm_work_t"] == "180"
    assert out["wf_other_work_t"] == "80"


def test_headcount_grids_require_header():
    from app.extraction_enhanced import extract_tables

    out = extract_tables("Permanent Employees went up this year.")["section_a"]
    assert not any(k.startswith("wf_") for k in out)


def test_headcount_grid_fields_bridge_to_esrs():
    from app.esrs_extract import FIELD_TO_BRSR, _resolve_esrs
    from app.esrs_datapoints import ESRS_DATAPOINTS

    by_std_dr = {(d.get("standard"), d.get("dr")) for d in ESRS_DATAPOINTS}
    for key in ["wf_perm_emp_m", "wf_perm_emp_f", "wf_other_emp_t",
                "wf_perm_work_m", "wf_other_work_f"]:
        assert key in FIELD_TO_BRSR, key
        parsed = _resolve_esrs(FIELD_TO_BRSR[key])
        assert parsed and parsed in by_std_dr, (key, parsed)


def test_canonicalise_energy_water_mass():
    from app.normalise import canonicalise

    assert canonicalise(5.4, "GWh") == (5400.0, "MWh", True)
    assert canonicalise(19440, "GJ") == (5400.0, "MWh", True)
    assert canonicalise(5400, "MWh") == (5400.0, "MWh", False)
    assert canonicalise(95, "ML") == (95000.0, "m3", True)
    assert canonicalise(300, "MT") == (300.0, "tonnes", False)
    assert canonicalise(7, "furlongs") == (7, "furlongs", False)


def test_bridge_applies_canonical_scale():
    out = brsr_fields_to_esrs_candidates(
        {
            "section_c": {"energy_consumption_total": "5.4 GWh"},
            "normalised": {"section_c": {"energy_consumption_total": {
                "raw": "5.4 GWh", "value": 5.4, "unit": "GWh", "value_inr": None}}},
        },
        {},
    )
    e = [c for c in out["candidates"] if c["source_field"] == "energy_consumption_total"]
    assert e, "energy field should map"
    assert e[0]["value"] == 5400.0
    assert e[0]["unit"] == "MWh"
    assert e[0]["unit_converted"] is True
    assert e[0]["raw_value"] == "5.4 GWh"


def test_sector_phrase_variants():
    from app.extraction import extract_with_regex

    r = extract_with_regex(
        "Revenue: Rs 4,850\nPermanent headcount: 1150\n"
        "Learning hours per employee: 30\nTRIFR: 0.4"
    )
    assert r["section_a"].get("turnover") == "4,850"
    assert r["section_a"].get("employees_permanent") == "1150"
    assert r["section_c"].get("training_hours_per_employee") == "30"
    assert r["section_c"].get("safety_incidents") == "0.4"


def test_parse_esrs_ref():
    assert parse_esrs_ref("ESRS S1-6.50(a)") == ("S1", "S1-6")
    assert parse_esrs_ref("ESRS 2 BP-1") == ("2", "BP-1")
    assert parse_esrs_ref("ESRS G1-1") == ("G1", "G1-1")
    assert parse_esrs_ref("something else") is None


def test_bridge_maps_fields_to_real_datapoints():
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"ghg_scope1": 1200.5, "waste_generated": 300, "zzz_unknown": 1},
         "section_a": {}, "section_b": {}, "normalised": {}},
        {"ghg_scope1": 0.9},
    )
    by_dp = {c["datapoint_id"]: c for c in out["candidates"]}
    assert out["candidates"], "expected candidates from mapped fields"
    assert out["stats"]["fields_mapped"] >= 2
    # Every candidate targets a real registry datapoint.
    from app.esrs_datapoints import by_id

    for c in out["candidates"]:
        assert by_id(c["datapoint_id"]) is not None
        assert c["status"] in ("reported", "in_progress")
    ghg = [c for c in out["candidates"] if c["source_field"] == "ghg_scope1"]
    assert ghg and ghg[0]["value"] == 1200.5
    # No unit context on a measure field -> weak-flagged and capped.
    assert ghg[0]["confidence"] == 0.3
    assert ghg[0]["weak_reasons"] == ["no_unit"]


def test_unit_context_preserves_confidence():
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"ghg_scope1": 1200.5},
         "normalised": {"section_c": {"ghg_scope1": {
             "raw": 1200.5, "value": 1200.5, "unit": "tCO2e", "value_inr": None}}}},
        {"ghg_scope1": 0.9},
    )
    ghg = [c for c in out["candidates"] if c["source_field"] == "ghg_scope1"]
    assert ghg and ghg[0]["confidence"] == 0.9
    assert ghg[0]["weak_reasons"] == []


def test_snippet_recovers_dropped_unit():
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"ghg_scope1": 1200.5},
         "citations": {"section_c": {"ghg_scope1": {
             "source_page": 12, "snippet": "Scope 1 emissions: 1200 tCO2e", "match_kind": "numeric"}}}},
        {"ghg_scope1": 0.9},
    )
    ghg = [c for c in out["candidates"] if c["source_field"] == "ghg_scope1"]
    assert ghg
    assert ghg[0]["unit"] == "tCO2e"
    assert ghg[0]["weak_reasons"] == []
    assert ghg[0]["confidence"] == 0.9


def test_junk_values_dropped():
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"ghg_scope1": "n", "ghg_scope2": " ", "waste_generated": 5}},
        {},
    )
    fields = {c["source_field"] for c in out["candidates"]}
    assert "ghg_scope1" not in fields
    assert "ghg_scope2" not in fields
    assert out["stats"]["dropped_junk"] == 2
    assert "waste_generated" in fields


def test_narrative_datapoints_get_snippets_not_numbers():
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"anti_corruption_policy": "Yes, zero-tolerance policy"},
         "citations": {"section_c": {"anti_corruption_policy": {
             "source_page": 25, "snippet": "zero-tolerance policy", "match_kind": "text"}}}},
        {},
    )
    nar = [c for c in out["candidates"]
           if c["source_field"] == "anti_corruption_policy" and c.get("needs_writing")]
    assert nar, "narrative datapoints should get snippet candidates"
    assert all(c["status"] == "in_progress" and c.get("needs_writing") for c in nar)
    assert all(c["source_page"] == 25 for c in nar)
    # Figure is kept alongside the snippet so nothing is lost.
    assert all(c["value"] is not None for c in nar)


def test_semi_narrative_bare_numbers_route_to_snippets():
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"ghg_scope1": 67.6},
         "citations": {"section_c": {}}},
        {},
    )
    # E1-3.23 is semi-narrative: bare number without snippet context stays
    # visible but weak-flagged (recall preserved, trust withheld).
    e13 = [c for c in out["candidates"] if c["datapoint_id"] == "E1.E1-3.23"]
    assert not e13  # ghg maps to E1-6, not E1-3 — use the right field below
    out2 = brsr_fields_to_esrs_candidates(
        {"section_c": {"r_and_d_spend": 96000000},
         "citations": {"section_c": {"r_and_d_spend": {
             "source_page": 9, "snippet": "R&D spend Rs 9.6 Cr on clean tech", "match_kind": "numeric"}}}},
        {},
    )
    e13b = [c for c in out2["candidates"] if c["datapoint_id"] == "E1.E1-3.23"]
    assert e13b, "E1-3 narrative family should surface with snippet"
    assert e13b[0]["status"] == "in_progress"
    assert e13b[0].get("needs_writing") is True


def test_policy_field_numerics_flagged_unexpected():
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"anti_corruption_policy": 25}},
        {},
    )
    flagged = [c for c in out["candidates"] if c["source_field"] == "anti_corruption_policy"]
    assert flagged
    assert all("unexpected_number" in (c.get("weak_reasons") or []) for c in flagged)
    assert all((c.get("confidence") or 0) <= 0.35 for c in flagged)


def test_bridge_passes_citations_and_normalised_units():
    out = brsr_fields_to_esrs_candidates(
        {
            "section_c": {"ghg_scope1": 1200.5},
            "citations": {"section_c": {"ghg_scope1": {
                "source_page": 47, "snippet": "Scope 1 emissions: 1200 tCO2e", "match_kind": "numeric"}}},
            "normalised": {"section_c": {"ghg_scope1": {
                "raw": 1200.5, "value": 1200.5, "unit": "tCO2e", "value_inr": None}}},
        },
        {},
    )
    assert out["candidates"]
    c = out["candidates"][0]
    assert c["source_page"] == 47
    assert "Scope 1" in (c["snippet"] or "")
    assert c["match_kind"] == "numeric"
    assert c["unit"] == "tonnes"  # tCO2e canonicalised, same scale
    assert c["unit_converted"] is False
    assert c["raw_value"] is None  # display == raw here


def test_bridge_inr_magnitude_uses_normalised_value():
    out = brsr_fields_to_esrs_candidates(
        {
            "section_c": {"csr_spend": "Rs 1.5 Cr"},
            "normalised": {"section_c": {"csr_spend": {
                "raw": "Rs 1.5 Cr", "value": 15000000.0, "unit": "INR", "value_inr": 15000000.0}}},
        },
        {},
    )
    csr = [c for c in out["candidates"] if c["source_field"] == "csr_spend"]
    assert csr, "csr_spend should map"
    assert csr[0]["value"] == 15000000.0
    assert csr[0]["raw_value"] == "Rs 1.5 Cr"
    assert csr[0]["unit"] == "INR"
    assert csr[0]["unit_converted"] is False  # magnitude applied upstream, no rescale here


def test_field_map_every_id_has_esrs_ref():
    """CI gate: no dead-end bridge fields (each maps to a real ESRS ref)."""
    from app.esrs_extract import FIELD_TO_BRSR, _resolve_esrs
    from app.esrs_datapoints import ESRS_DATAPOINTS

    by_std_dr = {(d.get("standard"), d.get("dr")) for d in ESRS_DATAPOINTS}
    dead = []
    for field, brsr_id in FIELD_TO_BRSR.items():
        parsed = _resolve_esrs(brsr_id)
        if not parsed or parsed not in by_std_dr:
            dead.append((field, brsr_id))
    assert dead == [], f"bridge fields with no ESRS target: {dead}"
    assert len(FIELD_TO_BRSR) >= 30


def test_bridge_skips_empties_and_caps():
    out = brsr_fields_to_esrs_candidates(
        {"section_a": {"ghg_scope1": None, "waste_generated": ""}}, {}, max_candidates=1
    )
    assert out["candidates"] == []
    out = brsr_fields_to_esrs_candidates(
        {"section_c": {"ghg_scope1": 1, "ghg_scope2": 2}}, {}, max_candidates=1
    )
    assert len(out["candidates"]) == 1
    assert out["stats"]["capped"] is True


@pytest.mark.asyncio
async def test_extract_endpoint_bridges_pipeline_output(client, db):
    mint(db)
    fake_result = {
        "status": "completed",
        "error": None,
        "extracted_data": {
            "section_a": {},
            "section_b": {},
            "section_c": {"ghg_scope1": 1200.5},
            "normalised": {},
        },
        "confidence_scores": {"ghg_scope1": 0.85},
        "company_name": "Acme Ltd",
        "financial_year": "FY2025",
    }
    with patch("app.extraction_pipeline.run_full_extraction", new=AsyncMock(return_value=fake_result)):
        resp = await client.post(
            "/api/platform/csrd/extract",
            files={"file": ("report.pdf", b"%PDF-fake", "application/pdf")},
            headers=_auth(),
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["company_name"] == "Acme Ltd"
    assert body["candidates"]
    assert all(c["status"] == "reported" for c in body["candidates"])


@pytest.mark.asyncio
async def test_mining_reports_drift_and_calibration(client, db):
    mint(db)
    # Two AI-confirmed entries, one later edited by the reviewer.
    for dp, val, conf in [("E1.E1-6.44", 1200, 0.9), ("E1.E1-5.37", 5400, 0.4)]:
        resp = await client.post(
            "/api/platform/csrd/entries",
            json={"financial_year": FY, "entries": [
                {"datapoint_id": dp, "status": "reported", "value": val,
                 "source": "ai-extract", "ai_value": val, "ai_confidence": conf},
            ]},
            headers=_auth(),
        )
        assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FY, "entries": [
            {"datapoint_id": "E1.E1-5.37", "status": "reported", "value": 5900,
             "source": "ai-extract", "ai_value": 5400, "ai_confidence": 0.4},
        ]},
        headers=_auth(),
    )
    assert resp.status_code == 200
    resp = await client.get(
        "/api/platform/csrd/extract/miss-patterns", params={"financial_year": FY}, headers=_auth()
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ai_confirmed"] == 2
    assert body["drifted"] == 1
    assert body["drift_rate"] == 0.5
    by_dp = {r["datapoint_id"]: r for r in body["by_datapoint"]}
    assert by_dp["E1.E1-5.37"]["drifted"] == 1
    assert by_dp["E1.E1-6.44"]["drifted"] == 0
    # The drifted entry had lower confidence than the clean one.
    assert body["avg_conf_drifted"] == 0.4
    assert body["avg_conf_clean"] == 0.9


@pytest.mark.asyncio
async def test_extract_endpoint_rejects_oversize_and_failures(client, db, settings, monkeypatch):
    mint(db)
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 0)
    resp = await client.post(
        "/api/platform/csrd/extract",
        files={"file": ("big.pdf", b"x" * 16, "application/pdf")},
        headers=_auth(),
    )
    assert resp.status_code == 400
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 50)
    with patch(
        "app.extraction_pipeline.run_full_extraction",
        new=AsyncMock(return_value={"status": "failed", "error": "no text"}),
    ):
        resp = await client.post(
            "/api/platform/csrd/extract",
            files={"file": ("report.pdf", b"%PDF-fake", "application/pdf")},
            headers=_auth(),
        )
    assert resp.status_code == 422
