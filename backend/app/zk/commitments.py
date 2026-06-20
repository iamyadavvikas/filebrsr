"""
Cryptographic commitments for privacy-preserving disclosure (Phase E).

A commitment lets FileBRSR publish that it *holds* a confidential value (e.g. a
supplier's raw Scope-3 input) and later prove statements about it — without
revealing the value on the public `/verify` surface. The provenance graph can
store the commitment in place of the raw input.

Phase E ships the binding+hiding **hash commitment** (production-usable for
"reveal later" flows) and a **Pedersen** scaffold (additively homomorphic, for
range/sum proofs) whose elliptic-curve group operations are intentionally left
as a stub pending the proving-system decision in RFC 0003.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Commitment:
    """A commitment plus the scheme that produced it (opening kept off-graph)."""

    scheme: str
    commitment_hex: str


def random_blinding() -> bytes:
    """32-byte cryptographically secure blinding factor (the opening secret)."""
    return os.urandom(32)


def hash_commit(value: str, blinding: bytes) -> Commitment:
    """Hash commitment ``H(blinding || value)`` — binding + hiding.

    Binding: SHA-256 collision resistance. Hiding: the random blinding makes the
    commitment reveal nothing about ``value``. Open by revealing
    ``(value, blinding)`` and recomputing — see :func:`open_hash_commit`.
    """
    digest = hashlib.sha256(blinding + value.encode("utf-8")).hexdigest()
    return Commitment(scheme="sha256-hash", commitment_hex=digest)


def open_hash_commit(commitment: Commitment, value: str, blinding: bytes) -> bool:
    """Verify a hash commitment opening in constant time."""
    if commitment.scheme != "sha256-hash":
        return False
    recomputed = hashlib.sha256(blinding + value.encode("utf-8")).hexdigest()
    return hmac.compare_digest(recomputed, commitment.commitment_hex)


def pedersen_commit(value: int, blinding: int) -> Commitment:  # pragma: no cover - stub
    """Pedersen commitment ``g^value · h^blinding`` over an EC group.

    STUB. Additively homomorphic — required for range/sum proofs that show e.g.
    "Scope-3 reduction ≥ X%" without revealing inputs. The concrete curve +
    generators land with the proving-system decision (RFC 0003); until then this
    raises so no caller silently relies on an insecure placeholder.
    """
    raise NotImplementedError(
        "Pedersen commitments require an EC group (curve + NUMS generators) and "
        "land with the proving-system decision in docs/rfcs/0003-zk-verification.md."
    )
