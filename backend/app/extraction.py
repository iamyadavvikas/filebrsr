import re
from typing import Any

import re
from typing import Any
from dataclasses import dataclass

@dataclass
class Pattern:
    """Represents a pattern with metadata for better extraction."""
    pattern: str
    field_name: str
    section: str
    priority: int = 1  # Higher priority patterns are tried first
    flags: int = re.IGNORECASE | re.MULTILINE
    post_process: callable = None

# BRSR Section A - General Disclosures
SECTION_A_PATTERNS = {
    "cin": [
        {
            "pattern": r"(?:CIN|Corporate\s+Identity\s+Number)[:\s]*([A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})",
            "priority": 1
        },
        {
            "pattern": r"CIN[:\s]*([A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})",
            "priority": 2
        }
    ],
    "company_name": [
        {
            "pattern": r"(?:Name\s+of\s+the\s+Listed\s+Entity|Company\s+Name)[:\s]*([A-Za-z\s&.,()]+?)(?:\n|$)",
            "priority": 1
        },
        {
            "pattern": r"(?:^|\n)([A-Z][A-Za-z\s&]+(?:Limited|Ltd\.?))\s*\n",
            "priority": 2
        }
    ],
    "year_of_incorporation": [
        {"pattern": r"(?:Year\s+of\s+incorporation|Date\s+of\s+Incorporation)[:\s]*(\d{4})", "priority": 1}
    ],
    "registered_office": {
        "patterns": [
            r"(?:Registered\s+office\s+address|Registered\s+Address)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
        ],
        "post_process": lambda x: x.strip()[:500]
    },
    "corporate_office": {
        "patterns": [
            r"(?:Corporate\s+address|Corporate\s+office)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
        ]
    },
    "email": {
        "patterns": [
            r"(?:E-?mail|Email\s+ID)[:\s]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        ]
    },
    "telephone": {
        "patterns": [
            r"(?:Telephone|Phone|Contact\s+No)[:\s]*([\d\s\-+()]+)",
        ]
    },
    "website": {
        "patterns": [
            r"(?:Website|Web)[:\s]*((?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+[^\s]*)",
        ]
    },
    "financial_year": {
        "patterns": [
            r"(?:Financial\s+year|FY|F\.Y\.)[:\s]*(\d{4}[-–]\d{2,4})",
            r"(?:Reporting\s+[Pp]eriod|Year\s+of\s+[Rr]eporting)[:\s]*(\d{4}[-–]\d{2,4})",
        ]
    },
    "stock_exchange": {
        "patterns": [
            r"(?:Stock\s+Exchange|Listed\s+on|Listed\s+at)[:\s]*((?:BSE|NSE|(?:Bombay|National)\s+Stock\s+Exchange)[^\n]*)",
        ]
    },
    "paid_up_capital": {
        "patterns": [
            r"(?:Paid[- ]up\s+(?:Share\s+)?Capital|Authorized\s+Capital)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
        ],
        "post_process": lambda x: x.replace(",", "").replace(",", "")
    },
    "turnover": {
        "patterns": [
            r"(?:Turnover|Revenue\s+from\s+Operations|Net\s+Revenue|Net\s+sales|Revenue|Income\s+from\s+operations)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
        ],
        "post_process": lambda x: x.replace(",", "").replace(",", "")
    },
    "paid_up_capital": {
        "patterns": [
            r"(?:Paid[- ]up\s+(?:Share\s+)?Capital|Authorized\s+Capital)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
        ],
        "post_process": lambda x: x.replace(",", "").replace(",", "")
    },
    "turnover": {
        "patterns": [
            r"(?:Turnover|Revenue\s+from\s+Operations|Net\s+Revenue|Net\s+sales|Revenue|Income\s+from\s+operations)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
        ],
        "post_process": lambda x: x.replace(",", "").replace(",", "")
    },
    "net_worth": {
        "patterns": [
            r"(?:Net\s+[Ww]orth|Networth)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
        ]
    },
    "employees_permanent": {
        "patterns": [
            r"(?:Permanent\s+[Ee]mployees|No\.?\s+of\s+permanent\s+employees|Permanent\s+headcount|Employees?\s+on\s+rolls?)[:\s]*(\d[\d,]*)",
        ]
    },
    "employees_contract": {
        "patterns": [
            r"(?:Contract(?:ual)?\s+[Ee]mployees|Workers\s+on\s+contract)[:\s]*(\d[\d,]*)",
        ]
    },
    "women_employees_pct": {
        "patterns": [
            r"(?:Women\s+[Ee]mployees|Female\s+employees)[:\s]*(\d+(?:\.\d+)?)\s*%",
        ]
    },
    # Locations & markets (A.III)
    "plants_national": {
        "patterns": [
            r"(?:Number\s+of\s+plants?(?:\s+in\s+India|\s+\(National\))?|Plants?\s*\(National\))[:\s]*(\d[\d,]*)",
        ]
    },
    "offices_national": {
        "patterns": [
            r"(?:Number\s+of\s+offices?(?:\s+in\s+India|\s+\(National\))?|Offices?\s*\(National\))[:\s]*(\d[\d,]*)",
        ]
    },
    "plants_international": {
        "patterns": [
            r"(?:Number\s+of\s+plants?.*?[Ii]nternational|Plants?\s*\(International\))[:\s]*(\d[\d,]*)",
        ]
    },
    "offices_international": {
        "patterns": [
            r"(?:Number\s+of\s+offices?.*?[Ii]nternational|Offices?\s*\(International\))[:\s]*(\d[\d,]*)",
        ]
    },
    "states_served": {
        "patterns": [
            r"(?:Number\s+of\s+[Ss]tates?(?:\/UTs)?\s+served|States?\s+served|Markets?\s+served.*?[Ss]tates?)[:\s]*(\d[\d,]*)",
        ]
    },
    "countries_served": {
        "patterns": [
            r"(?:Number\s+of\s+countries\s+served|Countries\s+served|Exports?\s+to.*countries)[:\s]*(\d[\d,]*)",
        ]
    },
    "export_contribution_pct": {
        "patterns": [
            r"(?:Contribution\s+of\s+exports?|Exports?\s+as\s+%|Export\s+turnover\s+share)[:\s]*(\d+(?:\.\d+)?)\s*%",
        ]
    },
    # Workforce splits (A.IV)
    "employees_perm_male": {
        "patterns": [
            r"(?:Permanent\s+[Ee]mployees?\s*[-–]\s*Male|Male\s+permanent\s+employees?)[:\s]*(\d[\d,]*)",
        ]
    },
    "employees_perm_female": {
        "patterns": [
            r"(?:Permanent\s+[Ee]mployees?\s*[-–]\s*Female|Female\s+permanent\s+employees?)[:\s]*(\d[\d,]*)",
        ]
    },
    "employees_perm_total": {
        "patterns": [
            r"(?:Permanent\s+[Ee]mployees?\s*[-–]\s*Total|Total\s+permanent\s+employees?)[:\s]*(\d[\d,]*)",
        ]
    },
    "employees_other_male": {
        "patterns": [
            r"(?:Other\s+than\s+permanent\s+[Ee]mployees?\s*[-–]\s*Male)[:\s]*(\d[\d,]*)",
        ]
    },
    "employees_other_female": {
        "patterns": [
            r"(?:Other\s+than\s+permanent\s+[Ee]mployees?\s*[-–]\s*Female)[:\s]*(\d[\d,]*)",
        ]
    },
    "employees_other_total": {
        "patterns": [
            r"(?:Other\s+than\s+permanent\s+[Ee]mployees?\s*[-–]\s*Total)[:\s]*(\d[\d,]*)",
        ]
    },
    "workers_perm_male": {
        "patterns": [
            r"(?:Permanent\s+[Ww]orkers?\s*[-–]\s*Male|Male\s+permanent\s+workers?)[:\s]*(\d[\d,]*)",
        ]
    },
    "workers_perm_female": {
        "patterns": [
            r"(?:Permanent\s+[Ww]orkers?\s*[-–]\s*Female|Female\s+permanent\s+workers?)[:\s]*(\d[\d,]*)",
        ]
    },
    "workers_perm_total": {
        "patterns": [
            r"(?:Permanent\s+[Ww]orkers?\s*[-–]\s*Total|Total\s+permanent\s+workers?)[:\s]*(\d[\d,]*)",
        ]
    },
    # Company economics (A.VI)
    "net_worth": {
        "patterns": [
            r"(?:Net\s+[Ww]orth|Networth)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
        ]
    },
    "csr_applicable": {
        "patterns": [
            r"(?:CSR\s+applicable|CSR\s+under\s+[Ss]ection\s+135|Section\s+135\s+applicable)[:\s]*(Yes|No|Y|N|Applicable|Not\s+Applicable)",
        ]
    },
    # Principle-level grievances (A.VII)
    "principle_complaints_filed": {
        "patterns": [
            r"(?:Complaints?\s+on\s+Principles?\s*\(P1[-–]P9\)|P1-P9\s+complaints?|Grievances?\s+on\s+principles?)[:\s]*(\d[\d,]*)",
        ]
    },
}

# BRSR Section B - Management and Process Disclosures
SECTION_B_PATTERNS = {
    "policy_available": {
        "patterns": [
            r"(?:Policy\s+available|Whether\s+.*policy)[:\s]*(Yes|No|Y|N)",
        ]
    },
    "policy_approved_by_board": {
        "patterns": [
            r"(?:Approved\s+by\s+the\s+Board|Board\s+approved)[:\s]*(Yes|No|Y|N)",
        ]
    },
    "policy_translated_to_procedures": {
        "patterns": [
            r"(?:Policy\s+translated\s+into\s+procedures?|Translated\s+into\s+codes?)[:\s]*(Yes|No|Y|N)",
        ]
    },
    "policy_extends_value_chain": {
        "patterns": [
            r"(?:Policy\s+extends?\s+to\s+value\s+chain|Value\s+chain\s+partners?\s+covered)[:\s]*(Yes|No|Y|N)",
        ]
    },
    "sustainability_in_board_committees": {
        "patterns": [
            r"(?:Sustainability.*[Bb]oard\s+[Cc]ommittees?|Board\s+committees?.*sustainability)[:\s]*(Yes|No|Y|N)",
        ]
    },
    "policy_external_assessment": {
        "patterns": [
            r"(?:Independent\s+assessment.*polic|External\s+evaluation.*polic|Policies?.*externally\s+assessed)[:\s]*(Yes|No|Y|N)",
        ]
    },
    "policy_web_link": {
        "patterns": [
            r"(?:Web\s*[Ll]ink|Policy\s+link|URL)[:\s]*(https?://[^\s]+)",
        ]
    },
    "grievance_mechanism": {
        "patterns": [
            r"(?:Grievance\s+[Rr]edressal\s+[Mm]echanism|Stakeholder\s+grievance)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
        ]
    },
    "policy_web_link": {
        "patterns": [
            r"(?:Web\s*[Ll]ink|Policy\s+link|URL)[:\s]*(https?://[^\s]+)",
        ]
    },
    "grievance_mechanism": {
        "patterns": [
            r"(?:Grievance\s+[Rr]edressal\s+[Mm]echanism|Stakeholder\s+grievance)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
        ]
    },
}

# BRSR Section C - Principle-wise Performance
SECTION_C_PATTERNS = {
    # Principle 1 - Ethics, openness, RPT & concentration
    "code_of_conduct": r"(?:Code\s+of\s+[Cc]onduct|Ethics\s+[Pp]olicy)[:\s]*(Yes|No|Available|[\s\S]+?)(?:\n\n|\d+\.)",
    "anti_corruption_policy": r"(?:Anti[- ]corruption|Anti[- ]bribery)[:\s]*(Yes|No|Available|[\s\S]+?)(?:\n\n|\d+\.)",
    "complaints_ethics": r"(?:Complaints?\s+.*ethics|Ethical\s+complaints?)[:\s]*(\d+)",
    "corruption_incidents": r"(?:Corruption\s+incidents?|Bribery\s+incidents?|Cases?\s+of\s+corruption)[:\s]*(\d[\d,]*)",
    "top10_supplier_concentration_pct": r"(?:Top\s*10\s+suppliers?|Concentration\s+of\s+purchases?.*?top\s*10)[^:\n]*[:\s]*(\d+(?:\.\d+)?)\s*%",
    "top10_customer_concentration_pct": r"(?:Top\s*10\s+customers?|Concentration\s+of\s+sales?.*?top\s*10)[^:\n]*[:\s]*(\d+(?:\.\d+)?)\s*%",
    "trading_house_purchases_pct": r"(?:Purchases?\s+from\s+trading\s+houses?|Trading\s+house\s+share)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "trading_house_count": r"(?:Number\s+of\s+trading\s+houses?|Trading\s+houses?\s+count)[:\s]*(\d[\d,]*)",
    "dealer_sales_pct": r"(?:Sales?\s+to\s+dealers?\/distributors?|Dealer.*share)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "dealer_count": r"(?:Number\s+of\s+dealers?(\/distributors?)?|Dealers?\s+count)[:\s]*(\d[\d,]*)",
    "rpt_purchases_pct": r"(?:Related\s+party\s+purchases?|RPT\s+purchases?|Purchases?\s+with\s+related\s+parties?)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "rpt_sales_pct": r"(?:Related\s+party\s+sales?|RPT\s+sales?|Sales?\s+to\s+related\s+parties?)[:\s]*(\d+(?:\.\d+)?)\s*%",
    # Principle 2 - Products
    "r_and_d_spend": r"(?:R&D|Research\s+and\s+Development)\s+(?:spend|expenditure|investment)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "msme_sourcing_pct": r"(?:MSME\s+sourcing|Sourced\s+from\s+MSMEs?|MSME\s+share)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "sustainable_sourcing_pct": r"(?:Sustainable\s+sourcing|Sustainably\s+sourced)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "recycled_input_pct": r"(?:Recycled\s+(?:or\s+reused\s+)?input|Recycled\s+materials?)[:\s]*(\d+(?:\.\d+)?)\s*%",
    # Principle 3 - Employee Wellbeing
    "employee_turnover_rate": r"(?:Employee\s+turnover\s+rate|Attrition\s+rate)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "safety_incidents": r"(?:Safety\s+incidents?|LTIFR|TRIFR|Lost\s+[Tt]ime\s+[Ii]njury|Total\s+recordable\s+incidents?)[:\s]*(\d+(?:\.\d+)?)",
    "fatalities": r"(?:Fatalities|Number\s+of\s+fatalities|Work-related\s+fatalities)[:\s]*(\d[\d,]*)",
    "ltifr": r"(?:LTIFR|Lost\s+Time\s+Injury\s+Frequency\s+Rate)[^:\n]*[:\s]*(\d+(?:\.\d+)?)",
    "minimum_wage_compliance_pct": r"(?:Minimum\s+wage\s+compliance|Paid\s+minimum\s+wage|Wages?.*minimum\s+wage)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "training_hours_per_employee": r"(?:Training\s+hours?\s+per\s+employee|Average\s+training|Learning\s+hours?\s+per\s+employee|Training\s+man-?hours?)[:\s]*(\d+(?:\.\d+)?)",
    "parental_return_rate_pct": r"(?:Return\s+to\s+work\s+rate|Retention\s+rate.*parental|Parental\s+leave\s+return)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "grievance_mechanism_employees": r"(?:Grievance\s+redressal.*employees?|Employee\s+grievance\s+mechanism)[:\s]*(Yes|No|Y|N|Available)",
    "median_salary_male": r"(?:Median\s+.*salary.*male|Male\s+median\s+(?:remuneration|salary))[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "median_salary_female": r"(?:Median\s+.*salary.*female|Female\s+median\s+(?:remuneration|salary))[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    # Principle 4 - Stakeholder Engagement
    "stakeholder_groups_identified": r"(?:Stakeholder\s+groups?\s+identified|Key\s+stakeholders?)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
    # Principle 5 - Human Rights
    "human_rights_training_pct": r"(?:Human\s+rights?\s+training|Training\s+on\s+human\s+rights?)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "child_labor_complaints": r"(?:Child\s+labo[u]?r\s+complaints?|Child\s+labo[u]?r)[:\s]*(\d+)",
    "posh_filed": r"(?:POSH\s+complaints?\s+filed|Sexual\s+harassment\s+complaints?\s+filed|Complaints?\s+on\s+sexual\s+harassment)[:\s]*(\d[\d,]*)",
    "posh_upheld": r"(?:POSH\s+complaints?\s+upheld|Upheld.*sexual\s+harassment|Sexual\s+harassment.*upheld)[:\s]*(\d[\d,]*)",
    "posh_pct_female": r"(?:POSH\s+complaints?\s+as\s+%|Sexual\s+harassment.*%\s+of\s+female)[:\s]*(\d+(?:\.\d+)?)\s*%",
    # Principle 6 - Environment
    "energy_consumption_total": r"(?:Total\s+energy\s+consumption|Energy\s+consumed)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:GJ|TJ|MWh|kWh)",
    "renewable_energy_pct": r"(?:Renewable\s+energy|Energy\s+from\s+renewable)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "water_withdrawal": r"(?:Total\s+water\s+withdrawal|Water\s+consumed|Water\s+consumption)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:KL|ML|m3|cubic)",
    "water_discharge": r"(?:Water\s+discharged|Wastewater\s+discharge|Effluent\s+discharge)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:KL|ML|m3|cubic)",
    "ghg_scope1": r"(?:Scope\s*1\s+emissions?|Direct\s+emissions?)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|tonnes?\s+CO2)",
    "ghg_scope2": r"(?:Scope\s*2\s+emissions?|Indirect\s+emissions?)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|tonnes?\s+CO2)",
    "ghg_scope3": r"(?:Scope\s*3\s+emissions?|Value\s+chain\s+emissions?)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:tCO2|tCO2e|tonnes?\s+CO2)",
    "ghg_intensity_turnover": r"(?:Scope\s*1\s*\+\s*2\s+intensity|GHG\s+intensity|Emission\s+intensity)[^:\n]*[:\s]*([\d,]+(?:\.\d+)?)",
    "energy_intensity_turnover": r"(?:Energy\s+intensity)[^:\n]*[:\s]*([\d,]+(?:\.\d+)?)",
    "water_intensity_turnover": r"(?:Water\s+intensity)[^:\n]*[:\s]*([\d,]+(?:\.\d+)?)",
    "waste_intensity_turnover": r"(?:Waste\s+intensity)[^:\n]*[:\s]*([\d,]+(?:\.\d+)?)",
    "waste_generated": r"(?:Total\s+waste\s+generated|Waste\s+generated)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:MT|tonnes?|kg)",
    "waste_disposed": r"(?:Waste\s+disposed|Disposal.*waste|Waste\s+to\s+landfill)[:\s]*([\d,]+(?:\.\d+)?)\s*(?:MT|tonnes?|kg)",
    "waste_recycled_pct": r"(?:Waste\s+recycled|Recycling\s+rate)[:\s]*(\d+(?:\.\d+)?)\s*%",
    # Principle 7 - Policy Advocacy
    "trade_associations": r"(?:Trade\s+(?:and\s+industry\s+)?(?:associations?|chambers?|bodies))[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
    # Principle 8 - Inclusive Growth
    "csr_spend": r"(?:CSR\s+(?:spend|expenditure|amount)|Corporate\s+Social\s+Responsibility\s+spend)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "community_beneficiaries": r"(?:Beneficiaries?\s+from\s+CSR|Community\s+beneficiaries?|Number\s+of\s+beneficiaries?)[:\s]*([\d,]+)",
    # Principle 9 - Consumer
    "consumer_complaints": r"(?:Consumer\s+complaints?\s+received|Customer\s+complaints?)[:\s]*(\d[\d,]*)",
    "data_breach_incidents": r"(?:Data\s+breaches?|Personal\s+data\s+breaches?|Customer\s+data\s+breaches?)[:\s]*(\d[\d,]*)",
    "data_privacy_complaints": r"(?:Data\s+privacy\s+complaints?|Cyber\s+security\s+complaints?)[:\s]*(\d+)",
    "product_recalls": r"(?:Product\s+recalls?|Number\s+of\s+recalls?)[:\s]*(\d+)",
}


def extract_with_regex(text: str) -> dict[str, Any]:
    """Extract BRSR metrics from text using regex patterns."""
    results: dict[str, Any] = {}

    all_patterns: dict[str, dict[str, Any]] = {
        "section_a": SECTION_A_PATTERNS,
        "section_b": SECTION_B_PATTERNS,
        "section_c": SECTION_C_PATTERNS,
    }

    for section, section_patterns in all_patterns.items():
        results[section] = {}
        for field_name, pattern_def in section_patterns.items():
            # Handle different pattern formats:
            # 1. String (old format - direct regex)
            # 2. List of dicts with "pattern" key (new format with priority)
            # 3. Dict with "patterns" key containing list of strings or dicts
            
            patterns_to_try: list[dict[str, Any]] = []
            
            if isinstance(pattern_def, str):
                # Old format - single regex string
                patterns_to_try = [{"pattern": pattern_def, "flags": re.IGNORECASE | re.MULTILINE}]
            elif isinstance(pattern_def, list):
                # List of dicts with "pattern" key
                patterns_to_try = pattern_def
            elif isinstance(pattern_def, dict):
                if "patterns" in pattern_def:
                    # Dict with "patterns" key
                    patterns_raw = pattern_def["patterns"]
                    patterns_to_try = []
                    for p in patterns_raw:
                        if isinstance(p, str):
                            patterns_to_try.append({"pattern": p, "flags": re.IGNORECASE | re.MULTILINE})
                        elif isinstance(p, dict) and "pattern" in p:
                            patterns_to_try.append(p)
                else:
                    # Dict without "patterns" - treat as single pattern dict?
                    if "pattern" in pattern_def:
                        patterns_to_try = [pattern_def]
            else:
                continue
            
            # Try each pattern in order (higher priority first if specified)
            patterns_to_try.sort(key=lambda x: x.get("priority", 1), reverse=True)
            
            for pattern_info in patterns_to_try:
                pattern = str(pattern_info.get("pattern", ""))
                flags = int(pattern_info.get("flags", re.IGNORECASE | re.MULTILINE))
                match = re.search(pattern, text, flags)
                if match:
                    value = match.group(1).strip()
                    # Apply post_process if available
                    if isinstance(pattern_def, dict) and "post_process" in pattern_def:
                        post_process = pattern_def["post_process"]
                        if callable(post_process):
                            value = post_process(value)
                    results[section][field_name] = value
                    break  # Use first matching pattern

    return results


def calculate_confidence(
    regex_results: dict,
    ai_results: dict,
    extraction_quality: dict | None = None
) -> dict[str, float]:
    """Calculate confidence scores by comparing regex, AI, and enhanced extraction."""
    confidence: dict[str, float] = {}
    
    all_sections = set(regex_results.keys()) | set(ai_results.keys()) | set(ai_results.keys()) if False else set()
    all_sections = set(regex_results.keys()) | set(ai_results.keys())
    
    for section in all_sections:
        regex_section = regex_results.get(section, {})
        ai_section = ai_results.get(section, {})
        
        all_keys = set(regex_results.get(section, {})) | set(ai_results.get(section, {}))
        
        for key in all_keys:
            regex_val = regex_results.get(section, {}).get(key)
            ai_val = ai_results.get(section, {}).get(key)
            
            if regex_val is not None and ai_val is not None:
                regex_val_str = str(regex_val).strip().lower()
                ai_val_str = str(ai_val).strip().lower()
                
                if regex_val == ai_val:
                    confidence[f"{section}.{key}"] = 0.95
                elif regex_val in ai_val or ai_val in regex_val:
                    confidence[f"{section}.{key}"] = 0.75
                else:
                    confidence[f"{section}.{key}"] = 0.5
            elif regex_val is not None:
                # Only regex found - moderate confidence
                confidence[f"{section}.{key}"] = 0.65
            elif ai_val is not None:
                # Only AI found - moderate confidence
                confidence[f"{section}.{key}"] = 0.6
            else:
                confidence[f"{section}.{key}"] = 0.1
    
    return confidence


def calculate_advanced_confidence(
    regex_results: dict,
    ai_results: dict,
    extraction_quality: dict | None = None
) -> dict[str, float]:
    """
    Enhanced confidence scoring with multiple signals:
    - Pattern match quality
    - Source consistency
    - Value plausibility
    - Cross-field validation
    """
    confidence: dict[str, float] = {}
    
    for section in ["section_a", "section_b", "section_c"]:
        regex_section = regex_results.get(section, {})
        ai_section = ai_results.get(section, {})
        
        all_keys = set(regex_results.get(section, {}).keys()) | set(ai_results.get(section, {}).keys())
        
        for key in all_keys:
            regex_val = regex_results.get(section, {}).get(key)
            ai_val = ai_results.get(section, {}).get(key)
            
            base_confidence = 0.0
            signals = []
            
            # Signal 1: Both regex and AI agree exactly
            regex_val = regex_results.get(section, {}).get(key)
            ai_val = ai_results.get(section, {}).get(key)
            
            if regex_val is not None and ai_val is not None:
                regex_val_norm = str(regex_val).strip().lower()
                ai_val_str = str(ai_val).strip().lower()
                
                if regex_val == ai_val:
                    base = 0.95
                elif regex_val in ai_val or ai_val in regex_val:
                    base = 0.85
                else:
                    base = 0.6
                signals.append(("agreement", base))
            elif regex_val is not None:
                confidence_score = 0.7
                signals.append(("regex_only", confidence_score))
            elif ai_val is not None:
                confidence_score = 0.6
                signals.append(("ai_only", confidence_score))
            else:
                continue
            
            # Signal 2: Value plausibility checks
            value = regex_val or ai_val
            if value:
                if _is_plausible_value(key, value):
                    signals.append(("plausibility", 0.1))
                else:
                    signals.append(("implausibility", -0.15))
            
            # Signal 3: Cross-field validation
            if _cross_validate(key, regex_results, ai_results):
                signals.append(("cross_validation", 0.05))
            
            # Combine signals with weighted average
            total_weight = sum(w for _, w in signals)
            if total_weight > 0:
                final_confidence = sum(score * weight for _, (_, weight) in [(s[0], s[1]) for s in signals]) / total_weight
                # Cap at 0.95
                final_conf = min(0.95, max(0.1, weighted))
                confidence[f"{section}.{key}"] = final_conf
    
    return confidence


def _is_plausible_value(key: str, value: Any) -> bool:
    """Check if a value is plausible for a given field."""
    if value is None:
        return False
    val_str = str(value).strip()
    if not val_str:
        return False
    
    key_lower = key.lower()
    
    # Percentage fields should be 0-100
    if "pct" in key.lower() or "percentage" in key.lower():
        try:
            val = float(str(value).replace(",", "").replace("%", ""))
            return 0 <= val <= 100
        except:
            return False
    
    # Percentage fields
    if "pct" in key.lower() or "percentage" in key.lower():
        try:
            val = float(str(value).replace(",", "").replace("%", ""))
            return 0 <= val <= 100
        except:
            return False
    
    # Percentage fields
    if "pct" in key.lower() or "percentage" in key.lower():
        try:
            val = float(str(value).replace(",", "").replace("%", ""))
            return 0 <= val <= 100
        except:
            return False
    
    # Large monetary values should be reasonable
    if any(k in key.lower() for k in ["turnover", "capital", "worth", "spend", "revenue"]):
        try:
            val = float(str(value).replace(",", "").replace("₹", "").replace("₹", "").replace("Rs", "").replace("INR", ""))
            return val >= 0 and val < 1e15  # Up to 1000 trillion
        except:
            return True  # Allow if parsing fails
    
    # Percentages should be 0-100
    if "pct" in key.lower() or "percentage" in key.lower():
        try:
            val = float(str(value).replace(",", "").replace("%", ""))
            return 0 <= val <= 100
        except:
            return False
    
    # Email format
    if "email" in key.lower():
        return "@" in str(value) and "." in str(value).split("@")[-1]
    
    # CIN format
    if "cin" in key.lower():
        import re
        return bool(re.match(r'^[A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$', str(value).strip()))
    
    return True


def _cross_validate(key: str, regex_results: dict, ai_results: dict) -> bool:
    """Cross-validate extracted values across sections."""
    # Example: turnover in section_a should be consistent with turnover in section_c
    # This is a placeholder for cross-field validation logic
    return True


# Enhanced confidence calculation with multiple signals
def calculate_confidence_enhanced(
    regex_results: dict,
    ai_results: dict,
    retrieval_results: dict = None,
    extraction_quality: dict = None
) -> dict[str, float]:
    """
    Enhanced confidence calculation with multiple signals:
    1. Agreement between extractors (regex, enhanced, AI)
    2. Value plausibility checks
    2. Cross-field validation
    4. Source reliability
    4. Pattern match quality
    """
    confidence: dict[str, float] = {}
    
    all_sections = set()
    for results in [regex_results, ai_results]:
        for section in results:
            all_sections.add(section)
    
    for section in ["section_a", "section_b", "section_c"]:
        regex_section = regex_results.get(section, {})
        ai_section = ai_results.get(section, {})
        
        all_keys = set(regex_results.get(section, {})) | set(ai_results.get(section, {}))
        
        for key in all_keys:
            regex_val = regex_results.get(section, {}).get(key)
            ai_val = ai_results.get(section, {}).get(key)
            
            # Both extractors found a value
            if regex_val is not None and ai_val is not None:
                regex_str = str(regex_val).strip().lower()
                ai_str = str(ai_val).strip().lower()
                
                if regex_val == ai_val:
                    confidence_score = 0.95
                elif regex_val in ai_val or ai_val in regex_val:
                    confidence_score = 0.85
                else:
                    confidence_score = 0.5
            elif regex_val is not None:
                # Only regex found - moderate confidence
                confidence_score = 0.7
            elif ai_val is not None:
                # Only AI found - moderate confidence
                confidence_score = 0.6
            else:
                confidence_score = 0.1
            
            # Plausibility check
            value = regex_val or ai_val
            if not _is_plausible_value(key, regex_val or ai_val):
                confidence_score *= 0.5
            
            # Cross-field validation bonus
            if _cross_validate(key, regex_results, ai_results):
                confidence_score = min(0.95, confidence_score + 0.05)
            
            confidence_score = min(0.95, max(0.1, confidence_score))
            confidence[f"{section}.{key}"] = confidence_score
    
    return confidence


def normalize_extracted_value(key: str, value: Any) -> Any:
    """Normalize extracted values to standard formats."""
    if value is None:
        return None
    
    val = str(value).strip()
    if not val:
        return None
    
    key_lower = key.lower()
    
    # Percentage values - normalize to decimal
    if "pct" in key.lower() or "percentage" in key.lower() or "pct" in key.lower():
        try:
            val = val.replace(",", "").replace("%", "").strip()
            val = float(val)
            return round(val / 100, 4)  # Return as decimal (0.25 for 25%)
        except:
            pass
    
    # Monetary values - normalize to base units
    if any(k in key.lower() for k in ["turnover", "capital", "worth", "spend", "revenue", "income", "income"]):
        # Extract numeric value
        import re
        match = re.search(r'[\d,]+\.?\d*', str(value).replace(",", ""))
        if match:
            try:
                return float(match.group().replace(",", ""))
            except:
                pass
    
    # Normalize CIN
    if "cin" in key.lower():
        return str(value).strip().upper()
    
    # Normalize percentages
    if "pct" in key.lower() or "percentage" in key.lower() or "pct" in key.lower():
        try:
            val = str(value).replace("%", "").replace(",", "").strip()
            val = float(val)
            return round(val / 100, 4)
        except:
            pass
    
    # Normalize monetary values to base units
    if any(k in key.lower() for k in ["turnover", "capital", "worth", "spend", "revenue", "income"]):
        import re
        match = re.search(r'[\d,]+\.?\d*', str(value).replace(",", ""))
        if match:
            try:
                return float(match.group().replace(",", ""))
            except:
                pass
    
    # Clean whitespace
    return val.strip() if val else None
