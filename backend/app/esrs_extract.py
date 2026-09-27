"""BRSR extraction -> ESRS candidate bridge (CSRD Upload & Extract).

Runs the existing BRSR PDF pipeline (:func:`run_full_extraction`) and
converts its flat field output into reviewable ESRS datapoint candidates:

BRSR field --(FIELD_TO_BRSR)--> BRSR id --(cross-framework map)--> ESRS
paragraph ref --(registry DR index)--> ESRS datapoint ids.

Nothing is saved by this module — the workspace shows candidates for
human review and confirms through the normal ``POST /entries`` bulk path
(``source="ai-extract"`` with the pipeline confidence attached).
"""

from __future__ import annotations

import re
from typing import Any

# BRSR pipeline field -> BRSR catalog id (extends the seed map inside
# generate_cross_framework_report with the fields the regex/enhanced
# extractors actually emit).
FIELD_TO_BRSR: dict[str, str] = {
    "energy_consumption_total": "C.P6.E.1",
    "renewable_energy_pct": "C.P6.E.2",
    "ghg_scope1": "C.P6.E.3",
    "ghg_scope2": "C.P6.E.4",
    "ghg_scope3": "C.P6.E.5",
    "ghg_intensity": "C.P6.E.6",
    "water_withdrawal": "C.P6.E.6",
    "water_consumption": "C.P6.E.7",
    "water_discharge": "C.P6.E.8",
    "waste_generated": "C.P6.E.8",
    "waste_recycled_pct": "C.P6.E.9",
    "waste_disposed": "C.P6.E.10",
    "employee_turnover_rate": "A.IV.19-22",
    "employee_headcount": "A.IV.1-3",
    "women_board_pct": "A.IV.17",
    "women_employees_pct": "A.IV.18",
    "training_hours_per_employee": "C.P3.E.3",
    "safety_incidents": "C.P3.E.2",
    "fatalities": "C.P3.E.2",
    "ltifr": "C.P3.E.2",
    "median_salary_male": "C.P3.E.4",
    "median_salary_female": "C.P3.E.4",
    "minimum_wage_compliance_pct": "C.P3.E.5",
    "human_rights_training_pct": "C.P5.E.1",
    "child_labor_complaints": "C.P5.E.2",
    "posh_complaints": "C.P5.E.3",
    "code_of_conduct": "C.P1.E.1",
    "anti_corruption_policy": "C.P1.E.1",
    "corruption_incidents": "C.P1.E.2",
    "r_and_d_spend": "C.P2.E.1",
    "sustainable_sourcing_pct": "C.P2.E.2",
    "recycled_input_pct": "C.P2.E.3",
    "msme_sourcing_pct": "C.P8.E.1",
    "csr_spend": "C.P8.E.2",
    "consumer_complaints": "C.P9.E.1",
    "data_breach_incidents": "C.P9.E.2",
}

# "ESRS S1-6.50(a)" -> ("S1", "S1-6"); "ESRS 2 BP-1" -> ("2", "BP-1").
# "ESRS E1-6.44(a)" -> ("E1", "E1-6"); "ESRS 2 BP-1" -> ("2", "BP-1").
_ESRS_REF_RE = re.compile(r"ESRS\s+(2|[A-Z]+\d*(?:-[A-Za-z0-9]+)?)")


def parse_esrs_ref(ref: str) -> tuple[str, str] | None:
    """Split an ESRS paragraph ref into (standard, DR)."""
    m = _ESRS_REF_RE.search(ref or "")
    if not m:
        return None
    token = m.group(1)
    if token == "2":
        # "ESRS 2 BP-1..." — DR follows as the next token.
        rest = (ref[m.end():] or "").strip()
        dm = re.match(r"([A-Za-z0-9]+(?:-[A-Za-z0-9]+)?)", rest)
        if not dm:
            return None
        return "2", dm.group(1)
    # Fused form: "E1-6.44(a)" -> standard "E1", DR "E1-6".
    dr = token.split(".")[0]
    std = dr.split("-")[0]
    if not std or not dr:
        return None
    return std, dr


def _flat_fields(extracted_data: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for section in ("section_a", "section_b", "section_c", "normalised"):
        part = (extracted_data or {}).get(section)
        if isinstance(part, dict):
            for k, v in part.items():
                if k not in flat and v is not None:
                    flat[k] = v
    return flat


def brsr_fields_to_esrs_candidates(
    extracted_data: dict[str, Any],
    confidence_scores: dict[str, Any] | None = None,
    *,
    max_candidates: int = 200,
) -> dict[str, Any]:
    """Convert pipeline output into reviewable ESRS candidates."""
    from app.cross_framework_mapping import get_mapping_for_brsr_id
    from app.esrs_datapoints import ESRS_DATAPOINTS

    confidence_scores = confidence_scores or {}
    by_std_dr: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for dp in ESRS_DATAPOINTS:
        by_std_dr.setdefault((dp.get("standard"), dp.get("dr")), []).append(dp)

    candidates: list[dict[str, Any]] = []
    fields_seen = 0
    fields_mapped = 0
    for field, value in _flat_fields(extracted_data).items():
        if value is None or value == "":
            continue
        brsr_id = FIELD_TO_BRSR.get(field)
        if not brsr_id:
            continue
        fields_seen += 1
        mapping = get_mapping_for_brsr_id(brsr_id)
        if not mapping or not mapping.get("esrs_ref"):
            continue
        parsed = parse_esrs_ref(mapping["esrs_ref"])
        if not parsed:
            continue
        dps = by_std_dr.get(parsed, [])
        if not dps:
            continue
        fields_mapped += 1
        conf = confidence_scores.get(field)
        try:
            conf_f = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf_f = None
        for dp in dps:
            candidates.append({
                "datapoint_id": dp["id"],
                "dr": dp.get("dr"),
                "standard": dp.get("standard"),
                "name": dp.get("name"),
                "value": value,
                "confidence": conf_f,
                "source_brsr_id": brsr_id,
                "source_field": field,
                "status": "reported",
            })
            if len(candidates) >= max_candidates:
                break
        if len(candidates) >= max_candidates:
            break

    return {
        "candidates": candidates,
        "stats": {
            "fields_seen": fields_seen,
            "fields_mapped": fields_mapped,
            "candidates": len(candidates),
            "capped": len(candidates) >= max_candidates,
        },
    }
