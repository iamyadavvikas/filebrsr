"""
XBRL-JSON Export — Generate inline XBRL (iXBRL) / XBRL-JSON for BRSR filings.

Follows the XBRL-JSON specification (OIM - Open Information Model) and maps
BRSR datapoints to the Indian XBRL taxonomy.

Reference: https://specifications.xbrl.org/spec-group-index-open-information-model.html
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.brsr_datapoints import BRSR_DATAPOINTS

router = APIRouter(prefix="/api/v2", tags=["XBRL Export"])
settings = get_settings()

# BRSR XBRL taxonomy namespace (SEBI India)
TAXONOMY_NS = "http://www.sebi.gov.in/xbrl/brsr/2024"
ENTITY_SCHEME = "http://www.mca.gov.in/CIN"

# Map BRSR data types to XBRL types
XBRL_TYPE_MAP = {
    "narrative": "xbrli:stringItemType",
    "boolean": "xbrli:booleanItemType",
    "integer": "xbrli:integerItemType",
    "monetary": "xbrli:monetaryItemType",
    "percent": "xbrli:pureItemType",
    "decimal": "xbrli:decimalItemType",
    "date": "xbrli:dateItemType",
    "gyear": "xbrli:gYearItemType",
    "mass": "num:massItemType",
    "energy": "num:energyItemType",
    "volume": "num:volumeItemType",
    "area": "num:areaItemType",
    "intensity": "xbrli:decimalItemType",
    "table": "xbrli:stringItemType",
    "enumeration": "enum2:enumerationItemType",
}


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


def dp_to_xbrl_concept(dp_id: str) -> str:
    """Convert BRSR datapoint ID to XBRL concept name."""
    # A.I.1 → brsr:SectionA_EntityDetails_CIN
    return f"brsr:{dp_id.replace('.', '_')}"


@router.post("/export/xbrl-json")
async def export_xbrl_json(
    financial_year: str = "FY2024-25",
    company_name: Optional[str] = None,
    cin: Optional[str] = None,
    authorization: str = Header(...),
):
    """
    Generate XBRL-JSON (OIM format) for a user's BRSR filing data.

    Returns a complete xBRL-JSON report package with:
    - documentInfo (taxonomy refs, namespaces)
    - facts (all reported datapoints as XBRL facts)
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Get user's data entries
    entries = sb.table("brsr_entries").select(
        "datapoint_id, value, updated_at"
    ).eq("user_id", user_id).eq("financial_year", financial_year).execute()

    if not entries.data:
        raise HTTPException(status_code=404, detail="No data entries found for this financial year")

    # Get profile for entity info
    profile = sb.table("profiles").select(
        "company_name, cin"
    ).eq("id", user_id).single().execute()

    entity_name = company_name or (profile.data or {}).get("company_name", "Unknown Entity")
    entity_cin = cin or (profile.data or {}).get("cin", "UNKNOWN")

    # Build datapoint lookup
    dp_lookup = {dp["id"]: dp for dp in BRSR_DATAPOINTS}

    # Determine reporting period from financial year
    # FY2024-25 → 2024-04-01 to 2025-03-31
    fy_start_year = int(financial_year.replace("FY", "").split("-")[0])
    period_start = f"{fy_start_year}-04-01"
    period_end = f"{fy_start_year + 1}-03-31"

    # Build XBRL-JSON facts
    facts = {}
    for entry in entries.data:
        dp_id = entry["datapoint_id"]
        dp_meta = dp_lookup.get(dp_id)
        if not dp_meta:
            continue

        concept = dp_to_xbrl_concept(dp_id)
        data_type = dp_meta.get("data_type", "narrative")

        # Build fact
        fact_id = f"f-{dp_id.replace('.', '-').lower()}"
        fact = {
            "value": entry["value"],
            "dimensions": {
                "concept": concept,
                "entity": f"{ENTITY_SCHEME}/{entity_cin}",
                "period": f"{period_start}/{period_end}",
            },
        }

        # Add type-specific attributes
        if data_type == "monetary":
            fact["dimensions"]["unit"] = "iso4217:INR"
        elif data_type in ("mass", "energy", "volume"):
            fact["dimensions"]["unit"] = f"brsr:{data_type}Unit"
        elif data_type == "percent":
            fact["dimensions"]["unit"] = "xbrli:pure"

        # Add section/principle dimension
        if dp_meta.get("section"):
            fact["dimensions"]["brsr:section"] = dp_meta["section"]
        if dp_meta.get("subsection"):
            fact["dimensions"]["brsr:subsection"] = dp_meta["subsection"]

        facts[fact_id] = fact

    # Build complete XBRL-JSON document
    xbrl_json = {
        "documentInfo": {
            "documentType": "https://xbrl.org/2021/xbrl-json",
            "features": {},
            "namespaces": {
                "brsr": TAXONOMY_NS,
                "xbrli": "http://www.xbrl.org/2003/instance",
                "iso4217": "http://www.xbrl.org/2003/iso4217",
                "enum2": "http://xbrl.org/2020/extensible-enumerations-2.0",
            },
            "taxonomy": [
                f"{TAXONOMY_NS}/brsr-2024.xsd",
            ],
            "baseURL": "https://filebrsr.com/xbrl/",
        },
        "facts": facts,
        "metadata": {
            "entity": {
                "name": entity_name,
                "cin": entity_cin,
                "scheme": ENTITY_SCHEME,
            },
            "reportingPeriod": {
                "financialYear": financial_year,
                "startDate": period_start,
                "endDate": period_end,
            },
            "generator": {
                "name": "FileBRSR Platform",
                "version": "4.0.0",
                "generatedAt": date.today().isoformat(),
            },
            "statistics": {
                "totalFacts": len(facts),
                "totalDatapoints": len(BRSR_DATAPOINTS),
                "completionPercent": round(len(facts) / len(BRSR_DATAPOINTS) * 100, 1),
            },
        },
    }

    return JSONResponse(
        content=xbrl_json,
        headers={
            "Content-Disposition": f'attachment; filename="brsr_{entity_cin}_{financial_year}_xbrl.json"',
        },
    )


@router.get("/export/xbrl-taxonomy")
async def get_xbrl_taxonomy():
    """
    Return the BRSR XBRL taxonomy structure — maps datapoint IDs to XBRL concepts.
    Useful for validation and integration with XBRL processors.
    """
    taxonomy = []
    for dp in BRSR_DATAPOINTS:
        taxonomy.append({
            "concept": dp_to_xbrl_concept(dp["id"]),
            "datapointId": dp["id"],
            "label": dp["label"],
            "xbrlType": XBRL_TYPE_MAP.get(dp.get("data_type", "narrative"), "xbrli:stringItemType"),
            "mandatory": dp.get("mandatory", False),
            "core": dp.get("core", False),
            "section": dp.get("section"),
            "esrsRef": dp.get("esrs_ref"),
        })

    return {
        "namespace": TAXONOMY_NS,
        "version": "2024",
        "totalConcepts": len(taxonomy),
        "concepts": taxonomy,
    }
