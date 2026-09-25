"""CSRD / ESRS platform router tests (migration v23).

Acceptance:
- registry endpoints return the full ESRS Set 1 encoding (standards,
  paginated/searchable datapoints, whole-registry coverage statics);
- entry CRUD is org-scoped: upserts against (org, year, datapoint), rejects
  unknown datapoint ids, and refuses writes/reads across organisations;
- the gap analysis computes per-standard readiness (handled vs remaining);
- the double-materiality register stores IROs and auto-derives the material
  flag from the 1-5 scores (threshold 3.0);
- Word/PDF statement export records an immutable snapshot (sha256, size,
  coverage) and streams a regenerable artifact with the right content type.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.esrs_datapoints import ESRS_DATAPOINTS

USER_ID = "user-csrd-1"
OTHER_USER = "user-csrd-2"
ORG_ID = "org-csrd-1"
OTHER_ORG = "org-csrd-2"


# ─── stateful fake supabase (mirrors test_assurance_persistence.py) ─────────

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

    def single(self):
        self._single_mode = "exact"
        return self

    def insert(self, rows):
        rows = rows if isinstance(rows, list) else [rows]
        self._op = ("insert", rows)
        return self

    def upsert(self, rows, on_conflict=None):
        self._op = ("upsert", rows, on_conflict)
        return self

    def update(self, patch):
        self._op = ("update", patch)
        return self

    def delete(self):
        self._op = ("delete",)
        return self

    def _matched(self) -> list[dict]:
        rows = [r for r in self._store if all(r.get(c) == v for c, v in self._filters)]
        if self._order:
            col, desc = self._order
            rows = sorted(rows, key=lambda r: r.get(col) or "", reverse=desc)
        return rows

    def execute(self):
        op = self._op
        if op is None:  # plain select
            rows = self._matched()
            if self._single_mode == "maybe":
                return _Resp(rows[0] if rows else None)
            return _Resp(rows)
        kind, *rest = op
        if kind == "insert":
            rows = rest[0]
            for r in rows:
                r.setdefault("id", str(uuid.uuid4()))
                r.setdefault("created_at", "2026-01-01T00:00:00Z")
                r.setdefault("updated_at", "2026-01-01T00:00:00Z")
                self._store.append(r)
            return _Resp(rows)
        if kind == "upsert":
            rows, on_conflict = rest
            rows = rows if isinstance(rows, list) else [rows]
            keys = [k.strip() for k in (on_conflict or "id").split(",") if k.strip()]
            written = []
            for r in rows:
                match = next(
                    (x for x in self._store if all(x[k] == r.get(k) for k in keys)),
                    None,
                )
                if match is None:
                    r.setdefault("id", str(uuid.uuid4()))
                    r.setdefault("created_at", "2026-01-01T00:00:00Z")
                    r.setdefault("updated_at", "2026-01-01T00:00:00Z")
                    self._store.append(r)
                    written.append(r)
                else:
                    match.update({k: v for k, v in r.items() if v is not None and k != "id"})
                    match["updated_at"] = "2026-01-02T00:00:00Z"
                    written.append(match)
            return _Resp(written)
        if kind == "update":
            patch = rest[0]
            matched = self._matched()
            for r in matched:
                r.update({k: v for k, v in patch.items() if k != "id"})
                r["updated_at"] = "2026-01-02T00:00:00Z"
            return _Resp(matched)
        if kind == "delete":
            matched = self._matched()
            for r in matched:
                self._store.remove(r)
            return _Resp(matched)
        raise AssertionError(f"unhandled op {kind}")


class _FakeDB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "org_members": [
                {"org_id": ORG_ID, "user_id": USER_ID, "role": "owner"},
            ],
            "organization_members": [
                {"org_id": ORG_ID, "user_id": USER_ID, "role": "owner"},
            ],
            "profiles": [
                {"id": USER_ID, "org_id": ORG_ID, "plan": "enterprise"},
                {"id": OTHER_USER, "org_id": OTHER_ORG, "plan": "free"},
            ],
            "esrs_entries": [],
            "esrs_materiality": [],
            "esrs_reports": [],
        }

    def table(self, name: str) -> _Query:
        if name not in self.tables:
            self.tables[name] = []
        return _Query(self.tables[name])


@pytest.fixture
def db():
    return _FakeDB()


@pytest.fixture
def client(db):
    import app.router_csrd as csrd
    from app.main import app

    app.dependency_overrides.clear()
    with patch.object(csrd, "get_supabase_admin", return_value=db):
        transport = ASGITransport(app=app)
        yield AsyncClient(transport=transport, base_url="http://test")


def _auth(user: str = USER_ID) -> dict:
    return {"authorization": f"Bearer {user}"}


# ─── registry ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_standards_endpoint(client):
    resp = await client.get("/api/platform/csrd/standards", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_datapoints"] == len(ESRS_DATAPOINTS) == 664
    assert len(body["standards"]) == 11
    assert body["standards"][0]["standard"] == "2"
    assert body["standards"][0]["datapoints"] > 100


@pytest.mark.asyncio
async def test_registry_pagination_and_filters(client):
    resp = await client.get(
        "/api/platform/csrd/registry", params={"limit": 20, "offset": 0}, headers=_auth()
    )
    body = resp.json()
    assert body["total"] == 664
    assert len(body["datapoints"]) == 20

    resp = await client.get(
        "/api/platform/csrd/registry", params={"standard": "E1"}, headers=_auth()
    )
    body = resp.json()
    assert body["total"] == 104
    assert all(d["standard"] == "E1" for d in body["datapoints"])

    resp = await client.get(
        "/api/platform/csrd/registry", params={"q": "ghg"}, headers=_auth()
    )
    assert resp.status_code == 200
    assert resp.json()["total"] > 0


@pytest.mark.asyncio
async def test_registry_is_public(client):
    """Reference data (standards, registry, coverage) needs no auth."""
    for path in (
        "/api/platform/csrd/standards",
        "/api/platform/csrd/registry",
        "/api/platform/csrd/coverage",
    ):
        resp = await client.get(path)
        assert resp.status_code == 200, path


@pytest.mark.asyncio
async def test_coverage_endpoint(client):
    resp = await client.get("/api/platform/csrd/coverage", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_datapoints"] == 664
    assert len(body["standards"]) == 11
    assert "SFDR" in body["derived_from_eu_legislation"]


# ─── entries + gap analysis ────────────────────────────────────────────────

_E1_DP = [d["id"] for d in ESRS_DATAPOINTS if d["standard"] == "E1"]


@pytest.mark.asyncio
async def test_upsert_and_list_entries(client, db):
    payload = {
        "financial_year": "FY2025",
        "entries": [
            {"datapoint_id": _E1_DP[0], "status": "reported", "value": "tCO2e"},
            {"datapoint_id": _E1_DP[1], "status": "in_progress", "notes": "collect data"},
        ],
    }
    resp = await client.post("/api/platform/csrd/entries", json=payload, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["saved"] == 2

    resp = await client.get(
        "/api/platform/csrd/entries",
        params={"financial_year": "FY2025", "standard": "E1"},
        headers=_auth(),
    )
    body = resp.json()
    assert body["org_id"] == ORG_ID
    assert body["count"] == 2
    entry_id = next(e["id"] for e in body["entries"] if e["datapoint_id"] == _E1_DP[0])

    # update one row, then upsert again -> conflict key keeps one row per datapoint
    resp = await client.put(
        f"/api/platform/csrd/entries/{entry_id}",
        json={"status": "assessed", "value": "updated"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [{"datapoint_id": _E1_DP[0], "status": "reported"}],
        },
        headers=_auth(),
    )
    assert resp.json()["saved"] == 1
    resp = await client.get(
        "/api/platform/csrd/entries",
        params={"financial_year": "FY2025", "standard": "E1"},
        headers=_auth(),
    )
    assert resp.json()["count"] == 2


@pytest.mark.asyncio
async def test_upsert_rejects_unknown_datapoint(client):
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [{"datapoint_id": "E9-99.999", "status": "reported"}],
        },
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "Unknown datapoint" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_entries_are_org_scoped(client):
    payload = {
        "financial_year": "FY2025",
        "entries": [{"datapoint_id": _E1_DP[0], "status": "reported"}],
    }
    await client.post("/api/platform/csrd/entries", json=payload, headers=_auth())

    # outsider cannot read this org's entries even via explicit org_id
    resp = await client.get(
        "/api/platform/csrd/entries",
        params={"org_id": ORG_ID, "financial_year": "FY2025"},
        headers=_auth(OTHER_USER),
    )
    assert resp.status_code == 403

    # outsider cannot save into this org either
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={**payload, "org_id": ORG_ID},
        headers=_auth(OTHER_USER),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_entry(client, db):
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [{"datapoint_id": _E1_DP[0], "status": "reported"}],
        },
        headers=_auth(),
    )
    entry_id = resp.json()["entries"][0]["id"]
    resp = await client.delete(f"/api/platform/csrd/entries/{entry_id}", headers=_auth())
    assert resp.status_code == 200
    assert db.tables["esrs_entries"] == []


@pytest.mark.asyncio
async def test_gap_analysis_readiness(client, db):
    # seed: E2 fully reported, half of E1 reported, rest untouched
    entries = [
        {"datapoint_id": d["id"], "status": "reported"}
        for d in ESRS_DATAPOINTS
        if d["standard"] == "E2" or d["id"] in _E1_DP[: len(_E1_DP) // 2]
    ]
    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": "FY2025", "entries": entries},
        headers=_auth(),
    )
    resp = await client.get(
        "/api/platform/csrd/gap-analysis",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.json()
    # FY2025 excludes the 12 FY2026 phase-in datapoints from the 664-registry
    assert body["registry_datapoints"] == 664
    assert body["total_datapoints"] == 652
    assert body["has_material_iro"] is False
    e1 = next(s for s in body["standards"] if s["standard"] == "E1")
    e2 = next(s for s in body["standards"] if s["standard"] == "E2")
    assert e2["handled"] == e2["datapoints"]  # all E2 in scope and reported
    assert e1["handled"] <= len(_E1_DP) // 2
    assert body["effective_gap"] == body["total_datapoints"] - body["handled"]
    assert sum(s["handled"] for s in body["standards"]) == body["handled"]


@pytest.mark.asyncio
async def test_phase_in_scopes_the_gap_by_reporting_year(client, db):
    """Phase-in datapoints count only once their FY applies (displayed == computed)."""
    dp = "E4.E4-1.15"  # gated to FY2025 -> out of scope for FY2024 and before
    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": "FY2024", "entries": [{"datapoint_id": dp, "status": "reported"}]},
        headers=_auth(),
    )
    await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": "FY2025", "entries": [{"datapoint_id": dp, "status": "reported"}]},
        headers=_auth(),
    )

    # FY2024 scope: 664 - 3 (FY2025-gated) - 12 (FY2026-gated) = 649
    for fy, total, handled in (("FY2024", 649, 0), ("FY2025", 652, 1)):
        resp = await client.get(
            "/api/platform/csrd/gap-analysis", params={"financial_year": fy}, headers=_auth()
        )
        body = resp.json()
        assert body["total_datapoints"] == total, fy
        e4 = next(s for s in body["standards"] if s["standard"] == "E4")
        assert e4["handled"] == handled, fy


@pytest.mark.asyncio
async def test_not_material_requires_materiality_basis(client, db):
    """not_material only closes a gap once the register backs it."""
    dp = _E1_DP[0]
    resp = await client.post(
        "/api/platform/csrd/materiality",
        json={
            "financial_year": "FY2025",
            "iro_type": "impact",
            "standard": "E1",
            "title": "Material climate impact",
            "impact_materiality": 4.2,
            "financial_materiality": 3.5,
        },
        headers=_auth(),
    )
    iro_id = resp.json()["iro"]["id"]

    entry = await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [{"datapoint_id": dp, "status": "not_material"}],
        },
        headers=_auth(),
    )
    entry_id = entry.json()["entries"][0]["id"]

    gap = await client.get(
        "/api/platform/csrd/gap-analysis", params={"financial_year": "FY2025"}, headers=_auth()
    )
    e1 = next(s for s in gap.json()["standards"] if s["standard"] == "E1")
    assert e1["handled"] == 0  # not_material without an IRO doesn't close the gap

    # linking the materiality basis closes it
    await client.put(
        f"/api/platform/csrd/entries/{entry_id}", json={"materiality_id": iro_id}, headers=_auth()
    )
    gap = await client.get(
        "/api/platform/csrd/gap-analysis", params={"financial_year": "FY2025"}, headers=_auth()
    )
    e1 = next(s for s in gap.json()["standards"] if s["standard"] == "E1")
    assert e1["handled"] == 1

    # a year with no material IRO at all accepts not_material without a link
    await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2024",
            "entries": [{"datapoint_id": _E1_DP[1], "status": "not_material"}],
        },
        headers=_auth(),
    )
    gap = await client.get(
        "/api/platform/csrd/gap-analysis", params={"financial_year": "FY2024"}, headers=_auth()
    )
    e1 = next(s for s in gap.json()["standards"] if s["standard"] == "E1")
    assert e1["handled"] == 1


# ─── double materiality ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_iro_crud_and_material_threshold(client, db):
    payload = {
        "financial_year": "FY2025",
        "iro_type": "impact",
        "standard": "E1",
        "title": "Climate impact from operations",
        "severity": 4,
        "likelihood": 5,
        "impact_materiality": 4.2,
        "financial_materiality": 1.1,
    }
    resp = await client.post("/api/platform/csrd/materiality", json=payload, headers=_auth())
    assert resp.status_code == 200
    iro = resp.json()["iro"]
    assert iro["material"] is True  # impact 4.2 >= 3.0
    iro_id = iro["id"]

    # non-material: both below threshold
    resp = await client.post(
        "/api/platform/csrd/materiality",
        json={
            "financial_year": "FY2025",
            "iro_type": "opportunity",
            "standard": "E2",
            "title": "Minor",
            "impact_materiality": 1.0,
            "financial_materiality": 2.0,
        },
        headers=_auth(),
    )
    assert resp.json()["iro"]["material"] is False

    # raise one score -> material flips
    resp = await client.put(
        f"/api/platform/csrd/materiality/{iro_id}",
        json={"financial_materiality": 4.8},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["iro"]["material"] is True

    resp = await client.get(
        "/api/platform/csrd/materiality",
        params={"financial_year": "FY2025", "material_only": True},
        headers=_auth(),
    )
    body = resp.json()
    assert body["count"] == 1
    assert body["iro"][0]["id"] == iro_id


@pytest.mark.asyncio
async def test_delete_iro_detaches_linked_entries(client, db):
    resp = await client.post(
        "/api/platform/csrd/materiality",
        json={
            "financial_year": "FY2025",
            "iro_type": "impact",
            "standard": "E1",
            "title": "Ships that unlink",
            "impact_materiality": 4.0,
        },
        headers=_auth(),
    )
    iro_id = resp.json()["iro"]["id"]
    await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [
                {"datapoint_id": _E1_DP[0], "status": "not_material", "materiality_id": iro_id}
            ],
        },
        headers=_auth(),
    )
    assert db.tables["esrs_entries"][0]["materiality_id"] == iro_id

    resp = await client.delete(f"/api/platform/csrd/materiality/{iro_id}", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["deleted"] == iro_id
    assert db.tables["esrs_materiality"] == []
    assert db.tables["esrs_entries"][0]["materiality_id"] is None

    resp = await client.delete("/api/platform/csrd/materiality/does-not-exist", headers=_auth())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scope_endpoints_and_value_chain_filter(client, db):
    scope = await client.get("/api/platform/csrd/scope", headers=_auth())
    assert scope.status_code == 200
    assert scope.json()["value_chain_scope"] == ["own_operations", "upstream", "downstream"]

    bad = await client.put(
        "/api/platform/csrd/scope", json={"value_chain_scope": ["own_operations", "mars"]},
        headers=_auth(),
    )
    assert bad.status_code == 400

    ok = await client.put(
        "/api/platform/csrd/scope", json={"value_chain_scope": ["own_operations"]},
        headers=_auth(),
    )
    assert ok.status_code == 200
    scope = await client.get("/api/platform/csrd/scope", headers=_auth())
    assert scope.json()["value_chain_scope"] == ["own_operations"]

    # value-chain registry filter: every row is "all", so boundaries keep all rows
    reg = await client.get(
        "/api/platform/csrd/registry", params={"value_chain": "downstream"}, headers=_auth()
    )
    assert reg.status_code == 200
    assert reg.json()["total"] == 664

    # scoped gap analysis matches the full-chain baseline when data is all-"all"
    gap = await client.get(
        "/api/platform/csrd/gap-analysis",
        params={"financial_year": "FY2025", "value_chain": "own_operations"},
        headers=_auth(),
    )
    assert gap.status_code == 200
    assert gap.json()["total_datapoints"] == 652
    assert gap.json()["value_chain_scope"] == ["own_operations"]


# ─── report export ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_generation_and_download(client, db):
    await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [{"datapoint_id": _E1_DP[0], "status": "reported", "value": 120.5}],
        },
        headers=_auth(),
    )
    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "word"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.json()
    report_id = body["report_id"]
    assert body["datapoints_covered"] == 1
    assert body["coverage_pct"] == pytest.approx(round(1 / 652 * 100, 2))
    assert body["file_size_bytes"] > 0

    download = await client.get(
        f"/api/platform/csrd/reports/{report_id}/download", headers=_auth()
    )
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )
    assert len(download.content) == body["file_size_bytes"]

    listed = await client.get(
        "/api/platform/csrd/reports",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    assert listed.json()["count"] == 1
    assert listed.json()["reports"][0]["file_sha256"]


@pytest.mark.asyncio
async def test_pdf_report_type(client):
    await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "pdf"},
        headers=_auth(),
    )
    listed = await client.get(
        "/api/platform/csrd/reports",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    reports = listed.json()["reports"]
    assert reports and reports[0]["report_type"] == "pdf"
    download = await client.get(
        f"/api/platform/csrd/reports/{reports[0]['id']}/download", headers=_auth()
    )
    assert download.status_code == 200
    assert download.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_report_rejects_bad_format(client):
    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "xlsx"},
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "esef" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_report_coverage_is_phase_in_aware(client, db):
    """Report coverage uses the in-scope (phase-filtered) total, not 664."""
    for fy in ("FY2025", "FY2026"):
        await client.post(
            "/api/platform/csrd/entries",
            json={
                "financial_year": fy,
                "entries": [{"datapoint_id": _E1_DP[0], "status": "reported"}],
            },
            headers=_auth(),
        )

    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "word"},
        headers=_auth(),
    )
    assert resp.json()["coverage_pct"] == pytest.approx(round(1 / 652 * 100, 2))

    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2026", "format": "word"},
        headers=_auth(),
    )
    assert resp.json()["coverage_pct"] == pytest.approx(round(1 / 664 * 100, 2))


@pytest.mark.asyncio
async def test_report_excludes_unsubstantiated_not_material(client, db):
    """A material IRO in the register makes unlinked not-material shrink coverage."""
    resp = await client.post(
        "/api/platform/csrd/materiality",
        json={
            "financial_year": "FY2025",
            "iro_type": "impact",
            "standard": "E1",
            "title": "Material climate risk",
            "impact_materiality": 4.0,
        },
        headers=_auth(),
    )
    iro_id = resp.json()["iro"]["id"]
    await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [{"datapoint_id": _E1_DP[0], "status": "not_material"}],
        },
        headers=_auth(),
    )

    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "word"},
        headers=_auth(),
    )
    assert resp.json()["datapoints_covered"] == 0

    await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [
                {"datapoint_id": _E1_DP[0], "status": "not_material", "materiality_id": iro_id}
            ],
        },
        headers=_auth(),
    )
    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "word"},
        headers=_auth(),
    )
    assert resp.json()["datapoints_covered"] == 1


@pytest.mark.asyncio
async def test_registry_search_combines_with_filters(client):
    """q narrows the already-filtered list instead of replacing it."""
    resp = await client.get(
        "/api/platform/csrd/registry", params={"q": "pollution", "phase_in": "FY2026"}, headers=_auth()
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] > 0
    assert all(d["phase_in"] == "FY2026" for d in body["datapoints"])

    resp = await client.get(
        "/api/platform/csrd/registry", params={"q": "financial", "standard": "E1"}, headers=_auth()
    )
    body = resp.json()
    assert body["total"] > 0
    assert all(d["standard"] == "E1" for d in body["datapoints"])


@pytest.mark.asyncio
async def test_upsert_rejects_invalid_status(client):
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [{"datapoint_id": _E1_DP[0], "status": "shipped"}],
        },
        headers=_auth(),
    )
    assert resp.status_code == 400
    assert "Invalid status" in resp.json()["detail"]


# ─── ESEF single-file export, assurance gate, OAM submission (v25) ─────────

_ESEF_NUM = "E1.E1-6.44"
_ESEF_TXT = "ESRS2.BP-1.3"


async def _mk_esef_report(client, value=_ESEF_NUM):
    await client.post(
        "/api/platform/csrd/entries",
        json={
            "financial_year": "FY2025",
            "entries": [
                {"datapoint_id": _ESEF_NUM, "status": "reported", "value": 2140.0},
                {"datapoint_id": _ESEF_TXT, "status": "reported", "value": "Transition plan covers Scopes 1-3."},
            ],
        },
        headers=_auth(),
    )
    resp = await client.post(
        "/api/platform/csrd/reports",
        json={"financial_year": "FY2025", "format": "esef"},
        headers=_auth(),
    )
    assert resp.status_code == 200
    return resp.json()["report_id"]


@pytest.mark.asyncio
async def test_esef_report_generation_and_download(client, db):
    """ESEF export is well-formed XHTML with inline-XBRL facts + schemaRef."""
    import xml.dom.minidom as minidom

    report_id = await _mk_esef_report(client)
    listed = await client.get(
        "/api/platform/csrd/reports",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    reports = listed.json()["reports"]
    assert reports and reports[0]["report_type"] == "esef"

    download = await client.get(
        f"/api/platform/csrd/reports/{report_id}/download", headers=_auth()
    )
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/xhtml+xml"
    body = download.content.decode("utf-8")
    minidom.parseString(body)  # must be XML-serializable XHTML
    assert "<ix:header" in body
    assert 'xlink:href="https://xbrl.efrag.org/taxonomy/esrs/2023-12-22/esrs_all.xsd"' in body
    assert "<ix:nonFraction" in body  # numeric GHG fact tagged
    assert "<ix:nonNumeric" in body  # text fact tagged


@pytest.mark.asyncio
async def test_esef_report_has_concept_tags_for_numeric_and_text(client):
    download = await client.get(
        f"/api/platform/csrd/reports/{await _mk_esef_report(client)}/download",
        headers=_auth(),
    )
    body = download.content.decode("utf-8")
    assert 'name="esrs:GrossGreenhouseGasEmissions"' in body
    assert 'name="esrs:DisclosureOfExtentToWhichSustainabilityStatementCoversUpstreamAndDownstreamValueChainExplanatory"' in body


@pytest.mark.asyncio
async def test_submission_requires_assurance(client):
    report_id = await _mk_esef_report(client)
    resp = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={},
        headers=_auth(),
    )
    assert resp.status_code == 409
    assert "assurance" in resp.json()["detail"].lower()


async def _mk_validated_report(client) -> str:
    """ESEF report with a limited assurance opinion and a passing validation."""
    report_id = await _mk_esef_report(client)
    await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={"status": "limited", "firm": "B4 Assurance LLP", "date": "2026-03-15", "statement": "Fairly presented."},
        headers=_auth(),
    )
    resp = await client.post(f"/api/platform/csrd/reports/{report_id}/validate", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["passed"] is True
    return report_id


@pytest.mark.asyncio
async def test_validate_endpoint_persists_pass(client, db):
    report_id = await _mk_esef_report(client)
    await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={"status": "limited"},
        headers=_auth(),
    )
    resp = await client.post(f"/api/platform/csrd/reports/{report_id}/validate", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] is True
    assert body["errors"] == []
    listed = await client.get(
        "/api/platform/csrd/reports",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    row = next(r for r in listed.json()["reports"] if r["id"] == report_id)
    assert row["validation_status"] == "pass"
    assert row["validation_summary"]["passed"] is True


@pytest.mark.asyncio
async def test_validate_without_assurance_fails(client):
    """Pre-flight validation reflects that filing is not possible without assurance."""
    report_id = await _mk_esef_report(client)
    resp = await client.post(f"/api/platform/csrd/reports/{report_id}/validate", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] is False
    assert any(e["code"] == "assurance_missing" for e in body["errors"])


@pytest.mark.asyncio
async def test_submit_requires_validation_pass(client):
    """Assurance alone is not enough — the ESEF file must pass validation."""
    report_id = await _mk_esef_report(client)
    await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={"status": "limited"},
        headers=_auth(),
    )
    resp = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "REF"},
        headers=_auth(),
    )
    assert resp.status_code == 409
    assert "validation" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assurance_and_submission_flow(client, db):
    report_id = await _mk_esef_report(client)

    bad = await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={"status": "comprehensive"},
        headers=_auth(),
    )
    assert bad.status_code == 400

    resp = await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={
            "status": "limited",
            "firm": "B4 Assurance LLP",
            "date": "2026-03-15",
            "statement": "The ESRS sustainability statement is fairly presented.",
        },
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["assurance"] == "limited"

    # validation gate blocks submission before /validate runs
    blocked = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "CSRD-FY2025-ACME"},
        headers=_auth(),
    )
    assert blocked.status_code == 409
    assert "validation" in blocked.json()["detail"].lower()

    vr = await client.post(
        f"/api/platform/csrd/reports/{report_id}/validate",
        headers=_auth(),
    )
    assert vr.status_code == 200 and vr.json()["passed"] is True

    sub = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "CSRD-FY2025-ACME"},
        headers=_auth(),
    )
    assert sub.status_code == 200
    body = sub.json()
    assert body["status"] == "queued_local"
    assert body["submission_ref"] == "CSRD-FY2025-ACME"
    assert body["manifest_sha256"]

    listed = await client.get(
        "/api/platform/csrd/submissions",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    assert listed.json()["count"] == 1
    sub_row = listed.json()["submissions"][0]
    assert sub_row["report_id"] == report_id
    assert sub_row["status"] == "queued_local"

    # download reflects the stored assurance opinion
    download = await client.get(
        f"/api/platform/csrd/reports/{report_id}/download", headers=_auth()
    )
    assert download.status_code == 200
    assert "limited assurance" in download.content.decode("utf-8").lower()


@pytest.mark.asyncio
async def test_submit_is_idempotent(client, db):
    report_id = await _mk_validated_report(client)
    first = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "REF-X"},
        headers=_auth(),
    )
    assert first.status_code == 200
    assert first.json()["already_submitted"] is False
    second = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "REF-X"},
        headers=_auth(),
    )
    assert second.status_code == 200
    # queued (webhook endpoint unset) → not yet at the OAM, so no re-submit marker
    assert second.json()["already_submitted"] is False
    assert second.json()["submission_id"] == first.json()["submission_id"]
    assert second.json()["submission_ref"] == "REF-X"
    listed = await client.get(
        "/api/platform/csrd/submissions",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    assert listed.json()["count"] == 1


@pytest.mark.asyncio
async def test_submit_retries_webhook_failure(client, db, monkeypatch):
    """A failed webhook marks the submission and bumps retry_count; a later
    successful attempt flips status to submitted without creating a new row."""
    from app import router_csrd
    from app.config import Settings

    report_id = await _mk_validated_report(client)
    settings = Settings(
        SUPABASE_URL="http://fake", SUPABASE_SERVICE_KEY="k", OAM_FILING_ENDPOINT="https://oam.example/filing"
    )
    monkeypatch.setattr(router_csrd, "get_settings", lambda: settings)

    import urllib.request

    def _boom(_url, data=None, timeout=None, headers=None):
        raise ConnectionError("regulator down")

    def _ok(_url, data=None, timeout=None, headers=None):
        class Resp:
            def read(self):
                return b"ref-ok"

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        return Resp()

    calls = {"n": 0}

    def _flaky(url, **kw):
        calls["n"] += 1
        return _boom(url, **kw) if calls["n"] == 1 else _ok(url, **kw)

    monkeypatch.setattr(urllib.request, "urlopen", _flaky)
    first = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "REF-Y"},
        headers=_auth(),
    )
    assert first.status_code == 200
    assert first.json()["status"] == "webhook_failed:ConnectionError"

    ok = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "REF-Y"},
        headers=_auth(),
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "submitted"
    assert ok.json()["submission_ref"] == "ref-ok"
    assert ok.json()["submission_id"] == first.json()["submission_id"]
    listed = await client.get(
        "/api/platform/csrd/submissions",
        params={"financial_year": "FY2025"},
        headers=_auth(),
    )
    assert listed.json()["count"] == 1
    assert listed.json()["submissions"][0]["retry_count"] == 1
    assert listed.json()["submissions"][0]["last_error"] is None


@pytest.mark.asyncio
async def test_not_ready_report_409s_on_submission_and_assurance(client, db):
    """Assurance/submission both 409 when the report is not ``ready``."""
    report_id = await _mk_esef_report(client)
    await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={"status": "limited"},
        headers=_auth(),
    )
    row = next(r for r in db.tables["esrs_reports"] if r["id"] == report_id)
    row["status"] = "archived"
    resp = await client.post(
        f"/api/platform/csrd/reports/{report_id}/submit",
        json={"filing_ref": "x"},
        headers=_auth(),
    )
    assert resp.status_code == 409
    resp = await client.post(
        f"/api/platform/csrd/reports/{report_id}/assurance",
        json={"status": "reasonable"},
        headers=_auth(),
    )
    assert resp.status_code == 409
