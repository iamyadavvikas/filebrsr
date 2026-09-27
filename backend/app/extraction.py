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
    # Locations & markets (A.III)
    "plants_national": r"(?:Number\s+of\s+plants?(?:\s+in\s+India|\s+\(National\))?|Plants?\s*\(National\))[:\s]*(\d[\d,]*)",
    "offices_national": r"(?:Number\s+of\s+offices?(?:\s+in\s+India|\s+\(National\))?|Offices?\s*\(National\))[:\s]*(\d[\d,]*)",
    "plants_international": r"(?:Number\s+of\s+plants?.*?[Ii]nternational|Plants?\s*\(International\))[:\s]*(\d[\d,]*)",
    "offices_international": r"(?:Number\s+of\s+offices?.*?[Ii]nternational|Offices?\s*\(International\))[:\s]*(\d[\d,]*)",
    "states_served": r"(?:Number\s+of\s+[Ss]tates(?:\/UTs)?\s+served|States?\s+served|Markets?\s+served.*?[Ss]tates?)[:\s]*(\d[\d,]*)",
    "countries_served": r"(?:Number\s+of\s+countries\s+served|Countries\s+served|Exports?\s+to.*countries)[:\s]*(\d[\d,]*)",
    "export_contribution_pct": r"(?:Contribution\s+of\s+exports?|Exports?\s+as\s+%|Export\s+turnover\s+share)[:\s]*(\d+(?:\.\d+)?)\s*%",
    # Workforce splits (A.IV)
    "employees_perm_male": r"(?:Permanent\s+[Ee]mployees?\s*[-–]\s*Male|Male\s+permanent\s+employees?)[:\s]*(\d[\d,]*)",
    "employees_perm_female": r"(?:Permanent\s+[Ee]mployees?\s*[-–]\s*Female|Female\s+permanent\s+employees?)[:\s]*(\d[\d,]*)",
    "employees_perm_total": r"(?:Permanent\s+[Ee]mployees?\s*[-–]\s*Total|Total\s+permanent\s+employees?)[:\s]*(\d[\d,]*)",
    "employees_other_male": r"(?:Other\s+than\s+permanent\s+[Ee]mployees?\s*[-–]\s*Male)[:\s]*(\d[\d,]*)",
    "employees_other_female": r"(?:Other\s+than\s+permanent\s+[Ee]mployees?\s*[-–]\s*Female)[:\s]*(\d[\d,]*)",
    "employees_other_total": r"(?:Other\s+than\s+permanent\s+[Ee]mployees?\s*[-–]\s*Total)[:\s]*(\d[\d,]*)",
    "workers_perm_male": r"(?:Permanent\s+[Ww]orkers?\s*[-–]\s*Male|Male\s+permanent\s+workers?)[:\s]*(\d[\d,]*)",
    "workers_perm_female": r"(?:Permanent\s+[Ww]orkers?\s*[-–]\s*Female|Female\s+permanent\s+workers?)[:\s]*(\d[\d,]*)",
    "workers_perm_total": r"(?:Permanent\s+[Ww]orkers?\s*[-–]\s*Total|Total\s+permanent\s+workers?)[:\s]*(\d[\d,]*)",
    # Company economics (A.VI)
    "net_worth": r"(?:Net\s+[Ww]orth|Networth)[:\s]*(?:(?:Rs|INR|₹)[.\s]*)?([\d,]+(?:\.\d+)?)",
    "csr_applicable": r"(?:CSR\s+applicable|CSR\s+under\s+[Ss]ection\s+135|Section\s+135\s+applicable)[:\s]*(Yes|No|Y|N|Applicable|Not\s+Applicable)",
    # Principle-level grievances (A.VII)
    "principle_complaints_filed": r"(?:Complaints?\s+on\s+Principles?\s*\(P1[-–]P9\)|P1-P9\s+complaints?|Grievances?\s+on\s+principles?)[:\s]*(\d[\d,]*)",
}

# BRSR Section B - Management and Process Disclosures
SECTION_B_PATTERNS = {
    "policy_available": r"(?:Policy\s+available|Whether\s+.*policy)[:\s]*(Yes|No|Y|N)",
    "policy_approved_by_board": r"(?:Approved\s+by\s+the\s+Board|Board\s+approved)[:\s]*(Yes|No|Y|N)",
    "policy_translated_to_procedures": r"(?:Policy\s+translated\s+into\s+procedures?|Translated\s+into\s+codes?)[:\s]*(Yes|No|Y|N)",
    "policy_extends_value_chain": r"(?:Policy\s+extends?\s+to\s+value\s+chain|Value\s+chain\s+partners?\s+covered)[:\s]*(Yes|No|Y|N)",
    "sustainability_in_board_committees": r"(?:Sustainability.*[Bb]oard\s+[Cc]ommittees?|Board\s+committees?.*sustainability)[:\s]*(Yes|No|Y|N)",
    "policy_external_assessment": r"(?:Independent\s+assessment.*polic|External\s+evaluation.*polic|Policies?.*externally\s+assessed)[:\s]*(Yes|No|Y|N)",
    "policy_web_link": r"(?:Web\s*[Ll]ink|Policy\s+link|URL)[:\s]*(https?://[^\s]+)",
    "grievance_mechanism": r"(?:Grievance\s+[Rr]edressal\s+[Mm]echanism|Stakeholder\s+grievance)[:\s]*([\s\S]+?)(?:\n\n|\d+\.)",
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
    "safety_incidents": r"(?:Safety\s+incidents?|LTIFR|Lost\s+[Tt]ime\s+[Ii]njury)[:\s]*(\d+(?:\.\d+)?)",
    "fatalities": r"(?:Fatalities|Number\s+of\s+fatalities|Work-related\s+fatalities)[:\s]*(\d[\d,]*)",
    "ltifr": r"(?:LTIFR|Lost\s+Time\s+Injury\s+Frequency\s+Rate)[^:\n]*[:\s]*(\d+(?:\.\d+)?)",
    "minimum_wage_compliance_pct": r"(?:Minimum\s+wage\s+compliance|Paid\s+minimum\s+wage|Wages?.*minimum\s+wage)[:\s]*(\d+(?:\.\d+)?)\s*%",
    "training_hours_per_employee": r"(?:Training\s+hours?\s+per\s+employee|Average\s+training)[:\s]*(\d+(?:\.\d+)?)",
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
