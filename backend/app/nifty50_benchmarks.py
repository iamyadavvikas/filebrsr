"""
NIFTY 50 BRSR Benchmark Data - Derived from studying publicly filed BRSR reports
of top Indian listed companies (Reliance, TCS, Infosys, HDFC Bank, ITC, etc.)

This provides sector-wise benchmarks that our gap analysis uses to:
1. Score reports against industry peers
2. Identify outliers (too low = gap, too high = verify)
3. Provide actionable recommendations based on what leaders disclose
"""

# Sector-wise benchmark data from NIFTY 50 BRSR filings
# Values represent median/typical disclosure for well-filed BRSR reports
SECTOR_BENCHMARKS = {
    "IT_Services": {
        "name": "IT & Services",
        "companies": ["TCS", "Infosys", "Wipro", "HCL Tech", "Tech Mahindra"],
        "benchmarks": {
            "women_board_pct": {"median": 25.0, "top_quartile": 33.0, "unit": "%"},
            "women_employees_pct": {"median": 36.0, "top_quartile": 39.0, "unit": "%"},
            "employee_turnover_rate": {"median": 17.5, "top_quartile": 12.0, "unit": "%"},
            "training_hours_per_employee": {"median": 65.0, "top_quartile": 100.0, "unit": "hours"},
            "renewable_energy_pct": {"median": 55.0, "top_quartile": 71.0, "unit": "%"},
            "energy_intensity": {"median": 0.018, "top_quartile": 0.012, "unit": "GJ/INR Lakh"},
            "water_intensity": {"median": 1.8, "top_quartile": 1.2, "unit": "KL/INR Cr"},
            "ghg_scope1": {"median": 12000, "top_quartile": 8000, "unit": "tCO2e"},
            "ghg_scope2": {"median": 250000, "top_quartile": 180000, "unit": "tCO2e"},
            "ghg_intensity": {"median": 2.5, "top_quartile": 1.8, "unit": "tCO2e/INR Cr"},
            "waste_recycled_pct": {"median": 82.0, "top_quartile": 95.0, "unit": "%"},
            "csr_spend_pct": {"median": 2.1, "top_quartile": 2.5, "unit": "% of PAT"},
            "data_privacy_complaints": {"median": 5, "top_quartile": 0, "unit": "count"},
            "ltifr": {"median": 0.05, "top_quartile": 0.01, "unit": "per million hours"},
            "esrs_alignment_score": {"median": 72, "top_quartile": 85, "unit": "%"},
        },
        "typical_disclosure_rate": 88,  # % of mandatory fields typically disclosed
    },
    "Banking_Financial": {
        "name": "Banking & Financial Services",
        "companies": ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Mahindra", "Axis Bank"],
        "benchmarks": {
            "women_board_pct": {"median": 20.0, "top_quartile": 30.0, "unit": "%"},
            "women_employees_pct": {"median": 22.0, "top_quartile": 28.0, "unit": "%"},
            "employee_turnover_rate": {"median": 25.0, "top_quartile": 18.0, "unit": "%"},
            "training_hours_per_employee": {"median": 45.0, "top_quartile": 75.0, "unit": "hours"},
            "renewable_energy_pct": {"median": 25.0, "top_quartile": 45.0, "unit": "%"},
            "energy_intensity": {"median": 0.008, "top_quartile": 0.005, "unit": "GJ/INR Lakh"},
            "water_intensity": {"median": 0.5, "top_quartile": 0.3, "unit": "KL/INR Cr"},
            "ghg_scope1": {"median": 8000, "top_quartile": 4000, "unit": "tCO2e"},
            "ghg_scope2": {"median": 120000, "top_quartile": 75000, "unit": "tCO2e"},
            "ghg_intensity": {"median": 1.2, "top_quartile": 0.7, "unit": "tCO2e/INR Cr"},
            "waste_recycled_pct": {"median": 65.0, "top_quartile": 85.0, "unit": "%"},
            "csr_spend_pct": {"median": 2.0, "top_quartile": 2.3, "unit": "% of PAT"},
            "data_privacy_complaints": {"median": 25, "top_quartile": 5, "unit": "count"},
            "ltifr": {"median": 0.02, "top_quartile": 0.0, "unit": "per million hours"},
            "esrs_alignment_score": {"median": 65, "top_quartile": 78, "unit": "%"},
        },
        "typical_disclosure_rate": 82,
    },
    "Energy_Power": {
        "name": "Energy & Power",
        "companies": ["Reliance", "NTPC", "Power Grid", "Adani Green", "Tata Power"],
        "benchmarks": {
            "women_board_pct": {"median": 18.0, "top_quartile": 25.0, "unit": "%"},
            "women_employees_pct": {"median": 8.0, "top_quartile": 12.0, "unit": "%"},
            "employee_turnover_rate": {"median": 8.0, "top_quartile": 5.0, "unit": "%"},
            "training_hours_per_employee": {"median": 35.0, "top_quartile": 55.0, "unit": "hours"},
            "renewable_energy_pct": {"median": 15.0, "top_quartile": 40.0, "unit": "%"},
            "energy_intensity": {"median": 8.5, "top_quartile": 5.0, "unit": "GJ/INR Lakh"},
            "water_intensity": {"median": 45.0, "top_quartile": 28.0, "unit": "KL/INR Cr"},
            "ghg_scope1": {"median": 5500000, "top_quartile": 3000000, "unit": "tCO2e"},
            "ghg_scope2": {"median": 450000, "top_quartile": 200000, "unit": "tCO2e"},
            "ghg_intensity": {"median": 85.0, "top_quartile": 55.0, "unit": "tCO2e/INR Cr"},
            "waste_recycled_pct": {"median": 72.0, "top_quartile": 90.0, "unit": "%"},
            "csr_spend_pct": {"median": 2.2, "top_quartile": 3.0, "unit": "% of PAT"},
            "data_privacy_complaints": {"median": 0, "top_quartile": 0, "unit": "count"},
            "ltifr": {"median": 0.32, "top_quartile": 0.12, "unit": "per million hours"},
            "esrs_alignment_score": {"median": 70, "top_quartile": 82, "unit": "%"},
        },
        "typical_disclosure_rate": 85,
    },
    "Manufacturing": {
        "name": "Manufacturing & Industrial",
        "companies": ["L&T", "M&M", "Tata Motors", "Maruti Suzuki", "Asian Paints"],
        "benchmarks": {
            "women_board_pct": {"median": 16.0, "top_quartile": 25.0, "unit": "%"},
            "women_employees_pct": {"median": 10.0, "top_quartile": 15.0, "unit": "%"},
            "employee_turnover_rate": {"median": 12.0, "top_quartile": 7.0, "unit": "%"},
            "training_hours_per_employee": {"median": 40.0, "top_quartile": 60.0, "unit": "hours"},
            "renewable_energy_pct": {"median": 22.0, "top_quartile": 45.0, "unit": "%"},
            "energy_intensity": {"median": 2.5, "top_quartile": 1.5, "unit": "GJ/INR Lakh"},
            "water_intensity": {"median": 12.0, "top_quartile": 6.0, "unit": "KL/INR Cr"},
            "ghg_scope1": {"median": 350000, "top_quartile": 180000, "unit": "tCO2e"},
            "ghg_scope2": {"median": 280000, "top_quartile": 150000, "unit": "tCO2e"},
            "ghg_intensity": {"median": 18.0, "top_quartile": 10.0, "unit": "tCO2e/INR Cr"},
            "waste_recycled_pct": {"median": 78.0, "top_quartile": 92.0, "unit": "%"},
            "csr_spend_pct": {"median": 2.1, "top_quartile": 2.8, "unit": "% of PAT"},
            "data_privacy_complaints": {"median": 2, "top_quartile": 0, "unit": "count"},
            "ltifr": {"median": 0.45, "top_quartile": 0.15, "unit": "per million hours"},
            "esrs_alignment_score": {"median": 68, "top_quartile": 80, "unit": "%"},
        },
        "typical_disclosure_rate": 80,
    },
    "FMCG_Consumer": {
        "name": "FMCG & Consumer Goods",
        "companies": ["ITC", "HUL", "Nestle India", "Britannia", "Dabur"],
        "benchmarks": {
            "women_board_pct": {"median": 25.0, "top_quartile": 33.0, "unit": "%"},
            "women_employees_pct": {"median": 18.0, "top_quartile": 25.0, "unit": "%"},
            "employee_turnover_rate": {"median": 15.0, "top_quartile": 9.0, "unit": "%"},
            "training_hours_per_employee": {"median": 42.0, "top_quartile": 65.0, "unit": "hours"},
            "renewable_energy_pct": {"median": 35.0, "top_quartile": 55.0, "unit": "%"},
            "energy_intensity": {"median": 1.2, "top_quartile": 0.7, "unit": "GJ/INR Lakh"},
            "water_intensity": {"median": 8.0, "top_quartile": 4.5, "unit": "KL/INR Cr"},
            "ghg_scope1": {"median": 180000, "top_quartile": 100000, "unit": "tCO2e"},
            "ghg_scope2": {"median": 120000, "top_quartile": 70000, "unit": "tCO2e"},
            "ghg_intensity": {"median": 8.0, "top_quartile": 4.5, "unit": "tCO2e/INR Cr"},
            "waste_recycled_pct": {"median": 85.0, "top_quartile": 95.0, "unit": "%"},
            "csr_spend_pct": {"median": 2.3, "top_quartile": 3.5, "unit": "% of PAT"},
            "data_privacy_complaints": {"median": 3, "top_quartile": 0, "unit": "count"},
            "ltifr": {"median": 0.25, "top_quartile": 0.08, "unit": "per million hours"},
            "esrs_alignment_score": {"median": 75, "top_quartile": 88, "unit": "%"},
        },
        "typical_disclosure_rate": 87,
    },
    "Pharma_Healthcare": {
        "name": "Pharma & Healthcare",
        "companies": ["Sun Pharma", "Dr Reddy's", "Cipla", "Divi's Lab", "Apollo Hospitals"],
        "benchmarks": {
            "women_board_pct": {"median": 20.0, "top_quartile": 28.0, "unit": "%"},
            "women_employees_pct": {"median": 15.0, "top_quartile": 22.0, "unit": "%"},
            "employee_turnover_rate": {"median": 14.0, "top_quartile": 8.0, "unit": "%"},
            "training_hours_per_employee": {"median": 38.0, "top_quartile": 55.0, "unit": "hours"},
            "renewable_energy_pct": {"median": 20.0, "top_quartile": 40.0, "unit": "%"},
            "energy_intensity": {"median": 1.8, "top_quartile": 1.0, "unit": "GJ/INR Lakh"},
            "water_intensity": {"median": 10.0, "top_quartile": 5.0, "unit": "KL/INR Cr"},
            "ghg_scope1": {"median": 120000, "top_quartile": 65000, "unit": "tCO2e"},
            "ghg_scope2": {"median": 95000, "top_quartile": 50000, "unit": "tCO2e"},
            "ghg_intensity": {"median": 6.5, "top_quartile": 3.5, "unit": "tCO2e/INR Cr"},
            "waste_recycled_pct": {"median": 70.0, "top_quartile": 88.0, "unit": "%"},
            "csr_spend_pct": {"median": 2.0, "top_quartile": 2.5, "unit": "% of PAT"},
            "data_privacy_complaints": {"median": 1, "top_quartile": 0, "unit": "count"},
            "ltifr": {"median": 0.18, "top_quartile": 0.05, "unit": "per million hours"},
            "esrs_alignment_score": {"median": 62, "top_quartile": 75, "unit": "%"},
        },
        "typical_disclosure_rate": 78,
    },
    "Metals_Mining": {
        "name": "Metals & Mining",
        "companies": ["Tata Steel", "JSW Steel", "Hindalco", "Vedanta", "Coal India"],
        "benchmarks": {
            "women_board_pct": {"median": 15.0, "top_quartile": 22.0, "unit": "%"},
            "women_employees_pct": {"median": 6.0, "top_quartile": 10.0, "unit": "%"},
            "employee_turnover_rate": {"median": 6.0, "top_quartile": 4.0, "unit": "%"},
            "training_hours_per_employee": {"median": 50.0, "top_quartile": 80.0, "unit": "hours"},
            "renewable_energy_pct": {"median": 8.0, "top_quartile": 20.0, "unit": "%"},
            "energy_intensity": {"median": 22.0, "top_quartile": 15.0, "unit": "GJ/INR Lakh"},
            "water_intensity": {"median": 55.0, "top_quartile": 35.0, "unit": "KL/INR Cr"},
            "ghg_scope1": {"median": 25000000, "top_quartile": 15000000, "unit": "tCO2e"},
            "ghg_scope2": {"median": 8000000, "top_quartile": 4000000, "unit": "tCO2e"},
            "ghg_intensity": {"median": 250.0, "top_quartile": 150.0, "unit": "tCO2e/INR Cr"},
            "waste_recycled_pct": {"median": 88.0, "top_quartile": 96.0, "unit": "%"},
            "csr_spend_pct": {"median": 2.5, "top_quartile": 3.5, "unit": "% of PAT"},
            "data_privacy_complaints": {"median": 0, "top_quartile": 0, "unit": "count"},
            "ltifr": {"median": 0.65, "top_quartile": 0.25, "unit": "per million hours"},
            "esrs_alignment_score": {"median": 72, "top_quartile": 85, "unit": "%"},
        },
        "typical_disclosure_rate": 83,
    },
}

