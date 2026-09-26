"""BRSR Core value-chain partner module (CIR/2025/42).

Scopes and scores the top-250 value-chain reporting surface. Under CIR/2023/122
cl.4, as revised by CIR/2025/42 (effective for disclosures FY2024-25 onwards),
the top-250 listed entities disclose their BRSR Core KPIs for value-chain
partners that are individually a top upstream/downstream partner comprising
>=2% of the entity's purchases/sales (by value), and may limit cumulative
disclosure to 75% of purchases and sales respectively. Disclosures are
voluntary from FY2025-26; assessment/assurance is voluntary from FY2026-27.

This module is the pure scope + coverage layer: it decides which partners are
in scope, computes cumulative purchase/sales coverage against the 75% cap, and
maps the per-partner KPI set (the same 43 BRSR Core KPIs flagged
``value_chain_kpi``). Persistence and entry state live in the router; attributed
assurance state reuses :mod:`app.brsr_core_assurance`.

The filing gate enforces entity-level assurance only (see
``brsr_core.kpi_required_mode``); value-chain disclosure status is reported
(``disclosed``) but never blocks an entity's own filing.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.brsr_core import VALUE_CHAIN_COVERAGE, get_core_kpis
from app.brsr_core_assurance import (
    AssuranceValidationError,
    check_transition,
    requires_evidence,
    validate_financial_year,
)

__all__ = [
    "COVERAGE_CAP_PCT",
    "DIRECTIONS",
    "PARTNER_THRESHOLD_PCT",
    "coverage_status",
    "cumulative_coverage",
    "delete_entry",
    "delete_partner",
    "disclosed_coverage",
    "in_scope_partner",
    "list_entries",
    "list_partners",
    "partner_report",
    "upsert_entry",
    "upsert_partner",
    "validate_direction",
    "value_chain_kpi_codes",
    "value_chain_kpis",
    "value_chain_report",
]

PARTNER_THRESHOLD_PCT: float = VALUE_CHAIN_COVERAGE["partner_threshold_pct"]
COVERAGE_CAP_PCT: float = VALUE_CHAIN_COVERAGE["cumulative_cap_pct"]

DIRECTIONS = ("upstream", "downstream")

INVALID_DIRECTION_MSG = "direction must be 'upstream' or 'downstream'"


def _pct(value: float | int | str | None) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"percentage must be numeric, got {value!r}") from None
    if not 0.0 <= num <= 100.0:
        raise ValueError(f"percentage must be between 0 and 100, got {num}")
    return num


def validate_direction(direction: str) -> str:
    if direction not in DIRECTIONS:
        raise ValueError(INVALID_DIRECTION_MSG)
    return direction


def in_scope_partner(purchases_pct: float | int | str | None = None,
                     sales_pct: float | int | str | None = None) -> bool:
    """A partner is in scope when it is >=2% of purchases or sales (by value)."""
    return (
        (_pct(purchases_pct) is not None and (_pct(purchases_pct) or 0) >= PARTNER_THRESHOLD_PCT)
        or (_pct(sales_pct) is not None and (_pct(sales_pct) or 0) >= PARTNER_THRESHOLD_PCT)
    )


def cumulative_coverage(
    partners: list[dict[str, Any]], direction: str
) -> float:
    """Sum of the direction-relevant percentages for in-scope partners.

    Upstream (suppliers) report against purchases; downstream (customers)
    report against sales. A partner below the 2% threshold contributes 0.
    """
    validate_direction(direction)
    key = "purchases_pct" if direction == "upstream" else "sales_pct"
    total = 0.0
    for p in partners:
        value = _pct(p.get(key))
        if value is None or value < PARTNER_THRESHOLD_PCT:
            continue
        total += value
    return min(total, COVERAGE_CAP_PCT) if total > COVERAGE_CAP_PCT else total


def disclosed_coverage(
    partners: list[dict[str, Any]], direction: str
) -> float:
    """Sum of the direction-relevant percentages for partners the entity
    actually disclosed ESG data for (CIR/2025/42 cl.3.6 requires stating this)."""
    validate_direction(direction)
    key = "purchases_pct" if direction == "upstream" else "sales_pct"
    total = 0.0
    for p in partners:
        if not p.get("disclosed"):
            continue
        value = _pct(p.get(key))
        if value is None or value < PARTNER_THRESHOLD_PCT:
            continue
        total += value
    return min(total, COVERAGE_CAP_PCT) if total > COVERAGE_CAP_PCT else total


def coverage_status(partners: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-direction coverage vs the 75% cap, plus the entity's disclosed %.

    Because coverage is capped at 75%, ``shortfall_pct`` is the gap between the
    disclosed % and the cap — the portion the entity chose not to disclose
    (allowed under the cap). ``incomplete_partners`` lists in-scope partners
    with no disclosure yet.
    """
    status: dict[str, Any] = {}
    for direction in DIRECTIONS:
        covered = round(cumulative_coverage(partners, direction), 1)
        disclosed = round(disclosed_coverage(partners, direction), 1)
        key = "purchases_pct" if direction == "upstream" else "sales_pct"
        in_scope = [
            p
            for p in partners
            if (_pct(p.get(key)) or 0) >= PARTNER_THRESHOLD_PCT
        ]
        pending = [p for p in in_scope if not p.get("disclosed")]
        status[direction] = {
            "in_scope_partners": len(in_scope),
            "cumulative_pct": covered,
            "disclosed_pct": disclosed,
            "cap_pct": COVERAGE_CAP_PCT,
            "shortfall_to_cap_pct": round(max(COVERAGE_CAP_PCT - disclosed, 0.0), 1),
            "disclosures_required": disclosed < covered - 1e-9,
            "pending_partners": len(pending),
        }
    return status


