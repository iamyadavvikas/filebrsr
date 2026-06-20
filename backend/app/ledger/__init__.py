"""
``app.ledger`` — tamper-evident Merkle transparency log (Phase D).

Augments the plain append-only ``audit_log`` (v15) with cryptographic
tamper-evidence: events become RFC 6962 Merkle leaves and each new tree head is
Ed25519-signed (reusing :mod:`app.prov`). Mutating any stored row breaks both
the leaf recomputation and the signed root.
"""

from __future__ import annotations

from app.ledger.merkle import (
    consistency_proof,
    hash_leaf,
    hash_node,
    inclusion_proof,
    merkle_root,
    verify_inclusion,
)
from app.ledger.service import append_event, get_inclusion_proof

__all__ = [
    "hash_leaf",
    "hash_node",
    "merkle_root",
    "inclusion_proof",
    "verify_inclusion",
    "consistency_proof",
    "append_event",
    "get_inclusion_proof",
]
