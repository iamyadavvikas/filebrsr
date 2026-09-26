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
import secrets
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import GUEST_TOKEN_PREFIX
from app.auth import get_user_id_from_header as get_user_id
from app.config import get_settings
from app.esef_arelle import apply_arelle
from app.esrs_datapoints import (
    ESRS_DATAPOINTS,
    ESRS_STANDARDS,
    by_id,
    by_standard,
    coverage_stats,
    search,
)
from app.esrs_esef import build_esef_statement
from app.esrs_validate import validate_esef_statement

router = APIRouter(prefix="/api/platform/csrd", tags=["CSRD / ESRS"])
settings = get_settings()
logger = logging.getLogger("filebrsr.csrd")

# Statuses that count as "handled" for gap analysis / readiness.
HANDLED_STATUSES = frozenset({"reported", "assessed", "not_material", "not_applicable"})
VALID_STATUSES = frozenset({"not_assessed", "in_progress", "assessed", "reported", "not_material", "not_applicable"})
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


def _is_guest(user_id: str) -> bool:
    """True when the identity is an opaque guest-sandbox session token."""
    return user_id.startswith(GUEST_TOKEN_PREFIX)


def _subject_id(user_id: str) -> str | None:
    """Provenance user id for a row; guests have none (real profiles FK)."""
    return None if _is_guest(user_id) else user_id


