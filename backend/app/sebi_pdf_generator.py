"""
SEBI BRSR Filing PDF Generator — Annexure II Format.

Generates the actual BRSR report in SEBI's prescribed format (Annexure II)
that compliance officers submit to stock exchanges (BSE/NSE).

This is the "last mile" deliverable — the one document every compliance officer needs.
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.brsr_datapoints import BRSR_DATAPOINTS


# ─── SEBI Standard Styling ─────────────────────────────────────
SEBI_BLUE = colors.HexColor("#1a237e")
HEADER_BG = colors.HexColor("#e8eaf6")
BORDER_COLOR = colors.HexColor("#333333")
LIGHT_GRAY = colors.HexColor("#f5f5f5")


def _get_styles():
    """SEBI filing standard styles."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "SEBITitle", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=14,
        textColor=SEBI_BLUE, alignment=TA_CENTER, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SEBISubtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor("#424242"), alignment=TA_CENTER, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "SectionTitle", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=12,
        textColor=SEBI_BLUE, spaceBefore=14, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "SubsectionTitle", parent=styles["Heading3"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.HexColor("#1565c0"), spaceBefore=10, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "CellText", parent=styles["Normal"],
        fontName="Helvetica", fontSize=8, leading=10,
    ))
    styles.add(ParagraphStyle(
        "CellBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=8, leading=10,
    ))
    styles.add(ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontName="Helvetica", fontSize=7,
        textColor=colors.HexColor("#757575"), alignment=TA_CENTER,
    ))
    return styles


def _format_value(value, data_type: str) -> str:
    """Format a value for display in SEBI format."""
    if value is None or value == "" or value == "N/A":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, dict):
        # Table-type data: flatten key-values
        parts = []
        for k, v in value.items():
            if v is not None and v != "":
                parts.append(f"{k}: {v}")
        return "\n".join(parts) if parts else "—"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if data_type == "percent":
        try:
            return f"{float(value):.1f}%"
        except (ValueError, TypeError):
            return str(value)
    if data_type == "monetary":
        try:
            val = float(value)
            if val >= 1e7:
                return f"₹{val / 1e7:.2f} Cr"
            elif val >= 1e5:
                return f"₹{val / 1e5:.2f} L"
            return f"₹{val:,.0f}"
        except (ValueError, TypeError):
            return str(value)
    return str(value)


