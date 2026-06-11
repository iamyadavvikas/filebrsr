"""
Signed batch export for raw_records (Tally Slice 5).

Why HMAC and not asymmetric (RSA/Ed25519)? Today both the producer (this
backend) and the consumer (the Next.js dashboard + a future BRSR
disclosure XBRL bundler) live inside the same trust boundary — we share
a secret rather than manage public keys. The signature exists to detect
**tampering** of an exported batch JSON file that may sit in object
storage for years between export and audit retrieval. When a third party
(an auditor pulling our published BRSR PDF) needs to verify the export
independently, we can layer Ed25519 on top by signing the HMAC payload
with our long-term key.

Canonicalisation: ``json.dumps(rows, sort_keys=True, separators=(",", ":"))``.
Sorted keys make the byte-for-byte representation deterministic across
Python versions and across JSON libraries the consumer might be using.
The compact separators strip insignificant whitespace.

Output schema::

    {
      "rows":         [...],                  # original list, untouched
      "sha256":       "<hex>",                # of the canonical JSON bytes
      "hmac_sha256":  "<hex>",                # HMAC over the canonical JSON
      "signed_at":    "2025-01-15T10:30:00Z", # UTC ISO-8601
      "key_id":       "<caller-provided id>",
      "algorithm":    "HMAC-SHA256",
      "version":      "tally-export-v1"
    }
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any

_EXPORT_VERSION = "tally-export-v1"
_ALGORITHM = "HMAC-SHA256"


def canonical_json(rows: list[dict[str, Any]]) -> bytes:
    """Deterministic JSON encoding for signing.

    ``sort_keys=True`` to make the output stable across implementations.
    Compact ``separators`` to remove ambiguity around whitespace.
    ``default=str`` so Decimal / datetime survive serialisation — they
    are already pre-stringified upstream in ``app.tally.ingest._row_for``
    but we belt-and-brace here in case the export is called on a list
    built elsewhere."""
    return json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def sign_batch(
    rows: list[dict[str, Any]],
    *,
    signing_key: bytes | str | None = None,
    key_id: str,
    signed_at: datetime | None = None,
) -> dict[str, Any]:
    """Produce a signed envelope for ``rows``.

    Parameters
    ----------
    rows
        The list of dicts to sign. NOT mutated.
    signing_key
        HMAC key. When ``None``, falls back to the
        ``TALLY_EXPORT_SIGNING_KEY`` env (raises ``RuntimeError`` if also
        absent — refusing to sign with an empty key catches misconfigured
        production deploys at the call site rather than silently
        producing forgeable batches).
    key_id
        Caller-supplied identifier for the signing key. The consumer
        looks this up in a key catalogue to find the matching secret.
        Required; rotates without code changes.
    signed_at
        Optional override for the timestamp; mostly for deterministic
        tests. Defaults to ``datetime.now(timezone.utc)``.

    Raises
    ------
    RuntimeError
        When no signing key is provided AND
        ``TALLY_EXPORT_SIGNING_KEY`` is unset.
    """
    key = signing_key
    if key is None:
        env_key = os.environ.get("TALLY_EXPORT_SIGNING_KEY", "")
        if not env_key:
            raise RuntimeError(
                "no signing key supplied: pass signing_key=… or set "
                "TALLY_EXPORT_SIGNING_KEY",
            )
        key = env_key
    if isinstance(key, str):
        key = key.encode("utf-8")
    if not key:
        raise RuntimeError("signing key is empty")

    payload = canonical_json(rows)
    sha = hashlib.sha256(payload).hexdigest()
    mac = hmac.new(key, payload, hashlib.sha256).hexdigest()
    when = (signed_at or datetime.now(timezone.utc)).isoformat()

    return {
        "rows": rows,
        "sha256": sha,
        "hmac_sha256": mac,
        "signed_at": when,
        "key_id": key_id,
        "algorithm": _ALGORITHM,
        "version": _EXPORT_VERSION,
    }


def verify_batch(
    envelope: dict[str, Any],
    *,
    signing_key: bytes | str,
) -> bool:
    """Verify a signed envelope. Returns ``True`` iff the HMAC matches.

    Used by tests today, and by the auditor-side verifier later. Performs
    a constant-time comparison via :func:`hmac.compare_digest`."""
    rows = envelope.get("rows")
    expected_mac = envelope.get("hmac_sha256")
    if rows is None or expected_mac is None:
        return False

    key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
    payload = canonical_json(rows)

    # Optionally re-verify the SHA-256 too — cheap and catches the case
    # where someone has tampered with rows but recomputed only the HMAC.
    expected_sha = envelope.get("sha256")
    if expected_sha is not None:
        actual_sha = hashlib.sha256(payload).hexdigest()
        if not hmac.compare_digest(actual_sha, expected_sha):
            return False

    actual_mac = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(actual_mac, expected_mac)


__all__ = ["canonical_json", "sign_batch", "verify_batch"]
