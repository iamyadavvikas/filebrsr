"""BRSR Core assurance tracking (migration v32, brsr_core_assurance.py).

Acceptance:
- Assurance must escalate unassured -> evidence -> limited -> reasonable; skips
  and regressions are rejected by the transition matrix.
- A limited/reasonable claim requires evidence_id or a named provider.
- Unknown BRSC codes and malformed financial years are rejected.
- Coverage reports committed vs required mode per market-cap tier (phase-in).
"""

from __future__ import annotations

import pytest

from app.brsr_core import (
    ASSURANCE_PHASEIN,
    DATAPOINT_TO_BRSC,
    get_core_kpis,
    kpi_required_mode,
)
from app.brsr_core_assurance import (
    AssuranceValidationError,
    assurance_gate,
    coverage,
    get_assurance,
    upsert_assurance,
    validate_financial_year,
)
from app.brsr_datapoints import BRSR_DATAPOINTS

_ORG = "org-11111111-2222-3333-4444-555555555555"
_FY = "FY2024-25"
_SCOPED_KPI_COUNT = len(get_core_kpis())  # 43 — all KPIs gate at entity level
_VALUE_CHAIN_KPI = next(k for k in get_core_kpis() if k["value_chain_kpi"])


# ─── stateful fake supabase (mirrors tests/test_assurance_persistence.py) ────

class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, table, mode="read", payload=None):
        self._table = table
        self._mode = mode
        self._payload = payload
        self._filters: list[tuple[str, object]] = []

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, col, desc=False):
        return self

    def limit(self, n):
        return self

    def single(self):
        return self

    def _matches(self, row):
        return dict(row) if all(row.get(c) == v for c, v in self._filters) else None

    def execute(self):
        tab = self._table
        if self._mode == "read":
            if self._filters:
                rows = [r for r in tab if all(r.get(c) == v for c, v in self._filters)]
            else:
                rows = list(tab)
            return _Resp(rows)
        if self._mode == "update":
            updated = []
            for row in tab:
                matched = all(row.get(c) == v for c, v in self._filters)
                if matched:
                    merged = {**row, **self._payload}
                    tab[tab.index(row)] = merged
                    updated.append(merged)
            return _Resp(updated)
        if self._mode == "delete":
            killed = [r for r in tab if all(r.get(c) == v for c, v in self._filters)]
            for r in killed:
                tab.remove(r)
            return _Resp(killed)
        raise AssertionError("unknown query mode")


class _InsertExec:
    def __init__(self, rows, payload):
        self._rows = rows
        self._payload = payload
        self.data = payload

    def execute(self):
        self._rows.append(dict(self._payload))
        return _Resp([dict(self._payload)])


class _Table:
    def __init__(self, store: dict[str, list[dict]], name: str):
        self._store = store
        self._name = name

    def _rows(self):
        return self._store.setdefault(self._name, [])

    def select(self, *_a, **_k):
        return _Query(self._rows())

    def insert(self, row):
        payload = dict(row)
        payload.pop("created_at", None)
        return _InsertExec(self._rows(), payload)

    def update(self, payload):
        return _Query(self._rows(), mode="update", payload=payload)

    def delete(self):
        return _Query(self._rows(), mode="delete")


class FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


# ─── tests ───────────────────────────────────────────────────────────────────

def test_valid_financial_year():
    assert validate_financial_year("FY2025-26") == "FY2025-26"


@pytest.mark.parametrize("bad", ["2024-25", "FY202425", "fy2024-25", "FY2024-2025"])
def test_bad_financial_year_rejected(bad):
    with pytest.raises(AssuranceValidationError):
        validate_financial_year(bad)


def test_unknown_kpi_rejected():
    sb = FakeSupabase()
    with pytest.raises(AssuranceValidationError):
        upsert_assurance(sb, _ORG, _FY, "BRSC-99.9", state="evidence")


def test_escalation_must_pass_evidence_then_limited():
    sb = FakeSupabase()
    # unassured -> reasonable: direct skip is illegal
    with pytest.raises(AssuranceValidationError):
        upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="reasonable")
    # unassured -> evidence: legal
    upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="evidence")
    # evidence -> reasonable without limited: illegal
    with pytest.raises(AssuranceValidationError):
        upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="reasonable")
    # evidence -> limited requires evidence or provider
    with pytest.raises(AssuranceValidationError):
        upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="limited")
    # evidence -> limited with a provider: legal
    upsert_assurance(
        sb, _ORG, _FY, "BRSC-1.1", state="limited",
        provider_name="Deloitte Haskins & Sells LLP",
    )
    # limited -> reasonable with evidence: legal
    upsert_assurance(
        sb, _ORG, _FY, "BRSC-1.1", state="reasonable", evidence_id="ev-1",
        provider_name="Deloitte Haskins & Sells LLP",
    )
    row = get_assurance(sb, _ORG, _FY, "BRSC-1.1")
    assert row["assurance_state"] == "reasonable"


