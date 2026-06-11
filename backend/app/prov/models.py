"""
Typed inputs and outputs for the provenance layer.

These dataclasses are intentionally framework-free (no FastAPI/Supabase
imports) so the provenance builder is unit-testable in isolation and can be
reused by the worker, the calculator, and the ingestion API alike.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

# Current calculator/software-agent identity stamped into every graph.
SOFTWARE_AGENT = "filebrsr-calculator"
SOFTWARE_AGENT_VERSION = "4.0.0"


@dataclass(frozen=True)
class CalculationProvenanceInput:
    """Everything needed to assert provenance for one calculated number.

    Mirrors the charter's ``CalculationResult`` contract. ``value`` accepts
    ``Decimal | int | str`` and is serialised as a string in the graph so the
    canonical form never contains a JSON float (audit determinism).
    """

    calculation_id: str
    org_id: str
    value: Decimal | int | str
    unit: str
    method: str
    factor_id: str
    factor_version: str
    input_record_ids: list[str]
    calculation_timestamp: datetime
    factor_source: str | None = None
    factor_citation: str | None = None
    uncertainty: dict[str, Any] | None = None
    agent_run_id: str | None = None
    software_agent: str = SOFTWARE_AGENT
    software_agent_version: str = SOFTWARE_AGENT_VERSION


@dataclass(frozen=True)
class SignedProvenance:
    """A PROV-O graph plus its canonical hash and Ed25519 signature."""

    graph: dict[str, Any]
    canonical_sha256: str
    signature_b64: str
    public_key_b64: str
    algorithm: str
    key_id: str
    signed_at: str
    extra_signatures: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise for storage (e.g. the ``calculations`` / signatures tables)."""
        return {
            "graph": self.graph,
            "canonical_sha256": self.canonical_sha256,
            "signature_b64": self.signature_b64,
            "public_key_b64": self.public_key_b64,
            "algorithm": self.algorithm,
            "key_id": self.key_id,
            "signed_at": self.signed_at,
            "extra_signatures": self.extra_signatures,
        }
