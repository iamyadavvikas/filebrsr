"""
Phase B — KMS envelope signing key.

Acceptance:
- ``_build_signer`` decrypts a KMS-wrapped seed (boto3 mocked) and produces a
  ``LocalEd25519Signer`` keyed by the KMS key id.
- A record signed under the envelope key re-verifies AFTER a simulated process
  restart (signer cache reset + KMS decrypt → same 32-byte seed → same public
  key), proving signatures are reproducible across restarts.
- Production refuses to start with no key configured (ephemeral is dev-only).
"""

from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.calculator import scope2_location_based, sign_result
from app.factors_india import reset_cache
from app.prov import signing as signing_mod
from app.prov import verify_signed_provenance
from app.prov.signing import SigningError, reset_signer

# A fixed plaintext seed the mocked KMS will "decrypt" to.
_PLAINTEXT_SEED = bytes(range(32))
_CIPHERTEXT_B64 = base64.b64encode(b"opaque-kms-ciphertext").decode("ascii")
_KMS_KEY_ID = "arn:aws:kms:ap-south-1:000000000000:key/abc"


def _settings(**overrides) -> SimpleNamespace:
    base = dict(
        ENVIRONMENT="production",
        PROV_SIGNING_KMS_KEY_ID="",
        PROV_SIGNING_KEY_CIPHERTEXT_B64="",
        PROV_SIGNING_KEY_B64="",
        PROV_SIGNING_KEY_ID="local-dev",
        DATA_REGION="ap-south-1",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def _mock_kms(monkeypatch):
    """Patch boto3.client('kms').decrypt to return the fixed plaintext seed."""
    kms = MagicMock()
    kms.decrypt.return_value = {"Plaintext": _PLAINTEXT_SEED}
    fake_boto3 = MagicMock()
    fake_boto3.client.return_value = kms
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)
    return kms


@pytest.fixture(autouse=True)
def _reset():
    reset_signer()
    reset_cache()
    yield
    reset_signer()
    reset_cache()


def test_build_signer_uses_kms_envelope(monkeypatch, _mock_kms):
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: _settings(
            PROV_SIGNING_KMS_KEY_ID=_KMS_KEY_ID,
            PROV_SIGNING_KEY_CIPHERTEXT_B64=_CIPHERTEXT_B64,
        ),
    )
    signer = signing_mod._build_signer()
    assert signer.key_id == _KMS_KEY_ID
    _mock_kms.decrypt.assert_called_once()


def test_envelope_signature_survives_restart(monkeypatch, _mock_kms):
    """Sign under the KMS-derived key, then 'restart' and re-verify."""
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: _settings(
            PROV_SIGNING_KMS_KEY_ID=_KMS_KEY_ID,
            PROV_SIGNING_KEY_CIPHERTEXT_B64=_CIPHERTEXT_B64,
        ),
    )

    result = scope2_location_based(150_000, jurisdiction="AU", state="NSW")
    _, signed = sign_result(result, org_id="org-1", jurisdiction="AU")
    pubkey_before = signed.public_key_b64
    assert verify_signed_provenance(signed) is True

    # Simulate a process restart: drop the cached signer, KMS decrypt again.
    reset_signer()
    signer_after = signing_mod.get_signer()
    assert signer_after.public_key_b64() == pubkey_before
    # The previously-signed record still verifies against the reloaded key.
    assert verify_signed_provenance(signed) is True


def test_production_refuses_without_key(monkeypatch):
    monkeypatch.setattr(
        "app.config.get_settings", lambda: _settings(ENVIRONMENT="production")
    )
    with pytest.raises(SigningError, match="No provenance signing key"):
        signing_mod._build_signer()


def test_plaintext_seed_path_still_works(monkeypatch):
    seed_b64 = base64.b64encode(_PLAINTEXT_SEED).decode("ascii")
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: _settings(ENVIRONMENT="development", PROV_SIGNING_KEY_B64=seed_b64),
    )
    signer = signing_mod._build_signer()
    # Same seed as the KMS path → identical public key.
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: _settings(
            PROV_SIGNING_KMS_KEY_ID=_KMS_KEY_ID,
            PROV_SIGNING_KEY_CIPHERTEXT_B64=_CIPHERTEXT_B64,
        ),
    )
    fake_boto3 = MagicMock()
    fake_boto3.client.return_value.decrypt.return_value = {"Plaintext": _PLAINTEXT_SEED}
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)
    kms_signer = signing_mod._build_signer()
    assert signer.public_key_b64() == kms_signer.public_key_b64()
