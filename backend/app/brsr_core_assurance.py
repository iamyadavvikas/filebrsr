"""BRSR Core per-KPI assurance tracking (migration v32).

Tracks the assurance state machine for each canonical ``BRSC-*`` KPI across a
financial year, org-scoped and persisted to Supabase. Enforces the escalation
path (unassured -> evidence -> limited -> reasonable) and the SEBI rule that a
limited/reasonable claim requires an evidence document or a named provider.

The canonical KPI definitions and phase-in are owned by :mod:`app.brsr_core`;
this module is the persistence + state layer on top of it.
"""

from __future__ import annotations

import re
from typing import Any

from app.brsr_core import (
    ASSURANCE_PHASEIN,
    assurance_mode_for,
    core_kpi_codes,
    get_core_kpis,
    kpi_required_mode,
    tier_for_reporting_category,
)

FINANCIAL_YEAR_RE = re.compile(r"^FY[0-9]{4}-[0-9]{2}$")

STATES = (
    "unassured",
    "evidence",
    "limited",
    "reasonable",
    "not_applicable",
)

# Legal transitions. Escalation must pass through evidence -> limited before
# reasonable; every non-initial state may step back down to document a reversal.
TRANSITIONS: dict[str, frozenset[str]] = {
    "unassured": frozenset({"evidence", "not_applicable"}),
    "evidence": frozenset({"limited", "unassured", "not_applicable"}),
    "limited": frozenset({"reasonable", "evidence", "unassured", "not_applicable"}),
    "reasonable": frozenset({"limited", "evidence", "unassured", "not_applicable"}),
    "not_applicable": frozenset({"unassured"}),
}

# States that claim third-party assurance on the KPI value.
ASSURED_STATES = frozenset({"limited", "reasonable"})

INVALID_TARGET_MODE_MSG = "target_mode must be 'limited', 'reasonable', 'none' or ''"


class AssuranceValidationError(ValueError):
    pass


def validate_financial_year(fy: str) -> str:
    if not FINANCIAL_YEAR_RE.match(fy):
        raise AssuranceValidationError(
            f"financial_year must look like 'FY2024-25', got {fy!r}"
        )
    return fy


def requires_evidence(state: str) -> bool:
    """A limited/reasonable claim must be backed by an evidence document or a
    named provider (SEBI expects identification of the assurance provider)."""
    return state in ASSURED_STATES


def check_transition(current: str, target: str) -> None:
    if current not in STATES or target not in STATES:
        raise AssuranceValidationError(f"unknown assurance state {target!r}")
    if target not in TRANSITIONS[current]:
        raise AssuranceValidationError(
            f"illegal assurance transition '{current}' -> '{target}' "
            f"(allowed: {', '.join(sorted(TRANSITIONS[current])) or 'none'})"
        )


def check_target_mode(mode: str | None) -> str:
    mode = (mode or "").strip() or "none"
    if mode not in ("limited", "reasonable", "none"):
        raise AssuranceValidationError(INVALID_TARGET_MODE_MSG)
    return mode


def _kpi_def(kpi_code: str) -> dict[str, Any] | None:
    return next((k for k in get_core_kpis() if k["code"] == kpi_code), None)


def list_assurance(sb: object, org_id: str, financial_year: str) -> list[dict[str, Any]]:
    validate_financial_year(financial_year)
    res = (
        sb.table("brsr_core_assurance")
        .select("*")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .order("created_at", desc=True)
        .execute()
    )
    return list(res.data or [])


