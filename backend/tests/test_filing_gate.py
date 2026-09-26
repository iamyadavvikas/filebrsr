"""BRSR Core filing gate (BRSR-Core 4) — end-to-end on the filing endpoints.

Assurance coverage (migration v32, brsr_core_assurance.py) blocks XBRL XML and
SEBI PDF exports with 409 when the org's market-cap tier has uncovered KPI gaps
and enforce_assurance is requested. validate stays a read-only report.
"""

import asyncio

import pytest
from fastapi import HTTPException

from app.brsr_core import get_core_kpis
from app.sebi_pdf_filing import export_sebi_pdf
from app.xbrl_filing import export_xbrl_xml, validate_xbrl_readiness

USER_ID = "user-11111111-2222-3333-4444-555555555555"
ORG_ID = "org-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FY = "FY2024-25"

_GATE_CODES = [k["code"] for k in get_core_kpis()]  # all 43 gate at entity level


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, mode="read", payload=None):
        self._table = table
        self._mode = mode
        self._payload = payload
        self._filters = []

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, col, desc=False):
        return self

    def limit(self, n):
        return self

    def execute(self):
        tab = self._table
        if self._mode == "read":
            rows = (
                [r for r in tab if all(r.get(c) == v for c, v in self._filters)]
                if self._filters
                else list(tab)
            )
            return _Resp(rows)
        if self._mode == "update":
            updated = []
            for row in tab:
                if all(row.get(c) == v for c, v in self._filters):
                    merged = {**row, **self._payload}
                    tab[tab.index(row)] = merged
                    updated.append(merged)
            return _Resp(updated)
        killed = [r for r in tab if all(r.get(c) == v for c, v in self._filters)]
        for r in killed:
            tab.remove(r)
        return _Resp(killed)


class _Table:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def _rows(self):
        return self._store.setdefault(self._name, [])

    def select(self, *_a, **_k):
        return _Query(self._rows())

    def insert(self, row):
        self._rows().append(dict(row))
        return _Resp([dict(row)])

    def update(self, payload):
        return _Query(self._rows(), mode="update", payload=payload)

    def delete(self):
        return _Query(self._rows(), mode="delete")


class FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


def _profile(reporting_category="Top 1000 (BRSR Full)", org_id=ORG_ID):
    return {
        "id": USER_ID,
        "org_id": org_id,
        "reporting_category": reporting_category,
        "company_name": "Acme Industries Pvt Ltd",
        "cin": "L11111MH2020PLC000000",
    }


def _make_sb(assured_codes=(), entries=(("C.P1.E.1", "Test"),), reporting_category="Top 1000 (BRSR Full)", org_id=ORG_ID):
    sb = FakeSupabase()
    sb.table("profiles").insert(_profile(reporting_category, org_id=org_id))
    for dp_id, value in entries:
        sb.table("brsr_entries").insert(
            {"user_id": USER_ID, "financial_year": FY, "datapoint_id": dp_id, "value": value}
        )
    for code in assured_codes:
        sb.table("brsr_core_assurance").insert(
            {
                "org_id": ORG_ID,
                "financial_year": FY,
                "kpi_code": code,
                "assurance_state": "limited",
                "provider_name": "Deloitte Haskins & Sells LLP",
            }
        )
    return sb


@pytest.fixture
def fake_env(monkeypatch):
    sb = _make_sb()

    async def _user_id(_auth):
        return USER_ID

    monkeypatch.setattr("app.xbrl_filing.get_user_id", _user_id)
    monkeypatch.setattr("app.sebi_pdf_filing.get_user_id", _user_id)
    monkeypatch.setattr("app.xbrl_filing.get_supabase_admin", lambda: sb)
    monkeypatch.setattr("app.sebi_pdf_filing.get_supabase_admin", lambda: sb)

    def set_sb(other):
        monkeypatch.setattr("app.xbrl_filing.get_supabase_admin", lambda: other)
        monkeypatch.setattr("app.sebi_pdf_filing.get_supabase_admin", lambda: other)

    return {"sb": sb, "set_sb": set_sb}


def test_xbrl_export_blocks_on_assurance_gaps(fake_env):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            export_xbrl_xml(financial_year=FY, enforce_assurance=True, authorization="Bearer x")
        )
    assert exc.value.status_code == 409
    assert "BRSC-" in exc.value.detail


def test_sebi_pdf_blocks_on_assurance_gaps(fake_env):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            export_sebi_pdf(financial_year=FY, enforce_assurance=True, authorization="Bearer x")
        )
    assert exc.value.status_code == 409
    assert "BRSC-" in exc.value.detail


def test_xbrl_export_passes_when_scope_covered(fake_env):
    sb = _make_sb(assured_codes=_GATE_CODES)
    fake_env["set_sb"](sb)
    res = asyncio.run(
        export_xbrl_xml(financial_year=FY, enforce_assurance=True, authorization="Bearer x")
    )
    assert res.status_code == 200
    assert res.headers["X-FileBRSR-Assurance-Ready"] == "1"


def test_validate_reports_assurance_blockers_without_404(fake_env):
    payload = asyncio.run(
        validate_xbrl_readiness(financial_year=FY, authorization="Bearer x")
    )
    assurance = payload["assurance"]
    assert assurance["applicable"] is True
    assert assurance["tier"] == "top_1000"
    assert assurance["ready"] is False
    assert assurance["blocker_count"] == len(_GATE_CODES)
    assert assurance["required_mode"] == "limited"


def test_validate_ready_when_covered(fake_env):
    sb = _make_sb(assured_codes=_GATE_CODES)
    fake_env["set_sb"](sb)
    payload = asyncio.run(
        validate_xbrl_readiness(financial_year=FY, authorization="Bearer x")
    )
    assert payload["assurance"]["ready"] is True
    assert payload["assurance"]["blockers"] == []


def test_gate_not_applicable_when_no_org(fake_env):
    sb = _make_sb(reporting_category="Top 1000 (BRSR Full)", org_id=None)
    fake_env["set_sb"](sb)
    payload = asyncio.run(
        validate_xbrl_readiness(financial_year=FY, authorization="Bearer x")
    )
    assert payload["assurance"]["applicable"] is False
    assert payload["assurance"]["ready"] is True
    assert payload["assurance"]["blocker_count"] == 0
