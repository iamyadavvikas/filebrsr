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
    "ghg_scope3": "C.P6.L.2",
    "ghg_intensity": "C.P6.E.18",
    "water_withdrawal": "C.P6.E.8",
    "water_consumption": "C.P6.E.8",
    "water_discharge": "C.P6.E.53",
    "waste_generated": "C.P6.E.29",
    "waste_recycled_pct": "C.P6.E.70",
    "waste_disposed": "C.P6.E.71",
    "employee_turnover_rate": "A.IV.19",
    "turnover_rate_male": "A.IV.19",
    "turnover_rate_female": "A.IV.20",
    "net_worth": "A.VI.3",
    "principle_complaints_filed": "A.VII.1",
    "plants_national": "A.III.1",
    "plants_international": "A.III.2",
    "offices_national": "A.III.3",
    "offices_international": "A.III.4",
    "states_served": "A.III.5",
    "countries_served": "A.III.6",
    "export_contribution_pct": "A.III.7",
    "employees_perm_male": "A.IV.1",
    "employees_perm_female": "A.IV.2",
    "employees_perm_total": "A.IV.3",
    "wf_perm_emp_m": "A.IV.1",
    "wf_perm_emp_f": "A.IV.2",
    "wf_perm_emp_t": "A.IV.3",
    "employees_other_male": "A.IV.4",
    "employees_other_female": "A.IV.5",
    "employees_other_total": "A.IV.6",
    "wf_other_emp_m": "A.IV.4",
    "wf_other_emp_f": "A.IV.5",
    "wf_other_emp_t": "A.IV.6",
    "workers_perm_male": "A.IV.7",
    "workers_perm_female": "A.IV.8",
    "workers_perm_total": "A.IV.9",
    "wf_perm_work_m": "A.IV.7",
    "wf_perm_work_f": "A.IV.8",
    "wf_perm_work_t": "A.IV.9",
    "wf_other_work_m": "A.IV.10",
    "wf_other_work_f": "A.IV.11",
    "wf_other_work_t": "A.IV.12",
    "policy_translated_to_procedures": "B.4",
    "policy_extends_value_chain": "B.5",
    "sustainability_in_board_committees": "B.11",
    "policy_external_assessment": "B.13",
    "top10_supplier_concentration_pct": "C.P1.E.13",
    "top10_customer_concentration_pct": "C.P1.E.14",
    "trading_house_purchases_pct": "C.P1.E.15",
    "trading_house_count": "C.P1.E.16",
    "dealer_sales_pct": "C.P1.E.17",
    "dealer_count": "C.P1.E.18",
    "rpt_purchases_pct": "C.P1.E.20",
    "rpt_sales_pct": "C.P1.E.21",
    "ghg_intensity_turnover": "C.P6.E.18",
    "energy_intensity_turnover": "C.P6.E.5",
    "water_intensity_turnover": "C.P6.E.13",
    "waste_intensity_turnover": "C.P6.E.30",
    "women_board_pct": "A.IV.17",
    "women_employees_pct": "A.IV.18",
    "training_hours_per_employee": "C.P3.E.3",
    "safety_incidents": "C.P3.E.22",
    "fatalities": "C.P3.E.21",
    "ltifr": "C.P3.E.20",
    "minimum_wage_compliance_pct": "C.P5.E.3",
    "human_rights_training_pct": "C.P5.E.1",
    "child_labor_complaints": "C.P5.E.2",
    "posh_complaints": "C.P5.E.7",
    "posh_filed": "C.P5.E.7",
    "posh_upheld": "C.P5.E.18",
    "posh_pct_female": "C.P5.E.17",
    "parental_return_rate_pct": "C.P3.E.11",
    "grievance_mechanism_employees": "C.P3.E.12",
    "code_of_conduct": "C.P1.E.1",
    "anti_corruption_policy": "C.P1.E.1",
    "corruption_incidents": "C.P1.E.8",
    "r_and_d_spend": "C.P2.E.1",
    "sustainable_sourcing_pct": "C.P2.E.2",
    "recycled_input_pct": "C.P2.E.3",
    "msme_sourcing_pct": "C.P8.E.1",
    "csr_spend": "C.P8.E.2",
    "consumer_complaints": "C.P9.E.1",
    "data_breach_incidents": "C.P9.E.19",
}

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


