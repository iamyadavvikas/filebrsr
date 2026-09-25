"""
CSRD / ESRS Platform Router — ESRS datapoint registry, gap analysis,
double-materiality IRO register, and ESRS sustainability-statement export
(Word / PDF).

The static ESRS Set 1 registry lives in ``app/esrs_datapoints.py`` (keyed by
the standards' own paragraph references). These endpoints persist the ORG's
live assessment into ``esrs_entries`` / ``esrs_materiality`` /
``esrs_reports`` (see supabase/migration_v23_esrs.sql). All endpoints require
a verified Bearer JWT (see ``app.auth.resolve_user_id``) and scope every read
and write to the caller's organisation.
"""

from __future__ import annotations

import io
import json
import logging
import time
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import get_user_id_from_header as get_user_id
from app.config import get_settings
from app.esrs_datapoints import (
    ESRS_DATAPOINTS,
    ESRS_STANDARDS,
    by_id,
    by_standard,
    coverage_stats,
    search,
)

router = APIRouter(prefix="/api/platform/csrd", tags=["CSRD / ESRS"])
settings = get_settings()
logger = logging.getLogger("filebrsr.csrd")

# Statuses that count as "handled" for gap analysis / readiness.
HANDLED_STATUSES = frozenset({"reported", "assessed", "not_material", "not_applicable"})
UNKNOWN_DP = "unknown_datapoint"
DEFAULT_MATERIALITY_THRESHOLD = 3.0


