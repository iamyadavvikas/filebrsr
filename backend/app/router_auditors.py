"""Auditor portal API: magic-link grants, scoped reads, findings loop.

Auditors are assurance providers working *inside* the platform without full
accounts. A per-(org, email) grant holds only a token *hash*; the raw
``auditor_`` token is shown once at mint and travels as the Bearer
credential until expiry/revocation. All reads are org-scoped to the grant;
auditors can raise findings, answer threads, and close them — they can
never write client data.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings

router = APIRouter(prefix="/api/auditors", tags=["auditors"])

TOKEN_PREFIX = "auditor_"
DEFAULT_TTL_DAYS = 90


def get_supabase_admin():
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def _grant_row(sb, token: str) -> dict[str, Any] | None:
    """Live grant for a raw bearer token, else None (fail closed)."""
    if not token.startswith(TOKEN_PREFIX):
        return None
    res = sb.table("auditor_grants").select("*").eq(
        "token_hash", _hash_token(token)).execute()
    rows = list(res.data or []) if res is not None else []
    if not rows:
        return None
    g = rows[0]
    if g.get("revoked"):
        return None
    try:
        exp = datetime.fromisoformat(str(g["expires_at"]).replace("Z", "+00:00"))
    except (ValueError, TypeError, KeyError):
        return None
    if exp <= _now():
        return None
    return g


def _auditor_org(sb, authorization: str) -> tuple[dict[str, Any], str]:
    token = (authorization or "").replace("Bearer ", "").strip()
    grant = _grant_row(sb, token)
    if grant is None:
        raise HTTPException(status_code=401, detail="Invalid or expired auditor credential")
    return grant, grant["org_id"]


class InviteIn(BaseModel):
    email: str
    scope: str = "read"
    ttl_days: int = Field(DEFAULT_TTL_DAYS, ge=1, le=365)
    financial_year: Optional[str] = None


class AcceptIn(BaseModel):
    token: str


class FindingIn(BaseModel):
    financial_year: Optional[str] = None
    entity_type: str = "general"
    entity_ref: Optional[str] = None
    severity: str = "medium"
    message: str


class FindingReply(BaseModel):
    message: Optional[str] = None
    status: Optional[str] = None


VALID_FINDING_STATUSES = ("open", "answered", "closed")


VALID_FINDING_STATUSES = ("open", "answered", "closed")


@router.post("/invite", status_code=200)
async def invite_auditor(body: InviteIn, authorization: str = Header(...)):
    """Owner/admin mints a magic-link grant (raw token shown once)."""
    from app.router_brsr_core import _resolve_org

    token = (authorization or "").replace("Bearer ", "").strip()
    if token.startswith(TOKEN_PREFIX):
        raise HTTPException(status_code=403, detail="Auditors cannot invite auditors")
    sb, org_id = _resolve_org(authorization)
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "valid email required")
    if body.scope not in ("read", "read_assure"):
        raise HTTPException(400, "scope must be read or read_assure")
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires_at = (_now() + timedelta(days=body.ttl_days)).isoformat()
    row = {
        "org_id": org_id,
        "email": email,
        "token_hash": _hash_token(raw),
        "scope": body.scope,
        "expires_at": expires_at,
        "revoked": False,
    }
    sb.table("auditor_grants").upsert(row, on_conflict="org_id,email").execute()
    org = sb.table("organizations").select("name").eq("id", org_id).execute()
    org_name = ((org.data or [{}])[0] if org is not None else {}).get("name") or "your organisation"
    try:
        from app import email_service

        await email_service.send_email(email, "auditor_invite", {
            "org_name": org_name,
            "inviter_name": "your FileBRSR admin",
            "financial_year": body.financial_year or "current",
            "ttl_days": body.ttl_days,
            "invite_url": f"https://filebrsr.com/platform/assurance/auditor?token={raw}",
        })
    except Exception:  # noqa: BLE001 - invite link below is authoritative
        pass
    return {"org_id": org_id, "email": email, "expires_at": expires_at,
            "invite_url": f"https://filebrsr.com/platform/assurance/auditor?token={raw}",
            "token": raw}


@router.post("/accept", status_code=200)
async def accept_invite(body: AcceptIn):
    """First-use handshake: validates the magic link, stamps accepted_at."""
    sb = get_supabase_admin()
    grant = _grant_row(sb, (body.token or "").strip())
    if grant is None:
        raise HTTPException(status_code=401, detail="Invalid or expired auditor credential")
    if not grant.get("accepted_at"):
        sb.table("auditor_grants").update(
            {"accepted_at": _now().isoformat()}).eq("id", grant["id"]).execute()
    return {"org_id": grant["org_id"], "email": grant["email"],
            "scope": grant.get("scope", "read"), "expires_at": grant["expires_at"]}


@router.get("/grants")
async def list_grants(authorization: str = Header(...)):
    """Owner/admin view of their org's auditor grants (hashes never leave)."""
    from app.router_brsr_core import _resolve_org

    token = (authorization or "").replace("Bearer ", "").strip()
    if token.startswith(TOKEN_PREFIX):
        raise HTTPException(status_code=403, detail="Auditors cannot list grants")
    sb, org_id = _resolve_org(authorization)
    res = sb.table("auditor_grants").select(
        "id,email,scope,expires_at,accepted_at,revoked,created_at").eq("org_id", org_id).execute()
    rows = list(res.data or []) if res is not None else []
    return {"org_id": org_id, "count": len(rows), "grants": rows}