def _build_section_a_tables(data: dict, styles) -> list:
    """Build SECTION A: General Disclosures in SEBI format."""
    elements = []
    section_data = data.get("section_a", {})

    # I. Details of Listed Entity
    elements.append(Paragraph("I. Details of the Listed Entity", styles["SubsectionTitle"]))

    entity_fields = [
        ("Corporate Identity Number (CIN)", section_data.get("cin")),
        ("Name of the Listed Entity", section_data.get("company_name")),
        ("Year of Incorporation", section_data.get("year_of_incorporation")),
        ("Registered Office Address", section_data.get("registered_address")),
        ("Corporate Address", section_data.get("corporate_address")),
        ("E-mail", section_data.get("email")),
        ("Telephone", section_data.get("telephone")),
        ("Website", section_data.get("website")),
        ("Financial Year of Reporting", section_data.get("financial_year")),
        ("Stock Exchange(s)", section_data.get("stock_exchange")),
        ("Paid-up Capital (₹)", section_data.get("paid_up_capital")),
        ("Contact Person for BRSR", section_data.get("brsr_contact")),
        ("Reporting Boundary", section_data.get("reporting_boundary", "Standalone")),
        ("Assurance Provider", section_data.get("assurance_provider")),
        ("Type of Assurance", section_data.get("assurance_type")),
    ]

    table_data = [
        [Paragraph("<b>Sr.</b>", styles["CellBold"]),
         Paragraph("<b>Particulars</b>", styles["CellBold"]),
         Paragraph("<b>Details</b>", styles["CellBold"])]
    ]
    for i, (label, value) in enumerate(entity_fields, 1):
        table_data.append([
            Paragraph(str(i), styles["CellText"]),
            Paragraph(label, styles["CellText"]),
            Paragraph(_format_value(value, "narrative"), styles["CellText"]),
        ])

    t = Table(table_data, colWidths=[1.2 * cm, 7 * cm, 8.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5 * cm))

    # IV. Employees (key table)
    elements.append(Paragraph("IV. Employees", styles["SubsectionTitle"]))

    emp_data = [
        [Paragraph("<b>Particulars</b>", styles["CellBold"]),
         Paragraph("<b>Male</b>", styles["CellBold"]),
         Paragraph("<b>Female</b>", styles["CellBold"]),
         Paragraph("<b>Total</b>", styles["CellBold"])],
        [Paragraph("Permanent Employees", styles["CellText"]),
         Paragraph(_format_value(section_data.get("permanent_employees_male"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("permanent_employees_female"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("permanent_employees_total"), "integer"), styles["CellText"])],
        [Paragraph("Other than Permanent Employees", styles["CellText"]),
         Paragraph(_format_value(section_data.get("other_employees_male"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("other_employees_female"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("other_employees_total"), "integer"), styles["CellText"])],
        [Paragraph("Permanent Workers", styles["CellText"]),
         Paragraph(_format_value(section_data.get("permanent_workers_male"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("permanent_workers_female"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("permanent_workers_total"), "integer"), styles["CellText"])],
        [Paragraph("Other than Permanent Workers", styles["CellText"]),
         Paragraph(_format_value(section_data.get("other_workers_male"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("other_workers_female"), "integer"), styles["CellText"]),
         Paragraph(_format_value(section_data.get("other_workers_total"), "integer"), styles["CellText"])],
    ]

    t = Table(emp_data, colWidths=[7 * cm, 3.2 * cm, 3.2 * cm, 3.6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(t)

    return elements


def _build_section_b_table(data: dict, styles) -> list:
    """Build SECTION B: Management & Process Disclosures (NGRBC Principles)."""
    elements = []
    section_data = data.get("section_b", {})

    PRINCIPLES = [
        ("P1", "Ethics, Transparency & Accountability"),
        ("P2", "Sustainable & Safe Products"),
        ("P3", "Employee Well-being"),
        ("P4", "Stakeholder Responsiveness"),
        ("P5", "Human Rights"),
        ("P6", "Environment"),
        ("P7", "Public Policy Advocacy"),
        ("P8", "Inclusive Growth"),
        ("P9", "Consumer Responsibility"),
    ]

    # Policy & Governance table
    elements.append(Paragraph("Disclosure Questions", styles["SubsectionTitle"]))

    questions = [
        "Policy available (Y/N)",
        "Policy approved by Board (Y/N)",
        "Web link of Policy",
        "Translated to local languages (Y/N)",
        "Policy extends to value chain (Y/N)",
        "Committees/Director responsible",
        "Compliance with National/International standards",
        "Review frequency (Annual/Half-yearly/Quarterly)",
        "Independent assessment/evaluation (Y/N)",
    ]

    # Build header row
    header = [Paragraph("<b>Questions</b>", styles["CellBold"])]
    for code, _ in PRINCIPLES:
        header.append(Paragraph(f"<b>{code}</b>", styles["CellBold"]))

    table_data = [header]
    for q in questions:
        row = [Paragraph(q, styles["CellText"])]
        for code, _ in PRINCIPLES:
            key = f"{code.lower()}_{q.split('(')[0].strip().lower().replace(' ', '_')[:20]}"
            val = section_data.get(key, "—")
            if isinstance(val, bool):
                val = "Y" if val else "N"
            row.append(Paragraph(str(val) if val else "—", styles["CellText"]))
        table_data.append(row)

    col_widths = [4.5 * cm] + [1.3 * cm] * 9
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(t)

    return elements


def _build_section_c_tables(data: dict, styles) -> list:
    """Build SECTION C: Principle-wise Performance Disclosures."""
    elements = []
    section_data = data.get("section_c", {})

    PRINCIPLES = {
        "P1": "Ethics, Transparency & Accountability",
        "P2": "Sustainable & Safe Products/Services",
        "P3": "Employee Well-being",
        "P4": "Stakeholder Engagement",
        "P5": "Human Rights",
        "P6": "Environment",
        "P7": "Public Policy",
        "P8": "Inclusive Growth & Equitable Development",
        "P9": "Consumer Responsibility",
    }

    # Group datapoints by principle
    for principle_code, principle_name in PRINCIPLES.items():
        elements.append(Paragraph(
            f"Principle {principle_code[1]}: {principle_name}",
            styles["SubsectionTitle"]
        ))

        # Get datapoints for this principle
        principle_dps = [
            dp for dp in BRSR_DATAPOINTS
            if dp.get("section") == "section_c" and
            principle_code.lower() in dp.get("id", "").lower()
        ]

        # Also get from subsection names
        if not principle_dps:
            principle_num = principle_code[1]
            principle_dps = [
                dp for dp in BRSR_DATAPOINTS
                if dp.get("section") == "section_c" and
                f"principle_{principle_num}" in dp.get("subsection", "")
            ]

        if not principle_dps:
            elements.append(Paragraph("No specific datapoints mapped.", styles["CellText"]))
            elements.append(Spacer(1, 0.3 * cm))
            continue

        # Essential indicators
        essential = [dp for dp in principle_dps if dp.get("indicator_type") == "essential"]
        leadership = [dp for dp in principle_dps if dp.get("indicator_type") == "leadership"]

        if essential:
            elements.append(Paragraph("Essential Indicators", styles["CellBold"]))
            table_data = [[
                Paragraph("<b>Sr.</b>", styles["CellBold"]),
                Paragraph("<b>Disclosure</b>", styles["CellBold"]),
                Paragraph("<b>Response</b>", styles["CellBold"]),
                Paragraph("<b>Type</b>", styles["CellBold"]),
            ]]
            for i, dp in enumerate(essential[:15], 1):
                # Try to find the value from extracted data
                dp_id = dp["id"]
                # Look for value using various key formats
                value = (
                    section_data.get(dp_id) or
                    section_data.get(dp_id.lower()) or
                    section_data.get(dp["label"].lower().replace(" ", "_")[:30]) or
                    "—"
                )
                table_data.append([
                    Paragraph(str(i), styles["CellText"]),
                    Paragraph(dp["label"][:60], styles["CellText"]),
                    Paragraph(_format_value(value, dp["data_type"]), styles["CellText"]),
                    Paragraph("M" if dp.get("mandatory") else "V", styles["CellText"]),
                ])

            t = Table(table_data, colWidths=[1 * cm, 7 * cm, 7 * cm, 1.5 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.3 * cm))

        if leadership:
            elements.append(Paragraph("Leadership Indicators", styles["CellBold"]))
            table_data = [[
                Paragraph("<b>Sr.</b>", styles["CellBold"]),
                Paragraph("<b>Disclosure</b>", styles["CellBold"]),
                Paragraph("<b>Response</b>", styles["CellBold"]),
            ]]
            for i, dp in enumerate(leadership[:10], 1):
                dp_id = dp["id"]
                value = (
                    section_data.get(dp_id) or
                    section_data.get(dp_id.lower()) or
                    "—"
                )
                table_data.append([
                    Paragraph(str(i), styles["CellText"]),
                    Paragraph(dp["label"][:60], styles["CellText"]),
                    Paragraph(_format_value(value, dp["data_type"]), styles["CellText"]),
                ])

            t = Table(table_data, colWidths=[1 * cm, 8 * cm, 7.5 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(t)

        elements.append(Spacer(1, 0.3 * cm))

    return elements


def generate_sebi_brsr_filing(
    extracted_data: dict,
    company_name: str = "Company",
    financial_year: str = "FY 2024-25",
    cin: str = "",
) -> bytes:
    """
    Generate SEBI BRSR Annexure II format PDF — the actual filing document.

    This is what compliance officers submit to BSE/NSE.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = _get_styles()
    elements = []

    # ═══ COVER PAGE (SEBI Standard Header) ═══
    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "BUSINESS RESPONSIBILITY & SUSTAINABILITY REPORT",
        styles["SEBITitle"]
    ))
    elements.append(Paragraph(
        "(As per SEBI Circular SEBI/HO/CFD/CMD-2/P/CIR/2021/562 dated May 10, 2021<br/>"
        "read with SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 dated July 12, 2023)",
        styles["SEBISubtitle"]
    ))
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=SEBI_BLUE))
    elements.append(Spacer(1, 1 * cm))

    # Company details box
    cover_data = [
        [Paragraph("<b>Name of Listed Entity</b>", styles["CellBold"]),
         Paragraph(company_name, styles["CellText"])],
        [Paragraph("<b>CIN</b>", styles["CellBold"]),
         Paragraph(cin or extracted_data.get("section_a", {}).get("cin", "—"), styles["CellText"])],
        [Paragraph("<b>Financial Year</b>", styles["CellBold"]),
         Paragraph(financial_year, styles["CellText"])],
        [Paragraph("<b>Reporting Boundary</b>", styles["CellBold"]),
         Paragraph(extracted_data.get("section_a", {}).get("reporting_boundary", "Standalone"), styles["CellText"])],
        [Paragraph("<b>Date of Report</b>", styles["CellBold"]),
         Paragraph(datetime.now().strftime("%d %B %Y"), styles["CellText"])],
    ]
    t = Table(cover_data, colWidths=[5 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("BACKGROUND", (0, 0), (0, -1), HEADER_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "This report has been prepared in accordance with the format prescribed under "
        "Regulation 34(2)(f) of the SEBI (Listing Obligations and Disclosure Requirements) "
        "Regulations, 2015.",
        styles["CellText"]
    ))

    elements.append(PageBreak())

    # ═══ TABLE OF CONTENTS ═══
    elements.append(Paragraph("Table of Contents", styles["SectionTitle"]))
    toc_items = [
        "Section A: General Disclosures",
        "Section B: Management & Process Disclosures",
        "Section C: Principle-wise Performance Disclosures",
        "  Principle 1: Businesses should conduct and govern themselves with integrity",
        "  Principle 2: Businesses should provide goods & services in a sustainable manner",
        "  Principle 3: Businesses should respect and promote well-being of employees",
        "  Principle 4: Businesses should respect interests of all stakeholders",
        "  Principle 5: Businesses should respect and promote human rights",
        "  Principle 6: Businesses should respect and make efforts to protect the environment",
        "  Principle 7: Businesses should engage in policy advocacy responsibly",
        "  Principle 8: Businesses should promote inclusive growth and equitable development",
        "  Principle 9: Businesses should engage with consumers responsibly",
    ]
    for item in toc_items:
        elements.append(Paragraph(item, styles["CellText"]))
        elements.append(Spacer(1, 2 * mm))

    elements.append(PageBreak())

    # ═══ SECTION A ═══
    elements.append(Paragraph("SECTION A: GENERAL DISCLOSURES", styles["SectionTitle"]))
    elements.extend(_build_section_a_tables(extracted_data, styles))
    elements.append(PageBreak())

    # ═══ SECTION B ═══
    elements.append(Paragraph(
        "SECTION B: MANAGEMENT AND PROCESS DISCLOSURES",
        styles["SectionTitle"]
    ))
    elements.append(Paragraph(
        "This section is applicable to all nine NGRBC Principles. "
        "Disclosures relate to policy, governance structure, and process.",
        styles["CellText"]
    ))
    elements.append(Spacer(1, 0.3 * cm))
    elements.extend(_build_section_b_table(extracted_data, styles))
    elements.append(PageBreak())

    # ═══ SECTION C ═══
    elements.append(Paragraph(
        "SECTION C: PRINCIPLE WISE PERFORMANCE DISCLOSURE",
        styles["SectionTitle"]
    ))
    elements.append(Paragraph(
        "This section requires disclosure of performance against each of the nine NGRBC principles. "
        "Each principle has Essential Indicators (mandatory) and Leadership Indicators (voluntary).",
        styles["CellText"]
    ))
    elements.append(Spacer(1, 0.3 * cm))
    elements.extend(_build_section_c_tables(extracted_data, styles))

    # ═══ FOOTER / DECLARATION ═══
    elements.append(PageBreak())
    elements.append(Paragraph("DECLARATION", styles["SectionTitle"]))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(
        f"We hereby confirm that the disclosures made in this Business Responsibility & "
        f"Sustainability Report for {financial_year} are true and accurate to the best of our "
        f"knowledge and belief.",
        styles["CellText"]
    ))
    elements.append(Spacer(1, 1.5 * cm))

    sign_data = [
        [Paragraph("<b>For and on behalf of</b>", styles["CellBold"]),
         Paragraph(company_name, styles["CellText"])],
        [Paragraph("<b>Authorized Signatory</b>", styles["CellBold"]),
         Paragraph("_________________________", styles["CellText"])],
        [Paragraph("<b>Designation</b>", styles["CellBold"]),
         Paragraph("_________________________", styles["CellText"])],
        [Paragraph("<b>Date</b>", styles["CellBold"]),
         Paragraph(datetime.now().strftime("%d/%m/%Y"), styles["CellText"])],
        [Paragraph("<b>Place</b>", styles["CellBold"]),
         Paragraph("_________________________", styles["CellText"])],
    ]
    t = Table(sign_data, colWidths=[5 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 2 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdbdbd")))
    elements.append(Paragraph(
        f"Generated by FileBRSR (filebrsr.com) on {datetime.now().strftime('%d %B %Y')}. "
        "This document is generated based on AI extraction and should be reviewed by the "
        "compliance team before submission to the Stock Exchange.",
        styles["Footer"]
    ))

    # Build
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