def _resolve_guest_org(supabase, token: str) -> str:
    """Map a guest session token to its sandbox org, validating liveness.

    An expired or unknown token yields 401. The row is deleted on expiry so a
    repeat call fails closed instead of silently recycling a dead workspace.
    """
    row = (
        supabase.table("esrs_guest_sessions")
        .select("org_id, expires_at")
        .eq("token", token)
        .maybe_single()
        .execute()
    )
    if row is None or not row.data:
        raise HTTPException(status_code=401, detail="Invalid or expired guest session")
    raw_exp = row.data.get("expires_at")
    try:
        expires = datetime.fromisoformat(str(raw_exp).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        expires = datetime.min.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        supabase.table("esrs_guest_sessions").delete().eq("token", token).execute()
        raise HTTPException(status_code=401, detail="Guest session expired")
    return row.data["org_id"]


def _resolve_org(supabase, user_id: str, org_id: Optional[str]) -> str:
    """Return the org to operate on, enforcing caller membership (403 otherwise)."""
    if user_id in ("service_role",):
        raise HTTPException(status_code=401, detail="Service key not permitted here")
    if _is_guest(user_id):
        if not get_settings().CSRD_GUEST_ENABLED:
            raise HTTPException(status_code=403, detail="Guest workspace is disabled")
        sandbox_org = _resolve_guest_org(supabase, user_id)
        if org_id and org_id != sandbox_org:
            raise HTTPException(
                status_code=403,
                detail="Guest sessions can only access their own sandbox workspace",
            )
        return sandbox_org
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
    profile = supabase.table("profiles").select("org_id").eq("id", user_id).maybe_single().execute()
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
# GUEST SANDBOX (open-to-all exploration, no sign-in)
# ═══════════════════════════════════════════════════════════════════

GUEST_ORG_NAME = "Acme Sandbox Ltd."
SESSION_GRACE_MINUTES = 5


class SeedRequest(BaseModel):
    financial_year: str = "FY2025"


def _prune_expired_guests(sb) -> None:
    """Delete expired guest sessions (cascades to their sandbox org + rows)."""
    now = datetime.now(timezone.utc)
    rows = sb.table("esrs_guest_sessions").select("token, expires_at").execute()
    for r in rows.data or []:
        try:
            expires = datetime.fromisoformat(str(r.get("expires_at")).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if expires <= now:
            sb.table("esrs_guest_sessions").delete().eq("token", r.get("token")).execute()


def _guest_rate_ok(sb) -> bool:
    """Rolling one-minute cap on guest session minting (abuse guard)."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    rows = sb.table("esrs_guest_sessions").select("created_at").execute()
    count = 0
    for r in rows.data or []:
        created = _parse_ts(r.get("created_at"))
        if created is not None and created >= cutoff:
            count += 1
    return count < max(1, get_settings().CSRD_GUEST_RATE_MINUTE)


def _parse_ts(raw) -> datetime | None:
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@router.post("/guest/session")
async def create_guest_session():
    """Mint a throwaway sandbox workspace for a logged-out visitor.

    Returns an opaque bearer token backed by a fresh sandbox organisation
    (``esrs_guest_sessions``). The token is passed as the ``Authorization``
    Bearer credential on every CSRD call; the backend scopes every read and
    write to the session's own org, so guests can explore the entire workflow
    without any sign-in (and without touching another guest's data). Expired
    sessions are pruned here so storage is bounded.
    """
    if not get_settings().CSRD_GUEST_ENABLED:
        raise HTTPException(status_code=404, detail="Guest workspace is disabled")
    sb = get_supabase_admin()
    _prune_expired_guests(sb)
    if not _guest_rate_ok(sb):
        raise HTTPException(status_code=429, detail="Too many guest workspaces. Try again shortly.")
    token = f"{GUEST_TOKEN_PREFIX}{secrets.token_urlsafe(24)}"
    slug = f"guest-sandbox-{secrets.token_urlsafe(6)}"
    org = (
        sb.table("organizations")
        .insert({"name": GUEST_ORG_NAME, "slug": slug, "plan": "starter"})
        .execute()
    )
    org_id = (org.data or [{}])[0].get("id")
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=max(1, get_settings().CSRD_GUEST_TTL_HOURS))).isoformat()
    sb.table("esrs_guest_sessions").insert({"token": token, "org_id": org_id, "expires_at": expires_at}).execute()
    return {"token": token, "org_id": org_id, "expires_at": expires_at, "mode": "guest"}


def _seed_datapoint_ids(standard: str, drs: set[str]) -> list[str]:
    return [d["id"] for d in by_standard(standard) if (d.get("dr") or "") in drs]


@router.post("/guest/seed")
async def seed_guest_workspace(req: SeedRequest, authorization: str = Header(...)):
    """Seed sample assessments + IROs into the caller's guest sandbox org.

    Mirrors the browser demo seed so logged-out visitors can instantly explore
    reports / assurance / attestation / sandbox submission on realistic data.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    if not _is_guest(user_id):
        raise HTTPException(status_code=403, detail="Use your own org workspace to assess real data")
    org_id = _resolve_org(sb, user_id, None)

    entries = []
    for status, std, drs in (
        ("assessed", "2", {"BP-1", "BP-2", "GOV-1", "GOV-3", "GOV-5", "SBM-1", "SBM-2", "MDR-P", "MDR-A", "MDR-M"}),
        ("reported", "E1", {"E1-6"}),
        ("not_material", "E5", {"E5-5"}),
    ):
        for dp_id in _seed_datapoint_ids(std, drs):
            entries.append(
                {
                    "org_id": org_id,
                    "user_id": None,
                    "financial_year": req.financial_year,
                    "datapoint_id": dp_id,
                    "status": status,
                    "evidence": "Sample evidence — replace with your source.",
                    "notes": "Seeded in the open sandbox.",
                    "source": "manual",
                }
            )

    iros = [
        {
            "org_id": org_id,
            "financial_year": req.financial_year,
            "iro_type": "impact",
            "standard": "E1",
            "title": "Scope 1 & 2 emissions from operations",
            "description": "Operational energy use drives direct and energy-indirect GHG emissions.",
            "severity": 4,
            "likelihood": 5,
            "impact_materiality": 4.2,
            "financial_materiality": 3.5,
            "material": True,
            "status": "assessed",
            "created_by": None,
        },
        {
            "org_id": org_id,
            "financial_year": req.financial_year,
            "iro_type": "risk",
            "standard": "E1",
            "title": "CBAM exposure on exported product lines",
            "description": "Carbon-border pricing raises landed cost for EU-bound exports.",
            "severity": 3,
            "likelihood": 4,
            "impact_materiality": 3.2,
            "financial_materiality": 4.0,
            "material": True,
            "status": "draft",
            "created_by": None,
        },
        {
            "org_id": org_id,
            "financial_year": req.financial_year,
            "iro_type": "opportunity",
            "standard": "E3",
            "title": "Water reuse at flagship plant",
            "description": "Zero-discharge loop reduces intake risk and operating cost.",
            "severity": 3,
            "likelihood": 3,
            "impact_materiality": 2.4,
            "financial_materiality": 2.1,
            "material": False,
            "status": "draft",
            "created_by": None,
        },
        {
            "org_id": org_id,
            "financial_year": req.financial_year,
            "iro_type": "opportunity",
            "standard": "E5",
            "title": "Post-consumer recycled input for packaging",
            "description": "Recycled-content switch cut virgin resin use; below the materiality threshold for now.",
            "severity": 2,
            "likelihood": 3,
            "impact_materiality": 1.8,
            "financial_materiality": 2.2,
            "material": False,
            "status": "draft",
            "created_by": None,
        },
    ]

    iro_result = sb.table("esrs_materiality").insert(iros).execute()
    saved_iro = iro_result.data or []
    not_material_link = next(
        (r.get("id") for r in saved_iro if r.get("standard") == "E5"),
        None,
    )
    for row in entries:
        if row["status"] == "not_material":
            row["materiality_id"] = not_material_link
    sb.table("esrs_entries").upsert(entries, on_conflict="org_id,financial_year,datapoint_id").execute()

    return {
        "seeded_entries": len(entries),
        "seeded_iro": len(iros),
        "financial_year": req.financial_year,
        "org_id": org_id,
    }


@router.delete("/guest/workspace")
async def reset_guest_workspace(authorization: str = Header(...)):
    """Wipe the caller's guest sandbox org (entries, materiality, reports, submissions)."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    if not _is_guest(user_id):
        raise HTTPException(status_code=403, detail="Own organisations cannot be bulk-reset here")
    org_id = _resolve_org(sb, user_id, None)
    for table in ("esrs_submissions", "esrs_reports", "esrs_materiality", "esrs_entries"):
        sb.table(table).delete().eq("org_id", org_id).execute()
    return {"org_id": org_id, "reset": True}


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
                "dr_count": next((r["dr_count"] for r in cs["standards"] if r["standard"] == std_id), 0),
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
                "user_id": _subject_id(user_id),
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
    result = sb.table("esrs_entries").upsert(rows, on_conflict="org_id,financial_year,datapoint_id").execute()
    saved = result.data or []
    return {"org_id": org_id, "saved": len(saved), "entries": saved}


@router.put("/entries/{entry_id}")
async def update_entry(entry_id: str, req: EntryUpdate, authorization: str = Header(...)):
    """Update selected fields of one entry row."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    existing = sb.table("esrs_entries").select("*").eq("id", entry_id).eq("org_id", org_id).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Entry not found")
    if req.status is not None and req.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {req.status} (allowed: {', '.join(sorted(VALID_STATUSES))})",
        )
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    patch["user_id"] = _subject_id(user_id)
    result = sb.table("esrs_entries").update(patch).eq("id", entry_id).eq("org_id", org_id).execute()
    return {"entry": (result.data or [{}])[0]}


@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, authorization: str = Header(...)):
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    existing = sb.table("esrs_entries").select("id").eq("id", entry_id).eq("org_id", org_id).maybe_single().execute()
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

    in_scope_ids, entries_map, scope, has_material_iro = _scoped_state(sb, org_id, financial_year, value_chain)

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
        res = sb.table("esrs_profiles").select("value_chain_scope").eq("org_id", org_id).maybe_single().execute()
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
    resp = sb.table("esrs_entries").select("*").eq("org_id", org_id).eq("financial_year", financial_year).execute()
    entries_map = {r["datapoint_id"]: r for r in (resp.data or [])}
    scope = _active_scope(sb, org_id, value_chain)
    in_scope_ids = {
        d["id"]
        for d in ESRS_DATAPOINTS
        if _phase_for_year(d.get("phase_in"), financial_year) and bool(_value_chain_segments(d) & scope)
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


def _material_flag(impact: Optional[float], financial: Optional[float], explicit: Optional[bool]) -> bool:
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
        "created_by": _subject_id(user_id),
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
    existing = sb.table("esrs_materiality").select("*").eq("id", iro_id).eq("org_id", org_id).maybe_single().execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="IRO not found")
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    if "material" not in patch and any(k in patch for k in ("impact_materiality", "financial_materiality")):
        impact = patch.get("impact_materiality", existing.data.get("impact_materiality"))
        financial = patch.get("financial_materiality", existing.data.get("financial_materiality"))
        patch["material"] = _material_flag(impact, financial, None)
    result = sb.table("esrs_materiality").update(patch).eq("id", iro_id).eq("org_id", org_id).execute()
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
    existing = sb.table("esrs_materiality").select("id").eq("id", iro_id).eq("org_id", org_id).maybe_single().execute()
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
        res = sb.table("esrs_profiles").select("value_chain_scope").eq("org_id", org_id).maybe_single().execute()
        stored = (res.data or {}).get("value_chain_scope")
    except Exception:  # noqa: BLE001 - profile table may not exist yet
        stored = None
    scope = [s for s in (stored or []) if s in VALUE_CHAIN_SEGMENTS]
    return {
        "org_id": org_id,
        "value_chain_scope": scope or list(VALUE_CHAIN_SEGMENTS),
    }