def _resolve_esrs(brsr_id: str) -> tuple[str, str] | None:
    """Resolve a BRSR id to (standard, DR): catalog first, cross-map fallback.

    The catalog carries 242 esrs_refs; the curated cross-framework table
    covers ids the catalog misses (and legacy range ids).
    """
    from app.brsr_datapoints import BRSR_DATAPOINTS
    from app.cross_framework_mapping import get_mapping_for_brsr_id

    for dp in BRSR_DATAPOINTS:
        if dp.get("id") == brsr_id and dp.get("esrs_ref"):
            parsed = parse_esrs_ref(dp["esrs_ref"])
            if parsed:
                return parsed
    mapping = get_mapping_for_brsr_id(brsr_id)
    if mapping and mapping.get("esrs_ref"):
        return parse_esrs_ref(mapping["esrs_ref"])
    return None


def _is_junk_value(value: Any) -> bool:
    """Single characters and empty strings carry no disclosure content."""
    if value is None:
        return True
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        if s == "":
            return True
        if len(s) <= 1:
            try:
                float(s)
                return False
            except ValueError:
                return True
    return False


_MEASURE_HINTS = ("ghg", "energy", "water", "waste", "emission", "fuel", "electricity")

# Fields whose BRSR answers are Yes/No or prose — a bare number here is
# almost always a page number, footnote index, or table counter.
TEXT_EXPECTED_FIELDS = frozenset({
    "code_of_conduct", "anti_corruption_policy", "policy_available",
    "policy_approved_by_board", "policy_translated_to_procedures",
    "policy_extends_value_chain", "sustainability_in_board_committees",
    "policy_external_assessment", "grievance_mechanism",
    "grievance_mechanism_employees", "stakeholder_groups_identified",
    "trade_associations",
})


def _is_measure_field(field: str) -> bool:
    f = field.lower()
    return any(k in f for k in _MEASURE_HINTS)


def _unit_family(unit: str) -> str | None:
    """Which physical family a unit token belongs to (None if unknown)."""
    from app.normalise import ENERGY_TO_MWH, MASS_TO_TONNES, VOLUME_TO_M3

    u = (unit or "").upper()
    if u in ENERGY_TO_MWH:
        return "energy"
    if u in VOLUME_TO_M3:
        return "volume"
    if u in MASS_TO_TONNES:
        return "mass"
    if u == "%":
        return "percent"
    return None


def _expected_family(field: str) -> str | None:
    f = field.lower()
    if any(k in f for k in ("ghg", "emission", "waste")):
        return "mass"
    if "energy" in f or "fuel" in f or "electricity" in f:
        return "energy"
    if "water" in f:
        return "volume"
    return None


_UNIT_TOKEN_RE = re.compile(
    r"(tCO2e?|tonnes?|MT\b|kg\b|MWh|kWh|GWh|[GTM]J\b|ML\b|KL\b|m3\b|%|Rs\b|INR\b|EUR\b|USD\b)",
    re.IGNORECASE,
)


def _snippet_unit(snippet: str | None) -> str | None:
    """Recover a unit token from the citation snippet.

    Regex captures numbers but drops their units; the snippet usually
    still carries them ("Scope 1 emissions: 1200 tCO2e"). Without this,
    good extractions look unitless and get weak-flagged.
    """
    if not snippet:
        return None
    m = _UNIT_TOKEN_RE.search(snippet)
    return m.group(1) if m else None


def _flat_fields(extracted_data: dict[str, Any]) -> dict[str, tuple[str, Any]]:
    """Flatten sections to field -> (section, value), skipping empties."""
    flat: dict[str, tuple[str, Any]] = {}
    for section in ("section_a", "section_b", "section_c"):
        part = (extracted_data or {}).get(section)
        if isinstance(part, dict):
            for k, v in part.items():
                if k not in flat and v is not None and v != "":
                    flat[k] = (section, v)
    return flat


