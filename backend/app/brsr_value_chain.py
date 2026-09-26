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

from typing import Any

from app.brsr_core import VALUE_CHAIN_COVERAGE, get_core_kpis

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