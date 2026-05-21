"""
FileBRSR API v2 Router — Comprehensive BRSR compliance API.

Endpoints:
- POST /api/v2/extract          — Upload PDF → structured BRSR data
- POST /api/v2/extract/batch    — Multi-PDF batch extraction
- POST /api/v2/validate         — Validate extracted data
- POST /api/v2/score            — CDP-style compliance score
- POST /api/v2/gap-analysis     — Gap analysis with cross-framework context

- GET  /api/v2/datapoints                  — Full taxonomy
- GET  /api/v2/datapoints/{section}        — Filter by section
- GET  /api/v2/datapoints/principle/{p}    — Filter by principle

- GET  /api/v2/mapping              — Cross-framework mapping stats
- GET  /api/v2/mapping/esrs         — BRSR ↔ ESRS
- GET  /api/v2/mapping/gri          — BRSR ↔ GRI
- GET  /api/v2/mapping/tcfd         — BRSR ↔ TCFD
- GET  /api/v2/mapping/issb         — BRSR ↔ ISSB
- POST /api/v2/mapping/coverage     — Framework coverage for extracted data

- POST /api/v2/generate/brsr-template   — Generate BRSR Excel
- POST /api/v2/generate/brsr-core       — Generate BRSR Core subset

- GET  /api/v2/sectors                  — Available sectors
- GET  /api/v2/sectors/{id}/benchmarks  — Sector benchmarks
- POST /api/v2/benchmarks/compare       — Compare against sector

- POST /api/v2/yoy-compare             — Year-over-year comparison
"""

import io
from typing import Optional

import pdfplumber
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.extraction import extract_with_regex, calculate_confidence
from app.extraction_enhanced import extract_enhanced
from app.ai_extraction import extract_with_ai
from app.brsr_datapoints import BRSR_DATAPOINTS, get_datapoints_stats, analyze_gaps_v2
from app.cross_framework_mapping import (
    get_all_mappings,
    get_mapping_by_framework,
    get_mapping_by_principle,
    get_mapping_by_section,
    get_framework_coverage_stats,
    generate_cross_framework_report,
)
from app.validation_engine import validate_brsr_data, validate_year_over_year
from app.scoring import calculate_brsr_score
from app.template_generator import generate_brsr_excel, generate_brsr_core_excel
from app.nifty50_benchmarks import SECTOR_BENCHMARKS, get_benchmark_comparison
from app.api_keys import validate_api_key, check_feature_access

router = APIRouter(prefix="/api/v2", tags=["v2"])
settings = get_settings()


# ═══════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════


class ExtractedDataRequest(BaseModel):
    extracted_data: dict


class BenchmarkCompareRequest(BaseModel):
    extracted_data: dict
    sector: Optional[str] = None


class YoYCompareRequest(BaseModel):
    current_data: dict
    previous_data: dict
    threshold_pct: float = 50.0


class GenerateTemplateRequest(BaseModel):
    extracted_data: dict
    company_name: str = "Company"


# ═══════════════════════════════════════════════════════════════════════
# EXTRACTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════


@router.post("/extract")
async def extract_v2(
    file: UploadFile = File(...),
    api_key_data: dict = Depends(validate_api_key),
):
    """
    Extract BRSR data from an uploaded PDF.
    Returns structured data + validation + score + gap analysis + framework coverage.
    """
    await check_feature_access(api_key_data, "extract")

    max_size = api_key_data["limits"]["max_file_size_mb"]
    content = await file.read()

    if len(content) > max_size * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {max_size}MB")

    text = ""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from PDF")

    # Triple extraction pipeline
    regex_results = extract_with_regex(text)
    enhanced_results = extract_enhanced(text)
    try:
        ai_results = await extract_with_ai(text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY)
    except Exception:
        ai_results = {"section_a": {}, "section_b": {}, "section_c": {}}

    # Merge: enhanced → regex → AI (AI takes precedence)
    merged = {"section_a": {}, "section_b": {}, "section_c": {}}
    for section in ["section_a", "section_b", "section_c"]:
        merged[section] = {**enhanced_results.get(section, {})}
        merged[section].update(regex_results.get(section, {}))
        merged[section].update(ai_results.get(section, {}))

    confidence = calculate_confidence(regex_results, ai_results)

    # Run all analysis
    validation = validate_brsr_data(merged)
    score = calculate_brsr_score(merged)
    gap_analysis = analyze_gaps_v2(merged)
    framework_coverage = generate_cross_framework_report(merged)
    benchmark = get_benchmark_comparison(merged)

    return {
        "status": "completed",
        "extracted_data": merged,
        "confidence_scores": confidence,
        "validation": validation,
        "score": score,
        "gap_analysis": gap_analysis,
        "framework_coverage": framework_coverage,
        "benchmark": benchmark,
        "datapoints_stats": get_datapoints_stats(),
        "api_usage": {
            "tier": api_key_data["tier"],
            "usage_today": api_key_data.get("usage_today"),
        },
    }


