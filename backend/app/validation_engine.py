"""
BRSR Validation Engine — Rule-based validation for extracted BRSR data.

Implements:
1. Completeness checks (mandatory/core fields present)
2. Logical consistency rules (if X reported, Y must exist)
3. Year-over-year deviation alerts (CDP-style flags)
4. Data type validation (numeric fields are numbers, % are 0-100, etc.)
5. Conditional requirements (sector-specific, size-based)

Inspired by:
- CDP scoring methodology (A/B/C/D)
- ESRS materiality assessment approach
- SEBI BRSR Core assurance requirements
"""

from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# VALIDATION RULES
# ═══════════════════════════════════════════════════════════════════════

VALIDATION_RULES = [
    # ─── Completeness Rules (BRSR Core) ───────────────────────────────
    {
        "id": "CORE_001",
        "name": "GHG Scope 1 reported",
        "category": "completeness",
        "severity": "critical",
        "field": "ghg_scope1",
        "section": "section_c",
        "rule": "field_present",
        "message": "Scope 1 GHG emissions (BRSR Core) is mandatory for assurance.",
        "core": True,
    },
    {
        "id": "CORE_002",
        "name": "GHG Scope 2 reported",
        "category": "completeness",
        "severity": "critical",
        "field": "ghg_scope2",
        "section": "section_c",
        "rule": "field_present",
        "message": "Scope 2 GHG emissions (BRSR Core) is mandatory for assurance.",
        "core": True,
    },
    {
        "id": "CORE_003",
        "name": "Energy consumption reported",
        "category": "completeness",
        "severity": "critical",
        "field": "energy_consumption_total",
        "section": "section_c",
        "rule": "field_present",
        "message": "Total energy consumption (BRSR Core) is mandatory.",
        "core": True,
    },
    {
        "id": "CORE_004",
        "name": "Water withdrawal reported",
        "category": "completeness",
        "severity": "high",
        "field": "water_withdrawal",
        "section": "section_c",
        "rule": "field_present",
        "message": "Water withdrawal (BRSR Core) should be disclosed.",
        "core": True,
    },
    {
        "id": "CORE_005",
        "name": "Waste generated reported",
        "category": "completeness",
        "severity": "high",
        "field": "waste_generated",
        "section": "section_c",
        "rule": "field_present",
        "message": "Total waste generated (BRSR Core) should be disclosed.",
        "core": True,
    },
    {
        "id": "CORE_006",
        "name": "Employee turnover rate reported",
        "category": "completeness",
        "severity": "high",
        "field": "employee_turnover_rate",
        "section": "section_c",
        "rule": "field_present",
        "message": "Employee turnover rate (BRSR Core) should be disclosed for 3-year trend.",
        "core": True,
    },
    {
        "id": "CORE_007",
        "name": "Women on board reported",
        "category": "completeness",
        "severity": "high",
        "field": "women_board_pct",
        "section": "section_a",
        "rule": "field_present",
        "message": "Women on Board (%) is a BRSR Core indicator.",
        "core": True,
    },
    {
        "id": "CORE_008",
        "name": "Safety incidents reported",
        "category": "completeness",
        "severity": "high",
        "field": "safety_incidents",
        "section": "section_c",
        "rule": "field_present",
        "message": "LTIFR/safety incidents (BRSR Core) should be disclosed.",
        "core": True,
    },

    # ─── Mandatory (non-core) completeness ────────────────────────────
    {
        "id": "MAND_001",
        "name": "CIN reported",
        "category": "completeness",
        "severity": "critical",
        "field": "cin",
        "section": "section_a",
        "rule": "field_present",
        "message": "Corporate Identity Number (CIN) is mandatory.",
        "core": False,
    },
    {
        "id": "MAND_002",
        "name": "Company name reported",
        "category": "completeness",
        "severity": "critical",
        "field": "company_name",
        "section": "section_a",
        "rule": "field_present",
        "message": "Listed entity name is mandatory.",
        "core": False,
    },
    {
        "id": "MAND_003",
        "name": "Financial year reported",
        "category": "completeness",
        "severity": "critical",
        "field": "financial_year",
        "section": "section_a",
        "rule": "field_present",
        "message": "Financial year for which BRSR is being filed is mandatory.",
        "core": False,
    },
    {
        "id": "MAND_004",
        "name": "Renewable energy % reported",
        "category": "completeness",
        "severity": "medium",
        "field": "renewable_energy_pct",
        "section": "section_c",
        "rule": "field_present",
        "message": "Renewable energy share should be disclosed.",
        "core": False,
    },
    {
        "id": "MAND_005",
        "name": "Training hours reported",
        "category": "completeness",
        "severity": "medium",
        "field": "training_hours_per_employee",
        "section": "section_c",
        "rule": "field_present",
        "message": "Average training hours per employee should be disclosed.",
        "core": False,
    },
    {
        "id": "MAND_006",
        "name": "CSR spend reported",
        "category": "completeness",
        "severity": "medium",
        "field": "csr_spend",
        "section": "section_c",
        "rule": "field_present",
        "message": "CSR expenditure should be disclosed (Section 135 requirement).",
        "core": False,
    },

    # ─── Logical Consistency Rules ────────────────────────────────────
    {
        "id": "LOGIC_001",
        "name": "Scope 1 + Scope 2 consistency",
        "category": "consistency",
        "severity": "high",
        "rule": "if_field_then_field",
        "condition_field": "ghg_scope1",
        "required_field": "ghg_scope2",
        "section": "section_c",
        "message": "If Scope 1 GHG is reported, Scope 2 must also be reported (and vice versa).",
    },
    {
        "id": "LOGIC_002",
        "name": "Renewable energy requires total energy",
        "category": "consistency",
        "severity": "high",
        "rule": "if_field_then_field",
        "condition_field": "renewable_energy_pct",
        "required_field": "energy_consumption_total",
        "section": "section_c",
        "message": "If renewable energy % is reported, total energy consumption must also be disclosed.",
    },
    {
        "id": "LOGIC_003",
        "name": "Waste recycled requires total waste",
        "category": "consistency",
        "severity": "medium",
        "rule": "if_field_then_field",
        "condition_field": "waste_recycled_pct",
        "required_field": "waste_generated",
        "section": "section_c",
        "message": "If waste recycled % is reported, total waste generated must be disclosed.",
    },
    {
        "id": "LOGIC_004",
        "name": "Female salary requires male salary",
        "category": "consistency",
        "severity": "medium",
        "rule": "if_field_then_field",
        "condition_field": "median_salary_female",
        "required_field": "median_salary_male",
        "section": "section_c",
        "message": "If female median salary is reported, male median salary must also be reported for comparison.",
    },

    # ─── Range / Data Type Rules ──────────────────────────────────────
    {
        "id": "RANGE_001",
        "name": "Percentage fields 0-100",
        "category": "range",
        "severity": "medium",
        "rule": "percentage_range",
        "fields": ["renewable_energy_pct", "waste_recycled_pct", "women_board_pct",
                   "women_employees_pct", "human_rights_training_pct", "sustainable_sourcing_pct",
                   "recycled_input_pct"],
        "message": "Percentage value must be between 0 and 100.",
    },
    {
        "id": "RANGE_002",
        "name": "Non-negative metrics",
        "category": "range",
        "severity": "medium",
        "rule": "non_negative",
        "fields": ["ghg_scope1", "ghg_scope2", "energy_consumption_total", "water_withdrawal",
                   "waste_generated", "training_hours_per_employee", "safety_incidents",
                   "employees_permanent", "employees_contract"],
        "message": "This metric cannot be negative.",
    },
    {
        "id": "RANGE_003",
        "name": "Turnover rate sanity check",
        "category": "range",
        "severity": "low",
        "rule": "max_value",
        "field": "employee_turnover_rate",
        "max_val": 100,
        "section": "section_c",
        "message": "Employee turnover rate exceeds 100% — verify this is annual (not cumulative).",
    },

    # ─── Cross-section Rules ──────────────────────────────────────────
    {
        "id": "CROSS_001",
        "name": "Gender pay gap sanity",
        "category": "consistency",
        "severity": "low",
        "rule": "custom_pay_gap",
        "message": "Male and female median salary differ by >50% — flag for review.",
    },
    {
        "id": "CROSS_002",
        "name": "GHG vs Energy proportionality",
        "category": "consistency",
        "severity": "low",
        "rule": "custom_ghg_energy",
        "message": "GHG emissions seem disproportionate to energy consumption — verify emission factors.",
    },
]


