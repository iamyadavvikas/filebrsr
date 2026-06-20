"""Self-contained cryptographic core for the Carbon Assurance subsystem.

This is a dependency-light port of CarbonTrace's integrity primitives
(``carbontrace_core``) so FileBRSR can produce and *offline-verify* tamper-evident
emission records without pulling in ``rfc8785`` or external Merkle libraries. It
relies only on ``cryptography`` (already a FileBRSR dependency).

Design (matches CarbonTrace so bundles are conceptually identical):

* **Canonicalization** — deterministic JSON (sorted keys, tight separators). All
  numeric quantities are serialised as strings upstream (Pydantic ``mode="json"``)
  so there is no float drift. This is JCS-style; it is internally consistent
  between the signer here and the verifier in :mod:`app.assurance.verify_cli`.
* **Merkle tree** — RFC 6962 Merkle Tree Hash with domain separation
  (``0x00`` leaf prefix, ``0x01`` interior prefix); odd nodes are promoted, never
  duplicated. Inclusion proofs are a flat list of sibling hashes any language can
  re-verify with two hash primitives.
* **Signatures** — Ed25519 (raw 32-byte keys, base64 for JSON transport). Supplier
  keys sign each record; a server key signs Merkle checkpoint roots.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_LEAF_PREFIX = b"\x00"
_INTERIOR_PREFIX = b"\x01"


# ── Canonicalization & hashing ────────────────────────────────────────────────
def canonical_bytes(obj: Any) -> bytes:
    """Return deterministic canonical UTF-8 bytes for ``obj``.

    Sorted keys + tight separators make the output reproducible for any party
    that serialises the same logical object the same way.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def leaf_hash(record: Any, *, algorithm: str = "sha256") -> str:
    """Hex Merkle-leaf digest = ``sha256(0x00 || canonical(record))``."""
    h = hashlib.new(algorithm)
    h.update(_LEAF_PREFIX)
    h.update(canonical_bytes(record))
    return h.hexdigest()


# ── Merkle tree (RFC 6962) ────────────────────────────────────────────────────
@dataclass(frozen=True)
class ProofStep:
    """One sibling hash on the audit path. ``side`` says where the sibling sits."""

    side: str  # "L" if the sibling is on the left, "R" if on the right
    hash: str  # hex digest of the sibling node


def _hash_interior(left: bytes, right: bytes, algorithm: str) -> bytes:
    h = hashlib.new(algorithm)
    h.update(_INTERIOR_PREFIX)
    h.update(left)
    h.update(right)
    return h.digest()


def _largest_power_of_two_below(n: int) -> int:
    k = 1
    while k << 1 < n:
        k <<= 1
    return k


def merkle_root(leaves: list[bytes], *, algorithm: str = "sha256") -> bytes:
    """RFC 6962 Merkle Tree Hash over raw leaf digests."""
    if not leaves:
        return hashlib.new(algorithm).digest()
    if len(leaves) == 1:
        return leaves[0]
    k = _largest_power_of_two_below(len(leaves))
    left = merkle_root(leaves[:k], algorithm=algorithm)
    right = merkle_root(leaves[k:], algorithm=algorithm)
    return _hash_interior(left, right, algorithm)


def inclusion_path(
    leaves: list[bytes], index: int, *, algorithm: str = "sha256"
) -> list[ProofStep]:
    """Audit path proving ``leaves[index]`` is in the tree over ``leaves``."""
    if not 0 <= index < len(leaves):
        raise IndexError(f"leaf index {index} out of range for {len(leaves)} leaves")
    if len(leaves) == 1:
        return []
    k = _largest_power_of_two_below(len(leaves))
    if index < k:
        sub = inclusion_path(leaves[:k], index, algorithm=algorithm)
        sibling = merkle_root(leaves[k:], algorithm=algorithm)
        return [*sub, ProofStep(side="R", hash=sibling.hex())]
    sub = inclusion_path(leaves[k:], index - k, algorithm=algorithm)
    sibling = merkle_root(leaves[:k], algorithm=algorithm)
    return [*sub, ProofStep(side="L", hash=sibling.hex())]


def verify_inclusion(
    leaf_hex: str,
    root_hex: str,
    proof: list[ProofStep],
    *,
    algorithm: str = "sha256",
) -> bool:
    """Recompute the root from ``leaf_hex`` + ``proof`` and compare to ``root_hex``.

    Pure function: needs only the leaf digest, the claimed root and the sibling
    path. No tree state, server or database required.
    """
    try:
        acc = bytes.fromhex(leaf_hex)
        for step in proof:
            sibling = bytes.fromhex(step.hash)
            if step.side == "L":
                acc = _hash_interior(sibling, acc, algorithm)
            elif step.side == "R":
                acc = _hash_interior(acc, sibling, algorithm)
            else:
                return False
    except ValueError:
        return False
    return acc.hex() == root_hex


# ── Ed25519 signing ───────────────────────────────────────────────────────────
def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair as ``(private_b64, public_b64)`` raw keys."""
    private = Ed25519PrivateKey.generate()
    return (
        _b64encode(private.private_bytes_raw()),
        _b64encode(private.public_key().public_bytes_raw()),
    )


def keypair_from_seed(seed: str) -> tuple[str, str]:
    """Deterministically derive an Ed25519 ``(private_b64, public_b64)`` from a string.

    The private scalar is ``sha256(seed)`` (a valid raw 32-byte Ed25519 key). The
    signatures it produces are genuine Ed25519 signatures; the seed only makes the
    keypair reproducible (used for repeatable demo-supplier identities, never for
    the server checkpoint key \u2014 that comes from :func:`app.prov.get_signer`).
    """
    raw = hashlib.sha256(seed.encode("utf-8")).digest()
    private = Ed25519PrivateKey.from_private_bytes(raw)
    return (
        _b64encode(raw),
        _b64encode(private.public_key().public_bytes_raw()),
    )


def load_private_key(private_b64: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(_b64decode(private_b64))


def load_public_key(public_b64: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(_b64decode(public_b64))


def sign(private_b64: str, message: bytes) -> str:
    """Sign ``message`` with the base64 private key. Returns base64 signature."""
    return _b64encode(load_private_key(private_b64).sign(message))


def verify_signature(public_b64: str, message: bytes, signature_b64: str) -> bool:
    """Return ``True`` iff ``signature_b64`` is a valid signature of ``message``."""
    try:
        load_public_key(public_b64).verify(_b64decode(signature_b64), message)
    except (InvalidSignature, ValueError):
        return False
    return True


def root_header(root: str, size: int, algorithm: str) -> dict[str, Any]:
    """Canonical header the server signs for a checkpoint.

    Binding the root to its size + algorithm prevents replaying a root under a
    different tree size.
    """
    return {"algorithm": algorithm, "root": root, "size": size}


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))
