"""
BRSR Compliance Scoring System — CDP-style maturity scoring (0-100).

Scoring Dimensions:
1. Completeness (40%) — How many mandatory/core fields are filled
2. Quality (25%) — Data type validity, no anomalies, year-over-year consistency
3. Cross-framework alignment (20%) — ESRS/GRI/TCFD/ISSB coverage
4. Depth (15%) — Leadership indicators beyond essential, narrative quality

Rating Scale (inspired by CDP):
- A  (85-100): Comprehensive, leadership-level disclosures
- B  (70-84):  Strong compliance, most core indicators present
- C  (50-69):  Adequate, meets minimum BRSR requirements
- D  (30-49):  Below average, significant gaps
- F  (0-29):   Failing, major non-compliance
"""

from typing import Any
from app.validation_engine import validate_brsr_data, _get_field_value, _parse_numeric
from app.cross_framework_mapping import generate_cross_framework_report


# ═══════════════════════════════════════════════════════════════════════
# SCORING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

WEIGHTS = {
    "completeness": 0.40,
    "quality": 0.25,
    "cross_framework": 0.20,
    "depth": 0.15,
}

# Fields grouped by importance
MANDATORY_FIELDS = [
    # Section A essentials
    "cin", "company_name", "financial_year", "registered_office",
    "email", "website", "paid_up_capital", "turnover",
    "employees_permanent", "women_employees_pct",
    # Section C essentials
    "energy_consumption_total", "renewable_energy_pct",
    "ghg_scope1", "ghg_scope2", "water_withdrawal",
    "waste_generated", "waste_recycled_pct",
    "employee_turnover_rate", "safety_incidents",
    "training_hours_per_employee",
    "code_of_conduct", "anti_corruption_policy",
    "csr_spend",
]

CORE_FIELDS = [
    "ghg_scope1", "ghg_scope2", "energy_consumption_total",
    "water_withdrawal", "waste_generated",
    "employee_turnover_rate", "women_board_pct",
    "safety_incidents",
]

LEADERSHIP_FIELDS = [
    "sustainable_sourcing_pct", "recycled_input_pct",
    "human_rights_training_pct", "stakeholder_groups_identified",
    "median_salary_male", "median_salary_female",
    "r_and_d_spend", "community_beneficiaries",
    "data_privacy_complaints", "product_recalls",
]

NARRATIVE_FIELDS = [
    "code_of_conduct", "anti_corruption_policy",
    "grievance_mechanism", "stakeholder_groups_identified",
    "policy_available", "policy_web_link",
]


def _count_present(extracted_data: dict, fields: list[str]) -> int:
    """Count how many fields from the list have values."""
    count = 0
    for field in fields:
        val = _get_field_value(extracted_data, field)
        if val is not None:
            count += 1
    return count


def _score_completeness(extracted_data: dict) -> dict:
    """Score based on how many mandatory/core fields are present (0-100)."""
    mandatory_present = _count_present(extracted_data, MANDATORY_FIELDS)
    core_present = _count_present(extracted_data, CORE_FIELDS)

    mandatory_score = (mandatory_present / len(MANDATORY_FIELDS)) * 100 if MANDATORY_FIELDS else 0
    core_score = (core_present / len(CORE_FIELDS)) * 100 if CORE_FIELDS else 0

    # Weight core fields higher (60% core, 40% mandatory)
    score = core_score * 0.6 + mandatory_score * 0.4

    return {
        "score": round(score, 1),
        "mandatory_present": mandatory_present,
        "mandatory_total": len(MANDATORY_FIELDS),
        "core_present": core_present,
        "core_total": len(CORE_FIELDS),
    }


def _score_quality(extracted_data: dict) -> dict:
    """Score based on data quality — no anomalies, valid ranges, consistency."""
    validation = validate_brsr_data(extracted_data)

    # Start at 100, deduct per issue
    score = 100.0
    for issue in validation["issues"]:
        if issue["severity"] == "critical":
            score -= 15
        elif issue["severity"] == "high":
            score -= 8
        elif issue["severity"] == "medium":
            score -= 4
        elif issue["severity"] == "low":
            score -= 2

    score = max(0, score)

    return {
        "score": round(score, 1),
        "issues_found": validation["failed"],
        "critical_issues": validation["critical_issues"],
    }


def _score_cross_framework(extracted_data: dict) -> dict:
    """Score based on alignment with international frameworks."""
    report = generate_cross_framework_report(extracted_data)
    summary = report["summary"]

    # Average coverage across frameworks (weighted: ESRS > GRI > ISSB > TCFD)
    esrs_pct = summary["esrs"]["coverage_pct"]
    gri_pct = summary["gri"]["coverage_pct"]
    issb_pct = summary["issb"]["coverage_pct"]
    tcfd_pct = summary["tcfd"]["coverage_pct"]

    # Weighted average
    score = esrs_pct * 0.35 + gri_pct * 0.30 + issb_pct * 0.20 + tcfd_pct * 0.15

    return {
        "score": round(score, 1),
        "esrs_coverage_pct": esrs_pct,
        "gri_coverage_pct": gri_pct,
        "issb_coverage_pct": issb_pct,
        "tcfd_coverage_pct": tcfd_pct,
    }


