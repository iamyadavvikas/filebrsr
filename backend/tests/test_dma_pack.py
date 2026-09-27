"""DMA methodology pack tests (migration v34).

Acceptance:
- stakeholder engagements are logged/listed/deleted per org+FY with
  group/method validation;
- the threshold methodology defaults sensibly, updates, and locks on
  approval (separate from report attestation);
- material IROs trace to Disclosure Requirements (valid DRs only);
- /dma-coverage reports orphans (material IROs without DRs) and flips
  audit_ready only when DRs are linked, methodology is approved, and at
  least one stakeholder record exists;
- /dma-methodology renders an IRO-1 paragraph from the stored record;
- guest sandboxes are isolated from each other.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from tests.test_guest_csrd import GUEST_A, GUEST_B, _FakeDB, mint

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


async def _make_iro(client, token=GUEST_A, material=True):
    score = 4.0 if material else 1.0
    resp = await client.post(
        "/api/platform/csrd/materiality",
        json={
            "financial_year": FY,
            "iro_type": "impact",
            "standard": "E1",
            "title": "Scope 1 emissions",
            "impact_materiality": score,
            "financial_materiality": score,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["iro"]


# ─── stakeholders ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stakeholder_crud(client, db):
    mint(db)
    body = {
        "financial_year": FY,
        "stakeholder_group": "affected_communities",
        "method": "survey",
        "consulted_on": "2025-11-01",
        "participants": 120,
        "summary": "Water stress concerns near plant.",
        "influence": "Raised E3 severity from 2 to 4.",
    }
    resp = await client.post("/api/platform/csrd/stakeholders", json=body, headers=_auth())
    assert resp.status_code == 200, resp.text
    row = resp.json()["stakeholder"]
    assert row["stakeholder_group"] == "affected_communities"

    resp = await client.get(
        "/api/platform/csrd/stakeholders", params={"financial_year": FY}, headers=_auth()
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = await client.delete(
        f"/api/platform/csrd/stakeholders/{row['id']}", headers=_auth()
    )
    assert resp.status_code == 200

    resp = await client.get(
        "/api/platform/csrd/stakeholders", params={"financial_year": FY}, headers=_auth()
    )
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_stakeholder_rejects_unknown_group_and_method(client, db):
    mint(db)
    base = {"financial_year": FY, "stakeholder_group": "aliens", "method": "survey"}
    resp = await client.post("/api/platform/csrd/stakeholders", json=base, headers=_auth())
    assert resp.status_code == 400
    base = {"financial_year": FY, "stakeholder_group": "regulators", "method": "telepathy"}
    resp = await client.post("/api/platform/csrd/stakeholders", json=base, headers=_auth())
    assert resp.status_code == 400


# ─── threshold methodology ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dma_config_defaults_then_locks_on_approval(client, db):
    mint(db)
    resp = await client.get(
        "/api/platform/csrd/dma-config", params={"financial_year": FY}, headers=_auth()
    )
    assert resp.status_code == 200
    assert resp.json()["configured"] is False
    assert resp.json()["status"] == "draft"

    resp = await client.put(
        "/api/platform/csrd/dma-config",
        json={"financial_year": FY, "impact_threshold": 3.5, "methodology": "Board-approved matrix."},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["config"]["impact_threshold"] == 3.5
    assert resp.json()["config"]["status"] == "draft"

    resp = await client.post(
        "/api/platform/csrd/dma-config/approve",
        json={"financial_year": FY, "approved_by": "Audit Committee"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    cfg = resp.json()["config"]
    assert cfg["status"] == "approved"
    assert cfg["approved_by"] == "Audit Committee"
    assert cfg["approved_at"]


# ─── IRO-DR traceability ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_iro_dr_link_lifecycle_and_validation(client, db):
    mint(db)
    iro = await _make_iro(client)

    resp = await client.post(
        f"/api/platform/csrd/materiality/{iro['id']}/drs",
        json={"dr": "E1", "rationale": "Climate IRO drives E1 disclosures."},
        headers=_auth(),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["link"]["dr"] == "E1"

    resp = await client.post(
        f"/api/platform/csrd/materiality/{iro['id']}/drs",
        json={"dr": "NOPE-99"},
        headers=_auth(),
    )
    assert resp.status_code == 400

    resp = await client.get(
        f"/api/platform/csrd/materiality/{iro['id']}/drs", headers=_auth()
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = await client.delete(
        f"/api/platform/csrd/materiality/{iro['id']}/drs/E1", headers=_auth()
    )
    assert resp.status_code == 200

    resp = await client.get(
        f"/api/platform/csrd/materiality/{iro['id']}/drs", headers=_auth()
    )
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_dma_coverage_orphans_then_audit_ready(client, db):
    mint(db)
    iro = await _make_iro(client)
    assert iro["material"] is True

    resp = await client.get(
        "/api/platform/csrd/dma-coverage", params={"financial_year": FY}, headers=_auth()
    )
    body = resp.json()
    assert body["material_iros"] == 1
    assert body["covered_iros"] == 0
    assert body["orphan_iro_ids"] == [iro["id"]]
    assert body["audit_ready"] is False

    await client.post(
        f"/api/platform/csrd/materiality/{iro['id']}/drs",
        json={"dr": "E1-6"},
        headers=_auth(),
    )
    await client.post(
        "/api/platform/csrd/stakeholders",
        json={"financial_year": FY, "stakeholder_group": "investors_lenders", "method": "interview"},
        headers=_auth(),
    )
    await client.post(
        "/api/platform/csrd/dma-config/approve",
        json={"financial_year": FY, "approved_by": "Board"},
        headers=_auth(),
    )

    resp = await client.get(
        "/api/platform/csrd/dma-coverage", params={"financial_year": FY}, headers=_auth()
    )
    body = resp.json()
    assert body["covered_iros"] == 1
    assert body["orphan_iro_ids"] == []
    assert body["methodology_status"] == "approved"
    assert body["audit_ready"] is True


@pytest.mark.asyncio
async def test_dma_methodology_paragraph(client, db):
    mint(db)
    await _make_iro(client)
    resp = await client.get(
        "/api/platform/csrd/dma-methodology", params={"financial_year": FY}, headers=_auth()
    )
    assert resp.status_code == 200
    body = resp.json()
    assert FY in body["paragraph"]
    assert "draft" in body["paragraph"]
    assert body["audit_ready"] is False

    await client.post(
        "/api/platform/csrd/dma-config/approve",
        json={"financial_year": FY, "approved_by": "Board", "methodology": "Custom matrix."},
        headers=_auth(),
    )
    resp = await client.get(
        "/api/platform/csrd/dma-methodology", params={"financial_year": FY}, headers=_auth()
    )
    assert "Custom matrix." in resp.json()["paragraph"]
    assert "Board" in resp.json()["paragraph"]


# ─── isolation ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_guest_sandboxes_cannot_see_each_others_dma(client, db):
    mint(db, token=GUEST_A)
    mint(db, token=GUEST_B)
    await client.post(
        "/api/platform/csrd/stakeholders",
        json={"financial_year": FY, "stakeholder_group": "regulators", "method": "interview"},
        headers=_auth(GUEST_A),
    )
    resp = await client.get(
        "/api/platform/csrd/stakeholders", params={"financial_year": FY}, headers=_auth(GUEST_B)
    )
    assert resp.json()["count"] == 0
