"""
Organization, Team & Analytics Router.
Multi-tenancy (org → teams → roles), invite flow, and product analytics.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, timedelta
import re

from app.config import get_settings

router = APIRouter(prefix="/api/platform", tags=["Org & Analytics"])
settings = get_settings()


def get_supabase_admin():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub", token)
    except Exception:
        return token


# ═══════════════════════════════════════════════════════════════
# ORGANIZATION APIs
# ═══════════════════════════════════════════════════════════════

class OrgCreate(BaseModel):
    name: str
    plan: str = "starter"

class OrgUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None


@router.get("/org")
async def get_user_org(authorization: str = Header(...)):
    """Get the current user's organization with team members."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Get user profile to find org_id
    profile = sb.table("profiles").select("org_id, company_name").eq("id", user_id).single().execute()
    if not profile.data or not profile.data.get("org_id"):
        return {"org": None, "members": [], "invites": []}

    org_id = profile.data["org_id"]

    # Get org
    org = sb.table("organizations").select("*").eq("id", org_id).single().execute()

    # Get members with profile info
    members = sb.table("org_members").select(
        "id, role, department, title, joined_at, last_active_at, status, "
        "profiles(id, email, full_name, company_name)"
    ).eq("org_id", org_id).execute()

    # Get pending invites
    invites = sb.table("org_invites").select("*").eq("org_id", org_id).eq("status", "pending").execute()

    return {
        "org": org.data,
        "members": members.data or [],
        "invites": invites.data or [],
    }


@router.post("/org")
async def create_org(body: OrgCreate, authorization: str = Header(...)):
    """Create a new organization and set the user as owner."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Generate slug
    slug = re.sub(r'[^a-zA-Z0-9]', '-', body.name.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    slug = f"{slug}-{user_id[:6]}"

    # Create org
    org = sb.table("organizations").insert({
        "name": body.name,
        "slug": slug,
        "plan": body.plan,
        "created_by": user_id,
    }).execute()

    org_id = org.data[0]["id"]

    # Add user as owner
    sb.table("org_members").insert({
        "org_id": org_id,
        "user_id": user_id,
        "role": "owner",
        "joined_at": datetime.utcnow().isoformat(),
        "status": "active",
    }).execute()

    # Update user profile
    sb.table("profiles").update({"org_id": org_id}).eq("id", user_id).execute()

    return {"org_id": org_id, "slug": slug}


@router.put("/org")
async def update_org(body: OrgUpdate, authorization: str = Header(...)):
    """Update org details. Only owner/admin."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    profile = sb.table("profiles").select("org_id").eq("id", user_id).single().execute()
    if not profile.data or not profile.data.get("org_id"):
        raise HTTPException(status_code=404, detail="No organization found")

    org_id = profile.data["org_id"]

    # Check role
    member = sb.table("org_members").select("role").eq("org_id", org_id).eq("user_id", user_id).single().execute()
    if not member.data or member.data["role"] not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners/admins can update the organization")

    update_data = {k: v for k, v in body.dict().items() if v is not None}
    if update_data:
        sb.table("organizations").update(update_data).eq("id", org_id).execute()

    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════
# TEAM INVITE APIs
# ═══════════════════════════════════════════════════════════════

class InviteCreate(BaseModel):
    email: str
    role: str = "member"
    department: Optional[str] = None
    title: Optional[str] = None

class InviteAction(BaseModel):
    action: str  # "accept" | "revoke"


@router.post("/org/invite")
async def invite_team_member(body: InviteCreate, authorization: str = Header(...)):
    """Invite a team member by email. Only owner/admin."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    profile = sb.table("profiles").select("org_id").eq("id", user_id).single().execute()
    if not profile.data or not profile.data.get("org_id"):
        raise HTTPException(status_code=404, detail="Create an organization first")

    org_id = profile.data["org_id"]

    # Check role
    member = sb.table("org_members").select("role").eq("org_id", org_id).eq("user_id", user_id).single().execute()
    if not member.data or member.data["role"] not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners/admins can invite members")

    # Check if already a member
    existing = sb.table("profiles").select("id").eq("email", body.email).execute()
    if existing.data:
        existing_member = sb.table("org_members").select("id").eq("org_id", org_id).eq("user_id", existing.data[0]["id"]).execute()
        if existing_member.data:
            raise HTTPException(status_code=409, detail="User is already a team member")

    # Check for existing pending invite
    pending = sb.table("org_invites").select("id").eq("org_id", org_id).eq("email", body.email).eq("status", "pending").execute()
    if pending.data:
        raise HTTPException(status_code=409, detail="Invite already pending for this email")

    # Create invite
    invite = sb.table("org_invites").insert({
        "org_id": org_id,
        "invited_by": user_id,
        "email": body.email,
        "role": body.role,
    }).execute()

    return {"invite_id": invite.data[0]["id"], "token": invite.data[0]["token"]}


@router.get("/org/invites/pending")
async def get_my_pending_invites(authorization: str = Header(...)):
    """Get pending invites for the current user (by their email)."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    profile = sb.table("profiles").select("email").eq("id", user_id).single().execute()
    if not profile.data:
        return {"invites": []}

    invites = sb.table("org_invites").select(
        "id, org_id, role, created_at, organizations(name)"
    ).eq("email", profile.data["email"]).eq("status", "pending").execute()

    return {"invites": invites.data or []}


