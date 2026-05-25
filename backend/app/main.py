from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfplumber
import io
import time
import logging
import sentry_sdk
from supabase import create_client

from app.config import get_settings

# ─── Structured Logging ───────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("filebrsr")

# ─── Sentry Error Tracking ────────────────────────────────────
_settings = get_settings()
if _settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=_settings.SENTRY_DSN,
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        environment=_settings.ENVIRONMENT,
    )
    logger.info("Sentry initialized for %s", _settings.ENVIRONMENT)
from app.extraction import extract_with_regex, calculate_confidence
from app.extraction_enhanced import extract_enhanced
from app.ai_extraction import extract_with_ai
from app.agent_extraction import extract_with_agent
from app.brsr_framework import analyze_gaps, BRSR_FRAMEWORK, get_mandatory_fields, get_core_fields
from app.brsr_datapoints import BRSR_DATAPOINTS, get_datapoints_stats, analyze_gaps_v2, get_esrs_mapped_datapoints
from app.nifty50_benchmarks import (
    SECTOR_BENCHMARKS, detect_sector, get_benchmark_comparison,
    NIFTY50_DISCLOSURE_PATTERNS, BENCHMARK_METADATA,
)
from app.billing import router as billing_router
from app.pdf_generator import generate_compliance_pdf
from app.router_v2 import router as v2_router
from app.router_platform import router as platform_router
from app.router_advanced import router as advanced_router
from app.router_org import router as org_router
from app.router_moat import router as moat_router
from app.router_market import router as market_router
from app.excel_import import router as excel_import_router
from app.router_cron import router as cron_router
from app.xbrl_export import router as xbrl_router
from app.xbrl_filing import router as xbrl_filing_router
from app.sebi_pdf_filing import router as sebi_pdf_router
from app.router_trends import router as trends_router

app = FastAPI(title="FileBRSR Platform API", version="4.0.0")

settings = get_settings()


# ─── Simple IP rate limiter for public endpoints ──────────────────────────
from collections import defaultdict
from datetime import datetime, timedelta

_GUEST_EXTRACT_LOG: dict[str, list[datetime]] = defaultdict(list)
_GUEST_EXTRACT_DAILY_LIMIT = 3  # per IP per 24h, per worker process


