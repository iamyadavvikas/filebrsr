"""Year-rollover tests: carry-forward, variance flags, restatement reasons."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.test_guest_csrd import GUEST_A, _FakeDB, mint

FROM = "FY2025"
TO = "FY2026"


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


async def _seed_from(client):
    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FROM, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 1000},
            {"datapoint_id": "E1.E1-5.37", "status": "not_applicable", "value": None},
        ]},
        headers=_auth(),
    )
    await client.post(
        "/api/platform/csrd/materiality",
        json={"financial_year": FROM, "iro_type": "impact", "standard": "E1",
              "title": "Scope 1 emissions", "impact_materiality": 4, "financial_materiality": 3},
        headers=_auth(),
    )
    await client.post(
        "/api/platform/csrd/dma-config/approve",
        json={"financial_year": FROM, "approved_by": "Board"},
        headers=_auth(),
    )


@pytest.mark.asyncio
async def test_rollover_copies_and_resets(client, db):
    mint(db)
    await _seed_from(client)
    resp = await client.post(
        "/api/platform/csrd/rollover", json={"from_fy": FROM, "to_fy": TO}, headers=_auth()
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["entries_copied"] == 2
    assert body["iros_copied"] == 1

    resp = await client.get(
        "/api/platform/csrd/entries", params={"financial_year": TO}, headers=_auth()
    )
    rows = {e["datapoint_id"]: e for e in resp.json()["entries"]}
    assert rows["E1.E1-6.44"]["status"] == "in_progress"
    assert rows["E1.E1-6.44"]["value"] == 1000
    assert rows["E1.E1-5.37"]["status"] == "not_applicable"

    resp = await client.get(
        "/api/platform/csrd/materiality", params={"financial_year": TO}, headers=_auth()
    )
    iros = resp.json()["iro"]
    assert len(iros) == 1
    assert iros[0]["status"] == "draft"
    assert iros[0]["material"] is False

    resp = await client.get(
        "/api/platform/csrd/dma-config", params={"financial_year": TO}, headers=_auth()
    )
    assert resp.json()["status"] == "draft"
    assert resp.json()["approved_by"] is None

    # Rerun is idempotent: nothing new copied.
    resp = await client.post(
        "/api/platform/csrd/rollover", json={"from_fy": FROM, "to_fy": TO}, headers=_auth()
    )
    assert resp.json()["entries_copied"] == 0
    assert resp.json()["entries_skipped"] == 2


@pytest.mark.asyncio
async def test_rollover_rejects_same_fy(client, db):
    mint(db)
    resp = await client.post(
        "/api/platform/csrd/rollover", json={"from_fy": FROM, "to_fy": FROM}, headers=_auth()
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_variance_flags_thresholds(client, db):
    mint(db)
    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FROM, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 1000},
            {"datapoint_id": "E1.E1-5.37", "status": "reported", "value": 500},
        ]},
        headers=_auth(),
    )
    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": TO, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 1200},
            {"datapoint_id": "E1.E1-5.37", "status": "reported", "value": 505},
        ]},
        headers=_auth(),
    )
    resp = await client.get(
        "/api/platform/csrd/rollover/variance",
        params={"from_fy": FROM, "to_fy": TO}, headers=_auth(),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["compared"] == 2
    assert body["flagged"] == 1
    assert body["flags"][0]["datapoint_id"] == "E1.E1-6.44"
    assert body["flags"][0]["pct_change"] == 20.0


@pytest.mark.asyncio
async def test_bulk_reason_lands_in_audit_for_real_users(client, db):
    from tests.test_guest_csrd import REAL_ORG, REAL_USER

    auth = {"authorization": f"Bearer {REAL_USER}"}
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FROM, "org_id": REAL_ORG, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 900},
        ], "reason": "Restated: meter recalibration"},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    trail = db.tables.get("audit_trail", [])
    assert len(trail) == 1
    assert trail[0]["change_reason"] == "Restated: meter recalibration"
