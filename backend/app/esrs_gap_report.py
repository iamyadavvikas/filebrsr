"""Tenant gap-analysis report engine (CSRD compliance-lead view).

Translates raw workspace state into the prioritized, actionable report
defined in the product spec: readiness overview, critical gaps, sequential
workflow, QC checklist. Pure functions over plain dicts — no I/O, so the
same code paths are unit-tested and the endpoint only populates inputs.

Honesty rules (per spec): missing/ambiguous inputs are *reported*, never
defaulted. An unset rule_set_version or unlocked scope is itself a
critical finding. Rule-set-specific facts (e.g. which DRs gate) are
anchored to the provided rule_set_version via GATING_SETS.
"""

from __future__ import annotations

from typing import Any

# Gating sets per rule-set version. The revised ESRS may change these —
# add a new key rather than editing history.
GATING_SETS: dict[str, list[dict[str, str]]] = {
    "ESRS Set 1 (2023)": [
        {"id": "BP-1", "name": "Basis for preparation"},
        {"id": "BP-2", "name": "Disclosures in relation to specific circumstances"},
        {"id": "SBM-1", "name": "Strategy and business model"},
        {"id": "SBM-2", "name": "Interests and views of stakeholders"},
        {"id": "GOV-1", "name": "Role of administrative bodies"},
        {"id": "MDR-P", "name": "Policies adopted (minimum disclosure)"},
    ],
}

WORKFLOW_STEPS: list[dict[str, str]] = [
    {"key": "seed",
     "title": "Data seeding & ingestion",
     "work": "Import prior-year reports, sample/VSME data, or set up the registry.",
     "exit": "All entities and prior-period baselines loaded."},
    {"key": "dma",
     "title": "Double materiality & scope lock",
     "work": "Define material IROs; set value-chain and entity boundaries.",
     "exit": "scope_locked = true with zero orphan IROs."},
    {"key": "collect",
     "title": "Topical data collection & assessment",
     "work": "Close effective gaps across E, S, G standards.",
     "exit": "effective_gaps = 0 on all applicable datapoints."},
    {"key": "mapping",
     "title": "Multi-framework mapping & alignment",
     "work": "Review pre-mapped GRI/ISSB/TCFD/SDG references against actual disclosures.",
     "exit": "Mapping coverage reviewed and confirmed, not left as auto-suggestion."},
    {"key": "export",
     "title": "Final review, rollover & statement export",
     "work": "QC pass, tagging validation, export.",
     "exit": "Statement passes validation with zero blocking errors."},
]

QC_ITEMS: list[dict[str, str]] = [
    {"key": "orphans", "label": "No orphan IROs remain"},
    {"key": "gating", "label": "All gating disclosures complete"},
    {"key": "gaps", "label": "Zero effective gaps on in-scope datapoints"},
    {"key": "evidence", "label": "Every quantitative datapoint has a source/evidence reference"},
    {"key": "mapping", "label": "Framework mapping (GRI/ISSB/TCFD/SDG) manually reviewed, not left as auto-suggestion only"},
    {"key": "tagging", "label": "Tagging/export validation run with zero blocking errors"},
    {"key": "signoff", "label": "Sign-off recorded from designated reviewer(s) before export"},
]


def _risk_flag(due_in_days: int | None) -> str:
    if due_in_days is None:
        return "⚪ unscheduled"
    if due_in_days < 0:
        return "🔴 overdue"
    if due_in_days <= 14:
        return "🟠 due within 2 weeks"
    return "🟢 on track"


def _standard_status(row: dict[str, Any]) -> str:
    gaps = row.get("gaps", 0) or 0
    applicable = row.get("applicable_dps", 0) or 0
    assessed = row.get("assessed", 0) or 0
    if applicable and gaps == 0 and assessed >= applicable:
        return "On Track"
    if gaps > 0 and assessed > 0:
        return "At Risk"
    if applicable and assessed == 0:
        return "Blocked"
    return "At Risk" if gaps else "On Track"


