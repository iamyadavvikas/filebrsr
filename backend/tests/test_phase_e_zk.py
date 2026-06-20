"""
Phase E — commitment scheme (ZK scaffold).

Acceptance:
- The hash commitment is binding+hiding: a correct opening verifies, a wrong
  value/blinding does not, and the commitment leaks nothing about the value.
- The Pedersen scaffold raises (no insecure placeholder is silently usable).
- The proving-system Prover/Verifier are explicit ``NotImplementedError`` stubs.
"""

from __future__ import annotations

import pytest

from app.zk import (
    Commitment,
    hash_commit,
    open_hash_commit,
    pedersen_commit,
    random_blinding,
)


def test_hash_commit_roundtrip():
    blinding = random_blinding()
    c = hash_commit("1234.56", blinding)
    assert isinstance(c, Commitment)
    assert c.scheme == "sha256-hash"
    assert open_hash_commit(c, "1234.56", blinding) is True


def test_hash_commit_rejects_wrong_value():
    blinding = random_blinding()
    c = hash_commit("1234.56", blinding)
    assert open_hash_commit(c, "1234.57", blinding) is False


def test_hash_commit_rejects_wrong_blinding():
    c = hash_commit("1234.56", random_blinding())
    assert open_hash_commit(c, "1234.56", random_blinding()) is False


def test_hash_commit_is_hiding():
    """Same value + different blindings → different commitments (hiding)."""
    a = hash_commit("100", random_blinding())
    b = hash_commit("100", random_blinding())
    assert a.commitment_hex != b.commitment_hex


def test_open_rejects_foreign_scheme():
    forged = Commitment(scheme="not-a-real-scheme", commitment_hex="00")
    assert open_hash_commit(forged, "100", random_blinding()) is False


def test_pedersen_commit_is_stub():
    with pytest.raises(NotImplementedError):
        pedersen_commit(100, 7)


def test_unimplemented_prover_verifier_raise():
    from app.zk import (
        Proof,
        RangeClaim,
        UnimplementedProver,
        UnimplementedVerifier,
    )

    c = hash_commit("50", random_blinding())
    claim = RangeClaim(commitment=c, lower=0, upper=100)
    with pytest.raises(NotImplementedError):
        UnimplementedProver().prove(claim, {"value": 50})
    with pytest.raises(NotImplementedError):
        UnimplementedVerifier().verify(
            claim, Proof(system="none", proof_b64="")
        )