@router.delete("/grants/{grant_id}", status_code=200)
async def revoke_grant(grant_id: str, authorization: str = Header(...)):
    from app.router_brsr_core import _resolve_org

    token = (authorization or "").replace("Bearer ", "").strip()
    if token.startswith(TOKEN_PREFIX):
        raise HTTPException(status_code=403, detail="Auditors cannot revoke grants")
    sb, org_id = _resolve_org(authorization)
    sb.table("auditor_grants").update({"revoked": True}).eq("id", grant_id).eq("org_id", org_id).execute()
    return {"revoked": grant_id}


@router.get("/workspace")
async def auditor_workspace(financial_year: Optional[str] = None, authorization: str = Header(...)):
    """Read-only bundle for the auditor: coverage, workpapers, trail, findings."""
    from app.brsr_core_assurance import coverage as core_coverage
    from app.brsr_workpapers import progress as wp_progress

    sb = get_supabase_admin()
    grant, org_id = _auditor_org(sb, authorization)
    fy = financial_year or ""
    try:
        cov = core_coverage(sb, org_id, fy) if fy else {"coverage": "financial_year required"}
    except Exception as exc:  # noqa: BLE001 - coverage errors degrade, never fail the bundle
        cov = {"error": str(exc)}
    try:
        wp = wp_progress(sb, org_id, fy) if fy else {}
    except Exception as exc:  # noqa: BLE001
        wp = {"error": str(exc)}
    trail = sb.table("audit_trail").select(
        "id,action,entity_type,entity_id,datapoint_id,financial_year,created_at").eq(
        "org_id", org_id).order("created_at", desc=True).limit(50).execute()
    findings = sb.table("assurance_findings").select("*").eq("org_id", org_id)
    if fy:
        findings = findings.eq("financial_year", fy)
    frows = findings.order("created_at", desc=True).execute()
    docs = sb.table("documents").select("id,file_name,category,financial_year,created_at").eq("org_id", org_id)
    if fy:
        docs = docs.eq("financial_year", fy)
    drows = docs.order("created_at", desc=True).limit(50).execute()
    return {
        "org_id": org_id,
        "scope": grant.get("scope", "read"),
        "grant_expires_at": grant.get("expires_at"),
        "coverage": cov,
        "workpapers": wp,
        "audit_trail": list(trail.data or []) if trail is not None else [],
        "findings": list(frows.data or []) if frows is not None else [],
        "documents": list(drows.data or []) if drows is not None else [],
    }


@router.post("/findings", status_code=200)
async def raise_finding(body: FindingIn, authorization: str = Header(...)):
    """Auditor raises a query (org members answer via PUT)."""
    sb = get_supabase_admin()
    grant, org_id = _auditor_org(sb, authorization)
    if body.entity_type not in ("general", "kpi", "datapoint", "report", "workpaper"):
        raise HTTPException(400, "invalid entity_type")
    if body.severity not in ("low", "medium", "high", "blocking"):
        raise HTTPException(400, "invalid severity")
    if not (body.message or "").strip():
        raise HTTPException(400, "message required")
    row = {
        "org_id": org_id,
        "financial_year": body.financial_year,
        "raised_by_grant": grant["id"],
        "raised_by_email": grant.get("email"),
        "entity_type": body.entity_type,
        "entity_ref": body.entity_ref,
        "severity": body.severity,
        "message": body.message.strip(),
        "status": "open",
        "thread": [{"by": grant.get("email"), "at": _now().isoformat(), "message": body.message.strip()}],
    }
    res = sb.table("assurance_findings").insert(row).execute()
    saved = list(res.data or [row]) if res is not None else [row]
    return {"finding": saved[0]}


@router.put("/findings/{finding_id}", status_code=200)
async def reply_finding(finding_id: str, body: FindingReply, authorization: str = Header(...)):
    """Append to the thread; auditor closes, org answers."""
    sb = get_supabase_admin()
    token = (authorization or "").replace("Bearer ", "").strip()
    is_auditor = token.startswith(TOKEN_PREFIX)
    if is_auditor:
        grant, org_id = _auditor_org(sb, authorization)
        who = grant.get("email") or "auditor"
    else:
        from app.router_brsr_core import _resolve_org

        sb, org_id = _resolve_org(authorization)
        who = "org"
    cur = sb.table("assurance_findings").select("*").eq("id", finding_id).eq("org_id", org_id).execute()
    rows = list(cur.data or []) if cur is not None else []
    if not rows:
        raise HTTPException(status_code=404, detail="Finding not found")
    row = rows[0]
    if body.status is not None:
        if body.status not in VALID_FINDING_STATUSES:
            raise HTTPException(400, "invalid status")
        current = row.get("status", "open")
        if is_auditor:
            # Auditors close findings; discussion continues via replies.
            if body.status != "closed":
                raise HTTPException(400, "auditors may only close findings")
        else:
            # The org answers open findings; closed findings stay closed.
            if body.status != "answered" or current == "closed":
                raise HTTPException(400, "org may only answer open findings")
    thread = list(row.get("thread") or [])
    if body.message and body.message.strip():
        thread.append({"by": who, "at": _now().isoformat(), "message": body.message.strip()})
    patch: dict[str, Any] = {"thread": thread, "updated_at": _now().isoformat()}
    if body.status is not None:
        patch["status"] = body.status
    res = sb.table("assurance_findings").update(patch).eq("id", finding_id).execute()
    saved = list(res.data or [dict(row, **patch)]) if res is not None else [dict(row, **patch)]
    return {"finding": saved[0]}
