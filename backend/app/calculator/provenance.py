"""
Bridge between the deterministic calculator and the provenance layer.

Turns a :class:`~app.calculator.results.CalculationResult` into a signed
W3C PROV-O graph (:mod:`app.prov`) and, when the tenancy/provenance tables
exist (migrations v15/v16), persists both the calculation and its signed
provenance record. Persistence is best-effort and never blocks returning a
signed graph to the caller.
"""

from __future__ import annotations

import logging
import uuid

from app.calculator.results import CalculationResult
from app.prov import (
    CalculationProvenanceInput,
    SignedProvenance,
    build_signed_provenance,
)

logger = logging.getLogger("filebrsr.calculator")


def result_to_prov_input(
    result: CalculationResult, *, org_id: str, calculation_id: str
) -> CalculationProvenanceInput:
    """Map a CalculationResult onto the provenance input contract."""
    return CalculationProvenanceInput(
        calculation_id=calculation_id,
        org_id=org_id,
        value=result.value,
        unit=result.unit,
        method=result.method,
        factor_id=result.factor_id,
        factor_version=result.factor_version,
        input_record_ids=list(result.input_record_ids),
        calculation_timestamp=result.calculation_timestamp,
        factor_source=result.factor_source,
        factor_citation=result.factor_citation,
        uncertainty=result.uncertainty,
        agent_run_id=result.agent_run_id,
    )


def sign_result(
    result: CalculationResult,
    *,
    org_id: str,
    calculation_id: str | None = None,
) -> tuple[str, SignedProvenance]:
    """Build + Ed25519-sign the PROV-O graph for a calculation.

    Returns ``(calculation_id, SignedProvenance)``. Pure/​DB-free so it works
    today, before the v15/v16 migrations are applied.
    """
    calc_id = calculation_id or str(uuid.uuid4())
    prov_input = result_to_prov_input(result, org_id=org_id, calculation_id=calc_id)
    return calc_id, build_signed_provenance(prov_input)


def persist_calculation(
    supabase,
    *,
    result: CalculationResult,
    signed: SignedProvenance,
    calculation_id: str,
    org_id: str,
    user_id: str | None = None,
) -> bool:
    """Best-effort persist to ``calculations`` + ``provenance_records``.

    Requires migrations v15/v16. Returns True on success; logs and returns
    False if the tables do not yet exist or the write fails, so the caller
    can still return the signed graph to the user.
    """
    try:
        supabase.table("calculations").insert(
            {
                "id": calculation_id,
                "org_id": org_id,
                "user_id": user_id,
                "scope": result.scope,
                "category": result.category,
                "method": result.method,
                "value": str(result.value),
                "unit": result.unit,
                "factor_id": result.factor_id,
                "factor_version": result.factor_version,
                "factor_source": result.factor_source,
                "factor_citation": result.factor_citation,
                "input_record_ids": [
                    int(r) for r in result.input_record_ids if str(r).isdigit()
                ],
                "uncertainty": result.uncertainty,
                "agent_run_id": result.agent_run_id,
                "calculated_by_version": "4.0.0",
                "calculation_timestamp": result.calculation_timestamp.isoformat(),
            }
        ).execute()
        supabase.table("provenance_records").insert(
            {
                "calculation_id": calculation_id,
                "org_id": org_id,
                "prov_graph": signed.graph,
                "canonical_sha256": signed.canonical_sha256,
                "algorithm": signed.algorithm,
                "signature_b64": signed.signature_b64,
                "public_key_b64": signed.public_key_b64,
                "key_id": signed.key_id,
                "signed_at": signed.signed_at,
            }
        ).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "persist_calculation skipped (tables present? migrations v15/v16 "
            "applied?): %s",
            exc,
        )
        return False
