"""
Canonical SEBI BRSR Core registry.

Source of truth for what actually falls under BRSR Core assurance — derived from
SEBI's BRSR Core format (Annexure I, sebi_doc/brsr_core_text.txt) and the
assurance phase-in of CIR no. 2023/122 (sebi_doc/1689166456465.pdf), with the
ISF reporting standards of CIR no. 2024/177 (sebi_doc/1734693844962.pdf).

Background: the legacy `core=True` flags on BRSR_DATAPOINTS over-flag (~121 data
points) because they treat most mandatory fields as "Core". The actual BRSR Core
is exactly NINE ESG attributes with ~43 measurable/assurable parameters. This
module is the canonical list those flags must be reconciled against.

The nine attributes:
    1  GHG footprint (Scope 1, Scope 2, intensity)
    2  Water footprint (consumption, intensity, discharge by treatment)
    3  Energy footprint (consumption, % renewable, intensity)
    4  Embracing circularity — waste management (A–H categories, total,
       intensity, recovery, disposal)
    5  Enhancing employee wellbeing and safety (wellbeing spend, disabilities,
       LTIFR, fatalities)
    6  Enabling gender diversity (female gross wages %, POSH complaints)
    7  Enabling inclusive development (MSME/in-country sourcing, smaller-town
       wages)
    8  Fairness in engaging with customers & suppliers (customer-data breaches,
       days of accounts payable)
    9  Open-ness of business (trading houses, dealers/distributors, RPTs)

Cross-reference note: the Annexure text cites BRSR question numbers from the
older layout (e.g. GHG = "P6 Q7"), but the platform's BRSR_DATAPOINTS catalog
uses the updated-format numbering (GHG = P6 Q4). Both are preserved:
`cross_ref` = annexure citation, `cross_ref_datapoints` = catalog ids.
"""

from __future__ import annotations

import re
from typing import Any

ATTRIBUTES: list[dict[str, str]] = [
    {"sr": "1", "name": "GHG footprint", "cross_ref": "P6/Q7/E",
     "summary": "Scope 1 and Scope 2 GHG emissions and Scope 1+2 intensity (revenue-PPP and output)."},
    {"sr": "2", "name": "Water footprint", "cross_ref": "P6/Q3/E",
     "summary": "Total water consumption, consumption intensity, and discharge by destination and treatment level."},
    {"sr": "3", "name": "Energy footprint", "cross_ref": "P6/Q1/E",
     "summary": "Total energy consumed, % from renewable sources, and energy intensity."},
    {"sr": "4", "name": "Embracing circularity (waste management)", "cross_ref": "P6/Q9/E",
     "summary": "Waste by category A–H, total, intensity, recovery, and disposal by method."},
    {"sr": "5", "name": "Enhancing employee wellbeing and safety", "cross_ref": "P3/Q1(c)&Q11/E",
     "summary": "Wellbeing spend as % of revenue, permanent disabilities, LTIFR, fatalities."},
    {"sr": "6", "name": "Enabling gender diversity in business", "cross_ref": "P5/Q3(b)&Q7/E",
     "summary": "Gross female wages %, POSH complaints reported / % of female staff / upheld."},
    {"sr": "7", "name": "Enabling inclusive development", "cross_ref": "P8/Q4&Q5/E",
     "summary": "MSME/in-India sourcing % and wages paid in smaller towns as % of wage cost."},
    {"sr": "8", "name": "Fairness in engaging with customers and suppliers", "cross_ref": "P9/Q7 & P1/Q8/E",
     "summary": "Customer-data breach/cyber incidents % and days of accounts payable."},
    {"sr": "9", "name": "Open-ness of business", "cross_ref": "P1/Q9/E",
     "summary": "Concentration of purchases/sales with trading houses, dealers/distributors (incl. top-10) and RPTs."},
]

# Legacy `brsr_core_kpis.kpi_code` values that do NOT belong to the nine Core
# attributes (BRSR metrics, but not part of BRSR Core assurance scope). These
# should be retired from the KPI table or moved to a general KPI registry.
NON_CORE_LEGACY_KPI_CODES = {
    "wages_complaints_resolved_pct": "P5 Q10 wages-compliance assessment — BRSR, not Core",
    "gender_diversity_board_pct": "P2 board diversity — BRSR, not Core",
    "training_coverage_pct": "P3 essential training coverage — BRSR, not Core",
    "directors_renumeration_to_median_ratio": "P5 Q3 remuneration ratio — BRSR, not Core",
    "csr_spend_pct_of_pat": "P8 CSR spend — BRSR, not Core",
}


