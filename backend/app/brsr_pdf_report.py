"""
SEBI-Prescribed BRSR Format PDF Generator.
Generates the actual BRSR report in the official SEBI Annexure II format
that can be directly filed with BSE/NSE.
"""

import io
from datetime import datetime
from typing import List, Dict, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# SEBI colors
SEBI_BLUE = colors.HexColor("#1A237E")
SEBI_DARK = colors.HexColor("#212121")
TABLE_HEADER = colors.HexColor("#E8EAF6")
TABLE_ALT = colors.HexColor("#F5F5F5")
GREEN = colors.HexColor("#2E7D32")
RED = colors.HexColor("#C62828")

# BRSR Section Structure (SEBI Annexure II format)
BRSR_SECTIONS = {
    "section_a": {
        "title": "SECTION A: GENERAL DISCLOSURES",
        "subsections": [
            ("I", "Details of the listed entity"),
            ("II", "Products/services"),
            ("III", "Operations"),
            ("IV", "Employees"),
            ("V", "Holding, Subsidiary and Associate Companies"),
            ("VI", "CSR Details"),
            ("VII", "Transparency and Disclosures Compliances"),
        ]
    },
    "section_b": {
        "title": "SECTION B: MANAGEMENT AND PROCESS DISCLOSURES",
        "subsections": [
            ("P1", "Principle 1: Businesses should conduct and govern themselves with integrity"),
            ("P2", "Principle 2: Businesses should provide goods and services in a sustainable manner"),
            ("P3", "Principle 3: Businesses should respect and promote well-being of employees"),
            ("P4", "Principle 4: Businesses should respect interests of all stakeholders"),
            ("P5", "Principle 5: Businesses should respect and promote human rights"),
            ("P6", "Principle 6: Businesses should respect and make efforts to protect environment"),
            ("P7", "Principle 7: Businesses should engage in influencing public and regulatory policy"),
            ("P8", "Principle 8: Businesses should promote inclusive growth and equitable development"),
            ("P9", "Principle 9: Businesses should engage with and provide value to consumers"),
        ]
    },
    "section_c": {
        "title": "SECTION C: PRINCIPLE WISE PERFORMANCE DISCLOSURE",
        "subsections": [
            ("P1", "PRINCIPLE 1: Businesses should conduct with Ethics, Transparency and Accountability"),
            ("P2", "PRINCIPLE 2: Sustainable and Safe Goods/Services"),
            ("P3", "PRINCIPLE 3: Employee Well-being"),
            ("P4", "PRINCIPLE 4: Stakeholder Engagement"),
            ("P5", "PRINCIPLE 5: Human Rights"),
            ("P6", "PRINCIPLE 6: Environment"),
            ("P7", "PRINCIPLE 7: Policy Advocacy"),
            ("P8", "PRINCIPLE 8: Inclusive Growth"),
            ("P9", "PRINCIPLE 9: Consumer Value"),
        ]
    },
}


