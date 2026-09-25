"""
CSRD / ESRS Platform Router — ESRS datapoint registry, gap analysis,
double-materiality IRO register, and ESRS sustainability-statement export
(Word / PDF).

The static ESRS Set 1 registry lives in ``app/esrs_datapoints.py`` (keyed by
the standards' own paragraph references). Reference endpoints
(``/standards``, ``/registry``, ``/coverage``) are **public** — they serve
immutable regulatory data and power the logged-out demo workspace.

Assessment CRUD persists the ORG's live assessment into ``esrs_entries`` /
``esrs_materiality`` / ``esrs_reports`` (see supabase/migration_v23_esrs.sql).
Those endpoints require a verified Bearer JWT (see ``app.auth.resolve_user_id``)
and scope every read and write to the caller's organisation.
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
from app.esrs_esef import build_esef_statement

router = APIRouter(prefix="/api/platform/csrd", tags=["CSRD / ESRS"])
settings = get_settings()
logger = logging.getLogger("filebrsr.csrd")

# Statuses that count as "handled" for gap analysis / readiness.
HANDLED_STATUSES = frozenset({"reported", "assessed", "not_material", "not_applicable"})
VALID_STATUSES = frozenset(
    {"not_assessed", "in_progress", "assessed", "reported", "not_material", "not_applicable"}
)
UNKNOWN_DP = "unknown_datapoint"
DEFAULT_MATERIALITY_THRESHOLD = 3.0

# Value-chain segments an undertaking can report on. The static registry marks
# each datapoint with the segments it answers ("all" = every segment); the org
# declares its own boundary in `esrs_profiles.value_chain_scope`, and gap
# analysis only counts datapoints inside that boundary.
VALUE_CHAIN_SEGMENTS = ("own_operations", "upstream", "downstream")


def _value_chain_segments(dp: dict) -> set[str]:
    """Segments a datapoint answers: "all" (the registry default) = all three."""
    raw = (dp.get("value_chain") or "all").strip()
    if raw == "all":
        return set(VALUE_CHAIN_SEGMENTS)
    parts = {p.strip() for p in raw.split(",") if p.strip()}
    return parts if parts else set(VALUE_CHAIN_SEGMENTS)


def _status_handled(status: str, materiality_id: Optional[str], has_material_iro: bool) -> bool:
    """Whether an entry status closes the gap for its datapoint this year.

    ``not_material`` only closes the gap once it has a materiality basis: the
    entry must be linked to an IRO from the double-materiality register (the
    row that shows the IRO is below threshold). Orgs that have declared no
    material IRO for the year are exempt from that substantiation rule.
    """
    if status in ("reported", "assessed", "not_applicable"):
        return True
    if status == "not_material":
        return not has_material_iro or bool(materiality_id)
    return False


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
async def list_standards():
    """Standards with datapoint / DR counts (whole registry). Public."""
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
    value_chain: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
):
    """Paginated registry search with standard/DR/type/phase/VC filters. Public."""
    items = ESRS_DATAPOINTS if standard is None else by_standard(standard)
    if dr:
        items = [d for d in items if d["dr"] == dr]
    if data_type:
        items = [d for d in items if d["data_type"] == data_type]
    if requirement:
        items = [d for d in items if d["requirement"] == requirement]
    if phase_in:
        items = [d for d in items if d["phase_in"] == phase_in]
    if value_chain:
        wanted = {p.strip() for p in value_chain.split(",") if p.strip()}
        items = [d for d in items if _value_chain_segments(d) & wanted]
    if q:
        hits = {d["id"] for d in search(q, standard=standard)}
        items = [d for d in items if d["id"] in hits]
    total = len(items)
    page = items[offset : offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "datapoints": page,
    }


@router.get("/coverage")
async def registry_coverage():
    """Whole-registry coverage stats (standards, mandatory/voluntary, phase-ins). Public."""
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
    invalid = sorted({e.status for e in req.entries} - VALID_STATUSES)
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {', '.join(invalid)} (allowed: {', '.join(sorted(VALID_STATUSES))})",
        )

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
    if req.status is not None and req.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {req.status} (allowed: {', '.join(sorted(VALID_STATUSES))})",
        )
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
    value_chain: Optional[str] = None,
    authorization: str = Header(...),
):
    """Readiness per ESRS standard for a year, honoring phase-in and scope.

    A datapoint is **in scope** for a year when its phase-in applies AND its
    value-chain segments intersect the org's declared boundary (``value_chain``
    query param beats the org profile; both default to the full value chain).
    Only in-scope datapoints feed ``handled`` / ``remaining`` / ``coverage_pct``,
    so phase-in and value-chain policies actually move the numbers instead of
    being decorative.

    A datapoint counts as handled when its entry status is ``reported`` /
    ``assessed`` / ``not_applicable``, or ``not_material`` backed by the org's
    double-materiality register (linked IRO) once the org has any material IRO.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    if not financial_year:
        raise HTTPException(status_code=400, detail="financial_year is required")

    in_scope_ids, entries_map, scope, has_material_iro = _scoped_state(
        sb, org_id, financial_year, value_chain
    )

    standards = []
    for std_id, m in ESRS_STANDARDS.items():
        scoped = [d for d in by_standard(std_id) if d["id"] in in_scope_ids]
        handled = 0
        statuses: dict[str, int] = {}
        for d in scoped:
            e = entries_map.get(d["id"], {})
            status = e.get("status", "not_assessed")
            if _status_handled(status, e.get("materiality_id"), has_material_iro):
                handled += 1
            statuses[status] = statuses.get(status, 0) + 1
        standards.append(
            {
                "code": m["code"],
                "standard": std_id,
                "name": m["name"],
                "datapoints": len(scoped),
                "remaining": len(scoped) - handled,
                "handled": handled,
                "status_counts": {s: statuses[s] for s in sorted(statuses)},
            }
        )

    in_scope_total = sum(s["datapoints"] for s in standards)
    handled_total = sum(s["handled"] for s in standards)
    coverage_pct = round(handled_total / in_scope_total * 100, 2) if in_scope_total else 0.0
    return {
        "org_id": org_id,
        "financial_year": financial_year,
        "registry_datapoints": len(ESRS_DATAPOINTS),
        "total_datapoints": in_scope_total,
        "value_chain_scope": sorted(scope),
        "has_material_iro": has_material_iro,
        "handled": handled_total,
        "effective_gap": in_scope_total - handled_total,
        "coverage_pct": coverage_pct,
        "standards": standards,
    }


