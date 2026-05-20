"""
Cross-Framework Mapping: BRSR ↔ ESRS ↔ GRI ↔ TCFD ↔ ISSB (IFRS S1/S2)

This is the first structured cross-framework taxonomy for India's BRSR.
No official XBRL taxonomy exists for BRSR; this module bridges that gap.

References:
- SEBI BRSR Annexure II (2023 updated format)
- EFRAG ESRS Set 1 (EU CSRD) — ESRS 2, E1-E5, S1-S4, G1
- GRI Universal Standards 2021 + Topic Standards
- TCFD Recommendations (now subsumed into ISSB)
- IFRS S1 (General) + S2 (Climate) — ISSB
- UN SDG mapping
"""

from typing import Optional

# ═══════════════════════════════════════════════════════════════════════
# MASTER CROSS-FRAMEWORK MAP
# Each entry maps a BRSR disclosure to equivalent disclosures in other frameworks
# ═══════════════════════════════════════════════════════════════════════

FRAMEWORK_MAPPING = [
    # ─── SECTION A: GENERAL DISCLOSURES ───────────────────────────────
    {
        "brsr_id": "A.I.1",
        "brsr_label": "Corporate Identity Number (CIN)",
        "section": "section_a",
        "principle": None,
        "esrs_ref": "ESRS 2 BP-1",
        "esrs_label": "Basis for preparation - General",
        "gri_ref": "GRI 2-1",
        "gri_label": "Organizational details",
        "tcfd_ref": None,
        "issb_ref": "IFRS S1.13",
        "issb_label": "Reporting entity",
        "sdg_ref": [],
    },
    {
        "brsr_id": "A.I.13",
        "brsr_label": "Reporting boundary (Standalone/Consolidated)",
        "section": "section_a",
        "principle": None,
        "esrs_ref": "ESRS 2 BP-1.9",
        "esrs_label": "Consolidation scope",
        "gri_ref": "GRI 2-2",
        "gri_label": "Entities included in sustainability reporting",
        "tcfd_ref": None,
        "issb_ref": "IFRS S1.20",
        "issb_label": "Reporting entity and consolidation",
        "sdg_ref": [],
    },
    {
        "brsr_id": "A.I.14",
        "brsr_label": "Assurance provider details",
        "section": "section_a",
        "principle": None,
        "esrs_ref": "ESRS 2 BP-1.11",
        "esrs_label": "Statement on assurance",
        "gri_ref": "GRI 2-5",
        "gri_label": "External assurance",
        "tcfd_ref": None,
        "issb_ref": "IFRS S1.78",
        "issb_label": "Assurance disclosures",
        "sdg_ref": [],
    },
    # ─── EMPLOYEES & WORKFORCE ────────────────────────────────────────
    {
        "brsr_id": "A.IV.1-3",
        "brsr_label": "Permanent employees (Male/Female/Total)",
        "section": "section_a",
        "principle": None,
        "esrs_ref": "ESRS S1-6.50(a)",
        "esrs_label": "Total number of employees by gender",
        "gri_ref": "GRI 2-7",
        "gri_label": "Employees",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 8.5"],
    },
    {
        "brsr_id": "A.IV.17",
        "brsr_label": "Women on Board of Directors (%)",
        "section": "section_a",
        "principle": None,
        "esrs_ref": "ESRS S1-9.66",
        "esrs_label": "Diversity metrics - governance bodies",
        "gri_ref": "GRI 405-1",
        "gri_label": "Diversity of governance bodies and employees",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 5.5"],
    },
    {
        "brsr_id": "A.IV.19-22",
        "brsr_label": "Turnover rate (Permanent employees/workers, 3yr trend)",
        "section": "section_a",
        "principle": None,
        "esrs_ref": "ESRS S1-6.53",
        "esrs_label": "Employee turnover rate by gender",
        "gri_ref": "GRI 401-1",
        "gri_label": "New employee hires and employee turnover",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 8.5"],
    },

    # ─── SECTION B: MANAGEMENT & PROCESS ──────────────────────────────
    {
        "brsr_id": "B.P1.Policy",
        "brsr_label": "Policy on Principle 1 (Ethics/Governance)",
        "section": "section_b",
        "principle": "P1",
        "esrs_ref": "ESRS G1-1",
        "esrs_label": "Business conduct policies",
        "gri_ref": "GRI 2-23",
        "gri_label": "Policy commitments",
        "tcfd_ref": "Governance (a)",
        "issb_ref": "IFRS S1.26",
        "issb_label": "Governance - processes and controls",
        "sdg_ref": ["SDG 16.5"],
    },
    {
        "brsr_id": "B.Grievance",
        "brsr_label": "Grievance redressal mechanism details",
        "section": "section_b",
        "principle": None,
        "esrs_ref": "ESRS S1-3.24",
        "esrs_label": "Remediation channels and processes",
        "gri_ref": "GRI 2-25",
        "gri_label": "Processes to remediate negative impacts",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 16.6"],
    },

    # ─── PRINCIPLE 1: ETHICS & GOVERNANCE ─────────────────────────────
    {
        "brsr_id": "C.P1.E.1",
        "brsr_label": "Anti-corruption/anti-bribery policy coverage",
        "section": "section_c",
        "principle": "P1",
        "esrs_ref": "ESRS G1-3",
        "esrs_label": "Prevention and detection of corruption/bribery",
        "gri_ref": "GRI 205-1",
        "gri_label": "Operations assessed for risks related to corruption",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 16.5"],
    },
    {
        "brsr_id": "C.P1.E.2",
        "brsr_label": "Disciplinary action on corruption/bribery",
        "section": "section_c",
        "principle": "P1",
        "esrs_ref": "ESRS G1-4",
        "esrs_label": "Confirmed incidents of corruption",
        "gri_ref": "GRI 205-3",
        "gri_label": "Confirmed incidents of corruption and actions taken",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 16.5"],
    },

    # ─── PRINCIPLE 2: PRODUCT LIFECYCLE SUSTAINABILITY ────────────────
    {
        "brsr_id": "C.P2.E.1",
        "brsr_label": "R&D and capex in specific technologies for sustainability",
        "section": "section_c",
        "principle": "P2",
        "esrs_ref": "ESRS E1-3.29",
        "esrs_label": "GHG reduction targets and capital expenditure",
        "gri_ref": "GRI 201-2",
        "gri_label": "Financial implications of climate change",
        "tcfd_ref": "Strategy (b)",
        "issb_ref": "IFRS S2.14(a)",
        "issb_label": "Climate transition plan - capital expenditure",
        "sdg_ref": ["SDG 9.4"],
    },
    {
        "brsr_id": "C.P2.E.2",
        "brsr_label": "Sustainable sourcing (% inputs from sustainable sources)",
        "section": "section_c",
        "principle": "P2",
        "esrs_ref": "ESRS E5-4",
        "esrs_label": "Resource inflows including recycled content",
        "gri_ref": "GRI 301-1",
        "gri_label": "Materials used by weight or volume",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 12.2"],
    },
    {
        "brsr_id": "C.P2.E.3",
        "brsr_label": "Recycled/reused input material (%)",
        "section": "section_c",
        "principle": "P2",
        "esrs_ref": "ESRS E5-4.36",
        "esrs_label": "Percentage of recycled input materials",
        "gri_ref": "GRI 301-2",
        "gri_label": "Recycled input materials used",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 12.5"],
    },

    # ─── PRINCIPLE 3: EMPLOYEE WELLBEING ──────────────────────────────
    {
        "brsr_id": "C.P3.E.1",
        "brsr_label": "Employee wellbeing measures (health insurance, maternity, etc.)",
        "section": "section_c",
        "principle": "P3",
        "esrs_ref": "ESRS S1-11",
        "esrs_label": "Social protection - benefits coverage",
        "gri_ref": "GRI 401-2",
        "gri_label": "Benefits provided to full-time employees",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 3.8", "SDG 8.8"],
    },
    {
        "brsr_id": "C.P3.E.2",
        "brsr_label": "Safety incidents (LTIFR / fatalities)",
        "section": "section_c",
        "principle": "P3",
        "esrs_ref": "ESRS S1-14.88(a-c)",
        "esrs_label": "Health and safety metrics - work-related injuries",
        "gri_ref": "GRI 403-9",
        "gri_label": "Work-related injuries",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 8.8"],
    },
    {
        "brsr_id": "C.P3.E.3",
        "brsr_label": "Training hours per employee/worker",
        "section": "section_c",
        "principle": "P3",
        "esrs_ref": "ESRS S1-13.83",
        "esrs_label": "Training and skills development",
        "gri_ref": "GRI 404-1",
        "gri_label": "Average hours of training per year per employee",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 4.4"],
    },
    {
        "brsr_id": "C.P3.E.4",
        "brsr_label": "Median remuneration (male vs female)",
        "section": "section_c",
        "principle": "P3",
        "esrs_ref": "ESRS S1-16.97(a)",
        "esrs_label": "Pay gap between female and male employees",
        "gri_ref": "GRI 405-2",
        "gri_label": "Ratio of basic salary by gender",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 5.1", "SDG 10.4"],
    },

    # ─── PRINCIPLE 4: STAKEHOLDER ENGAGEMENT ──────────────────────────
    {
        "brsr_id": "C.P4.E.1",
        "brsr_label": "Key stakeholder groups identified",
        "section": "section_c",
        "principle": "P4",
        "esrs_ref": "ESRS 2 SBM-2",
        "esrs_label": "Interests and views of stakeholders",
        "gri_ref": "GRI 2-29",
        "gri_label": "Approach to stakeholder engagement",
        "tcfd_ref": None,
        "issb_ref": "IFRS S1.22",
        "issb_label": "Strategy - stakeholders considered",
        "sdg_ref": ["SDG 17.17"],
    },

    # ─── PRINCIPLE 5: HUMAN RIGHTS ────────────────────────────────────
    {
        "brsr_id": "C.P5.E.1",
        "brsr_label": "Human rights training (%)",
        "section": "section_c",
        "principle": "P5",
        "esrs_ref": "ESRS S1-4.31",
        "esrs_label": "Taking action on material impacts - human rights",
        "gri_ref": "GRI 412-2",
        "gri_label": "Employee training on human rights policies",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 4.7"],
    },
    {
        "brsr_id": "C.P5.E.2",
        "brsr_label": "Child labour / forced labour complaints",
        "section": "section_c",
        "principle": "P5",
        "esrs_ref": "ESRS S1-17",
        "esrs_label": "Incidents and severe human rights impacts",
        "gri_ref": "GRI 408-1",
        "gri_label": "Operations at risk for child labor",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 8.7"],
    },
    {
        "brsr_id": "C.P5.E.3",
        "brsr_label": "Minimum wage paid (Y/N) and wage complaints",
        "section": "section_c",
        "principle": "P5",
        "esrs_ref": "ESRS S1-10",
        "esrs_label": "Adequate wages",
        "gri_ref": "GRI 202-1",
        "gri_label": "Ratios of standard entry level wage to local minimum wage",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 1.2", "SDG 10.4"],
    },

    # ─── PRINCIPLE 6: ENVIRONMENT (Largest section) ───────────────────
    {
        "brsr_id": "C.P6.E.1",
        "brsr_label": "Total energy consumption (GJ)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E1-5.37",
        "esrs_label": "Energy consumption and mix",
        "gri_ref": "GRI 302-1",
        "gri_label": "Energy consumption within the organization",
        "tcfd_ref": "Metrics & Targets (b)",
        "issb_ref": "IFRS S2.29(b)",
        "issb_label": "Climate-related metrics - energy consumption",
        "sdg_ref": ["SDG 7.2", "SDG 7.3"],
    },
    {
        "brsr_id": "C.P6.E.2",
        "brsr_label": "Energy from renewable sources (%)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E1-5.38",
        "esrs_label": "Share of renewable energy",
        "gri_ref": "GRI 302-1(e)",
        "gri_label": "Electricity from renewable sources",
        "tcfd_ref": "Metrics & Targets (b)",
        "issb_ref": "IFRS S2.29(b)",
        "issb_label": "Climate metrics - renewable share",
        "sdg_ref": ["SDG 7.2"],
    },
    {
        "brsr_id": "C.P6.E.3",
        "brsr_label": "Total Scope 1 GHG emissions (tCO2e)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E1-6.44(a)",
        "esrs_label": "Gross Scope 1 GHG emissions",
        "gri_ref": "GRI 305-1",
        "gri_label": "Direct (Scope 1) GHG emissions",
        "tcfd_ref": "Metrics & Targets (a)",
        "issb_ref": "IFRS S2.29(a)(i)",
        "issb_label": "Scope 1 greenhouse gas emissions",
        "sdg_ref": ["SDG 13.2"],
    },
    {
        "brsr_id": "C.P6.E.4",
        "brsr_label": "Total Scope 2 GHG emissions (tCO2e)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E1-6.44(b)",
        "esrs_label": "Gross Scope 2 GHG emissions",
        "gri_ref": "GRI 305-2",
        "gri_label": "Energy indirect (Scope 2) GHG emissions",
        "tcfd_ref": "Metrics & Targets (a)",
        "issb_ref": "IFRS S2.29(a)(ii)",
        "issb_label": "Scope 2 greenhouse gas emissions",
        "sdg_ref": ["SDG 13.2"],
    },
    {
        "brsr_id": "C.P6.E.5",
        "brsr_label": "GHG emission intensity (per rupee of turnover)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E1-6.53",
        "esrs_label": "GHG intensity per net revenue",
        "gri_ref": "GRI 305-4",
        "gri_label": "GHG emissions intensity",
        "tcfd_ref": "Metrics & Targets (a)",
        "issb_ref": "IFRS S2.29(a)(iv)",
        "issb_label": "GHG emissions intensity",
        "sdg_ref": ["SDG 13.2"],
    },
    {
        "brsr_id": "C.P6.E.6",
        "brsr_label": "Total water withdrawal (KL)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E3-4.28(a)",
        "esrs_label": "Total water consumption",
        "gri_ref": "GRI 303-3",
        "gri_label": "Water withdrawal",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 6.4"],
    },
    {
        "brsr_id": "C.P6.E.7",
        "brsr_label": "Water intensity (per rupee of turnover)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E3-4.29",
        "esrs_label": "Water intensity per net revenue",
        "gri_ref": "GRI 303-5(b)",
        "gri_label": "Water consumption intensity",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 6.4"],
    },
    {
        "brsr_id": "C.P6.E.8",
        "brsr_label": "Total waste generated (MT)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E5-5.37(a)",
        "esrs_label": "Total waste generated",
        "gri_ref": "GRI 306-3",
        "gri_label": "Waste generated",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 12.4", "SDG 12.5"],
    },
    {
        "brsr_id": "C.P6.E.9",
        "brsr_label": "Waste recycled/reused (%)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E5-5.40",
        "esrs_label": "Waste diverted from disposal",
        "gri_ref": "GRI 306-4",
        "gri_label": "Waste diverted from disposal",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 12.5"],
    },
    {
        "brsr_id": "C.P6.E.10",
        "brsr_label": "Air emissions (NOx, SOx, PM, etc.)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E2-4.28",
        "esrs_label": "Pollution of air - substances of concern",
        "gri_ref": "GRI 305-7",
        "gri_label": "Nitrogen oxides, sulfur oxides, and other emissions",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 3.9", "SDG 11.6"],
    },
    {
        "brsr_id": "C.P6.E.11",
        "brsr_label": "Biodiversity impact assessment (EIA conducted Y/N)",
        "section": "section_c",
        "principle": "P6",
        "esrs_ref": "ESRS E4-5",
        "esrs_label": "Impact metrics related to biodiversity",
        "gri_ref": "GRI 304-2",
        "gri_label": "Significant impacts on biodiversity",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 15.1", "SDG 15.5"],
    },

    # ─── PRINCIPLE 7: POLICY ADVOCACY ─────────────────────────────────
    {
        "brsr_id": "C.P7.E.1",
        "brsr_label": "Trade/industry association memberships",
        "section": "section_c",
        "principle": "P7",
        "esrs_ref": "ESRS G1-5",
        "esrs_label": "Political engagement and lobbying activities",
        "gri_ref": "GRI 2-28",
        "gri_label": "Membership associations",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 17.17"],
    },
    {
        "brsr_id": "C.P7.E.2",
        "brsr_label": "Anti-competitive conduct proceedings",
        "section": "section_c",
        "principle": "P7",
        "esrs_ref": "ESRS G1-4",
        "esrs_label": "Fines for anti-competitive practices",
        "gri_ref": "GRI 206-1",
        "gri_label": "Legal actions for anti-competitive behavior",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 16.3"],
    },

    # ─── PRINCIPLE 8: INCLUSIVE GROWTH (CSR) ──────────────────────────
    {
        "brsr_id": "C.P8.E.1",
        "brsr_label": "CSR spend (INR) and % of average net profit",
        "section": "section_c",
        "principle": "P8",
        "esrs_ref": "ESRS S3-4",
        "esrs_label": "Taking action on material impacts on communities",
        "gri_ref": "GRI 201-1",
        "gri_label": "Direct economic value generated and distributed",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 1.2", "SDG 2.1", "SDG 10.2"],
    },
    {
        "brsr_id": "C.P8.E.2",
        "brsr_label": "Community beneficiaries (number)",
        "section": "section_c",
        "principle": "P8",
        "esrs_ref": "ESRS S3-5",
        "esrs_label": "Affected communities engagement metrics",
        "gri_ref": "GRI 413-1",
        "gri_label": "Operations with community engagement",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 1.4", "SDG 11.1"],
    },

    # ─── PRINCIPLE 9: CONSUMER / CUSTOMER ─────────────────────────────
    {
        "brsr_id": "C.P9.E.1",
        "brsr_label": "Consumer complaints (total + resolved %)",
        "section": "section_c",
        "principle": "P9",
        "esrs_ref": "ESRS S4-3",
        "esrs_label": "Channels for affected consumers to raise concerns",
        "gri_ref": "GRI 418-1",
        "gri_label": "Substantiated complaints re: customer privacy",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 16.6"],
    },
    {
        "brsr_id": "C.P9.E.2",
        "brsr_label": "Data privacy complaints",
        "section": "section_c",
        "principle": "P9",
        "esrs_ref": "ESRS S4-4",
        "esrs_label": "Consumers - taking action on material impacts",
        "gri_ref": "GRI 418-1",
        "gri_label": "Substantiated complaints concerning customer privacy",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 16.10"],
    },
    {
        "brsr_id": "C.P9.E.3",
        "brsr_label": "Product recalls (number)",
        "section": "section_c",
        "principle": "P9",
        "esrs_ref": "ESRS S4-5",
        "esrs_label": "Material impacts on consumers - health & safety",
        "gri_ref": "GRI 416-2",
        "gri_label": "Incidents of non-compliance re: health impacts of products",
        "tcfd_ref": None,
        "issb_ref": None,
        "issb_label": None,
        "sdg_ref": ["SDG 3.9"],
    },
]


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def get_all_mappings() -> list[dict]:
    """Return complete cross-framework mapping."""
    return FRAMEWORK_MAPPING