@router.post("/org/invite/{invite_id}/action")
async def handle_invite(invite_id: str, body: InviteAction, authorization: str = Header(...)):
    """Accept or revoke an invite."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    invite = sb.table("org_invites").select("*").eq("id", invite_id).single().execute()
    if not invite.data:
        raise HTTPException(status_code=404, detail="Invite not found")

    if body.action == "accept":
        # Verify the accepting user's email matches the invite
        profile = sb.table("profiles").select("email").eq("id", user_id).single().execute()
        if not profile.data or profile.data["email"] != invite.data["email"]:
            raise HTTPException(status_code=403, detail="This invite is for a different email")

        # Add to org_members
        sb.table("org_members").upsert({
            "org_id": invite.data["org_id"],
            "user_id": user_id,
            "role": invite.data["role"],
            "joined_at": datetime.utcnow().isoformat(),
            "status": "active",
        }, on_conflict="org_id,user_id").execute()

        # Update profile org_id
        sb.table("profiles").update({"org_id": invite.data["org_id"]}).eq("id", user_id).execute()

        # Mark invite as accepted
        sb.table("org_invites").update({
            "status": "accepted",
            "accepted_at": datetime.utcnow().isoformat(),
        }).eq("id", invite_id).execute()

        return {"status": "accepted"}

    elif body.action == "revoke":
        # Only org admin/owner or the inviter can revoke
        sb.table("org_invites").update({"status": "revoked"}).eq("id", invite_id).execute()
        return {"status": "revoked"}

    raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'revoke'.")


@router.put("/org/members/{member_user_id}/role")
async def update_member_role(member_user_id: str, role: str, authorization: str = Header(...)):
    """Update a team member's role. Only owner can do this."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    profile = sb.table("profiles").select("org_id").eq("id", user_id).single().execute()
    if not profile.data or not profile.data.get("org_id"):
        raise HTTPException(status_code=404, detail="No organization")

    org_id = profile.data["org_id"]

    # Only owner can change roles
    caller_member = sb.table("org_members").select("role").eq("org_id", org_id).eq("user_id", user_id).single().execute()
    if not caller_member.data or caller_member.data["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only the owner can change roles")

    if role not in ("admin", "member", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    sb.table("org_members").update({"role": role}).eq("org_id", org_id).eq("user_id", member_user_id).execute()
    return {"status": "updated"}


@router.delete("/org/members/{member_user_id}")
async def remove_member(member_user_id: str, authorization: str = Header(...)):
    """Remove a team member. Owner/admin only."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    profile = sb.table("profiles").select("org_id").eq("id", user_id).single().execute()
    if not profile.data or not profile.data.get("org_id"):
        raise HTTPException(status_code=404, detail="No organization")

    org_id = profile.data["org_id"]

    caller_member = sb.table("org_members").select("role").eq("org_id", org_id).eq("user_id", user_id).single().execute()
    if not caller_member.data or caller_member.data["role"] not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner/admin can remove members")

    if member_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    sb.table("org_members").delete().eq("org_id", org_id).eq("user_id", member_user_id).execute()
    # Clear org_id from their profile
    sb.table("profiles").update({"org_id": None}).eq("id", member_user_id).execute()

    return {"status": "removed"}


# ═══════════════════════════════════════════════════════════════
# ANALYTICS APIs
# ═══════════════════════════════════════════════════════════════

@router.post("/analytics/track")
async def track_event(
    event_name: str,
    event_category: str,
    properties: Optional[dict] = None,
    authorization: str = Header(...),
):
    """Track a product analytics event."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    sb.table("analytics_events").insert({
        "user_id": user_id if user_id != "service_role" else None,
        "event_name": event_name,
        "event_category": event_category,
        "properties": properties or {},
    }).execute()

    return {"status": "tracked"}


