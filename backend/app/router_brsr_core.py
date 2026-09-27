"""BRSR Core — assurance tracking API (canonical registry + per-KPI states).

Endpoints:
* ``GET    /api/brsr-core/registry``             — the 9 attributes + 43 BRSC KPIs
* ``GET    /api/brsr-core/assurance``            — coverage for a financial year (vs phase-in tier)
* ``PUT    /api/brsr-core/assurance``            — upsert one KPI's assurance state
* ``DELETE /api/brsr-core/assurance/{kpi_code}`` — drop a KPI's assurance row

Registry data is served from the canonical :mod:`app.brsr_core` module (no I/O);
assurance rows are org-scoped and persisted via :mod:`app.brsr_core_assurance`
(migration v32).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.brsr_core import ASSURANCE_PHASEIN, ATTRIBUTES, BRSC, get_attributes
from app.brsr_core_assurance import (
    AssuranceValidationError,
    coverage,
    delete_assurance,
    get_assurance,
    list_assurance,
    upsert_assurance,
)
from app.config import get_settings

router = APIRouter(prefix="/api/brsr-core", tags=["brsr-core"])

TIERS = tuple(ASSURANCE_PHASEIN["reasonable"])


class AssuranceUpsert(BaseModel):
    kpi_code: str
    state: str | None = Field(None, description="next state; defaults to current state")
    target_mode: str | None = None
    provider_name: str | None = None
    provider_details: dict[str, Any] = Field(default_factory=dict)
    statement_short: str | None = None
    evidence_id: str | None = None
    evidence_note: str | None = None
    ppp_adjusted: bool | None = None
    output_denominator: str | None = None
    value_chain: bool | None = None
    assessed_value: float | None = None
    unit: str | None = None
    assessed_on: str | None = None


class CoverageRequest(BaseModel):
    financial_year: str
    tier: str | None = None


def get_supabase_admin():
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _resolve_user_id(token: str) -> str:
    """Resolve the Supabase user id from a JWT (main-branch auth convention)."""
    import jwt as pyjwt

    settings = get_settings()
    jwt_secret = settings.SUPABASE_JWT_SECRET
    if jwt_secret:
        try:
            payload = pyjwt.decode(
                token, jwt_secret, algorithms=["HS256"], audience="authenticated"
            )
            return payload.get("sub", "")
        except pyjwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    payload = pyjwt.decode(token, options={"verify_signature": False})
    return payload.get("sub", token)


def _resolve_org(authorization: str) -> tuple[object, str]:
    """Return (supabase_admin, org_id) for the caller, self-healing a personal
    org when the profile has none (mirrors /api/assurance behavior)."""
    token = (authorization or "").replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    user_id = _resolve_user_id(token)

    sb = get_supabase_admin()
    profile = (
        sb.table("profiles")
        .select("org_id, email, company_name")
        .eq("id", user_id)
        .single()
        .execute()
    )
    data = profile.data or {}
    org_id = data.get("org_id")
    if org_id:
        return sb, org_id
    existing = (
        sb.table("organizations")
        .select("id")
        .eq("created_by", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        org_id = existing.data[0]["id"]
    else:
        name = (
            (data.get("company_name") or "").strip()
            or (data.get("email") or "").split("@")[0].strip()
            or "My Organization"
        )
        slug = re.sub(r"-+", "-", re.sub(r"[^a-zA-Z0-9]", "-", name.lower())).strip("-")
        slug = f"{slug or 'org'}-{user_id[:6]}"
        org_row = (
            sb.table("organizations")
            .insert({"name": name, "slug": slug, "plan": "free", "created_by": user_id})
            .execute()
        )
        org_id = org_row.data[0]["id"]
        sb.table("org_members").insert(
            {
                "org_id": org_id,
                "user_id": user_id,
                "role": "owner",
                "joined_at": datetime.utcnow().isoformat(),
                "status": "active",
            }
        ).execute()
    sb.table("profiles").update({"org_id": org_id}).eq("id", user_id).execute()
    return sb, org_id


@router.get("/registry")
def registry() -> dict[str, Any]:
    """The canonical nine attributes and 43 BRSC KPIs (read-only, no DB)."""
    return {
        "attributes": get_attributes(),
        "kpis": BRSC,
        "attributes_count": len(ATTRIBUTES),
        "kpis_count": len(BRSC),
    }


@router.post("/assurance/coverage")
async def assurance_coverage(
    body: CoverageRequest, authorization: str = Header(...)
) -> dict:
    """Coverage for a financial year; pass tier for a phase-in compliance verdict."""
    sb, org_id = _resolve_org(authorization)
    if body.tier and body.tier not in TIERS:
        raise HTTPException(400, f"tier must be one of {', '.join(TIERS)}")
    try:
        return coverage(sb, org_id, body.financial_year, tier=body.tier)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/assurance")
async def assurance_list(
    financial_year: str, tier: str | None = None, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    if tier and tier not in TIERS:
        raise HTTPException(400, f"tier must be one of {', '.join(TIERS)}")
    try:
        rows = list_assurance(sb, org_id, financial_year)
        report = coverage(sb, org_id, financial_year, tier=tier)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"financial_year": financial_year, "tier": tier, "rows": rows, **report}


@router.put("/assurance", status_code=200)
async def assurance_upsert(
    financial_year: str, body: AssuranceUpsert, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        saved = upsert_assurance(
            sb,
            org_id,
            financial_year,
            body.kpi_code,
            state=body.state,
            target_mode=body.target_mode,
            provider_name=body.provider_name,
            provider_details=body.provider_details,
            statement_short=body.statement_short,
            evidence_id=body.evidence_id,
            evidence_note=body.evidence_note,
            ppp_adjusted=body.ppp_adjusted,
            output_denominator=body.output_denominator,
            value_chain=body.value_chain,
            assessed_value=body.assessed_value,
            unit=body.unit,
            assessed_on=body.assessed_on,
        )
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"kpi_code": body.kpi_code, "financial_year": financial_year, **saved}


@router.delete("/assurance/{kpi_code}", status_code=200)
async def assurance_delete(
    kpi_code: str, financial_year: str, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        deleted = delete_assurance(sb, org_id, financial_year, kpi_code)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"kpi_code": kpi_code, "financial_year": financial_year, "deleted": deleted}


@router.get("/assurance/{kpi_code}")
async def assurance_get(
    kpi_code: str, financial_year: str, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        row = get_assurance(sb, org_id, financial_year, kpi_code)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    if row is None:
        raise HTTPException(404, f"no assurance row for {kpi_code} / {financial_year}")
    return row


# ── assurance provider registry + ISAE 3000 workpapers (migration v35) ──


class ProviderIn(BaseModel):
    firm_name: str
    partner_name: str | None = None
    registration_no: str | None = None
    peer_review_valid_until: str | None = None
    independence_declared_on: str | None = None
    rotation_started_on: str | None = None
    contact_email: str | None = None
    status: str | None = None
    notes: str | None = None


class WorkpaperInstantiate(BaseModel):
    financial_year: str
    kpi_codes: list[str]
    level: str = "limited"


class WorkpaperUpdate(BaseModel):
    status: str | None = None
    evidence_ref: str | None = None
    detail: str | None = None
    prepared_by: str | None = None
    reviewed_by: str | None = None


@router.get("/providers")
async def providers_list(authorization: str = Header(...)) -> dict:
    from app.brsr_workpapers import list_providers, rotation_due

    sb, org_id = _resolve_org(authorization)
    rows = list_providers(sb, org_id)
    return {
        "org_id": org_id,
        "count": len(rows),
        "providers": [{**p, "rotation": rotation_due(p)} for p in rows],
    }


@router.put("/providers", status_code=200)
async def provider_upsert(body: ProviderIn, authorization: str = Header(...)) -> dict:
    from app.brsr_workpapers import list_providers, rotation_due, upsert_provider

    sb, org_id = _resolve_org(authorization)
    if body.status is not None and body.status not in ("active", "rotated", "suspended"):
        raise HTTPException(400, f"invalid status {body.status!r}")
    saved = upsert_provider(sb, org_id, body.model_dump(exclude_none=True))
    current = next((p for p in list_providers(sb, org_id) if p.get("id") == saved.get("id")), saved)
    return {"provider": {**current, "rotation": rotation_due(current)}}


@router.delete("/providers/{provider_id}", status_code=200)
async def provider_delete(provider_id: str, authorization: str = Header(...)) -> dict:
    sb, org_id = _resolve_org(authorization)
    sb.table("assurance_providers").delete().eq("id", provider_id).eq("org_id", org_id).execute()
    return {"deleted": provider_id}


@router.post("/workpapers/instantiate", status_code=200)
async def workpapers_instantiate(body: WorkpaperInstantiate, authorization: str = Header(...)) -> dict:
    from app.brsr_core import core_kpi_codes
    from app.brsr_workpapers import LEVELS, instantiate

    sb, org_id = _resolve_org(authorization)
    if body.level not in LEVELS:
        raise HTTPException(400, f"level must be one of {LEVELS}")
    known = set(core_kpi_codes())
    unknown = [c for c in body.kpi_codes if c not in known]
    if unknown:
        raise HTTPException(400, f"unknown KPI codes: {', '.join(unknown)}")
    from app.brsr_core import BRSC

    by_code = {k["code"]: k for k in BRSC}
    out = instantiate(sb, org_id, body.financial_year, body.kpi_codes, body.level, by_code.get)
    return {"financial_year": body.financial_year, "level": body.level, **out}


@router.get("/workpapers")
async def workpapers_list(
    financial_year: str, kpi_code: str | None = None, authorization: str = Header(...)
) -> dict:
    from app.brsr_workpapers import list_workpapers

    sb, org_id = _resolve_org(authorization)
    rows = list_workpapers(sb, org_id, financial_year, kpi_code)
    return {"financial_year": financial_year, "count": len(rows), "workpapers": rows}


@router.put("/workpapers/{kpi_code}/{checkpoint}", status_code=200)
async def workpaper_update(
    kpi_code: str, checkpoint: str, financial_year: str, body: WorkpaperUpdate,
    authorization: str = Header(...),
) -> dict:
    from app.brsr_workpapers import update_workpaper

    sb, org_id = _resolve_org(authorization)
    try:
        row = update_workpaper(sb, org_id, financial_year, kpi_code, checkpoint, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if row is None:
        raise HTTPException(404, f"no workpaper for {kpi_code} / {checkpoint} / {financial_year}")
    return {"workpaper": row}


@router.get("/workpapers/progress")
async def workpapers_progress(financial_year: str, authorization: str = Header(...)) -> dict:
    from app.brsr_workpapers import progress

    sb, org_id = _resolve_org(authorization)
    return {"org_id": org_id, **progress(sb, org_id, financial_year)}
