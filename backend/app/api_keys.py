"""
API Key Authentication for B2B access to FileBRSR API.

Provides:
- API key generation and validation
- Rate limiting per key
- Usage tracking
- Tiered access (free/pro/enterprise)
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings

logger = logging.getLogger("filebrsr.api_keys")


# ═══════════════════════════════════════════════════════════════════════
# API KEY TIERS
# ═══════════════════════════════════════════════════════════════════════

API_TIERS = {
    "free": {
        "requests_per_day": 10,
        "max_file_size_mb": 10,
        "batch_limit": 1,
        "features": ["extract", "validate", "gap_analysis"],
    },
    "pro": {
        "requests_per_day": 100,
        "max_file_size_mb": 50,
        "batch_limit": 5,
        "features": ["extract", "validate", "gap_analysis", "score", "mapping", "template"],
    },
    "enterprise": {
        "requests_per_day": 1000,
        "max_file_size_mb": 100,
        "batch_limit": 20,
        "features": ["extract", "validate", "gap_analysis", "score", "mapping",
                     "template", "batch", "benchmark", "yoy_compare"],
    },
}


def generate_api_key(prefix: str = "fbrsr") -> str:
    """Generate a new API key with prefix."""
    random_part = secrets.token_hex(24)
    return f"{prefix}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage (never store raw keys)."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def validate_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> dict:
    """
    FastAPI dependency to validate API key from X-API-Key header.
    Returns the key metadata if valid.

    For now, uses Supabase to store and look up keys.
    Falls back to allowing requests without key for backward compatibility.
    """
    if not x_api_key:
        # Allow keyless access for backward compatibility (rate limited)
        return {
            "tier": "free",
            "user_id": None,
            "key_id": None,
            "limits": API_TIERS["free"],
        }

    if not x_api_key.startswith("fbrsr_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    # Look up in Supabase
    settings = get_settings()
    from supabase import create_client
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    key_hash = hash_api_key(x_api_key)
    result = supabase.table("api_keys").select("*").eq("key_hash", key_hash).eq("active", True).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    key_record = result.data[0]
    tier = key_record.get("tier", "free")

    # Check rate limit
    today = datetime.now(timezone.utc).date().isoformat()
    usage_result = supabase.table("api_usage").select("request_count").eq(
        "key_id", key_record["id"]
    ).eq("date", today).execute()

    current_usage = usage_result.data[0]["request_count"] if usage_result.data else 0
    limit = API_TIERS[tier]["requests_per_day"]

    if current_usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. {tier} tier allows {limit} requests/day.",
        )

    # Increment usage
    if usage_result.data:
        supabase.table("api_usage").update(
            {"request_count": current_usage + 1}
        ).eq("key_id", key_record["id"]).eq("date", today).execute()
    else:
        supabase.table("api_usage").insert({
            "key_id": key_record["id"],
            "date": today,
            "request_count": 1,
        }).execute()

    return {
        "tier": tier,
        "user_id": key_record.get("user_id"),
        "key_id": key_record["id"],
        "limits": API_TIERS[tier],
        "usage_today": current_usage + 1,
    }


async def check_feature_access(api_key_data: dict, feature: str) -> None:
    """Check if the API key tier has access to a specific feature."""
    allowed = api_key_data["limits"]["features"]
    if feature not in allowed:
        tier = api_key_data["tier"]
        raise HTTPException(
            status_code=403,
            detail=f"Feature '{feature}' not available on {tier} tier. Upgrade for access.",
        )


# ═══════════════════════════════════════════════════════════════════════
# MANAGEMENT API (self-serve key CRUD from the dashboard)
# ═══════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/api/keys", tags=["api-keys"])

# Map a user's billing plan to the API tier its keys get.
_PLAN_TO_TIER = {
    "free": "free",
    "starter": "free",
    "pro": "pro",
    "growth": "pro",
    "professional": "pro",
    "enterprise": "enterprise",
    "scale": "enterprise",
}


async def _require_user_id(authorization: Optional[str]) -> str:
    """Resolve the authenticated Supabase user_id from a Bearer JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[len("Bearer "):].strip()
    if not token or token in ("guest", "undefined", "null"):
        raise HTTPException(status_code=401, detail="Invalid auth token")
    if token == get_settings().SUPABASE_SERVICE_KEY:
        raise HTTPException(status_code=401, detail="Service key not permitted here")
    try:
        import jwt as pyjwt

        payload = pyjwt.decode(token, options={"verify_signature": False})
        uid = payload.get("sub")
        if not uid or uid == "guest":
            raise HTTPException(status_code=401, detail="Invalid JWT payload")
        return uid
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=f"Could not decode JWT: {e}")


def _supabase():
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


class CreateKeyRequest(BaseModel):
    name: str = Field(default="API key", max_length=80)


@router.get("")
async def list_keys(authorization: Optional[str] = Header(default=None)):
    """List the caller's API keys (metadata only — never the raw key)."""
    user_id = await _require_user_id(authorization)
    sb = _supabase()

    rows = (
        sb.table("api_keys")
        .select("id, name, key_prefix, tier, active, last_used_at, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    keys = rows.data or []

    # Attach today's usage + the tier's daily limit for each key.
    today = datetime.now(timezone.utc).date().isoformat()
    for k in keys:
        usage = (
            sb.table("api_usage")
            .select("request_count")
            .eq("key_id", k["id"])
            .eq("date", today)
            .execute()
        )
        k["usage_today"] = usage.data[0]["request_count"] if usage.data else 0
        k["daily_limit"] = API_TIERS.get(k.get("tier", "free"), API_TIERS["free"])["requests_per_day"]
    return {"keys": keys}


@router.post("")
async def create_key(
    req: CreateKeyRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Generate a new API key. The raw key is returned ONCE and never stored."""
    user_id = await _require_user_id(authorization)
    sb = _supabase()

    # Derive tier + org from the caller's profile.
    profile = (
        sb.table("profiles")
        .select("plan, org_id")
        .eq("id", user_id)
        .single()
        .execute()
    )
    plan = (profile.data or {}).get("plan", "free")
    org_id = (profile.data or {}).get("org_id")
    tier = _PLAN_TO_TIER.get(plan, "free")

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    # Show enough of the key to recognise it later, e.g. "fbrsr_1a2b3c4d…".
    key_prefix = raw_key[:14] + "…"

    inserted = (
        sb.table("api_keys")
        .insert({
            "user_id": user_id,
            "org_id": org_id,
            "name": req.name.strip() or "API key",
            "key_prefix": key_prefix,
            "key_hash": key_hash,
            "tier": tier,
            "active": True,
        })
        .execute()
    )
    record = (inserted.data or [{}])[0]
    logger.info("API key created: user=%s tier=%s id=%s", user_id, tier, record.get("id"))

    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "tier": tier,
        "key_prefix": key_prefix,
        # Returned exactly once. The client must copy it now.
        "api_key": raw_key,
        "daily_limit": API_TIERS.get(tier, API_TIERS["free"])["requests_per_day"],
    }


@router.delete("/{key_id}")
async def revoke_key(
    key_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """Revoke (deactivate) one of the caller's API keys."""
    user_id = await _require_user_id(authorization)
    sb = _supabase()

    existing = (
        sb.table("api_keys")
        .select("id")
        .eq("id", key_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="API key not found")

    sb.table("api_keys").update({"active": False}).eq("id", key_id).eq("user_id", user_id).execute()
    logger.info("API key revoked: user=%s id=%s", user_id, key_id)
    return {"status": "revoked", "id": key_id}

