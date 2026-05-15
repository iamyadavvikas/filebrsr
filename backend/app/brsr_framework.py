"""
SEBI BRSR Framework - Complete reference schema based on official Annexure II.
Defines all required disclosures, organized by Section, Principle, and indicator type.
Each field has: id, label, section, principle, indicator_type (essential/leadership),
data_type, and whether it's mandatory for BRSR Core.
"""

BRSR_FRAMEWORK = {
    "section_a": {
        "title": "SECTION A: GENERAL DISCLOSURES",
        "subsections": {
            "details_of_entity": {
                "title": "I. Details of the Listed Entity",
                "fields": [
                    {"id": "cin", "label": "Corporate Identity Number (CIN)", "mandatory": True, "core": True},
                    {"id": "company_name", "label": "Name of the Listed Entity", "mandatory": True, "core": True},
                    {"id": "year_of_incorporation", "label": "Year of incorporation", "mandatory": True, "core": False},
                    {"id": "registered_office", "label": "Registered office address", "mandatory": True, "core": False},
                    {"id": "corporate_address", "label": "Corporate address", "mandatory": True, "core": False},
                    {"id": "email", "label": "E-mail", "mandatory": True, "core": False},
                    {"id": "telephone", "label": "Telephone", "mandatory": True, "core": False},
                    {"id": "website", "label": "Website", "mandatory": True, "core": False},
                    {"id": "financial_year", "label": "Financial year for which reporting is being done", "mandatory": True, "core": True},
                    {"id": "stock_exchange", "label": "Name of Stock Exchange(s) where shares are listed", "mandatory": True, "core": False},
                    {"id": "paid_up_capital", "label": "Paid-up Capital", "mandatory": True, "core": False},
                    {"id": "contact_person", "label": "Contact person for BRSR queries", "mandatory": True, "core": False},
                    {"id": "reporting_boundary", "label": "Reporting boundary (standalone/consolidated)", "mandatory": True, "core": True},
                    {"id": "assurance_provider", "label": "Name of assurance provider", "mandatory": False, "core": True},
                    {"id": "assurance_type", "label": "Type of assurance obtained", "mandatory": False, "core": True},
                ],
            },
            "products_services": {
                "title": "II. Products/Services",
                "fields": [
                    {"id": "business_activities", "label": "Details of business activities (90% of turnover)", "mandatory": True, "core": False},
                    {"id": "products_services_sold", "label": "Products/Services sold (90% of turnover) with NIC codes", "mandatory": True, "core": False},
                ],
            },
            "operations": {
                "title": "III. Operations",
                "fields": [
                    {"id": "plants_national", "label": "Number of plants - National", "mandatory": True, "core": False},
                    {"id": "plants_international", "label": "Number of plants - International", "mandatory": True, "core": False},
                    {"id": "offices_national", "label": "Number of offices - National", "mandatory": True, "core": False},
                    {"id": "offices_international", "label": "Number of offices - International", "mandatory": True, "core": False},
                    {"id": "states_served", "label": "Number of States served", "mandatory": True, "core": False},
                    {"id": "countries_served", "label": "Number of Countries served", "mandatory": True, "core": False},
                    {"id": "export_pct", "label": "Exports as % of total turnover", "mandatory": True, "core": False},
                    {"id": "customer_types", "label": "Types of customers", "mandatory": True, "core": False},
                ],
            },
            "employees": {
                "title": "IV. Employees",
                "fields": [
                    {"id": "employees_permanent_male", "label": "Permanent Employees - Male", "mandatory": True, "core": True},
                    {"id": "employees_permanent_female", "label": "Permanent Employees - Female", "mandatory": True, "core": True},
                    {"id": "employees_other_male", "label": "Other than Permanent Employees - Male", "mandatory": True, "core": False},
                    {"id": "employees_other_female", "label": "Other than Permanent Employees - Female", "mandatory": True, "core": False},
                    {"id": "workers_permanent_male", "label": "Permanent Workers - Male", "mandatory": True, "core": True},
                    {"id": "workers_permanent_female", "label": "Permanent Workers - Female", "mandatory": True, "core": True},
                    {"id": "workers_other_male", "label": "Other than Permanent Workers - Male", "mandatory": True, "core": False},
                    {"id": "workers_other_female", "label": "Other than Permanent Workers - Female", "mandatory": True, "core": False},
                    {"id": "differently_abled_employees", "label": "Differently abled Employees details", "mandatory": True, "core": False},
                    {"id": "differently_abled_workers", "label": "Differently abled Workers details", "mandatory": True, "core": False},
                    {"id": "women_board_pct", "label": "Women on Board of Directors (%)", "mandatory": True, "core": True},
                    {"id": "women_kmp_pct", "label": "Women in Key Management Personnel (%)", "mandatory": True, "core": False},
                    {"id": "turnover_rate_employees", "label": "Turnover rate - Permanent Employees (3 year trend)", "mandatory": True, "core": True},
                    {"id": "turnover_rate_workers", "label": "Turnover rate - Permanent Workers (3 year trend)", "mandatory": True, "core": True},
                ],
            },
            "holding_subsidiary": {
                "title": "V. Holding, Subsidiary and Associate Companies",
                "fields": [
                    {"id": "group_companies", "label": "Names and details of holding/subsidiary/associate/JV companies", "mandatory": True, "core": False},
                ],
            },
            "csr_details": {
                "title": "VI. CSR Details",
                "fields": [
                    {"id": "csr_applicable", "label": "Whether CSR is applicable (as per Section 135)", "mandatory": True, "core": False},
                    {"id": "turnover_for_csr", "label": "Turnover (in Rs.)", "mandatory": True, "core": False},
                    {"id": "net_worth", "label": "Net worth (in Rs.)", "mandatory": True, "core": False},
                ],
            },
            "transparency": {
                "title": "VII. Transparency and Disclosures Compliances",
                "fields": [
                    {"id": "complaints_grievances", "label": "Complaints/Grievances on Principles 1-9", "mandatory": True, "core": False},
                    {"id": "material_issues", "label": "Material responsible business conduct issues", "mandatory": True, "core": False},
                ],
            },
        },
    },
    "section_b": {
        "title": "SECTION B: MANAGEMENT AND PROCESS DISCLOSURES",
        "subsections": {
            "policy_management": {
                "title": "Policy and Management Processes",
                "fields": [
                    {"id": "policy_covers_principles", "label": "Policy covers each NGRBC principle (P1-P9)", "mandatory": True, "core": False},
                    {"id": "policy_board_approved", "label": "Policy approved by Board (P1-P9)", "mandatory": True, "core": False},
                    {"id": "policy_web_link", "label": "Web Link of Policies", "mandatory": True, "core": False},
                    {"id": "policy_translated_to_procedures", "label": "Policy translated into procedures", "mandatory": True, "core": False},
                    {"id": "policy_extends_value_chain", "label": "Policies extend to value chain partners", "mandatory": True, "core": False},
                    {"id": "certifications_standards", "label": "Codes/certifications/standards adopted (mapped to principles)", "mandatory": True, "core": False},
                    {"id": "commitments_goals_targets", "label": "Specific commitments, goals and targets with timelines", "mandatory": True, "core": False},
                    {"id": "performance_against_targets", "label": "Performance against commitments/goals/targets", "mandatory": True, "core": False},
                ],
            },
            "governance": {
                "title": "Governance, Leadership and Oversight",
                "fields": [
                    {"id": "director_statement", "label": "Statement by director on ESG challenges/targets/achievements", "mandatory": True, "core": False},
                    {"id": "highest_authority_br", "label": "Highest authority responsible for BR policy implementation", "mandatory": True, "core": False},
                    {"id": "sustainability_committee", "label": "Board Committee for sustainability decisions", "mandatory": True, "core": False},
                    {"id": "ngrbc_review_details", "label": "Details of NGRBC review by Board/Committee", "mandatory": True, "core": False},
                    {"id": "independent_assessment", "label": "Independent assessment of policies by external agency", "mandatory": True, "core": False},
                ],
            },
        },
    },
    "section_c": {
        "title": "SECTION C: PRINCIPLE WISE PERFORMANCE DISCLOSURE",
        "subsections": {
            "principle_1": {
                "title": "PRINCIPLE 1: Ethics, Transparency and Accountability",
                "essential": [
                    {"id": "p1_training_awareness", "label": "Training/awareness on principles (Board, KMP, Employees, Workers)", "mandatory": True, "core": False},
                    {"id": "p1_fines_penalties", "label": "Fines/penalties/punishment details", "mandatory": True, "core": True},
                    {"id": "p1_anti_corruption_policy", "label": "Anti-corruption or anti-bribery policy", "mandatory": True, "core": True},
                    {"id": "p1_disciplinary_action", "label": "Disciplinary action for bribery/corruption", "mandatory": True, "core": False},
                    {"id": "p1_conflict_of_interest", "label": "Complaints on conflict of interest (Directors/KMPs)", "mandatory": True, "core": False},
                    {"id": "p1_corrective_action", "label": "Corrective action on fines/penalties", "mandatory": True, "core": False},
                    {"id": "p1_accounts_payable_days", "label": "Number of days of accounts payables", "mandatory": True, "core": False},
                    {"id": "p1_openness_of_business", "label": "Concentration of purchases/sales/RPTs", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p1_value_chain_awareness", "label": "Awareness programmes for value chain partners", "mandatory": False, "core": False},
                    {"id": "p1_conflict_avoidance_process", "label": "Processes to avoid/manage conflict of interest", "mandatory": False, "core": False},
                ],
            },
            "principle_2": {
                "title": "PRINCIPLE 2: Sustainable and Safe Products/Services",
                "essential": [
                    {"id": "p2_rd_capex_green", "label": "R&D and capex for environmental/social improvements (%)", "mandatory": True, "core": False},
                    {"id": "p2_sustainable_sourcing", "label": "Sustainable sourcing procedures and % inputs", "mandatory": True, "core": True},
                    {"id": "p2_product_reclaim_process", "label": "Processes for product reclaim/reuse/recycle", "mandatory": True, "core": False},
                    {"id": "p2_epr_applicable", "label": "Extended Producer Responsibility (EPR) applicability", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p2_lca", "label": "Life Cycle Assessment (LCA) conducted", "mandatory": False, "core": False},
                    {"id": "p2_social_env_risks", "label": "Social/environmental risks from products", "mandatory": False, "core": False},
                    {"id": "p2_recycled_input_pct", "label": "Recycled/reused input material to total (%)", "mandatory": False, "core": True},
                    {"id": "p2_reclaimed_products", "label": "Reclaimed products/packaging (metric tonnes)", "mandatory": False, "core": False},
                ],
            },
            "principle_3": {
                "title": "PRINCIPLE 3: Employee Well-being",
                "essential": [
                    {"id": "p3_wellbeing_employees", "label": "Employee well-being measures (health/accident/maternity/paternity/day care)", "mandatory": True, "core": True},
                    {"id": "p3_wellbeing_workers", "label": "Worker well-being measures", "mandatory": True, "core": True},
                    {"id": "p3_wellbeing_spending", "label": "Spending on well-being as % of revenue", "mandatory": True, "core": False},
                    {"id": "p3_retirement_benefits", "label": "Retirement benefits (PF, Gratuity, ESI)", "mandatory": True, "core": False},
                    {"id": "p3_accessibility", "label": "Workplace accessibility for differently abled", "mandatory": True, "core": False},
                    {"id": "p3_equal_opportunity", "label": "Equal opportunity policy", "mandatory": True, "core": False},
                    {"id": "p3_parental_leave", "label": "Return to work/retention rates for parental leave", "mandatory": True, "core": False},
                    {"id": "p3_grievance_mechanism", "label": "Grievance mechanism for employees/workers", "mandatory": True, "core": False},
                    {"id": "p3_union_membership", "label": "Union/association membership details", "mandatory": True, "core": False},
                    {"id": "p3_training_details", "label": "Training on health/safety and skill upgradation", "mandatory": True, "core": True},
                    {"id": "p3_performance_reviews", "label": "Performance and career development reviews", "mandatory": True, "core": False},
                    {"id": "p3_health_safety_system", "label": "Occupational health and safety management system", "mandatory": True, "core": True},
                    {"id": "p3_safety_incidents", "label": "Safety incidents/injuries/fatalities (LTIFR, fatalities)", "mandatory": True, "core": True},
                    {"id": "p3_safe_working_conditions", "label": "Measures for safe working conditions", "mandatory": True, "core": False},
                    {"id": "p3_complaints_working_conditions", "label": "Complaints on working conditions/health/safety", "mandatory": True, "core": True},
                    {"id": "p3_assessments", "label": "Assessments of plants/offices for health & safety", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p3_life_insurance_details", "label": "Life insurance/disability cover details", "mandatory": False, "core": False},
                    {"id": "p3_transition_assistance", "label": "Transition assistance programs", "mandatory": False, "core": False},
                    {"id": "p3_high_consequence_injuries", "label": "High consequence work-related injuries/ill-health", "mandatory": False, "core": False},
                ],
            },
            "principle_4": {
                "title": "PRINCIPLE 4: Stakeholder Engagement",
                "essential": [
                    {"id": "p4_stakeholder_groups", "label": "Stakeholder groups identified (vulnerable/marginalized)", "mandatory": True, "core": False},
                    {"id": "p4_stakeholder_identification_process", "label": "Process for stakeholder identification", "mandatory": True, "core": False},
                    {"id": "p4_stakeholder_channels", "label": "Channels for stakeholder engagement", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p4_stakeholder_engagement_process", "label": "Process for stakeholder engagement in key decisions", "mandatory": False, "core": False},
                ],
            },
            "principle_5": {
                "title": "PRINCIPLE 5: Human Rights",
                "essential": [
                    {"id": "p5_human_rights_training", "label": "Human rights training for employees/workers (%)", "mandatory": True, "core": True},
                    {"id": "p5_minimum_wages", "label": "Minimum wages paid to employees/workers", "mandatory": True, "core": True},
                    {"id": "p5_remuneration_details", "label": "Gross wages/median remuneration (male/female)", "mandatory": True, "core": True},
                    {"id": "p5_complaints_sexual_harassment", "label": "Complaints on sexual harassment (POSH)", "mandatory": True, "core": False},
                    {"id": "p5_complaints_discrimination", "label": "Complaints on discrimination at workplace", "mandatory": True, "core": False},
                    {"id": "p5_complaints_child_labor", "label": "Complaints on child/forced labour", "mandatory": True, "core": True},
                    {"id": "p5_complaints_wages", "label": "Complaints on wages", "mandatory": True, "core": False},
                    {"id": "p5_hr_assessments", "label": "Human rights assessments of plants/offices", "mandatory": True, "core": False},
                    {"id": "p5_corrective_action", "label": "Corrective actions on HR issues", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p5_business_impact_hr", "label": "Business processes modified based on HR assessments", "mandatory": False, "core": False},
                    {"id": "p5_value_chain_hr", "label": "Value chain HR due diligence details", "mandatory": False, "core": False},
                ],
            },
            "principle_6": {
                "title": "PRINCIPLE 6: Environment",
                "essential": [
                    {"id": "p6_energy_consumption", "label": "Total energy consumption (GJ) from renewable/non-renewable", "mandatory": True, "core": True},
                    {"id": "p6_energy_intensity", "label": "Energy intensity per rupee of turnover", "mandatory": True, "core": True},
                    {"id": "p6_energy_from_renewable", "label": "Energy from renewable sources (%)", "mandatory": True, "core": True},
                    {"id": "p6_water_withdrawal", "label": "Water withdrawal by source", "mandatory": True, "core": True},
                    {"id": "p6_water_intensity", "label": "Water intensity per rupee of turnover", "mandatory": True, "core": True},
                    {"id": "p6_water_discharged", "label": "Water discharged (destination & treatment)", "mandatory": True, "core": True},
                    {"id": "p6_ghg_scope1", "label": "Scope 1 GHG emissions (tCO2e)", "mandatory": True, "core": True},
                    {"id": "p6_ghg_scope2", "label": "Scope 2 GHG emissions (tCO2e)", "mandatory": True, "core": True},
                    {"id": "p6_ghg_intensity", "label": "GHG emission intensity per rupee of turnover", "mandatory": True, "core": True},
                    {"id": "p6_waste_generated", "label": "Total waste generated (MT) by category", "mandatory": True, "core": True},
                    {"id": "p6_waste_recovered", "label": "Waste recovered/recycled/reused (MT)", "mandatory": True, "core": True},
                    {"id": "p6_waste_disposed", "label": "Waste disposed (MT) by method", "mandatory": True, "core": True},
                    {"id": "p6_ecologically_sensitive", "label": "Operations in ecologically sensitive areas", "mandatory": True, "core": False},
                    {"id": "p6_eia", "label": "Environmental impact assessments conducted", "mandatory": True, "core": False},
                    {"id": "p6_env_non_compliance", "label": "Environmental non-compliances", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p6_ghg_scope3", "label": "Scope 3 GHG emissions", "mandatory": False, "core": True},
                    {"id": "p6_renewable_energy_purchased", "label": "Renewable energy purchased/generated breakdown", "mandatory": False, "core": False},
                    {"id": "p6_water_zero_discharge", "label": "Zero liquid discharge status", "mandatory": False, "core": True},
                    {"id": "p6_biodiversity", "label": "Biodiversity impact assessment", "mandatory": False, "core": False},
                ],
            },
            "principle_7": {
                "title": "PRINCIPLE 7: Policy Advocacy",
                "essential": [
                    {"id": "p7_trade_associations", "label": "Trade/industry associations membership (top 10)", "mandatory": True, "core": False},
                    {"id": "p7_anti_competitive", "label": "Anti-competitive conduct cases", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p7_public_policy_positions", "label": "Public policy advocacy positions", "mandatory": False, "core": False},
                ],
            },
            "principle_8": {
                "title": "PRINCIPLE 8: Inclusive Growth",
                "essential": [
                    {"id": "p8_social_impact_assessment", "label": "Social Impact Assessments (SIA)", "mandatory": True, "core": False},
                    {"id": "p8_rehabilitation_resettlement", "label": "R&R details for affected communities", "mandatory": True, "core": False},
                    {"id": "p8_csr_spend", "label": "CSR spending and projects", "mandatory": True, "core": False},
                    {"id": "p8_community_grievances", "label": "Community grievances", "mandatory": True, "core": False},
                    {"id": "p8_input_material_local", "label": "Inputs sourced from local/small producers (%)", "mandatory": True, "core": True},
                ],
                "leadership": [
                    {"id": "p8_preferential_procurement", "label": "Preferential procurement from marginalized groups", "mandatory": False, "core": False},
                    {"id": "p8_beneficiaries", "label": "CSR beneficiaries (SC/ST/Others breakdown)", "mandatory": False, "core": False},
                ],
            },
            "principle_9": {
                "title": "PRINCIPLE 9: Consumer Responsibility",
                "essential": [
                    {"id": "p9_consumer_complaints", "label": "Consumer complaints (data privacy, advertising, delivery, etc.)", "mandatory": True, "core": True},
                    {"id": "p9_product_recalls", "label": "Product recalls and reasons", "mandatory": True, "core": True},
                    {"id": "p9_cybersecurity_policy", "label": "Cybersecurity and data privacy policy", "mandatory": True, "core": False},
                    {"id": "p9_corrective_action", "label": "Corrective action on consumer complaints", "mandatory": True, "core": False},
                ],
                "leadership": [
                    {"id": "p9_information_to_consumers", "label": "Information on environmental/social parameters of products", "mandatory": False, "core": False},
                    {"id": "p9_consumer_surveys", "label": "Consumer surveys / feedback mechanisms", "mandatory": False, "core": False},
                ],
            },
        },
    },
}


def get_all_field_ids() -> list[str]:
    """Get flat list of all field IDs in the framework."""
    ids = []
    for section_key, section in BRSR_FRAMEWORK.items():
        for subsection_key, subsection in section["subsections"].items():
            if "fields" in subsection:
                ids.extend(f["id"] for f in subsection["fields"])
            if "essential" in subsection:
                ids.extend(f["id"] for f in subsection["essential"])
            if "leadership" in subsection:
                ids.extend(f["id"] for f in subsection["leadership"])
    return ids


def get_mandatory_fields() -> list[dict]:
    """Get all mandatory (essential) fields."""
    fields = []
    for section_key, section in BRSR_FRAMEWORK.items():
        for subsection_key, subsection in section["subsections"].items():
            if "fields" in subsection:
                fields.extend(f for f in subsection["fields"] if f.get("mandatory"))
            if "essential" in subsection:
                fields.extend(f for f in subsection["essential"] if f.get("mandatory"))
    return fields


def get_core_fields() -> list[dict]:
    """Get all BRSR Core fields (required for assurance)."""
    fields = []
    for section_key, section in BRSR_FRAMEWORK.items():
        for subsection_key, subsection in section["subsections"].items():
            if "fields" in subsection:
                fields.extend(f for f in subsection["fields"] if f.get("core"))
            if "essential" in subsection:
                fields.extend(f for f in subsection["essential"] if f.get("core"))
            if "leadership" in subsection:
                fields.extend(f for f in subsection["leadership"] if f.get("core"))
    return fields


def analyze_gaps(extracted_data: dict) -> dict:
    """
    Compare extracted data against SEBI BRSR framework.
    Returns gap analysis with missing fields, compliance scores, and recommendations.
    """
    # Flatten extracted data keys
    extracted_keys = set()
    for section_key in ["section_a", "section_b", "section_c"]:
        section_data = extracted_data.get(section_key, {})
        if isinstance(section_data, dict):
            extracted_keys.update(section_data.keys())

    all_mandatory = get_mandatory_fields()
    core_fields = get_core_fields()

    # Check each field
    missing_mandatory = []
    missing_core = []
    found_mandatory = []
    found_core = []

    for field in all_mandatory:
        if field["id"] in extracted_keys:
            found_mandatory.append(field)
        else:
            missing_mandatory.append(field)

    for field in core_fields:
        if field["id"] in extracted_keys:
            found_core.append(field)
        else:
            missing_core.append(field)

    # Calculate scores
    total_mandatory = len(all_mandatory)
    total_core = len(core_fields)
    mandatory_score = (len(found_mandatory) / total_mandatory * 100) if total_mandatory > 0 else 0
    core_score = (len(found_core) / total_core * 100) if total_core > 0 else 0

    # Section-wise breakdown
    section_scores = {}
    for section_key, section in BRSR_FRAMEWORK.items():
        section_total = 0
        section_found = 0
        for subsection_key, subsection in section["subsections"].items():
            fields_list = []
            if "fields" in subsection:
                fields_list.extend(subsection["fields"])
            if "essential" in subsection:
                fields_list.extend(subsection["essential"])
            for f in fields_list:
                if f.get("mandatory"):
                    section_total += 1
                    if f["id"] in extracted_keys:
                        section_found += 1
        section_scores[section_key] = {
            "total": section_total,
            "found": section_found,
            "score": round(section_found / section_total * 100, 1) if section_total > 0 else 0,
        }

    # Generate recommendations for top missing items
    recommendations = []
    for field in missing_core[:10]:
        recommendations.append({
            "field_id": field["id"],
            "label": field["label"],
            "priority": "HIGH",
            "reason": "Required for BRSR Core assurance",
        })
    for field in missing_mandatory[:10]:
        if field not in missing_core:
            recommendations.append({
                "field_id": field["id"],
                "label": field["label"],
                "priority": "MEDIUM",
                "reason": "Mandatory BRSR disclosure",
            })

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
        "missing_mandatory": [{"id": f["id"], "label": f["label"], "core": f.get("core", False)} for f in missing_mandatory],
        "missing_core": [{"id": f["id"], "label": f["label"]} for f in missing_core],
        "recommendations": recommendations[:15],
    }
