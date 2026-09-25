"""Shared user-identity resolution for Bearer-JWT endpoints.

Every endpoint that authenticates an end user funnels through
:func:`resolve_user_id` so the verification policy lives in exactly one
place, instead of ~13 ad-hoc ``jwt.decode(..., verify_signature=False)``
copy-pastes that let a caller forge any ``sub`` claim (e.g. ``Bearer
<victim-uuid>``) and read another tenant's data.

Resolution order (see :func:`resolve_user_id` for details):

1. Supabase service key -> ``"service_role"`` (trusted internal caller)
2. Supabase anon key     -> the token itself (public demo/anonymous identity)
3. ``SUPABASE_JWT_SECRET`` set -> strict local HS256 verification
   (audience ``authenticated``, requires ``sub`` + ``exp`` claims)
4. else ``SUPABASE_ANON_KEY`` set -> remote verification via GoTrue
   ``/auth/v1/user`` (no secret needed; works with the public anon key)
5. production with neither -> HTTP 500, fail closed
6. development/test         -> legacy unverified decode (dev bridge only)
"""

import logging
import time

import jwt as pyjwt
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger("filebrsr.auth")

# Positive remote-verification cache: a verified token stays trusted for a
# short window so the fallback path doesn't round-trip GoTrue on every call.
_VERIFIED_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL_SECONDS = 300.0

_DENIED_IDENTITIES = {"guest", "undefined", "null"}

# Opaque guest-sandbox session tokens (see POST /platform/csrd/guest/session).
# These are self-identifying reference tokens verified against the
# ``esrs_guest_sessions`` table by the CSRD router's org resolver; they are
# accepted verbatim here so the CSRD endpoints can scope to the session's own
# sandbox org without a real Supabase user.
GUEST_TOKEN_PREFIX = "guest_"


def _deny(token: str) -> bool:
    return token in _DENIED_IDENTITIES


def _decode_strict(token: str, secret: str) -> dict:
    return pyjwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience="authenticated",
        options={"require": ["sub", "exp"]},
    )


def _remote_verify(token: str) -> str:
    settings = get_settings()
    now = time.monotonic()
    hit = _VERIFIED_CACHE.get(token)
    if hit and now - hit[0] < _CACHE_TTL_SECONDS:
        return hit[1]
    try:
        from supabase import create_client

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        res = client.auth.get_user(token)
        user_id = getattr(getattr(res, "user", None), "id", None)
    except Exception as exc:  # noqa: BLE001
        logger.info("auth: remote verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    _VERIFIED_CACHE[token] = (now, user_id)
    return user_id


def resolve_user_id(token: str, *, allow_anon: bool = True) -> str:
    """Verify a bare JWT and return the caller's identity.

    Parameters
    ----------
    token:
        The raw token from the ``Authorization`` header (without ``Bearer``).
    allow_anon:
        When ``False``, the service key and anon key are rejected (used by
        billing / self-serve API-key endpoints that must only see real users).

    Returns the verified Supabase ``sub`` (user id), ``"service_role"`` for
    service-key callers, or the token itself for anon-key demo callers.

    Raises ``HTTPException`` (401/500) when the token cannot be verified.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    if _deny(token):
        raise HTTPException(status_code=401, detail="Invalid auth token")

    # Guest sandbox tokens never go through JWT/anon verification: they are
    # opaque reference tokens. Authenticity is enforced separately by the
    # consuming router, which looks the token up in esrs_guest_sessions (so a
    # forged guest_xxx value resolves to nothing and is rejected there).
    if token.startswith(GUEST_TOKEN_PREFIX):
        return token

    settings = get_settings()
    service_key = settings.SUPABASE_SERVICE_KEY
    anon_key = settings.SUPABASE_ANON_KEY

    if service_key and token == service_key:
        if not allow_anon:
            raise HTTPException(status_code=401, detail="Service key not permitted here")
        return "service_role"

    if anon_key and token == anon_key:
        if not allow_anon:
            raise HTTPException(status_code=401, detail="Anon key not permitted here")
        return anon_key

    jwt_secret = settings.SUPABASE_JWT_SECRET
    if jwt_secret:
        try:
            payload = _decode_strict(token, jwt_secret)
        except pyjwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired") from None
        except pyjwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no sub claim")
        return user_id

    if anon_key:
        return _remote_verify(token)

    if settings.ENVIRONMENT == "production":
        logger.error(
            "auth: production has neither SUPABASE_JWT_SECRET nor SUPABASE_ANON_KEY set "
            "- refusing to authenticate"
        )
        raise HTTPException(
            status_code=500,
            detail="Server auth misconfigured",
        )

    # Development/test bridge: keep the historical local behaviour until a
    # JWT secret or anon key is configured. Never active in production.
    try:
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub") or token
    except Exception:  # noqa: BLE001
        return token


async def get_user_id_from_header(
    authorization: str | None,
    *,
    allow_anon: bool = True,
) -> str:
    """Dependency-style helper: strip ``"Bearer "`` and resolve the user id.

    Matches the signature of the per-router ``get_user_id`` helpers it
    replaces, so existing call sites keep working unchanged.
    """
    token = (authorization or "").replace("Bearer ", "").strip()
    return resolve_user_id(token, allow_anon=allow_anon)