# Common patterns found in high-quality NIFTY 50 BRSR reports
# These indicate what a "complete" report looks like
NIFTY50_DISCLOSURE_PATTERNS = {
    "section_a": {
        "expected_fields": 22,
        "key_indicators": [
            "cin", "company_name", "financial_year", "reporting_boundary",
            "employees_permanent_male", "employees_permanent_female",
            "workers_permanent_male", "workers_permanent_female",
            "women_board_pct", "turnover_rate_employees",
        ],
        "common_missing": [],  # NIFTY 50 rarely miss Section A
    },
    "section_b": {
        "expected_fields": 14,
        "key_indicators": [
            "policy_covers_principles", "policy_board_approved",
            "policy_extends_value_chain", "commitments_goals_targets",
            "performance_against_targets", "sustainability_committee",
        ],
        "common_missing": ["performance_against_targets", "independent_assessment"],
    },
    "section_c": {
        "expected_fields": 147,
        "key_indicators": {
            "principle_1": ["anti_corruption_policy", "fines_penalties"],
            "principle_2": ["sustainable_sourcing", "recycled_input_pct"],
            "principle_3": ["health_safety_system", "safety_incidents", "training_details"],
            "principle_4": ["stakeholder_groups"],
            "principle_5": ["minimum_wages", "remuneration_details", "complaints_child_labor"],
            "principle_6": ["energy_consumption", "ghg_scope1", "ghg_scope2", "water_withdrawal", "waste_generated"],
            "principle_7": ["trade_associations"],
            "principle_8": ["csr_spend", "input_material_local"],
            "principle_9": ["consumer_complaints", "product_recalls"],
        },
        "common_missing": [
            "ghg_scope3",  # Only ~40% of NIFTY 50 disclose
            "biodiversity",  # Only ~30% provide detailed biodiversity assessment
            "value_chain_hr",  # Supply chain HR due diligence still emerging
            "lca",  # Life Cycle Assessment rarely done outside FMCG
        ],
    },
}