def get_supabase_admin():
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _resolve_org(supabase, user_id: str, org_id: Optional[str]) -> str:
    """Return the org to operate on, enforcing caller membership (403 otherwise)."""
    if user_id in ("service_role",):
        raise HTTPException(status_code=401, detail="Service key not permitted here")
    if org_id:
        member = (
            supabase.table("org_members")
            .select("id")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if member.data:
            return org_id
        alt = (
            supabase.table("organization_members")
            .select("id")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if not alt.data:
            raise HTTPException(status_code=403, detail="Not a member of this organisation")
        return org_id
    profile = (
        supabase.table("profiles")
        .select("org_id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    resolved = (profile.data or {}).get("org_id")
    if not resolved:
        raise HTTPException(status_code=400, detail="No organisation associated with your account")
    return resolved


def _validate_datapoints(ids: list[str]) -> None:
    unknown = [i for i in ids if not by_id(i)]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown datapoint ids: {unknown[:10]}")


def _phase_for_year(phase_in: str, financial_year: str) -> bool:
    """Whether a phase-in datapoint applies for the given reporting year."""
    if not phase_in:
        return True
    fy = financial_year.upper().replace("FY", "").replace(" ", "")
    if phase_in == "FY2025":
        return fy >= "2025"
    if phase_in == "FY2026":
        return fy >= "2026"
    if phase_in == "3 years":
        return True  # <750-employee cohort; treated as always in-scope for a roadmap
    return True


# ═══════════════════════════════════════════════════════════════════
# REGISTRY (static ESRS Set 1 datapoints)
# ═══════════════════════════════════════════════════════════════════


@router.get("/standards")
async def list_standards(authorization: str = Header(...)):
    """Standards with datapoint / DR counts (whole registry)."""
    _user_id = await get_user_id(authorization)
    cs = coverage_stats()
    meta = []
    for std_id, m in ESRS_STANDARDS.items():
        meta.append(
            {
                "code": m["code"],
                "standard": std_id,
                "name": m["name"],
                "order": m["order"],
                "datapoints": next(
                    (r["datapoints"] for r in cs["standards"] if r["standard"] == std_id),
                    0,
                ),
                "dr_count": next(
                    (r["dr_count"] for r in cs["standards"] if r["standard"] == std_id), 0
                ),
            }
        )
    return {
        "standards": sorted(meta, key=lambda r: r["order"]),
        "total_datapoints": cs["total_datapoints"],
        "derived_from_eu_legislation": cs["derived_from_eu_legislation"],
    }


@router.get("/registry")
async def list_registry(
    standard: Optional[str] = None,
    dr: Optional[str] = None,
    q: Optional[str] = None,
    phase_in: Optional[str] = None,
    data_type: Optional[str] = None,
    requirement: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    authorization: str = Header(...),
):
    """Paginated registry search with standard/DR/type/phase filters."""
    _user_id = await get_user_id(authorization)
    items = ESRS_DATAPOINTS if standard is None else by_standard(standard)
    if dr:
        items = [d for d in items if d["dr"] == dr]
    if q:
        items = search(q, standard=standard)
    if phase_in:
        items = [d for d in items if d["phase_in"] == phase_in]
    if data_type:
        items = [d for d in items if d["data_type"] == data_type]
    if requirement:
        items = [d for d in items if d["requirement"] == requirement]
    total = len(items)
    page = items[offset : offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "datapoints": page,
    }


@router.get("/coverage")
async def registry_coverage(authorization: str = Header(...)):
    """Whole-registry coverage stats (standards, mandatory/voluntary, phase-ins)."""
    _user_id = await get_user_id(authorization)
    return coverage_stats()


# ═══════════════════════════════════════════════════════════════════
# ENTRIES (per-datapoint assessment + data) — gap analysis units
# ═══════════════════════════════════════════════════════════════════


class EntryItem(BaseModel):
    datapoint_id: str
    status: str = "not_assessed"
    value: Optional[Any] = None
    evidence: Optional[str] = None
    source: Optional[str] = None
    source_document: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    notes: Optional[str] = None
    materiality_id: Optional[str] = None


class EntryBulk(BaseModel):
    financial_year: str
    org_id: Optional[str] = None
    entries: list[EntryItem] = Field(..., min_length=1)


class EntryUpdate(BaseModel):
    status: Optional[str] = None
    value: Optional[Any] = None
    evidence: Optional[str] = None
    source: Optional[str] = None
    source_document: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    notes: Optional[str] = None
    materiality_id: Optional[str] = None
    verified: Optional[bool] = None


@router.get("/entries")
async def list_entries(
    org_id: Optional[str] = None,
    financial_year: Optional[str] = None,
    standard: Optional[str] = None,
    status: Optional[str] = None,
    authorization: str = Header(...),
):
    """The org's saved entry rows for a (year, standard) window."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    query = sb.table("esrs_entries").select("*").eq("org_id", org_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    if status:
        query = query.eq("status", status)
    result = query.order("datapoint_id").execute()
    rows = result.data or []
    if standard:
        known = {d["id"]: True for d in by_standard(standard)}
        rows = [r for r in rows if r.get("datapoint_id") in known]
    return {"org_id": org_id, "count": len(rows), "entries": rows}


@router.post("/entries")
async def upsert_entries(req: EntryBulk, authorization: str = Header(...)):
    """Bulk upsert the org's datapoint assessments for a financial year.

    Conflict key: (org_id, financial_year, datapoint_id). Rows already saved
    are updated in place; rows without an assessment are created. The static
    registry is the source of truth for datapoint ids — unknown ids are
    rejected with a 400 before anything is written.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, req.org_id)
    _validate_datapoints([e.datapoint_id for e in req.entries])

    rows = []
    for e in req.entries:
        rows.append(
            {
                "org_id": org_id,
                "user_id": user_id,
                "financial_year": req.financial_year,
                "datapoint_id": e.datapoint_id,
                "status": e.status,
                "value": e.value,
                "evidence": e.evidence,
                "source": e.source,
                "source_document": e.source_document,
                "confidence_score": e.confidence_score,
                "notes": e.notes,
                "materiality_id": e.materiality_id,
            }
        )
    result = sb.table("esrs_entries").upsert(
        rows, on_conflict="org_id,financial_year,datapoint_id"
    ).execute()
    saved = result.data or []
    return {"org_id": org_id, "saved": len(saved), "entries": saved}


@router.put("/entries/{entry_id}")
async def update_entry(
    entry_id: str, req: EntryUpdate, authorization: str = Header(...)
):
    """Update selected fields of one entry row."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    existing = (
        sb.table("esrs_entries")
        .select("*")
        .eq("id", entry_id)
        .eq("org_id", org_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Entry not found")
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    patch["user_id"] = user_id
    result = (
        sb.table("esrs_entries")
        .update(patch)
        .eq("id", entry_id)
        .eq("org_id", org_id)
        .execute()
    )
    return {"entry": (result.data or [{}])[0]}


@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, authorization: str = Header(...)):
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    existing = (
        sb.table("esrs_entries")
        .select("id")
        .eq("id", entry_id)
        .eq("org_id", org_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Entry not found")
    sb.table("esrs_entries").delete().eq("id", entry_id).execute()
    return {"deleted": entry_id}


@router.get("/gap-analysis")
async def gap_analysis(
    org_id: Optional[str] = None,
    financial_year: Optional[str] = None,
    authorization: str = Header(...),
):
    """Readiness per ESRS standard against the full registry for a year.

    A datapoint counts as "handled" when its entry status is one of
    ``reported`` / ``assessed`` / ``not_material`` / ``not_applicable``.
    ``effective_gap`` is the number of datapoints still in
    ``not_assessed`` / ``in_progress``.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    if not financial_year:
        raise HTTPException(status_code=400, detail="financial_year is required")

    result = (
        sb.table("esrs_entries")
        .select("datapoint_id, status")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .execute()
    )
    status_by_dp = {r["datapoint_id"]: r.get("status", "not_assessed") for r in (result.data or [])}

    standards = []
    for std_id, m in ESRS_STANDARDS.items():
        dps = by_standard(std_id)
        in_scope = [d for d in dps if _phase_for_year(d["phase_in"], financial_year)]
        statuses = [status_by_dp.get(d["id"], "not_assessed") for d in dps]
        handled = sum(1 for s in statuses if s in HANDLED_STATUSES)
        standards.append(
            {
                "code": m["code"],
                "standard": std_id,
                "name": m["name"],
                "datapoints": len(dps),
                "in_scope_for_year": len(in_scope),
                "handled": handled,
                "remaining": len(dps) - handled,
                "status_counts": {
                    s: statuses.count(s)
                    for s in sorted(set(statuses))
                },
            }
        )

    handled_total = sum(s["handled"] for s in standards)
    total = sum(s["datapoints"] for s in standards)
    coverage_pct = round(handled_total / total * 100, 2) if total else 0.0
    return {
        "org_id": org_id,
        "financial_year": financial_year,
        "total_datapoints": total,
        "handled": handled_total,
        "effective_gap": total - handled_total,
        "coverage_pct": coverage_pct,
        "standards": standards,
    }


# ═══════════════════════════════════════════════════════════════════
# DOUBLE MATERIALITY (IRO register)
# ═══════════════════════════════════════════════════════════════════


class IROItem(BaseModel):
    financial_year: str
    iro_type: str
    standard: str
    title: str
    org_id: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=5)
    likelihood: Optional[int] = Field(None, ge=1, le=5)
    impact_materiality: Optional[float] = Field(None, ge=0, le=5)
    financial_materiality: Optional[float] = Field(None, ge=0, le=5)
    material: Optional[bool] = None
    status: str = "draft"


class IROUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[int] = Field(None, ge=1, le=5)
    likelihood: Optional[int] = Field(None, ge=1, le=5)
    impact_materiality: Optional[float] = Field(None, ge=0, le=5)
    financial_materiality: Optional[float] = Field(None, ge=0, le=5)
    material: Optional[bool] = None
    status: Optional[str] = None


def _material_flag(
    impact: Optional[float], financial: Optional[float], explicit: Optional[bool]
) -> bool:
    if explicit is not None:
        return explicit
    impact = impact or 0.0
    financial = financial or 0.0
    return max(impact, financial) >= DEFAULT_MATERIALITY_THRESHOLD


@router.post("/materiality")
async def create_iro(req: IROItem, authorization: str = Header(...)):
    """Register a material impact / risk / opportunity (double materiality)."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, req.org_id)
    if req.standard not in ESRS_STANDARDS:
        raise HTTPException(status_code=400, detail=f"Unknown standard {req.standard!r}")
    if req.iro_type not in ("impact", "risk", "opportunity"):
        raise HTTPException(status_code=400, detail="iro_type must be impact/risk/opportunity")
    row = {
        "org_id": org_id,
        "financial_year": req.financial_year,
        "iro_type": req.iro_type,
        "standard": req.standard,
        "title": req.title,
        "description": req.description,
        "severity": req.severity,
        "likelihood": req.likelihood,
        "impact_materiality": req.impact_materiality,
        "financial_materiality": req.financial_materiality,
        "material": _material_flag(req.impact_materiality, req.financial_materiality, req.material),
        "status": req.status,
        "created_by": user_id,
    }
    result = sb.table("esrs_materiality").insert(row).execute()
    return {"iro": (result.data or [{}])[0]}


@router.get("/materiality")
async def list_iro(
    org_id: Optional[str] = None,
    financial_year: Optional[str] = None,
    iro_type: Optional[str] = None,
    material_only: bool = False,
    authorization: str = Header(...),
):
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    query = sb.table("esrs_materiality").select("*").eq("org_id", org_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    if iro_type:
        query = query.eq("iro_type", iro_type)
    if material_only:
        query = query.eq("material", True)
    result = query.order("created_at").execute()
    return {"org_id": org_id, "count": len(result.data or []), "iro": result.data or []}


@router.put("/materiality/{iro_id}")
async def update_iro(iro_id: str, req: IROUpdate, authorization: str = Header(...)):
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    existing = (
        sb.table("esrs_materiality")
        .select("*")
        .eq("id", iro_id)
        .eq("org_id", org_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="IRO not found")
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    if "material" not in patch and any(
        k in patch for k in ("impact_materiality", "financial_materiality")
    ):
        impact = patch.get("impact_materiality", existing.data.get("impact_materiality"))
        financial = patch.get(
            "financial_materiality", existing.data.get("financial_materiality")
        )
        patch["material"] = _material_flag(impact, financial, None)
    result = (
        sb.table("esrs_materiality")
        .update(patch)
        .eq("id", iro_id)
        .eq("org_id", org_id)
        .execute()
    )
    return {"iro": (result.data or [{}])[0]}


# ═══════════════════════════════════════════════════════════════════
# REPORT EXPORT (Word / PDF sustainability statement)
# ═══════════════════════════════════════════════════════════════════

REPORT_CONTENT_TYPES = {
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


def _fetch_entries_for_year(sb, org_id: str, financial_year: str) -> dict[str, Any]:
    result = (
        sb.table("esrs_entries")
        .select("*")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .execute()
    )
    return {r["datapoint_id"]: r for r in (result.data or [])}


def _build_word_stmt(
    org_id: str,
    financial_year: str,
    entries: dict[str, Any],
) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading("ESRS Sustainability Statement", 0)
    doc.add_paragraph(f"Organisation: {org_id}")
    doc.add_paragraph(f"Reporting period: {financial_year}")
    doc.add_paragraph(f"Generated: {date.today().isoformat()}")

    doc.add_heading("Coverage summary", level=1)
    handled = sum(1 for e in entries.values() if e.get("status") in HANDLED_STATUSES)
    doc.add_paragraph(
        f"{handled} of {len(ESRS_DATAPOINTS)} ESRS datapoints assessed "
        f"({round(handled / len(ESRS_DATAPOINTS) * 100, 2)}%)."
    )

    for std_id, m in ESRS_STANDARDS.items():
        dps = by_standard(std_id)
        doc.add_heading(f"{m['code']} — {m['name']}", level=1)
        table = doc.add_table(rows=1, cols=3)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Datapoint"
        hdr[1].text = "Status"
        hdr[2].text = "Value / note"
        for dp in dps:
            row = table.add_row().cells
            row[0].text = f"{dp['id']} — {dp['name']}"
            entry = entries.get(dp["id"])
            row[1].text = entry.get("status") if entry else "not_assessed"
            value = None
            if entry and entry.get("value") is not None:
                v = entry["value"]
                value = (
                    json.dumps(v, indent=1)
                    if isinstance(v, (dict, list))
                    else str(v)
                )
            elif entry and entry.get("notes"):
                value = entry["notes"]
            row[2].text = (value or "")[:512]
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _build_pdf_stmt(
    org_id: str,
    financial_year: str,
    entries: dict[str, Any],
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    story = [
        Paragraph("ESRS Sustainability Statement", styles["Title"]),
        Paragraph(
            f"Organisation: {org_id} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Reporting period: {financial_year} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Generated: {date.today().isoformat()}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]
    handled = sum(1 for e in entries.values() if e.get("status") in HANDLED_STATUSES)
    story.append(
        Paragraph(
            f"Coverage: {handled} of {len(ESRS_DATAPOINTS)} ESRS datapoints assessed "
            f"({round(handled / len(ESRS_DATAPOINTS) * 100, 2)}%).",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    cell = styles["BodyText"]
    for std_id, m in ESRS_STANDARDS.items():
        dps = by_standard(std_id)
        story.append(Paragraph(f"{m['code']} — {m['name']}", styles["Heading2"]))
        data = [["Datapoint", "Status", "Value / note"]]
        for dp in dps:
            entry = entries.get(dp["id"])
            status = entry.get("status") if entry else "not_assessed"
            value = ""
            if entry and entry.get("value") is not None:
                v = entry["value"]
                value = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            elif entry and entry.get("notes"):
                value = entry["notes"]
            data.append(
                [
                    Paragraph(f"{dp['id']}<br/>{dp['name']}", cell),
                    Paragraph(status, cell),
                    Paragraph((value or "")[:400], cell),
                ]
            )
        t = Table(data, colWidths=[70 * mm, 32 * mm, 154 * mm], repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2A41")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    doc.build(story)
    return buf.getvalue()


class ReportRequest(BaseModel):
    financial_year: str
    org_id: Optional[str] = None
    format: str = "word"


@router.post("/reports")
async def generate_report(req: ReportRequest, authorization: str = Header(...)):
    """Generate a Word/PDF ESRS statement from the org's saved entries.

    Persists an immutable snapshot row in ``esrs_reports`` (status ready,
    content sha256). The artifact itself is regenerated deterministically from
    the DB on download, so it needs no object storage.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, req.org_id)
    fmt = req.format.lower()
    if fmt not in REPORT_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="format must be word or pdf")
    entries = _fetch_entries_for_year(sb, org_id, req.financial_year)

    t0 = time.monotonic()
    if fmt == "word":
        content = _build_word_stmt(org_id, req.financial_year, entries)
    else:
        content = _build_pdf_stmt(org_id, req.financial_year, entries)

    import hashlib

    handled = sum(1 for e in entries.values() if e.get("status") in HANDLED_STATUSES)
    coverage_pct = round(handled / len(ESRS_DATAPOINTS) * 100, 2) if ESRS_DATAPOINTS else 0.0
    row = {
        "org_id": org_id,
        "financial_year": req.financial_year,
        "report_type": "word" if fmt == "word" else "pdf",
        "status": "ready",
        "file_sha256": hashlib.sha256(content).hexdigest(),
        "file_size_bytes": len(content),
        "datapoints_covered": handled,
        "coverage_pct": coverage_pct,
        "created_by": user_id,
    }
    result = sb.table("esrs_reports").insert(row).execute()
    report = (result.data or [{}])[0]
    report_id = report.get("id")
    return {
        "report_id": report_id,
        "format": fmt,
        "file_size_bytes": len(content),
        "datapoints_covered": handled,
        "coverage_pct": coverage_pct,
        "generated_ms": int((time.monotonic() - t0) * 1000),
        "download_url": f"/api/platform/csrd/reports/{report_id}/download" if report_id else None,
    }


