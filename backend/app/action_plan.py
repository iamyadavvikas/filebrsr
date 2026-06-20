"""
AI-powered Action Plan Generator for BRSR improvement roadmap.
Analyzes gaps in BRSR compliance and generates prioritized, actionable recommendations.
"""

import json
from typing import Optional


# Indian regulatory context for recommendations
NGRBC_PRINCIPLES = {
    "P1": {"name": "Ethics & Transparency", "focus": "Anti-corruption, ethical business conduct, transparency in operations"},
    "P2": {"name": "Product Lifecycle Sustainability", "focus": "Sustainable sourcing, circular economy, product safety, EPR compliance"},
    "P3": {"name": "Employee Wellbeing", "focus": "Worker safety, diversity, benefits, training, human rights in workplace"},
    "P4": {"name": "Stakeholder Engagement", "focus": "Community engagement, CSR, stakeholder responsiveness"},
    "P5": {"name": "Human Rights", "focus": "Human rights policy, UNGP alignment, grievance mechanisms"},
    "P6": {"name": "Environmental Protection", "focus": "GHG emissions, energy, water, waste, biodiversity, circular economy"},
    "P7": {"name": "Policy Advocacy", "focus": "Responsible policy engagement, trade association memberships"},
    "P8": {"name": "Inclusive Growth", "focus": "CSR, community development, input from marginalized groups"},
    "P9": {"name": "Consumer Responsibility", "focus": "Data privacy, product labeling, consumer complaints, cyber security"},
}

# Cost estimates for common BRSR improvements (INR)
IMPROVEMENT_COST_ESTIMATES = {
    "policy_creation": {"min": 50000, "max": 200000, "effort": "short_term"},
    "policy_review": {"min": 25000, "max": 100000, "effort": "quick_win"},
    "data_system_setup": {"min": 200000, "max": 1000000, "effort": "medium_term"},
    "training_program": {"min": 100000, "max": 500000, "effort": "short_term"},
    "audit_assurance": {"min": 500000, "max": 2000000, "effort": "medium_term"},
    "technology_implementation": {"min": 500000, "max": 5000000, "effort": "long_term"},
    "process_change": {"min": 100000, "max": 1000000, "effort": "medium_term"},
    "reporting_enhancement": {"min": 50000, "max": 300000, "effort": "quick_win"},
    "stakeholder_engagement": {"min": 200000, "max": 1000000, "effort": "medium_term"},
    "carbon_reduction_project": {"min": 1000000, "max": 50000000, "effort": "long_term"},
}