def _active_scope(sb, org_id: str, value_chain: Optional[str]) -> set[str]:
    """Resolve the org's value-chain boundary for a gap analysis.

    An explicit ``value_chain`` query param (comma-separated segments) wins;
    otherwise the org profile (``esrs_profiles.value_chain_scope``) is used,
    falling back to the full value chain when the profile is missing.
    """
    if value_chain:
        wanted = set(VALUE_CHAIN_SEGMENTS) & {p.strip() for p in value_chain.split(",") if p.strip()}
        if wanted:
            return wanted
    try:
        res = (
            sb.table("esrs_profiles")
            .select("value_chain_scope")
            .eq("org_id", org_id)
            .maybe_single()
            .execute()
        )
        stored = (res.data or {}).get("value_chain_scope")
    except Exception:  # noqa: BLE001 - profile table may not exist yet
        stored = None
    if stored:
        wanted = set(VALUE_CHAIN_SEGMENTS) & set(stored)
        if wanted:
            return wanted
    return set(VALUE_CHAIN_SEGMENTS)


def _scoped_state(
    sb, org_id: str, financial_year: str, value_chain: Optional[str] = None
) -> tuple[set[str], dict[str, dict], set[str], bool]:
    """One source of truth for what is in scope for an org/year.

    Returns ``(in_scope_ids, entries_map, scope, has_material_iro)`` where
    ``in_scope_ids`` are the datapoints whose phase-in applies for the year and
    whose value-chain segments intersect the org's boundary; ``entries_map`` is
    the org's saved rows keyed by datapoint; ``has_material_iro`` tells whether
    the org has declared a material IRO (gate for ``not_material``
    substantiation). Gap analysis and report export share this so their
    coverage numbers always agree.
    """
    resp = (
        sb.table("esrs_entries")
        .select("*")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .execute()
    )
    entries_map = {r["datapoint_id"]: r for r in (resp.data or [])}
    scope = _active_scope(sb, org_id, value_chain)
    in_scope_ids = {
        d["id"]
        for d in ESRS_DATAPOINTS
        if _phase_for_year(d.get("phase_in"), financial_year)
        and bool(_value_chain_segments(d) & scope)
    }
    material_rows = (
        sb.table("esrs_materiality")
        .select("id")
        .eq("org_id", org_id)
        .eq("financial_year", financial_year)
        .eq("material", True)
        .execute()
    )
    has_material_iro = bool(material_rows.data)
    return in_scope_ids, entries_map, scope, has_material_iro


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