@router.put("/scope")
async def set_scope(req: ScopeUpdate, org_id: Optional[str] = None, authorization: str = Header(...)):
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
    result = (
        sb.table("esrs_profiles").upsert({"org_id": org_id, "value_chain_scope": scope}, on_conflict="org_id").execute()
    )
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
    org = sb.table("organizations").select("id, name, cin, lei").eq("id", org_id).maybe_single().execute()
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


def _parse_oam_ack(body: str, fallback_ref: str) -> dict:
    """Interpret a regulator (OAM) webhook response.

    JSON receipts carry the acknowledgment reference and timestamp; plain-text
    responses are legacy refs. Returns ``{"submission_ref", "acknowledged_at",
    "ack_payload", "is_receipt"}`` where ``is_receipt`` is only true for a
    well-formed JSON ack.
    """
    try:
        parsed = json.loads(body)
    except (ValueError, TypeError):
        return {
            "submission_ref": body.strip() or fallback_ref,
            "acknowledged_at": None,
            "ack_payload": None,
            "is_receipt": False,
        }
    if not isinstance(parsed, dict):
        return {
            "submission_ref": fallback_ref,
            "acknowledged_at": None,
            "ack_payload": None,
            "is_receipt": False,
        }
    ref = parsed.get("submission_ref") or parsed.get("ack_ref") or fallback_ref
    received = parsed.get("received_at") or parsed.get("acknowledged_at")
    return {
        "submission_ref": ref or fallback_ref,
        "acknowledged_at": received or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ack_payload": parsed,
        "is_receipt": True,
    }