def generate_action_plan_from_gaps(gap_analysis: dict, extracted_data: dict, sector: str = "general") -> list:
    """
    Generate prioritized action plan from gap analysis results.
    Returns list of action items sorted by priority and impact.
    """
    actions = []
    
    # Analyze missing mandatory disclosures
    missing_essential = gap_analysis.get("missing_essential", [])
    missing_leadership = gap_analysis.get("missing_leadership", [])
    low_confidence = gap_analysis.get("low_confidence_fields", [])
    
    # Priority 1: Missing mandatory/core disclosures (SEBI compliance risk)
    for field in missing_essential[:20]:  # Top 20 critical gaps
        principle = _identify_principle(field)
        action = {
            "title": f"Disclose: {field.get('label', field.get('id', 'Unknown'))}",
            "description": f"Mandatory BRSR disclosure missing. Required by SEBI for all top-1000 listed companies. "
                          f"Failure to disclose may result in regulatory action.",
            "category": _field_to_category(field),
            "priority": "critical",
            "effort": "quick_win" if field.get("data_type") in ["boolean", "narrative"] else "short_term",
            "impact_score": 9,
            "principle": principle,
            "datapoint_ids": [field.get("id", "")],
            "estimated_cost_inr": _estimate_cost(field),
            "recommendations": _get_specific_recommendations(field, principle),
        }
        actions.append(action)
    
    # Priority 2: BRSR Core fields (subject to assurance)
    core_gaps = [f for f in missing_essential if f.get("core")]
    for field in core_gaps[:10]:
        principle = _identify_principle(field)
        action = {
            "title": f"[BRSR Core] Establish data for: {field.get('label', '')}",
            "description": f"BRSR Core indicator requiring reasonable assurance from FY 2026-27. "
                          f"Need documented data collection process with audit trail.",
            "category": _field_to_category(field),
            "priority": "high",
            "effort": "medium_term",
            "impact_score": 8,
            "principle": principle,
            "datapoint_ids": [field.get("id", "")],
            "estimated_cost_inr": _estimate_cost(field, multiplier=2),
            "recommendations": [
                "Establish documented data collection process",
                "Implement internal controls for data accuracy",
                "Engage assurance provider early for readiness assessment",
                "Create data lineage documentation",
            ],
        }
        actions.append(action)
    
    # Priority 3: Environmental improvements (P6)
    env_data = extracted_data.get("section_c", {})
    env_actions = _generate_environmental_actions(env_data, sector)
    actions.extend(env_actions)
    
    # Priority 4: Social & Governance improvements
    social_actions = _generate_social_actions(extracted_data, gap_analysis)
    actions.extend(social_actions)
    
    # Priority 5: Leadership indicators (competitive advantage)
    for field in missing_leadership[:10]:
        principle = _identify_principle(field)
        action = {
            "title": f"[Leadership] Adopt: {field.get('label', '')}",
            "description": f"Leadership indicator that demonstrates best-in-class ESG practice. "
                          f"Improves ESG ratings and investor confidence.",
            "category": _field_to_category(field),
            "priority": "medium",
            "effort": "medium_term",
            "impact_score": 6,
            "principle": principle,
            "datapoint_ids": [field.get("id", "")],
            "estimated_cost_inr": _estimate_cost(field),
            "recommendations": _get_leadership_recommendations(field),
        }
        actions.append(action)
    
    # Sort by priority then impact
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    actions.sort(key=lambda x: (priority_order.get(x["priority"], 4), -x["impact_score"]))
    
    return actions


def _identify_principle(field: dict) -> str:
    """Map a datapoint to its NGRBC principle."""
    dp_id = field.get("id", "")
    if dp_id.startswith("C.P"):
        # Extract principle number from ID like C.P1.E.1
        parts = dp_id.split(".")
        if len(parts) >= 2:
            return parts[1].upper()  # P1, P2, etc.
    if dp_id.startswith("A"):
        return "P1"  # General disclosures map to governance
    if dp_id.startswith("B"):
        return "P1"  # Management & process
    return "P1"


def _field_to_category(field: dict) -> str:
    """Map field to E/S/G category."""
    dp_id = field.get("id", "")
    principle = _identify_principle(field)
    
    if principle in ["P6"]:
        return "environment"
    elif principle in ["P3", "P4", "P5", "P8"]:
        return "social"
    elif principle in ["P1", "P7", "P9"]:
        return "governance"
    return "general"


def _estimate_cost(field: dict, multiplier: float = 1.0) -> float:
    """Estimate implementation cost based on data type and complexity."""
    data_type = field.get("data_type", "narrative")
    
    if data_type in ["boolean", "narrative"]:
        base = IMPROVEMENT_COST_ESTIMATES["policy_creation"]
    elif data_type in ["table"]:
        base = IMPROVEMENT_COST_ESTIMATES["data_system_setup"]
    elif data_type in ["monetary", "energy", "mass", "volume"]:
        base = IMPROVEMENT_COST_ESTIMATES["process_change"]
    else:
        base = IMPROVEMENT_COST_ESTIMATES["reporting_enhancement"]
    
    avg_cost = (base["min"] + base["max"]) / 2
    return round(avg_cost * multiplier, 0)


def _get_specific_recommendations(field: dict, principle: str) -> list:
    """Get specific actionable recommendations for a gap."""
    recommendations = []
    data_type = field.get("data_type", "narrative")
    
    if data_type == "boolean":
        recommendations.append("Create/update the required policy document")
        recommendations.append("Get board/committee approval")
        recommendations.append("Publish on company website")
    elif data_type == "narrative":
        recommendations.append("Draft disclosure text with specific details")
        recommendations.append("Include quantitative data where possible")
        recommendations.append("Reference supporting documents/policies")
    elif data_type in ["integer", "decimal", "monetary"]:
        recommendations.append("Establish data collection process from relevant departments")
        recommendations.append("Define calculation methodology and document assumptions")
        recommendations.append("Set up periodic data validation checkpoints")
    elif data_type == "table":
        recommendations.append("Design data collection template for all dimensions")
        recommendations.append("Assign data owners for each row/column")
        recommendations.append("Implement quarterly data refresh cycle")
    elif data_type in ["energy", "mass", "volume"]:
        recommendations.append("Install/verify meters and monitoring equipment")
        recommendations.append("Establish measurement protocol with frequency")
        recommendations.append("Cross-verify with utility bills/purchase records")
    
    # Add principle-specific advice
    if principle == "P6":
        recommendations.append("Consider engaging environmental consultant for baseline assessment")
    elif principle == "P3":
        recommendations.append("Coordinate with HR department for employee data")
    elif principle == "P9":
        recommendations.append("Review IT/data privacy policies for alignment")
    
    return recommendations