@router.delete("/materiality/{iro_id}")
async def delete_iro(iro_id: str, authorization: str = Header(...)):
    """Remove an IRO from the double-materiality register (org-scoped).

    Also detaches the IRO from any datapoints linked to it, so a deleted IRO
    never leaves dangling ``materiality_id`` references in ``esrs_entries``
    (defence-in-depth on top of the FK's ``on delete set null``).
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    existing = (
        sb.table("esrs_materiality")
        .select("id")
        .eq("id", iro_id)
        .eq("org_id", org_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="IRO not found")
    sb.table("esrs_materiality").delete().eq("id", iro_id).execute()
    sb.table("esrs_entries").update({"materiality_id": None}).eq("materiality_id", iro_id).execute()
    return {"deleted": iro_id}


# ═══════════════════════════════════════════════════════════════════
# ORG SCOPE (value-chain boundary for phase/scoped gap analysis)
# ═══════════════════════════════════════════════════════════════════


class ScopeUpdate(BaseModel):
    value_chain_scope: list[str]


@router.get("/scope")
async def get_scope(org_id: Optional[str] = None, authorization: str = Header(...)):
    """The org's declared value-chain boundary (defaults to the full chain)."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    try:
        res = (
            sb.table("esrs_profiles")
            .select("value_chain_scope")
            .eq("org_id", org_id)
            .maybe_single()
            .execute()
        )
        stored = (res.data or {}).get("value_chain_scope")
    except Exception:  # noqa: BLE001 - profile table may not exist yet
        stored = None
    scope = [s for s in (stored or []) if s in VALUE_CHAIN_SEGMENTS]
    return {
        "org_id": org_id,
        "value_chain_scope": scope or list(VALUE_CHAIN_SEGMENTS),
    }