def _client_ip(request: Request) -> str:
    """Resolve the real client IP behind nginx/Cloudflare proxies."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    real = request.headers.get("x-real-ip", "")
    if real:
        return real
    return request.client.host if request.client else "unknown"


def _check_guest_rate_limit(request: Request) -> None:
    """Raise 429 if this IP has exceeded the guest extraction quota."""
    ip = _client_ip(request)
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    history = [t for t in _GUEST_EXTRACT_LOG[ip] if t > cutoff]
    if len(history) >= _GUEST_EXTRACT_DAILY_LIMIT:
        oldest = min(history)
        retry_in = int((oldest + timedelta(hours=24) - now).total_seconds())
        logger.warning("Guest rate limit hit: ip=%s count=%d", ip, len(history))
        raise HTTPException(
            status_code=429,
            detail=f"Free demo limit reached ({_GUEST_EXTRACT_DAILY_LIMIT}/day). Sign up for a free account to continue. Try again in {max(1, retry_in // 60)} minutes.",
            headers={"Retry-After": str(max(60, retry_in))},
        )
    history.append(now)
    _GUEST_EXTRACT_LOG[ip] = history
    # Periodic cleanup to avoid unbounded memory growth
    if len(_GUEST_EXTRACT_LOG) > 10000:
        for k in list(_GUEST_EXTRACT_LOG.keys()):
            _GUEST_EXTRACT_LOG[k] = [t for t in _GUEST_EXTRACT_LOG[k] if t > cutoff]
            if not _GUEST_EXTRACT_LOG[k]:
                del _GUEST_EXTRACT_LOG[k]

# Register routers
app.include_router(billing_router)
app.include_router(v2_router)
app.include_router(platform_router)
app.include_router(advanced_router)
app.include_router(org_router)
app.include_router(moat_router)
app.include_router(market_router)
app.include_router(excel_import_router)
app.include_router(cron_router)
app.include_router(xbrl_router)
app.include_router(xbrl_filing_router)
app.include_router(sebi_pdf_router)
app.include_router(trends_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ─── Request Logging Middleware ────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    if duration > 2.0 or response.status_code >= 400:
        logger.warning(
            "%s %s → %d (%.2fs)",
            request.method, request.url.path, response.status_code, duration,
        )
    return response


def get_supabase_admin():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


@app.post("/api/extract")
async def extract_brsr(
    file: UploadFile = File(...),
    report_id: str = Form(...),
    user_id: str = Form(...),
    authorization: str = Header(...),
):
    # Verify the request comes from our Next.js backend
    expected_token = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase = get_supabase_admin()

    # ─── Backend Extraction Quota Enforcement ──────────────────
    try:
        profile = supabase.table("profiles").select("plan, credits_remaining").eq("id", user_id).single().execute()
        if profile.data:
            plan = profile.data.get("plan", "free")
            credits = profile.data.get("credits_remaining", 0)
            # Free/starter: limited credits; growth/pro/scale/enterprise: unlimited
            if plan in ("free", "starter") and credits <= 0:
                raise HTTPException(
                    status_code=403,
                    detail=f"Extraction quota exhausted on {plan} plan. Upgrade for more extractions."
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Could not check extraction quota for user %s: %s", user_id, str(e))

    try:
        # Read PDF
        content = await file.read()

        if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")

        # Extract text from PDF
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            supabase.table("reports").update({"status": "failed"}).eq(
                "id", report_id
            ).execute()
            return {"status": "failed", "error": "No text could be extracted from PDF"}

        # Dual extraction: regex + AI agent + enhanced
        regex_results = extract_with_regex(text)
        enhanced_results = extract_enhanced(text)

        # Use multi-pass agent (primary) with single-shot fallback
        try:
            ai_results = await extract_with_agent(text, settings.GROQ_API_KEY)
            agent_fields = sum(len(v) for v in ai_results.values() if isinstance(v, dict))
            print(f"Agent extraction: {agent_fields} fields")
            # If agent got very few fields, try single-shot as supplement
            if agent_fields < 10:
                print("Agent got few fields, supplementing with single-shot...")
                single_shot = await extract_with_ai(text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY)
                for section in ["section_a", "section_b", "section_c"]:
                    for k, v in single_shot.get(section, {}).items():
                        if k not in ai_results.get(section, {}):
                            ai_results.setdefault(section, {})[k] = v
        except Exception as ai_err:
            print(f"Agent extraction failed, falling back to single-shot: {ai_err}")
            try:
                ai_results = await extract_with_ai(text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY)
            except Exception:
                ai_results = {"section_a": {}, "section_b": {}, "section_c": {}}

        # Merge results: enhanced base → regex fills → AI takes precedence
        merged = {"section_a": {}, "section_b": {}, "section_c": {}}
        for section in ["section_a", "section_b", "section_c"]:
            merged[section] = {**enhanced_results.get(section, {})}
            merged[section].update(regex_results.get(section, {}))
            merged[section].update(ai_results.get(section, {}))

        # Calculate confidence scores
        confidence = calculate_confidence(regex_results, ai_results)

        # Extract company name and FY if available
        company_name = merged.get("section_a", {}).get("company_name", None)
        financial_year = merged.get("section_a", {}).get("financial_year", None)

        # Benchmark comparison against NIFTY 50 peers
        benchmark = get_benchmark_comparison(merged)
        gap_analysis = analyze_gaps_v2(merged)
        datapoints_stats = get_datapoints_stats()

        # Save full analysis to DB (skip for guest extractions)
        if report_id != "guest":
            full_extracted = {
                **merged,
                "gap_analysis": gap_analysis,
                "datapoints_stats": datapoints_stats,
                "benchmark": benchmark,
            }
            supabase.table("reports").update(
                {
                    "status": "completed",
                    "extracted_data": full_extracted,
                    "confidence_scores": confidence,
                    "company_name": company_name,
                    "financial_year": financial_year,
                }
            ).eq("id", report_id).execute()

        return {
            "status": "completed",
            "report_id": report_id,
            "extracted_data": merged,
            "confidence_scores": confidence,
            "gap_analysis": gap_analysis,
            "datapoints_stats": datapoints_stats,
            "benchmark": benchmark,
        }

    except HTTPException:
        raise
    except Exception as e:
        # Mark report as failed
        if report_id != "guest":
            supabase.table("reports").update({"status": "failed"}).eq(
                "id", report_id
            ).execute()
        return {"status": "failed", "error": str(e)}


@app.post("/api/guest-extract")
async def guest_extract_brsr(
    request: Request,
    file: UploadFile = File(...),
):
    """Public guest extraction endpoint — no auth, IP-rate-limited, 50MB max."""
    _check_guest_rate_limit(request)
    try:
        content = await file.read()

        if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")

        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            return {"status": "failed", "error": "No text could be extracted from PDF"}

        regex_results = extract_with_regex(text)
        enhanced_results = extract_enhanced(text)
        try:
            ai_results = await extract_with_agent(text, settings.GROQ_API_KEY)
            agent_fields = sum(len(v) for v in ai_results.values() if isinstance(v, dict))
            if agent_fields < 10:
                single_shot = await extract_with_ai(text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY)
                for section in ["section_a", "section_b", "section_c"]:
                    for k, v in single_shot.get(section, {}).items():
                        if k not in ai_results.get(section, {}):
                            ai_results.setdefault(section, {})[k] = v
        except Exception:
            try:
                ai_results = await extract_with_ai(text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY)
            except Exception:
                ai_results = {"section_a": {}, "section_b": {}, "section_c": {}}

        merged = {"section_a": {}, "section_b": {}, "section_c": {}}
        for section in ["section_a", "section_b", "section_c"]:
            merged[section] = {**enhanced_results.get(section, {})}
            merged[section].update(regex_results.get(section, {}))
            merged[section].update(ai_results.get(section, {}))

        confidence = calculate_confidence(regex_results, ai_results)
        benchmark = get_benchmark_comparison(merged)

        return {
            "status": "completed",
            "report_id": "guest",
            "extracted_data": merged,
            "confidence_scores": confidence,
            "gap_analysis": analyze_gaps_v2(merged),
            "datapoints_stats": get_datapoints_stats(),
            "benchmark": benchmark,
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/api/framework")
async def get_framework():
    """Return the complete SEBI BRSR framework structure."""
    return {
        "framework": BRSR_FRAMEWORK,
        "total_mandatory_fields": len(get_mandatory_fields()),
        "total_core_fields": len(get_core_fields()),
    }


@app.get("/api/datapoints")
async def get_datapoints():
    """Return the full list of BRSR data points (EFRAG IG 3 style) with stats."""
    return {
        "datapoints": BRSR_DATAPOINTS,
        "stats": get_datapoints_stats(),
    }


@app.get("/api/datapoints/esrs-mapping")
async def get_esrs_mapping():
    """Return BRSR data points that have ESRS cross-references."""
    mapped = get_esrs_mapped_datapoints()
    return {
        "total_mapped": len(mapped),
        "datapoints": mapped,
    }


@app.post("/api/gap-analysis")
async def gap_analysis(extracted_data: dict):
    """Run gap analysis on already-extracted data (uses enhanced v2 with ESRS refs)."""
    return analyze_gaps_v2(extracted_data)


@app.get("/api/benchmarks")
async def get_all_benchmarks():
    """Return all NIFTY 50 sector benchmarks with disclaimer metadata."""
    return {
        "sectors": {k: {"name": v["name"], "companies": v["companies"], "typical_disclosure_rate": v["typical_disclosure_rate"]} for k, v in SECTOR_BENCHMARKS.items()},
        "disclosure_patterns": NIFTY50_DISCLOSURE_PATTERNS,
        "metadata": BENCHMARK_METADATA,
    }


@app.get("/api/benchmarks/{sector}")
async def get_sector_benchmark(sector: str):
    """Return benchmark data for a specific sector."""
    if sector not in SECTOR_BENCHMARKS:
        raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found. Available: {list(SECTOR_BENCHMARKS.keys())}")
    return SECTOR_BENCHMARKS[sector]


class BenchmarkCompareRequest(BaseModel):
    extracted_data: dict
    sector: str | None = None


@app.post("/api/benchmarks/compare")
async def compare_with_benchmark(req: BenchmarkCompareRequest):
    """Compare extracted data against sector benchmarks."""
    return get_benchmark_comparison(req.extracted_data, req.sector)


# ─── Post-Extraction Email Notification ───────────────────────
class NotifyExtractionRequest(BaseModel):
    to_email: str
    file_name: str
    report_id: str


@app.post("/api/notify/extraction-complete")
async def notify_extraction_complete(
    req: NotifyExtractionRequest,
    authorization: str = Header(...),
):
    """Send email notification after extraction completes."""
    expected_token = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from app.email_service import send_extraction_complete

    # Get extraction stats from the report
    supabase = get_supabase_admin()
    report_data = supabase.table("reports").select("extracted_data, confidence_scores").eq("id", req.report_id).single().execute()

    datapoints_count = 0
    avg_confidence = 0
    compliance_score = 0

    if report_data.data and report_data.data.get("extracted_data"):
        extracted = report_data.data["extracted_data"]
        for section in ["section_a", "section_b", "section_c"]:
            datapoints_count += len(extracted.get(section, {}))
        # Compliance = filled / 216 total
        compliance_score = min(100, round((datapoints_count / 216) * 100))

    if report_data.data and report_data.data.get("confidence_scores"):
        scores = report_data.data["confidence_scores"]
        if isinstance(scores, dict) and scores:
            vals = [v for v in scores.values() if isinstance(v, (int, float))]
            avg_confidence = round(sum(vals) / len(vals)) if vals else 0

    await send_extraction_complete(
        to_email=req.to_email,
        file_name=req.file_name,
        report_id=req.report_id,
        datapoints_count=datapoints_count,
        avg_confidence=avg_confidence,
        compliance_score=compliance_score,
    )

    return {"status": "sent"}


class ExtractAsyncRequest(BaseModel):
    report_id: str
    user_id: str
    file_url: str  # Supabase Storage path e.g. "user_id/timestamp-filename.pdf"


@app.post("/api/extract-queue")
async def queue_extraction(req: ExtractAsyncRequest, authorization: str = Header(...)):
    """Queue an extraction job for background processing. Returns immediately."""
    expected_token = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase = get_supabase_admin()

    # Insert into extraction_jobs queue
    result = supabase.table("extraction_jobs").insert({
        "report_id": req.report_id,
        "user_id": req.user_id,
        "file_url": req.file_url,
        "status": "queued",
    }).execute()

    return {"status": "queued", "report_id": req.report_id, "job_id": result.data[0]["id"] if result.data else None}


@app.get("/api/extract-status/{report_id}")
async def get_extraction_status(report_id: str, authorization: str = Header(...)):
    """Poll extraction status for a report."""
    expected_token = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase = get_supabase_admin()
    result = supabase.table("reports").select("status, company_name, financial_year").eq("id", report_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"status": result.data["status"], "company_name": result.data.get("company_name"), "financial_year": result.data.get("financial_year")}


@app.post("/api/extract-async")
async def extract_brsr_async(
    req: ExtractAsyncRequest,
    authorization: str = Header(...),
):
    """Pull file from Supabase Storage and process. Called by frontend fire-and-forget."""
    expected_token = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase = get_supabase_admin()

    try:
        # Download file from Supabase Storage
        file_bytes = supabase.storage.from_("brsr-reports").download(req.file_url)

        if not file_bytes:
            supabase.table("reports").update({"status": "failed"}).eq(
                "id", req.report_id
            ).execute()
            return {"status": "failed", "error": "Could not download file from storage"}

        if len(file_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large")

        # Extract text from PDF (limit to first 80 pages for performance on free tier)
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= 80:
                    break
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            supabase.table("reports").update({"status": "failed"}).eq(
                "id", req.report_id
            ).execute()
            return {"status": "failed", "error": "No text could be extracted from PDF"}

        # Triple extraction: regex + enhanced + AI
        regex_results = extract_with_regex(text)
        enhanced_results = extract_enhanced(text)
        try:
            ai_results = await extract_with_ai(text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY)
        except Exception as ai_err:
            print(f"AI extraction failed (using regex only): {ai_err}")
            ai_results = {"section_a": {}, "section_b": {}, "section_c": {}}

        # Merge: enhanced base → regex fills → AI takes precedence
        merged = {"section_a": {}, "section_b": {}, "section_c": {}}
        for section in ["section_a", "section_b", "section_c"]:
            merged[section] = {**enhanced_results.get(section, {})}
            merged[section].update(regex_results.get(section, {}))
            merged[section].update(ai_results.get(section, {}))

        confidence = calculate_confidence(regex_results, ai_results)
        company_name = merged.get("section_a", {}).get("company_name", None)
        financial_year = merged.get("section_a", {}).get("financial_year", None)

        # Update report in DB
        supabase.table("reports").update(
            {
                "status": "completed",
                "extracted_data": merged,
                "confidence_scores": confidence,
                "company_name": company_name,
                "financial_year": financial_year,
            }
        ).eq("id", req.report_id).execute()

        return {"status": "completed", "report_id": req.report_id}

    except HTTPException:
        raise
    except Exception as e:
        supabase.table("reports").update({"status": "failed"}).eq(
            "id", req.report_id
        ).execute()
        return {"status": "failed", "error": str(e)}


@app.get("/health")
async def health():
    """Health check with dependency verification."""
    checks = {"api": "ok", "version": "4.0.0", "environment": settings.ENVIRONMENT}
    try:
        supabase = get_supabase_admin()
        supabase.table("reports").select("id").limit(1).execute()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"degraded: {type(e).__name__}"
        logger.error("Health check DB failure: %s", e)
    return checks


class PDFReportRequest(BaseModel):
    extracted_data: dict
    company_name: str = "Company"
    financial_year: str = "FY 2024-25"
    sector: str | None = None


@app.post("/api/report/pdf")
async def generate_pdf_report(req: PDFReportRequest):
    """Generate a branded PDF compliance report."""
    from fastapi.responses import Response
    
    gap_analysis = analyze_gaps_v2(req.extracted_data)
    benchmark = get_benchmark_comparison(req.extracted_data, req.sector)
    
    pdf_bytes = generate_compliance_pdf(
        extracted_data=req.extracted_data,
        gap_analysis=gap_analysis,
        benchmark=benchmark,
        company_name=req.company_name,
        financial_year=req.financial_year,
    )
    
    filename = f"BRSR_Report_{req.company_name.replace(' ', '_')}_{req.financial_year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class SEBIFilingRequest(BaseModel):
    extracted_data: dict
    company_name: str = "Company"
    financial_year: str = "FY 2024-25"
    cin: str = ""


@app.post("/api/report/sebi-filing")
async def generate_sebi_filing(req: SEBIFilingRequest, authorization: str = Header(...)):
    """Generate SEBI BRSR Annexure II format PDF — the actual stock exchange filing."""
    from fastapi.responses import Response
    from app.sebi_pdf_generator import generate_sebi_brsr_filing

    expected_token = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected_token:
        # Allow user JWTs too
        token = authorization.replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Unauthorized")

    pdf_bytes = generate_sebi_brsr_filing(
        extracted_data=req.extracted_data,
        company_name=req.company_name,
        financial_year=req.financial_year,
        cin=req.cin,
    )

    filename = f"BRSR_Filing_{req.company_name.replace(' ', '_')}_{req.financial_year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