def _get_leadership_recommendations(field: dict) -> list:
    """Recommendations for leadership indicators."""
    return [
        "Benchmark against NIFTY 50 sector peers who already disclose this",
        "Consider phased implementation over 2-3 reporting cycles",
        "Highlight in sustainability report as voluntary disclosure",
        "Use for ESG rating improvement (MSCI, Sustainalytics, S&P CSA)",
    ]


def _generate_environmental_actions(env_data: dict, sector: str) -> list:
    """Generate environmental improvement actions."""
    actions = []
    
    # Check renewable energy percentage
    renewable_pct = env_data.get("renewable_energy_percentage", 0)
    if isinstance(renewable_pct, str):
        try:
            renewable_pct = float(renewable_pct.replace("%", ""))
        except (ValueError, AttributeError):
            renewable_pct = 0
    
    if renewable_pct < 30:
        actions.append({
            "title": "Increase Renewable Energy to 30%+",
            "description": f"Current renewable energy at {renewable_pct}%. "
                          f"Indian RE100 target and investor expectations require >30%. "
                          f"Consider rooftop solar, open access, and green tariff options.",
            "category": "environment",
            "priority": "high",
            "effort": "long_term",
            "impact_score": 8,
            "principle": "P6",
            "datapoint_ids": ["C.P6.E.3"],
            "estimated_cost_inr": 5000000,
            "recommendations": [
                "Conduct rooftop solar feasibility study",
                "Explore open access RE procurement (group captive / third-party)",
                "Evaluate green tariff programs from DISCOMS",
                "Consider I-REC/REC certificates for market-based accounting",
                "Set year-wise RE% targets (e.g., 30% by FY26, 50% by FY28)",
            ],
        })
    
    # Water management
    if not env_data.get("water_recycled_percentage"):
        actions.append({
            "title": "Implement Water Recycling & Zero Liquid Discharge",
            "description": "BRSR requires disclosure of water recycled/reused. "
                          "Implement STP/ETP and track recycling percentage.",
            "category": "environment",
            "priority": "medium",
            "effort": "long_term",
            "impact_score": 7,
            "principle": "P6",
            "datapoint_ids": ["C.P6.W.3", "C.P6.W.4"],
            "estimated_cost_inr": 10000000,
            "recommendations": [
                "Conduct water audit across all facilities",
                "Install water meters at key consumption points",
                "Evaluate STP/ETP upgrade or installation",
                "Set water recycling targets (>50% recommended)",
                "Implement rainwater harvesting at all major sites",
            ],
        })
    
    # Waste management
    if not env_data.get("waste_diverted_from_landfill"):
        actions.append({
            "title": "Achieve Zero Waste to Landfill",
            "description": "Track waste by category and demonstrate diversion from landfill. "
                          "Required under BRSR P6 and aligned with EPR obligations.",
            "category": "environment",
            "priority": "medium",
            "effort": "medium_term",
            "impact_score": 6,
            "principle": "P6",
            "datapoint_ids": ["C.P6.WM.1", "C.P6.WM.2"],
            "estimated_cost_inr": 2000000,
            "recommendations": [
                "Conduct waste audit and categorization",
                "Partner with authorized recyclers and waste processors",
                "Implement source segregation at all facilities",
                "Track waste metrics monthly",
                "Comply with EPR obligations under Plastic Waste Management Rules",
            ],
        })
    
    return actions


