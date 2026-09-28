"""Supplier cascade tests: magic links, questionnaires, prefill."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.test_guest_csrd import _FakeDB

ORG = "org-sup-1"
FY = "FY2025-26"


@pytest.fixture
def db():
    return _FakeDB()


@pytest.fixture
def client(db, monkeypatch):
    import app.router_brsr_core as core
    import app.router_suppliers as suppliers

    monkeypatch.setattr(suppliers, "get_supabase_admin", lambda: db)
    monkeypatch.setattr(core, "_resolve_org", lambda authorization: (db, ORG))
    from app.main import app

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _owner() -> dict:
    return {"authorization": "Bearer owner-jwt"}


def test_questionnaire_maps_to_all_resolve():
    from app.esrs_datapoints import by_id
    from app.supplier_questions import BY_CODE

    bad = [(c, d) for c, q in BY_CODE.items() for d in q["maps_to"] if by_id(d) is None]
    assert bad == []


@pytest.mark.asyncio
async def test_questionnaires_catalog_public(client):
    resp = await client.get("/api/suppliers/questionnaires")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"brsr_a5", "esrs_s2"}
    assert len(body["brsr_a5"]["questions"]) >= 10
    assert len(body["esrs_s2"]["questions"]) >= 8


@pytest.mark.asyncio
async def test_invite_form_answer_submit_prefill(client, db):
    resp = await client.post(
        "/api/suppliers/invite",
        json={"name": "Acme Forgings", "email": "e@acme.in", "tier": "tier_1"},
        headers=_owner(),
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    assert token.startswith("supplier_")
    assert resp.json()["invite_url"].endswith(token)
    assert len(db.tables["cascade_suppliers"][0]["token_hash"]) == 64

    sh = {"authorization": f"Bearer {token}"}
    resp = await client.get(
        "/api/suppliers/form",
        params={"token": token, "financial_year": FY, "questionnaire": "brsr_a5"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["questions"]) >= 10

    answers = {"SUP2": 450, "SUP4": 1200.5, "SUP8": 62, "SUP9": "Yes, zero-waste policy"}
    resp = await client.put(
        "/api/suppliers/responses",
        json={"financial_year": FY, "questionnaire": "brsr_a5", "answers": answers},
        headers=sh,
    )
    assert resp.json()["status"] == "draft"
    resp = await client.post(
        "/api/suppliers/responses/submit",
        json={"financial_year": FY, "questionnaire": "brsr_a5", "answers": answers},
        headers=sh,
    )
    assert resp.json()["status"] == "submitted"

    resp = await client.get(
        "/api/suppliers/responses", params={"financial_year": FY}, headers=_owner()
    )
    assert resp.json()["count"] == 1
    rid = resp.json()["responses"][0]["id"]

    resp = await client.post(f"/api/suppliers/responses/{rid}/prefill", headers=_owner())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] >= 3
    by_dp = {e["datapoint_id"]: e for e in body["entries"]}
    assert by_dp["E1.E1-6.44"]["value"] == 1200.5
    assert all(e["source"] == "supplier" for e in body["entries"])


@pytest.mark.asyncio
async def test_supplier_isolation_and_guards(client, db):
    await client.post("/api/suppliers/invite", json={"name": "A"}, headers=_owner())
    token_a = (await client.post("/api/suppliers/invite", json={"name": "B"}, headers=_owner())).json()["token"]
    # Supplier cannot administer or see client views.
    sh = {"authorization": f"Bearer {token_a}"}
    resp = await client.post("/api/suppliers/invite", json={"name": "C"}, headers=sh)
    assert resp.status_code == 403
    resp = await client.get("/api/suppliers/responses", headers=sh)
    assert resp.status_code == 403
    # Bad token + unknown questionnaire fail closed.
    resp = await client.get("/api/suppliers/form",
                            params={"token": "supplier_nope", "financial_year": FY})
    assert resp.status_code == 401
    resp = await client.get("/api/suppliers/form",
                            params={"token": token_a, "financial_year": FY, "questionnaire": "nope"})
    assert resp.status_code == 400
    # Unknown prefill id 404s.
    resp = await client.post("/api/suppliers/responses/does-not-exist/prefill", headers=_owner())
    assert resp.status_code == 404