def get_mapping_by_framework(framework: str) -> list[dict]:
    """Filter mappings that have a reference in the specified framework."""
    key = f"{framework}_ref"
    return [m for m in FRAMEWORK_MAPPING if m.get(key)]


def get_mapping_by_principle(principle: str) -> list[dict]:
    """Get all mappings for a BRSR principle (P1-P9)."""
    return [m for m in FRAMEWORK_MAPPING if m.get("principle") == principle]


def get_mapping_by_section(section: str) -> list[dict]:
    """Get all mappings for a BRSR section (section_a, section_b, section_c)."""
    return [m for m in FRAMEWORK_MAPPING if m.get("section") == section]


def get_mapping_for_brsr_id(brsr_id: str) -> Optional[dict]:
    """Get the cross-framework mapping for a specific BRSR data point."""
    for m in FRAMEWORK_MAPPING:
        if m["brsr_id"] == brsr_id:
            return m
    return None


def get_framework_coverage_stats() -> dict:
    """Get statistics on how many BRSR fields map to each framework."""
    total = len(FRAMEWORK_MAPPING)
    return {
        "total_brsr_disclosures_mapped": total,
        "esrs_coverage": len([m for m in FRAMEWORK_MAPPING if m.get("esrs_ref")]),
        "gri_coverage": len([m for m in FRAMEWORK_MAPPING if m.get("gri_ref")]),
        "tcfd_coverage": len([m for m in FRAMEWORK_MAPPING if m.get("tcfd_ref")]),
        "issb_coverage": len([m for m in FRAMEWORK_MAPPING if m.get("issb_ref")]),
        "sdg_coverage": len([m for m in FRAMEWORK_MAPPING if m.get("sdg_ref")]),
        "frameworks": {
            "esrs": {"full_name": "European Sustainability Reporting Standards", "body": "EFRAG (EU CSRD)", "version": "Set 1 (2024)"},
            "gri": {"full_name": "Global Reporting Initiative Standards", "body": "GRI", "version": "Universal 2021 + Topics"},
            "tcfd": {"full_name": "Task Force on Climate-related Financial Disclosures", "body": "FSB (now ISSB)", "version": "2017 (sunset 2024)"},
            "issb": {"full_name": "IFRS Sustainability Disclosure Standards", "body": "ISSB / IFRS Foundation", "version": "S1 + S2 (2023)"},
            "sdg": {"full_name": "UN Sustainable Development Goals", "body": "United Nations", "version": "2030 Agenda"},
        },
    }


