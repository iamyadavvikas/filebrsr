import re
from typing import Any

# BRSR Section A - General Disclosures
SECTION_A_PATTERNS = {
    "cin": r"(?:CIN|Corporate\s+Identity\s+Number)[:\s]*([A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})",
    "company_name": r"(?:Name\s+of\s+the\s+Listed\s+Entity|Company\s+Name)[:\s]*([A-Za-z\s&.,()]+?)(?:\n|$)",
    "year_of_incorporation": r"(?:Year\s+of\s+incorporation|Date\s+of\s+Incorporation)[:\s]*(\d{4})",
    "registered_office": r"(?:Registered\s+office\s+address|Registered\s+Address)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
    "corporate_office": r"(?:Corporate\s+address|Corporate\s+office)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
    "email": r"(?:E-?mail|Email\s+ID)[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
    "telephone": r"(?:Telephone|Phone|Contact\s+No)[:\s]*([\d\s\-+()]+)",
    "website": r"(?:Website|Web)[:\s]*((?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*)",
    "financial_year": r"(?:Financial\s+year|FY|F\.Y\.)[:\s]*(\d{4}[-–]\d{2,4})",
    "stock_exchange": r"(?:Stock\s+Exchange|Listed\s+on|Listed\s+at)[:\s]*((?:BSE|NSE|(?:Bombay|National)\s+Stock\s+Exchange)[^\n]*)",
    "paid_up_capital": r"(?:Paid[- ]up\s+(?:Share\s+)?Capital|Authorized\s+Capital)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "turnover": r"(?:Turnover|Revenue\s+from\s+Operations|Net\s+Revenue)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "employees_permanent": r"(?:Permanent\s+[Ee]mployees|No\.?\s+of\s+permanent\s+employees)[:\s]*(\d[\d,]*)",
    "employees_contract": r"(?:Contract(?:ual)?\s+[Ee]mployees|Workers\s+on\s+contract)[:\s]*(\d[\d,]*)",
    "women_employees_pct": r"(?:Women\s+[Ee]mployees|Female\s+employees)[:\s]*(\d+(?:\.\d+)?)\s*%",
}

# BRSR Section B - Management and Process Disclosures
SECTION_B_PATTERNS = {
    "policy_available": r"(?:Policy\s+available|Whether\s+.*policy)[:\s]*(Yes|No|Y|N)",
    "policy_approved_by_board": r"(?:Approved\s+by\s+the\s+Board|Board\s+approved)[:\s]*(Yes|No|Y|N)",
    "policy_web_link": r"(?:Web\s*[Ll]ink|Policy\s+link|URL)[:\s]*(https?://[^\s]+)",
    "grievance_mechanism": r"(?:Grievance\s+[Rr]edressal\s+[Mm]echanism|Stakeholder\s+grievance)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
}

