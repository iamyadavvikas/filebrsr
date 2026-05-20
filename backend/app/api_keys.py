"""
API Key Authentication for B2B access to FileBRSR API.

Provides:
- API key generation and validation
- Rate limiting per key
- Usage tracking
- Tiered access (free/pro/enterprise)
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, Header

from app.config import get_settings


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
