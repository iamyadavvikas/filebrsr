"""
Ed25519 signing for provenance graphs.

Principle #3 (provenance first-class): every disclosed number traces back to
a signed source record. This module signs the canonical SHA-256 digest of a
PROV-O graph with an **Ed25519** key and verifies those signatures.

Key sourcing (in priority order):

1. **Cloud KMS (prod)** — when ``PROV_SIGNING_KMS_KEY_ID`` is set, signing is
   delegated to AWS KMS in ``ap-south-1`` (see :class:`KmsSigner`). The
   private key never leaves the HSM. *Phase-1 ships the interface + a clear
   ``NotImplementedError``; the boto3 wiring lands with the residency
   migration.*
2. **Local key (dev/CI)** — a base64-encoded 32-byte Ed25519 seed in
   ``PROV_SIGNING_KEY_B64``. Use only for local development.
3. **Ephemeral (fallback)** — if neither is configured, an in-memory key is
   generated and a loud warning logged. Signatures are NOT reproducible
   across restarts; never use in prod.

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


class KmsSigner(Signer):
    """Delegates signing to AWS KMS (ap-south-1). Wiring lands with residency."""

    def __init__(self, kms_key_id: str) -> None:
        self.key_id = kms_key_id

    def sign(self, message: bytes) -> bytes:  # pragma: no cover - Phase 5
        raise NotImplementedError(
            "KMS signing not wired yet. Configure PROV_SIGNING_KEY_B64 for local "
            "dev, or complete the boto3 KMS integration (residency migration)."
        )

    def public_key_b64(self) -> str:  # pragma: no cover - Phase 5
        raise NotImplementedError


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
    kms_key_id = getattr(settings, "PROV_SIGNING_KMS_KEY_ID", "") or ""
    if kms_key_id:
        return KmsSigner(kms_key_id)
    seed_b64 = getattr(settings, "PROV_SIGNING_KEY_B64", "") or ""
    key_id = getattr(settings, "PROV_SIGNING_KEY_ID", "") or "local-dev"
    if seed_b64:
        return LocalEd25519Signer.from_seed_b64(seed_b64, key_id)
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