@router.put("/scope")
async def set_scope(
    req: ScopeUpdate, org_id: Optional[str] = None, authorization: str = Header(...)
):
    """Persist the org's value-chain boundary (deduped, subset of the three)."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    if not req.value_chain_scope:
        raise HTTPException(status_code=400, detail="value_chain_scope cannot be empty")
    invalid = set(req.value_chain_scope) - set(VALUE_CHAIN_SEGMENTS)
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid value chain segments: {', '.join(sorted(invalid))}. "
                f"Allowed: {', '.join(VALUE_CHAIN_SEGMENTS)}"
            ),
        )
    scope = list(dict.fromkeys(req.value_chain_scope))
    result = sb.table("esrs_profiles").upsert(
        {"org_id": org_id, "value_chain_scope": scope}, on_conflict="org_id"
    ).execute()
    row = (result.data or [{}])[0]
    return {"org_id": org_id, "value_chain_scope": row.get("value_chain_scope") or scope}


# ═══════════════════════════════════════════════════════════════════
# REPORT EXPORT (Word / PDF sustainability statement)
# ═══════════════════════════════════════════════════════════════════

REPORT_CONTENT_TYPES = {
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "esef": "application/xhtml+xml",
}


def _resolve_entity(sb, org_id: str) -> dict:
    """Org entity identity for filing (name + LEI/CIN identifier + scheme)."""
    org = (
        sb.table("organizations")
        .select("id, name, cin, lei")
        .eq("id", org_id)
        .maybe_single()
        .execute()
    )
    row = org.data or {}
    name = row.get("name") or f"Organization {org_id[:8]}"
    identifier = row.get("lei") or row.get("cin") or org_id
    if row.get("lei"):
        scheme = "http://xbrl.efrag.org/LEI"
    elif row.get("cin"):
        scheme = "http://www.mca.gov.in/CIN"
    else:
        scheme = "filebrsr:org"
    return {"name": str(name), "identifier": str(identifier), "scheme": str(scheme)}


def _report_assurance(row: dict) -> dict:
    return {
        "status": row.get("assurance_status") or "none",
        "firm": row.get("assurance_firm") or "",
        "date": row.get("assurance_date") or "",
        "statement": row.get("assurance_statement") or "",
    }


def _entry_payload(row: dict) -> dict:
    """Shrink an ``esrs_entries`` row to the fields the ESEF builder needs."""
    return {
        "datapoint_id": row.get("datapoint_id"),
        "status": row.get("status") or "not_assessed",
        "value": row.get("value"),
        "evidence": row.get("evidence") or "",
        "notes": row.get("notes") or "",
    }


def _scoped_handled(
    in_scope_ids: set[str], entries_map: dict[str, Any], has_material_iro: bool
) -> int:
    """Count in-scope datapoints whose entry closes the gap this year.

    Mirrors ``_status_handled`` so report coverage matches gap analysis
    (phase-in + value-chain scope + substantiated ``not_material``).
    """
    return sum(
        1
        for dp_id in in_scope_ids
        if _status_handled(
            entries_map.get(dp_id, {}).get("status", "not_assessed"),
            entries_map.get(dp_id, {}).get("materiality_id"),
            has_material_iro,
        )
    )


def _build_word_stmt(
    org_id: str,
    financial_year: str,
    entries: dict[str, Any],
    in_scope_ids: set[str],
    has_material_iro: bool,
) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading("ESRS Sustainability Statement", 0)
    doc.add_paragraph(f"Organisation: {org_id}")
    doc.add_paragraph(f"Reporting period: {financial_year}")
    doc.add_paragraph(f"Generated: {date.today().isoformat()}")

    doc.add_heading("Coverage summary", level=1)
    handled = _scoped_handled(in_scope_ids, entries, has_material_iro)
    doc.add_paragraph(
        f"{handled} of {len(in_scope_ids)} in-scope ESRS datapoints assessed "
        f"for {financial_year} ({round(handled / len(in_scope_ids) * 100, 2)}%)."
    )

    for std_id, m in ESRS_STANDARDS.items():
        dps = [d for d in by_standard(std_id) if d["id"] in in_scope_ids]
        if not dps:
            continue
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
    in_scope_ids: set[str],
    has_material_iro: bool,
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
    handled = _scoped_handled(in_scope_ids, entries, has_material_iro)
    story.append(
        Paragraph(
            f"Coverage: {handled} of {len(in_scope_ids)} in-scope ESRS datapoints "
            f"assessed for {financial_year} "
            f"({round(handled / len(in_scope_ids) * 100, 2)}%).",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    cell = styles["BodyText"]
    for std_id, m in ESRS_STANDARDS.items():
        dps = [d for d in by_standard(std_id) if d["id"] in in_scope_ids]
        if not dps:
            continue
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
        raise HTTPException(status_code=400, detail="format must be word, pdf, or esef")
    in_scope_ids, entries_map, scope, has_material_iro = _scoped_state(
        sb, org_id, req.financial_year
    )

    t0 = time.monotonic()
    if fmt == "word":
        content = _build_word_stmt(
            org_id, req.financial_year, entries_map, in_scope_ids, has_material_iro
        )
    elif fmt == "pdf":
        content = _build_pdf_stmt(
            org_id, req.financial_year, entries_map, in_scope_ids, has_material_iro
        )
    else:
        entity = _resolve_entity(sb, org_id)
        entries = [_entry_payload(e) for e in sorted(entries_map.values(), key=lambda r: r["datapoint_id"])]
        handled = _scoped_handled(in_scope_ids, entries_map, has_material_iro)
        scope_total = len(in_scope_ids)
        content = build_esef_statement(
            financial_year=req.financial_year,
            org_id=org_id,
            org_name=entity["name"],
            entity_identifier=entity["identifier"],
            entity_scheme=entity["scheme"],
            entries=entries,
            in_scope_ids=sorted(in_scope_ids),
            coverage_pct=round(handled / scope_total * 100, 2) if scope_total else 0.0,
            value_chain_scope=sorted(scope),
        )

    import hashlib

    handled = _scoped_handled(in_scope_ids, entries_map, has_material_iro)
    scope_total = len(in_scope_ids)
    coverage_pct = round(handled / scope_total * 100, 2) if scope_total else 0.0
    row = {
        "org_id": org_id,
        "financial_year": req.financial_year,
        "report_type": "word" if fmt == "word" else ("pdf" if fmt == "pdf" else "esef"),
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
    in_scope_ids, entries_map, _, has_material_iro = _scoped_state(
        sb, org_id, row["financial_year"]
    )
    content_type = REPORT_CONTENT_TYPES.get(row["report_type"])
    if row["report_type"] == "word":
        content = _build_word_stmt(
            org_id, row["financial_year"], entries_map, in_scope_ids, has_material_iro
        )
    elif row["report_type"] == "pdf":
        content = _build_pdf_stmt(
            org_id, row["financial_year"], entries_map, in_scope_ids, has_material_iro
        )
    else:
        entity = _resolve_entity(sb, org_id)
        _, _, scope, _ = _scoped_state(sb, org_id, row["financial_year"])
        content = build_esef_statement(
            financial_year=row["financial_year"],
            org_id=org_id,
            org_name=entity["name"],
            entity_identifier=entity["identifier"],
            entity_scheme=entity["scheme"],
            entries=[_entry_payload(e) for e in sorted(entries_map.values(), key=lambda r: r["datapoint_id"])],
            in_scope_ids=sorted(in_scope_ids),
            coverage_pct=row.get("coverage_pct") or 0.0,
            value_chain_scope=sorted(scope),
            assurance=_report_assurance(row),
        )
    filename = (
        f"esrs_statement_{org_id[:8]}_{row['financial_year']}.docx"
        if row["report_type"] == "word"
        else (
            f"esrs_statement_{org_id[:8]}_{row['financial_year']}.pdf"
            if row["report_type"] == "pdf"
            else f"esrs_statement_{org_id[:8]}_{row['financial_year']}.html"
        )
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


class AssuranceRequest(BaseModel):
    status: str = "none"  # none | limited | reasonable
    firm: Optional[str] = None
    date: Optional[str] = None
    statement: Optional[str] = None


ASSURANCE_STATUSES = {"none", "limited", "reasonable"}


@router.post("/reports/{report_id}/assurance")
async def change_assurance(
    report_id: str, req: AssuranceRequest, authorization: str = Header(...)
):
    """Attach a limited/reasonable assurance opinion to a ready report."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    status = req.status.lower()
    if status not in ASSURANCE_STATUSES:
        raise HTTPException(status_code=400, detail="status must be none, limited, or reasonable")
    report = (
        sb.table("esrs_reports")
        .select("id, org_id, report_type, status")
        .eq("id", report_id)
        .eq("org_id", org_id)
        .maybe_single()
        .execute()
    )
    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.data.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Report is not ready")
    if status == "none":
        patch = {"assurance_status": "none", "assurance_firm": None,
                 "assurance_date": None, "assurance_statement": None}
    else:
        patch = {
            "assurance_status": status,
            "assurance_firm": req.firm,
            "assurance_date": req.date,
            "assurance_statement": req.statement,
        }
    result = sb.table("esrs_reports").update(patch).eq("id", report_id).execute()
    return {"report_id": report_id, "assurance": (result.data or [{}])[0].get("assurance_status")}