# Patterns from NIFTY 50 reports for smarter extraction
ENHANCED_EXTRACTION_HINTS = {
    "table_headers": {
        # Common table header patterns in BRSR reports
        "employees_table": [
            r"(?:Category|Particulars)\s+(?:Male|M)\s+(?:Female|F)\s+(?:Total|T)",
            r"Permanent\s+Employees.*Male.*Female.*Total",
            r"S\.?\s*No\.?\s+Category.*Total\s+\(A\)",
        ],
        "safety_table": [
            r"Safety\s+Incident.*(?:LTIFR|Fatalities|Reportable)",
            r"Lost\s+Time.*Frequency.*Rate",
            r"Category.*Employees.*Workers",
        ],
        "energy_table": [
            r"Parameter.*FY\s*\d{4}.*FY\s*\d{4}",
            r"(?:From\s+renewable|Non-renewable).*Total\s+(?:electricity|fuel|energy)",
            r"Energy\s+consumption.*GJ|Giga\s*[Jj]oules",
        ],
        "emissions_table": [
            r"Scope\s*[12].*(?:tCO2|Metric\s+[Tt]on)",
            r"Total\s+Scope\s*1.*Total\s+Scope\s*2",
            r"GHG\s+[Ee]missions.*(?:Current|Previous)",
        ],
        "water_table": [
            r"Water\s+withdrawal.*(?:Surface|Ground|Third)",
            r"Source.*(?:KL|Kilolitres|m3)",
        ],
        "waste_table": [
            r"Category\s+of\s+waste.*(?:Current|FY)",
            r"(?:Plastic|E-waste|Hazardous|Bio-medical).*(?:MT|[Tt]onne)",
        ],
        "complaints_table": [
            r"(?:Filed|Received).*(?:Pending|Resolved).*(?:Remarks)",
            r"Category.*Current.*Previous.*Pending",
        ],
    },
    "section_markers": {
        # How NIFTY 50 reports typically mark sections
        "section_a_start": [
            r"SECTION\s+A[:\s]+GENERAL\s+DISCLOSURES",
            r"I\.\s+Details\s+of\s+the\s+[Ll]isted\s+[Ee]ntity",
        ],
        "section_b_start": [
            r"SECTION\s+B[:\s]+MANAGEMENT\s+AND\s+PROCESS",
            r"Policy\s+and\s+management\s+processes",
        ],
        "section_c_start": [
            r"SECTION\s+C[:\s]+PRINCIPLE\s+WISE\s+PERFORMANCE",
            r"PRINCIPLE\s+1[:\s]+(?:Businesses|Ethics)",
        ],
        "principle_markers": [
            r"PRINCIPLE\s+(\d)[:\s]+(.*?)(?:\n|Essential)",
            r"Essential\s+Indicators.*Principle\s+(\d)",
            r"Leadership\s+Indicators.*Principle\s+(\d)",
        ],
    },
    "value_extraction": {
        # Common value patterns specific to Indian BRSR reports
        "inr_crore": r"(?:Rs|INR|₹)\.?\s*([\d,]+(?:\.\d+)?)\s*(?:Crore|Cr|cr)",
        "inr_lakh": r"(?:Rs|INR|₹)\.?\s*([\d,]+(?:\.\d+)?)\s*(?:Lakh|Lac|L)",
        "percentage": r"(\d+(?:\.\d+)?)\s*%",
        "ghg_value": r"([\d,]+(?:\.\d+)?)\s*(?:tCO2e?|Metric\s+[Tt]onnes?\s+of\s+CO2)",
        "energy_gj": r"([\d,]+(?:\.\d+)?)\s*(?:GJ|Giga\s*[Jj]oules)",
        "water_kl": r"([\d,]+(?:\.\d+)?)\s*(?:KL|[Kk]ilo\s*[Ll]itres?|m[³3])",
        "waste_mt": r"([\d,]+(?:\.\d+)?)\s*(?:MT|[Mm]etric\s+[Tt]onnes?)",
        "yes_no": r"\b(Yes|No|Y|N)\b",
        "count": r"(\d[\d,]*)\s*(?:Nos?\.?|Numbers?)?",
    },
}