def test_upsert_persists_registry_defaults():
    sb = FakeSupabase()
    # BRSC-4.9 is a value-chain KPI in the canonical registry
    upsert_assurance(sb, _ORG, _FY, "BRSC-4.9", state="evidence")
    row = get_assurance(sb, _ORG, _FY, "BRSC-4.9")
    assert row["value_chain"] is True
    # BRSC-1.3 is PPP + output-denominator (intensity)
    upsert_assurance(sb, _ORG, _FY, "BRSC-1.3", state="evidence")
    row = get_assurance(sb, _ORG, _FY, "BRSC-1.3")
    assert row["ppp_adjusted"] is True


def test_coverage_empty_and_full_gap_for_top1000():
    sb = FakeSupabase()
    report = coverage(sb, _ORG, _FY, tier="top_1000")
    assert report["assured_kpis"] == 0
    assert report["total_kpis"] == 43
    assert report["coverage_pct"] == 0.0
    # Entity-level: all 43 KPIs gate; value-chain flags are informational.
    assert len(report["gaps"]) == _SCOPED_KPI_COUNT
    assert report["required_mode"] == "limited"
    assert report["required_by_year"] == ASSURANCE_PHASEIN["limited"]["top_1000"]


def test_coverage_partial_assured():
    sb = FakeSupabase()
    upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="evidence")
    upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="limited", provider_name="X")
    upsert_assurance(sb, _ORG, _FY, "BRSC-6.1", state="evidence")
    upsert_assurance(sb, _ORG, _FY, "BRSC-6.1", state="limited", provider_name="X")
    upsert_assurance(
        sb, _ORG, _FY, "BRSC-6.1", state="reasonable", provider_name="X",
        evidence_id="ev-9",
    )
    report = coverage(sb, _ORG, _FY, tier="top_1000")
    assert report["assured_kpis"] == 2
    assert report["total_kpis"] == 43
    assert round(report["coverage_pct"], 1) == round(2 / 43 * 100, 1)
    # Both BRSC-6.1 and BRSC-1.1 are assured, so neither appears in the gaps.
    assert len(report["gaps"]) == _SCOPED_KPI_COUNT - 2
    gap_codes = {g["kpi_code"] for g in report["gaps"]}
    assert "BRSC-6.1" not in gap_codes
    assert "BRSC-1.1" not in gap_codes


def test_coverage_no_tier_is_raw_states():
    sb = FakeSupabase()
    upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="evidence")
    upsert_assurance(sb, _ORG, _FY, "BRSC-1.1", state="limited", provider_name="X")
    report = coverage(sb, _ORG, _FY)
    assert report["assurance_mode_for_universe"] is False
    assert report["gaps"] == []
    assert report["required_mode"] == ""


def test_datapoints_back_assurance_coverage():
    # Every flagged core datapoint in the catalog resolves to a BRSC KPI via
    # the coverage registry (no orphan core rows in the entry surface).
    flagged = {d["id"] for d in BRSR_DATAPOINTS if d["core"]}
    assert flagged == set(DATAPOINT_TO_BRSC)
    assert {"C.P1.E.24", "C.P3.E.32"} <= flagged


# ─── filing gate ─────────────────────────────────────────────────────────────

def _assure_kpis(sb, count):
    """Escalate the first `count` KPIs (incl. value-chain) to limited."""
    done = 0
    for kpi in get_core_kpis():
        upsert_assurance(sb, _ORG, _FY, kpi["code"], state="evidence")
        upsert_assurance(
            sb, _ORG, _FY, kpi["code"], state="limited",
            provider_name=f"Provider {done}",
        )
        done += 1
        if done >= count:
            return
    raise AssertionError("not enough KPIs in the registry")


def test_assurance_gate_blocks_when_gaps_exist():
    sb = FakeSupabase()
    verdict = assurance_gate(sb, _ORG, _FY, tier="top_1000")
    assert verdict["applicable"] is True
    assert verdict["ready"] is False
    assert len(verdict["blockers"]) == _SCOPED_KPI_COUNT
    assert verdict["coverage"]["required_mode"] == "limited"


def test_assurance_gate_ready_when_scope_covered():
    sb = FakeSupabase()
    _assure_kpis(sb, _SCOPED_KPI_COUNT)
    verdict = assurance_gate(sb, _ORG, _FY, tier="top_1000")
    assert verdict["ready"] is True
    assert verdict["blockers"] == []
    assert verdict["coverage"]["assured_kpis"] == _SCOPED_KPI_COUNT


def test_assurance_gate_not_applicable_without_tier():
    sb = FakeSupabase()
    verdict = assurance_gate(sb, _ORG, _FY, tier=None)
    assert verdict["applicable"] is False
    assert verdict["ready"] is True  # never blocks without an applicable universe
    assert verdict["blockers"] == []


def test_value_chain_kpis_gate_at_entity_level():
    # No deferral: value-chain KPIs are gated exactly like the rest.
    assert kpi_required_mode(_VALUE_CHAIN_KPI, "top_1000", "FY2024-25") == "limited"
    assert kpi_required_mode(_VALUE_CHAIN_KPI, "top_150", "FY2023-24") == ""
    assert kpi_required_mode(_VALUE_CHAIN_KPI, "top_150", "FY2024-25") == "reasonable"
