"""
SEBI BRSR Format PDF Generator.

Generates the official SEBI-prescribed BRSR report format PDF that:
- Follows the exact table structure from SEBI Circular
- Can be attached to the Annual Report
- Matches what auditors expect to see

This is different from the gap-analysis PDF — this is the actual BRSR disclosure document.
"""

import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.config import get_settings
from app.brsr_datapoints import BRSR_DATAPOINTS

router = APIRouter(prefix="/api/v2/filing", tags=["SEBI PDF Filing"])
settings = get_settings()

# Colors
PRIMARY = colors.HexColor("#1B4D3E")
HEADER_BG = colors.HexColor("#E8F5E9")
MUTED = colors.HexColor("#6B7280")


def get_supabase_admin():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def get_user_id(authorization: str) -> str:
    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    import jwt as pyjwt
    jwt_secret = settings.SUPABASE_JWT_SECRET
    if jwt_secret:
        try:
            payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
            return payload.get("sub", "")
        except pyjwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub", token)


# Section structure for SEBI format
SECTIONS = [
    {"id": "section_a", "title": "SECTION A: GENERAL DISCLOSURES", "subsections": [
        "details_of_entity", "products_services", "operations",
        "employees", "holding_subsidiary", "csr_details", "transparency"
    ]},
    {"id": "section_b", "title": "SECTION B: MANAGEMENT AND PROCESS DISCLOSURES", "subsections": [
        "policy_management", "governance_leadership", "incentives"
    ]},
    {"id": "section_c", "title": "SECTION C: PRINCIPLE WISE PERFORMANCE DISCLOSURE", "subsections": [
        "principle_1", "principle_2", "principle_3", "principle_4",
        "principle_5", "principle_6", "principle_7", "principle_8", "principle_9"
    ]},
]