def brsr_fields_to_esrs_candidates(
    extracted_data: dict[str, Any],
    confidence_scores: dict[str, Any] | None = None,
    *,
    max_candidates: int = 200,
) -> dict[str, Any]:
    """Convert pipeline output into reviewable ESRS candidates."""
    from app.esrs_datapoints import ESRS_DATAPOINTS

    confidence_scores = confidence_scores or {}
    citations = (extracted_data or {}).get("citations") or {}
    normalised = (extracted_data or {}).get("normalised") or {}
    by_std_dr: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for dp in ESRS_DATAPOINTS:
        by_std_dr.setdefault((dp.get("standard"), dp.get("dr")), []).append(dp)

    candidates: list[dict[str, Any]] = []
    fields_seen = 0
    fields_mapped = 0
    dropped_junk = 0
    for field, (section, value) in _flat_fields(extracted_data).items():
        brsr_id = FIELD_TO_BRSR.get(field)
        if not brsr_id:
            continue
        if _is_junk_value(value):
            dropped_junk += 1
            continue
        fields_seen += 1
        parsed = _resolve_esrs(brsr_id)
        if not parsed:
            continue
        dps = by_std_dr.get(parsed, [])
        if not dps:
            continue
        fields_mapped += 1
        conf = confidence_scores.get(field, confidence_scores.get(f"{section}.{field}"))
        try:
            conf_f = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf_f = None
        cite = (citations.get(section) or {}).get(field) or {}
        norm = (normalised.get(section) or {}).get(field) or {}
        unit = norm.get("unit") or ""
        if isinstance(norm.get("value"), (int, float)):
            from app.normalise import canonicalise

            display_value, unit, converted = canonicalise(float(norm["value"]), unit)
            if not unit:
                converted = False
        else:
            display_value = value
            converted = False
        # Sanity: measure-class fields with no unit context are weak
        # (page numbers, table indices, stray counts). Snippets often
        # retain the unit the regex capture dropped — recover it first.
        weak_reasons: list[str] = []
        if _is_measure_field(field) and not unit:
            recovered = _snippet_unit(cite.get("snippet"))
            if recovered:
                unit = recovered
            else:
                weak_reasons.append("no_unit")
                if conf_f is not None:
                    conf_f = min(conf_f, 0.3)
                else:
                    conf_f = 0.3
        if (field in TEXT_EXPECTED_FIELDS and isinstance(display_value, (int, float))
                and not isinstance(display_value, bool)):
            weak_reasons.append("unexpected_number")
            if conf_f is not None:
                conf_f = min(conf_f, 0.3)
            else:
                conf_f = 0.3
        # Unit-family validation against the field's physical class.
        expected = _expected_family(field)
        fam = _unit_family(unit) if unit else None
        if unit and expected and fam and fam != expected and fam != "percent":
            weak_reasons.append(f"unit_mismatch:{unit}")
            if conf_f is not None:
                conf_f = min(conf_f, 0.35)
        for dp in dps:
            dtype = dp.get("data_type") or ""
            bare_number = isinstance(display_value, (int, float)) and not isinstance(display_value, bool)
            if dtype == "narrative" or (dtype == "semi-narrative" and bare_number):
                # Prose datapoints take text, not bare numbers — keep the
                # figure attached but route to snippet-review (in_progress)
                # so the assessor writes proper prose instead of confirming
                # a naked number.
                if not cite.get("snippet"):
                    weak_reasons.append("no_snippet")
                    if conf_f is not None:
                        conf_f = min(conf_f, 0.3)
                    else:
                        conf_f = 0.3
                candidates.append({
                    "datapoint_id": dp["id"],
                    "dr": dp.get("dr"),
                    "standard": dp.get("standard"),
                    "name": dp.get("name"),
                    "value": display_value,
                    "raw_value": value if display_value != value else None,
                    "unit": unit or None,
                    "unit_converted": converted,
                    "confidence": conf_f,
                    "source_page": cite.get("source_page"),
                    "snippet": cite.get("snippet"),
                    "match_kind": cite.get("match_kind"),
                    "source_brsr_id": brsr_id,
                    "source_field": field,
                    "status": "in_progress",
                    "needs_writing": True,
                    "weak_reasons": weak_reasons,
                })
                continue
            candidates.append({
                "datapoint_id": dp["id"],
                "dr": dp.get("dr"),
                "standard": dp.get("standard"),
                "name": dp.get("name"),
                "value": display_value,
                "raw_value": value if display_value != value else None,
                "unit": unit or None,
                "unit_converted": converted,
                "confidence": conf_f if conf_f is not None else (0.3 if weak_reasons else None),
                "source_page": cite.get("source_page"),
                "snippet": cite.get("snippet"),
                "match_kind": cite.get("match_kind"),
                "source_brsr_id": brsr_id,
                "source_field": field,
                "status": "reported",
                "weak_reasons": weak_reasons,
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
            "dropped_junk": dropped_junk,
            "candidates": len(candidates),
            "capped": len(candidates) >= max_candidates,
        },
    }