def value_chain_kpis() -> list[dict[str, Any]]:
    """The BRSR Core KPIs that carry the value-chain reporting surface."""
    return get_core_kpis(value_chain_only=True)


def value_chain_kpi_codes() -> set[str]:
    return {k["code"] for k in value_chain_kpis()}


def partner_report(
    partner: dict[str, Any],
    attributed: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Per-partner value-chain view: scope verdict and, when provided, the
    attributed assurance state of each value-chain KPI for business with this
    partner (``attributed`` maps kpi_code -> assurance state)."""
    purchases = _pct(partner.get("purchases_pct"))
    sales = _pct(partner.get("sales_pct"))
    in_scope = in_scope_partner(purchases, sales)
    attributed = attributed or {}
    kpis = []
    assured = 0
    for kpi in value_chain_kpis():
        code = kpi["code"]
        state = attributed.get(code, "unassured")
        if state in ("limited", "reasonable"):
            assured += 1
        kpis.append(
            {
                "kpi_code": code,
                "kpi_label": kpi["label"],
                "attribute": kpi["attribute"],
                "state": state,
            }
        )
    return {
        "in_scope": in_scope,
        "direction": partner.get("direction"),
        "purchases_pct": purchases,
        "sales_pct": sales,
        "disclosed": bool(partner.get("disclosed")),
        "kpis_total": len(kpis),
        "kpis_assured": assured,
        "kpis": kpis,
    }


def list_partners(
    sb: object, org_id: str, financial_year: str
) -> list[dict[str, Any]]:
    validate_financial_year(financial_year)
    res = (
        sb.table("value_chain_partners")
        .select("*")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .order("direction")
        .order("created_at")
        .execute()
    )
    return list(res.data or [])


def upsert_partner(
    sb: object,
    org_id: str,
    financial_year: str,
    partner_name: str,
    direction: str,
    purchases_pct: float | int | None = None,
    sales_pct: float | int | None = None,
    disclosed: bool = False,
    notes: str | None = None,
) -> dict[str, Any]:
    validate_financial_year(financial_year)
    name = (partner_name or "").strip()
    if not name:
        raise AssuranceValidationError("partner_name is required")
    try:
        validate_direction(direction)
        _pct(purchases_pct)
        _pct(sales_pct)
    except ValueError as exc:
        raise AssuranceValidationError(str(exc)) from exc
    row = {
        "org_id": org_id,
        "financial_year": financial_year,
        "partner_name": name,
        "direction": direction,
        "disclosed": bool(disclosed),
    }
    if purchases_pct is not None:
        row["purchases_pct"] = float(purchases_pct)
    if sales_pct is not None:
        row["sales_pct"] = float(sales_pct)
    if notes is not None:
        row["notes"] = notes
    res = (
        sb.table("value_chain_partners")
        .upsert(
            row,
            on_conflict="org_id,financial_year,partner_name,direction",
        )
        .execute()
    )
    return (res.data or [{}])[0]


def delete_partner(
    sb: object, org_id: str, financial_year: str, partner_id: str
) -> bool:
    validate_financial_year(financial_year)
    res = (
        sb.table("value_chain_partners")
        .delete()
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .eq("id", partner_id)
        .execute()
    )
    return bool(res.data)


def list_entries(
    sb: object,
    org_id: str,
    financial_year: str,
    partner_id: str | None = None,
) -> list[dict[str, Any]]:
    validate_financial_year(financial_year)
    q = (
        sb.table("value_chain_entries")
        .select("*")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
    )
    if partner_id:
        q = q.eq("partner_id", partner_id)
    res = q.order("kpi_code").execute()
    return list(res.data or [])


def upsert_entry(
    sb: object,
    org_id: str,
    financial_year: str,
    partner_id: str,
    kpi_code: str,
    state: str,
    provider_name: str | None = None,
    provider_details: dict[str, Any] | None = None,
    evidence_id: str | None = None,
    evidence_note: str | None = None,
    assessed_value: float | None = None,
    unit: str | None = None,
    assessed_on: str | None = None,
) -> dict[str, Any]:
    validate_financial_year(financial_year)
    if kpi_code not in value_chain_kpi_codes():
        raise AssuranceValidationError(
            f"{kpi_code!r} is not a value-chain KPI (see value_chain_kpis)"
        )
    partner = (
        sb.table("value_chain_partners")
        .select("id")
        .eq("org_id", org_id)
        .eq("id", partner_id)
        .limit(1)
        .execute()
    )
    if not (partner.data or []):
        raise AssuranceValidationError("partner does not belong to this org")

    rows = {
        r["kpi_code"]: r
        for r in list_entries(sb, org_id, financial_year, partner_id=partner_id)
    }
    current = (rows.get(kpi_code) or {}).get("assurance_state", "unassured")
    check_transition(current, state)
    if requires_evidence(state) and not (evidence_id or provider_name):
        raise AssuranceValidationError(
            f"state {state!r} requires an evidence document or an assurance "
            "provider for the value-chain KPI"
        )

    row = {
        "org_id": org_id,
        "financial_year": financial_year,
        "partner_id": partner_id,
        "kpi_code": kpi_code,
        "assurance_state": state,
    }
    if provider_name is not None:
        row["provider_name"] = provider_name
    if provider_details is not None:
        row["provider_details"] = provider_details
    if evidence_id is not None:
        row["evidence_id"] = evidence_id
    if evidence_note is not None:
        row["evidence_note"] = evidence_note
    if assessed_value is not None:
        row["assessed_value"] = float(assessed_value)
    if unit is not None:
        row["unit"] = unit
    if assessed_on is not None:
        row["assessed_on"] = assessed_on
    res = (
        sb.table("value_chain_entries")
        .upsert(row, on_conflict="org_id,financial_year,partner_id,kpi_code")
        .execute()
    )
    return (res.data or [{}])[0]


def delete_entry(
    sb: object, org_id: str, financial_year: str, entry_id: str
) -> bool:
    validate_financial_year(financial_year)
    res = (
        sb.table("value_chain_entries")
        .delete()
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .eq("id", entry_id)
        .execute()
    )
    return bool(res.data)


def value_chain_report(
    sb: object, org_id: str, financial_year: str
) -> dict[str, Any]:
    """Aggregated value-chain view for a financial year: coverage status per
    direction, per-partner scope/attribution, and the KPI catalog."""
    validate_financial_year(financial_year)
    partners = list_partners(sb, org_id, financial_year)
    entries = list_entries(sb, org_id, financial_year)
    by_partner: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for entry in entries:
        by_partner[entry["partner_id"]][entry["kpi_code"]] = entry

    partner_rows = []
    for partner in partners:
        attributed = {
            code: row.get("assurance_state", "unassured")
            for code, row in by_partner[partner["id"]].items()
        }
        report = partner_report(partner, attributed)
        report["id"] = partner["id"]
        report["partner_name"] = partner["partner_name"]
        report["notes"] = partner.get("notes")
        partner_rows.append(report)

    status = coverage_status(partners)
    return {
        "financial_year": financial_year,
        "partners_count": len(partners),
        "coverage_status": status,
        "partners": partner_rows,
        "kpis_count": len(value_chain_kpis()),
    }
