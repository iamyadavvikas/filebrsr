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
        assert c["status"] == "reported"
    ghg = [c for c in out["candidates"] if c["source_field"] == "ghg_scope1"]
    assert ghg and ghg[0]["value"] == 1200.5
    assert ghg[0]["confidence"] == 0.9
    assert ghg[0]["source_brsr_id"] == "C.P6.E.3"


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
    assert c["unit"] == "tCO2e"
    assert c["unit_converted"] is True
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
    assert csr[0]["unit_converted"] is True


def test_field_map_every_id_has_esrs_ref():
    """CI gate: no dead-end bridge fields (each maps to a real ESRS ref)."""
    from app.cross_framework_mapping import get_mapping_for_brsr_id
    from app.esrs_extract import FIELD_TO_BRSR, parse_esrs_ref
    from app.esrs_datapoints import ESRS_DATAPOINTS

    by_std_dr = {(d.get("standard"), d.get("dr")) for d in ESRS_DATAPOINTS}
    dead = []
    for field, brsr_id in FIELD_TO_BRSR.items():
        m = get_mapping_for_brsr_id(brsr_id)
        parsed = parse_esrs_ref((m or {}).get("esrs_ref") or "")
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
