"""
Multi-Year Trend Charts API — Returns chart-ready data for 3+ year comparisons.

Used by the frontend analytics dashboard to render line charts, bar charts,
and heatmaps showing ESG performance trends over time.
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.config import get_settings
from app.brsr_datapoints import BRSR_DATAPOINTS

router = APIRouter(prefix="/api/v2/trends", tags=["Trend Charts"])
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


class TrendRequest(BaseModel):
    financial_years: List[str] = ["FY2022-23", "FY2023-24", "FY2024-25"]
    section: Optional[str] = None  # Filter to specific section (A, B, C)
    principle: Optional[str] = None  # Filter to specific principle (P1-P9)
    datapoint_ids: Optional[List[str]] = None  # Specific datapoints to chart


@router.post("/multi-year")
async def multi_year_trends(
    req: TrendRequest,
    authorization: str = Header(...),
):
    """
    Returns multi-year trend data for charting.
    Groups by section → returns completion counts and numeric value trends.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Get all entries across requested financial years
    query = sb.table("brsr_entries").select(
        "datapoint_id, value, financial_year"
    ).eq("user_id", user_id).in_("financial_year", req.financial_years)

    result = query.execute()
    entries = result.data or []

    # Build lookup for datapoint metadata
    dp_lookup = {dp["id"]: dp for dp in BRSR_DATAPOINTS}

    # Filter by section/principle if requested
    if req.section:
        entries = [e for e in entries if dp_lookup.get(e["datapoint_id"], {}).get("section") == req.section]
    if req.principle:
        entries = [e for e in entries if dp_lookup.get(e["datapoint_id"], {}).get("principle") == req.principle]
    if req.datapoint_ids:
        entries = [e for e in entries if e["datapoint_id"] in req.datapoint_ids]

    # Group by financial year
    by_year = {}
    for fy in req.financial_years:
        by_year[fy] = [e for e in entries if e["financial_year"] == fy]

    # Compute completion metrics per year
    total_datapoints = len(BRSR_DATAPOINTS)
    completion_trend = []
    for fy in req.financial_years:
        filled = len(by_year.get(fy, []))
        completion_trend.append({
            "year": fy,
            "filled": filled,
            "total": total_datapoints,
            "percent": round(filled / total_datapoints * 100, 1) if total_datapoints else 0,
        })

    # Compute section-wise breakdown per year
    sections = ["A", "B", "C"]
    section_trend = []
    for section in sections:
        section_dps = [dp["id"] for dp in BRSR_DATAPOINTS if dp.get("section") == section]
        series = []
        for fy in req.financial_years:
            filled = len([e for e in by_year.get(fy, []) if e["datapoint_id"] in section_dps])
            series.append({
                "year": fy,
                "filled": filled,
                "total": len(section_dps),
                "percent": round(filled / len(section_dps) * 100, 1) if section_dps else 0,
            })
        section_trend.append({"section": section, "data": series})

    # Numeric value trends (for specific KPI datapoints that are numeric)
    numeric_kpis = _extract_numeric_trends(entries, dp_lookup, req.financial_years)

    return {
        "financialYears": req.financial_years,
        "overallCompletion": completion_trend,
        "sectionBreakdown": section_trend,
        "numericKPIs": numeric_kpis,
        "metadata": {
            "totalDatapoints": total_datapoints,
            "yearsCompared": len(req.financial_years),
        },
    }


@router.get("/kpi-sparklines")
async def kpi_sparklines(
    authorization: str = Header(...),
    financial_years: str = "FY2022-23,FY2023-24,FY2024-25",
):
    """
    Returns sparkline-ready data for key ESG KPIs across multiple years.
    Used for dashboard widgets.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()
    fys = [fy.strip() for fy in financial_years.split(",")]

    # Key KPI datapoints that are typically numeric
    key_kpis = [
        "C.VII.1",   # Energy consumption
        "C.VII.2",   # Renewable energy %
        "C.VII.5",   # GHG emissions Scope 1
        "C.VII.6",   # GHG emissions Scope 2
        "C.VII.9",   # Water consumption
        "C.VII.15",  # Waste generated
        "C.V.1",     # Median salary ratio
        "C.III.1",   # Employee turnover
    ]

    result = sb.table("brsr_entries").select(
        "datapoint_id, value, financial_year"
    ).eq("user_id", user_id).in_("financial_year", fys).in_("datapoint_id", key_kpis).execute()

    dp_lookup = {dp["id"]: dp for dp in BRSR_DATAPOINTS}
    sparklines = []

    for kpi_id in key_kpis:
        dp = dp_lookup.get(kpi_id)
        if not dp:
            continue
        values = []
        for fy in fys:
            entry = next((e for e in (result.data or []) if e["datapoint_id"] == kpi_id and e["financial_year"] == fy), None)
            val = _try_parse_number(entry["value"]) if entry else None
            values.append({"year": fy, "value": val})

        sparklines.append({
            "datapointId": kpi_id,
            "label": dp["label"],
            "section": dp.get("section"),
            "unit": dp.get("unit", ""),
            "data": values,
        })

    return {"sparklines": sparklines, "financialYears": fys}


@router.get("/daily-metrics")
async def get_daily_metrics(
    days: int = 30,
    authorization: str = Header(...),
):
    """
    Returns daily_metrics for the admin chart (platform analytics).
    """
    from datetime import date, timedelta
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    start_date = (date.today() - timedelta(days=days)).isoformat()
    result = sb.table("daily_metrics").select("*").gte("date", start_date).order("date").execute()

    return {"days": days, "metrics": result.data or []}


# ─── Helpers ───────────────────────────────────────────────

def _try_parse_number(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = str(val).replace(",", "").replace("%", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _extract_numeric_trends(entries, dp_lookup, financial_years) -> list:
    """Find datapoints with numeric values across multiple years and return trend data."""
    # Group entries by datapoint
    by_dp = {}
    for e in entries:
        dp_id = e["datapoint_id"]
        if dp_id not in by_dp:
            by_dp[dp_id] = {}
        by_dp[dp_id][e["financial_year"]] = e["value"]

    trends = []
    for dp_id, year_values in by_dp.items():
        # Only include if has 2+ years of numeric data
        numeric_vals = {}
        for fy, val in year_values.items():
            parsed = _try_parse_number(val)
            if parsed is not None:
                numeric_vals[fy] = parsed

        if len(numeric_vals) >= 2:
            dp = dp_lookup.get(dp_id, {})
            series = [{"year": fy, "value": numeric_vals.get(fy)} for fy in financial_years]
            trends.append({
                "datapointId": dp_id,
                "label": dp.get("label", dp_id),
                "section": dp.get("section"),
                "unit": dp.get("unit", ""),
                "data": series,
            })

    # Sort by number of data points (most complete first), limit to 20
    trends.sort(key=lambda t: sum(1 for d in t["data"] if d["value"] is not None), reverse=True)
    return trends[:20]
