"""ISAE 3000 workpaper catalog + provider registry logic (BRSR Core).

The checkpoint catalog is data: common checkpoints for every engagement,
plus level-specific procedures (limited vs reasonable), plus per-attribute
evidence hints so preparers know *what* to attach. :func:`instantiate`
seeds one workpaper row per (KPI, checkpoint) idempotently; progress rolls
up per FY for the assurance dashboard.
"""

from __future__ import annotations

from datetime import date
from typing import Any

LEVELS = ("limited", "reasonable")

# Partner rotation clock (CA Act norms): flag rotation due after N years.
ROTATION_YEARS = 10

COMMON_CHECKPOINTS: list[dict[str, str]] = [
    {"code": "C1", "title": "Engagement scope & criteria agreed",
     "detail": "Confirm the 9-attribute BRSR Core scope, FY boundary, and applicable criteria (SEBI circulars + ISF standards) in the engagement letter."},
    {"code": "C2", "title": "Risk assessment",
     "detail": "Document where material misstatement is most likely (new meters, estimates, value-chain inputs) and the response planned."},
    {"code": "C3", "title": "Evidence tie-out",
     "detail": "Tie each reported KPI value to its source document/extract; record reference ids."},
    {"code": "C4", "title": "Management representations",
     "detail": "Obtain written representations covering completeness, methods, and subsequent events."},
    {"code": "C5", "title": "Conclusion",
     "detail": "Record the conclusion per KPI and the overall opinion basis (limited vs reasonable)."},
]

LIMITED_CHECKPOINTS: list[dict[str, str]] = [
    {"code": "L1", "title": "Inquiry & analytical procedures",
     "detail": "Inquiries of process owners plus analytics (trends, ratios) sufficient for limited assurance."},
    {"code": "L2", "title": "Variance review",
     "detail": "Review YoY variances above threshold; obtain explanations for outliers."},
]

REASONABLE_CHECKPOINTS: list[dict[str, str]] = [
    {"code": "R1", "title": "Substantive testing plan",
     "detail": "Define tests of details for each KPI: population, procedure, sample basis."},
    {"code": "R2", "title": "Sampling rationale",
     "detail": "Document sampling method, size rationale, and selection (esp. value-chain partners)."},
    {"code": "R3", "title": "Control walkthrough",
     "detail": "Walk through metering/calculation controls; note deficiencies and compensating checks."},
    {"code": "R4", "title": "Analytical procedures with thresholds",
     "detail": "Set expectation thresholds (e.g. energy↔GHG implied factor); investigate breaches."},
    {"code": "R5", "title": "Subsequent-events review",
     "detail": "Review events after FY-end up to report date for adjusting/non-adjusting items."},
]

# Per-attribute evidence hints (what to attach for C3).
ATTRIBUTE_EVIDENCE: dict[int, str] = {
    1: "Fuel invoices, CEMS/meter logs, CEA emission factors, fugitive-leak registers, carbon-credit retirement proofs.",
    2: "Water utility bills, meter readings, discharge lab reports by destination/treatment level.",
    3: "Electricity bills, renewable PPAs/RECs, fuel logs, energy audit reports.",
    4: "Weighbridge slips, waste manifests (SPCB), recycler certificates, disposal vendor invoices.",
    5: "Payroll registers, LTIFR calculation sheets, fatality investigation reports, wellbeing spend ledger.",
    6: "Wage registers by gender, ICC minutes, POSH complaint register with disposal evidence.",
    7: "MSME/Udyam certificates, sourcing ledger (MSME/in-India split), payroll location split.",
    8: "Breach incident log, IT security assessment, accounts-payable ageing.",
    9: "Purchase/sales concentration workings, dealer/distributor master, RPT board approvals.",
}