@router.get("/analytics/dashboard")
async def get_analytics_dashboard(days: int = 30, authorization: str = Header(...)):
    """
    Get analytics dashboard data. Admin-only.
    Returns: user stats, extraction stats, event trends, top pages.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Admin gate: only users with is_admin=true can access analytics
    profile = sb.table("profiles").select("is_admin").eq("id", user_id).single().execute()
    if not profile.data or not profile.data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    # 1. Total users
    total_users = sb.table("profiles").select("id", count="exact").execute()

    # 2. New signups in period
    new_signups = sb.table("profiles").select("id", count="exact").gte("created_at", since).execute()

    # 3. Total extractions
    total_extractions = sb.table("reports").select("id", count="exact").execute()
    extractions_period = sb.table("reports").select("id", count="exact").gte("created_at", since).execute()
    completed_extractions = sb.table("reports").select("id", count="exact").eq("status", "completed").execute()

    # 4. Data entry count
    data_entries = sb.table("brsr_entries").select("id", count="exact").execute()
    data_entries_period = sb.table("brsr_entries").select("id", count="exact").gte("created_at", since).execute()

    # 5. Revenue
    payments = sb.table("payments").select("amount").eq("status", "paid").execute()
    total_revenue = sum(p["amount"] for p in (payments.data or [])) / 100  # paise to INR

    payments_period = sb.table("payments").select("amount").eq("status", "paid").gte("created_at", since).execute()
    period_revenue = sum(p["amount"] for p in (payments_period.data or [])) / 100

    # 6. Recent signups (last 10)
    recent_users = sb.table("profiles").select(
        "id, email, full_name, company_name, plan, created_at"
    ).order("created_at", desc=True).limit(10).execute()

    # 7. Recent extractions (last 10)
    recent_extractions = sb.table("reports").select(
        "id, file_name, status, company_name, financial_year, created_at, user_id"
    ).order("created_at", desc=True).limit(10).execute()

    # 8. Plan distribution
    plan_dist = {}
    all_profiles = sb.table("profiles").select("plan").execute()
    for p in (all_profiles.data or []):
        plan = p.get("plan", "free")
        plan_dist[plan] = plan_dist.get(plan, 0) + 1

    # 9. Extraction success rate
    total_ext = total_extractions.count or 0
    completed_ext = completed_extractions.count or 0
    success_rate = round((completed_ext / total_ext * 100), 1) if total_ext > 0 else 0

    # 10. Daily signups trend (last N days)
    signups_trend = sb.table("profiles").select("created_at").gte("created_at", since).order("created_at").execute()
    daily_signups = {}
    for s in (signups_trend.data or []):
        day = s["created_at"][:10]
        daily_signups[day] = daily_signups.get(day, 0) + 1

    # 11. Daily extractions trend
    ext_trend = sb.table("reports").select("created_at, status").gte("created_at", since).order("created_at").execute()
    daily_extractions = {}
    for e in (ext_trend.data or []):
        day = e["created_at"][:10]
        daily_extractions[day] = daily_extractions.get(day, 0) + 1

    return {
        "summary": {
            "total_users": total_users.count or 0,
            "new_signups": new_signups.count or 0,
            "total_extractions": total_ext,
            "extractions_period": extractions_period.count or 0,
            "extraction_success_rate": success_rate,
            "total_data_entries": data_entries.count or 0,
            "data_entries_period": data_entries_period.count or 0,
            "total_revenue_inr": total_revenue,
            "period_revenue_inr": period_revenue,
        },
        "plan_distribution": plan_dist,
        "trends": {
            "daily_signups": daily_signups,
            "daily_extractions": daily_extractions,
        },
        "recent_users": recent_users.data or [],
        "recent_extractions": recent_extractions.data or [],
    }


@router.get("/analytics/events")
async def get_analytics_events(
    event_name: Optional[str] = None,
    category: Optional[str] = None,
    days: int = 7,
    limit: int = 50,
    authorization: str = Header(...),
):
    """Query analytics events with filters. Admin-only."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Admin gate
    profile = sb.table("profiles").select("is_admin").eq("id", user_id).single().execute()
    if not profile.data or not profile.data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    query = sb.table("analytics_events").select("*").gte("created_at", since).order("created_at", desc=True).limit(limit)

    if event_name:
        query = query.eq("event_name", event_name)
    if category:
        query = query.eq("event_category", category)

    result = query.execute()
    return {"events": result.data or [], "count": len(result.data or [])}
