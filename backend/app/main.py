from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfplumber
import io
from supabase import create_client

from app.config import get_settings
from app.extraction import extract_with_regex, calculate_confidence
from app.extraction_enhanced import extract_enhanced
from app.ai_extraction import extract_with_ai
from app.agent_extraction import extract_with_agent
from app.brsr_framework import analyze_gaps, BRSR_FRAMEWORK, get_mandatory_fields, get_core_fields
from app.brsr_datapoints import BRSR_DATAPOINTS, get_datapoints_stats, analyze_gaps_v2, get_esrs_mapped_datapoints
from app.nifty50_benchmarks import (
    SECTOR_BENCHMARKS, detect_sector, get_benchmark_comparison,
    NIFTY50_DISCLOSURE_PATTERNS
)
from app.billing import router as billing_router
from app.pdf_generator import generate_compliance_pdf
from app.router_v2 import router as v2_router
from app.router_platform import router as platform_router
from app.router_advanced import router as advanced_router
from app.router_org import router as org_router
from app.router_moat import router as moat_router
from app.router_market import router as market_router

app = FastAPI(title="FileBRSR Platform API", version="4.0.0")

settings = get_settings()

# Register routers
app.include_router(billing_router)
app.include_router(v2_router)
app.include_router(platform_router)
app.include_router(advanced_router)
app.include_router(org_router)
app.include_router(moat_router)
app.include_router(market_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


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
    file: UploadFile = File(...),
):
    """Public guest extraction endpoint — no auth, limited to 50MB."""
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
    """Return all NIFTY 50 sector benchmarks."""
    return {
        "sectors": {k: {"name": v["name"], "companies": v["companies"], "typical_disclosure_rate": v["typical_disclosure_rate"]} for k, v in SECTOR_BENCHMARKS.items()},
        "disclosure_patterns": NIFTY50_DISCLOSURE_PATTERNS,
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


class ExtractAsyncRequest(BaseModel):
    report_id: str
    user_id: str
    file_url: str  # Supabase Storage path e.g. "user_id/timestamp-filename.pdf"


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
    return {"status": "ok", "version": "2.0.0"}


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
