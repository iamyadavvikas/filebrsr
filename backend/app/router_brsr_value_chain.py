"""BRSR Core — value-chain partners API (CIR/2025/42).

Endpoints:
* ``GET    /api/value-chain/registry``   — value-chain KPI catalog (the 43-BRSC subset)
* ``GET    /api/value-chain``             — partners + coverage for a financial year
* ``PUT    /api/value-chain`               — upsert one partner (>=2% scope, disclosed flag)
* ``DELETE /api/value-chain/{partner_id}`  — drop a partner
* ``GET    /api/value-chain/entries`       — attributed entries (per partner)
* ``PUT    /api/value-chain/entries`       — upsert one partner's KPI state
* ``DELETE /api/value-chain/entries/{entry_id}` — drop an entry

Value-chain disclosure is voluntary (FY2025-26) and never blocks the entity's
own BRSR Core filing gate; status here is advisory coverage reporting.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.brsr_core_assurance import AssuranceValidationError
from app.brsr_value_chain import (
    delete_entry,
    delete_partner,
    list_entries,
    upsert_entry,
    upsert_partner,
    value_chain_kpis,
    value_chain_report,
)
from app.config import get_settings

router = APIRouter(prefix="/api/value-chain", tags=["value-chain"])


class PartnerUpsert(BaseModel):
    partner_name: str
    direction: str
    purchases_pct: float | None = Field(None, ge=0, le=100)
    sales_pct: float | None = Field(None, ge=0, le=100)
    disclosed: bool = False
    notes: str | None = None


class EntryUpsert(BaseModel):
    partner_id: str
    kpi_code: str
    state: str
    provider_name: str | None = None
    provider_details: dict[str, Any] = Field(default_factory=dict)
    evidence_id: str | None = None
    evidence_note: str | None = None
    assessed_value: float | None = None
    unit: str | None = None
    assessed_on: str | None = None


def get_supabase_admin():
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _resolve_user_id(token: str) -> str:
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
    """The value-chain KPI catalog (read-only, no DB)."""
    kpis = value_chain_kpis()
    return {"kpis": kpis, "kpis_count": len(kpis)}


@router.get("")
async def value_chain(
    financial_year: str, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        return value_chain_report(sb, org_id, financial_year)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("", status_code=200)
async def partner_upsert(
    financial_year: str, body: PartnerUpsert, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        saved = upsert_partner(
            sb,
            org_id,
            financial_year,
            body.partner_name,
            body.direction,
            purchases_pct=body.purchases_pct,
            sales_pct=body.sales_pct,
            disclosed=body.disclosed,
            notes=body.notes,
        )
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"financial_year": financial_year, **saved}


@router.delete("/{partner_id}", status_code=200)
async def partner_delete(
    partner_id: str, financial_year: str, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        deleted = delete_partner(sb, org_id, financial_year, partner_id)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not deleted:
        raise HTTPException(404, "partner not found for this org/financial_year")
    return {"partner_id": partner_id, "deleted": True}


@router.get("/entries")
async def entries_list(
    financial_year: str,
    partner_id: str | None = None,
    authorization: str = Header(...),
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        rows = list_entries(sb, org_id, financial_year, partner_id=partner_id)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"financial_year": financial_year, "rows": rows, "count": len(rows)}


@router.put("/entries", status_code=200)
async def entry_upsert(
    financial_year: str, body: EntryUpsert, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        saved = upsert_entry(
            sb,
            org_id,
            financial_year,
            body.partner_id,
            body.kpi_code,
            body.state,
            provider_name=body.provider_name,
            provider_details=body.provider_details,
            evidence_id=body.evidence_id,
            evidence_note=body.evidence_note,
            assessed_value=body.assessed_value,
            unit=body.unit,
            assessed_on=body.assessed_on,
        )
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"financial_year": financial_year, **saved}


@router.delete("/entries/{entry_id}", status_code=200)
async def entry_delete(
    entry_id: str, financial_year: str, authorization: str = Header(...)
) -> dict:
    sb, org_id = _resolve_org(authorization)
    try:
        deleted = delete_entry(sb, org_id, financial_year, entry_id)
    except AssuranceValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not deleted:
        raise HTTPException(404, "entry not found for this org/financial_year")
    return {"entry_id": entry_id, "deleted": True}
