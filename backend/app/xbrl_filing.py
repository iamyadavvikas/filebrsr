"""
XBRL XML Instance Document Generator for SEBI BRSR Filing.

Generates a proper XBRL instance document (.xml) that can be uploaded to:
- NEAPS (NSE Electronic Application Processing System)
- BSE Listing Centre

Follows the SEBI BRSR taxonomy published by XBRL India.

Usage:
    POST /api/v2/export/xbrl-xml
    → Returns .xml file ready for exchange upload
"""

import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import Response

from app.config import get_settings
from app.brsr_datapoints import BRSR_DATAPOINTS

router = APIRouter(prefix="/api/v2/filing", tags=["XBRL Filing"])
settings = get_settings()

# XBRL namespaces for BRSR taxonomy
NAMESPACES = {
    "xbrli": "http://www.xbrl.org/2003/instance",
    "link": "http://www.xbrl.org/2003/linkbase",
    "xlink": "http://www.w3.org/1999/xlink",
    "iso4217": "http://www.xbrl.org/2003/iso4217",
    "brsr": "http://www.sebi.gov.in/xbrl/brsr/2024",
    "in-brsr": "http://www.xbrl.org/india/brsr/2024",
    "xbrldi": "http://xbrl.org/2006/xbrldi",
    "xbrlt": "http://www.xbrl.org/2003/taxonomy",
}

# Map data_type to XBRL measure/unit
UNIT_MAP = {
    "monetary": ("iso4217", "INR"),
    "percent": ("xbrli", "pure"),
    "integer": None,  # no unit for count
    "mass": ("brsr", "MT"),
    "energy": ("brsr", "GJ"),
    "volume": ("brsr", "KL"),
    "area": ("brsr", "sqm"),
    "intensity": ("xbrli", "pure"),
    "decimal": None,
}


def get_supabase_admin():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    jwt_secret = settings.SUPABASE_JWT_SECRET
    import jwt as pyjwt
    if jwt_secret:
        try:
            payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
            return payload.get("sub", "")
        except pyjwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub", token)


