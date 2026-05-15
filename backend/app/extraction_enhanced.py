"""
Enhanced BRSR extraction engine trained on NIFTY 50 report patterns.
Uses section detection, table parsing, and multi-pattern matching for higher accuracy.
"""
import re
from typing import Any


def extract_enhanced(text: str) -> dict[str, Any]:
    """
    Enhanced extraction using NIFTY 50 filing patterns.
    Splits text into sections first, then applies targeted patterns.
    """
    # Step 1: Identify section boundaries
    sections_text = split_into_sections(text)
    
    results = {"section_a": {}, "section_b": {}, "section_c": {}}
    
    # Step 2: Extract from each section with section-specific patterns
    results["section_a"] = extract_section_a(sections_text.get("section_a", text))
    results["section_b"] = extract_section_b(sections_text.get("section_b", text))
    results["section_c"] = extract_section_c(sections_text.get("section_c", text))
    
    # Step 3: Extract tables (common in BRSR)
    table_data = extract_tables(text)
    for section in results:
        results[section].update(table_data.get(section, {}))
    
    return results


def split_into_sections(text: str) -> dict[str, str]:
    """Split BRSR text into Section A, B, C using standard markers."""
    sections = {}
    
    # Find section boundaries
    section_a_match = re.search(
        r"(?:SECTION\s+A|I\.\s*Details\s+of\s+the\s+[Ll]isted)", text, re.IGNORECASE
    )
    section_b_match = re.search(
        r"(?:SECTION\s+B|MANAGEMENT\s+AND\s+PROCESS\s+DISCLOSURES)", text, re.IGNORECASE
    )
    section_c_match = re.search(
        r"(?:SECTION\s+C|PRINCIPLE\s+WISE\s+PERFORMANCE)", text, re.IGNORECASE
    )
    
    if section_a_match and section_b_match:
        sections["section_a"] = text[section_a_match.start():section_b_match.start()]
    elif section_a_match:
        sections["section_a"] = text[section_a_match.start():]
    
    if section_b_match and section_c_match:
        sections["section_b"] = text[section_b_match.start():section_c_match.start()]
    elif section_b_match:
        sections["section_b"] = text[section_b_match.start():]
    
    if section_c_match:
        sections["section_c"] = text[section_c_match.start():]
    
    return sections