def generate_sebi_brsr_pdf(
    entries: List[Dict],
    prev_entries: List[Dict],
    company_name: str,
    cin: str,
    financial_year: str,
    report_type: str = "brsr_full",
) -> bytes:
    """Generate SEBI-format BRSR PDF report."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name="SEBITitle",
        parent=styles["Title"],
        fontSize=16,
        textColor=SEBI_BLUE,
        spaceAfter=6,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SEBISubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=SEBI_DARK,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name="SectionHead",
        parent=styles["Heading1"],
        fontSize=13,
        textColor=SEBI_BLUE,
        spaceBefore=20,
        spaceAfter=10,
        leftIndent=0,
    ))
    styles.add(ParagraphStyle(
        name="SubSectionHead",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=SEBI_DARK,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="CellText",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    ))
    styles.add(ParagraphStyle(
        name="FooterText",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#757575"),
        alignment=TA_CENTER,
    ))

    # Build entry maps
    current_map = {}
    for e in entries:
        current_map[e.get("datapoint_id", "")] = e

    prev_map = {}
    for e in prev_entries:
        prev_map[e.get("datapoint_id", "")] = e

    # Build document elements
    elements = []

    # Cover Page
    elements.append(Spacer(1, 3 * cm))
    elements.append(Paragraph(
        "BUSINESS RESPONSIBILITY &<br/>SUSTAINABILITY REPORT",
        styles["SEBITitle"]
    ))
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph(
        f"[As per SEBI Circular SEBI/HO/CFD/CMD-2/P/CIR/2021/562]",
        styles["SEBISubtitle"]
    ))
    elements.append(Spacer(1, 2 * cm))

    # Company details table on cover
    cover_data = [
        ["Company Name", company_name],
        ["CIN", cin or "—"],
        ["Financial Year", financial_year],
        ["Report Type", report_type.replace("_", " ").title()],
        ["Generated On", datetime.now().strftime("%d %B %Y")],
        ["Datapoints Reported", f"{len(entries)} / 216"],
    ]
    cover_table = Table(cover_data, colWidths=[6 * cm, 10 * cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (0, -1), SEBI_BLUE),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(cover_table)

    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "This report has been prepared in accordance with the SEBI (Listing Obligations and "
        "Disclosure Requirements) Regulations, 2015 as amended, read with SEBI Circular dated "
        "May 10, 2021 on Business Responsibility and Sustainability Reporting.",
        styles["Normal"]
    ))
    elements.append(PageBreak())

    # Table of Contents
    elements.append(Paragraph("TABLE OF CONTENTS", styles["SectionHead"]))
    elements.append(Spacer(1, 0.5 * cm))
    toc_data = [
        ["Section", "Description", "Status"],
        ["A", "General Disclosures", f"{_count_section(entries, 'section_a')}/30 filled"],
        ["B", "Management and Process Disclosures", f"{_count_section(entries, 'section_b')}/58 filled"],
        ["C", "Principle Wise Performance Disclosure", f"{_count_section(entries, 'section_c')}/128 filled"],
    ]
    toc_table = Table(toc_data, colWidths=[2 * cm, 10 * cm, 4 * cm])
    toc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SEBI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ALT]),
    ]))
    elements.append(toc_table)
    elements.append(PageBreak())

    # Sections
    for section_key, section_info in BRSR_SECTIONS.items():
        elements.append(Paragraph(section_info["title"], styles["SectionHead"]))
        elements.append(HRFlowable(width="100%", color=SEBI_BLUE, thickness=1))
        elements.append(Spacer(1, 0.3 * cm))

        for sub_id, sub_title in section_info["subsections"]:
            elements.append(Paragraph(f"{sub_id}. {sub_title}", styles["SubSectionHead"]))

            # Find entries for this subsection
            section_entries = [
                e for e in entries
                if e.get("section") == section_key and
                (e.get("subsection", "").startswith(sub_id.lower()) or
                 e.get("datapoint_id", "").startswith(f"{section_key[8].upper()}.{sub_id}"))
            ]

            if section_entries:
                table_data = [["Datapoint ID", "Current Year\n" + financial_year, "Previous Year\n" + _get_prev_fy(financial_year), "Source"]]
                for entry in section_entries[:20]:  # limit per subsection
                    dp_id = entry.get("datapoint_id", "")
                    curr_val = _format_value(entry.get("value"))
                    prev_entry = prev_map.get(dp_id)
                    prev_val = _format_value(prev_entry.get("value")) if prev_entry else "—"
                    source = (entry.get("source") or "manual").replace("_", " ").title()

                    table_data.append([
                        Paragraph(dp_id, styles["CellText"]),
                        Paragraph(curr_val, styles["CellText"]),
                        Paragraph(prev_val, styles["CellText"]),
                        Paragraph(source, styles["CellText"]),
                    ])

                col_widths = [3.5 * cm, 5 * cm, 4 * cm, 3.5 * cm]
                t = Table(table_data, colWidths=col_widths, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E0E0E0")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ALT]),
                ]))
                elements.append(t)
            else:
                elements.append(Paragraph(
                    "<i>No data reported for this subsection</i>",
                    ParagraphStyle("Italic", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#9E9E9E"))
                ))

            elements.append(Spacer(1, 0.4 * cm))

        elements.append(PageBreak())

    # Summary Page
    elements.append(Paragraph("DISCLOSURE SUMMARY", styles["SectionHead"]))
    elements.append(HRFlowable(width="100%", color=SEBI_BLUE, thickness=1))
    elements.append(Spacer(1, 0.5 * cm))

    summary_data = [
        ["Metric", "Value"],
        ["Total Datapoints Reported", str(len(entries))],
        ["Mandatory Datapoints (BRSR Full)", "216"],
        ["Completion Rate", f"{round((len(entries) / 216) * 100, 1)}%"],
        ["AI-Extracted Entries", str(len([e for e in entries if e.get("source") == "ai_extracted"]))],
        ["Manually Entered", str(len([e for e in entries if e.get("source") == "manual"]))],
        ["Verified Entries", str(len([e for e in entries if e.get("verified")]))],
        ["Previous Year Comparison", f"{len(prev_entries)} datapoints in {_get_prev_fy(financial_year)}"],
    ]
    summary_table = Table(summary_data, colWidths=[8 * cm, 8 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SEBI_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDBDBD")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TABLE_ALT]),
    ]))
    elements.append(summary_table)

    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "Note: This report has been generated by FileBRSR platform. The data accuracy "
        "is the responsibility of the reporting entity. For official filing, this report "
        "should be reviewed and signed by authorized signatories before submission to BSE/NSE.",
        ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#616161"))
    ))

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()


def _count_section(entries: List[Dict], section: str) -> int:
    return len([e for e in entries if e.get("section") == section])


def _get_prev_fy(fy: str) -> str:
    try:
        clean = fy.replace(" ", "").replace("FY", "")
        parts = clean.split("-")
        start = int(parts[0])
        return f"FY{start - 1}-{str(start)[-2:]}"
    except (ValueError, IndexError):
        return "FY2023-24"


def _format_value(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, dict):
        v = value.get("value", value.get("text", ""))
        unit = value.get("unit", "")
        if v is not None:
            return f"{v} {unit}".strip()
        return str(value)
    return str(value)