def build_xbrl_xml(
    entries: list[dict],
    entity_name: str,
    entity_cin: str,
    financial_year: str,
) -> bytes:
    """
    Build a complete XBRL XML instance document from BRSR data entries.
    
    Returns XML bytes ready for NEAPS/BSE upload.
    """
    # Parse financial year
    fy_start_year = int(financial_year.replace("FY", "").split("-")[0])
    period_start = f"{fy_start_year}-04-01"
    period_end = f"{fy_start_year + 1}-03-31"
    instant_date = period_end  # For instant contexts

    # Register namespaces for clean output
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    # Root element
    root = ET.Element(f"{{{NAMESPACES['xbrli']}}}xbrl")
    for prefix, uri in NAMESPACES.items():
        root.set(f"xmlns:{prefix}", uri)

    # Schema reference
    schema_ref = ET.SubElement(root, f"{{{NAMESPACES['link']}}}schemaRef")
    schema_ref.set(f"{{{NAMESPACES['xlink']}}}type", "simple")
    schema_ref.set(f"{{{NAMESPACES['xlink']}}}href", "http://www.sebi.gov.in/xbrl/brsr/2024/brsr-2024.xsd")

    # === CONTEXTS ===
    
    # Duration context (for the full financial year)
    ctx_duration = ET.SubElement(root, f"{{{NAMESPACES['xbrli']}}}context")
    ctx_duration.set("id", "Duration_CurrentYear")
    entity_el = ET.SubElement(ctx_duration, f"{{{NAMESPACES['xbrli']}}}entity")
    identifier = ET.SubElement(entity_el, f"{{{NAMESPACES['xbrli']}}}identifier")
    identifier.set("scheme", "http://www.mca.gov.in/CIN")
    identifier.text = entity_cin
    period_el = ET.SubElement(ctx_duration, f"{{{NAMESPACES['xbrli']}}}period")
    start_el = ET.SubElement(period_el, f"{{{NAMESPACES['xbrli']}}}startDate")
    start_el.text = period_start
    end_el = ET.SubElement(period_el, f"{{{NAMESPACES['xbrli']}}}endDate")
    end_el.text = period_end

    # Instant context (for point-in-time values like CIN, address)
    ctx_instant = ET.SubElement(root, f"{{{NAMESPACES['xbrli']}}}context")
    ctx_instant.set("id", "Instant_CurrentYear")
    entity_el2 = ET.SubElement(ctx_instant, f"{{{NAMESPACES['xbrli']}}}entity")
    identifier2 = ET.SubElement(entity_el2, f"{{{NAMESPACES['xbrli']}}}identifier")
    identifier2.set("scheme", "http://www.mca.gov.in/CIN")
    identifier2.text = entity_cin
    period_el2 = ET.SubElement(ctx_instant, f"{{{NAMESPACES['xbrli']}}}period")
    instant_el = ET.SubElement(period_el2, f"{{{NAMESPACES['xbrli']}}}instant")
    instant_el.text = instant_date

    # === UNITS ===
    
    # INR unit
    unit_inr = ET.SubElement(root, f"{{{NAMESPACES['xbrli']}}}unit")
    unit_inr.set("id", "INR")
    measure_inr = ET.SubElement(unit_inr, f"{{{NAMESPACES['xbrli']}}}measure")
    measure_inr.text = "iso4217:INR"

    # Pure unit (for percentages, ratios)
    unit_pure = ET.SubElement(root, f"{{{NAMESPACES['xbrli']}}}unit")
    unit_pure.set("id", "pure")
    measure_pure = ET.SubElement(unit_pure, f"{{{NAMESPACES['xbrli']}}}measure")
    measure_pure.text = "xbrli:pure"

    # Number unit (for counts)
    unit_number = ET.SubElement(root, f"{{{NAMESPACES['xbrli']}}}unit")
    unit_number.set("id", "number")
    measure_number = ET.SubElement(unit_number, f"{{{NAMESPACES['xbrli']}}}measure")
    measure_number.text = "xbrli:pure"

    # Mass unit (MT)
    unit_mt = ET.SubElement(root, f"{{{NAMESPACES['xbrli']}}}unit")
    unit_mt.set("id", "MT")
    measure_mt = ET.SubElement(unit_mt, f"{{{NAMESPACES['xbrli']}}}measure")
    measure_mt.text = "brsr:metricTonne"

    # Energy unit (GJ)
    unit_gj = ET.SubElement(root, f"{{{NAMESPACES['xbrli']}}}unit")
    unit_gj.set("id", "GJ")
    measure_gj = ET.SubElement(unit_gj, f"{{{NAMESPACES['xbrli']}}}measure")
    measure_gj.text = "brsr:gigajoule"

    # === FACTS ===
    
    # Build datapoint lookup
    dp_lookup = {dp["id"]: dp for dp in BRSR_DATAPOINTS}

    # Determine which datapoints use instant vs duration context
    INSTANT_SECTIONS = {"details_of_entity", "products_services"}

    for entry in entries:
        dp_id = entry["datapoint_id"]
        value = entry.get("value", "")
        if not value:
            continue

        dp_meta = dp_lookup.get(dp_id)
        if not dp_meta:
            continue

        data_type = dp_meta.get("data_type", "narrative")
        subsection = dp_meta.get("subsection", "")

        # Determine context
        context_ref = "Instant_CurrentYear" if subsection in INSTANT_SECTIONS else "Duration_CurrentYear"

        # Build XBRL concept name: brsr:A_I_1 format
        concept_name = f"in-brsr:{dp_id.replace('.', '_')}"

        # Create fact element
        fact_el = ET.SubElement(root, concept_name)
        fact_el.set("contextRef", context_ref)

        # Add unit and decimals for numeric types
        if data_type == "monetary":
            fact_el.set("unitRef", "INR")
            fact_el.set("decimals", "0")
        elif data_type == "percent":
            fact_el.set("unitRef", "pure")
            fact_el.set("decimals", "2")
        elif data_type in ("integer", "decimal"):
            fact_el.set("unitRef", "number")
            fact_el.set("decimals", "0" if data_type == "integer" else "2")
        elif data_type == "mass":
            fact_el.set("unitRef", "MT")
            fact_el.set("decimals", "2")
        elif data_type == "energy":
            fact_el.set("unitRef", "GJ")
            fact_el.set("decimals", "2")

        fact_el.text = str(value)

    # Serialize to XML
    tree = ET.ElementTree(root)
    buffer = BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


