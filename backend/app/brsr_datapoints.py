"""
SEBI BRSR Data Points — Comprehensive list using EFRAG IG 3 (ESRS) methodology.

Each data point follows the ESRS structure:
- id: Unique identifier (section.subsection.sequential)
- label: Short description of the disclosure
- data_type: One of narrative, boolean, integer, monetary, percent, decimal, date, gyear, table, enumeration, mass, energy, volume, area, intensity
- mandatory: True if required by SEBI BRSR
- core: True if part of BRSR Core (subject to assurance)
- indicator_type: essential or leadership
- esrs_ref: Cross-reference to ESRS standard (where applicable)
- conditional: True if only applicable in certain circumstances
- paragraph_ref: BRSR Annexure II paragraph reference

Based on:
- SEBI BRSR Annexure II (Updated Format)
- SEBI BRSR Core Annexure I
- EFRAG IG 3 List of ESRS Data Points methodology
"""

# Data types following EFRAG IG 3 / XBRL taxonomy
DATA_TYPES = {
    "narrative": "Free-text disclosure (textblock)",
    "boolean": "Yes/No (True/False)",
    "integer": "Non-decimal positive number",
    "monetary": "Currency amount (INR)",
    "percent": "Percentage value",
    "decimal": "Numeric with decimals",
    "date": "Day/Month/Year",
    "gyear": "Year only",
    "table": "Dimensional table with breakdowns",
    "enumeration": "Selection from predefined list",
    "mass": "Mass measurement (MT, kg)",
    "energy": "Energy measurement (GJ, MWh)",
    "volume": "Volume measurement (KL, m³)",
    "area": "Area measurement (sq m, hectare)",
    "intensity": "Ratio with numerator and denominator",
}

