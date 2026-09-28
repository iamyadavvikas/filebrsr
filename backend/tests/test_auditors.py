"""Auditor portal tests: magic-link grants, scoped reads, findings loop."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from tests.test_guest_csrd import _FakeDB

ORG = "org-audit-1"
FY = "FY2025-26"


@pytest.fixture
def db():
    return _FakeDB()


@pytest.fixture
def client(db, monkeypatch):
    import app.router_auditors as auditors
    import app.router_brsr_core as core

    monkeypatch.setattr(auditors, "get_supabase_admin", lambda: db)
    monkeypatch.setattr(core, "_resolve_org", lambda authorization: (db, ORG))
    from app.main import app

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _owner() -> dict:
    return {"authorization": "Bearer owner-jwt"}


async def _invite(client, email="auditor@verify.llp"):
    resp = await client.post(
        "/api/auditors/invite", json={"email": email}, headers=_owner()
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _past() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_invite_mint_accept_roundtrip(client, db):
    body = await _invite(client)
    assert body["token"].startswith("auditor_")
    assert body["invite_url"].endswith(body["token"])
    assert body["org_id"] == ORG

    # Raw token never persisted — only its hash.
    stored = db.tables["auditor_grants"][0]
    assert "token" not in stored or not str(stored.get("token", "")).startswith("auditor_")
    assert len(stored["token_hash"]) == 64

    resp = await client.post("/api/auditors/accept", json={"token": body["token"]})
    assert resp.status_code == 200
    assert resp.json()["org_id"] == ORG

    resp = await client.post("/api/auditors/accept", json={"token": "auditor_nope"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_and_revoked_fail_closed(client, db):
    body = await _invite(client)
    token = body["token"]
    db.tables["auditor_grants"][0]["expires_at"] = _past()
    resp = await client.post("/api/auditors/accept", json={"token": token})
    assert resp.status_code == 401

    body2 = await _invite(client, email="second@verify.llp")
    resp = await client.get("/api/auditors/workspace", params={"financial_year": FY},
                            headers={"authorization": f"Bearer {body2['token']}"})
    assert resp.status_code == 200
    resp = await client.delete(f"/api/auditors/grants/{db.tables['auditor_grants'][1]['id']}",
                               headers=_owner())
    assert resp.status_code == 200
    resp = await client.get("/api/auditors/workspace", params={"financial_year": FY},
                            headers={"authorization": f"Bearer {body2['token']}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auditors_cannot_administer(client, db):
    body = await _invite(client)
    h = {"authorization": f"Bearer {body['token']}"}
    resp = await client.post("/api/auditors/invite", json={"email": "x@y.z"}, headers=h)
    assert resp.status_code == 403
    resp = await client.get("/api/auditors/grants", headers=h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_workspace_bundle_and_isolation(client, db):
    body = await _invite(client)
    h = {"authorization": f"Bearer {body['token']}"}
    db.tables.setdefault("assurance_findings", []).append(
        {"id": "other-1", "org_id": "org-other", "status": "open", "message": "x"})
    resp = await client.get("/api/auditors/workspace", params={"financial_year": FY}, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["org_id"] == ORG
    assert "coverage" in data and "workpapers" in data
    assert all(f["org_id"] == ORG for f in data["findings"])


@pytest.mark.asyncio
async def test_findings_lifecycle_with_guards(client, db):
    body = await _invite(client)
    ah = {"authorization": f"Bearer {body['token']}"}
    resp = await client.post(
        "/api/auditors/findings",
        json={"financial_year": FY, "entity_type": "kpi", "entity_ref": "BRSC-1.1",
              "severity": "high", "message": "Tie Scope 1 to fuel invoices."},
        headers=ah,
    )
    assert resp.status_code == 200, resp.text
    fid = resp.json()["finding"]["id"]

    # Auditor cannot mark answered; org cannot close.
    resp = await client.put(f"/api/auditors/findings/{fid}", json={"status": "answered"}, headers=ah)
    assert resp.status_code == 400
    resp = await client.put(f"/api/auditors/findings/{fid}",
                            json={"status": "answered", "message": "Tied: see INV-101."},
                            headers=_owner())
    assert resp.status_code == 200
    assert resp.json()["finding"]["status"] == "answered"
    resp = await client.put(f"/api/auditors/findings/{fid}", json={"status": "closed"}, headers=_owner())
    assert resp.status_code == 400
    resp = await client.put(f"/api/auditors/findings/{fid}", json={"status": "closed"}, headers=ah)
    assert resp.status_code == 200
    assert resp.json()["finding"]["status"] == "closed"
    assert len(resp.json()["finding"]["thread"]) == 2  # close without message appends nothing

    resp = await client.post(
        "/api/auditors/findings", json={"message": "   "}, headers=ah)
    assert resp.status_code == 400