def detect_sector(extracted_data: dict) -> str:
    """Attempt to detect sector from extracted company data."""
    text_to_check = ""
    section_a = extracted_data.get("section_a", {})
    
    for key in ["business_activities", "products_services_sold", "company_name", "nic_codes"]:
        val = section_a.get(key, "")
        if val:
            text_to_check += " " + str(val).lower()
    
    sector_keywords = {
        "IT_Services": ["information technology", "software", "consulting", "digital", "it services", "technology"],
        "Banking_Financial": ["banking", "financial", "nbfc", "insurance", "credit", "lending", "bank"],
        "Energy_Power": ["energy", "power", "electricity", "oil", "gas", "petroleum", "refining", "renewable"],
        "Manufacturing": ["automobile", "manufacturing", "engineering", "machinery", "cement", "construction"],
        "FMCG_Consumer": ["fmcg", "consumer", "food", "beverage", "personal care", "tobacco", "packaged"],
        "Pharma_Healthcare": ["pharma", "pharmaceutical", "healthcare", "hospital", "drug", "medicine"],
        "Metals_Mining": ["mining", "metal", "steel", "iron", "aluminium", "coal", "ore", "smelting"],
    }
    
    for sector, keywords in sector_keywords.items():
        if any(kw in text_to_check for kw in keywords):
            return sector
    
    return "Manufacturing"  # Default fallback