def _sign_manifest_qes(manifest_digest: str, report_id: str, attested_by: str, sandbox: bool = False) -> dict:
    """Digitally sign the manifest digest and render the package's qes.xml.

    Uses the process Ed25519 signer from ``app.prov.signing`` (KMS envelope in
    production, local/ephemeral seed elsewhere). The signature is detached:
    the OAM recomputes the manifest digest from ``manifest.json`` and verifies
    it against the embedded public key. Sandbox (guest) packages are signed
    with a fresh ephemeral key labelled ``guest-sandbox`` so a sandbox package
    can never be mistaken for (or verified against) a real filing key.
    """
    from app.prov import signing

    if sandbox:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        signer = signing.LocalEd25519Signer(Ed25519PrivateKey.generate(), key_id="guest-sandbox")
    else:
        try:
            signer = signing.get_signer()
        except signing.SigningError as exc:
            raise HTTPException(status_code=500, detail=f"Cannot sign submission: {exc}") from exc
    import base64

    signature_b64 = base64.b64encode(signer.sign(manifest_digest.encode("ascii"))).decode("ascii")
    public_key_b64 = signer.public_key_b64()
    signed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<qes xmlns="filebrsr:qes">\n'
        f"  <subject>csrd-report:{report_id}</subject>\n"
        f"  <attested-by>{_xml_escape(attested_by)}</attested-by>\n"
        "  <algorithm>Ed25519</algorithm>\n"
        f"  <key-id>{_xml_escape(signer.key_id)}</key-id>\n"
        f'  <public-key base64="{public_key_b64}"/>\n'
        f"  <signed-at>{signed_at}</signed-at>\n"
        f'  <digest algorithm="SHA-256" of="manifest.json" value="{manifest_digest}"/>\n'
        f'  <signature base64="{signature_b64}"/>\n'
        "</qes>\n"
    )
    return {
        "algorithm": "Ed25519",
        "key_id": signer.key_id,
        "public_key_b64": public_key_b64,
        "signature_b64": signature_b64,
        "manifest_digest": manifest_digest,
        "signed_at": signed_at,
        "xml": xml,
    }


