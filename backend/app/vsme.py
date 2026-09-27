"""VSME feeder: Voluntary SME standard (EFRAG, Dec 2024) Basic Module.

The VSME Basic Module (B1-B11) is the mid-cap on-ramp to full ESRS Set 1:
a small enterprise answers ~30 feeder metrics once, and
:func:`upgrade_prefill` converts those answers into prefilled ESRS entries
(``source="vsme-feeder"``) so the CSRD workspace starts populated instead
of blank. Policy/narrative answers with no numeric ESRS counterpart feed
the MDR-P narrative (``narrative_feeds``) rather than inventing tags.

``code`` values (``VB3.1`` …) are this module's feeder coding, grouped by
the VSME Basic disclosure area in ``area``. Every ``maps_to`` id is a real
ESRS datapoint id — enforced by tests via ``by_id``.
"""

from __future__ import annotations

from typing import Any, Optional

VSME_VERSION = "EFRAG VSME ED Final (Dec 2024), Basic Module"


def _m(
    code: str,
    area: str,
    name: str,
    data_type: str,
    maps_to: list[str],
    unit: Optional[str] = None,
    narrative_feeds: Optional[str] = None,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "code": code,
        "module": "basic",
        "area": area,
        "name": name,
        "data_type": data_type,
        "unit": unit,
        "maps_to": maps_to,
        "narrative_feeds": narrative_feeds,
        "required": required,
    }


VSME_BASIC: list[dict[str, Any]] = [
    # B1 — Basis for preparation
    _m("VB1.1", "B1", "Reporting boundary and basis of preparation", "narrative",
       ["ESRS2.BP-1.3"]),
    _m("VB1.2", "B1", "Information arising from other EU legislation", "narrative",
       ["ESRS2.BP-2.8"], required=False),
    # B2 — Practices, policies, future initiatives
    _m("VB2.1", "B2", "Sustainability practices and transition initiatives", "narrative",
       [], narrative_feeds="MDR-P actions narrative"),
    _m("VB2.2", "B2", "Climate mitigation target adopted (Y/N + year + %)", "composite",
       ["E1.E1-4.33"], required=False),
    # B3 — Energy and GHG
    _m("VB3.1", "B3", "Total energy consumption", "number",
       ["E1.E1-5.37"], unit="MWh"),
    _m("VB3.2", "B3", "Share of energy from renewable sources", "number",
       ["E1.E1-5.37"], unit="%"),
    _m("VB3.3", "B3", "Gross Scope 1 GHG emissions", "number",
       ["E1.E1-6.44"], unit="tCO2e"),
    _m("VB3.4", "B3", "Gross Scope 2 GHG emissions (location-based)", "number",
       ["E1.E1-6.44"], unit="tCO2e"),
    _m("VB3.5", "B3", "Scope 2 market-based (if tracked)", "number",
       ["E1.E1-6.44"], unit="tCO2e", required=False),
    _m("VB3.6", "B3", "GHG intensity (Scope 1+2 per revenue)", "number",
       ["E1.E1-6.44"], unit="tCO2e/EUR", required=False),
    _m("VB3.7", "B3", "Internal carbon price in use (Y/N + price)", "composite",
       ["E1.E1-8.59"], required=False),
    # B4 — Pollution
    _m("VB4.1", "B4", "Pollutants discharged to air, water, soil", "narrative",
       ["E2.E2-4.20"], required=False),
    # B5 — Biodiversity
    _m("VB5.1", "B5", "Sites near biodiversity-sensitive areas (Y/N + ha)", "composite",
       ["E4.E4-5.37"], required=False),
    # B6 — Water
    _m("VB6.1", "B6", "Total water withdrawal", "number",
       ["E3.E3-4.24"], unit="m3"),
    _m("VB6.2", "B6", "Total water consumption", "number",
       ["E3.E3-4.24"], unit="m3"),
    # B7 — Resource use, circularity, waste
    _m("VB7.1", "B7", "Total waste generated", "number",
       ["E5.E5-5.37"], unit="tonnes"),
    _m("VB7.2", "B7", "Share of waste recycled / recovered", "number",
       ["E5.E5-5.37"], unit="%"),
    _m("VB7.3", "B7", "Hazardous waste generated", "number",
       ["E5.E5-5.37"], unit="tonnes", required=False),
    # B8 — Workforce, general characteristics
    _m("VB8.1", "B8", "Total headcount (employees)", "integer",
       ["S1.S1-6.40"]),
    _m("VB8.2", "B8", "Headcount by gender (F/M)", "composite",
       ["S1.S1-6.40"]),
    _m("VB8.3", "B8", "Non-employees in own workforce", "integer",
       ["S1.S1-7.51"], required=False),
    _m("VB8.4", "B8", "Employee turnover rate", "number",
       ["S1.S1-6.40"], unit="%", required=False),
    _m("VB8.5", "B8", "Gender split in top management", "composite",
       ["S1.S1-9.57"], required=False),
    # B9 — Workforce health & safety
    _m("VB9.1", "B9", "Recordable work-related injuries", "integer",
       ["S1.S1-14.67"]),
    _m("VB9.2", "B9", "Work-related fatalities", "integer",
       ["S1.S1-14.67"]),
    _m("VB9.3", "B9", "Share of workforce covered by H&S system", "number",
       ["S1.S1-14.67"], unit="%", required=False),
    # B10 — Governance: responsibilities & policies (VSME Basic)
    _m("VB10.1", "B10", "Governance body composition and roles", "narrative",
       ["ESRS2.GOV-1.21"]),
    _m("VB10.2", "B10", "Anti-corruption policy in place (Y/N)", "boolean",
       [], narrative_feeds="G1 MDR-P narrative"),
    _m("VB10.3", "B10", "Confirmed corruption/bribery incidents", "integer",
       ["G1.G1-3.20"]),
    _m("VB10.4", "B10", "Dismissals for corruption-related breaches", "integer",
       ["G1.G1-4.25"], required=False),
    # B11 — Business conduct anchors
    _m("VB11.1", "B11", "Significant sectors and revenue (for intensity denominators)", "composite",
       ["ESRS2.SBM-1.38"]),
    _m("VB11.2", "B11", "Climate actions and resources deployed", "narrative",
       ["E1.E1-3.23"], required=False),
]

