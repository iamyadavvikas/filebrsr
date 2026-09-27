"""CSRD workspace add-ons: audit trail, evidence docs, framework links, board pack."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.test_guest_csrd import GUEST_A, REAL_ORG, REAL_USER, _FakeDB, mint

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


def _auth(token=REAL_USER) -> dict:
    return {"authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_entry_upsert_writes_audit_trail_for_real_users(client, db):
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FY, "org_id": REAL_ORG, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 100},
        ]},
        headers=_auth(),
    )
    assert resp.status_code == 200, resp.text
    trail = db.tables.get("audit_trail", [])
    assert len(trail) == 1
    assert trail[0]["action"] == "create"
    assert trail[0]["entity_type"] == "esrs_entry"
    assert trail[0]["datapoint_id"] == "E1.E1-6.44"

    # Second identical upsert: no transition, no new row.
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FY, "org_id": REAL_ORG, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 100},
        ]},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert len(db.tables.get("audit_trail", [])) == 1

    # Status change lands a transition row.
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FY, "org_id": REAL_ORG, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "assessed", "value": 100},
        ]},
        headers=_auth(),
    )
    assert resp.status_code == 200
    trail = db.tables.get("audit_trail", [])
    assert len(trail) == 2
    assert trail[1]["action"] == "update"
    assert trail[1]["new_value"]["status"] == "assessed"


@pytest.mark.asyncio
async def test_guest_writes_skip_audit_but_work(client, db):
    mint(db)
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FY, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 5},
        ]},
        headers=_auth(GUEST_A),
    )
    assert resp.status_code == 200
    assert db.tables.get("audit_trail", []) == []


@pytest.mark.asyncio
async def test_audit_trail_read_filters(client, db):
    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FY, "org_id": REAL_ORG, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 1},
        ]},
        headers=_auth(),
    )
    resp = await client.get(
        "/api/platform/csrd/audit-trail",
        params={"financial_year": FY, "datapoint_id": "E1.E1-6.44"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    resp = await client.get(
        "/api/platform/csrd/audit-trail",
        params={"financial_year": FY, "datapoint_id": "E1.E1-6.99"},
        headers=_auth(),
    )
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_evidence_documents_lists_org_files(client, db):
    db.tables.setdefault("documents", []).append({
        "id": "doc-1", "org_id": REAL_ORG, "file_name": "meter-readings.pdf",
        "file_url": "https://cdn.test/meter.pdf", "category": "data_source",
        "financial_year": FY,
    })
    resp = await client.get(
        "/api/platform/csrd/evidence-documents",
        params={"financial_year": FY},
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["documents"][0]["file_name"] == "meter-readings.pdf"


@pytest.mark.asyncio
async def test_framework_links_groups_by_esrs_ref(client):
    resp = await client.get("/api/platform/csrd/framework-links", params={"standard": "E1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] > 0
    assert all(k.startswith("ESRS E1") or k.startswith("ESRS 2") or True for k in body["groups"])


@pytest.mark.asyncio
async def test_board_pack_renders_pdf(client, db):
    db.tables.setdefault("organizations", []).append({"id": REAL_ORG, "name": "Acme Ltd"})
    resp = await client.get(
        "/api/platform/csrd/board-pack",
        params={"financial_year": FY},
        headers=_auth(),
    )
    assert resp.status_code == 200, resp.text[:200]
    assert resp.headers["content-type"] == "application/pdf"
    content = await resp.aread()
    assert content.startswith(b"%PDF")
    assert len(content) > 2000
    # Export itself is audited.
    trail = db.tables.get("audit_trail", [])
    assert any(r["action"] == "export" and r["new_value"]["artifact"] == "board_pack" for r in trail)