class SubmitRequest(BaseModel):
    filing_ref: Optional[str] = None
    notes: Optional[str] = None


@router.post("/reports/{report_id}/submit")
async def submit_report(report_id: str, req: SubmitRequest, authorization: str = Header(...)):
    """Package the ESEF report (single-file XHTML + manifest + sha256) for filing.

    Requires report_type ``esef``, status ``ready``, and a ``limited`` or
    ``reasonable`` assurance opinion (ESRS-required precondition). Records the
    submission locally; when ``OAM_FILING_ENDPOINT`` is configured, posts a
    manifest webhook and records the returned reference.
    """
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
    row = report.data
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if row.get("report_type") != "esef":
        raise HTTPException(status_code=400, detail="Only ESEF reports can be submitted for filing")
    if row.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Report is not ready")
    assurance = _report_assurance(row)
    if assurance["status"] not in {"limited", "reasonable"}:
        raise HTTPException(
            status_code=409,
            detail="A limited or reasonable assurance opinion is required before submission",
        )

    in_scope_ids, entries_map, scope, has_material_iro = _scoped_state(
        sb, org_id, row["financial_year"]
    )
    entity = _resolve_entity(sb, org_id)
    content = build_esef_statement(
        financial_year=row["financial_year"],
        org_id=org_id,
        org_name=entity["name"],
        entity_identifier=entity["identifier"],
        entity_scheme=entity["scheme"],
        entries=[_entry_payload(e) for e in sorted(entries_map.values(), key=lambda r: r["datapoint_id"])],
        in_scope_ids=sorted(in_scope_ids),
        coverage_pct=row.get("coverage_pct") or 0.0,
        value_chain_scope=sorted(scope),
        assurance=_report_assurance(row),
    )

    import hashlib
    import io as _io
    import zipfile

    sha256 = hashlib.sha256(content).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "filing_ref": req.filing_ref or f"{org_id[:8]}-{row['financial_year']}",
        "entity_name": entity["name"],
        "entity_identifier": {"scheme": entity["scheme"], "value": entity["identifier"]},
        "financial_year": row["financial_year"],
        "report_id": report_id,
        "report_sha256": sha256,
        "report_size_bytes": len(content),
        "datapoints_covered": row.get("datapoints_covered"),
        "coverage_pct": row.get("coverage_pct"),
        "assurance": dict(assurance),
        "prepared_at": row.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": req.notes or "",
    }
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("esrs_statement.html", content)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        zf.writestr("sha256.txt", sha256)
    package = buf.getvalue()

    status = "queued_local"
    submission_ref = manifest["filing_ref"]
    settings = get_settings()
    if settings.OAM_FILING_ENDPOINT:
        import urllib.request

        status = "submitted"
        payload = json.dumps(manifest, default=str).encode("utf-8")
        try:
            with urllib.request.urlopen(
                settings.OAM_FILING_ENDPOINT,
                data=payload,
                timeout=15,
                headers={"Content-Type": "application/json", "User-Agent": "filebrsr-csrd/1.0"},
            ) as resp:
                body = resp.read().decode("utf-8", "replace")
                submission_ref = body.strip() or submission_ref
        except Exception as exc:  # noqa: BLE001    local-first: never fail the API on webhook trouble
            status = f"webhook_failed:{type(exc).__name__}"

    sub_row = {
        "org_id": org_id,
        "report_id": report_id,
        "financial_year": row["financial_year"],
        "status": status,
        "submission_ref": submission_ref,
        "manifest_sha256": hashlib.sha256(package).hexdigest(),
        "package_sha256": sha256,
        "submitted_by": user_id,
    }
    result = sb.table("esrs_submissions").insert(sub_row).execute()
    submission = (result.data or [{}])[0]
    return {
        "submission_id": submission.get("id"),
        "status": status,
        "submission_ref": submission_ref,
        "manifest_sha256": sub_row["manifest_sha256"],
        "package_bytes": len(package),
    }


@router.get("/submissions")
async def list_submissions(
    org_id: Optional[str] = None,
    financial_year: Optional[str] = None,
    authorization: str = Header(...),
):
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, org_id)
    query = sb.table("esrs_submissions").select("*").eq("org_id", org_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    result = query.order("created_at", desc=True).execute()
    return {"org_id": org_id, "count": len(result.data or []), "submissions": result.data or []}