def checkpoints_for(attribute: int, level: str) -> list[dict[str, str]]:
    """Ordered checkpoint list for an attribute at an assurance level."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, got {level!r}")
    out = [dict(c) for c in COMMON_CHECKPOINTS]
    out += [dict(c) for c in (LIMITED_CHECKPOINTS if level == "limited" else REASONABLE_CHECKPOINTS)]
    hint = ATTRIBUTE_EVIDENCE.get(attribute)
    if hint:
        out.append({"code": "E1", "title": "Attribute evidence pack",
                    "detail": f"Attach: {hint}"})
    return out


def catalog_size(level: str) -> int:
    return len(checkpoints_for(1, level))


def _kpi_attribute(kpi_code: str, kpi_lookup) -> int:
    kpi = kpi_lookup(kpi_code)
    if kpi is None:
        raise ValueError(f"unknown KPI {kpi_code!r}")
    return int(kpi["attribute"])


def instantiate(sb, org_id: str, financial_year: str, kpi_codes: list[str], level: str, kpi_lookup) -> dict[str, int]:
    """Seed workpaper rows for KPIs; existing rows are left untouched.

    Returns {"created": n, "skipped": m, "checkpoints_per_kpi": k}.
    """
    created = 0
    skipped = 0
    per_kpi = 0
    for code in kpi_codes:
        attr = _kpi_attribute(code, kpi_lookup)
        cps = checkpoints_for(attr, level)
        per_kpi = len(cps)
        for cp in cps:
            res = sb.table("assurance_workpapers").select("id").eq("org_id", org_id).eq(
                "financial_year", financial_year).eq("kpi_code", code).eq(
                "checkpoint", cp["code"]).execute()
            data = res.data if res is not None else None
            if data:
                skipped += 1
                continue
            sb.table("assurance_workpapers").insert({
                "org_id": org_id,
                "financial_year": financial_year,
                "kpi_code": code,
                "checkpoint": cp["code"],
                "detail": f"{cp['title']}: {cp['detail']}",
                "status": "open",
            }).execute()
            created += 1
    return {"created": created, "skipped": skipped, "checkpoints_per_kpi": per_kpi}


def list_workpapers(sb, org_id: str, financial_year: str, kpi_code: str | None = None) -> list[dict[str, Any]]:
    q = sb.table("assurance_workpapers").select("*").eq("org_id", org_id).eq("financial_year", financial_year)
    if kpi_code:
        q = q.eq("kpi_code", kpi_code)
    res = q.order("kpi_code").execute()
    return list(res.data or []) if res is not None else []


def update_workpaper(sb, org_id: str, financial_year: str, kpi_code: str, checkpoint: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"status", "evidence_ref", "detail", "prepared_by", "reviewed_by"}
    clean = {k: v for k, v in patch.items() if k in allowed}
    if clean.get("status") not in (None, "open", "closed", "not_applicable"):
        raise ValueError(f"invalid status {clean.get('status')!r}")
    from datetime import datetime, timezone

    if clean.get("status") == "closed" and "closed_at" not in clean:
        clean["closed_at"] = datetime.now(timezone.utc).isoformat()
    res = sb.table("assurance_workpapers").update(clean).eq("org_id", org_id).eq(
        "financial_year", financial_year).eq("kpi_code", kpi_code).eq("checkpoint", checkpoint).execute()
    rows = list(res.data or []) if res is not None else []
    return rows[0] if rows else None


def progress(sb, org_id: str, financial_year: str) -> dict[str, Any]:
    rows = list_workpapers(sb, org_id, financial_year)
    by_kpi: dict[str, dict[str, int]] = {}
    for r in rows:
        slot = by_kpi.setdefault(r["kpi_code"], {"total": 0, "closed": 0})
        slot["total"] += 1
        if r.get("status") in ("closed", "not_applicable"):
            slot["closed"] += 1
    total = sum(s["total"] for s in by_kpi.values())
    closed = sum(s["closed"] for s in by_kpi.values())
    return {
        "financial_year": financial_year,
        "kpis": len(by_kpi),
        "checkpoints": total,
        "closed": closed,
        "open": total - closed,
        "coverage_pct": round(100.0 * closed / total, 2) if total else 0.0,
        "by_kpi": by_kpi,
    }


def list_providers(sb, org_id: str) -> list[dict[str, Any]]:
    res = sb.table("assurance_providers").select("*").eq("org_id", org_id).order("firm_name").execute()
    return list(res.data or []) if res is not None else []


def upsert_provider(sb, org_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    row = dict(payload)
    row["org_id"] = org_id
    res = sb.table("assurance_providers").upsert(row, on_conflict="org_id,firm_name,partner_name").execute()
    rows = list(res.data or []) if res is not None else []
    return rows[0] if rows else dict(row)


def rotation_due(provider: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Rotation clock: due when tenure reaches ROTATION_YEARS."""
    today = today or date.today()
    started = (provider.get("rotation_started_on") or "")[:10]
    try:
        y, m, d = (int(x) for x in started.split("-"))
        tenure = (today - date(y, m, d)).days / 365.25
    except (ValueError, AttributeError):
        return {"due": False, "tenure_years": None, "reason": "rotation start not set"}
    due = tenure >= ROTATION_YEARS
    return {
        "due": due,
        "tenure_years": round(tenure, 1),
        "reason": f"partner tenure {tenure:.1f}y vs {ROTATION_YEARS}y limit" if due else "within limit",
    }