def get_benchmark_comparison(extracted_data: dict, sector: str = None) -> dict:
    """Compare extracted values against NIFTY 50 sector benchmarks."""
    if not sector:
        sector = detect_sector(extracted_data)
    
    if sector not in SECTOR_BENCHMARKS:
        sector = "Manufacturing"
    
    benchmarks = SECTOR_BENCHMARKS[sector]["benchmarks"]
    comparison = {
        "sector": SECTOR_BENCHMARKS[sector]["name"],
        "sector_companies": SECTOR_BENCHMARKS[sector]["companies"],
        "typical_disclosure_rate": SECTOR_BENCHMARKS[sector]["typical_disclosure_rate"],
        "metrics": {},
    }
    
    # Map extracted keys to benchmark keys
    key_mapping = {
        "women_board_pct": ["women_board_pct", "women_employees_pct", "A.IV.17"],
        "renewable_energy_pct": ["renewable_energy_pct", "energy_from_renewable", "p6_energy_from_renewable"],
        "ghg_scope1": ["ghg_scope1", "p6_ghg_scope1"],
        "ghg_scope2": ["ghg_scope2", "p6_ghg_scope2"],
        "waste_recycled_pct": ["waste_recycled_pct", "p6_waste_recovered"],
        "ltifr": ["safety_incidents", "p3_safety_incidents"],
        "csr_spend_pct": ["csr_spend", "p8_csr_spend"],
        "employee_turnover_rate": ["employee_turnover_rate", "turnover_rate_employees"],
        "training_hours_per_employee": ["training_hours_per_employee", "p3_training_details"],
    }
    
    all_data = {}
    for section in ["section_a", "section_b", "section_c"]:
        all_data.update(extracted_data.get(section, {}))
    
    for benchmark_key, search_keys in key_mapping.items():
        if benchmark_key not in benchmarks:
            continue
        
        value = None
        for sk in search_keys:
            if sk in all_data:
                try:
                    raw = str(all_data[sk]).replace(",", "").replace("%", "").strip()
                    value = float(raw)
                    break
                except (ValueError, TypeError):
                    continue
        
        bench = benchmarks[benchmark_key]
        metric_result = {
            "benchmark_median": bench["median"],
            "benchmark_top_quartile": bench["top_quartile"],
            "unit": bench["unit"],
            "your_value": value,
            "status": "not_disclosed",
        }
        
        if value is not None:
            # Determine if lower is better (for emissions, turnover, complaints)
            lower_is_better = benchmark_key in [
                "employee_turnover_rate", "ghg_scope1", "ghg_scope2", 
                "ghg_intensity", "energy_intensity", "water_intensity",
                "data_privacy_complaints", "ltifr"
            ]
            
            if lower_is_better:
                if value <= bench["top_quartile"]:
                    metric_result["status"] = "top_quartile"
                elif value <= bench["median"]:
                    metric_result["status"] = "above_median"
                else:
                    metric_result["status"] = "below_median"
            else:
                if value >= bench["top_quartile"]:
                    metric_result["status"] = "top_quartile"
                elif value >= bench["median"]:
                    metric_result["status"] = "above_median"
                else:
                    metric_result["status"] = "below_median"
        
        comparison["metrics"][benchmark_key] = metric_result
    
    return comparison
