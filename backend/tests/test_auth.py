"""Unit tests for app.auth.resolve_user_id.

Verification policy:
- service key  -> "service_role"
- anon key     -> the token itself (when allow_anon=True)
- JWT secret set -> strict HS256 verification of user session tokens
- no secret/anon, development -> legacy unverified bridge
- production with neither       -> HTTP 500 (fail closed)
"""
import asyncio

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from app.auth import get_user_id_from_header, resolve_user_id

FAKE_SECRET = "s3cret-jwt-secret"
FAKE_ANON = "anon-token-value"


def _user_token(uid: str = "user-123") -> str:
    return pyjwt.encode(
        {
            "sub": uid,
            "aud": "authenticated",
            "role": "authenticated",
            "exp": 4_000_000_000,
        },
        FAKE_SECRET,
        algorithm="HS256",
    )


class _SettingsStub:
    def __init__(self, **kwargs):
        self.SUPABASE_SERVICE_KEY = ""
        self.SUPABASE_ANON_KEY = ""
        self.SUPABASE_JWT_SECRET = ""
        self.ENVIRONMENT = "development"
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.fixture
def settings(monkeypatch):
    stub = _SettingsStub()
    monkeypatch.setattr("app.auth.get_settings", lambda: stub)
    return stub


class TestServiceAndAnonKeys:
    def test_service_key_returns_service_role(self, settings):
        settings.SUPABASE_SERVICE_KEY = "svc-key"
        assert resolve_user_id("svc-key") == "service_role"

    def test_service_key_rejected_when_disallowed(self, settings):
        settings.SUPABASE_SERVICE_KEY = "svc-key"
        with pytest.raises(HTTPException) as exc:
            resolve_user_id("svc-key", allow_anon=False)
        assert exc.value.status_code == 401

    def test_anon_key_returns_token_when_allowed(self, settings):
        settings.SUPABASE_ANON_KEY = FAKE_ANON
        assert resolve_user_id(FAKE_ANON) == FAKE_ANON

    def test_anon_key_rejected_when_disallowed(self, settings):
        settings.SUPABASE_ANON_KEY = FAKE_ANON
        with pytest.raises(HTTPException) as exc:
            resolve_user_id(FAKE_ANON, allow_anon=False)
        assert exc.value.status_code == 401


class TestStrictVerification:
    def test_valid_user_session_token(self, settings):
        settings.SUPABASE_JWT_SECRET = FAKE_SECRET
        assert resolve_user_id(_user_token("user-123")) == "user-123"

    def test_forged_sub_rejected(self, settings):
        settings.SUPABASE_JWT_SECRET = FAKE_SECRET
        token = pyjwt.encode(
            {
                "sub": "victim-uuid",
                "aud": "authenticated",
                "role": "authenticated",
                "exp": 4_000_000_000,
            },
            "attacker-secret",
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            resolve_user_id(token)
        assert exc.value.status_code == 401

    def test_garbage_token_rejected(self, settings):
        settings.SUPABASE_JWT_SECRET = FAKE_SECRET
        with pytest.raises(HTTPException) as exc:
            resolve_user_id("not-a-jwt")
        assert exc.value.status_code == 401

    def test_expired_token_rejected(self, settings):
        settings.SUPABASE_JWT_SECRET = FAKE_SECRET
        token = pyjwt.encode(
            {
                "sub": "u1",
                "aud": "authenticated",
                "role": "authenticated",
                "exp": 1,
            },
            FAKE_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            resolve_user_id(token)
        assert exc.value.status_code == 401

    def test_missing_audience_rejected(self, settings):
        settings.SUPABASE_JWT_SECRET = FAKE_SECRET
        token = pyjwt.encode(
            {"sub": "u1", "role": "authenticated", "exp": 4_000_000_000},
            FAKE_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            resolve_user_id(token)
        assert exc.value.status_code == 401


class TestDevBridge:
    def test_development_unverified_decode(self, settings):
        assert resolve_user_id("plain-token") == "plain-token"

    def test_development_sub_used_when_present(self, settings):
        token = pyjwt.encode({"sub": "u9"}, "irrelevant", algorithm="HS256")
        assert resolve_user_id(token) == "u9"

    def test_production_fails_closed_without_any_key(self, settings):
        settings.ENVIRONMENT = "production"
        with pytest.raises(HTTPException) as exc:
            resolve_user_id("anything")
        assert exc.value.status_code == 500


class TestDeniedIdentities:
    @pytest.mark.parametrize("token", ["guest", "undefined", "null", ""])
    def test_denied_identities_rejected(self, settings, token):
        with pytest.raises(HTTPException) as exc:
            resolve_user_id(token)
        assert exc.value.status_code == 401


class TestHeaderHelper:
    def test_strips_bearer(self, settings):
        settings.SUPABASE_JWT_SECRET = FAKE_SECRET
        result = asyncio.run(get_user_id_from_header(f"Bearer {_user_token('u1')}"))
        assert result == "u1"

    def test_missing_header(self, settings):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_user_id_from_header(None))
        assert exc.value.status_code == 401