def get_assurance(
    sb: object, org_id: str, financial_year: str, kpi_code: str
) -> dict[str, Any] | None:
    validate_financial_year(financial_year)
    if kpi_code not in core_kpi_codes():
        raise AssuranceValidationError(f"unknown BRSR Core KPI {kpi_code!r}")
    res = (
        sb.table("brsr_core_assurance")
        .select("*")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .eq("kpi_code", kpi_code)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def upsert_assurance(
    sb: object,
    org_id: str,
    financial_year: str,
    kpi_code: str,
    *,
    state: str | None = None,
    target_mode: str | None = None,
    provider_name: str | None = None,
    provider_details: dict[str, Any] | None = None,
    statement_short: str | None = None,
    evidence_id: str | None = None,
    evidence_note: str | None = None,
    ppp_adjusted: bool | None = None,
    output_denominator: str | None = None,
    value_chain: bool | None = None,
    assessed_value: float | None = None,
    unit: str | None = None,
    assessed_on: str | None = None,
) -> dict[str, Any]:
    """Create or update one org's assurance row for (fy, kpi_code)."""
    validate_financial_year(financial_year)
    kpi = _kpi_def(kpi_code)
    if kpi is None:
        raise AssuranceValidationError(f"unknown BRSR Core KPI {kpi_code!r}")

    current = get_assurance(sb, org_id, financial_year, kpi_code)
    prev_state = current["assurance_state"] if current else "unassured"
    new_state = (state or prev_state).strip().lower()
    check_transition(prev_state, new_state)

    target = check_target_mode(target_mode)

    if requires_evidence(new_state) and not (evidence_id or provider_name):
        raise AssuranceValidationError(
            f"'{new_state}' assurance on {kpi_code} requires evidence_id or provider_name"
        )

    payload: dict[str, Any] = {
        "assurance_state": new_state,
        "target_mode": target,
        "provider_name": (provider_name or "").strip() or None,
        "provider_details": provider_details or {},
        "statement_short": (statement_short or "").strip() or None,
        "evidence_id": evidence_id or None,
        "evidence_note": (evidence_note or "").strip() or None,
        "ppp_adjusted": bool(ppp_adjusted) if ppp_adjusted is not None else kpi["ppp_adjusted"],
        "output_denominator": (output_denominator or "").strip() or None,
        "value_chain": bool(value_chain) if value_chain is not None else kpi["value_chain_kpi"],
        "assessed_value": assessed_value,
        "unit": (unit or "").strip() or None,
        "assessed_on": assessed_on or None,
    }

    if current is None:
        payload["org_id"] = org_id
        payload["financial_year"] = financial_year
        payload["kpi_code"] = kpi_code
        sb.table("brsr_core_assurance").insert(payload).execute()
        return payload

    res = (
        sb.table("brsr_core_assurance")
        .update(payload)
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .eq("kpi_code", kpi_code)
        .execute()
    )
    row = (res.data or [{}])[0]
    if not row:
        row = payload
    return {**(current or {}), **row, **payload}


def delete_assurance(sb: object, org_id: str, financial_year: str, kpi_code: str) -> bool:
    validate_financial_year(financial_year)
    if kpi_code not in core_kpi_codes():
        raise AssuranceValidationError(f"unknown BRSR Core KPI {kpi_code!r}")
    res = (
        sb.table("brsr_core_assurance")
        .delete()
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .eq("kpi_code", kpi_code)
        .execute()
    )
    return bool(res.data)


def _mode_met(attained: str, required: str) -> bool:
    """Whether the attained state satisfies the phase-in required mode."""
    if not required or required == "none":
        return True
    if attained == "not_applicable" and required != "none":
        return False
    if required == "reasonable":
        return attained == "reasonable"
    if required == "limited":
        return attained in ("limited", "reasonable")
    return True


def coverage(
    sb: object,
    org_id: str,
    financial_year: str,
    tier: str | None = None,
) -> dict[str, Any]:
    """Assurance coverage for a financial year, per attribute and vs phase-in.

    ``tier`` (top_150 / top_250 / top_500 / top_1000 / None) selects the
    required mode from ``brsr_core.assurance_mode_for``; None reports raw state
    without a compliance verdict. All 43 KPIs gate at entity level; the
    ``value_chain`` flag on each gap is informational (marks KPIs that carry the
    top-250 value-chain reporting surface).
    """
    validate_financial_year(financial_year)
    required = ""
    required_by_year: str | None = None
    if tier:
        required = assurance_mode_for(tier, financial_year) or "none"
        if required in ASSURANCE_PHASEIN:
            required_by_year = ASSURANCE_PHASEIN[required][tier]

    rows = {r["kpi_code"]: r for r in list_assurance(sb, org_id, financial_year)}
    attributes: dict[str, Any] = {}
    gaps: list[dict[str, Any]] = []

    for kpi in get_core_kpis():
        attr = attributes.setdefault(
            kpi["attribute"],
            {"assured": 0, "preparing": 0, "not_applicable": 0, "total": 0},
        )
        attr["total"] += 1
        row = rows.get(kpi["code"])
        attained = (row or {}).get("assurance_state", "unassured")
        if attained in ASSURED_STATES:
            attr["assured"] += 1
        elif attained == "not_applicable":
            attr["not_applicable"] += 1
        else:
            attr["preparing"] += 1

        if tier:
            kpi_required = kpi_required_mode(kpi, tier, financial_year) or "none"
            if not _mode_met(attained, kpi_required):
                gaps.append(
                    {
                        "kpi_code": kpi["code"],
                        "kpi_label": kpi["label"],
                        "attribute": kpi["attribute"],
                        "attained": attained,
                        "required": kpi_required,
                        "value_chain": bool(kpi.get("value_chain_kpi")),
                        "evidence_linked": bool((row or {}).get("evidence_id")),
                    }
                )

    assured = sum(a["assured"] for a in attributes.values())
    total = sum(a["total"] for a in attributes.values())
    return {
        "financial_year": financial_year,
        "tier": tier,
        "required_mode": required,
        "required_by_year": required_by_year,
        "assurance_mode_for_universe": bool(tier),
        "coverage_pct": round(assured / total * 100, 1) if total else 0.0,
        "assured_kpis": assured,
        "total_kpis": total,
        "attributes": [{"attribute": k, **v} for k, v in sorted(attributes.items())],
        "gaps": gaps,
    }


def assurance_gate(
    sb: object,
    org_id: str,
    financial_year: str,
    tier: str | None,
) -> dict[str, Any]:
    """Filing-gate verdict: ready when no required BRSR Core assurance is missing.

    ``tier`` None (no declared market-cap band) returns ready=True with
    ``applicable=False`` — the gate cannot assert an obligation without a
    universe, so it does not block.
    """
    report = coverage(sb, org_id, financial_year, tier=tier)
    blockers = report["gaps"]
    return {
        "ready": not blockers,
        "applicable": bool(tier),
        "tier": tier,
        "blockers": blockers,
        "coverage": report,
    }


def resolve_org_for_gate(
    sb: object,
    user_id: str,
    explicit_tier: str | None = None,
    reporting_category: str | None = None,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """Resolve (org_id, tier, profile) for filing gates.

    Tier comes from the caller when supplied, else from the profile's
    self-declared reporting category (``brsr_core.tier_for_reporting_category``).
    org_id may be None when the user has no personal org yet — callers must
    treat that as \"gate not applicable\".
    """
    profile = (
        sb.table("profiles")
        .select("org_id, reporting_category, company_name, cin")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    data = (profile.data or [{}])[0] if (profile.data or []) else {}
    params = {"reporting_category": data.get("reporting_category")}
    if reporting_category is not None:
        params["reporting_category"] = reporting_category
    tier = explicit_tier or tier_for_reporting_category(params["reporting_category"])
    return data.get("org_id"), tier, data