def _xml_escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _entry_payload(row: dict) -> dict:
    """Shrink an ``esrs_entries`` row to the fields the ESEF builder needs."""
    return {
        "datapoint_id": row.get("datapoint_id"),
        "status": row.get("status") or "not_assessed",
        "value": row.get("value"),
        "evidence": row.get("evidence") or "",
        "notes": row.get("notes") or "",
    }


def _build_esef(sb, org_id: str, row: dict) -> bytes:
    """Regenerate the ESEF artifact for a report row (shared by all flows)."""
    in_scope_ids, entries_map, scope, has_material_iro = _scoped_state(sb, org_id, row["financial_year"])
    entity = _resolve_entity(sb, org_id)
    return build_esef_statement(
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


def _scoped_handled(in_scope_ids: set[str], entries_map: dict[str, Any], has_material_iro: bool) -> int:
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
                value = json.dumps(v, indent=1) if isinstance(v, (dict, list)) else str(v)
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
    if _is_guest(user_id):
        existing = (
            sb.table("esrs_reports")
            .select("id")
            .eq("org_id", org_id)
            .eq("financial_year", req.financial_year)
            .execute()
        )
        if len(existing.data or []) >= max(1, get_settings().CSRD_GUEST_MAX_REPORTS):
            raise HTTPException(
                status_code=429,
                detail=f"Guest sandbox limit reached ({get_settings().CSRD_GUEST_MAX_REPORTS} reports). Reset the workspace to start again.",
            )
    in_scope_ids, entries_map, scope, has_material_iro = _scoped_state(sb, org_id, req.financial_year)

    t0 = time.monotonic()
    if fmt == "word":
        content = _build_word_stmt(org_id, req.financial_year, entries_map, in_scope_ids, has_material_iro)
    elif fmt == "pdf":
        content = _build_pdf_stmt(org_id, req.financial_year, entries_map, in_scope_ids, has_material_iro)
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
        "created_by": _subject_id(user_id),
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
    report = sb.table("esrs_reports").select("*").eq("id", report_id).eq("org_id", org_id).maybe_single().execute()
    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")
    row = report.data
    if row.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Report is not ready")
    in_scope_ids, entries_map, _, has_material_iro = _scoped_state(sb, org_id, row["financial_year"])
    content_type = REPORT_CONTENT_TYPES.get(row["report_type"])
    if row["report_type"] == "word":
        in_scope_ids, entries_map, _, has_material_iro = _scoped_state(sb, org_id, row["financial_year"])
        content = _build_word_stmt(org_id, row["financial_year"], entries_map, in_scope_ids, has_material_iro)
    elif row["report_type"] == "pdf":
        in_scope_ids, entries_map, _, has_material_iro = _scoped_state(sb, org_id, row["financial_year"])
        content = _build_pdf_stmt(org_id, row["financial_year"], entries_map, in_scope_ids, has_material_iro)
    else:
        content = _build_esef(sb, org_id, row)
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


@router.post("/reports/{report_id}/validate")
async def validate_report(report_id: str, authorization: str = Header(...)):
    """Run the ESEF pre-flight validation and persist the result on the report.

    Submission for filing requires ``validation_status == 'pass'``. The check
    is deterministic for a given report snapshot (same inputs → same result),
    so re-running never blurs prior approval.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    report = sb.table("esrs_reports").select("*").eq("id", report_id).eq("org_id", org_id).maybe_single().execute()
    row = report.data
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if row.get("report_type") != "esef":
        raise HTTPException(status_code=400, detail="Only ESEF reports can be validated")
    if row.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Report is not ready")

    content = _build_esef(sb, org_id, row)
    settings = get_settings()
    result = validate_esef_statement(
        content,
        financial_year=row["financial_year"],
        coverage_pct=row.get("coverage_pct") or 0.0,
        assurance=_report_assurance(row),
    )
    if settings.ESEF_ARRELLE_ENABLED:
        apply_arelle(
            result,
            content,
            timeout=settings.ESEF_ARRELLE_TIMEOUT_SECONDS,
            cmdline=settings.ESEF_ARRELLE_CMDLINE,
        )
    payload = result.as_dict()
    patch = {
        "validation_status": "pass" if result.passed else "fail",
        "validation_summary": payload,
        "validated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    sb.table("esrs_reports").update(patch).eq("id", report_id).eq("org_id", org_id).execute()
    return {"report_id": report_id, **payload}


class AssuranceRequest(BaseModel):
    status: str = "none"  # none | limited | reasonable
    firm: Optional[str] = None
    date: Optional[str] = None
    statement: Optional[str] = None


ASSURANCE_STATUSES = {"none", "limited", "reasonable"}


@router.post("/reports/{report_id}/assurance")
async def change_assurance(report_id: str, req: AssuranceRequest, authorization: str = Header(...)):
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
        patch = {
            "assurance_status": "none",
            "assurance_firm": None,
            "assurance_date": None,
            "assurance_statement": None,
        }
    else:
        patch = {
            "assurance_status": status,
            "assurance_firm": req.firm,
            "assurance_date": req.date,
            "assurance_statement": req.statement,
        }
    result = sb.table("esrs_reports").update(patch).eq("id", report_id).execute()
    return {"report_id": report_id, "assurance": (result.data or [{}])[0].get("assurance_status")}


class AttestationRequest(BaseModel):
    signed_by: str
    statement: str = ""


@router.post("/reports/{report_id}/attestation")
async def attest_report(report_id: str, req: AttestationRequest, authorization: str = Header(...)):
    """Record the auditor's attestation of an assured ESEF report.

    Attestation is the final governance gate before the package may be
    submitted (see /submit). The named auditor affirms the ESRS statement and
    its assurance opinion; the identity is embedded in the qes.xml signature
    record of any subsequent submission.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    report = sb.table("esrs_reports").select("*").eq("id", report_id).eq("org_id", org_id).maybe_single().execute()
    row = report.data
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if row.get("report_type") != "esef":
        raise HTTPException(status_code=400, detail="Only ESEF reports can be attested")
    if not req.signed_by.strip():
        raise HTTPException(status_code=422, detail="signed_by is required")
    assurance = _report_assurance(row)
    if assurance["status"] not in {"limited", "reasonable"}:
        raise HTTPException(
            status_code=409,
            detail="An assurance opinion (limited or reasonable) is required before attestation",
        )
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    patch = {
        "attested_by": req.signed_by.strip(),
        "attested_at": now_ts,
        "attestation_statement": req.statement.strip(),
    }
    result = sb.table("esrs_reports").update(patch).eq("id", report_id).execute()
    updated = (result.data or [{}])[0]
    return {
        "report_id": report_id,
        "attested_by": updated.get("attested_by"),
        "attested_at": updated.get("attested_at"),
        "attestation_statement": updated.get("attestation_statement"),
    }


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
    report = sb.table("esrs_reports").select("*").eq("id", report_id).eq("org_id", org_id).maybe_single().execute()
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
    if row.get("validation_status") != "pass":
        raise HTTPException(
            status_code=409,
            detail="The ESEF statement has not passed pre-flight validation (run /validate)",
        )
    if not row.get("attested_at"):
        raise HTTPException(
            status_code=409,
            detail="An auditor attestation is required before submission (POST /attestation)",
        )

    content = _build_esef(sb, org_id, row)
    entity = _resolve_entity(sb, org_id)

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
        "attestation": (
            {
                "signed_by": row.get("attested_by"),
                "attested_at": row.get("attested_at"),
                "statement": row.get("attestation_statement") or "",
            }
            if row.get("attested_at")
            else None
        ),
        "prepared_at": row.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": req.notes or "",
    }
    manifest_str = json.dumps(manifest, indent=2, default=str)
    manifest_digest = hashlib.sha256(manifest_str.encode("utf-8")).hexdigest()
    is_guest = _is_guest(user_id)
    qes = _sign_manifest_qes(manifest_digest, report_id, row.get("attested_by") or "", sandbox=is_guest)
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("esrs_statement.html", content)
        zf.writestr("manifest.json", manifest_str)
        zf.writestr("sha256.txt", sha256)
        zf.writestr("qes.xml", qes["xml"].encode("utf-8"))
    package = buf.getvalue()

    status = "queued_local"
    submission_ref = manifest["filing_ref"]
    settings = get_settings()
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    channel = "local_queue"
    sent_at = now_ts
    ack: dict = {}
    payload = json.dumps(manifest, default=str).encode("utf-8")
    if is_guest:
        # Sandbox-only: never contact a real OAM, even when one is configured.
        channel = "guest_sandbox"
        status = "sandboxed"
    elif settings.OAM_FILING_ENDPOINT:
        import urllib.request

        channel = "oam_webhook"
        status = "submitted"
        try:
            with urllib.request.urlopen(
                settings.OAM_FILING_ENDPOINT,
                data=payload,
                timeout=15,
                headers={"Content-Type": "application/json", "User-Agent": "filebrsr-csrd/1.0"},
            ) as resp:
                body = resp.read().decode("utf-8", "replace")
            ack = _parse_oam_ack(body, submission_ref)
            submission_ref = ack["submission_ref"]
        except Exception as exc:  # noqa: BLE001    local-first: never fail the API on webhook trouble
            status = f"webhook_failed:{type(exc).__name__}"

    ack_ref = ack.get("submission_ref") if ack.get("is_receipt") else None
    acknowledged_at = ack.get("acknowledged_at") if ack.get("is_receipt") else None
    ack_payload = ack.get("ack_payload") if ack.get("is_receipt") else None

    manifest_sha = hashlib.sha256(package).hexdigest()
    # Idempotency: one submission per report. Re-submitting only ever retries a
    # webhook that has not reached the OAM yet; a confirmed submission is
    # returned as-is (its ref is the authoritative one).
    existing = (
        sb.table("esrs_submissions")
        .select("*")
        .eq("org_id", org_id)
        .eq("report_id", report_id)
        .maybe_single()
        .execute()
    )
    if existing.data:
        old = dict(existing.data)
        if old.get("status") == "submitted":
            return {
                "submission_id": old.get("id"),
                "status": "submitted",
                "submission_ref": old.get("submission_ref") or old.get("ack_ref"),
                "manifest_sha256": old.get("manifest_sha256") or manifest_sha,
                "package_bytes": len(package),
                "ack_ref": old.get("ack_ref"),
                "acknowledged_at": old.get("acknowledged_at"),
                "channel": old.get("channel"),
                "already_submitted": True,
            }
        patch = {
            "status": status,
            "submission_ref": ack_ref if ack.get("is_receipt") else submission_ref,
            "last_error": status if status.startswith("webhook_failed") else None,
            "retry_count": (old.get("retry_count") or 0) + 1,
            "channel": old.get("channel") or channel,
            "sent_at": old.get("sent_at") or sent_at,
            "ack_ref": old.get("ack_ref") or ack_ref,
            "acknowledged_at": old.get("acknowledged_at") or acknowledged_at,
            "ack_payload": old.get("ack_payload") or ack_payload,
            "qes_algorithm": old.get("qes_algorithm") or qes["algorithm"],
            "qes_key_id": old.get("qes_key_id") or qes["key_id"],
            "qes_signature_b64": old.get("qes_signature_b64") or qes["signature_b64"],
            "qes_public_key_b64": old.get("qes_public_key_b64") or qes["public_key_b64"],
            "qes_manifest_digest": old.get("qes_manifest_digest") or qes["manifest_digest"],
        }
        sb.table("esrs_submissions").update(patch).eq("id", old["id"]).execute()
        old.update(patch)
        return {
            "submission_id": old.get("id"),
            "status": old.get("status"),
            "submission_ref": old.get("submission_ref"),
            "manifest_sha256": old.get("manifest_sha256") or manifest_sha,
            "package_bytes": len(package),
            "ack_ref": old.get("ack_ref"),
            "acknowledged_at": old.get("acknowledged_at"),
            "channel": old.get("channel"),
            "already_submitted": False,
        }

    sub_row = {
        "org_id": org_id,
        "report_id": report_id,
        "financial_year": row["financial_year"],
        "status": status,
        "submission_ref": ack_ref if ack.get("is_receipt") else submission_ref,
        "manifest_sha256": manifest_sha,
        "package_sha256": sha256,
        "last_error": status if status.startswith("webhook_failed") else None,
        "submitted_by": _subject_id(user_id),
        "channel": channel,
        "sent_at": sent_at,
        "ack_ref": ack_ref,
        "acknowledged_at": acknowledged_at,
        "ack_payload": ack_payload,
        "qes_algorithm": qes["algorithm"],
        "qes_key_id": qes["key_id"],
        "qes_signature_b64": qes["signature_b64"],
        "qes_public_key_b64": qes["public_key_b64"],
        "qes_manifest_digest": qes["manifest_digest"],
    }
    result = sb.table("esrs_submissions").insert(sub_row).execute()
    submission = (result.data or [{}])[0]
    return {
        "submission_id": submission.get("id"),
        "status": status,
        "submission_ref": submission_ref,
        "manifest_sha256": manifest_sha,
        "package_bytes": len(package),
        "ack_ref": ack_ref,
        "acknowledged_at": acknowledged_at,
        "channel": channel,
        "already_submitted": False,
    }