def _score_depth(extracted_data: dict) -> dict:
    """Score based on leadership indicators and narrative quality."""
    leadership_present = _count_present(extracted_data, LEADERSHIP_FIELDS)
    narrative_present = _count_present(extracted_data, NARRATIVE_FIELDS)

    leadership_score = (leadership_present / len(LEADERSHIP_FIELDS)) * 100 if LEADERSHIP_FIELDS else 0
    narrative_score = (narrative_present / len(NARRATIVE_FIELDS)) * 100 if NARRATIVE_FIELDS else 0

    # Check narrative quality — longer narratives = better
    narrative_quality = 0
    for field in NARRATIVE_FIELDS:
        val = _get_field_value(extracted_data, field)
        if val and isinstance(val, str) and len(val) > 50:
            narrative_quality += 1

    quality_bonus = (narrative_quality / len(NARRATIVE_FIELDS)) * 20 if NARRATIVE_FIELDS else 0

    score = leadership_score * 0.5 + narrative_score * 0.3 + quality_bonus

    return {
        "score": round(min(100, score), 1),
        "leadership_present": leadership_present,
        "leadership_total": len(LEADERSHIP_FIELDS),
        "narrative_present": narrative_present,
        "narrative_total": len(NARRATIVE_FIELDS),
    }


def _get_rating(score: float) -> dict:
    """Convert numeric score to letter rating."""
    if score >= 85:
        return {"letter": "A", "label": "Leadership", "color": "#1B7A3D"}
    elif score >= 70:
        return {"letter": "B", "label": "Management", "color": "#4CAF50"}
    elif score >= 50:
        return {"letter": "C", "label": "Awareness", "color": "#FFC107"}
    elif score >= 30:
        return {"letter": "D", "label": "Disclosure", "color": "#FF9800"}
    else:
        return {"letter": "F", "label": "Non-Compliance", "color": "#F44336"}


def calculate_brsr_score(extracted_data: dict) -> dict:
    """
    Calculate comprehensive BRSR compliance score.

    Returns:
        {
            "overall_score": float (0-100),
            "rating": {"letter": "B", "label": "Management", "color": "#4CAF50"},
            "dimensions": {...},
            "recommendations": [...],
        }
    """
    completeness = _score_completeness(extracted_data)
    quality = _score_quality(extracted_data)
    cross_framework = _score_cross_framework(extracted_data)
    depth = _score_depth(extracted_data)

    overall = (
        completeness["score"] * WEIGHTS["completeness"]
        + quality["score"] * WEIGHTS["quality"]
        + cross_framework["score"] * WEIGHTS["cross_framework"]
        + depth["score"] * WEIGHTS["depth"]
    )

    rating = _get_rating(overall)

    # Generate recommendations
    recommendations = _generate_recommendations(
        overall, completeness, quality, cross_framework, depth, extracted_data
    )

    return {
        "overall_score": round(overall, 1),
        "rating": rating,
        "dimensions": {
            "completeness": completeness,
            "quality": quality,
            "cross_framework_alignment": cross_framework,
            "depth": depth,
        },
        "weights": WEIGHTS,
        "recommendations": recommendations,
    }


def _generate_recommendations(
    overall: float,
    completeness: dict,
    quality: dict,
    cross_framework: dict,
    depth: dict,
    extracted_data: dict,
) -> list[dict]:
    """Generate actionable recommendations to improve score."""
    recs = []

    # Completeness recommendations
    if completeness["core_present"] < completeness["core_total"]:
        missing_core = []
        for field in CORE_FIELDS:
            if _get_field_value(extracted_data, field) is None:
                missing_core.append(field)
        recs.append({
            "priority": "critical",
            "category": "completeness",
            "title": "Disclose missing BRSR Core indicators",
            "description": f"{len(missing_core)} BRSR Core fields are missing. These are mandatory for assurance from FY2024-25.",
            "missing_fields": missing_core,
            "impact": "+{:.0f} points potential".format(
                (len(missing_core) / completeness["core_total"]) * WEIGHTS["completeness"] * 60
            ),
        })

    if completeness["mandatory_present"] < completeness["mandatory_total"] * 0.8:
        recs.append({
            "priority": "high",
            "category": "completeness",
            "title": "Improve mandatory disclosure coverage",
            "description": f"Only {completeness['mandatory_present']}/{completeness['mandatory_total']} mandatory fields disclosed.",
            "impact": "Could significantly improve overall score",
        })

    # Quality recommendations
    if quality["critical_issues"] > 0:
        recs.append({
            "priority": "critical",
            "category": "quality",
            "title": "Fix critical data quality issues",
            "description": f"{quality['critical_issues']} critical validation failures found.",
            "impact": "Blocking assurance readiness",
        })

    # Cross-framework recommendations
    if cross_framework["esrs_coverage_pct"] < 50:
        recs.append({
            "priority": "medium",
            "category": "cross_framework",
            "title": "Improve ESRS alignment",
            "description": "Your BRSR disclosures cover less than 50% of equivalent ESRS requirements. This matters for EU investors.",
            "impact": "Better access to international capital",
        })

    if cross_framework["tcfd_coverage_pct"] < 50:
        recs.append({
            "priority": "medium",
            "category": "cross_framework",
            "title": "Strengthen climate disclosures (TCFD/ISSB)",
            "description": "Climate-related metrics (energy, GHG, transition plans) need improvement for TCFD/ISSB alignment.",
            "impact": "Required by global investors and ISSB-aligned markets",
        })

    # Depth recommendations
    if depth["leadership_present"] < depth["leadership_total"] * 0.5:
        recs.append({
            "priority": "low",
            "category": "depth",
            "title": "Add leadership indicators",
            "description": "Disclosing leadership-level metrics beyond essential requirements demonstrates maturity.",
            "impact": "Move from C/D rating to B/A",
        })

    return recs
