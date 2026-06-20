"""
Phase A — signed provenance wired into the live calculation path.

Acceptance:
- The Scope 1/2/3 provenance endpoints return a signed, self-verifying PROV-O
  graph (demo callers: not persisted).
- When the caller is authenticated (real org), the signed calculation is
  persisted to ``calculations`` + ``provenance_records`` AND a Merkle ledger
  append is scheduled as a background task.
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.factors_india import reset_cache
from app.main import app
from app.prov.signing import LocalEd25519Signer, reset_signer

_FIXED_SEED_B64 = base64.b64encode(bytes(range(2, 34))).decode("ascii")


@pytest.fixture(autouse=True)
def _fixed_signer(monkeypatch):
    reset_signer()
    reset_cache()
    signer = LocalEd25519Signer.from_seed_b64(_FIXED_SEED_B64, "live-test-key")
    monkeypatch.setattr("app.prov.signing._signer", signer, raising=False)
    yield
    reset_signer()
    reset_cache()


async def _post(path: str, json: dict, headers: dict | None = None):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.post(path, json=json, headers=headers or {})


# ─── demo (unauthenticated) path: signed but not persisted ─────────────────

async def test_scope2_provenance_demo_signed_not_persisted():
    resp = await _post(
        "/api/platform/carbon/scope2/provenance",
        {"kwh": 150000, "jurisdiction": "AU", "state": "NSW"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["persisted"] is False
    assert body["jurisdiction"] == "AU"
    assert body["factor"]["id"] == "nga/nsw"
    # The signed graph carries jurisdiction + framework tags.
    output = body["provenance"]["graph"]["@graph"][0]
    assert output["fbrsr:jurisdiction"] == "AU"


async def test_scope1_and_scope3_provenance_demo_paths():
    r1 = await _post(
        "/api/platform/carbon/scope1/provenance",
        {"fuel_type": "diesel", "quantity": 1000},
    )
    assert r1.status_code == 200
    assert r1.json()["verified"] is True

    # An unknown Scope 3 category must 400 (never substitute a factor).
    r3 = await _post(
        "/api/platform/carbon/scope3/provenance",
        {"category": "definitely_not_a_category", "quantity": 10},
    )
    assert r3.status_code == 400


# ─── authenticated path: persists + schedules ledger anchor ────────────────

async def test_scope2_provenance_authenticated_persists_and_anchors(monkeypatch):
    inserted: dict[str, list[dict]] = {"calculations": [], "provenance_records": []}

    def _table(name):
        t = MagicMock()

        def _insert(row):
            inserted.setdefault(name, []).append(row)
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[])
            return m

        t.insert.side_effect = _insert
        return t

    sb = MagicMock()
    sb.table.side_effect = _table

    scheduled: list[str] = []

    async def _fake_resolve(_auth):
        return "org-1", "user-1"

    # Force an authenticated org and capture the background ledger task.
    monkeypatch.setattr("app.router_platform.resolve_org_user", _fake_resolve)
    monkeypatch.setattr(
        "app.router_platform.get_supabase_admin", lambda: sb, raising=False
    )
    # Stub the ledger append (its own supabase path) so we only assert it's scheduled.
    import app.router_platform as rp

    orig = rp._ledger_append_calculation
    monkeypatch.setattr(
        rp,
        "_ledger_append_calculation",
        lambda *a, **k: scheduled.append("anchored"),
    )

    resp = await _post(
        "/api/platform/carbon/scope2/provenance",
        {"kwh": 150000, "jurisdiction": "AU", "state": "NSW"},
        headers={"Authorization": "Bearer fake.jwt.token"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["persisted"] is True

    # Both tables were written, with jurisdiction on the calculation row.
    assert len(inserted["calculations"]) == 1
    assert len(inserted["provenance_records"]) == 1
    assert inserted["calculations"][0]["jurisdiction"] == "AU"
    assert inserted["calculations"][0]["org_id"] == "org-1"
    # A ledger anchor was scheduled (background task ran in the test client).
    assert scheduled == ["anchored"]
    assert orig is not None