def _generate_social_actions(extracted_data: dict, gap_analysis: dict) -> list:
    """Generate social improvement actions."""
    actions = []
    section_b = extracted_data.get("section_b", {})
    section_c = extracted_data.get("section_c", {})
    
    # Diversity & inclusion
    women_pct = section_c.get("women_employees_percentage", 0)
    if isinstance(women_pct, str):
        try:
            women_pct = float(women_pct.replace("%", ""))
        except (ValueError, AttributeError):
            women_pct = 0
    
    if women_pct < 25:
        actions.append({
            "title": "Improve Gender Diversity (Target 25%+ Women)",
            "description": f"Current women representation at {women_pct}%. "
                          f"BRSR Core requires gender diversity disclosure. "
                          f"Low diversity impacts ESG ratings significantly.",
            "category": "social",
            "priority": "high",
            "effort": "long_term",
            "impact_score": 7,
            "principle": "P3",
            "datapoint_ids": ["C.P3.E.1", "C.P3.E.2"],
            "estimated_cost_inr": 1000000,
            "recommendations": [
                "Set gender diversity targets with board accountability",
                "Implement returnship programs for women re-entering workforce",
                "Review pay equity and publish gender pay gap",
                "Ensure 30%+ women in management/board",
                "Partner with women's professional networks for recruitment",
            ],
        })
    
    # Safety
    if not section_c.get("ltifr") and not section_c.get("lost_time_injury_frequency"):
        actions.append({
            "title": "Establish Safety KPI Tracking (LTIFR)",
            "description": "Lost Time Injury Frequency Rate not reported. "
                          "Critical BRSR Core metric for P3 assurance.",
            "category": "social",
            "priority": "high",
            "effort": "short_term",
            "impact_score": 8,
            "principle": "P3",
            "datapoint_ids": ["C.P3.S.1", "C.P3.S.2"],
            "estimated_cost_inr": 500000,
            "recommendations": [
                "Implement incident reporting system (all sites)",
                "Calculate LTIFR = (Lost time injuries × 1,000,000) / Man-hours worked",
                "Set LTIFR reduction targets (benchmark: <1.0 for manufacturing)",
                "Conduct safety audits quarterly",
                "Include contract workers in safety metrics",
            ],
        })
    
    return actions


def generate_ai_action_plan_prompt(gap_analysis: dict, extracted_data: dict, sector: str) -> str:
    """Generate prompt for AI-enhanced action plan."""
    prompt = f"""You are an expert ESG consultant specializing in SEBI BRSR compliance for Indian listed companies.

Based on the following gap analysis and extracted data, generate a detailed improvement roadmap.

SECTOR: {sector}
FINANCIAL YEAR: {extracted_data.get('section_a', {}).get('financial_year', 'FY2024-25')}
COMPANY: {extracted_data.get('section_a', {}).get('company_name', 'Unknown')}

GAP ANALYSIS SUMMARY:
- Total datapoints: {gap_analysis.get('total_datapoints', 216)}
- Filled: {gap_analysis.get('filled_datapoints', 0)}
- Missing Essential: {gap_analysis.get('missing_essential_count', 0)}
- Missing Leadership: {gap_analysis.get('missing_leadership_count', 0)}
- Completion: {gap_analysis.get('completion_percent', 0)}%

TOP MISSING DISCLOSURES:
{json.dumps(gap_analysis.get('missing_essential', [])[:15], indent=2, default=str)}

AVAILABLE DATA:
{json.dumps({k: len(v) if isinstance(v, dict) else v for k, v in extracted_data.items()}, indent=2, default=str)}

Generate a JSON array of 10-15 prioritized action items with this structure:
[{{
  "title": "Action title",
  "description": "Detailed description with Indian regulatory context",
  "category": "environment|social|governance",
  "priority": "critical|high|medium|low",
  "effort": "quick_win|short_term|medium_term|long_term",
  "impact_score": 1-10,
  "principle": "P1-P9",
  "estimated_cost_inr": number,
  "timeline_months": number,
  "recommendations": ["step1", "step2", ...]
}}]

Focus on:
1. SEBI compliance risks (filing deadlines, penalties)
2. BRSR Core assurance readiness (top 250 from FY2026-27)
3. Quick wins that improve ESG ratings immediately
4. Cost-effective improvements with highest ROI
5. Sector-specific best practices for {sector}
"""
    return prompt
