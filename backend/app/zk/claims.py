"""
Zero-knowledge claim interfaces (Phase E, design + stub).

Defines the statements FileBRSR wants to prove about confidential ESG data
without revealing it — e.g. "this supplier's verified Scope-3 reduction is at
least X%" — and the pluggable Prover/Verifier interface those proofs flow
through. The concrete proving system (Groth16 / PLONK / Bulletproofs) is chosen
in RFC 0003; this module fixes the contract so the rest of the platform can be
built against it now.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.zk.commitments import Commitment


@dataclass(frozen=True)
class RangeClaim:
    """Statement: the committed value lies in ``[lower, upper]``."""

    commitment: Commitment
    lower: int
    upper: int
    unit: str = ""


@dataclass(frozen=True)
class ReductionClaim:
    """Statement: ``(baseline - current) / baseline >= min_fraction``.

    Proven over commitments to ``baseline`` and ``current`` so neither absolute
    figure is revealed — only that the reduction meets the threshold.
    """

    baseline_commitment: Commitment
    current_commitment: Commitment
    min_fraction: float


@dataclass(frozen=True)
class Proof:
    """An opaque proof blob plus public inputs, for a named proving system."""

    system: str
    proof_b64: str
    public_inputs: dict[str, Any] = field(default_factory=dict)


class Prover(Protocol):
    """Produces a :class:`Proof` for a claim and its private witness."""

    def prove(self, claim: Any, witness: dict[str, Any]) -> Proof: ...


class Verifier(Protocol):
    """Checks a :class:`Proof` against a claim's public statement."""

    def verify(self, claim: Any, proof: Proof) -> bool: ...


class UnimplementedProver:
    """Placeholder Prover — raises until a proving system is wired (RFC 0003)."""

    def prove(self, claim: Any, witness: dict[str, Any]) -> Proof:  # pragma: no cover - stub
        raise NotImplementedError(
            "ZK proving is design-only in Phase E. Choose a proving system "
            "(Groth16 / PLONK / Bulletproofs) per docs/rfcs/0003-zk-verification.md "
            "before enabling proofs."
        )


class UnimplementedVerifier:
    """Placeholder Verifier — raises until a proving system is wired (RFC 0003)."""

    def verify(self, claim: Any, proof: Proof) -> bool:  # pragma: no cover - stub
        raise NotImplementedError(
            "ZK verification is design-only in Phase E. See "
            "docs/rfcs/0003-zk-verification.md."
        )
