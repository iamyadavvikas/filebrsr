"""
Ed25519 signing for provenance graphs.

Principle #3 (provenance first-class): every disclosed number traces back to
a signed source record. This module signs the canonical SHA-256 digest of a
PROV-O graph with an **Ed25519** key and verifies those signatures.

Key sourcing (in priority order):

1. **KMS envelope (prod)** — when ``PROV_SIGNING_KMS_KEY_ID`` and
   ``PROV_SIGNING_KEY_CIPHERTEXT_B64`` are set, the KMS-encrypted 32-byte
   Ed25519 seed is decrypted once at boot via ``kms.Decrypt`` (ap-south-1) and
   loaded into an in-process :class:`LocalEd25519Signer`. KMS cannot natively
   sign Ed25519, so we use it only to guard the seed at rest; the plaintext
   seed exists only in memory. ``key_id`` is the KMS key id.
2. **Local key (dev/CI)** — a base64-encoded 32-byte Ed25519 seed in
   ``PROV_SIGNING_KEY_B64``. Use only for local development.
3. **Ephemeral (fallback)** — if neither is configured, an in-memory key is
   generated and a loud warning logged. Signatures are NOT reproducible
   across restarts; **refused when ENVIRONMENT=production**.

The DSC (eMudhra/Sify) browser-side dual signature is a separate, later layer
(Phase 5) — this module provides the server-side Ed25519 half.
"""

from __future__ import annotations

import base64
import logging
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger("filebrsr.prov")

ALGORITHM = "Ed25519"


class SigningError(RuntimeError):
    """Raised when signing or verification cannot be performed."""


class Signer:
    """Abstract signer interface (local key or Cloud KMS)."""

    key_id: str

    def sign(self, message: bytes) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    def public_key_b64(self) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class LocalEd25519Signer(Signer):
    """Signs with an in-process Ed25519 private key."""

    def __init__(self, private_key: Ed25519PrivateKey, key_id: str) -> None:
        self._private_key = private_key
        self.key_id = key_id

    @classmethod
    def from_seed_b64(cls, seed_b64: str, key_id: str) -> "LocalEd25519Signer":
        try:
            seed = base64.b64decode(seed_b64)
        except Exception as exc:  # noqa: BLE001
            raise SigningError(f"PROV_SIGNING_KEY_B64 is not valid base64: {exc}") from exc
        if len(seed) != 32:
            raise SigningError(
                f"Ed25519 seed must be 32 bytes, got {len(seed)} bytes"
            )
        return cls(Ed25519PrivateKey.from_private_bytes(seed), key_id)

    @classmethod
    def from_seed_bytes(cls, seed: bytes, key_id: str) -> "LocalEd25519Signer":
        if len(seed) != 32:
            raise SigningError(
                f"Ed25519 seed must be 32 bytes, got {len(seed)} bytes"
            )
        return cls(Ed25519PrivateKey.from_private_bytes(seed), key_id)

    @classmethod
    def ephemeral(cls) -> "LocalEd25519Signer":
        logger.warning(
            "PROV: no signing key configured — generating EPHEMERAL Ed25519 key. "
            "Signatures will NOT be reproducible across restarts. Dev/CI only."
        )
        return cls(Ed25519PrivateKey.generate(), key_id="ephemeral-dev")

    def sign(self, message: bytes) -> bytes:
        return self._private_key.sign(message)

    def public_key_b64(self) -> str:
        from cryptography.hazmat.primitives import serialization

        raw = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("ascii")


def _decrypt_kms_seed(ciphertext_b64: str, kms_key_id: str, region: str) -> bytes:
    """Decrypt a KMS-encrypted Ed25519 seed (envelope at rest, sign in memory)."""
    try:
        ciphertext = base64.b64decode(ciphertext_b64)
    except Exception as exc:  # noqa: BLE001
        raise SigningError(
            f"PROV_SIGNING_KEY_CIPHERTEXT_B64 is not valid base64: {exc}"
        ) from exc
    try:
        import boto3

        kms = boto3.client("kms", region_name=region)
        resp = kms.decrypt(CiphertextBlob=ciphertext, KeyId=kms_key_id)
        return resp["Plaintext"]
    except Exception as exc:  # noqa: BLE001
        raise SigningError(f"KMS decrypt of provenance seed failed: {exc}") from exc


_signer_lock = threading.Lock()
_signer: Signer | None = None


def get_signer() -> Signer:
    """Return the process-wide signer, constructed from settings on first use."""
    global _signer
    if _signer is not None:
        return _signer
    with _signer_lock:
        if _signer is not None:
            return _signer
        _signer = _build_signer()
        return _signer


def reset_signer() -> None:
    """Drop the cached signer (used by tests that swap key configuration)."""
    global _signer
    with _signer_lock:
        _signer = None


def _build_signer() -> Signer:
    # Imported lazily so this package has no import-time settings dependency.
    from app.config import get_settings

    settings = get_settings()
    is_production = (getattr(settings, "ENVIRONMENT", "") or "").lower() == "production"
    kms_key_id = getattr(settings, "PROV_SIGNING_KMS_KEY_ID", "") or ""
    ciphertext_b64 = getattr(settings, "PROV_SIGNING_KEY_CIPHERTEXT_B64", "") or ""
    region = getattr(settings, "DATA_REGION", "ap-south-1") or "ap-south-1"

    # 1. KMS envelope — decrypt the seed once, sign in memory.
    if kms_key_id and ciphertext_b64:
        seed = _decrypt_kms_seed(ciphertext_b64, kms_key_id, region)
        logger.info("PROV: signing key loaded via KMS envelope (key_id=%s)", kms_key_id)
        return LocalEd25519Signer.from_seed_bytes(seed, key_id=kms_key_id)

    # 2. Local plaintext seed (dev/CI).
    seed_b64 = getattr(settings, "PROV_SIGNING_KEY_B64", "") or ""
    key_id = getattr(settings, "PROV_SIGNING_KEY_ID", "") or "local-dev"
    if seed_b64:
        if is_production:
            logger.warning(
                "PROV: using PLAINTEXT PROV_SIGNING_KEY_B64 in production — "
                "prefer KMS envelope (PROV_SIGNING_KMS_KEY_ID + ciphertext)."
            )
        return LocalEd25519Signer.from_seed_b64(seed_b64, key_id)

    # 3. Ephemeral — never in production.
    if is_production:
        raise SigningError(
            "No provenance signing key configured in production. Set "
            "PROV_SIGNING_KMS_KEY_ID + PROV_SIGNING_KEY_CIPHERTEXT_B64 (KMS "
            "envelope) or PROV_SIGNING_KEY_B64 (plaintext seed)."
        )
    return LocalEd25519Signer.ephemeral()


def verify(message: bytes, signature: bytes, public_key_b64: str) -> bool:
    """Return True if ``signature`` is a valid Ed25519 signature of ``message``."""
    try:
        raw = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(raw)
        public_key.verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False
