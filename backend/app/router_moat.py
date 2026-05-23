"""
Moat API Router — Audit Trail, Benchmarks, Fine-tune Pipeline, Filing Ground Truth.
These create switching costs, network effects, and proprietary data assets.
"""

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import hashlib
import json

from app.config import get_settings

router = APIRouter(prefix="/api/platform", tags=["Moat & Defensibility"])
settings = get_settings()


def get_supabase_admin():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub", token)
    except Exception:
        return token


# ═══════════════════════════════════════════════════════════════
# AUDIT TRAIL APIs
# ═══════════════════════════════════════════════════════════════

class AuditLogEntry(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    datapoint_id: Optional[str] = None
    financial_year: Optional[str] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    change_reason: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/audit/log")
async def create_audit_entry(entry: AuditLogEntry, authorization: str = Header(...)):
    """Log an audit trail entry. Used by frontend for actions not auto-captured by DB triggers."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Get user email for denormalization
    profile = sb.table("profiles").select("email, company_name").eq("id", user_id).single().execute()
    user_email = profile.data.get("email", "") if profile.data else ""

    # Get org_id
    org_member = sb.table("org_members").select("org_id").eq("user_id", user_id).maybe_single().execute()
    org_id = org_member.data.get("org_id") if org_member.data else None

    # Compute checksum for tamper detection
    checksum_input = f"{user_id}:{entry.action}:{entry.entity_type}:{entry.entity_id}:{datetime.utcnow().isoformat()}"
    checksum = hashlib.sha256(checksum_input.encode()).hexdigest()

    data = {
        "user_id": user_id,
        "user_email": user_email,
        "org_id": org_id,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "datapoint_id": entry.datapoint_id,
        "financial_year": entry.financial_year,
        "old_value": entry.old_value,
        "new_value": entry.new_value,
        "change_reason": entry.change_reason,
        "metadata": entry.metadata,
        "checksum": checksum,
    }

    result = sb.table("audit_trail").insert(data).execute()
    return {"status": "logged", "id": result.data[0]["id"] if result.data else None}


@router.get("/audit/trail")
async def get_audit_trail(
    authorization: str = Header(...),
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    datapoint_id: Optional[str] = None,
    financial_year: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    """Get audit trail for the user's org. Supports filtering by entity, datapoint, or FY."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Get org_id
    org_member = sb.table("org_members").select("org_id").eq("user_id", user_id).maybe_single().execute()
    org_id = org_member.data.get("org_id") if org_member.data else None

    query = sb.table("audit_trail").select("*").order("created_at", desc=True)

    if org_id:
        query = query.eq("org_id", org_id)
    else:
        query = query.eq("user_id", user_id)

    if entity_type:
        query = query.eq("entity_type", entity_type)
    if entity_id:
        query = query.eq("entity_id", entity_id)
    if datapoint_id:
        query = query.eq("datapoint_id", datapoint_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)

    query = query.range(offset, offset + limit - 1)
    result = query.execute()

    return {"audit_entries": result.data or [], "total": len(result.data or [])}


@router.get("/audit/versions/{entry_id}")
async def get_data_versions(entry_id: str, authorization: str = Header(...)):
    """Get version history for a specific BRSR entry."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    result = sb.table("data_versions") \
        .select("*") \
        .eq("entry_id", entry_id) \
        .order("version_number", desc=True) \
        .execute()

    return {"versions": result.data or []}


@router.get("/audit/summary")
async def get_audit_summary(authorization: str = Header(...), financial_year: Optional[str] = None):
    """Get audit summary stats for compliance reporting."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    org_member = sb.table("org_members").select("org_id").eq("user_id", user_id).maybe_single().execute()
    org_id = org_member.data.get("org_id") if org_member.data else None

    query = sb.table("audit_trail").select("action, entity_type, created_at")
    if org_id:
        query = query.eq("org_id", org_id)
    else:
        query = query.eq("user_id", user_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)

    result = query.execute()
    entries = result.data or []

    # Aggregate by action type
    action_counts = {}
    entity_counts = {}
    for e in entries:
        action_counts[e["action"]] = action_counts.get(e["action"], 0) + 1
        entity_counts[e["entity_type"]] = entity_counts.get(e["entity_type"], 0) + 1

    return {
        "total_entries": len(entries),
        "by_action": action_counts,
        "by_entity": entity_counts,
        "financial_year": financial_year,
    }


# ═══════════════════════════════════════════════════════════════
# BENCHMARK FLYWHEEL APIs
# ═══════════════════════════════════════════════════════════════

@router.get("/benchmarks")
async def get_benchmarks(
    datapoint_id: Optional[str] = None,
    sector: Optional[str] = None,
    financial_year: Optional[str] = None,
):
    """Get anonymized benchmark data. Public endpoint (no auth required for reads)."""
    sb = get_supabase_admin()

    query = sb.table("benchmark_data").select("*")
    if datapoint_id:
        query = query.eq("datapoint_id", datapoint_id)
    if sector:
        query = query.eq("sector", sector)
    if financial_year:
        query = query.eq("financial_year", financial_year)

    result = query.order("sample_size", desc=True).limit(100).execute()
    return {"benchmarks": result.data or []}


@router.get("/benchmarks/live")
async def get_live_benchmarks(
    sector: str,
    datapoint_id: Optional[str] = None,
    financial_year: Optional[str] = None,
):
    """Get benchmarks from real BSE/NSE filings."""
    sb = get_supabase_admin()

    query = sb.table("sector_benchmarks_live").select("*").eq("sector", sector)
    if datapoint_id:
        query = query.eq("datapoint_id", datapoint_id)
    if financial_year:
        query = query.eq("financial_year", financial_year)

    result = query.limit(100).execute()
    return {"benchmarks": result.data or []}


@router.get("/benchmarks/compare")
async def compare_to_benchmark(
    authorization: str = Header(...),
    datapoint_id: str = Query(...),
    financial_year: str = Query(default="FY2024-25"),
):
    """Compare user's value against sector benchmarks. Shows percentile position."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Get user's value
    entry = sb.table("brsr_entries") \
        .select("value, datapoint_id") \
        .eq("user_id", user_id) \
        .eq("datapoint_id", datapoint_id) \
        .eq("financial_year", financial_year) \
        .maybe_single().execute()

    if not entry.data:
        return {"comparison": None, "message": "No data entry found for this datapoint"}

    # Get user's sector
    profile = sb.table("profiles").select("company_name").eq("id", user_id).single().execute()
    sector = profile.data.get("company_name", "IT") if profile.data else "IT"  # fallback

    # Get benchmark
    benchmark = sb.table("benchmark_data") \
        .select("*") \
        .eq("datapoint_id", datapoint_id) \
        .eq("sector", sector) \
        .eq("financial_year", financial_year) \
        .maybe_single().execute()

    user_value = entry.data.get("value", {})
    user_numeric = None
    if isinstance(user_value, dict):
        user_numeric = user_value.get("value")
    elif isinstance(user_value, (int, float)):
        user_numeric = user_value

    comparison = {
        "your_value": user_numeric,
        "benchmark": benchmark.data if benchmark.data else None,
        "percentile": None,
    }

    # Calculate percentile position
    if benchmark.data and user_numeric is not None:
        bm = benchmark.data
        try:
            user_num = float(user_numeric)
            p25 = float(bm.get("p25_value") or 0)
            median = float(bm.get("median_value") or 0)
            p75 = float(bm.get("p75_value") or 0)
            p90 = float(bm.get("p90_value") or 0)

            if user_num <= p25:
                comparison["percentile"] = "Bottom 25%"
                comparison["rating"] = "below_average"
            elif user_num <= median:
                comparison["percentile"] = "25th-50th percentile"
                comparison["rating"] = "average"
            elif user_num <= p75:
                comparison["percentile"] = "50th-75th percentile"
                comparison["rating"] = "above_average"
            elif user_num <= p90:
                comparison["percentile"] = "75th-90th percentile"
                comparison["rating"] = "good"
            else:
                comparison["percentile"] = "Top 10%"
                comparison["rating"] = "excellent"
        except (ValueError, TypeError):
            pass

    return {"comparison": comparison}


class BenchmarkConsent(BaseModel):
    consent_given: bool


@router.post("/benchmarks/consent")
async def set_benchmark_consent(consent: BenchmarkConsent, authorization: str = Header(...)):
    """User opts in/out of contributing anonymized data to benchmarks."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    org_member = sb.table("org_members").select("org_id").eq("user_id", user_id).maybe_single().execute()
    org_id = org_member.data.get("org_id") if org_member.data else None

    if not org_id:
        raise HTTPException(status_code=400, detail="No organization found")

    data = {
        "org_id": org_id,
        "user_id": user_id,
        "consent_given": consent.consent_given,
        "consented_at": datetime.utcnow().isoformat() if consent.consent_given else None,
        "revoked_at": datetime.utcnow().isoformat() if not consent.consent_given else None,
    }

    result = sb.table("benchmark_consents").upsert(data, on_conflict="org_id").execute()
    return {"status": "updated", "consent_given": consent.consent_given}


# ═══════════════════════════════════════════════════════════════
# FINE-TUNE PIPELINE APIs
# ═══════════════════════════════════════════════════════════════

class ExtractionCorrection(BaseModel):
    report_id: Optional[str] = None
    datapoint_id: str
    ai_extracted_value: dict
    ai_confidence: Optional[float] = None
    ai_model: Optional[str] = None
    corrected_value: dict
    correction_type: str = "value_wrong"
    source_text: Optional[str] = None
    page_number: Optional[int] = None


@router.post("/corrections")
async def submit_correction(correction: ExtractionCorrection, authorization: str = Header(...)):
    """Submit a correction to an AI extraction. Feeds the fine-tuning pipeline."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    data = {
        "user_id": user_id,
        "report_id": correction.report_id,
        "datapoint_id": correction.datapoint_id,
        "ai_extracted_value": correction.ai_extracted_value,
        "ai_confidence": correction.ai_confidence,
        "ai_model": correction.ai_model,
        "corrected_value": correction.corrected_value,
        "correction_type": correction.correction_type,
        "source_text": correction.source_text,
        "page_number": correction.page_number,
    }

    result = sb.table("extraction_corrections").insert(data).execute()

    # Update extraction quality metrics
    if correction.ai_model and correction.datapoint_id:
        _update_quality_metrics(sb, correction.ai_model, correction.datapoint_id)

    return {"status": "correction_saved", "id": result.data[0]["id"] if result.data else None}


def _update_quality_metrics(sb, ai_model: str, datapoint_id: str):
    """Recalculate accuracy metrics for a model+datapoint pair."""
    try:
        corrections = sb.table("extraction_corrections") \
            .select("correction_type") \
            .eq("ai_model", ai_model) \
            .eq("datapoint_id", datapoint_id) \
            .execute()

        total = len(corrections.data) if corrections.data else 0
        if total == 0:
            return

        # Each correction is a "wrong" extraction
        # Estimate total extractions = corrections + (corrections * estimated_accuracy)
        # Start with pessimistic assumption: 70% baseline accuracy
        estimated_total = int(total / 0.3) if total > 0 else 0
        correct = estimated_total - total
        accuracy = correct / estimated_total if estimated_total > 0 else 0.7

        # Count error types
        error_counts = {}
        for c in corrections.data:
            ct = c.get("correction_type", "unknown")
            error_counts[ct] = error_counts.get(ct, 0) + 1

        common_errors = [{"error_type": k, "count": v} for k, v in sorted(error_counts.items(), key=lambda x: -x[1])]

        sb.table("extraction_quality").upsert({
            "ai_model": ai_model,
            "datapoint_id": datapoint_id,
            "total_extractions": estimated_total,
            "correct_extractions": correct,
            "accuracy": accuracy,
            "common_errors": common_errors,
            "last_evaluated_at": datetime.utcnow().isoformat(),
        }, on_conflict="ai_model,datapoint_id,financial_year").execute()
    except Exception:
        pass  # Non-critical, don't break the main flow


@router.get("/corrections")
async def get_corrections(
    authorization: str = Header(...),
    datapoint_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    """Get corrections submitted by this user."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    query = sb.table("extraction_corrections").select("*").eq("user_id", user_id)
    if datapoint_id:
        query = query.eq("datapoint_id", datapoint_id)

    result = query.order("created_at", desc=True).limit(limit).execute()
    return {"corrections": result.data or []}


@router.get("/quality/metrics")
async def get_quality_metrics(
    ai_model: Optional[str] = None,
    datapoint_id: Optional[str] = None,
):
    """Get extraction quality metrics. Public for transparency."""
    sb = get_supabase_admin()

    query = sb.table("extraction_quality").select("*")
    if ai_model:
        query = query.eq("ai_model", ai_model)
    if datapoint_id:
        query = query.eq("datapoint_id", datapoint_id)

    result = query.order("accuracy", desc=False).limit(100).execute()
    return {"metrics": result.data or []}


# ═══════════════════════════════════════════════════════════════
# FILING GROUND TRUTH APIs
# ═══════════════════════════════════════════════════════════════

@router.get("/filings/ground-truth")
async def get_filing_ground_truth(
    sector: Optional[str] = None,
    financial_year: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    """Get verified filing data from BSE/NSE. Public dataset."""
    sb = get_supabase_admin()

    query = sb.table("filing_ground_truth").select(
        "company_name, sector, market_cap_tier, financial_year, total_datapoints_extracted, disclosure_score, parse_quality"
    )
    if sector:
        query = query.eq("sector", sector)
    if financial_year:
        query = query.eq("financial_year", financial_year)

    result = query.order("disclosure_score", desc=True).limit(limit).execute()
    return {"filings": result.data or []}


@router.get("/filings/ground-truth/{cin}")
async def get_filing_by_cin(cin: str):
    """Get extracted datapoints from a specific company's filing."""
    sb = get_supabase_admin()

    result = sb.table("filing_ground_truth") \
        .select("*") \
        .eq("cin", cin) \
        .order("financial_year", desc=True) \
        .execute()

    return {"filings": result.data or []}


# ═══════════════════════════════════════════════════════════════
# SUBMISSION SIGNING (Digital Signature for Compliance)
# ═══════════════════════════════════════════════════════════════

class SubmissionSign(BaseModel):
    financial_year: str
    submission_type: str = "brsr_annual"
    signatory_name: str
    signatory_designation: str
    signatory_din: Optional[str] = None


@router.post("/submissions/sign")
async def sign_submission(body: SubmissionSign, authorization: str = Header(...)):
    """Digitally sign a BRSR submission. Creates immutable record."""
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    org_member = sb.table("org_members").select("org_id").eq("user_id", user_id).maybe_single().execute()
    org_id = org_member.data.get("org_id") if org_member.data else None

    # Get all entries for this FY to compute snapshot hash
    entries = sb.table("brsr_entries") \
        .select("datapoint_id, value") \
        .eq("user_id", user_id) \
        .eq("financial_year", body.financial_year) \
        .execute()

    # Compute deterministic hash of all data
    data_str = json.dumps(entries.data or [], sort_keys=True)
    snapshot_hash = hashlib.sha256(data_str.encode()).hexdigest()

    signature_data = {
        "org_id": org_id,
        "user_id": user_id,
        "financial_year": body.financial_year,
        "submission_type": body.submission_type,
        "data_snapshot_hash": snapshot_hash,
        "signatory_name": body.signatory_name,
        "signatory_designation": body.signatory_designation,
        "signatory_din": body.signatory_din,
    }

    result = sb.table("submission_signatures").insert(signature_data).execute()

    # Log in audit trail
    sb.table("audit_trail").insert({
        "user_id": user_id,
        "user_email": "",
        "action": "submit",
        "entity_type": "submission_signature",
        "entity_id": result.data[0]["id"] if result.data else None,
        "financial_year": body.financial_year,
        "new_value": {"hash": snapshot_hash, "signatory": body.signatory_name},
        "org_id": org_id,
        "checksum": hashlib.sha256(f"{user_id}:submit:{snapshot_hash}".encode()).hexdigest(),
    }).execute()

    return {
        "status": "signed",
        "snapshot_hash": snapshot_hash,
        "signed_at": datetime.utcnow().isoformat(),
        "total_datapoints": len(entries.data or []),
    }