def extract_section_a(text: str) -> dict[str, str]:
    """Extract Section A - General Disclosures with enhanced patterns."""
    data = {}
    
    patterns = {
        "cin": [
            r"(?:CIN|Corporate\s+Identity\s+Number)[:\s]*([A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})",
            r"([A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})",
        ],
        "company_name": [
            r"(?:Name\s+of\s+the\s+Listed\s+Entity|Name\s+of\s+the\s+Company)[:\s]*([A-Za-z\s&.,()]+?)(?:\n|$)",
            r"(?:^|\n)([A-Z][A-Za-z\s&]+(?:Limited|Ltd\.?))\s*\n",
        ],
        "financial_year": [
            r"(?:Financial\s+[Yy]ear|FY|F\.Y\.)[:\s]*(\d{4}[-–]\d{2,4})",
            r"(?:Reporting\s+[Pp]eriod|Year\s+of\s+[Rr]eporting)[:\s]*(\d{4}[-–]\d{2,4})",
            r"FY\s*(\d{4}[-–]\d{2})",
        ],
        "reporting_boundary": [
            r"(?:Reporting\s+[Bb]oundary)[:\s]*(Standalone|Consolidated|Both)",
            r"(?:on\s+a\s+)(standalone|consolidated)\s+basis",
        ],
        "registered_office": [
            r"(?:Registered\s+[Oo]ffice\s+[Aa]ddress|Regd\.\s+Office)[:\s]*([\s\S]{20,200}?)(?:\n\s*\n|\d+\.|\n[A-Z])",
        ],
        "email": [
            r"(?:E-?mail|Email\s+(?:ID|address))[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        ],
        "website": [
            r"(?:Website|Web\s*Link)[:\s]*((?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*)",
        ],
        "paid_up_capital": [
            r"(?:Paid[- ]up\s+(?:Share\s+)?Capital)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:Crore|Cr|Lakh)?",
            r"(?:Paid[- ]up\s+Capital)[:\s]*([\d,]+(?:\.\d+)?)",
        ],
        "turnover": [
            r"(?:Turnover|Revenue\s+from\s+[Oo]perations|Total\s+Revenue)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:Crore|Cr)",
            r"(?:Turnover)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:Crore|Cr)",
        ],
        "net_worth": [
            r"(?:Net\s+[Ww]orth)[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:Crore|Cr)?",
        ],
        "stock_exchange": [
            r"(?:Stock\s+Exchange|Listed\s+(?:on|at))[:\s]*((?:BSE|NSE|Bombay|National)[^\n]*)",
        ],
        "employees_permanent_male": [
            r"(?:Permanent\s+[Ee]mployees?).*?(?:Male|M)[:\s]*(\d[\d,]*)",
            r"Male.*?Permanent.*?(\d[\d,]*)",
        ],
        "employees_permanent_female": [
            r"(?:Permanent\s+[Ee]mployees?).*?(?:Female|F)[:\s]*(\d[\d,]*)",
            r"Female.*?Permanent.*?(\d[\d,]*)",
        ],
        "women_board_pct": [
            r"(?:Women\s+(?:on\s+)?Board)[:\s]*(\d+(?:\.\d+)?)\s*%",
            r"(?:Board\s+of\s+Directors).*?(?:Women|Female)[:\s]*(\d+(?:\.\d+)?)\s*%",
        ],
        "csr_applicable": [
            r"(?:CSR\s+applicable|Section\s+135\s+applicable)[:\s]*(Yes|No)",
        ],
    }
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                data[key] = match.group(1).strip()
                break
    
    # Employee count extraction from tables
    employee_patterns = [
        # Pattern: "Permanent Employees ... 5000 ... 2000 ... 7000"
        (r"Permanent\s+[Ee]mployees\D*?(\d[\d,]*)\D+?(\d[\d,]*)\D+?(\d[\d,]*)", 
         "employees_permanent_male", "employees_permanent_female", "employees_permanent_total"),
        (r"Permanent\s+[Ww]orkers\D*?(\d[\d,]*)\D+?(\d[\d,]*)\D+?(\d[\d,]*)",
         "workers_permanent_male", "workers_permanent_female", "workers_permanent_total"),
    ]
    
    for pattern, key_m, key_f, key_t in employee_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data.setdefault(key_m, match.group(1).strip())
            data.setdefault(key_f, match.group(2).strip())
            data.setdefault(key_t, match.group(3).strip())
    
    return data


def extract_section_b(text: str) -> dict[str, str]:
    """Extract Section B - Management and Process Disclosures."""
    data = {}
    
    # Policy matrix - typically a Yes/No table across P1-P9
    policy_patterns = {
        "policy_available": [
            r"(?:policy.*?cover|policy\s+available).*?(Yes|No|Y|N)",
            r"(?:Whether.*?policy)[:\s]*(Yes|No)",
        ],
        "policy_board_approved": [
            r"(?:Board\s+approv|Approved\s+by.*?Board).*?(Yes|No|Y|N)",
        ],
        "policy_web_link": [
            r"(?:Web\s*[Ll]ink|Policy.*?URL|available\s+at)[:\s]*(https?://[^\s]+)",
        ],
        "policy_translated_to_procedures": [
            r"(?:translated\s+into\s+procedures|operationali[sz]ed).*?(Yes|No|Y|N)",
        ],
        "policy_extends_value_chain": [
            r"(?:extend.*?value\s+chain|cover.*?supply\s+chain).*?(Yes|No|Y|N)",
        ],
        "sustainability_committee": [
            r"(?:(?:CSR|Sustainability|ESG)\s+Committee|Board.*?Committee.*?sustainability)[:\s]*([\w\s]+Committee[^\n]*)",
            r"(?:Committee.*?responsible)[:\s]*([\w\s]+)",
        ],
        "ngrbc_review_frequency": [
            r"(?:review.*?(annually|quarterly|half-yearly|periodically))",
        ],
    }
    
    for key, pattern_list in policy_patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                data[key] = match.group(1).strip()
                break
    
    return data


def extract_section_c(text: str) -> dict[str, str]:
    """Extract Section C - Principle-wise Performance Disclosures."""
    data = {}
    
    # Principle 1 - Ethics
    p1_patterns = {
        "anti_corruption_policy": [
            r"(?:anti[- ]corruption|anti[- ]bribery)\s+(?:policy|code).*?(Yes|No|Available|in\s+place)",
            r"(?:Does\s+the\s+entity\s+have\s+an\s+anti[- ]corruption).*?(Yes|No)",
        ],
        "fines_penalties_amount": [
            r"(?:(?:Fine|Penalty|Penalt)(?:ies|y)?.*?(?:NFRA|SEBI|RBI|CPCB|Court))[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)",
            r"(?:Monetary\s+fines|Penalty\s+amount)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)",
        ],
        "fines_penalties_count": [
            r"(?:Number\s+of.*?(?:fines|penalties|punishment))[:\s]*(\d+)",
            r"(?:fines?|penalt(?:y|ies)).*?(\d+)\s*(?:case|instance|occasion)",
        ],
    }
    
    # Principle 2 - Products
    p2_patterns = {
        "sustainable_sourcing": [
            r"(?:sustainable\s+sourcing|sustainably\s+sourced)[:\s]*(Yes|No|\d+(?:\.\d+)?%?)",
        ],
        "sustainable_sourcing_pct": [
            r"(?:sustainable\s+sourcing|sustainably\s+sourced).*?(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%.*?(?:sustainable|sustainably)\s+(?:source|procure)",
        ],
        "recycled_input_pct": [
            r"(?:[Rr]ecycled.*?input|[Rr]ecycled.*?material).*?(\d+(?:\.\d+)?)\s*%",
        ],
    }
    
    # Principle 3 - Employees
    p3_patterns = {
        "health_safety_system": [
            r"(?:occupational\s+health.*?safety\s+(?:management\s+)?system|OHS\s+system|ISO\s+45001)[:\s]*(Yes|No|Implemented|Available|in\s+place)",
        ],
        "ltifr_employees": [
            r"(?:LTIFR|Lost\s+Time\s+Injury\s+Frequency\s+Rate).*?[Ee]mployees?[:\s]*(\d+(?:\.\d+)?)",
            r"[Ee]mployees?.*?(?:LTIFR|Lost\s+Time)[:\s]*(\d+(?:\.\d+)?)",
        ],
        "ltifr_workers": [
            r"(?:LTIFR|Lost\s+Time\s+Injury\s+Frequency\s+Rate).*?[Ww]orkers?[:\s]*(\d+(?:\.\d+)?)",
            r"[Ww]orkers?.*?(?:LTIFR|Lost\s+Time)[:\s]*(\d+(?:\.\d+)?)",
        ],
        "fatalities_employees": [
            r"(?:Fatalit(?:y|ies)).*?[Ee]mployees?[:\s]*(\d+)",
            r"[Ee]mployees?.*?[Ff]atalit[:\s]*(\d+)",
        ],
        "fatalities_workers": [
            r"(?:Fatalit(?:y|ies)).*?[Ww]orkers?[:\s]*(\d+)",
        ],
        "training_health_safety_pct": [
            r"(?:[Hh]ealth.*?[Ss]afety\s+training|[Tt]raining.*?[Hh]ealth.*?[Ss]afety).*?(\d+(?:\.\d+)?)\s*%",
        ],
        "training_skill_pct": [
            r"(?:[Ss]kill\s+upgradation|[Ss]kill.*?training).*?(\d+(?:\.\d+)?)\s*%",
        ],
    }
    
    # Principle 5 - Human Rights
    p5_patterns = {
        "minimum_wages_compliance": [
            r"(?:[Mm]inimum\s+[Ww]ages?).*?(Yes|No|100%|All|Compliant)",
            r"(?:Equal\s+to\s+Minimum\s+Wage|More\s+than\s+Minimum\s+Wage).*?(\d+(?:\.\d+)?)\s*%",
        ],
        "median_remuneration_male": [
            r"(?:[Mm]ale.*?[Mm]edian|[Mm]edian.*?[Mm]ale).*?(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)",
        ],
        "median_remuneration_female": [
            r"(?:[Ff]emale.*?[Mm]edian|[Mm]edian.*?[Ff]emale).*?(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)",
        ],
        "sexual_harassment_complaints": [
            r"(?:[Ss]exual\s+[Hh]arassment|POSH).*?(?:[Ff]iled|[Rr]eceived)[:\s]*(\d+)",
        ],
        "child_labor_complaints": [
            r"(?:[Cc]hild\s+[Ll]abo[u]?r).*?(?:[Ff]iled|[Rr]eceived|complaints?)[:\s]*(\d+)",
        ],
    }
    
    # Principle 6 - Environment
    p6_patterns = {
        "energy_consumption_renewable": [
            r"(?:[Rr]enewable.*?(?:energy|sources))[:\s]*([\d,]+(?:\.\d+)?)\s*(?:GJ|TJ)",
            r"(?:Total\s+energy.*?renewable)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:GJ|TJ)",
        ],
        "energy_consumption_nonrenewable": [
            r"(?:[Nn]on-?[Rr]enewable.*?(?:energy|sources))[:\s]*([\d,]+(?:\.\d+)?)\s*(?:GJ|TJ)",
        ],
        "energy_consumption_total": [
            r"(?:[Tt]otal\s+[Ee]nergy\s+[Cc]onsumption)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:GJ|TJ)",
        ],
        "energy_intensity": [
            r"(?:[Ee]nergy\s+[Ii]ntensity)[:\s]*([\d,]+(?:\.\d+)?)",
        ],
        "renewable_energy_pct": [
            r"(?:renewable.*?energy|energy.*?renewable).*?(\d+(?:\.\d+)?)\s*%",
        ],
        "water_withdrawal_total": [
            r"(?:[Tt]otal\s+[Ww]ater\s+[Ww]ithdrawal)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:KL|ML|m3)",
        ],
        "water_consumption_total": [
            r"(?:[Tt]otal\s+[Ww]ater\s+[Cc]onsumption)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:KL|ML)",
        ],
        "water_intensity": [
            r"(?:[Ww]ater\s+[Ii]ntensity)[:\s]*([\d,]+(?:\.\d+)?)",
        ],
        "ghg_scope1": [
            r"(?:Scope\s*1|[Dd]irect\s+[Ee]missions?)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|[Tt]onne)",
            r"Scope\s*1\D*?([\d,]+(?:\.\d+)?)\s*(?:tCO2|MT|[Tt]onne)",
        ],
        "ghg_scope2": [
            r"(?:Scope\s*2|[Ii]ndirect\s+[Ee]missions?)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|[Tt]onne)",
            r"Scope\s*2\D*?([\d,]+(?:\.\d+)?)\s*(?:tCO2|MT|[Tt]onne)",
        ],
        "ghg_scope3": [
            r"(?:Scope\s*3)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|[Tt]onne)",
        ],
        "ghg_intensity": [
            r"(?:GHG\s+[Ii]ntensity|[Ee]mission\s+[Ii]ntensity)[:\s]*([\d,]+(?:\.\d+)?)",
        ],
        "waste_generated_total": [
            r"(?:[Tt]otal\s+[Ww]aste\s+[Gg]enerated)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:MT|[Tt]onne)",
        ],
        "waste_recycled_pct": [
            r"(?:[Ww]aste\s+[Rr]ecycl(?:ed|ing))[:\s]*.*?(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%.*?(?:recycl|recover|reuse)",
        ],
        "hazardous_waste": [
            r"(?:[Hh]azardous\s+[Ww]aste)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:MT|[Tt]onne)",
        ],
    }
    
    # Principle 8 - Inclusive Growth
    p8_patterns = {
        "csr_spend": [
            r"(?:CSR\s+(?:spend|expenditure|amount))[:\s]*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:Crore|Cr|Lakh)?",
        ],
        "input_from_msme_pct": [
            r"(?:MSME|small\s+producers?).*?(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%.*?(?:MSME|small\s+producer|local)",
        ],
        "input_local_pct": [
            r"(?:local|within\s+(?:district|state)).*?(\d+(?:\.\d+)?)\s*%",
        ],
    }
    
    # Principle 9 - Consumer
    p9_patterns = {
        "consumer_complaints_total": [
            r"(?:[Cc]onsumer\s+[Cc]omplaints?|[Cc]ustomer\s+[Cc]omplaints?)[:\s]*(\d[\d,]*)",
        ],
        "data_privacy_complaints": [
            r"(?:[Dd]ata\s+[Pp]rivacy).*?(?:[Rr]eceived|[Ff]iled)[:\s]*(\d+)",
        ],
        "cyber_security_complaints": [
            r"(?:[Cc]yber\s+[Ss]ecurity).*?(?:[Rr]eceived|[Ff]iled)[:\s]*(\d+)",
        ],
        "product_recalls": [
            r"(?:[Pp]roduct\s+[Rr]ecalls?|[Rr]ecall.*?[Pp]roduct)[:\s]*(\d+)",
        ],
        "cybersecurity_policy": [
            r"(?:[Cc]yber\s*[Ss]ecurity.*?[Pp]olicy|[Dd]ata\s+[Pp]rivacy.*?[Pp]olicy)[:\s]*(Yes|No|Available|in\s+place)",
        ],
    }
    
    # Apply all principle patterns
    all_patterns = {}
    all_patterns.update(p1_patterns)
    all_patterns.update(p2_patterns)
    all_patterns.update(p3_patterns)
    all_patterns.update(p5_patterns)
    all_patterns.update(p6_patterns)
    all_patterns.update(p8_patterns)
    all_patterns.update(p9_patterns)
    
    for key, pattern_list in all_patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                data[key] = match.group(1).strip()
                break
    
    return data


def extract_tables(text: str) -> dict[str, dict]:
    """Extract data from common BRSR table patterns."""
    results = {"section_a": {}, "section_b": {}, "section_c": {}}
    
    # Turnover rate table pattern
    turnover_match = re.search(
        r"[Tt]urnover\s+[Rr]ate.*?(?:Male|M)\D*?(\d+(?:\.\d+)?)\s*%.*?(?:Female|F)\D*?(\d+(?:\.\d+)?)\s*%",
        text, re.IGNORECASE | re.DOTALL
    )
    if turnover_match:
        results["section_a"]["turnover_rate_male"] = turnover_match.group(1)
        results["section_a"]["turnover_rate_female"] = turnover_match.group(2)
    
    # Complaints table (common across P3, P5, P9)
    complaint_types = [
        ("working_conditions_complaints", r"[Ww]orking\s+[Cc]onditions?"),
        ("health_safety_complaints", r"[Hh]ealth\s+(?:and|&)\s+[Ss]afety"),
        ("sexual_harassment_complaints", r"[Ss]exual\s+[Hh]arassment"),
        ("discrimination_complaints", r"[Dd]iscrimination"),
        ("child_labor_complaints", r"[Cc]hild\s+[Ll]abo[u]?r"),
        ("forced_labor_complaints", r"[Ff]orced.*?[Ll]abo[u]?r"),
        ("wages_complaints", r"[Ww]ages?"),
    ]
    
    for key, pattern in complaint_types:
        match = re.search(
            pattern + r".*?(?:Filed|Received|Current)[:\s]*(\d+)",
            text, re.IGNORECASE | re.DOTALL
        )
        if match:
            results["section_c"][key] = match.group(1)
    
    return results