# BRSR Section C - Principle-wise Performance
SECTION_C_PATTERNS = {
    # Principle 1 - Ethics
    "code_of_conduct": r"(?:Code\s+of\s+[Cc]onduct|Ethics\s+[Pp]olicy)[:\s]*(Yes|No|Available|[\s\S]+?)(?:\n\n|\d+\.)",
    "anti_corruption_policy": r"(?:Anti[- ]corruption|Anti[- ]bribery)[:\s]*(Yes|No|Available|[\s\S]+?)(?:\n\n|\d+\.)",
    "complaints_ethics": r"(?:Complaints?\s+.*ethics|Ethical\s+complaints?)[:\s]*(\d+)",
    # Principle 2 - Products
    "r_and_d_spend": r"(?:R&D|Research\s+and\s+Development)\s+(?:spend|expenditure|investment)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "sustainable_sourcing_pct": r"(?:Sustainable\s+sourcing|Sustainably\s+sourced)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "recycled_input_pct": r"(?:Recycled\s+(?:or\s+reused\s+)?input|Recycled\s+materials?)[:\s]*(\d+(?:\.\d+)?)\s*%",
    # Principle 3 - Employee Wellbeing
    "employee_turnover_rate": r"(?:Employee\s+turnover\s+rate|Attrition\s+rate)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "safety_incidents": r"(?:Safety\s+incidents?|LTIFR|Lost\s+[Tt]ime\s+[Ii]njury)[:\s]*(\d+(?:\.\d+)?)",
    "training_hours_per_employee": r"(?:Training\s+hours?\s+per\s+employee|Average\s+training)[:\s]*(\d+(?:\.\d+)?)",
    "median_salary_male": r"(?:Median\s+.*salary.*male|Male\s+median\s+(?:remuneration|salary))[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "median_salary_female": r"(?:Median\s+.*salary.*female|Female\s+median\s+(?:remuneration|salary))[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    # Principle 4 - Stakeholder Engagement
    "stakeholder_groups_identified": r"(?:Stakeholder\s+groups?\s+identified|Key\s+stakeholders?)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
    # Principle 5 - Human Rights
    "human_rights_training_pct": r"(?:Human\s+rights?\s+training|Training\s+on\s+human\s+rights?)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "child_labor_complaints": r"(?:Child\s+labo[u]?r\s+complaints?|Child\s+labo[u]?r)[:\s]*(\d+)",
    # Principle 6 - Environment
    "energy_consumption_total": r"(?:Total\s+energy\s+consumption|Energy\s+consumed)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:GJ|TJ|MWh|kWh)",
    "renewable_energy_pct": r"(?:Renewable\s+energy|Energy\s+from\s+renewable)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "water_withdrawal": r"(?:Total\s+water\s+withdrawal|Water\s+consumed|Water\s+consumption)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:KL|ML|m3|cubic)",
    "ghg_scope1": r"(?:Scope\s*1\s+emissions?|Direct\s+emissions?)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|tonnes?\s+CO2)",
    "ghg_scope2": r"(?:Scope\s*2\s+emissions?|Indirect\s+emissions?)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|tonnes?\s+CO2)",
    "waste_generated": r"(?:Total\s+waste\s+generated|Waste\s+generated)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:MT|tonnes?|kg)",
    "waste_recycled_pct": r"(?:Waste\s+recycled|Recycling\s+rate)[:\s]*(\d+(?:\.\d+)?)\s*%",
    # Principle 7 - Policy Advocacy
    "trade_associations": r"(?:Trade\s+(?:and\s+industry\s+)?(?:associations?|chambers?|bodies))[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
    # Principle 8 - Inclusive Growth
    "csr_spend": r"(?:CSR\s+(?:spend|expenditure|amount)|Corporate\s+Social\s+Responsibility\s+spend)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "community_beneficiaries": r"(?:Beneficiaries?\s+from\s+CSR|Community\s+beneficiaries?|Number\s+of\s+beneficiaries?)[:\s]*([\d,]+)",
    # Principle 9 - Consumer
    "consumer_complaints": r"(?:Consumer\s+complaints?\s+received|Customer\s+complaints?)[:\s]*(\d[\d,]*)",
    "data_privacy_complaints": r"(?:Data\s+privacy\s+complaints?|Cyber\s+security\s+complaints?)[:\s]*(\d+)",
    "product_recalls": r"(?:Product\s+recalls?|Number\s+of\s+recalls?)[:\s]*(\d+)",
}


def extract_with_regex(text: str) -> dict[str, Any]:
    """Extract BRSR metrics from text using regex patterns."""
    results: dict[str, Any] = {}

    all_patterns = {
        "section_a": SECTION_A_PATTERNS,
        "section_b": SECTION_B_PATTERNS,
        "section_c": SECTION_C_PATTERNS,
    }

    for section, patterns in all_patterns.items():
        results[section] = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                results[section][key] = value

    return results


def calculate_confidence(regex_results: dict, ai_results: dict) -> dict[str, float]:
    """Calculate confidence scores by comparing regex and AI extraction."""
    confidence: dict[str, float] = {}

    for section in regex_results:
        if section not in ai_results:
            continue
        for key in regex_results[section]:
            if key in ai_results.get(section, {}):
                regex_val = str(regex_results[section][key]).strip().lower()
                ai_val = str(ai_results[section].get(key, "")).strip().lower()
                if regex_val == ai_val:
                    confidence[f"{section}.{key}"] = 0.95
                elif regex_val in ai_val or ai_val in regex_val:
                    confidence[f"{section}.{key}"] = 0.75
                else:
                    confidence[f"{section}.{key}"] = 0.5
            else:
                confidence[f"{section}.{key}"] = 0.6

    return confidence
