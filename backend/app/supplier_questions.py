"""Supplier questionnaires: BRSR Section A.V set + ESRS S2 set.

Short, answerable question sets a vendor completes over a magic link.
Each question optionally maps to an ESRS datapoint so confirmed responses
can prefill workspace entries (``source="supplier"``) through the same
review discipline as AI extraction: prefill proposes, the client confirms.

``maps_to`` ids are verified against the registry in tests.
"""

from __future__ import annotations

from typing import Any

QUESTIONNAIRES: dict[str, dict[str, Any]] = {
    "brsr_a5": {
        "title": "BRSR supplier basics (Section A.V family)",
        "description": "Identity, workforce scale, environmental footprint and conduct policies.",
    },
    "esrs_s2": {
        "title": "ESRS S2 value-chain workers",
        "description": "Working conditions, collective bargaining, incidents and remediation in the value chain.",
    },
}


def _q(code: str, text: str, data_type: str, maps_to: list[str] | None = None,
       unit: str | None = None, required: bool = True) -> dict[str, Any]:
    return {"code": code, "text": text, "data_type": data_type,
            "maps_to": maps_to or [], "unit": unit, "required": required}


QUESTIONS: dict[str, list[dict[str, Any]]] = {
    "brsr_a5": [
        _q("SUP1", "Legal name and location of operations", "narrative", []),
        _q("SUP2", "Total employees (all sites serving us)", "integer", ["S1.S1-6.40"]),
        _q("SUP3", "Share of women in workforce (%)", "number", ["S1.S1-9.57"], unit="%"),
        _q("SUP4", "Scope 1 GHG emissions attributable to our orders", "number", ["E1.E1-6.44"], unit="tCO2e"),
        _q("SUP5", "Scope 2 GHG emissions attributable to our orders", "number", ["E1.E1-6.44"], unit="tCO2e"),
        _q("SUP6", "Renewable electricity share (%)", "number", ["E1.E1-5.37"], unit="%"),
        _q("SUP7", "Total water consumption", "number", ["E3.E3-4.24"], unit="m3"),
        _q("SUP8", "Waste generated / recycled (%)", "number", ["E5.E5-5.37"], unit="%"),
        _q("SUP9", "Code of conduct + anti-corruption policy in place (Y/N + link)", "composite", []),
        _q("SUP10", "Recordable safety incidents (last FY)", "integer", ["S1.S1-14.67"]),
        _q("SUP11", "Grievance mechanism for workers (Y/N + description)", "composite", []),
        _q("SUP12", "MSME / small-producer status (Y/N + certificate)", "composite", []),
    ],
    "esrs_s2": [
        _q("S2Q1", "Countries of operation for work performed for us", "narrative", []),
        _q("S2Q2", "Value-chain workers covered (headcount estimate)", "integer", ["S1.S1-7.51"]),
        _q("S2Q3", "Collective bargaining coverage (%)", "number", [], unit="%", required=False),
        _q("S2Q4", "Severe human-rights incidents linked to our orders (count + remediation)", "composite", ["S1.S1-17.79"]),
        _q("S2Q5", "Child/forced labour risk screening performed (Y/N + method)", "composite", []),
        _q("S2Q6", "Living-wage assessment for lowest-paid tier (Y/N + gap %)", "composite", ["S1.S1-10.60"], required=False),
        _q("S2Q7", "Worker fatalities in value chain (count)", "integer", ["S1.S1-14.67"]),
        _q("S2Q8", "Corrective action plans open with deadlines", "narrative", [], required=False),
        _q("S2Q9", "Audit/certification held (SA8000, SMETA, ISO 45001…)", "narrative", [], required=False),
        _q("S2Q10", "Contact for follow-up queries", "narrative", []),
    ],
}

BY_CODE: dict[str, dict[str, Any]] = {q["code"]: q for qs in QUESTIONS.values() for q in qs}


def prefill_from_answers(questionnaire: str, answers: dict[str, Any]) -> dict[str, Any]:
    """Convert supplier answers into ESRS prefill entries (review-first).

    Returns {"entries": [...], "unmapped": [...]} mirroring the VSME
    upgrade shape so the same review UI pattern applies.
    """
    if questionnaire not in QUESTIONS:
        raise ValueError(f"unknown questionnaire {questionnaire!r}")
    defs = {q["code"]: q for q in QUESTIONS[questionnaire]}
    entries: list[dict[str, Any]] = []
    unmapped: list[str] = []
    for code, value in (answers or {}).items():
        q = defs.get(code)
        if q is None:
            unmapped.append(code)
            continue
        if value is None or value == "":
            continue
        if not q["maps_to"]:
            unmapped.append(code)
            continue
        for dp_id in q["maps_to"]:
            entries.append({
                "datapoint_id": dp_id,
                "status": "reported",
                "value": value,
                "source": "supplier",
                "note": f"Supplier-reported via {questionnaire}/{code} — verify before filing.",
            })
    seen: set[str] = set()
    deduped = [e for e in entries if not (e["datapoint_id"] in seen or seen.add(e["datapoint_id"]))]
    return {"entries": deduped, "unmapped": sorted(set(unmapped))}
