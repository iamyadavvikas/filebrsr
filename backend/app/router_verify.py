"""
Public verification surface (Phase C).

Lets anyone independently confirm that a disclosed FileBRSR number is
authentic and untampered, with no login. Given a ``calculation_id`` we load
its signed PROV-O record, re-canonicalise + re-verify the Ed25519 signature
(:func:`app.prov.verify_signed_provenance`), and report PASS/FAIL plus the
factor lineage. An auditor evidence bundle is available at ``/bundle``.

Exposure is **published-only**: a calculation is verifiable only once its org
flags it ``published`` (migration v18). Records without that flag set return
404 so internal drafts can't be enumerated. Pre-migration (no ``published``
column yet) the gate is skipped so the surface works during rollout.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.metrics import record_verification
from app.prov import SignedProvenance, verify_signed_provenance

logger = logging.getLogger("filebrsr.verify")

router = APIRouter(prefix="/api/verify", tags=["Verify"])
settings = get_settings()

# ─── lightweight per-IP rate limit (public, unauthenticated) ────────────────
_VERIFY_LOG: dict[str, list[datetime]] = defaultdict(list)
_VERIFY_LOCK = threading.Lock()
_VERIFY_WINDOW = timedelta(minutes=1)
_VERIFY_LIMIT = 30  # per IP per minute, per worker process


def get_supabase_admin():
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = datetime.utcnow()
    cutoff = now - _VERIFY_WINDOW
    with _VERIFY_LOCK:
        history = [t for t in _VERIFY_LOG[ip] if t > cutoff]
        if len(history) >= _VERIFY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many verification requests. Try again shortly.",
                headers={"Retry-After": "60"},
            )
        history.append(now)
        _VERIFY_LOG[ip] = history
        if len(_VERIFY_LOG) > 10000:
            for k in list(_VERIFY_LOG.keys()):
                _VERIFY_LOG[k] = [t for t in _VERIFY_LOG[k] if t > cutoff]
                if not _VERIFY_LOG[k]:
                    del _VERIFY_LOG[k]


def _load_published_record(calculation_id: str) -> tuple[dict, dict]:
    """Return ``(provenance_record, calculation)`` for a published calc or 404."""
    sb = get_supabase_admin()
    try:
        prov = (
            sb.table("provenance_records")
            .select("*")
            .eq("calculation_id", calculation_id)
            .single()
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("verify: provenance lookup failed for %s: %s", calculation_id, exc)
        raise HTTPException(status_code=404, detail="Record not found") from exc
    if not prov.data:
        raise HTTPException(status_code=404, detail="Record not found")

    calc: dict = {}
    try:
        calc_resp = (
            sb.table("calculations")
            .select("*")
            .eq("id", calculation_id)
            .single()
            .execute()
        )
        calc = calc_resp.data or {}
    except Exception as exc:  # noqa: BLE001
        logger.info("verify: calculation lookup failed for %s: %s", calculation_id, exc)

    # Published-only gate. Skip if the column doesn't exist yet (pre-v18).
    if "published" in calc and not calc["published"]:
        raise HTTPException(status_code=404, detail="Record not found")

    return prov.data, calc


def _signed_from_record(prov: dict) -> SignedProvenance:
    return SignedProvenance(
        graph=prov.get("prov_graph") or {},
        canonical_sha256=prov.get("canonical_sha256", ""),
        signature_b64=prov.get("signature_b64", ""),
        public_key_b64=prov.get("public_key_b64", ""),
        algorithm=prov.get("algorithm", "Ed25519"),
        key_id=prov.get("key_id", ""),
        signed_at=prov.get("signed_at", ""),
        extra_signatures=prov.get("extra_signatures") or [],
    )


def _inclusion_proof(org_id, calculation_id: str) -> dict | None:
    """Merkle inclusion proof for a calculation, if the ledger has it (Phase D)."""
    if not org_id:
        return None
    try:
        from app.ledger import get_inclusion_proof

        sb = get_supabase_admin()
        return get_inclusion_proof(
            sb, org_id=org_id, ref_table="calculations", ref_pk=calculation_id
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("verify: inclusion proof lookup failed for %s: %s", calculation_id, exc)
        return None


@router.get("/{calculation_id}")
async def verify_calculation(calculation_id: str, request: Request):
    """Verify a published calculation's signed provenance. PASS/FAIL + lineage."""
    _check_rate_limit(request)
    prov, calc = _load_published_record(calculation_id)
    signed = _signed_from_record(prov)
    verified = verify_signed_provenance(signed)
    record_verification(verified)
    inclusion = _inclusion_proof(calc.get("org_id"), calculation_id)

    return {
        "calculation_id": calculation_id,
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "algorithm": signed.algorithm,
        "key_id": signed.key_id,
        "signed_at": signed.signed_at,
        "value": calc.get("value"),
        "unit": calc.get("unit"),
        "scope": calc.get("scope"),
        "method": calc.get("method"),
        "jurisdiction": calc.get("jurisdiction"),
        "factor": {
            "id": calc.get("factor_id"),
            "version": calc.get("factor_version"),
            "source": calc.get("factor_source"),
            "citation_url": calc.get("factor_citation"),
        },
        "ledger_inclusion": inclusion,
        "provenance_graph": signed.graph,
    }


@router.get("/{calculation_id}/bundle")
async def verify_bundle(calculation_id: str, request: Request):
    """Auditor evidence bundle: signed record + factor citation, self-verifying."""
    _check_rate_limit(request)
    prov, calc = _load_published_record(calculation_id)
    signed = _signed_from_record(prov)
    verified = verify_signed_provenance(signed)
    record_verification(verified)
    inclusion = _inclusion_proof(calc.get("org_id"), calculation_id)

    return {
        "calculation_id": calculation_id,
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "calculation": {
            "value": calc.get("value"),
            "unit": calc.get("unit"),
            "scope": calc.get("scope"),
            "category": calc.get("category"),
            "method": calc.get("method"),
            "jurisdiction": calc.get("jurisdiction"),
            "factor_id": calc.get("factor_id"),
            "factor_version": calc.get("factor_version"),
            "factor_source": calc.get("factor_source"),
            "factor_citation": calc.get("factor_citation"),
            "calculation_timestamp": calc.get("calculation_timestamp"),
        },
        "signature": {
            "algorithm": signed.algorithm,
            "key_id": signed.key_id,
            "signed_at": signed.signed_at,
            "canonical_sha256": signed.canonical_sha256,
            "signature_b64": signed.signature_b64,
            "public_key_b64": signed.public_key_b64,
            "extra_signatures": signed.extra_signatures,
        },
        "ledger_inclusion": inclusion,
        "provenance_graph": signed.graph,
        "how_to_verify": (
            "Re-canonicalise provenance_graph (RFC 8785), SHA-256 it, confirm it "
            "equals signature.canonical_sha256, then verify signature_b64 over "
            "that digest with public_key_b64 (Ed25519). For ledger_inclusion, "
            "recompute the RFC 6962 leaf from payload and walk proof to "
            "signed_root.merkle_root, then check the root signature."
        ),
    }