@router.post("/extract/batch")
async def extract_batch_v2(
    files: list[UploadFile] = File(...),
    api_key_data: dict = Depends(validate_api_key),
):
    """
    Batch extraction from multiple PDFs (e.g., subsidiaries).
    Enterprise tier only.
    """
    await check_feature_access(api_key_data, "batch")

    batch_limit = api_key_data["limits"]["batch_limit"]
    if len(files) > batch_limit:
        raise HTTPException(
            status_code=400,
            detail=f"Batch limit exceeded. {api_key_data['tier']} tier allows {batch_limit} files.",
        )

    results = []
    for file in files:
        content = await file.read()
        text = ""
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception:
            results.append({"filename": file.filename, "status": "failed", "error": "Invalid PDF"})
            continue

        if not text.strip():
            results.append({"filename": file.filename, "status": "failed", "error": "No text extracted"})
            continue

        regex_results = extract_with_regex(text)
        enhanced_results = extract_enhanced(text)
        try:
            ai_results = await extract_with_ai(text, settings.GEMINI_API_KEY, settings.GROQ_API_KEY, settings.ANTHROPIC_API_KEY)
        except Exception:
            ai_results = {"section_a": {}, "section_b": {}, "section_c": {}}

        merged = {"section_a": {}, "section_b": {}, "section_c": {}}
        for section in ["section_a", "section_b", "section_c"]:
            merged[section] = {**enhanced_results.get(section, {})}
            merged[section].update(regex_results.get(section, {}))
            merged[section].update(ai_results.get(section, {}))

        score = calculate_brsr_score(merged)

        results.append({
            "filename": file.filename,
            "status": "completed",
            "extracted_data": merged,
            "score": score,
        })

    return {
        "total_files": len(files),
        "successful": len([r for r in results if r["status"] == "completed"]),
        "failed": len([r for r in results if r["status"] == "failed"]),
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════════
# VALIDATION & SCORING
# ═══════════════════════════════════════════════════════════════════════


@router.post("/validate")
async def validate_v2(
    req: ExtractedDataRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """Validate extracted BRSR data against all rules."""
    await check_feature_access(api_key_data, "validate")
    return validate_brsr_data(req.extracted_data)


@router.post("/score")
async def score_v2(
    req: ExtractedDataRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """Calculate CDP-style BRSR compliance score (0-100, A-F rating)."""
    await check_feature_access(api_key_data, "score")
    return calculate_brsr_score(req.extracted_data)


@router.post("/gap-analysis")
async def gap_analysis_v2(
    req: ExtractedDataRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """Run comprehensive gap analysis with cross-framework context."""
    await check_feature_access(api_key_data, "gap_analysis")

    gaps = analyze_gaps_v2(req.extracted_data)
    validation = validate_brsr_data(req.extracted_data)
    framework_coverage = generate_cross_framework_report(req.extracted_data)

    return {
        "gap_analysis": gaps,
        "validation_issues": validation["issues"],
        "assurance_readiness": validation["assurance_readiness"],
        "framework_gaps": framework_coverage["summary"],
    }


# ═══════════════════════════════════════════════════════════════════════
# DATAPOINTS & TAXONOMY
# ═══════════════════════════════════════════════════════════════════════


@router.get("/datapoints")
async def get_all_datapoints():
    """Return the complete BRSR taxonomy (400+ data points with types and cross-refs)."""
    return {
        "datapoints": BRSR_DATAPOINTS,
        "stats": get_datapoints_stats(),
    }


@router.get("/datapoints/{section}")
async def get_datapoints_by_section(section: str):
    """Filter data points by section (section_a, section_b, section_c)."""
    valid = ["section_a", "section_b", "section_c"]
    if section not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid section. Use: {valid}")
    filtered = [dp for dp in BRSR_DATAPOINTS if dp.get("section") == section]
    return {"section": section, "count": len(filtered), "datapoints": filtered}


@router.get("/datapoints/principle/{principle}")
async def get_datapoints_by_principle(principle: str):
    """Filter data points by principle (P1 through P9)."""
    valid = [f"P{i}" for i in range(1, 10)]
    p = principle.upper()
    if p not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid principle. Use: {valid}")
    # Match principle in section_c
    filtered = [dp for dp in BRSR_DATAPOINTS if p.lower() in dp.get("subsection", "").lower() or f"principle_{p[1]}" in dp.get("subsection", "")]
    # Fallback: match by subsection naming conventions
    if not filtered:
        principle_num = p[1]
        filtered = [dp for dp in BRSR_DATAPOINTS if dp.get("section") == "section_c" and f"p{principle_num}" in dp.get("id", "").lower()]
    return {"principle": p, "count": len(filtered), "datapoints": filtered}


# ═══════════════════════════════════════════════════════════════════════
# CROSS-FRAMEWORK MAPPING
# ═══════════════════════════════════════════════════════════════════════


@router.get("/mapping")
async def get_mapping_overview():
    """Get cross-framework mapping statistics and metadata."""
    return get_framework_coverage_stats()


@router.get("/mapping/esrs")
async def get_esrs_mapping():
    """Get BRSR ↔ ESRS (EU CSRD) mapping."""
    mappings = get_mapping_by_framework("esrs")
    return {"framework": "ESRS", "count": len(mappings), "mappings": mappings}


@router.get("/mapping/gri")
async def get_gri_mapping():
    """Get BRSR ↔ GRI mapping."""
    mappings = get_mapping_by_framework("gri")
    return {"framework": "GRI", "count": len(mappings), "mappings": mappings}


@router.get("/mapping/tcfd")
async def get_tcfd_mapping():
    """Get BRSR ↔ TCFD mapping."""
    mappings = get_mapping_by_framework("tcfd")
    return {"framework": "TCFD", "count": len(mappings), "mappings": mappings}


@router.get("/mapping/issb")
async def get_issb_mapping():
    """Get BRSR ↔ ISSB (IFRS S1/S2) mapping."""
    mappings = get_mapping_by_framework("issb")
    return {"framework": "ISSB", "count": len(mappings), "mappings": mappings}


@router.post("/mapping/coverage")
async def get_framework_coverage(
    req: ExtractedDataRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """Check how well your extracted data covers each international framework."""
    await check_feature_access(api_key_data, "mapping")
    return generate_cross_framework_report(req.extracted_data)


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATE GENERATION
# ═══════════════════════════════════════════════════════════════════════


@router.post("/generate/brsr-template")
async def generate_template(
    req: GenerateTemplateRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """Generate a SEBI BRSR format Excel workbook from extracted data."""
    await check_feature_access(api_key_data, "template")

    try:
        excel_bytes = generate_brsr_excel(req.extracted_data, req.company_name)
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))

    filename = f"BRSR_{req.company_name.replace(' ', '_')}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/generate/brsr-core")
async def generate_core_template(
    req: ExtractedDataRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """Generate BRSR Core assurance-ready Excel (subset for auditors)."""
    await check_feature_access(api_key_data, "template")

    try:
        excel_bytes = generate_brsr_core_excel(req.extracted_data)
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))

    company = req.extracted_data.get("section_a", {}).get("company_name", "Company")
    filename = f"BRSR_Core_{company.replace(' ', '_')}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ═══════════════════════════════════════════════════════════════════════
# BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════


@router.get("/sectors")
async def list_sectors():
    """List all available sectors with metadata."""
    return {
        "sectors": [
            {
                "id": k,
                "name": v["name"],
                "companies": v["companies"],
                "typical_disclosure_rate": v["typical_disclosure_rate"],
            }
            for k, v in SECTOR_BENCHMARKS.items()
        ]
    }


@router.get("/sectors/{sector_id}/benchmarks")
async def get_sector_benchmarks(sector_id: str):
    """Get detailed benchmark data for a sector."""
    if sector_id not in SECTOR_BENCHMARKS:
        raise HTTPException(
            status_code=404,
            detail=f"Sector '{sector_id}' not found. Available: {list(SECTOR_BENCHMARKS.keys())}",
        )
    return SECTOR_BENCHMARKS[sector_id]


@router.post("/benchmarks/compare")
async def compare_benchmarks(
    req: BenchmarkCompareRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """Compare extracted data against sector/Nifty50 benchmarks."""
    await check_feature_access(api_key_data, "benchmark")
    return get_benchmark_comparison(req.extracted_data, req.sector)


# ═══════════════════════════════════════════════════════════════════════
# YEAR-OVER-YEAR COMPARISON
# ═══════════════════════════════════════════════════════════════════════


@router.post("/yoy-compare")
async def year_over_year_compare(
    req: YoYCompareRequest,
    api_key_data: dict = Depends(validate_api_key),
):
    """
    Compare current year vs previous year extracted data.
    Flags large deviations (CDP-style consistency check).
    """
    await check_feature_access(api_key_data, "yoy_compare")
    flags = validate_year_over_year(req.current_data, req.previous_data, req.threshold_pct)
    return {
        "total_flags": len(flags),
        "high_severity": len([f for f in flags if f["severity"] == "high"]),
        "medium_severity": len([f for f in flags if f["severity"] == "medium"]),
        "flags": flags,
    }