def _kpi(
    code: str,
    attribute: int,
    label: str,
    parameter: str,
    unit: str,
    data_type: str,
    cross_ref: str,
    cross_ref_datapoints: list[str],
    measurement: str,
    ppp_adjusted: bool = False,
    output_denominator: bool = False,
    value_chain_kpi: bool = False,
    catalog_gap: bool = False,
    legacy_kpi_code: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "attribute": attribute,
        "label": label,
        "parameter": parameter,
        "unit": unit,
        "data_type": data_type,
        "mandatory": True,
        "core": True,
        "cross_ref": cross_ref,
        "cross_ref_datapoints": cross_ref_datapoints,
        "measurement": measurement,
        "ppp_adjusted": ppp_adjusted,
        "output_denominator": output_denominator,
        "value_chain_kpi": value_chain_kpi,
        "catalog_gap": catalog_gap,
        "legacy_kpi_code": legacy_kpi_code,
        "source": "SEBI BRSR Core Annexure I (sebi_doc/brsr_core_text.txt)",
    }


# Each entry is one parameter SEBI names in Annexure I that is subject to
# assurance. `catalog_gap` marks parameters the 337-row BRSR_DATAPOINTS catalog
# does not yet model (they must be added when core flags are reconciled).
BRSC: list[dict[str, Any]] = [
    # ── Attribute 1: GHG footprint ─────────────────────────────────────────
    _kpi("BRSC-1.1", 1, "Total Scope 1 GHG emissions",
         "Direct GHG emissions from owned/controlled sources, broken into CO2, CH4, N2O, HFCs, PFCs, SF6, NF3",
         "Mn MT / KT / MT (tCO2e)", "mass", "P6/Q7/E",
         ["C.P6.E.16"],
         "Fossil fuel consumption × emission factor − carbon capture + process (non-fuel) emissions + fugitive emissions. "
         "Emission factor: IPCC or actual testing from accredited lab.",
         value_chain_kpi=True),
    _kpi("BRSC-1.2", 1, "Total Scope 2 GHG emissions",
         "Indirect emissions from purchased electricity/steam/refrigeration",
         "Mn MT / KT / MT (tCO2e)", "mass", "P6/Q7/E",
         ["C.P6.E.17"],
         "Total purchased energy consumption × CO2e emission factor across all purchased energy sources. "
         "India grid: latest applicable CEA grid emission factor.",
         value_chain_kpi=True),
    _kpi("BRSC-1.3", 1, "GHG emission intensity (Scope 1+2)",
         "Scope 1 + Scope 2 emissions / revenue adjusted for PPP (and sector-specific output)",
         "tCO2e / INR-PPP (and / unit output)", "intensity", "P6/Q7/E",
         ["C.P6.E.63", "C.P6.E.64"],
         "Total emission (Scopes 1 & 2) / total revenue from operations adjusted for PPP; "
         "sector-specific option: e.g. tCO2e per vehicle / MT material / Mn TB / seat / room-night.",
         ppp_adjusted=True, output_denominator=True, value_chain_kpi=True,
         legacy_kpi_code="ghg_intensity_per_crore_turnover"),
    # ── Attribute 2: Water footprint ───────────────────────────────────────
    _kpi("BRSC-2.1", 2, "Total water consumption",
         "Water withdrawn and consumed (not returned / no longer available to ecosystem)",
         "Mn Lt or KL", "volume", "P6/Q3/E",
         ["C.P6.E.12"],
         "Calibrated input minus output flow-meter logs; consumption = input − output.",
         value_chain_kpi=True),
    _kpi("BRSC-2.2", 2, "Water consumption intensity",
         "Total water consumed / revenue adjusted for PPP (and sector-specific output)",
         "Mn Lt or KL / INR-PPP", "intensity", "P6/Q3/E",
         ["C.P6.E.50", "C.P6.E.51"],
         "Total water consumed / total revenue (audited P&L) adjusted for PPP; "
         "sector-specific option (vehicles, MT material, seats, etc.).",
         ppp_adjusted=True, output_denominator=True, value_chain_kpi=True,
         legacy_kpi_code="water_intensity_per_crore_turnover"),
    _kpi("BRSC-2.3", 2, "Water discharge by destination and levels of treatment",
         "Discharge volume by destination and treatment level (untreated, primary, secondary, tertiary)",
         "Mn Lt or KL", "volume", "P6/Q3/E",
         ["C.P6.E.14", "C.P6.E.53"],
         "Report untreated, primary treatment (filtration/screening/sedimentation), secondary "
         "(oxidation/digestion), tertiary (disinfection/pathogen removal).",
         value_chain_kpi=True),
    # ── Attribute 3: Energy footprint ──────────────────────────────────────
    _kpi("BRSC-3.1", 3, "Total energy consumed",
         "Non-renewable + renewable fuel + purchased electricity/heating/cooling/steam + self-generated (count once)",
         "Joules or multiples", "energy", "P6/Q1/E",
         ["C.P6.E.43"],
         "Total energy consumption = non-renewable fuel + renewable fuel + purchased electricity/heating/cooling/steam "
         "+ self-generated; self-generated fuel consumed counts once.",
         value_chain_kpi=True),
    _kpi("BRSC-3.2", 3, "% of energy consumed from renewable sources",
         "Share of renewable energy in total energy consumed",
         "%", "percent", "P6/Q1/E",
         ["C.P6.E.1", "C.P6.E.40"],
         "Energy consumed through renewable sources / total energy consumed.",
         value_chain_kpi=True),
    _kpi("BRSC-3.3", 3, "Energy intensity",
         "Total energy consumed / revenue adjusted for PPP (and sector-specific output)",
         "Joules / INR-PPP", "intensity", "P6/Q1/E",
         ["C.P6.E.44", "C.P6.E.45"],
         "Total energy consumed / total revenue (audited P&L) adjusted for PPP; sector-specific output option.",
         ppp_adjusted=True, output_denominator=True, value_chain_kpi=True,
         legacy_kpi_code="energy_intensity_per_crore_turnover"),
    # ── Attribute 4: Embracing circularity — waste management ──────────────
    _kpi("BRSC-4.1", 4, "Plastic waste (A)", "Absolute weight of packaging etc. discarded under Plastic Waste Mgmt Rules 2016",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.21"],
         "Absolute weight of packaging material (bags, bottles, pallets etc.) discarded, per PWM Rules 2016.",
         value_chain_kpi=True),
    _kpi("BRSC-4.2", 4, "E-waste (B)", "Discarded electronics under E-Waste Mgmt Rules 2016",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.22"],
         "Discarded computers, TVs, phones, copiers, fax machines etc. per E-Waste Rules 2016.",
         value_chain_kpi=True),
    _kpi("BRSC-4.3", 4, "Bio-medical waste (C)", "Solids/liquids waste generated during diagnosis/treatment/immunization",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.23"],
         "Per Bio-Medical Waste Mgmt Rules 2016.",
         value_chain_kpi=True),
    _kpi("BRSC-4.4", 4, "Construction and demolition waste (D)",
         "Concrete, plaster, metal rods/wires, wood, plastics per C&D Rules 2016",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.24"],
         "Per Construction & Demolition Waste Rules 2016.",
         value_chain_kpi=True),
    _kpi("BRSC-4.5", 4, "Battery waste (E)",
         "Discarded Li-ion, alkaline, lead-acid batteries (vehicles, computers, UPS etc.)",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.25"],
         "Per Battery Waste Mgmt Rules 2016 and amendments.",
         value_chain_kpi=True),
    _kpi("BRSC-4.6", 4, "Radioactive waste (F)",
         "Discarded material with radiation exposure (nuclear plants, hospitals, labs, industry)",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.26"],
         "As defined under applicable radiation rules.",
         value_chain_kpi=True),
    _kpi("BRSC-4.7", 4, "Other hazardous waste (G)", "Hazardous waste per CPCB rules",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.27"],
         "As per Hazardous Waste Management Rules of CPCB.", value_chain_kpi=True),
    _kpi("BRSC-4.8", 4, "Other non-hazardous waste (H)",
         "Non-hazardous waste by composition (sector-relevant materials)",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.28"],
         "As per CPCB; break-up by material relevant to the sector.", value_chain_kpi=True),
    _kpi("BRSC-4.9", 4, "Total waste generated", "Sum of categories A–H",
         "Kg / MT", "mass", "P6/Q9/E", ["C.P6.E.29"],
         "Total = A + B + C + D + E + F + G + H.", value_chain_kpi=True),
    _kpi("BRSC-4.10", 4, "Waste intensity",
         "Total waste generated / revenue adjusted for PPP (and sector-specific output)",
         "Kg or MT / INR-PPP", "intensity", "P6/Q9/E",
         ["C.P6.E.67", "C.P6.E.68"],
         "Total waste generated / total revenue (audited P&L) adjusted for PPP; sector output option.",
         ppp_adjusted=True, output_denominator=True, value_chain_kpi=True),
    _kpi("BRSC-4.11", 4, "Waste recovered (recycled / re-used / other recovery) per category",
         "Each category: waste recycled/recovered as share of waste generated",
         "Kg recycled-recovered / Kg total", "intensity", "P6/Q9/E",
         ["C.P6.E.31", "C.P6.E.32", "C.P6.E.33", "C.P6.E.70"],
         "Per-category recovery operations; vendor certificates may be relied upon for assurance.",
         value_chain_kpi=True),
    _kpi("BRSC-4.12", 4, "Waste disposed by nature of disposal method",
         "Per category: incineration, landfill, or other disposal",
         "Kg / MT", "mass", "P6/Q9/E",
         ["C.P6.E.34", "C.P6.E.35", "C.P6.E.69", "C.P6.E.71"],
         "For each category report amount disposed via incineration, landfill, or any other method.",
         value_chain_kpi=True),
    # ── Attribute 5: Employee wellbeing and safety ─────────────────────────
    _kpi("BRSC-5.1", 5, "Spending on measures towards well-being of employees and workers",
         "Cost incurred as % of total revenue (health/accident insurance, maternity/paternity, day care, H&S incl. mental health)",
         "%", "percent", "P3/Q1(c)/E", ["C.P3.E.7"],
         "Insurance policies & premium paid, infant-care policy, invoices towards facilities; "
         "5 defined initiatives plus health & safety measures including mental health."),
    _kpi("BRSC-5.2", 5, "Number of permanent disabilities",
         "Permanent disabilities among employees and workers",
         "count", "integer", "P3/Q11/E", ["C.P3.E.32"],
         "Verified on the basis of claims."),
    _kpi("BRSC-5.3", 5, "Lost Time Injury Frequency Rate (LTIFR)",
         "Lost-time injuries per million person-hours (employees and workers incl. contract)",
         "per one million person-hours", "decimal", "P3/Q11/E",
         ["C.P3.E.20"],
         "LTIFR = (total lost-time injuries × 1,000,000) / total working hours."),
    _kpi("BRSC-5.4", 5, "Number of fatalities",
         "Fatalities among employees and workers (incl. contract, e.g. construction sites)",
         "count", "integer", "P3/Q11/E", ["C.P3.E.21"],
         "Per claims reported to the Factory Inspector."),
    # ── Attribute 6: Gender diversity ──────────────────────────────────────
    _kpi("BRSC-6.1", 6, "Gross wages paid to females as % of wages paid",
         "Total gross wages to female employees/workers / total gross wages",
         "%", "percent", "P5/Q3(b)/E", ["C.P5.E.6"],
         "From employee master / register."),
    _kpi("BRSC-6.2", 6, "Total complaints on POSH reported",
         "Complaints under Sexual Harassment of Women at Workplace (POSH)",
         "count", "integer", "P5/Q7/E", ["C.P5.E.7"],
         "Reported complaints during the FY."),
    _kpi("BRSC-6.3", 6, "Complaints on POSH as a % of female employees/workers",
         "POSH complaints / female headcount",
         "%", "percent", "P5/Q7/E", ["C.P5.E.17"],
         "Complaints on POSH as % of female employees/workers."),
    _kpi("BRSC-6.4", 6, "Complaints on POSH upheld",
         "POSH complaints found upheld",
         "count", "integer", "P5/Q7/E", ["C.P5.E.18"],
         "Number of POSH complaints upheld after inquiry."),
    # ── Attribute 7: Inclusive development ─────────────────────────────────
    _kpi("BRSC-7.1", 7, "Input material sourced from MSMEs / small producers / within India",
         "As % of total purchases by value",
         "%", "percent", "P8/Q4/E", ["C.P8.E.5", "C.P8.E.6"],
         "All procurement (raw material, spares, services, capex) by value from MSMEs / small producers / within India."),
    _kpi("BRSC-7.2", 7, "Job creation in smaller towns",
         "Wages paid to persons in smaller towns (RBI rural/semi-urban/urban/metro) as % of total wage cost",
         "%", "percent", "P8/Q5/E", ["C.P8.E.8", "C.P8.L.1"],
         "Classify employment location per RBI rural / semi-urban / urban / metropolitan."),
    # ── Attribute 8: Fairness with customers & suppliers ───────────────────
    _kpi("BRSC-8.1", 8, "Loss/breach of customer data",
         "Instances involving loss/breach of customer data as % of total data breaches or cyber-security events",
         "%", "percent", "P9/Q7/E", ["C.P9.E.19", "C.P9.E.20"],
         "Percentage of cyber-security incidents reported per CERT-In directions (28-Apr-2022) that involved "
         "personally identifiable information of customers."),
    _kpi("BRSC-8.2", 8, "Number of days of accounts payable",
         "Accounts-payable days",
         "days", "integer", "P1/Q8/E", ["C.P1.E.12"],
         "(Accounts payable × 365) / cost of goods/services procured; verify from financial statements."),
    # ── Attribute 9: Open-ness of business ─────────────────────────────────
    _kpi("BRSC-9.1", 9, "Purchases from trading houses",
         "Purchases from trading houses as % of total purchases",
         "%", "percent", "P1/Q9/E", ["C.P1.E.15"],
         "Purchases from trading houses as % of total purchases."),
    _kpi("BRSC-9.2", 9, "Number of trading houses",
         "Count of trading houses purchases are made from",
         "count", "integer", "P1/Q9/E", ["C.P1.E.16"],
         "Number of distinct trading houses."),
_kpi("BRSC-9.3", 9, "Purchases from top 10 trading houses",
          "Purchases from top 10 trading houses as % of total purchases from trading houses",
          "%", "percent", "P1/Q9/E", ["C.P1.E.24"],
          "Top-10 trading-house concentration."),
    _kpi("BRSC-9.4", 9, "Sales to dealers/distributors",
         "Sales to dealers/distributors as % of total sales",
         "%", "percent", "P1/Q9/E", ["C.P1.E.17"],
         "Sales to dealers/distributors as % of total sales."),
    _kpi("BRSC-9.5", 9, "Number of dealers/distributors",
         "Count of dealers/distributors",
         "count", "integer", "P1/Q9/E", ["C.P1.E.18"],
         "Number of distinct dealers/distributors."),
    _kpi("BRSC-9.6", 9, "Sales to top 10 dealers/distributors",
         "Sales to top 10 dealers/distributors as % of total sales to dealers/distributors",
         "%", "percent", "P1/Q9/E", ["C.P1.E.19"],
         "Top-10 dealer/distributor concentration."),
    _kpi("BRSC-9.7", 9, "Share of related-party purchases",
         "Purchases with related parties as % of total purchases",
         "%", "percent", "P1/Q9/E", ["C.P1.E.20"],
         "RPT = Regulation 2(1)(zb); purchases with related parties / total purchases."),
    _kpi("BRSC-9.8", 9, "Share of related-party sales",
         "Sales to related parties as % of total sales",
         "%", "percent", "P1/Q9/E", ["C.P1.E.21"],
         "Sales with related parties / total sales."),
    _kpi("BRSC-9.9", 9, "Share of related-party loans & advances",
         "Loans & advances to related parties as % of total loans & advances",
         "%", "percent", "P1/Q9/E", ["C.P1.E.22"],
         "Loans & advances with related parties / total loans & advances."),
    _kpi("BRSC-9.10", 9, "Share of related-party investments",
         "Investments in related parties as % of total investments",
         "%", "percent", "P1/Q9/E", ["C.P1.E.23"],
         "Investments with related parties / total investments made."),
]