@router.post("/xbrl-xml")
async def export_xbrl_xml(
    financial_year: str = "FY2025-26",
    company_name: Optional[str] = None,
    cin: Optional[str] = None,
    authorization: str = Header(...),
):
    """
    Generate XBRL XML instance document for BSE/NSE filing.
    
    Returns a downloadable .xml file that can be directly uploaded to:
    - NEAPS (NSE Electronic Application Processing System)
    - BSE Listing Centre
    
    The file follows the SEBI BRSR taxonomy (2024) with proper:
    - Contexts (duration for FY, instant for point-in-time)
    - Units (INR, percentages, mass, energy)
    - Facts (mapped to in-brsr: namespace concepts)
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    # Fetch all data entries for this user + FY
    entries_result = sb.table("brsr_entries").select(
        "datapoint_id, value"
    ).eq("user_id", user_id).eq("financial_year", financial_year).execute()

    if not entries_result.data:
        raise HTTPException(
            status_code=404,
            detail="No data entries found. Complete the Data Entry section first."
        )

    # Get entity details
    profile = sb.table("profiles").select(
        "company_name, cin"
    ).eq("id", user_id).single().execute()

    entity_name = company_name or (profile.data or {}).get("company_name", "Unknown")
    entity_cin = cin or (profile.data or {}).get("cin", "L00000MH2020PLC000000")

    # Validate completeness
    dp_lookup = {dp["id"]: dp for dp in BRSR_DATAPOINTS}
    filled_ids = {e["datapoint_id"] for e in entries_result.data}
    mandatory_ids = {dp["id"] for dp in BRSR_DATAPOINTS if dp.get("mandatory")}
    missing_mandatory = mandatory_ids - filled_ids

    # Generate XBRL XML
    xml_bytes = build_xbrl_xml(
        entries=entries_result.data,
        entity_name=entity_name,
        entity_cin=entity_cin,
        financial_year=financial_year,
    )

    # Build filename
    filename = f"BRSR_{entity_cin}_{financial_year}.xml"

    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-FileBRSR-Facts-Count": str(len(entries_result.data)),
            "X-FileBRSR-Mandatory-Missing": str(len(missing_mandatory)),
            "X-FileBRSR-Completion": f"{round((1 - len(missing_mandatory)/len(mandatory_ids)) * 100, 1)}%",
        },
    )


@router.get("/xbrl-xml/validate")
async def validate_xbrl_readiness(
    financial_year: str = "FY2025-26",
    authorization: str = Header(...),
):
    """
    Check if the data entry is complete enough to generate a valid XBRL filing.
    Returns completeness stats and lists missing mandatory fields.
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    entries_result = sb.table("brsr_entries").select(
        "datapoint_id"
    ).eq("user_id", user_id).eq("financial_year", financial_year).execute()

    filled_ids = {e["datapoint_id"] for e in (entries_result.data or [])}
    
    mandatory_dps = [dp for dp in BRSR_DATAPOINTS if dp.get("mandatory")]
    core_dps = [dp for dp in BRSR_DATAPOINTS if dp.get("core")]
    
    missing_mandatory = [dp for dp in mandatory_dps if dp["id"] not in filled_ids]
    missing_core = [dp for dp in core_dps if dp["id"] not in filled_ids]

    # Group missing by section
    missing_by_section = {}
    for dp in missing_mandatory:
        section = dp.get("section", "unknown")
        if section not in missing_by_section:
            missing_by_section[section] = []
        missing_by_section[section].append({
            "id": dp["id"],
            "label": dp["label"],
            "core": dp.get("core", False),
        })

    total_filled = len(filled_ids)
    total_datapoints = len(BRSR_DATAPOINTS)
    mandatory_filled = len(mandatory_dps) - len(missing_mandatory)

    return {
        "ready_for_filing": len(missing_mandatory) == 0,
        "completion": {
            "total_filled": total_filled,
            "total_datapoints": total_datapoints,
            "percent": round(total_filled / total_datapoints * 100, 1),
            "mandatory_filled": mandatory_filled,
            "mandatory_total": len(mandatory_dps),
            "mandatory_percent": round(mandatory_filled / len(mandatory_dps) * 100, 1),
            "core_filled": len(core_dps) - len(missing_core),
            "core_total": len(core_dps),
        },
        "missing_mandatory_count": len(missing_mandatory),
        "missing_core_count": len(missing_core),
        "missing_by_section": missing_by_section,
        "filing_targets": {
            "neaps_nse": "Upload .xml to NEAPS → Corporate Filing → BRSR",
            "bse_listing": "Upload .xml to BSE Listing Centre → Compliance → BRSR Annual",
        },
    }