BRSR_DATAPOINTS = [
    # ═══════════════════════════════════════════════════════════
    # SECTION A: GENERAL DISCLOSURES
    # ═══════════════════════════════════════════════════════════

    # I. Details of the Listed Entity
    {"id": "A.I.1", "label": "Corporate Identity Number (CIN)", "data_type": "narrative", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": "ESRS 2 BP-1", "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.2", "label": "Name of the Listed Entity", "data_type": "narrative", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": "ESRS 2 BP-1", "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.3", "label": "Year of incorporation", "data_type": "gyear", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.4", "label": "Registered office address", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.5", "label": "Corporate address", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.6", "label": "E-mail", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.7", "label": "Telephone", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.8", "label": "Website", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.9", "label": "Financial year for which reporting is being done", "data_type": "gyear", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": "ESRS 2 BP-1.7", "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.10", "label": "Name of Stock Exchange(s) where shares are listed", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.11", "label": "Paid-up Capital (INR)", "data_type": "monetary", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.12", "label": "Name and contact details of person for BRSR queries", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.13", "label": "Reporting boundary - Standalone or Consolidated", "data_type": "enumeration", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": "ESRS 2 BP-1.9", "conditional": False, "paragraph_ref": "Section A.I"},
    {"id": "A.I.14", "label": "Name of assurance provider", "data_type": "narrative", "mandatory": False, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": "ESRS 2 BP-1.11", "conditional": True, "paragraph_ref": "Section A.I"},
    {"id": "A.I.15", "label": "Type of assurance obtained (limited/reasonable)", "data_type": "enumeration", "mandatory": False, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "details_of_entity", "esrs_ref": "ESRS 2 BP-1.11", "conditional": True, "paragraph_ref": "Section A.I"},

    # II. Products/Services
    {"id": "A.II.1", "label": "Details of business activities (accounting for 90% of turnover)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "products_services", "esrs_ref": "ESRS 2 SBM-1", "conditional": False, "paragraph_ref": "Section A.II"},
    {"id": "A.II.2", "label": "Products/Services sold (accounting for 90% of turnover)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "products_services", "esrs_ref": "ESRS 2 SBM-1", "conditional": False, "paragraph_ref": "Section A.II"},
    {"id": "A.II.3", "label": "NIC codes for products/services", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "products_services", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.II"},

    # III. Operations
    {"id": "A.III.1", "label": "Number of locations - Plants (National)", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": "ESRS 2 SBM-1.40(a)", "conditional": False, "paragraph_ref": "Section A.III"},
    {"id": "A.III.2", "label": "Number of locations - Plants (International)", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": "ESRS 2 SBM-1.40(a)", "conditional": False, "paragraph_ref": "Section A.III"},
    {"id": "A.III.3", "label": "Number of locations - Offices (National)", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.III"},
    {"id": "A.III.4", "label": "Number of locations - Offices (International)", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.III"},
    {"id": "A.III.5", "label": "Markets served - Number of States/UTs", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": "ESRS 2 SBM-1.40(b)", "conditional": False, "paragraph_ref": "Section A.III"},
    {"id": "A.III.6", "label": "Markets served - Number of Countries", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": "ESRS 2 SBM-1.40(b)", "conditional": False, "paragraph_ref": "Section A.III"},
    {"id": "A.III.7", "label": "Contribution of exports as % of total turnover", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.III"},
    {"id": "A.III.8", "label": "Types of customers", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "operations", "esrs_ref": "ESRS 2 SBM-1.40(c)", "conditional": False, "paragraph_ref": "Section A.III"},

    # IV. Employees
    {"id": "A.IV.1", "label": "Total employees - Permanent - Male", "data_type": "integer", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(a)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.2", "label": "Total employees - Permanent - Female", "data_type": "integer", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(a)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.3", "label": "Total employees - Permanent - Total", "data_type": "integer", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(a)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.4", "label": "Total employees - Other than Permanent - Male", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(b)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.5", "label": "Total employees - Other than Permanent - Female", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(b)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.6", "label": "Total employees - Other than Permanent - Total", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(b)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.7", "label": "Total workers - Permanent - Male", "data_type": "integer", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(a)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.8", "label": "Total workers - Permanent - Female", "data_type": "integer", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(a)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.9", "label": "Total workers - Permanent - Total", "data_type": "integer", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(a)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.10", "label": "Total workers - Other than Permanent - Male", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(b)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.11", "label": "Total workers - Other than Permanent - Female", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(b)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.12", "label": "Total workers - Other than Permanent - Total", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.50(b)", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.13", "label": "Differently abled Employees - Permanent (Male/Female/Total)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-12", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.14", "label": "Differently abled Employees - Other than Permanent (Male/Female/Total)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-12", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.15", "label": "Differently abled Workers - Permanent (Male/Female/Total)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-12", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.16", "label": "Differently abled Workers - Other than Permanent (Male/Female/Total)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-12", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.17", "label": "Participation/Inclusion/Representation of women - Board of Directors (%)", "data_type": "percent", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-9.66", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.18", "label": "Participation/Inclusion/Representation of women - Key Management Personnel (%)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-9.66", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.19", "label": "Turnover rate for permanent employees - Male (current + 2 preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.53", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.20", "label": "Turnover rate for permanent employees - Female (current + 2 preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.53", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.21", "label": "Turnover rate for permanent workers - Male (current + 2 preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.53", "conditional": False, "paragraph_ref": "Section A.IV"},
    {"id": "A.IV.22", "label": "Turnover rate for permanent workers - Female (current + 2 preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_a", "subsection": "employees", "esrs_ref": "ESRS S1-6.53", "conditional": False, "paragraph_ref": "Section A.IV"},

    # V. Holding, Subsidiary and Associate Companies
    {"id": "A.V.1", "label": "Names of holding/subsidiary/associate/JV companies", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "holding_subsidiary", "esrs_ref": "ESRS 2 BP-1.8", "conditional": False, "paragraph_ref": "Section A.V"},
    {"id": "A.V.2", "label": "Whether business conduct/ethics policies apply to group companies", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "holding_subsidiary", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.V"},

    # VI. CSR Details
    {"id": "A.VI.1", "label": "Whether CSR is applicable as per Section 135 of Companies Act 2013", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "csr_details", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.VI"},
    {"id": "A.VI.2", "label": "Turnover (in Rs.)", "data_type": "monetary", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "csr_details", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.VI"},
    {"id": "A.VI.3", "label": "Net worth (in Rs.)", "data_type": "monetary", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "csr_details", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section A.VI"},

    # VII. Transparency and Disclosures Compliances
    {"id": "A.VII.1", "label": "Complaints/Grievances on any of the Principles (P1-P9) - Number filed/pending/remarks", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "transparency", "esrs_ref": "ESRS 2 GOV-1", "conditional": False, "paragraph_ref": "Section A.VII"},
    {"id": "A.VII.2", "label": "Overview of material responsible business conduct and sustainability issues", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_a", "subsection": "transparency", "esrs_ref": "ESRS 2 SBM-3", "conditional": False, "paragraph_ref": "Section A.VII"},

    # ═══════════════════════════════════════════════════════════
    # SECTION B: MANAGEMENT AND PROCESS DISCLOSURES
    # ═══════════════════════════════════════════════════════════

    # Policy and Management Processes (for each principle P1-P9)
    {"id": "B.1", "label": "Whether policy covers each principle (P1-P9)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": "ESRS 2 MDR-P", "conditional": False, "paragraph_ref": "Section B.1"},
    {"id": "B.2", "label": "Whether policy approved by Board (P1-P9)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": "ESRS 2 MDR-P.65(a)", "conditional": False, "paragraph_ref": "Section B.1"},
    {"id": "B.3", "label": "Web link of each policy (P1-P9)", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section B.1"},
    {"id": "B.4", "label": "Whether policy has been translated into procedures/codes", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": "ESRS 2 MDR-P.65(d)", "conditional": False, "paragraph_ref": "Section B.1"},
    {"id": "B.5", "label": "Whether policy extends to value chain partners", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": "ESRS 2 MDR-P.65(e)", "conditional": False, "paragraph_ref": "Section B.1"},
    {"id": "B.6", "label": "National/international codes/certifications/labels adopted (mapped to principles)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section B.1"},
    {"id": "B.7", "label": "Specific commitments, goals and targets set with defined timelines", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": "ESRS 2 MDR-T", "conditional": False, "paragraph_ref": "Section B.1"},
    {"id": "B.8", "label": "Performance of entity against specific commitments/goals/targets", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "policy_management", "esrs_ref": "ESRS 2 MDR-T.80(b)", "conditional": False, "paragraph_ref": "Section B.1"},

    # Governance, Leadership and Oversight
    {"id": "B.9", "label": "Statement by director responsible for BR highlighting ESG challenges, targets, achievement", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "governance", "esrs_ref": "ESRS 2 GOV-1", "conditional": False, "paragraph_ref": "Section B.2"},
    {"id": "B.10", "label": "Details of highest authority responsible for implementation of BR policies", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "governance", "esrs_ref": "ESRS 2 GOV-1.21", "conditional": False, "paragraph_ref": "Section B.2"},
    {"id": "B.11", "label": "Whether sustainability-related decisions are considered in Board Committee meetings", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "governance", "esrs_ref": "ESRS 2 GOV-1.22(c)", "conditional": False, "paragraph_ref": "Section B.2"},
    {"id": "B.12", "label": "Details of review of NGRBCs by Board/Committee - frequency and scope", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "governance", "esrs_ref": "ESRS 2 GOV-1.22", "conditional": False, "paragraph_ref": "Section B.2"},
    {"id": "B.13", "label": "Whether independent assessment/evaluation of policies by external agency", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "governance", "esrs_ref": None, "conditional": False, "paragraph_ref": "Section B.2"},
    {"id": "B.14", "label": "Name of external agency performing assessment", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "essential", "section": "section_b", "subsection": "governance", "esrs_ref": None, "conditional": True, "paragraph_ref": "Section B.2"},

    # ═══════════════════════════════════════════════════════════
    # SECTION C: PRINCIPLE WISE PERFORMANCE DISCLOSURE
    # ═══════════════════════════════════════════════════════════

    # PRINCIPLE 1: Ethics, Transparency and Accountability
    # Essential Indicators
    {"id": "C.P1.E.1", "label": "Percentage of training/awareness on principles (Board of Directors)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-1.10", "conditional": False, "paragraph_ref": "P1 Essential Q1"},
    {"id": "C.P1.E.2", "label": "Percentage of training/awareness on principles (KMPs)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-1.10", "conditional": False, "paragraph_ref": "P1 Essential Q1"},
    {"id": "C.P1.E.3", "label": "Percentage of training/awareness on principles (Employees other than BoD/KMPs)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-1.10", "conditional": False, "paragraph_ref": "P1 Essential Q1"},
    {"id": "C.P1.E.4", "label": "Percentage of training/awareness on principles (Workers)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-1.10", "conditional": False, "paragraph_ref": "P1 Essential Q1"},
    {"id": "C.P1.E.5", "label": "Details of fines/penalties/punishment/award/compounding from NFRA/SEBI/regulatory/judicial", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-4.24", "conditional": False, "paragraph_ref": "P1 Essential Q2"},
    {"id": "C.P1.E.6", "label": "Details of appeal/revision preferred (against fines/penalties)", "data_type": "narrative", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": None, "conditional": True, "paragraph_ref": "P1 Essential Q2"},
    {"id": "C.P1.E.7", "label": "Whether entity has anti-corruption or anti-bribery policy", "data_type": "boolean", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-1.10(b)", "conditional": False, "paragraph_ref": "P1 Essential Q3"},
    {"id": "C.P1.E.8", "label": "Number of Directors/KMPs/employees against whom disciplinary action taken for bribery/corruption", "data_type": "integer", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-4", "conditional": False, "paragraph_ref": "P1 Essential Q4"},
    {"id": "C.P1.E.9", "label": "Number of complaints regarding conflict of interest - Directors (current FY + preceding FY)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-3", "conditional": False, "paragraph_ref": "P1 Essential Q5"},
    {"id": "C.P1.E.10", "label": "Number of complaints regarding conflict of interest - KMPs (current FY + preceding FY)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-3", "conditional": False, "paragraph_ref": "P1 Essential Q5"},
    {"id": "C.P1.E.11", "label": "Corrective action taken on fines/penalties/action in current FY", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": None, "conditional": False, "paragraph_ref": "P1 Essential Q6"},
    {"id": "C.P1.E.12", "label": "Number of days of accounts payables (current FY + preceding FY)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": None, "conditional": False, "paragraph_ref": "P1 Essential Q7"},
    {"id": "C.P1.E.13", "label": "Concentration of purchases - top 10 suppliers as % of total purchases", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": None, "conditional": False, "paragraph_ref": "P1 Essential Q8"},
    {"id": "C.P1.E.14", "label": "Concentration of sales - top 10 customers as % of total sales", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_1", "esrs_ref": None, "conditional": False, "paragraph_ref": "P1 Essential Q8"},
    # Leadership Indicators
    {"id": "C.P1.L.1", "label": "Awareness programmes conducted for value chain partners on principles", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-1.10(c)", "conditional": False, "paragraph_ref": "P1 Leadership Q1"},
    {"id": "C.P1.L.2", "label": "Whether entity has processes to avoid/manage conflict of interest (Board/KMPs)", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_1", "esrs_ref": "ESRS G1-3", "conditional": False, "paragraph_ref": "P1 Leadership Q2"},

    # PRINCIPLE 2: Sustainable and Safe Products/Services
    # Essential Indicators
    {"id": "C.P2.E.1", "label": "R&D and capex investments for improvement in environmental aspects of products (% of turnover)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E1-3.29(c)", "conditional": False, "paragraph_ref": "P2 Essential Q1"},
    {"id": "C.P2.E.2", "label": "R&D and capex investments for improvement in social aspects of products (% of turnover)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E1-3.29(c)", "conditional": False, "paragraph_ref": "P2 Essential Q1"},
    {"id": "C.P2.E.3", "label": "Whether entity has procedures for sustainable sourcing", "data_type": "boolean", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-4", "conditional": False, "paragraph_ref": "P2 Essential Q2"},
    {"id": "C.P2.E.4", "label": "Percentage of inputs sourced sustainably", "data_type": "percent", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-4", "conditional": False, "paragraph_ref": "P2 Essential Q2"},
    {"id": "C.P2.E.5", "label": "Describe processes in place to safely reclaim products at end of life (reuse/recycle/safe disposal)", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-5", "conditional": False, "paragraph_ref": "P2 Essential Q3"},
    {"id": "C.P2.E.6", "label": "Whether Extended Producer Responsibility (EPR) is applicable", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": None, "conditional": False, "paragraph_ref": "P2 Essential Q4"},
    {"id": "C.P2.E.7", "label": "EPR - Plastic waste collected/recycled (if applicable)", "data_type": "mass", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": None, "conditional": True, "paragraph_ref": "P2 Essential Q4"},
    {"id": "C.P2.E.8", "label": "EPR - E-waste collected/recycled (if applicable)", "data_type": "mass", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_2", "esrs_ref": None, "conditional": True, "paragraph_ref": "P2 Essential Q4"},
    # Leadership Indicators
    {"id": "C.P2.L.1", "label": "Whether Life Cycle Perspective/Assessment (LCA) conducted for products", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-1.12", "conditional": False, "paragraph_ref": "P2 Leadership Q1"},
    {"id": "C.P2.L.2", "label": "Results of LCA and significant social/environmental concerns identified", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-1.12", "conditional": True, "paragraph_ref": "P2 Leadership Q1"},
    {"id": "C.P2.L.3", "label": "Recycled/reused input material to total material - by weight (%)", "data_type": "percent", "mandatory": False, "core": True, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-4.37", "conditional": False, "paragraph_ref": "P2 Leadership Q2"},
    {"id": "C.P2.L.4", "label": "Products and packaging reclaimed at end of life - Reused (MT/% of total)", "data_type": "table", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-5", "conditional": False, "paragraph_ref": "P2 Leadership Q3"},
    {"id": "C.P2.L.5", "label": "Products and packaging reclaimed at end of life - Recycled (MT/% of total)", "data_type": "table", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_2", "esrs_ref": "ESRS E5-5", "conditional": False, "paragraph_ref": "P2 Leadership Q3"},

    # PRINCIPLE 3: Employee Well-being
    # Essential Indicators
    {"id": "C.P3.E.1", "label": "Well-being measures for employees - Health insurance coverage (%)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-11", "conditional": False, "paragraph_ref": "P3 Essential Q1a"},
    {"id": "C.P3.E.2", "label": "Well-being measures for employees - Accident insurance coverage (%)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-11", "conditional": False, "paragraph_ref": "P3 Essential Q1a"},
    {"id": "C.P3.E.3", "label": "Well-being measures for employees - Maternity benefits coverage (%)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-15", "conditional": False, "paragraph_ref": "P3 Essential Q1a"},
    {"id": "C.P3.E.4", "label": "Well-being measures for employees - Paternity benefits coverage (%)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-15", "conditional": False, "paragraph_ref": "P3 Essential Q1a"},
    {"id": "C.P3.E.5", "label": "Well-being measures for employees - Day care facilities coverage (%)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": None, "conditional": False, "paragraph_ref": "P3 Essential Q1a"},
    {"id": "C.P3.E.6", "label": "Well-being measures for workers - Health/Accident/Maternity/Paternity/Day care (%)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-11", "conditional": False, "paragraph_ref": "P3 Essential Q1b"},
    {"id": "C.P3.E.7", "label": "Spending on measures towards well-being of employees and workers (% of total revenue)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": None, "conditional": False, "paragraph_ref": "P3 Essential Q1c"},
    {"id": "C.P3.E.8", "label": "Retirement benefits (PF/Gratuity/ESI/Others) - deducted and deposited on time", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-11.78(c)", "conditional": False, "paragraph_ref": "P3 Essential Q2"},
    {"id": "C.P3.E.9", "label": "Whether premises/offices accessible to differently abled employees/workers", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-12", "conditional": False, "paragraph_ref": "P3 Essential Q3"},
    {"id": "C.P3.E.10", "label": "Whether entity has an equal opportunity policy", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-1", "conditional": False, "paragraph_ref": "P3 Essential Q4"},
    {"id": "C.P3.E.11", "label": "Return to work and Retention rates of permanent employees that took parental leave", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-15.93", "conditional": False, "paragraph_ref": "P3 Essential Q5"},
    {"id": "C.P3.E.12", "label": "Whether mechanism for grievance redressal available for employees", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-3", "conditional": False, "paragraph_ref": "P3 Essential Q6"},
    {"id": "C.P3.E.13", "label": "Whether mechanism for grievance redressal available for workers", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-3", "conditional": False, "paragraph_ref": "P3 Essential Q6"},
    {"id": "C.P3.E.14", "label": "Membership of employees and workers in associations/unions (current + preceding FY)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-8", "conditional": False, "paragraph_ref": "P3 Essential Q7"},
    {"id": "C.P3.E.15", "label": "Training details - Health and safety measures (employees/workers by gender)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-14.88(b)", "conditional": False, "paragraph_ref": "P3 Essential Q8"},
    {"id": "C.P3.E.16", "label": "Training details - Skill upgradation (employees/workers by gender)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-13", "conditional": False, "paragraph_ref": "P3 Essential Q8"},
    {"id": "C.P3.E.17", "label": "Performance and career development reviews - Employees (Male/Female/%)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-13.85", "conditional": False, "paragraph_ref": "P3 Essential Q9"},
    {"id": "C.P3.E.18", "label": "Performance and career development reviews - Workers (Male/Female/%)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-13.85", "conditional": False, "paragraph_ref": "P3 Essential Q9"},
    {"id": "C.P3.E.19", "label": "Whether occupational health and safety management system has been implemented", "data_type": "boolean", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-14.88(a)", "conditional": False, "paragraph_ref": "P3 Essential Q10"},
    {"id": "C.P3.E.20", "label": "Details of safety incidents - LTIFR (Employees/Workers)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-14.88(b)", "conditional": False, "paragraph_ref": "P3 Essential Q11"},
    {"id": "C.P3.E.21", "label": "Details of safety incidents - Fatalities (Employees/Workers)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-14.88(e)", "conditional": False, "paragraph_ref": "P3 Essential Q11"},
    {"id": "C.P3.E.22", "label": "Details of safety incidents - Reportable injuries", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-14.88(b)", "conditional": False, "paragraph_ref": "P3 Essential Q11"},
    {"id": "C.P3.E.23", "label": "Measures taken to ensure safe and healthy workplace", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-14", "conditional": False, "paragraph_ref": "P3 Essential Q12"},
    {"id": "C.P3.E.24", "label": "Complaints on working conditions/health & safety (current + preceding FY - filed/pending/resolved)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-17", "conditional": False, "paragraph_ref": "P3 Essential Q13"},
    {"id": "C.P3.E.25", "label": "Assessments for the year - % of plants/offices assessed for health & safety", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_3", "esrs_ref": None, "conditional": False, "paragraph_ref": "P3 Essential Q14"},
    # Leadership Indicators
    {"id": "C.P3.L.1", "label": "Whether entity provides life insurance/disability and invalidity coverage to employees/workers", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-11", "conditional": False, "paragraph_ref": "P3 Leadership Q1"},
    {"id": "C.P3.L.2", "label": "Transition assistance programs provided to retiring employees", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_3", "esrs_ref": None, "conditional": False, "paragraph_ref": "P3 Leadership Q2"},
    {"id": "C.P3.L.3", "label": "High consequence work-related injuries/ill-health (employees/workers)", "data_type": "table", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_3", "esrs_ref": "ESRS S1-14.88(c)", "conditional": False, "paragraph_ref": "P3 Leadership Q3"},
    {"id": "C.P3.L.4", "label": "Whether entity provides rehab support for affected employees/workers", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_3", "esrs_ref": None, "conditional": False, "paragraph_ref": "P3 Leadership Q3"},

    # PRINCIPLE 4: Stakeholder Engagement
    # Essential Indicators
    {"id": "C.P4.E.1", "label": "Stakeholder group(s) identified as key for the entity", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_4", "esrs_ref": "ESRS 2 SBM-2", "conditional": False, "paragraph_ref": "P4 Essential Q1"},
    {"id": "C.P4.E.2", "label": "Channels/platforms/structure for stakeholder engagement", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_4", "esrs_ref": "ESRS 2 SBM-2.45", "conditional": False, "paragraph_ref": "P4 Essential Q2"},
    # Leadership Indicators
    {"id": "C.P4.L.1", "label": "Details of processes for consulting stakeholders on economic/environmental/social topics", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_4", "esrs_ref": "ESRS 2 SBM-2.46", "conditional": False, "paragraph_ref": "P4 Leadership Q1"},
    {"id": "C.P4.L.2", "label": "Whether key stakeholder concerns form part of decision-making", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_4", "esrs_ref": "ESRS 2 SBM-2.47", "conditional": False, "paragraph_ref": "P4 Leadership Q2"},

    # PRINCIPLE 5: Human Rights
    # Essential Indicators
    {"id": "C.P5.E.1", "label": "Employees covered by training on Human Rights issues/policy (% by category)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-14", "conditional": False, "paragraph_ref": "P5 Essential Q1"},
    {"id": "C.P5.E.2", "label": "Workers covered by training on Human Rights issues/policy (% by category)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-14", "conditional": False, "paragraph_ref": "P5 Essential Q1"},
    {"id": "C.P5.E.3", "label": "Details of minimum wages paid - Employees (Equal to/More than min wage by gender)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-10.72", "conditional": False, "paragraph_ref": "P5 Essential Q2"},
    {"id": "C.P5.E.4", "label": "Details of minimum wages paid - Workers (Equal to/More than min wage by gender)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-10.72", "conditional": False, "paragraph_ref": "P5 Essential Q2"},
    {"id": "C.P5.E.5", "label": "Details of remuneration/salary/wages - Median remuneration Male vs Female (Board/KMP/Employees/Workers)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-16.97(a)", "conditional": False, "paragraph_ref": "P5 Essential Q3"},
    {"id": "C.P5.E.6", "label": "Gross wages paid to females as % of total wages (by Board/KMP/Employees/Workers)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-16.97(a)", "conditional": False, "paragraph_ref": "P5 Essential Q3"},
    {"id": "C.P5.E.7", "label": "Complaints on Sexual Harassment (POSH) - Filed/Pending/Resolved (current + preceding FY)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-17", "conditional": False, "paragraph_ref": "P5 Essential Q4"},
    {"id": "C.P5.E.8", "label": "Complaints on Discrimination at workplace - Filed/Pending/Resolved (current + preceding FY)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-17", "conditional": False, "paragraph_ref": "P5 Essential Q4"},
    {"id": "C.P5.E.9", "label": "Complaints on Child Labour - Filed/Pending/Resolved (current + preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-17", "conditional": False, "paragraph_ref": "P5 Essential Q4"},
    {"id": "C.P5.E.10", "label": "Complaints on Forced Labour/Involuntary Labour - Filed/Pending/Resolved", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-17", "conditional": False, "paragraph_ref": "P5 Essential Q4"},
    {"id": "C.P5.E.11", "label": "Complaints on Wages - Filed/Pending/Resolved (current + preceding FY)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-17", "conditional": False, "paragraph_ref": "P5 Essential Q4"},
    {"id": "C.P5.E.12", "label": "% of plants/offices assessed for Human Rights (by entity/statutory/third party)", "data_type": "percent", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": None, "conditional": False, "paragraph_ref": "P5 Essential Q5"},
    {"id": "C.P5.E.13", "label": "Corrective actions taken/underway to address significant HR risks/concerns", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-4", "conditional": False, "paragraph_ref": "P5 Essential Q6"},
    # Leadership Indicators
    {"id": "C.P5.L.1", "label": "Details of business processes modified based on HR due diligence/assessments", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-4.40", "conditional": False, "paragraph_ref": "P5 Leadership Q1"},
    {"id": "C.P5.L.2", "label": "Details of scope and coverage of Human Rights due diligence (value chain)", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_5", "esrs_ref": "ESRS S1-4", "conditional": False, "paragraph_ref": "P5 Leadership Q2"},

    # PRINCIPLE 6: Environment
    # Essential Indicators
    {"id": "C.P6.E.1", "label": "Total energy consumption - from renewable sources (GJ)", "data_type": "energy", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-5.38(a)", "conditional": False, "paragraph_ref": "P6 Essential Q1"},
    {"id": "C.P6.E.2", "label": "Total energy consumption - from non-renewable sources (GJ)", "data_type": "energy", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-5.38(b)", "conditional": False, "paragraph_ref": "P6 Essential Q1"},
    {"id": "C.P6.E.3", "label": "Total electricity consumption (GJ)", "data_type": "energy", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-5.37", "conditional": False, "paragraph_ref": "P6 Essential Q1"},
    {"id": "C.P6.E.4", "label": "Total fuel consumption (GJ)", "data_type": "energy", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-5.37", "conditional": False, "paragraph_ref": "P6 Essential Q1"},
    {"id": "C.P6.E.5", "label": "Energy intensity per rupee of turnover (GJ/INR cr)", "data_type": "intensity", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-5.40", "conditional": False, "paragraph_ref": "P6 Essential Q1"},
    {"id": "C.P6.E.6", "label": "Whether entity has indicated voluntary target for renewable energy usage", "data_type": "boolean", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-3", "conditional": False, "paragraph_ref": "P6 Essential Q1"},
    {"id": "C.P6.E.7", "label": "Whether entity uses PAT scheme (Perform Achieve Trade)", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": None, "conditional": False, "paragraph_ref": "P6 Essential Q2"},
    {"id": "C.P6.E.8", "label": "Water withdrawal by source - Surface water (KL)", "data_type": "volume", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28(a)", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.9", "label": "Water withdrawal by source - Groundwater (KL)", "data_type": "volume", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28(a)", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.10", "label": "Water withdrawal by source - Third party (KL)", "data_type": "volume", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28(a)", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.11", "label": "Total volume of water withdrawal (KL)", "data_type": "volume", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.12", "label": "Total volume of water consumption (KL)", "data_type": "volume", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.13", "label": "Water intensity per rupee of turnover (KL/INR cr)", "data_type": "intensity", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.29", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.14", "label": "Water discharged by destination and treatment (KL)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28(c)", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.15", "label": "Whether water withdrawal from areas of water stress", "data_type": "boolean", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28(b)", "conditional": False, "paragraph_ref": "P6 Essential Q3"},
    {"id": "C.P6.E.16", "label": "Scope 1 emissions - Total GHG (tCO2e)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-6.44(a)", "conditional": False, "paragraph_ref": "P6 Essential Q4"},
    {"id": "C.P6.E.17", "label": "Scope 2 emissions - Total GHG (tCO2e)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-6.44(b)", "conditional": False, "paragraph_ref": "P6 Essential Q4"},
    {"id": "C.P6.E.18", "label": "Total Scope 1 and Scope 2 emissions per rupee of turnover (intensity)", "data_type": "intensity", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-6.53", "conditional": False, "paragraph_ref": "P6 Essential Q4"},
    {"id": "C.P6.E.19", "label": "Whether entity has voluntarily set GHG emission reduction target", "data_type": "boolean", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-4", "conditional": False, "paragraph_ref": "P6 Essential Q4"},
    {"id": "C.P6.E.20", "label": "Whether project registered under CDM/voluntary mechanism", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": None, "conditional": False, "paragraph_ref": "P6 Essential Q5"},
    {"id": "C.P6.E.21", "label": "Waste generated - Plastic waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.22", "label": "Waste generated - E-waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.23", "label": "Waste generated - Bio-medical waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.24", "label": "Waste generated - Construction/demolition waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.25", "label": "Waste generated - Battery waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.26", "label": "Waste generated - Radioactive waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.27", "label": "Waste generated - Other Hazardous waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.28", "label": "Waste generated - Other Non-hazardous waste (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(a)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.29", "label": "Total waste generated (MT)", "data_type": "mass", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.30", "label": "Waste intensity per rupee of turnover (MT/INR cr)", "data_type": "intensity", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.31", "label": "Each category of waste - Recovered through recycling (MT)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(b)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.32", "label": "Each category of waste - Recovered through re-using (MT)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(b)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.33", "label": "Each category of waste - Recovered through other recovery (MT)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(b)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.34", "label": "Each category of waste - Disposed to landfill (MT)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(c)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.35", "label": "Each category of waste - Disposed by incineration (MT)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-5.37(c)", "conditional": False, "paragraph_ref": "P6 Essential Q6"},
    {"id": "C.P6.E.36", "label": "Whether entity has operations in/around ecologically sensitive areas", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E4-5.35", "conditional": False, "paragraph_ref": "P6 Essential Q7"},
    {"id": "C.P6.E.37", "label": "Details of environmental impact assessments (EIAs) undertaken", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": None, "conditional": False, "paragraph_ref": "P6 Essential Q8"},
    {"id": "C.P6.E.38", "label": "Details of environmental compliance/non-compliances", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E2-6", "conditional": False, "paragraph_ref": "P6 Essential Q9"},
    # Leadership Indicators
    {"id": "C.P6.L.1", "label": "Water discharge - Zero Liquid Discharge status (with breakup)", "data_type": "narrative", "mandatory": False, "core": True, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E3-4.28(c)", "conditional": False, "paragraph_ref": "P6 Leadership Q1"},
    {"id": "C.P6.L.2", "label": "Scope 3 emissions - Total GHG (tCO2e) with sources", "data_type": "mass", "mandatory": False, "core": True, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E1-6.44(c)", "conditional": False, "paragraph_ref": "P6 Leadership Q2"},
    {"id": "C.P6.L.3", "label": "Whether entity has signed voluntary pledge/agreement for environmental protection", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_6", "esrs_ref": None, "conditional": False, "paragraph_ref": "P6 Leadership Q3"},
    {"id": "C.P6.L.4", "label": "Significant direct/indirect impact on biodiversity", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E4-5", "conditional": False, "paragraph_ref": "P6 Leadership Q4"},
    {"id": "C.P6.L.5", "label": "Whether entity has framework/policy on circular economy", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_6", "esrs_ref": "ESRS E5-1", "conditional": False, "paragraph_ref": "P6 Leadership Q5"},

    # PRINCIPLE 7: Policy Advocacy
    # Essential Indicators
    {"id": "C.P7.E.1", "label": "Trade and industry chambers/associations entity is member of (top 10 by fees)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_7", "esrs_ref": "ESRS G1-5.27", "conditional": False, "paragraph_ref": "P7 Essential Q1"},
    {"id": "C.P7.E.2", "label": "Details of cases of anti-competitive conduct by entity (past 5 years)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_7", "esrs_ref": "ESRS G1-4.24", "conditional": False, "paragraph_ref": "P7 Essential Q2"},
    # Leadership Indicators
    {"id": "C.P7.L.1", "label": "Public policy advocacy positions - top issues and entity's position", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_7", "esrs_ref": "ESRS G1-5.28", "conditional": False, "paragraph_ref": "P7 Leadership Q1"},

    # PRINCIPLE 8: Inclusive Growth and Equitable Development
    # Essential Indicators
    {"id": "C.P8.E.1", "label": "Details of Social Impact Assessments (SIA) - Name/Date/Results/External agency", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_8", "esrs_ref": "ESRS S3-4", "conditional": False, "paragraph_ref": "P8 Essential Q1"},
    {"id": "C.P8.E.2", "label": "Details of rehabilitation and resettlement - project name/affected families/amount paid", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_8", "esrs_ref": "ESRS S3-4", "conditional": True, "paragraph_ref": "P8 Essential Q2"},
    {"id": "C.P8.E.3", "label": "Whether entity has mechanisms to receive/redress community grievances", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_8", "esrs_ref": "ESRS S3-3", "conditional": False, "paragraph_ref": "P8 Essential Q3"},
    {"id": "C.P8.E.4", "label": "Community complaints/grievances - Number received and pending resolution (%)", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_8", "esrs_ref": "ESRS S3-5", "conditional": False, "paragraph_ref": "P8 Essential Q3"},
    {"id": "C.P8.E.5", "label": "Percentage of input material sourced from MSMEs/small producers", "data_type": "percent", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_8", "esrs_ref": None, "conditional": False, "paragraph_ref": "P8 Essential Q4"},
    {"id": "C.P8.E.6", "label": "Percentage of input material sourced from within district/neighbouring districts", "data_type": "percent", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_8", "esrs_ref": None, "conditional": False, "paragraph_ref": "P8 Essential Q4"},
    {"id": "C.P8.E.7", "label": "Details of CSR projects - Amount spent/allocated/unspent", "data_type": "table", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_8", "esrs_ref": None, "conditional": True, "paragraph_ref": "P8 Essential Q5"},
    # Leadership Indicators
    {"id": "C.P8.L.1", "label": "Job creation in smaller towns - Wages paid to persons employed in smaller towns", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_8", "esrs_ref": None, "conditional": False, "paragraph_ref": "P8 Leadership Q1"},
    {"id": "C.P8.L.2", "label": "Whether entity has beneficial impact on local community (aspiration districts)", "data_type": "narrative", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_8", "esrs_ref": "ESRS S3-4", "conditional": False, "paragraph_ref": "P8 Leadership Q2"},
    {"id": "C.P8.L.3", "label": "Preferential procurement policy for marginalized/vulnerable groups", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_8", "esrs_ref": None, "conditional": False, "paragraph_ref": "P8 Leadership Q3"},
    {"id": "C.P8.L.4", "label": "CSR beneficiaries breakdown by SC/ST/Others", "data_type": "table", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_8", "esrs_ref": None, "conditional": False, "paragraph_ref": "P8 Leadership Q4"},

    # PRINCIPLE 9: Consumer Responsibility
    # Essential Indicators
    {"id": "C.P9.E.1", "label": "Complaints on Data Privacy - Number received/pending/remarks (current + preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q1"},
    {"id": "C.P9.E.2", "label": "Complaints on Advertising - Number received/pending/remarks (current + preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q1"},
    {"id": "C.P9.E.3", "label": "Complaints on Cyber-Security - Number received/pending/remarks", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q1"},
    {"id": "C.P9.E.4", "label": "Complaints on Delivery of essential services - Number received/pending/remarks", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q1"},
    {"id": "C.P9.E.5", "label": "Complaints on Restrictive Trade Practices - Number received/pending/remarks", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q1"},
    {"id": "C.P9.E.6", "label": "Complaints on Unfair Trade Practices - Number received/pending/remarks", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q1"},
    {"id": "C.P9.E.7", "label": "Number of instances of product recalls - voluntary/forced (current + preceding FY)", "data_type": "table", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q2"},
    {"id": "C.P9.E.8", "label": "Reasons for each product recall", "data_type": "narrative", "mandatory": True, "core": True, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": None, "conditional": True, "paragraph_ref": "P9 Essential Q2"},
    {"id": "C.P9.E.9", "label": "Whether entity has a framework/policy on cyber security and data privacy", "data_type": "boolean", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-1", "conditional": False, "paragraph_ref": "P9 Essential Q3"},
    {"id": "C.P9.E.10", "label": "Details of corrective actions taken/underway on issues related to product/service quality", "data_type": "narrative", "mandatory": True, "core": False, "indicator_type": "essential", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-4", "conditional": False, "paragraph_ref": "P9 Essential Q4"},
    # Leadership Indicators
    {"id": "C.P9.L.1", "label": "Whether entity provides information on environmental/social parameters of products to consumers", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-2", "conditional": False, "paragraph_ref": "P9 Leadership Q1"},
    {"id": "C.P9.L.2", "label": "Whether entity conducts consumer surveys/feedback mechanisms", "data_type": "boolean", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_9", "esrs_ref": "ESRS S4-2", "conditional": False, "paragraph_ref": "P9 Leadership Q2"},
    {"id": "C.P9.L.3", "label": "Turnover from products/services incorporating social/environmental risks/concerns (%)", "data_type": "percent", "mandatory": False, "core": False, "indicator_type": "leadership", "section": "section_c", "subsection": "principle_9", "esrs_ref": None, "conditional": False, "paragraph_ref": "P9 Leadership Q3"},
]


# ═══════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════

def get_datapoints_stats():
    """Get statistics on the data points list (EFRAG IG 3 style)."""
    total = len(BRSR_DATAPOINTS)
    mandatory = sum(1 for dp in BRSR_DATAPOINTS if dp["mandatory"])
    voluntary = total - mandatory
    core = sum(1 for dp in BRSR_DATAPOINTS if dp["core"])
    conditional = sum(1 for dp in BRSR_DATAPOINTS if dp["conditional"])

    # By data type
    by_type = {}
    for dp in BRSR_DATAPOINTS:
        dt = dp["data_type"]
        by_type[dt] = by_type.get(dt, 0) + 1

    # By section
    by_section = {}
    for dp in BRSR_DATAPOINTS:
        s = dp["section"]
        by_section[s] = by_section.get(s, 0) + 1

    # By principle (section C)
    by_principle = {}
    for dp in BRSR_DATAPOINTS:
        if dp["section"] == "section_c":
            p = dp["subsection"]
            by_principle[p] = by_principle.get(p, 0) + 1

    return {
        "total_datapoints": total,
        "mandatory": mandatory,
        "voluntary": voluntary,
        "core_assurance": core,
        "conditional": conditional,
        "by_data_type": by_type,
        "by_section": by_section,
        "by_principle": by_principle,
        "esrs_mapped": sum(1 for dp in BRSR_DATAPOINTS if dp["esrs_ref"]),
    }


def get_datapoints_by_section(section: str) -> list[dict]:
    """Get all data points for a section."""
    return [dp for dp in BRSR_DATAPOINTS if dp["section"] == section]


def get_datapoints_by_principle(principle: str) -> list[dict]:
    """Get all data points for a principle (e.g. 'principle_6')."""
    return [dp for dp in BRSR_DATAPOINTS if dp["subsection"] == principle]


def get_core_datapoints() -> list[dict]:
    """Get all BRSR Core data points (subject to assurance)."""
    return [dp for dp in BRSR_DATAPOINTS if dp["core"]]


def get_mandatory_datapoints() -> list[dict]:
    """Get all mandatory data points."""
    return [dp for dp in BRSR_DATAPOINTS if dp["mandatory"]]


def get_esrs_mapped_datapoints() -> list[dict]:
    """Get data points that have an ESRS cross-reference."""
    return [dp for dp in BRSR_DATAPOINTS if dp["esrs_ref"]]


def analyze_gaps_v2(extracted_data: dict) -> dict:
    """
    Enhanced gap analysis comparing extracted data against the comprehensive data points list.
    Returns detailed gap analysis with ESRS cross-references.
    """
    # Flatten extracted data keys
    extracted_keys = set()
    for section_key in ["section_a", "section_b", "section_c"]:
        section_data = extracted_data.get(section_key, {})
        if isinstance(section_data, dict):
            extracted_keys.update(section_data.keys())

    mandatory_dps = get_mandatory_datapoints()
    core_dps = get_core_datapoints()

    # Build a mapping from old field IDs to new DP IDs for backward compatibility
    # This allows matching extracted keys against BRSR_DATAPOINTS
    found_mandatory = []
    missing_mandatory = []
    found_core = []
    missing_core = []

    for dp in mandatory_dps:
        # Check if any extracted key matches (fuzzy match on label keywords)
        dp_id_lower = dp["id"].lower().replace(".", "_")
        if dp_id_lower in extracted_keys or _matches_extracted(dp, extracted_keys):
            found_mandatory.append(dp)
        else:
            missing_mandatory.append(dp)

    for dp in core_dps:
        dp_id_lower = dp["id"].lower().replace(".", "_")
        if dp_id_lower in extracted_keys or _matches_extracted(dp, extracted_keys):
            found_core.append(dp)
        else:
            missing_core.append(dp)

    total_mandatory = len(mandatory_dps)
    total_core = len(core_dps)
    mandatory_score = (len(found_mandatory) / total_mandatory * 100) if total_mandatory > 0 else 0
    core_score = (len(found_core) / total_core * 100) if total_core > 0 else 0

    # Section scores
    section_scores = {}
    for section in ["section_a", "section_b", "section_c"]:
        section_dps = [dp for dp in mandatory_dps if dp["section"] == section]
        section_found = sum(1 for dp in section_dps if _matches_extracted(dp, extracted_keys))
        section_scores[section] = {
            "total": len(section_dps),
            "found": section_found,
            "score": round(section_found / len(section_dps) * 100, 1) if section_dps else 0,
        }

    # Priority recommendations with ESRS references
    recommendations = []
    for dp in missing_core[:12]:
        rec = {
            "field_id": dp["id"],
            "label": dp["label"],
            "priority": "HIGH",
            "reason": "Required for BRSR Core assurance",
            "data_type": dp["data_type"],
        }
        if dp["esrs_ref"]:
            rec["esrs_ref"] = dp["esrs_ref"]
        recommendations.append(rec)

    for dp in missing_mandatory[:8]:
        if dp not in missing_core:
            rec = {
                "field_id": dp["id"],
                "label": dp["label"],
                "priority": "MEDIUM",
                "reason": "Mandatory BRSR disclosure",
                "data_type": dp["data_type"],
            }
            if dp["esrs_ref"]:
                rec["esrs_ref"] = dp["esrs_ref"]
            recommendations.append(rec)

    return {
        "overall_compliance": round(mandatory_score, 1),
        "core_compliance": round(core_score, 1),
        "total_fields": total_mandatory,
        "fields_found": len(found_mandatory),
        "fields_missing": len(missing_mandatory),
        "core_total": total_core,
        "core_found": len(found_core),
        "core_missing": len(missing_core),
        "section_scores": section_scores,
        "missing_mandatory": [{"id": dp["id"], "label": dp["label"], "core": dp["core"], "data_type": dp["data_type"], "esrs_ref": dp["esrs_ref"]} for dp in missing_mandatory],
        "missing_core": [{"id": dp["id"], "label": dp["label"], "esrs_ref": dp["esrs_ref"]} for dp in missing_core],
        "recommendations": recommendations[:20],
    }


def _matches_extracted(dp: dict, extracted_keys: set) -> bool:
    """Check if a data point was captured in extracted keys (fuzzy matching)."""
    # Generate possible key variants from the data point
    label_lower = dp["label"].lower()

    for key in extracted_keys:
        key_lower = key.lower().replace("_", " ")
        # Check for significant keyword overlap
        dp_words = set(w for w in label_lower.split() if len(w) > 3)
        key_words = set(w for w in key_lower.split() if len(w) > 3)
        if dp_words and key_words:
            overlap = dp_words & key_words
            if len(overlap) >= min(2, len(dp_words)):
                return True
    return False