# Assured datapoint id → Core KPI codes it backs (derived; used to reconcile
# the legacy `core=True` flags).
def _inverse_map() -> dict[str, list[str]]:
    m: dict[str, list[str]] = {}
    for k in BRSC:
        for dp in k["cross_ref_datapoints"]:
            m.setdefault(dp, []).append(k["code"])
    return m


DATAPOINT_TO_BRSC: dict[str, list[str]] = _inverse_map()

# Phase-in for reasonable/limited assurance on BRSR Core, by market-cap tier
# (SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 cl.3.4.2, applied from FY2024-25 ff.;
# the original glide path started FY2023-24 top-150). Projected one year later
# to avoid anchoring to FY2023-24 (the platform's earliest tracked FY) —
# REGULATORY: re-verify the current glide path before relying on it for gating.
ASSURANCE_PHASEIN: dict[str, dict[str, str]] = {
    "reasonable": {
        "top_150": "FY2024-25",
        "top_250": "FY2025-26",
        "top_500": "FY2026-27",
        "top_1000": "FY2027-28",
    },
    # Entities inside the assurance universe start with limited assurance;
    # reasonable applies from the tier's phase-in year.
    "limited": {"top_1000": "FY2024-25"},
}

# Value-chain surface (SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122 cl.4): the top-250
# entities additionally report the SAME 43 BRSR Core KPIs for their top
# upstream/downstream partners (~75% of purchases/sales), comply-or-explain.
# That is a separate obligation on a subset of entities — it does NOT defer any
# entity's own (entity-level) assurance of the 43 KPIs. We record the original
# circular's value-chain assurance watch for FY2025-26 for reference; the
# filing gate enforces entity-level assurance (see kpi_required_mode).
VALUE_CHAIN_ASSURANCE: dict[str, str] = {
    "reporting": "FY2024-25",  # top-250 value-chain disclosures (comply-or-explain)
    "limited": "FY2025-26",    # top-250 value-chain limited assurance (comply-or-explain)
}