def build_report(state: dict[str, Any]) -> dict[str, Any]:
    """Build the gap-analysis report from platform state (see spec)."""
    rule_set = (state.get("rule_set_version") or "").strip()
    period = state.get("reporting_period") or "unspecified period"
    dp = state.get("datapoint_summary") or {}
    total = dp.get("total_datapoints", 0) or 0
    assessed = dp.get("assessed_datapoints", 0) or 0
    gaps = dp.get("effective_gaps", 0) or 0
    readiness = round(100.0 * assessed / total, 1) if total else 0.0

    findings: list[str] = []
    if not rule_set:
        findings.append(
            "CRITICAL: rule_set_version is unset — readiness is computed against "
            "whatever registry the tenant currently serves; confirm ESRS Set 1 (2023) "
            "before treating any number as filing-grade."
        )
    dma = state.get("dma_status") or {}
    if not dma.get("scope_locked"):
        findings.append(
            "CRITICAL: DMA scope is not locked — downstream collection is chasing "
            "a moving target; lock scope before scaling assessment."
        )
    gating_set = GATING_SETS.get(rule_set, [])
    if rule_set and not gating_set:
        findings.append(
            f"NOTE: no gating set encoded for rule set {rule_set!r} — gating "
            "completion cannot be evaluated; add it before relying on this report."
        )

    standards = []
    for row in state.get("standard_status") or []:
        standards.append({**row, "computed_status": _standard_status(row)})

    gating_in = {g.get("id"): g for g in state.get("gating_disclosures_status") or []}
    days_to_deadline = state.get("days_to_deadline")
    gating_rows = []
    for g in gating_set:
        cur = gating_in.get(g["id"], {})
        status = cur.get("status", "not_started")
        due = cur.get("due_date")
        due_in = cur.get("due_in_days")
        if status == "complete":
            flag = "🟢 on track"
        elif due_in is not None:
            flag = _risk_flag(due_in)
        else:
            # No explicit due date: unscheduled. The filing deadline is
            # display context, not a per-item promise.
            flag = "⚪ unscheduled"
        gating_rows.append({
            "id": g["id"], "name": cur.get("name") or g["name"],
            "status": status, "owner": cur.get("owner") or "unassigned",
            "due_date": due, "risk": flag,
        })
    gating_done = sum(1 for g in gating_rows if g["status"] == "complete")
    # Tenant-supplied gating rows for ids outside the known set still count.
    for gid, cur in gating_in.items():
        if gid not in {g["id"] for g in gating_set}:
            gating_rows.append({
                "id": gid, "name": cur.get("name") or gid,
                "status": cur.get("status", "not_started"),
                "owner": cur.get("owner") or "unassigned",
                "due_date": cur.get("due_date"),
                "risk": "⚪ unscheduled" if cur.get("status") != "complete" else "🟢 on track",
            })

    orphans = dma.get("orphan_iro_ids") or dma.get("orphans") or []
    if isinstance(orphans, int):
        orphans = [f"orphan-{i+1}" for i in range(orphans)]
    vc = state.get("value_chain_scope") or {}
    mapping = state.get("framework_mapping_coverage") or {}

    biggest = "no assessed datapoints yet"
    if gaps:
        worst = max(standards, key=lambda r: r.get("gaps", 0)) if standards else None
        if worst and worst.get("gaps"):
            label = worst.get("code") or worst.get("name") or worst.get("standard", "a standard")
            biggest = f"{worst['gaps']} open gaps in {label}"
    elif orphans:
        biggest = f"{len(orphans)} orphan IRO(s) decoupling DMA from data collection"
    elif not dma.get("scope_locked"):
        biggest = "unlocked DMA scope"
    summary = (
        f"{period}: {readiness}% readiness ({assessed}/{total} datapoints), "
        f"{gating_done}/{len(gating_rows)} gating disclosures complete, "
        f"{days_to_deadline if days_to_deadline is not None else '?'} days to deadline. "
        f"Biggest blocker: {biggest}."
    )

    # Workflow step states from live flags.
    steps = []
    seed_done = bool((state.get("entity_scope") or total) and True)
    dma_done = bool(dma.get("scope_locked")) and not orphans
    collect_done = gaps == 0 and total > 0
    mapping_done = bool(mapping.get("reviewed", False))
    export_done = bool(state.get("export_validated", False))
    done_flags = [seed_done, dma_done, collect_done, mapping_done, export_done]
    for i, step in enumerate(WORKFLOW_STEPS):
        entry = i == 0 or done_flags[i - 1]
        st = "done" if done_flags[i] else ("current" if entry else "blocked")
        steps.append({**step, "state": st})

    qc = [
        {"key": "orphans", "label": "No orphan IROs remain", "met": not orphans},
        {"key": "gating",
         "label": "All gating disclosures complete",
         "met": bool(gating_rows) and all(g["status"] == "complete" for g in gating_rows)},
        {"key": "gaps", "label": "Zero effective gaps on in-scope datapoints",
         "met": gaps == 0 and total > 0},
        {"key": "evidence", "label": "Every quantitative datapoint has a source/evidence reference",
         "met": None},  # requires per-datapoint evidence audit — surfaced, not assumed
        {"key": "mapping",
         "label": "Framework mapping (GRI/ISSB/TCFD/SDG) manually reviewed, not left as auto-suggestion only",
         "met": bool(mapping.get("reviewed", False))},
        {"key": "tagging", "label": "Tagging/export validation run with zero blocking errors",
         "met": None},  # requires a validation run artifact — surfaced, not assumed
        {"key": "signoff", "label": "Sign-off recorded from designated reviewer(s) before export",
         "met": None},
    ]

    return {
        "rule_set_version": rule_set or None,
        "rule_set_unset": not bool(rule_set),
        "reporting_period": state.get("reporting_period"),
        "summary": summary,
        "readiness_pct": readiness,
        "days_to_deadline": days_to_deadline,
        "filing_deadline": state.get("filing_deadline"),
        "standards": standards,
        "gating": gating_rows,
        "gating_complete": gating_done,
        "gating_total": len(gating_rows),
        "orphan_iros": orphans,
        "value_chain_scope": vc,
        "framework_mapping_coverage": mapping,
        "workflow": steps,
        "qc": qc,
        "critical_findings": findings,
    }