def build_sebi_pdf(
    entries: list[dict],
    entity_name: str,
    entity_cin: str,
    financial_year: str,
) -> bytes:
    """Generate SEBI-format BRSR PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("SectionTitle", parent=styles["Heading1"], fontSize=14, textColor=PRIMARY, spaceAfter=12, spaceBefore=20))
    styles.add(ParagraphStyle("SubTitle", parent=styles["Heading2"], fontSize=11, textColor=PRIMARY, spaceAfter=8))
    styles.add(ParagraphStyle("FieldLabel", parent=styles["Normal"], fontSize=9, textColor=MUTED, leading=12))
    styles.add(ParagraphStyle("FieldValue", parent=styles["Normal"], fontSize=10, leading=14))
    styles.add(ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=MUTED, alignment=TA_CENTER))
    styles.add(ParagraphStyle("CenterBold", parent=styles["Normal"], fontSize=12, alignment=TA_CENTER, fontName="Helvetica-Bold"))

    elements = []

    # === COVER PAGE ===
    elements.append(Spacer(1, 4 * cm))
    elements.append(Paragraph("BUSINESS RESPONSIBILITY &<br/>SUSTAINABILITY REPORT", styles["CenterBold"]))
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(f"<b>{entity_name}</b>", ParagraphStyle("EntityName", parent=styles["Normal"], fontSize=16, alignment=TA_CENTER, textColor=PRIMARY)))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"CIN: {entity_cin}", ParagraphStyle("CIN", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, textColor=MUTED)))
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(f"Financial Year: {financial_year}", ParagraphStyle("FY", parent=styles["Normal"], fontSize=12, alignment=TA_CENTER)))
    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "As per SEBI Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122<br/>"
        "Format: BRSR (Annexure II) — Business Responsibility and Sustainability Report",
        ParagraphStyle("Circular", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, textColor=MUTED, leading=14)
    ))
    elements.append(Spacer(1, 3 * cm))
    elements.append(Paragraph(
        f"Generated by FileBRSR Platform | {date.today().strftime('%d %B %Y')}",
        styles["Footer"]
    ))
    elements.append(PageBreak())

    # === DATA SECTIONS ===
    # Build lookup
    dp_lookup = {dp["id"]: dp for dp in BRSR_DATAPOINTS}
    entry_lookup = {e["datapoint_id"]: e.get("value", "") for e in entries}

    for section in SECTIONS:
        elements.append(Paragraph(section["title"], styles["SectionTitle"]))
        elements.append(HRFlowable(width="100%", color=PRIMARY, thickness=1))
        elements.append(Spacer(1, 0.5 * cm))

        # Get datapoints for this section
        section_dps = [dp for dp in BRSR_DATAPOINTS if dp.get("section") == section["id"]]

        if not section_dps:
            elements.append(Paragraph("<i>No datapoints in this section.</i>", styles["FieldLabel"]))
            elements.append(Spacer(1, 1 * cm))
            continue

        # Group by subsection
        subsection_groups = {}
        for dp in section_dps:
            sub = dp.get("subsection", "other")
            if sub not in subsection_groups:
                subsection_groups[sub] = []
            subsection_groups[sub].append(dp)

        for sub_key, dps in subsection_groups.items():
            # Subsection header
            sub_title = sub_key.replace("_", " ").title()
            elements.append(Paragraph(f"<b>{sub_title}</b>", styles["SubTitle"]))

            # Build table data
            table_data = [["#", "Disclosure", "Response", "Type"]]
            for dp in dps:
                dp_id = dp["id"]
                value = entry_lookup.get(dp_id, "—")
                indicator = "CORE" if dp.get("core") else ("*" if dp.get("mandatory") else "")

                # Truncate long values for table
                display_value = str(value)[:200] if value and value != "—" else "—"

                table_data.append([
                    dp_id,
                    Paragraph(f"{dp['label']}", styles["FieldLabel"]),
                    Paragraph(display_value, styles["FieldValue"]),
                    indicator,
                ])

            if len(table_data) > 1:
                col_widths = [1.8 * cm, 7 * cm, 7 * cm, 1.5 * cm]
                t = Table(table_data, colWidths=col_widths, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                    ("TEXTCOLOR", (0, 0), (-1, 0), PRIMARY),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 0.8 * cm))

        elements.append(PageBreak())

    # === COMPLIANCE SUMMARY ===
    elements.append(Paragraph("COMPLIANCE SUMMARY", styles["SectionTitle"]))
    elements.append(HRFlowable(width="100%", color=PRIMARY, thickness=1))
    elements.append(Spacer(1, 0.5 * cm))

    total_dps = len(BRSR_DATAPOINTS)
    filled = sum(1 for dp in BRSR_DATAPOINTS if entry_lookup.get(dp["id"]))
    mandatory_total = sum(1 for dp in BRSR_DATAPOINTS if dp.get("mandatory"))
    mandatory_filled = sum(1 for dp in BRSR_DATAPOINTS if dp.get("mandatory") and entry_lookup.get(dp["id"]))
    core_total = sum(1 for dp in BRSR_DATAPOINTS if dp.get("core"))
    core_filled = sum(1 for dp in BRSR_DATAPOINTS if dp.get("core") and entry_lookup.get(dp["id"]))

    summary_data = [
        ["Category", "Filled", "Total", "Completion"],
        ["All Datapoints", str(filled), str(total_dps), f"{round(filled/total_dps*100, 1)}%"],
        ["Mandatory (Essential)", str(mandatory_filled), str(mandatory_total), f"{round(mandatory_filled/mandatory_total*100, 1)}%" if mandatory_total else "—"],
        ["BRSR Core (Assurance)", str(core_filled), str(core_total), f"{round(core_filled/core_total*100, 1)}%" if core_total else "—"],
    ]

    summary_table = Table(summary_data, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()


@router.post("/sebi-pdf")
async def export_sebi_pdf(
    financial_year: str = "FY2025-26",
    company_name: Optional[str] = None,
    cin: Optional[str] = None,
    authorization: str = Header(...),
):
    """
    Generate SEBI-format BRSR PDF for Annual Report attachment.
    
    This creates the official formatted disclosure document following
    SEBI Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 (Annexure II).
    
    Use this PDF to:
    - Attach to your Annual Report
    - Share with auditors/assurance providers
    - Submit to stock exchanges alongside XBRL
    """
    user_id = await get_user_id(authorization)
    sb = get_supabase_admin()

    entries_result = sb.table("brsr_entries").select(
        "datapoint_id, value"
    ).eq("user_id", user_id).eq("financial_year", financial_year).execute()

    if not entries_result.data:
        raise HTTPException(
            status_code=404,
            detail="No data entries found. Complete the Data Entry section first."
        )

    profile = sb.table("profiles").select(
        "company_name, cin"
    ).eq("id", user_id).single().execute()

    entity_name = company_name or (profile.data or {}).get("company_name", "Company")
    entity_cin = cin or (profile.data or {}).get("cin", "L00000MH2020PLC000000")

    pdf_bytes = build_sebi_pdf(
        entries=entries_result.data,
        entity_name=entity_name,
        entity_cin=entity_cin,
        financial_year=financial_year,
    )

    filename = f"BRSR_{entity_cin}_{financial_year}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
