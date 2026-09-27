"""ISAE workpapers + provider registry tests (migration v35)."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.brsr_core import BRSC
from app.brsr_workpapers import (
    catalog_size,
    checkpoints_for,
    instantiate,
    list_providers,
    list_workpapers,
    progress,
    rotation_due,
    update_workpaper,
    upsert_provider,
)

BY_CODE = {k["code"]: k for k in BRSC}
ORG = "org-test-1"
FY = "FY2025-26"


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, store):
        self._store = store
        self._filters = []
        self._op = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, *_a, **_k):
        return self

    def insert(self, rows):
        rows = rows if isinstance(rows, list) else [rows]
        self._op = ("insert", rows)
        return self

    def upsert(self, rows, on_conflict=None):
        rows = rows if isinstance(rows, list) else [rows]
        self._op = ("upsert", rows, on_conflict)
        return self

    def update(self, patch):
        self._op = ("update", patch)
        return self

    def delete(self):
        self._op = ("delete",)
        return self

    def _matched(self):
        return [r for r in self._store if all(r.get(c) == v for c, v in self._filters)]

    def execute(self):
        if self._op is None:
            return _Resp(self._matched())
        kind, *rest = self._op
        if kind == "insert":
            for r in rest[0]:
                r.setdefault("id", f"id-{len(self._store)}")
                self._store.append(r)
            return _Resp(rest[0])
        if kind == "upsert":
            rows, on_conflict = rest
            keys = [k.strip() for k in (on_conflict or "id").split(",")]
            written = []
            for r in rows:
                match = next((x for x in self._store if all(x.get(k) == r.get(k) for k in keys)), None)
                if match is None:
                    r.setdefault("id", f"id-{len(self._store)}")
                    self._store.append(r)
                    written.append(r)
                else:
                    match.update(r)
                    written.append(match)
            return _Resp(written)
        if kind == "update":
            matched = self._matched()
            for r in matched:
                r.update(rest[0])
            return _Resp(matched)
        if kind == "delete":
            matched = self._matched()
            for r in matched:
                self._store.remove(r)
            return _Resp(matched)
        raise AssertionError(kind)


class _FakeSB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}

    def table(self, name):
        return _Query(self.tables.setdefault(name, []))


# ─── catalog ────────────────────────────────────────────────────────────────


def test_checkpoint_counts():
    assert catalog_size("limited") == 5 + 2 + 1
    assert catalog_size("reasonable") == 5 + 5 + 1
    codes = [c["code"] for c in checkpoints_for(1, "limited")]
    assert codes[:5] == ["C1", "C2", "C3", "C4", "C5"]
    assert "E1" in codes
    assert any("fuel invoices" in c["detail"].lower() for c in checkpoints_for(1, "limited"))
    with pytest.raises(ValueError):
        checkpoints_for(1, "absolute")


def test_instantiate_unknown_kpi_rejected():
    with pytest.raises(ValueError):
        instantiate(_FakeSB(), ORG, FY, ["BRSC-99.9"], "limited", BY_CODE.get)


def test_instantiate_idempotent_and_progress():
    sb = _FakeSB()
    out = instantiate(sb, ORG, FY, ["BRSC-1.1", "BRSC-2.1"], "reasonable", BY_CODE.get)
    assert out["created"] == 2 * catalog_size("reasonable")
    assert out["skipped"] == 0
    out2 = instantiate(sb, ORG, FY, ["BRSC-1.1"], "reasonable", BY_CODE.get)
    assert out2["created"] == 0
    assert out2["skipped"] == catalog_size("reasonable")

    rows = list_workpapers(sb, ORG, FY)
    assert len(rows) == 2 * catalog_size("reasonable")

    upd = update_workpaper(sb, ORG, FY, "BRSC-1.1", "C1", {"status": "closed", "prepared_by": "A. Rao"})
    assert upd["status"] == "closed"
    assert upd["closed_at"]
    with pytest.raises(ValueError):
        update_workpaper(sb, ORG, FY, "BRSC-1.1", "C2", {"status": "bogus"})
    assert update_workpaper(sb, ORG, FY, "BRSC-9.9", "C1", {"status": "closed"}) is None

    p = progress(sb, ORG, FY)
    assert p["kpis"] == 2
    assert p["closed"] == 1
    assert p["coverage_pct"] == round(100.0 / (2 * catalog_size("reasonable")), 2)


def test_providers_and_rotation():
    sb = _FakeSB()
    p = upsert_provider(sb, ORG, {"firm_name": "Verify LLP", "partner_name": "S. Iyer",
                                  "rotation_started_on": "2010-01-01"})
    assert p["firm_name"] == "Verify LLP"
    rows = list_providers(sb, ORG)
    assert len(rows) == 1
    assert rotation_due(rows[0], today=date(2026, 9, 27))["due"] is True
    assert rotation_due({"rotation_started_on": "2024-01-01"}, today=date(2026, 9, 27))["due"] is False
    assert rotation_due({}, today=date(2026, 9, 27))["due"] is False


# ─── endpoints ──────────────────────────────────────────────────────────────


@pytest.fixture
def api_client(monkeypatch):
    import app.router_brsr_core as router

    sb = _FakeSB()
    monkeypatch.setattr(router, "get_supabase_admin", lambda: sb)
    monkeypatch.setattr(router, "_resolve_org", lambda authorization: (sb, ORG))
    from app.main import app

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_provider_endpoints(api_client):
    resp = await api_client.put(
        "/api/brsr-core/providers",
        params={},
        json={"firm_name": "Verify LLP", "rotation_started_on": "2010-06-01"},
        headers={"authorization": "Bearer x"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["provider"]["rotation"]["due"] is True

    resp = await api_client.get("/api/brsr-core/providers", headers={"authorization": "Bearer x"})
    assert resp.json()["count"] == 1

    resp = await api_client.put(
        "/api/brsr-core/providers",
        json={"firm_name": "Verify LLP", "status": "bogus"},
        headers={"authorization": "Bearer x"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_workpaper_endpoints(api_client):
    resp = await api_client.post(
        "/api/brsr-core/workpapers/instantiate",
        json={"financial_year": FY, "kpi_codes": ["BRSC-1.1"], "level": "limited"},
        headers={"authorization": "Bearer x"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == catalog_size("limited")

    resp = await api_client.post(
        "/api/brsr-core/workpapers/instantiate",
        json={"financial_year": FY, "kpi_codes": ["BRSC-99.9"], "level": "limited"},
        headers={"authorization": "Bearer x"},
    )
    assert resp.status_code == 400

    resp = await api_client.put(
        "/api/brsr-core/workpapers/BRSC-1.1/C1",
        params={"financial_year": FY},
        json={"status": "closed", "evidence_ref": "INV-2025-001"},
        headers={"authorization": "Bearer x"},
    )
    assert resp.status_code == 200
    assert resp.json()["workpaper"]["status"] == "closed"

    resp = await api_client.get(
        "/api/brsr-core/workpapers/progress",
        params={"financial_year": FY},
        headers={"authorization": "Bearer x"},
    )
    body = resp.json()
    assert body["kpis"] == 1
    assert body["closed"] == 1
