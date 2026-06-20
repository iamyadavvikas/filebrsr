"""
RFC 6962 Merkle tree primitives (domain-separated hashing).

Leaves are hashed ``SHA-256(0x00 || data)`` and internal nodes
``SHA-256(0x01 || left || right)``. This domain separation is what makes the
tree second-preimage resistant against leaf/node confusion. Used by the
tamper-evident ledger (Phase D) to produce signed tree heads and inclusion /
consistency proofs an auditor can recompute independently.
"""

from __future__ import annotations

import hashlib

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


def hash_leaf(data: bytes) -> bytes:
    """RFC 6962 leaf hash: SHA-256(0x00 || data)."""
    return hashlib.sha256(LEAF_PREFIX + data).digest()


def hash_node(left: bytes, right: bytes) -> bytes:
    """RFC 6962 interior node hash: SHA-256(0x01 || left || right)."""
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _split(n: int) -> int:
    """Largest power of two strictly less than n (RFC 6962 split point)."""
    k = 1
    while k < n:
        k <<= 1
    return k >> 1


def merkle_root(leaves: list[bytes]) -> bytes:
    """Root hash over already-leaf-hashed ``leaves`` (RFC 6962 MTH)."""
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return leaves[0]
    k = _split(n)
    return hash_node(merkle_root(leaves[:k]), merkle_root(leaves[k:]))


def inclusion_proof(leaves: list[bytes], index: int) -> list[bytes]:
    """Audit path proving ``leaves[index]`` is in the tree of ``leaves``."""
    n = len(leaves)
    if index < 0 or index >= n:
        raise IndexError(f"leaf index {index} out of range for tree size {n}")
    if n == 1:
        return []
    k = _split(n)
    if index < k:
        return inclusion_proof(leaves[:k], index) + [merkle_root(leaves[k:])]
    return inclusion_proof(leaves[k:], index - k) + [merkle_root(leaves[:k])]


def verify_inclusion(
    leaf_hash: bytes, index: int, tree_size: int, proof: list[bytes], root: bytes
) -> bool:
    """Recompute the root from a leaf + audit path and compare to ``root``."""
    if index < 0 or index >= tree_size:
        return False
    fn = index
    sn = tree_size - 1
    h = leaf_hash
    for sibling in proof:
        if fn % 2 == 1 or fn == sn:
            h = hash_node(sibling, h)
            while fn % 2 == 0 and fn != 0:
                fn >>= 1
                sn >>= 1
        else:
            h = hash_node(h, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and h == root


def consistency_proof(leaves: list[bytes], m: int, n: int) -> list[bytes]:
    """RFC 6962 consistency proof between tree sizes ``m`` (old) and ``n`` (new)."""
    if not 0 < m <= n <= len(leaves):
        raise ValueError(f"invalid consistency request m={m} n={n} size={len(leaves)}")
    if m == n:
        return []
    return _consistency(leaves[:n], m, n, True)


def _consistency(leaves: list[bytes], m: int, n: int, is_full: bool) -> list[bytes]:
    if m == n:
        return [] if is_full else [merkle_root(leaves)]
    k = _split(n)
    if m <= k:
        return _consistency(leaves[:k], m, k, is_full) + [merkle_root(leaves[k:])]
    return [merkle_root(leaves[:k])] + _consistency(
        leaves[k:], m - k, n - k, False
    )
