"""BRSR value-chain partners API + persistence (migration v33).

Exercises brsr_value_chain.py against an in-memory Supabase fake: partner
scope/coverage on the >=2% rule and 75% cap, partner/entry upserts, and the
attributed state validation (transition + evidence rules).
"""

from __future__ import annotations

import uuid

import pytest

from app.brsr_value_chain import (
    AssuranceValidationError,
    upsert_entry,
    upsert_partner,
    value_chain_report,
)

ORG_ID = "org-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FY = "FY2025-26"


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, mode="read", payload=None, on_conflict=None):
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


class _Upsert:
    def __init__(self, rows, row, conflicts):
        self._rows = rows
        self._row = row
        self._conflicts = conflicts

    def execute(self):
        for existing in self._rows:
            if all(existing.get(c) == self._row.get(c) for c in self._conflicts):
                existing.update(
                    {k: v for k, v in self._row.items() if v is not None}
                )
                return _Resp([dict(existing)])
        saved = dict(self._row)
        saved.setdefault("id", f"id-{uuid.uuid4().hex[:12]}")
        self._rows.append(saved)
        return _Resp([dict(saved)])


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

    def upsert(self, row, on_conflict=None):
        conflicts = (on_conflict or "").split(",") if on_conflict else []
        return _Upsert(self._rows(), dict(row), conflicts)

    def update(self, payload):
        return _Query(self._rows(), mode="update", payload=payload)

    def delete(self):
        return _Query(self._rows(), mode="delete")


class FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


def _make_sb(partners=()):
    sb = FakeSupabase()
    for p in partners:
        upsert_partner(sb, ORG_ID, FY, p["partner_name"], p["direction"],
                       purchases_pct=p.get("purchases_pct"),
                       sales_pct=p.get("sales_pct"),
                       disclosed=p.get("disclosed", False))
    return sb


def test_upsert_partner_roundtrip_and_idempotency():
    sb = FakeSupabase()
    saved = upsert_partner(sb, ORG_ID, FY, "Acme Minerals", "upstream",
                           purchases_pct=30, disclosed=True)
    assert saved["partner_name"] == "Acme Minerals"
    assert saved["financial_year"] == FY
    assert saved["org_id"] == ORG_ID

    again = upsert_partner(sb, ORG_ID, FY, "Acme Minerals", "upstream",
                           purchases_pct=31)
    assert again["purchases_pct"] == 31
    rows = sb.store["value_chain_partners"]
    assert len(rows) == 1


def test_upsert_partner_validates_direction_and_range():
    sb = FakeSupabase()
    with pytest.raises(AssuranceValidationError):
        upsert_partner(sb, ORG_ID, FY, "X", "lateral")
    with pytest.raises(ValueError):
        upsert_partner(sb, ORG_ID, FY, "X", "upstream", purchases_pct=120)
    with pytest.raises(AssuranceValidationError):
        upsert_partner(sb, ORG_ID, FY, "   ", "upstream")


def test_value_chain_report_coverage():
    sb = _make_sb(
        [
            {"partner_name": "A", "direction": "upstream", "purchases_pct": 40,
             "disclosed": True},
            {"partner_name": "B", "direction": "upstream", "purchases_pct": 20},
            {"partner_name": "C", "direction": "downstream", "sales_pct": 55,
             "disclosed": True},
        ]
    )
    report = value_chain_report(sb, ORG_ID, FY)
    up = report["coverage_status"]["upstream"]
    down = report["coverage_status"]["downstream"]
    assert up["in_scope_partners"] == 2
    assert up["disclosed_pct"] == 40.0
    assert up["shortfall_to_cap_pct"] == 35.0
    assert up["pending_partners"] == 1
    assert down["disclosed_pct"] == 55.0
    assert down["pending_partners"] == 0
    assert report["partners_count"] == 3


def test_value_chain_report_rejects_bad_financial_year():
    sb = _make_sb()
    with pytest.raises(AssuranceValidationError):
        value_chain_report(sb, ORG_ID, "2025")


def test_entry_requires_value_chain_kpi():
    sb = _make_sb([{"partner_name": "A", "direction": "upstream",
                    "purchases_pct": 10}])
    partner_id = sb.store["value_chain_partners"][0]["id"]
    with pytest.raises(AssuranceValidationError):
        upsert_entry(sb, ORG_ID, FY, partner_id, "NOT-A-KPI", "limited",
                     provider_name="P")
    with pytest.raises(AssuranceValidationError):
        upsert_entry(sb, ORG_ID, FY, partner_id, "BRSC-99.99", "limited",
                     provider_name="P")


def test_entry_transition_rules():
    sb = _make_sb([{"partner_name": "A", "direction": "upstream",
                    "purchases_pct": 10}])
    partner_id = sb.store["value_chain_partners"][0]["id"]
    with pytest.raises(AssuranceValidationError):
        upsert_entry(sb, ORG_ID, FY, partner_id, "BRSC-1.1", "reasonable")
    ok = upsert_entry(sb, ORG_ID, FY, partner_id, "BRSC-1.1", "evidence")
    assert ok["assurance_state"] == "evidence"


def test_entry_requires_evidence_for_assured_state():
    sb = _make_sb([{"partner_name": "A", "direction": "upstream",
                    "purchases_pct": 10}])
    partner_id = sb.store["value_chain_partners"][0]["id"]
    upsert_entry(sb, ORG_ID, FY, partner_id, "BRSC-1.1", "evidence")
    with pytest.raises(AssuranceValidationError):
        upsert_entry(sb, ORG_ID, FY, partner_id, "BRSC-1.1", "limited")
    ok = upsert_entry(sb, ORG_ID, FY, partner_id, "BRSC-1.1", "limited",
                      evidence_id="doc-1")
    assert ok["assurance_state"] == "limited"


def test_entry_rejects_partner_of_other_org():
    sb = FakeSupabase()
    saved = upsert_partner(sb, "org-other", FY, "A", "upstream",
                           purchases_pct=10)
    with pytest.raises(AssuranceValidationError):
        upsert_entry(sb, ORG_ID, FY, saved["id"], "BRSC-1.1", "evidence")


def test_report_attributes_entries_to_partners():
    sb = _make_sb([{"partner_name": "A", "direction": "upstream",
                    "purchases_pct": 10, "disclosed": True}])
    partner_id = sb.store["value_chain_partners"][0]["id"]
    for kpi, state in (("BRSC-1.1", "evidence"), ("BRSC-1.1", "limited"),
                       ("BRSC-1.1", "reasonable")):
        upsert_entry(sb, ORG_ID, FY, partner_id, kpi, state,
                     provider_name="Assure Co")
    report = value_chain_report(sb, ORG_ID, FY)
    partner = report["partners"][0]
    assert partner["kpis_assured"] >= 1
    assert partner["in_scope"] is True
    assert partner["disclosed"] is True
    states = {k["kpi_code"]: k["state"] for k in partner["kpis"]}
    assert states.get("BRSC-1.1") == "reasonable"
