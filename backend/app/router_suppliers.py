"""Supplier cascade API: magic-link vendors, questionnaires, prefill.

A client invites vendors by name/email; each vendor answers a short
questionnaire over a magic link (no account). Responses stay
org-scoped; prefill into workspace entries happens only on explicit
client confirm through the normal entries bulk path.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.supplier_questions import (
    QUESTIONNAIRES,
    QUESTIONS,
    prefill_from_answers,
)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

TOKEN_PREFIX = "supplier_"
DEFAULT_TTL_DAYS = 180


def get_supabase_admin():
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def _supplier_row(sb, token: str) -> dict[str, Any] | None:
    if not token.startswith(TOKEN_PREFIX):
        return None
    res = sb.table("cascade_suppliers").select("*").eq(
        "token_hash", _hash_token(token)).execute()
    rows = list(res.data or []) if res is not None else []
    if not rows:
        return None
    s = rows[0]
    exp = s.get("expires_at")
    if exp:
        try:
            if datetime.fromisoformat(str(exp).replace("Z", "+00:00")) <= _now():
                return None
        except (ValueError, TypeError):
            return None
    return s


def _supplier_org(sb, authorization: str) -> tuple[dict[str, Any], str]:
    token = (authorization or "").replace("Bearer ", "").strip()
    row = _supplier_row(sb, token)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired supplier credential")
    return row, row["org_id"]


class InviteIn(BaseModel):
    name: str
    email: Optional[str] = None
    tier: str = "tier_1"
    spend_band: Optional[str] = None
    ttl_days: int = Field(DEFAULT_TTL_DAYS, ge=1, le=730)


class AnswersIn(BaseModel):
    financial_year: str
    questionnaire: str = "brsr_a5"
    answers: dict[str, Any] = {}


@router.get("/questionnaires")
async def questionnaires():
    """Public catalog of question sets (the form needs no login to render)."""
    return {
        name: {"title": meta["title"], "description": meta["description"],
               "count": len(QUESTIONS[name]),
               "questions": QUESTIONS[name]}
        for name, meta in QUESTIONNAIRES.items()
    }


@router.post("/invite", status_code=200)
async def invite_supplier(body: InviteIn, authorization: str = Header(...)):
    from app.router_brsr_core import _resolve_org

    token = (authorization or "").replace("Bearer ", "").strip()
    if token.startswith(TOKEN_PREFIX) or token.startswith("auditor_"):
        raise HTTPException(status_code=403, detail="Suppliers cannot invite suppliers")
    sb, org_id = _resolve_org(authorization)
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "supplier name required")
    if body.tier not in ("tier_1", "tier_2", "tier_3"):
        raise HTTPException(400, "invalid tier")
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    row = {
        "org_id": org_id,
        "name": name,
        "email": (body.email or "").strip().lower() or None,
        "token_hash": _hash_token(raw),
        "tier": body.tier,
        "spend_band": body.spend_band,
        "expires_at": (_now() + timedelta(days=body.ttl_days)).isoformat(),
    }
    sb.table("cascade_suppliers").upsert(row, on_conflict="org_id,name").execute()
    return {"org_id": org_id, "name": name,
            "invite_url": f"https://filebrsr.com/supplier?token={raw}",
            "token": raw, "expires_at": row["expires_at"]}


@router.get("")
async def list_suppliers(authorization: str = Header(...)):
    from app.router_brsr_core import _resolve_org

    token = (authorization or "").replace("Bearer ", "").strip()
    if token.startswith(TOKEN_PREFIX) or token.startswith("auditor_"):
        raise HTTPException(status_code=403, detail="Not permitted")
    sb, org_id = _resolve_org(authorization)
    res = sb.table("cascade_suppliers").select(
        "id,name,email,tier,spend_band,expires_at,created_at").eq("org_id", org_id).execute()
    rows = list(res.data or []) if res is not None else []
    return {"org_id": org_id, "count": len(rows), "suppliers": rows}


@router.delete("/{supplier_id}", status_code=200)
async def delete_supplier(supplier_id: str, authorization: str = Header(...)):
    from app.router_brsr_core import _resolve_org

    sb, org_id = _resolve_org(authorization)
    sb.table("cascade_suppliers").delete().eq("id", supplier_id).eq("org_id", org_id).execute()
    return {"deleted": supplier_id}


@router.get("/form")
async def supplier_form(token: str, financial_year: str, questionnaire: str = "brsr_a5"):
    """Vendor view: questions + their saved answers (magic-link auth)."""
    if questionnaire not in QUESTIONS:
        raise HTTPException(400, "unknown questionnaire")
    sb = get_supabase_admin()
    supplier, org_id = _supplier_org(sb, f"Bearer {token}")
    existing = sb.table("cascade_responses").select("answers,status").eq(
        "supplier_id", supplier["id"]).eq("financial_year", financial_year).eq(
        "questionnaire", questionnaire).execute()
    row = ((existing.data or [None])[0]) if existing is not None else None
    return {
        "supplier": {"id": supplier["id"], "name": supplier["name"], "tier": supplier["tier"]},
        "financial_year": financial_year,
        "questionnaire": questionnaire,
        "title": QUESTIONNAIRES[questionnaire]["title"],
        "questions": QUESTIONS[questionnaire],
        "answers": (row or {}).get("answers") or {},
        "status": (row or {}).get("status", "draft"),
    }


@router.put("/responses", status_code=200)
async def save_responses(body: AnswersIn, authorization: str = Header(...)):
    """Vendor autosave (draft)."""
    if body.questionnaire not in QUESTIONS:
        raise HTTPException(400, "unknown questionnaire")
    sb = get_supabase_admin()
    supplier, org_id = _supplier_org(sb, authorization)
    valid = {q["code"] for q in QUESTIONS[body.questionnaire]}
    clean = {k: v for k, v in (body.answers or {}).items() if k in valid}
    sb.table("cascade_responses").upsert({
        "supplier_id": supplier["id"], "org_id": org_id,
        "financial_year": body.financial_year, "questionnaire": body.questionnaire,
        "answers": clean, "status": "draft",
    }, on_conflict="supplier_id,financial_year,questionnaire").execute()
    return {"saved": len(clean), "status": "draft"}


@router.post("/responses/submit", status_code=200)
async def submit_responses(body: AnswersIn, authorization: str = Header(...)):
    """Vendor locks answers as submitted."""
    if body.questionnaire not in QUESTIONS:
        raise HTTPException(400, "unknown questionnaire")
    sb = get_supabase_admin()
    supplier, org_id = _supplier_org(sb, authorization)
    valid = {q["code"] for q in QUESTIONS[body.questionnaire]}
    clean = {k: v for k, v in (body.answers or {}).items() if k in valid}
    sb.table("cascade_responses").upsert({
        "supplier_id": supplier["id"], "org_id": org_id,
        "financial_year": body.financial_year, "questionnaire": body.questionnaire,
        "answers": clean, "status": "submitted",
        "submitted_at": _now().isoformat(),
    }, on_conflict="supplier_id,financial_year,questionnaire").execute()
    return {"saved": len(clean), "status": "submitted"}


@router.get("/responses")
async def list_responses(financial_year: Optional[str] = None, authorization: str = Header(...)):
    """Client view of all vendor responses."""
    from app.router_brsr_core import _resolve_org

    token = (authorization or "").replace("Bearer ", "").strip()
    if token.startswith(TOKEN_PREFIX) or token.startswith("auditor_"):
        raise HTTPException(status_code=403, detail="Not permitted")
    sb, org_id = _resolve_org(authorization)
    query = sb.table("cascade_responses").select("*").eq("org_id", org_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)
    res = query.order("created_at", desc=True).execute()
    rows = list(res.data or []) if res is not None else []
    names = sb.table("cascade_suppliers").select("id,name,tier").eq("org_id", org_id).execute()
    by_id = {r["id"]: r for r in ((names.data or []) if names is not None else [])}
    for r in rows:
        r["supplier"] = by_id.get(r["supplier_id"], {})
    return {"org_id": org_id, "count": len(rows), "responses": rows}


@router.post("/responses/{response_id}/prefill", status_code=200)
async def prefill_from_response(response_id: str, authorization: str = Header(...)):
    """Compute ESRS prefill entries from a submitted response (review-first)."""
    from app.router_brsr_core import _resolve_org

    token = (authorization or "").replace("Bearer ", "").strip()
    if token.startswith(TOKEN_PREFIX) or token.startswith("auditor_"):
        raise HTTPException(status_code=403, detail="Not permitted")
    sb, org_id = _resolve_org(authorization)
    res = sb.table("cascade_responses").select("*").eq("id", response_id).eq(
        "org_id", org_id).execute()
    rows = list(res.data or []) if res is not None else []
    if not rows:
        raise HTTPException(status_code=404, detail="Response not found")
    out = prefill_from_answers(rows[0]["questionnaire"], rows[0].get("answers") or {})
    return {**out, "count": len(out["entries"]), "response_id": response_id}
