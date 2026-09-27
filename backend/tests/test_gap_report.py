"""Gap-report engine tests: honesty rules, readiness math, workflow states."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.esrs_gap_report import build_report
from tests.test_guest_csrd import GUEST_A, _FakeDB, mint

FY = "FY2025"


def _state(**kw):
    base = {
        "rule_set_version": "ESRS Set 1 (2023)",
        "reporting_period": FY,
        "entity_scope": ["Acme Ltd"],
        "value_chain_scope": {"own_operations": True, "upstream": True, "downstream": False},
        "datapoint_summary": {"total_datapoints": 100, "assessed_datapoints": 60,
                              "handled_disclosures": 60, "effective_gaps": 40},
        "standard_status": [
            {"standard": "ESRS 2", "applicable_dps": 50, "assessed": 50, "gaps": 0, "status": ""},
            {"standard": "E1", "applicable_dps": 50, "assessed": 10, "gaps": 40, "status": ""},
        ],
        "gating_disclosures_status": [
            {"id": "BP-1", "name": "Basis", "status": "complete", "owner": "A. Rao", "due_in_days": 30},
            {"id": "SBM-1", "name": "Strategy", "status": "in_progress", "owner": "", "due_in_days": 5},
            {"id": "GOV-1", "name": "Bodies", "status": "not_started"},
        ],
        "dma_status": {"iros_identified": 2, "iros_assessed": 2, "iros_material": 2,
                       "orphan_iro_ids": ["Scope 3 cotton"], "scope_locked": False},
        "framework_mapping_coverage": {"gri": 20, "issb": 15, "reviewed": False},
        "filing_deadline": "2026-04-30",
        "days_to_deadline": 90,
    }
    base.update(kw)
    return base


def test_readiness_and_biggest_blocker():
    r = build_report(_state())
    assert r["readiness_pct"] == 60.0
    assert "E1" in r["summary"] and "40 open gaps" in r["summary"]
    assert r["standards"][0]["computed_status"] == "On Track"
    assert r["standards"][1]["computed_status"] == "At Risk"
    assert any("scope is not locked" in f for f in r["critical_findings"])


def test_unset_rule_set_is_critical_finding():
    r = build_report(_state(rule_set_version=""))
    assert r["rule_set_unset"] is True
    assert any("rule_set_version is unset" in f for f in r["critical_findings"])
    # Unknown rule sets don't invent gating facts.
    r2 = build_report(_state(rule_set_version="ESRS 9 (imaginary)"))
    assert any("no gating set encoded" in f for f in r2["critical_findings"])


def test_gating_risk_flags_and_unassigned_honesty():
    r = build_report(_state())
    by_id = {g["id"]: g for g in r["gating"]}
    assert by_id["BP-1"]["risk"] == "🟢 on track"
    assert by_id["SBM-1"]["risk"] == "🟠 due within 2 weeks"
    assert by_id["SBM-1"]["owner"] == "unassigned"
    assert by_id["GOV-1"]["risk"] == "⚪ unscheduled"
    assert r["gating_complete"] == 1


def test_orphans_and_qc_checklist():
    r = build_report(_state())
    assert r["orphan_iros"] == ["Scope 3 cotton"]
    qc = {q["key"]: q for q in r["qc"]}
    assert qc["orphans"]["met"] is False
    assert qc["gaps"]["met"] is False
    assert qc["evidence"]["met"] is None  # surfaced, never assumed
    assert qc["mapping"]["met"] is False
    ready = build_report(_state(
        datapoint_summary={"total_datapoints": 100, "assessed_datapoints": 100,
                           "handled_disclosures": 100, "effective_gaps": 0},
        standard_status=[{"standard": "ESRS 2", "applicable_dps": 100, "assessed": 100, "gaps": 0, "status": ""}],
        gating_disclosures_status=[{"id": "BP-1", "status": "complete"}],
        dma_status={"iros_identified": 1, "iros_assessed": 1, "iros_material": 1,
                    "orphan_iro_ids": [], "scope_locked": True},
        framework_mapping_coverage={"reviewed": True},
        export_validated=True,
    ))
    assert ready["qc"][0]["met"] is True
    assert [s["state"] for s in ready["workflow"]] == ["done"] * 5


def test_workflow_gates_in_order():
    r = build_report(_state())
    states = {s["key"]: s["state"] for s in r["workflow"]}
    assert states == {"seed": "done", "dma": "current", "collect": "blocked",
                      "mapping": "blocked", "export": "blocked"}


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


@pytest.mark.asyncio
async def test_gap_report_endpoint_live_state(client, db):
    mint(db)
    resp = await client.post(
        "/api/platform/csrd/entries",
        json={"financial_year": FY, "entries": [
            {"datapoint_id": "E1.E1-6.44", "status": "reported", "value": 10},
        ]},
        headers={"authorization": "Bearer guest_aaaa"},
    )
    assert resp.status_code == 200
    resp = await client.get(
        "/api/platform/csrd/gap-report",
        params={"financial_year": FY, "rule_set_version": "ESRS Set 1 (2023)",
                "days_to_deadline": 60},
        headers={"authorization": "Bearer guest_aaaa"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["rule_set_version"] == "ESRS Set 1 (2023)"
    assert body["readiness_pct"] > 0
    assert len(body["standards"]) == 11
    assert any(g["id"] == "BP-1" for g in body["gating"])
    assert len(body["workflow"]) == 5
    assert len(body["qc"]) == 7
    # Empty sandbox: DMA unlocked is flagged, not hidden.
    assert any("scope is not locked" in f for f in body["critical_findings"])