@router.post("/reports/{report_id}/sandbox/ack")
async def simulate_receipt(report_id: str, authorization: str = Header(...)):
    """Dev-only: mark a queued submission as acknowledged by the OAM.

    Lets end-to-end flows be exercised without a live regulator: applies a
    fake ESAP acceptance receipt (``channel = 'sandbox'``) to the submission
    for the report. Disabled in production.
    """
    user_id = await get_user_id(authorization)
    # Guest sandbox sessions can always exercise the ack loop (that is their
    # entire point); real users may only do so outside production.
    if get_settings().ENVIRONMENT == "production" and not _is_guest(user_id):
        raise HTTPException(status_code=404, detail="Sandbox is disabled in production")
    sb = get_supabase_admin()
    org_id = _resolve_org(sb, user_id, None)
    submission = (
        sb.table("esrs_submissions")
        .select("*")
        .eq("org_id", org_id)
        .eq("report_id", report_id)
        .maybe_single()
        .execute()
    )
    row = submission.data
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found for this report")
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    ack = {
        "submission_ref": row.get("submission_ref"),
        "received_at": now_ts,
        "channel": "sandbox",
        "acknowledged_by": "sandbox-oam",
    }
    patch = {
        "status": "submitted",
        "channel": "sandbox",
        "ack_ref": ack["submission_ref"],
        "acknowledged_at": now_ts,
        "ack_payload": ack,
        "last_error": None,
    }
    sb.table("esrs_submissions").update(patch).eq("id", row["id"]).execute()
    return {
        "submission_id": row.get("id"),
        "status": "submitted",
        "ack_ref": ack["submission_ref"],
        "acknowledged_at": now_ts,
        "channel": "sandbox",
        "ack_payload": ack,
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