def generate_cross_framework_report(extracted_data: dict) -> dict:
    """
    Given extracted BRSR data, show which international framework requirements
    are already covered and which are gaps.
    """
    extracted_fields = set()
    for section_data in extracted_data.values():
        if isinstance(section_data, dict):
            extracted_fields.update(section_data.keys())

    # Map extracted fields to BRSR IDs
    field_to_brsr_id = {
        "energy_consumption_total": "C.P6.E.1",
        "renewable_energy_pct": "C.P6.E.2",
        "ghg_scope1": "C.P6.E.3",
        "ghg_scope2": "C.P6.E.4",
        "water_withdrawal": "C.P6.E.6",
        "waste_generated": "C.P6.E.8",
        "waste_recycled_pct": "C.P6.E.9",
        "employee_turnover_rate": "A.IV.19-22",
        "women_board_pct": "A.IV.17",
        "training_hours_per_employee": "C.P3.E.3",
        "safety_incidents": "C.P3.E.2",
        "median_salary_male": "C.P3.E.4",
        "median_salary_female": "C.P3.E.4",
        "human_rights_training_pct": "C.P5.E.1",
        "child_labor_complaints": "C.P5.E.2",
        "code_of_conduct": "C.P1.E.1",
        "anti_corruption_policy": "C.P1.E.1",
        "r_and_d_spend": "C.P2.E.1",
        "sustainable_sourcing_pct": "C.P2.E.2",
        "recycled_input_pct": "C.P2.E.3",
        "csr_spend": "C.P8.E.1",
        "consumer_complaints": "C.P9.E.1",
        "data_privacy_complaints": "C.P9.E.2",
        "product_recalls": "C.P9.E.3",
        "stakeholder_groups_identified": "C.P4.E.1",
    }

    covered_brsr_ids = set()
    for field in extracted_fields:
        if field in field_to_brsr_id:
            covered_brsr_ids.add(field_to_brsr_id[field])

    # Check coverage per framework
    result = {"esrs": [], "gri": [], "tcfd": [], "issb": []}
    for mapping in FRAMEWORK_MAPPING:
        is_covered = mapping["brsr_id"] in covered_brsr_ids
        entry = {
            "brsr_id": mapping["brsr_id"],
            "brsr_label": mapping["brsr_label"],
            "covered": is_covered,
        }
        for fw in ["esrs", "gri", "tcfd", "issb"]:
            if mapping.get(f"{fw}_ref"):
                result[fw].append({
                    **entry,
                    f"{fw}_ref": mapping[f"{fw}_ref"],
                    f"{fw}_label": mapping.get(f"{fw}_label", ""),
                })

    summary = {}
    for fw in ["esrs", "gri", "tcfd", "issb"]:
        total = len(result[fw])
        covered = len([x for x in result[fw] if x["covered"]])
        summary[fw] = {
            "total_applicable": total,
            "covered": covered,
            "gaps": total - covered,
            "coverage_pct": round(covered / total * 100, 1) if total > 0 else 0,
        }

    return {
        "summary": summary,
        "details": result,
    }
