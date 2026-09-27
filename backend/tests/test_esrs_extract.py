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
