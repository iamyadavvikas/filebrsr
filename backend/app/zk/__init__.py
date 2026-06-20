"""
``app.zk`` — privacy-preserving disclosure primitives (Phase E).

Production-usable hash commitments today; a Pedersen + ZK-proof scaffold whose
concrete proving system is decided in docs/rfcs/0003-zk-verification.md. The
goal: prove statements about confidential ESG inputs (e.g. supplier Scope-3
data) without revealing them on the public verify surface.
"""

from __future__ import annotations

from app.zk.claims import (
    Proof,
    Prover,
    RangeClaim,
    ReductionClaim,
    UnimplementedProver,
    UnimplementedVerifier,
    Verifier,
)
from app.zk.commitments import (
    Commitment,
    hash_commit,
    open_hash_commit,
    pedersen_commit,
    random_blinding,
)

__all__ = [
    "Commitment",
    "hash_commit",
    "open_hash_commit",
    "pedersen_commit",
    "random_blinding",
    "RangeClaim",
    "ReductionClaim",
    "Proof",
    "Prover",
    "Verifier",
    "UnimplementedProver",
    "UnimplementedVerifier",
]