@router.get("/reports")
async def list_reports(
    org_id: Optional[str] = None,
    financial_year: Optional[str] = None,
    authorization: str = Header(...),
):
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    query = sb.table("esrs_reports").select("*").eq("org_id", org_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    result = query.order("created_at", desc=True).execute()
    return {"org_id": org_id, "count": len(result.data or []), "reports": result.data or []}


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str, authorization: str = Header(...)):
    """Stream the report artifact. Regenerates deterministically from the DB."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    report = (
        sb.table("esrs_reports")
        .select("*")
        .eq("id", report_id)
        .eq("org_id", org_id)
        .maybe_single()
        .execute()
    )
    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")
    row = report.data
    if row.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Report is not ready")
    entries = _fetch_entries_for_year(sb, org_id, row["financial_year"])
    content_type = REPORT_CONTENT_TYPES.get(row["report_type"])
    if row["report_type"] == "word":
        content = _build_word_stmt(org_id, row["financial_year"], entries)
    else:
        content = _build_pdf_stmt(org_id, row["financial_year"], entries)
    filename = (
        f"esrs_statement_{org_id[:8]}_{row['financial_year']}.docx"
        if row["report_type"] == "word"
        else f"esrs_statement_{org_id[:8]}_{row['financial_year']}.pdf"
    )
    response = StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
    return response