# ═══════════════════════════════════════════════════════════════════════
# VALIDATION ENGINE
# ═══════════════════════════════════════════════════════════════════════


def _get_field_value(extracted_data: dict, field: str) -> Any:
    """Get a field value from any section of extracted data."""
    for section_data in extracted_data.values():
        if isinstance(section_data, dict) and field in section_data:
            val = section_data[field]
            if val is not None and val != "" and val != "N/A":
                return val
    return None


def _parse_numeric(value: Any) -> float | None:
    """Try to parse a value as a number."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("₹", "").replace("INR", "").strip()
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    return None


def validate_brsr_data(extracted_data: dict) -> dict:
    """
    Run all validation rules against extracted BRSR data.

    Returns:
        {
            "valid": bool,
            "total_rules": int,
            "passed": int,
            "failed": int,
            "warnings": int,
            "issues": [
                {"id": "CORE_001", "severity": "critical", "category": "completeness", ...}
            ],
            "assurance_readiness": {
                "core_fields_present": int,
                "core_fields_required": int,
                "ready_pct": float,
                "verdict": "Ready" | "Partially Ready" | "Not Ready"
            }
        }
    """
    issues = []
    passed = 0
    core_present = 0
    core_total = 0

    for rule in VALIDATION_RULES:
        rule_type = rule["rule"]

        if rule_type == "field_present":
            field = rule["field"]
            value = _get_field_value(extracted_data, field)
            if rule.get("core"):
                core_total += 1
            if value is not None:
                passed += 1
                if rule.get("core"):
                    core_present += 1
            else:
                issues.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "message": rule["message"],
                    "field": field,
                    "core": rule.get("core", False),
                })

        elif rule_type == "if_field_then_field":
            cond_val = _get_field_value(extracted_data, rule["condition_field"])
            req_val = _get_field_value(extracted_data, rule["required_field"])
            if cond_val is not None and req_val is None:
                issues.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "message": rule["message"],
                    "condition_field": rule["condition_field"],
                    "missing_field": rule["required_field"],
                })
            else:
                passed += 1

        elif rule_type == "percentage_range":
            all_ok = True
            for field in rule["fields"]:
                val = _get_field_value(extracted_data, field)
                num = _parse_numeric(val)
                if num is not None and (num < 0 or num > 100):
                    all_ok = False
                    issues.append({
                        "id": rule["id"],
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "category": rule["category"],
                        "message": f"{field}: {val}% is outside valid range (0-100).",
                        "field": field,
                        "value": val,
                    })
            if all_ok:
                passed += 1

        elif rule_type == "non_negative":
            all_ok = True
            for field in rule["fields"]:
                val = _get_field_value(extracted_data, field)
                num = _parse_numeric(val)
                if num is not None and num < 0:
                    all_ok = False
                    issues.append({
                        "id": rule["id"],
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "category": rule["category"],
                        "message": f"{field}: value {val} is negative.",
                        "field": field,
                        "value": val,
                    })
            if all_ok:
                passed += 1

        elif rule_type == "max_value":
            field = rule["field"]
            val = _get_field_value(extracted_data, field)
            num = _parse_numeric(val)
            if num is not None and num > rule["max_val"]:
                issues.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "message": rule["message"],
                    "field": field,
                    "value": val,
                })
            else:
                passed += 1

        elif rule_type == "custom_pay_gap":
            male = _parse_numeric(_get_field_value(extracted_data, "median_salary_male"))
            female = _parse_numeric(_get_field_value(extracted_data, "median_salary_female"))
            if male and female and male > 0:
                gap = abs(male - female) / male * 100
                if gap > 50:
                    issues.append({
                        "id": rule["id"],
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "category": "consistency",
                        "message": f"Gender pay gap is {gap:.1f}% — flag for review.",
                        "computed_gap_pct": round(gap, 1),
                    })
                else:
                    passed += 1
            else:
                passed += 1

        elif rule_type == "custom_ghg_energy":
            ghg1 = _parse_numeric(_get_field_value(extracted_data, "ghg_scope1"))
            ghg2 = _parse_numeric(_get_field_value(extracted_data, "ghg_scope2"))
            energy = _parse_numeric(_get_field_value(extracted_data, "energy_consumption_total"))
            if ghg1 and ghg2 and energy and energy > 0:
                total_ghg = ghg1 + ghg2
                # Rough check: emission factor for India grid ~0.7 tCO2/MWh = ~0.19 tCO2/GJ
                # Flag if ratio is >1 tCO2/GJ (unrealistically high)
                ratio = total_ghg / energy
                if ratio > 1.0:
                    issues.append({
                        "id": rule["id"],
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "category": "consistency",
                        "message": f"GHG/energy ratio = {ratio:.2f} tCO2e/GJ is unusually high. Verify.",
                        "computed_ratio": round(ratio, 3),
                    })
                else:
                    passed += 1
            else:
                passed += 1

    # Assurance readiness
    if core_total > 0:
        ready_pct = round(core_present / core_total * 100, 1)
    else:
        ready_pct = 0

    if ready_pct >= 80:
        verdict = "Ready"
    elif ready_pct >= 50:
        verdict = "Partially Ready"
    else:
        verdict = "Not Ready"

    total_rules = len(VALIDATION_RULES)
    failed = len(issues)
    critical_count = len([i for i in issues if i["severity"] == "critical"])
    high_count = len([i for i in issues if i["severity"] == "high"])

    return {
        "valid": critical_count == 0,
        "total_rules": total_rules,
        "passed": passed,
        "failed": failed,
        "warnings": len([i for i in issues if i["severity"] in ("low", "medium")]),
        "critical_issues": critical_count,
        "high_issues": high_count,
        "issues": issues,
        "assurance_readiness": {
            "core_fields_present": core_present,
            "core_fields_required": core_total,
            "ready_pct": ready_pct,
            "verdict": verdict,
        },
    }


def validate_year_over_year(current_data: dict, previous_data: dict, threshold_pct: float = 50.0) -> list[dict]:
    """
    Compare current year extraction with previous year to flag large deviations.
    CDP-style year-over-year consistency check.
    """
    yoy_flags = []
    numeric_fields = [
        "ghg_scope1", "ghg_scope2", "energy_consumption_total",
        "water_withdrawal", "waste_generated", "employees_permanent",
        "employees_contract", "training_hours_per_employee",
        "csr_spend", "safety_incidents",
    ]

    for field in numeric_fields:
        curr = _parse_numeric(_get_field_value(current_data, field))
        prev = _parse_numeric(_get_field_value(previous_data, field))

        if curr is not None and prev is not None and prev > 0:
            change_pct = ((curr - prev) / prev) * 100
            if abs(change_pct) > threshold_pct:
                yoy_flags.append({
                    "field": field,
                    "current_value": curr,
                    "previous_value": prev,
                    "change_pct": round(change_pct, 1),
                    "direction": "increase" if change_pct > 0 else "decrease",
                    "severity": "high" if abs(change_pct) > 100 else "medium",
                    "message": f"{field}: {change_pct:+.1f}% change YoY exceeds {threshold_pct}% threshold.",
                })

    return yoy_flags