BY_CODE: dict[str, dict[str, Any]] = {m["code"]: m for m in VSME_BASIC}


def upgrade_prefill(answers: dict[str, Any]) -> dict[str, Any]:
    """Convert VSME feeder answers into ESRS prefill entries.

    ``answers`` maps feeder ``code`` -> value. Returns
    ``{"entries": [{datapoint_id, status, value, source, note}], "unmapped": [codes]}``.
    Values that are None/empty are skipped; composite values pass through
    as-is for the assessor to split in the registry.
    """
    entries: list[dict[str, Any]] = []
    unmapped: list[str] = []
    for code, value in (answers or {}).items():
        metric = BY_CODE.get(code)
        if metric is None:
            unmapped.append(code)
            continue
        if value is None or value == "":
            continue
        if not metric["maps_to"]:
            unmapped.append(code)
            continue
        for dp_id in metric["maps_to"]:
            entries.append(
                {
                    "datapoint_id": dp_id,
                    "status": "reported",
                    "value": value,
                    "source": "vsme-feeder",
                    "note": f"Prefilled from VSME {code} ({metric['name']}) — verify before filing.",
                }
            )
    # De-duplicate: same datapoint from several feeder metrics keeps the first.
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for e in entries:
        if e["datapoint_id"] not in seen:
            seen.add(e["datapoint_id"])
            deduped.append(e)
    return {"entries": deduped, "unmapped": sorted(set(unmapped)), "vsme_version": VSME_VERSION}
