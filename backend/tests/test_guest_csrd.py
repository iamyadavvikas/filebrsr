"""Open-to-all guest sandbox tests (migration v29).

Acceptance:
- a logged-out visitor can mint a throwaway sandbox org and run the whole
  CSRD workflow (seed -> entries -> materiality -> esef -> assurance ->
  attestation -> sandbox-only submission) without any sign-in;
- each guest session is a fresh org and can never see or write another org's
  data (org_id override is refused);
- guest submissions are sandbox-only: status ``sandboxed`` / channel
  ``guest_sandbox``, never posted to a real OAM, and signed with a test key;
- guest sandbox acknowledgements work even in production (that is their
  point), while real users still get 404;
- expired/unknown sessions fail closed (401), disabled config -> 404, and the
  mint path is rate-limited.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

GUEST_A = "guest_aaaa"
GUEST_B = "guest_bbbb"
REAL_USER = "user-csrd-1"
REAL_ORG = "org-csrd-1"

_ESEF_NUM = "E1.E1-6.44"
_ESEF_TXT = "ESRS2.BP-1.3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def _future() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, store: list[dict]):
        self._store = store
        self._filters: list[tuple[str, object]] = []
        self._order: tuple[str, bool] | None = None
        self._single_mode: str | None = None
        self._op: tuple | None = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def maybe_single(self):
        self._single_mode = "maybe"
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

    def execute(self):
        op = self._op
        if op is None:
            rows = [r for r in self._store if all(r.get(c) == v for c, v in self._filters)]
            if self._single_mode == "maybe":
                return _Resp(rows[0] if rows else None)
            return _Resp(rows)
        kind, *rest = op
        if kind == "insert":
            rows = rest[0]
            for r in rows:
                r.setdefault("id", str(uuid.uuid4()))
                r.setdefault("created_at", _now())
                r.setdefault("updated_at", _now())
                self._store.append(r)
            return _Resp(rows)
        if kind == "upsert":
            rows, on_conflict = rest
            keys = [k.strip() for k in (on_conflict or "id").split(",") if k.strip()]
            written = []
            for r in rows:
                match = next((x for x in self._store if all(x[k] == r.get(k) for k in keys)), None)
                if match is None:
                    r.setdefault("id", str(uuid.uuid4()))
                    r.setdefault("created_at", _now())
                    self._store.append(r)
                    written.append(r)
                else:
                    match.update({k: v for k, v in r.items() if v is not None and k != "id"})
                    written.append(match)
            return _Resp(written)
        if kind == "update":
            matched = [r for r in self._store if all(r.get(c) == v for c, v in self._filters)]
            for r in matched:
                r.update({k: v for k, v in rest[0].items() if k != "id"})
            return _Resp(matched)
        if kind == "delete":
            matched = [r for r in self._store if all(r.get(c) == v for c, v in self._filters)]
            for r in matched:
                self._store.remove(r)
            return _Resp(matched)
        raise AssertionError(f"unhandled op {kind}")


class _FakeDB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "org_members": [{"org_id": REAL_ORG, "user_id": REAL_USER, "role": "owner"}],
            "organization_members": [{"org_id": REAL_ORG, "user_id": REAL_USER, "role": "owner"}],
            "profiles": [{"id": REAL_USER, "org_id": REAL_ORG, "plan": "enterprise"}],
            "organizations": [],
            "esrs_guest_sessions": [],
            "esrs_entries": [],
            "esrs_materiality": [],
            "esrs_reports": [],
            "esrs_submissions": [],
        }

    def table(self, name: str) -> _Query:
        if name not in self.tables:
            self.tables[name] = []
        return _Query(self.tables[name])


def mint(db, token=GUEST_A, org_id=None):
    """Insert a live guest session + its sandbox org into the store directly."""
    org_id = org_id or f"sandbox-{token[6:]}"
    db.tables["organizations"].append(
        {"id": org_id, "name": "Acme Sandbox Ltd.", "slug": f"guest-{token[6:]}", "plan": "starter", "created_by": None}
    )
    db.tables["esrs_guest_sessions"].append(
        {"token": token, "org_id": org_id, "created_at": _now(), "expires_at": _future()}
    )
    return org_id


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

    def setter(**kw):
        cfg.__dict__.update(kw)

    monkeypatch.setattr(csrd, "get_settings", lambda: cfg)
    return cfg, setter


@pytest.fixture
def client(db, settings, monkeypatch):
    import app.router_csrd as csrd
    from app.main import app

    cfg, _ = settings
    app.dependency_overrides.clear()
    monkeypatch.setattr(csrd, "get_supabase_admin", lambda: db)
    monkeypatch.setattr(csrd, "get_settings", lambda: cfg)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _auth(token=GUEST_A) -> dict:
    return {"authorization": f"Bearer {token}"}


# ─── minting + isolation ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_guest_session_mint_creates_own_sandbox_org(client, db):
    resp = await client.post("/api/platform/csrd/guest/session")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "guest"
    assert body["token"].startswith("guest_")
    assert body["org_id"]
    assert body["expires_at"]
    assert len(db.tables["esrs_guest_sessions"]) == 1
    assert db.tables["esrs_guest_sessions"][0]["token"] == body["token"]
    assert db.tables["organizations"][0]["slug"].startswith("guest-sandbox-")

    resp = await client.get(
        "/api/platform/csrd/entries",
        params={"financial_year": "FY2025"},
        headers=_auth(body["token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["org_id"] == body["org_id"]
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_guest_sessions_are_isolated(client, db):
    org_a = mint(db, GUEST_A)
    mint(db, GUEST_B)

    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": "FY2025", "entries": [{"datapoint_id": _ESEF_NUM, "status": "reported", "value": 10}]},
        headers=_auth(GUEST_A),
    )

    # guest B cannot read guest A's org, even via an explicit org_id
    resp = await client.get(
        "/api/platform/csrd/entries",
        params={"org_id": org_a, "financial_year": "FY2025"},
        headers=_auth(GUEST_B),
    )
    assert resp.status_code == 403
    resp = await client.get("/api/platform/csrd/entries", params={"financial_year": "FY2025"}, headers=_auth(GUEST_B))
    assert resp.json()["count"] == 0

    # a guest cannot be coerced into a real org's data
    resp = await client.get(
        "/api/platform/csrd/entries",
        params={"org_id": REAL_ORG, "financial_year": "FY2025"},
        headers=_auth(GUEST_A),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_guest_session_expired_and_unknown_fail_closed(client, db):
    resp = await client.get("/api/platform/csrd/entries", params={"financial_year": "FY2025"}, headers=_auth("guest_never"))
    assert resp.status_code == 401

    mint(db, GUEST_A)
    db.tables["esrs_guest_sessions"][0]["expires_at"] = _past()
    resp = await client.get("/api/platform/csrd/entries", params={"financial_year": "FY2025"}, headers=_auth(GUEST_A))
    assert resp.status_code == 401
    assert db.tables["esrs_guest_sessions"] == []  # expired row pruned on access


@pytest.mark.asyncio
async def test_guest_disabled_config_404s(settings, monkeypatch):
    import app.router_csrd as csrd
    from app.main import app

    cfg, _ = settings
    cfg.__dict__.update(CSRD_GUEST_ENABLED=False)
    db = _FakeDB()
    app.dependency_overrides.clear()
    monkeypatch.setattr(csrd, "get_supabase_admin", lambda: db)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/platform/csrd/guest/session")
        assert resp.status_code == 404
        resp = await c.get("/api/platform/csrd/entries", params={"financial_year": "FY2025"}, headers=_auth())
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_guest_mint_rate_limit(client, db, settings):
    _, setter = settings
    setter(CSRD_GUEST_RATE_MINUTE=1)
    # consume the rolling one-minute budget before the mint attempt
    db.tables["esrs_guest_sessions"].append(
        {"token": "guest_preexisting", "org_id": "sandbox-x", "created_at": _now(), "expires_at": _future()}
    )
    resp = await client.post("/api/platform/csrd/guest/session")
    assert resp.status_code == 429


# ─── seed + full workflow in sandbox ────────────────────────────────────────


@pytest.mark.asyncio
async def test_guest_seed_and_reset(client, db):
    mint(db, GUEST_A)
    resp = await client.post("/api/platform/csrd/guest/seed", json={"financial_year": "FY2025"}, headers=_auth(GUEST_A))
    assert resp.status_code == 200
    body = resp.json()
    assert body["seeded_entries"] > 0
    assert body["seeded_iro"] == 4

    entries = await client.get("/api/platform/csrd/entries", params={"financial_year": "FY2025"}, headers=_auth(GUEST_A))
    assert entries.json()["count"] == body["seeded_entries"]
    iro = await client.get("/api/platform/csrd/materiality", params={"financial_year": "FY2025"}, headers=_auth(GUEST_A))
    assert iro.json()["count"] == 4
    assert any(r["material"] for r in iro.json()["iro"])

    resp = await client.post("/api/platform/csrd/guest/seed", json={"financial_year": "FY2025"}, headers=_auth(REAL_USER))
    assert resp.status_code == 403

    resp = await client.delete("/api/platform/csrd/guest/workspace", headers=_auth(GUEST_A))
    assert resp.status_code == 200
    assert db.tables["esrs_entries"] == []
    assert db.tables["esrs_materiality"] == []


@pytest.mark.asyncio
async def test_guest_submission_is_sandbox_only(client, db, settings):
    """Guests can run assured/attested/esef submission, but it never files."""
    mint(db, GUEST_A)
    await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [
                {"datapoint_id": _ESEF_NUM, "status": "reported", "value": 2140.0},
                {"datapoint_id": _ESEF_TXT, "status": "reported", "value": "Copied."},
            ],
        },
        headers=_auth(GUEST_A),
    )
    report = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "esef"},
        headers=_auth(GUEST_A),
    )
    assert report.status_code == 200
    report_id = report.json()["report_id"]

    await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={"status": "reasonable", "firm": "Sandbox Assurance LLP", "date": "2026-03-15"},
        headers=_auth(GUEST_A),
    )
    val = await client.post(f"/api/platform/csrd/reports/{report_id}/validate", headers=_auth(GUEST_A))
    assert val.status_code == 200 and val.json()["passed"] is True
    await client.post(
        f"/api/platform/csrd/reports/{report_id}/attestation",
        json={"signed_by": "Demo Auditor", "statement": "Sandbox sign-off."},
        headers=_auth(GUEST_A),
    )

    # the real OAM endpoint is configured AND production, but guests never touch it
    _, setter = settings
    setter(OAM_FILING_ENDPOINT="https://oam.example/filing", ENVIRONMENT="production")
    with patch(
        "urllib.request.urlopen",
        side_effect=AssertionError("guest submissions must never call the OAM"),
    ):
        resp = await client.post(f"/api/platform/csrd/reports/{report_id}/submit", json={}, headers=_auth(GUEST_A))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "sandboxed"
    assert body["channel"] == "guest_sandbox"

    # sandbox acknowledgement works for guests even in production
    ack = await client.post(f"/api/platform/csrd/reports/{report_id}/sandbox/ack", headers=_auth(GUEST_A))
    assert ack.status_code == 200
    assert ack.json()["channel"] == "sandbox"
    assert ack.json()["ack_ref"]

    assert len(db.tables["esrs_submissions"]) == 1
    assert db.tables["esrs_submissions"][0]["qes_key_id"] == "guest-sandbox"
    assert db.tables["esrs_submissions"][0]["submitted_by"] is None


@pytest.mark.asyncio
async def test_real_user_sandbox_ack_is_production_locked(client, settings):
    _, setter = settings
    setter(ENVIRONMENT="production")
    resp = await client.post("/api/platform/csrd/reports/whatever/sandbox/ack", headers=_auth(REAL_USER))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_guest_report_quota(client, db, settings):
    _, setter = settings
    setter(CSRD_GUEST_MAX_REPORTS=1)
    mint(db, GUEST_A)
    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "word"},
        headers=_auth(GUEST_A),
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "word"},
        headers=_auth(GUEST_A),
    )
    assert resp.status_code == 429

    # reset frees the quota
    await client.delete("/api/platform/csrd/guest/workspace", headers=_auth(GUEST_A))
    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "word"},
        headers=_auth(GUEST_A),
    )
    assert resp.status_code == 200