def get_attributes() -> list[dict[str, str]]:
    return list(ATTRIBUTES)


def get_core_kpis(
    attribute: int | None = None,
    value_chain_only: bool = False,
    catalog_gap_only: bool = False,
) -> list[dict[str, Any]]:
    kpis = BRSC
    if attribute is not None:
        kpis = [k for k in kpis if k["attribute"] == attribute]
    if value_chain_only:
        kpis = [k for k in kpis if k["value_chain_kpi"]]
    if catalog_gap_only:
        kpis = [k for k in kpis if k["catalog_gap"]]
    return list(kpis)


def core_kpi_codes() -> set[str]:
    return {k["code"] for k in BRSC}


def assurance_mode_for(tier: str, fy: str) -> str:
    """Return the assurance mode a market-cap tier requires in a given FY.

    Returns 'reasonable', 'limited', or '' (outside the assurance universe).
    """
    phased = ASSURANCE_PHASEIN["reasonable"].get(tier)
    if phased and fy >= phased:
        return "reasonable"
    universe = ASSURANCE_PHASEIN["limited"].get(tier)
    if universe and fy >= universe:
        return "limited"
    return ""


def kpi_required_mode(kpi: dict[str, Any], tier: str, fy: str) -> str:
    """Assurance mode a single BRSR Core KPI requires for an entity in a given FY.

    Entity-level: ALL 43 KPIs across the 9 attributes are in scope. The
    `value_chain_kpi` flag is informational — it marks KPIs the top-250
    additionally report for their value-chain partners under the separate
    comply-or-explain surface, carried through to `coverage()` gaps so the
    cockpit can show which KPIs carry the top-250 value-chain obligation.
    """
    return assurance_mode_for(tier, fy)


def tier_for_reporting_category(reporting_category: str | None) -> str | None:
    """Map the platform's self-declared reporting category to a phase-in tier.

    e.g. "Top 1000 (BRSR Full)" -> "top_1000"; "Below Top 1000 ..." -> None.
    Returns None when no top-N band is declared (assurance not applicable).
    """
    if not reporting_category or "below" in (category := reporting_category.lower()):
        return None
    match = re.search(r"top\s*(\d+)", category)
    if not match:
        return None
    number = int(match.group(1))
    tiers = {150: "top_150", 250: "top_250", 500: "top_500", 1000: "top_1000"}
    return tiers.get(number)


def catalog_gaps() -> list[dict[str, Any]]:
    return get_core_kpis(catalog_gap_only=True)


def legacy_mismatches() -> dict[str, str]:
    """Legacy brsr_core_kpis codes that are not part of BRSR Core scope."""
    return dict(NON_CORE_LEGACY_KPI_CODES)
