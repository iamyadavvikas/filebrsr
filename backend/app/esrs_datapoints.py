"""ESRS (CSRD) datapoint registry — sector-agnostic ESRS Set 1.

Machine-ready encoding of the EFRAG IG 3 "List of ESRS datapoints" covering
every disclosure requirement (DR) in the sector-agnostic Set 1 standards
adopted by the European Commission on 31 July 2023 (published in the Official
Journal on 22 December 2023):

  - ESRS 2 General disclosures  (BP / GOV / SBM / IRO / MDR chapters)
  - ESRS E1 – E5  (environment: climate, pollution, water, biodiversity, circular)
  - ESRS S1 – S4  (social: own workforce / value-chain workers / communities / consumers)
  - ESRS G1       (business conduct)

ESRS 1 is intentionally absent (it sets general requirements, no disclosure
requirements — mirroring EFRAG IG 3).

Each datapoint is a dict with the schema documented below. References are to
ESRS Set 1 paragraphs (e.g. "44") or Application Requirements ("AR 48"),
exactly as cited in the standard text.  Data types follow the EFRAG IG 3
classification (Narrative / Semi-narrative / Numerical, incl. Table/… variants).
"origin" flags datapoints in ESRS 2 Appendix B that derive from other EU
legislation (SFDR, Pillar 3, Benchmark Regulation, EU Climate Law).
"""

from __future__ import annotations

from typing import Any

# ─── Data-type vocabulary (EFRAG IG 3 / ESRS XBRL taxonomy) ────────────────
DATA_TYPES = frozenset({
    "narrative",          # free text disclosure
    "semi-narrative",     # structured narrative (e.g. policies/actions descriptions)
    "boolean",            # yes / no
    "integer",            # count
    "decimal",            # plain number
    "percentage",         # %
    "monetary",           # €
    "date",               # calendar date
    "duration",           # period / time horizon
    "table/measure",      # multi-dimensional quantitative table
    "table/volume",       # m3, t (volume)
    "table/mass",         # tonnes (mass)
    "table/monetary",     # monetary amounts table
    "table/ghg",          # GHG (tCO2e) table
    "table/energy",       # energy (MWh/GJ) table
    "table/ratio",        # ratio / intensity table
})

REQ_TYPES = frozenset({"shall", "may", "MDR"})  # mandatory / voluntary / minimum disclosure req.
VC_BOUNDARIES = frozenset({"own", "upstream", "downstream", "all"})

# Phase-in values follow ESRS 1 Appendix C / ESRS 2 BP-2 §17 (<750 employees).
PHASE_2025 = "FY2025"
PHASE_2026 = "FY2026"
PHASE_3YR = "3 years"

# ESRS 2 Appendix B origins (other EU legislation)
ORIGIN_SFDR = "SFDR"
ORIGIN_PILLAR3 = "Pillar3"
ORIGIN_BMR = "Benchmark"
ORIGIN_CLIMATE = "EU Climate Law"

# Validity checks: standards present in Set 1 (ESRS 2 + topical)
VALID_STANDARDS = frozenset({"2", "E1", "E2", "E3", "E4", "E5", "S1", "S2", "S3", "S4", "G1"})

ESRS_DATAPOINTS: list[dict[str, Any]] = []


def _dp(
    standard: str,
    dr: str,
    para: str,
    name: str,
    dtype: str,
    *,
    req: str = "shall",
    conditional: bool = False,
    voluntary: bool = False,
    phase_in: str = "",
    origin: str = "",
    vc: str = "all",
) -> dict[str, Any]:
    """Register one ESRS datapoint."""
    if standard not in VALID_STANDARDS:
        raise ValueError(f"Unknown ESRS standard {standard!r}")
    if dtype not in DATA_TYPES:
        raise ValueError(f"Unknown data type {dtype!r} for {dr}.{para}")
    if req not in REQ_TYPES:
        raise ValueError(f"Unknown requirement type {req!r}")
    if vc not in VC_BOUNDARIES:
        raise ValueError(f"Unknown value-chain boundary {vc!r}")
    # unique id: "E1-6.44", "E1-6.AR48", "ESRS2.GOV1.21"
    prefix = "ESRS2" if standard == "2" else standard
    points = [p for p in (para or "").split(";") if p]
    base = f"{prefix}.{dr}.{'.'.join(points)}"
    n = 1
    dp_id = base if n == 1 else f"{base}#{n}"
    while any(d["id"] == dp_id for d in ESRS_DATAPOINTS):
        n += 1
        dp_id = f"{base}#{n}"
    dp = {
        "id": dp_id,
        "standard": standard,
        "dr": dr,
        "paragraph": para,
        "name": name,
        "data_type": dtype,
        "requirement": "may" if voluntary else req,
        "conditional": bool(conditional),
        "voluntary": bool(voluntary),
        "phase_in": phase_in,
        "origin": origin,
        "value_chain": vc,
    }
    ESRS_DATAPOINTS.append(dp)
    return dp


def _dps(standard: str, dr: str, rows: list[tuple]) -> None:
    """Register many datapoints for one DR.

    rows: (para, name, dtype, [kwargs…]) — kwargs via trailing dict.
    """
    for row in rows:
        para, name, dtype = row[0], row[1], row[2]
        kw: dict = row[3] if len(row) > 3 and isinstance(row[3], dict) else {}
        _dp(standard, dr, para, name, dtype, **kw)


def _drs(rows: list[tuple]) -> None:
    """(standard, dr, list_of_rows)."""
    for standard, dr, dr_rows in rows:
        _dps(standard, dr, dr_rows)


# ═══════════════════════════════════════════════════════════════════════════
# ESRS 2 — GENERAL DISCLOSURES
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("2", "BP-1", [
        ("3", "General basis for preparation of the sustainability statement", "narrative"),
        ("3", "Whether the sustainability statement is prepared on a consolidated basis", "semi-narrative"),
        ("4", "Jurisdiction(s) under which the consolidated sustainability statement is prepared", "narrative"),
        ("4", "Statement that the disclosures are prepared in accordance with ESRS", "boolean"),
        ("4", "Declaration of conformity of the consolidated sustainability statement with the CSRD", "boolean"),
        ("5", "Legal entities included in the consolidated sustainability statement", "narrative"),
        ("6", "Whether the undertaking applies the exemption from a sustainability statement for a subsidiary (ESRS 1 §38)", "boolean"),
    ]),
    ("2", "BP-2", [
        ("8", "Disclosure of information arising from other legislation or generally accepted sustainability reporting pronouncements", "semi-narrative"),
        ("9", "Estimations and outcome uncertainty — level of estimation uncertainty", "semi-narrative"),
        ("10", "Sources of estimation and outcome uncertainty and assumptions made", "narrative"),
        ("11", "Disclosures derived from other legislation or reporting pronouncements do not themselves relieve the undertaking of the corresponding ESRS disclosures", "boolean"),
        ("13", "Comparative information — restated disclosures and reasons for restatement", "narrative"),
        ("13b", "Disclosure of revised comparative figures", "narrative", {"conditional": True}),
        ("13c", "Changes to the presentation of comparative figures and reasons", "narrative", {"conditional": True}),
        ("14", "Scope of the undertaking's disclosures (reporting boundaries)", "semi-narrative"),
        ("15", "Changes in reporting boundaries and how they are reflected in the disclosures", "narrative", {"conditional": True}),
        ("16", "Mismatches between the reporting boundaries for the sustainability statement and the undertaking's consolidated financial statements", "semi-narrative", {"conditional": True}),
        ("17", "Phase-in of requirements for undertakings with 750 employees or fewer", "semi-narrative", {"phase_in": PHASE_3YR}),
    ]),
    ("2", "GOV-1", [
        ("21", "Composition and diversity of members of administrative, management and supervisory bodies", "semi-narrative"),
        ("21", "Body composition together with competences and expertise", "narrative"),
        ("21", "Representation of relevant stakeholders and workers in the bodies", "narrative"),
        ("21", "Percentage of body members who are female", "percentage"),
        ("21", "Percentage of body members from groups that are under-represented in the workforce", "percentage", {"conditional": True}),
        ("21", "Body members' sustainability-related expertise and competences", "narrative"),
        ("22", "Job descriptions, mandates of the bodies responsible for impacts, risks and opportunities", "narrative"),
        ("23", "Disclosure of nature and extent of the role of the bodies", "narrative"),
        ("24", "Reporting lines and composition of the bodies", "narrative"),
        ("27", "Number of other significant positions and commitments held by body members", "integer"),
        ("27", "Nature of the commitments and the number of board members affected", "semi-narrative"),
        ("AR21", "Proportion of senior and functionally relevant management involved in material IROs", "semi-narrative"),
        ("AR23", "Highest governance body committee responsible for sustainability reporting", "narrative"),
    ]),
    ("2", "GOV-2", [
        ("26", "Information provided to and sustainability matters addressed by the administrative, management and supervisory bodies", "narrative"),
        ("27", "Differences in the list of sustainability matters addressed", "narrative", {"conditional": True}),
        ("27", "Frequency of reporting of material IROs to the bodies", "narrative", {"conditional": True}),
    ]),
    ("2", "GOV-3", [
        ("29", "Integration of sustainability-related performance in incentive schemes", "semi-narrative"),
        ("30", "Amount of remuneration linked to sustainability-related considerations", "monetary"),
        ("30", "Percentage of remuneration linked to sustainability-related considerations", "percentage"),
        ("31", "Whether the sustainability-related performance targets or incentive schemes are subject to approval by the highest governance body", "boolean"),
    ]),
    ("2", "GOV-4", [
        ("32", "Statement on due diligence in relation to sustainability matters", "narrative"),
        ("33", "Whether the undertaking has a process to identify and assess material impacts and risks", "boolean"),
        ("34", "Mapping of the elements of the due diligence process: governance", "semi-narrative"),
        ("34", "Mapping of the elements of the due diligence process: strategy and business model", "semi-narrative"),
        ("34", "Mapping of the elements of the due diligence process: process to identify and assess adverse impacts", "semi-narrative"),
        ("34", "Mapping of the elements of the due diligence process: prevention and mitigation/actions", "semi-narrative"),
        ("34", "Mapping of the elements of the due diligence process: remediation", "semi-narrative"),
        ("34", "Mapping of the elements of the due diligence process: effectiveness of engagement", "semi-narrative"),
    ]),
    ("2", "GOV-5", [
        ("35", "Risk management and internal controls over sustainability reporting", "semi-narrative"),
        ("36", "Level of assurance applicable to the sustainability statement", "semi-narrative"),
        ("37", "Internal risks and controls relating to sustainability reporting", "narrative"),
    ]),
    ("2", "SBM-1", [
        ("38", "Strategy and business model — significant sectors and exposures", "narrative"),
        ("40", "Significant sectors that generated significant revenue in the reporting period", "semi-narrative"),
        ("40", "Significant sectors and their associated revenue", "table/monetary"),
        ("40", "Products/material/significant markets in which the undertaking operates", "narrative"),
        ("40", "Type of products or services and markets", "narrative"),
        ("40", "Type of relationships the undertaking has with customers or business partners", "narrative"),
        ("40", "Geographic areas of the undertaking's activities", "narrative"),
        ("40", "Number of employees and number of employees in EEA vs non-EEA", "table/measure"),
        ("40", "Revenue by significant sector", "table/monetary"),
        ("40", "Revenue derived from the undertaking's operations, disaggregated by significant sector and geography", "table/monetary"),
        ("40", "Revenue from chemical production, i.e. activities falling under Division 20.2 of Annex I to Regulation (EC) No 1893/2006", "table/monetary", {"conditional": True}),
        ("40d", "Number of employees by region between headcount at end of period and average during period", "table/measure"),
        ("41", "Number of employees in the undertaking's workforce by category and by region", "table/measure"),
        ("41", "Gender distribution of employees by category", "table/measure"),
        ("42", "Description of the undertaking's significant impacts and how it creates value", "narrative"),
        ("43", "Main characteristics of the undertaking's value chain", "narrative"),
        ("44", "Whether the value chain contains significant negative social or environmental impacts", "semi-narrative", {"conditional": True}),
        ("AR8", "Undertaking's strategy: description of significant sectors of operation", "narrative"),
        ("AR9", "Undertaking's strategy: description of products and markets", "narrative"),
        ("AR10", "Undertaking's strategy: description of relationships with customers or business partners", "narrative"),
        ("AR11", "Undertaking's strategy: description of the process to define its business model and its key elements", "narrative"),
    ]),
    ("2", "SBM-2", [
        ("45", "Interests and views of stakeholders and how they are taken into account", "narrative"),
        ("46", "Whether the interests and views of stakeholders are taken into account in the strategy", "semi-narrative"),
        ("47", "Whether the undertaking has mechanisms to involve stakeholders in the reporting, including for the identification of IROs", "semi-narrative"),
    ]),
    ("2", "SBM-3", [
        ("48", "Material impacts, risks and opportunities (IROs) and their interaction with the strategy and business model", "semi-narrative"),
        ("49", "Description of the material IROs, includes where they are concentrated in the value chain", "narrative"),
        ("50", "Description of the financial effects of material IROs on the undertaking's strategy and business model", "narrative"),
        ("51", "Contribution of the IROs to the undertaking's business model over multiple time horizons", "narrative"),
    ]),
    ("2", "IRO-1", [
        ("53", "Description of the process to identify and assess material impacts, risks and opportunities", "narrative"),
        ("53", "Description of the process to identify and assess material impacts, risks and opportunities encompassing the entire value chain", "semi-narrative"),
        ("54", "Undertaking's processes to identify and assess the positive and negative impacts", "semi-narrative"),
        ("55", "Undertaking's process for assessing financial materiality", "semi-narrative"),
        ("56", "Undertaking's process for assessing how significant the impact, risk and opportunity is", "semi-narrative"),
        ("AR22", "Factors considered in the materiality assessment", "narrative"),
    ]),
    ("2", "IRO-2", [
        ("57", "Disclosure Requirements in ESRS covered by the undertaking's sustainability statement", "semi-narrative"),
        ("58", "Table of all datapoints that derive from other EU legislation (Appendix B)", "table/measure", {"origin": ORIGIN_SFDR}),
        ("59", "Indication of where in the financial statements datapoints from other EU legislation are disclosed", "narrative"),
        ("60", "Statement of not material datapoints that derive from other EU legislation", "semi-narrative", {"origin": ORIGIN_SFDR}),
    ]),
    ("2", "MDR-P", [
        ("62", "Minimum disclosure requirement — policies adopted to manage material sustainability matters", "semi-narrative"),
        ("62", "Disclosure of policies adopted in relation to material sustainability matters", "semi-narrative"),
        ("62", "Sustainability matters for which policies have not been adopted", "semi-narrative", {"conditional": True}),
        ("62", "Disclosure of the reason for not having adopted policies", "narrative", {"conditional": True}),
        ("65", "Scope of the policies", "semi-narrative"),
        ("65", "Whether the policy covers subsidiaries", "boolean"),
        ("65", "Whether the policy covers value chain", "boolean"),
        ("65", "Objective of the policy", "semi-narrative"),
        ("65", "Persons responsible for the policy", "narrative"),
        ("65", "Time horizon of the policy", "semi-narrative"),
        ("65", "How the policy is connected to the undertaking's strategy and business model", "narrative"),
        ("65", "How the policy is aligned with internationally recognised standards", "semi-narrative"),
        ("AR20", "Element indicating global coverage of the policy", "boolean"),
        ("AR21", "Element indicating whether the policy integrates any due diligence requirements", "boolean"),
    ]),
    ("2", "MDR-A", [
        ("66", "Minimum disclosure requirement — actions taken to manage material sustainability matters", "semi-narrative"),
        ("67", "Actions and initiatives taken during the reporting period", "semi-narrative"),
        ("69", "Financial resources allocated to actions when relevant", "monetary"),
        ("69a", "Key actions and their scope", "narrative"),
        ("69a", "Description of scope of key action in own operations", "narrative"),
        ("69a", "Description of scope of key action in the upstream and/or downstream value chain", "narrative"),
        ("69b", "Explanation of how current financial resources relate to the most relevant amounts presented in the financial statements", "narrative"),
        ("70", "State of progress of the actions taken", "narrative"),
        ("71", "Resources and the action plan developed to implement the actions", "semi-narrative"),
        ("71", "Current and future financial resources allocated to the actions, breakdown by time horizon and by action", "table/monetary"),
        ("72", "How the undertaking monitors the implementation", "semi-narrative"),
        ("AR23", "Description of scope of key action coverage", "semi-narrative"),
        ("AR23", "Sustainability matters addressed by each action", "semi-narrative"),
    ]),
    ("2", "MDR-T", [
        ("73", "Minimum disclosure requirement — targets adopted to manage material sustainability matters", "semi-narrative"),
        ("75", "Targets used to address material sustainability matters", "semi-narrative"),
        ("75", "Whether the targets relate to the undertaking's strategy", "boolean"),
        ("75", "Whether the targets are time-bound, measurable and based on conclusive evidence", "semi-narrative"),
        ("75", "Whether the targets are determined and implemented in and through the highest governance body", "boolean"),
        ("75", "Commentary on the extent to which the targets are science-based", "narrative"),
        ("76", "Disclosure of every target in relation to the corresponding material sustainability matter", "semi-narrative"),
        ("76", "Metric and target in relation to the sustainability matter", "semi-narrative"),
        ("76", "Baseline value of measurable target (absolute value)", "table/measure"),
        ("76", "Baseline value of measurable target (percentage)", "table/measure"),
        ("76", "Period to which the target applies (start year and end year)", "date"),
        ("76", "Description of the approach used to define materiality and methodology", "narrative"),
        ("77", "Engagement of stakeholders in target setting", "narrative"),
        ("78", "Whether the undertaking has adopted targets in relation to material sustainability matters", "boolean"),
        ("78", "Description of the measures taken to achieve the reported targets", "narrative"),
        ("78", "Disclosure of the reason for not having adopted targets", "narrative", {"conditional": True}),
        ("AR24", "Sustainability matter(s) for which targets have not been adopted", "semi-narrative", {"conditional": True}),
        ("AR25", "Disclosure of the reason for not having adopted targets", "narrative", {"conditional": True}),
    ]),
    ("2", "MDR-M", [
        ("80", "Minimum disclosure requirement — metrics used to address material sustainability matters", "semi-narrative"),
        ("81", "Metrics list, with reference to the pertinent DRs", "table/measure"),
        ("82", "Metrics used by the undertaking to measure results against the targets", "semi-narrative"),
        ("83", "Metrics for the material sustainability matters, including all the metrics prescribed by the topical standards", "semi-narrative"),
        ("83", "Key performance indicators on metrics disclosed by the undertaking", "semi-narrative"),
        ("83", "Additional or entity-specific metrics used by the undertaking", "semi-narrative"),
        ("83", "Methods and assumptions used to calculate metrics", "narrative"),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS E1 — CLIMATE CHANGE
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("E1", "GOV-3", [
        ("13", "Description of how the highest governance body delegates or links the integration of climate-related performance in incentive schemes", "narrative"),
        ("14", "Percentage of incentives linked to climate-related considerations", "percentage", {"origin": ORIGIN_CLIMATE}),
        ("14", "Whether the climate-related considerations are included in the remuneration criteria of the highest governance members", "boolean"),
    ]),
    ("E1", "SBM-3", [
        ("18", "Description of the material gross and net impacts, risks and opportunities of the undertaking's activities on climate and society and how they arise", "narrative"),
        ("19", "Description of the resilience analysis of the undertaking's strategy and business model concerning climate change", "semi-narrative"),
        ("18", "Types of climate-related physical risks", "semi-narrative"),
        ("18", "Types of climate-related transition risks", "semi-narrative"),
        ("19", "Disclosure of when the resilience analysis has been conducted", "date"),
        ("19", "Disclosure of how the resilience analysis has been conducted", "narrative"),
        ("AR5", "Cross-reference of climate-related information with ESRS E1 requirements", "semi-narrative"),
    ]),
    ("E1", "IRO-1", [
        ("20", "Process to identify and assess climate-related impacts, risks and opportunities", "narrative"),
        ("20", "Description of the process in relation to the identification of climate-related hazards, considering at least high-emission climate scenarios", "narrative"),
        ("20", "Description of the process in relation to the assessment of how the assets and business activities may be exposed and are sensitive to climate-related hazards, creating gross physical risks", "narrative"),
        ("20", "Description of interaction between the undertaking and its value chain costs for carbon (transition risks)", "narrative"),
        ("20", "Description of the interaction of the undertaking and its clients with carbon pricing mechanisms", "semi-narrative"),
        ("AR11", "Identification of climate-related hazards considering at least two climate scenarios, one of which consistent with 1.5°C", "narrative"),
    ]),
    ("E1", "E1-1", [
        ("14", "Transition plan for climate change mitigation", "semi-narrative", {"origin": ORIGIN_CLIMATE}),
        ("14", "Whether the plan is approved by the highest governance body and how it is managed", "boolean"),
        ("15", "Whether the transition plan is prepared in alignment with the European Climate Law", "boolean", {"origin": ORIGIN_CLIMATE}),
        ("16", "Whether the undertaking is excluded from Paris-aligned benchmarks", "boolean", {"origin": ORIGIN_BMR}),
        ("16", "Explanation of how the undertaking may be affected by physical or transition risks", "narrative", {"conditional": True}),
        ("16", "Exposure of the undertaking to coal, oil and gas related activities", "semi-narrative", {"origin": ORIGIN_PILLAR3}),
        ("16", "Involvement in activities related to fossil fuel activities", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("16", "Whether the undertaking has adopted exclusionary criteria in its strategy for fossil fuel activities", "boolean"),
        ("16", "Net zero targets including the extent to which the targets are science-based", "semi-narrative"),
        ("16", "Whether the targets have been set based on absolute or intensity criteria", "semi-narrative"),
        ("16", "Whether carbon offsets have been used and how they relate to the targets", "semi-narrative"),
        ("16", "Explanation of planned decarbonisation levers and their quantified contribution", "narrative"),
        ("16", "Operational expenditure and capital expenditure planned for decarbonisation", "monetary", {"conditional": True}),
    ]),
    ("E1", "E1-2", [
        ("21", "Policies related to climate change mitigation and adaptation", "semi-narrative"),
        ("21", "Description of the policies and their alignment with the transition plan", "semi-narrative"),
        ("22", "Cross-reference to the relevant sustainability matter and global coverage of the policy", "boolean"),
        ("22", "Whether the policy sets out any requirement to comply with the EU Taxonomy", "boolean", {"origin": ORIGIN_SFDR}),
        ("22", "Whether the policy requires the undertaking to contribute to the Just Transition", "boolean"),
        ("22", "Whether the policy extends to the undertaking's value chain", "boolean"),
    ]),
    ("E1", "E1-3", [
        ("23", "Actions and resources in relation to climate change policies", "semi-narrative"),
        ("23", "List of the actions taken during the reporting period (which can include the adoption of products or services)", "semi-narrative"),
        ("23", "Cross-link of the actions with the E1-1 transition plan", "semi-narrative"),
        ("23", "Values of the planned wastewater, waste, and other relevant actions", "narrative"),
        ("24", "Financial resources required to implement the actions and the possible sources of funding", "monetary"),
    ]),
    ("E1", "E1-4", [
        ("33", "Targets related to climate change mitigation and adaptation", "semi-narrative"),
        ("34", "GHG emission reduction targets — absolute net value", "table/ghg", {"origin": ORIGIN_BMR}),
        ("34", "GHG emission reduction targets — base year and baseline value", "table/ghg", {"origin": ORIGIN_BMR}),
        ("34", "GHG emission reduction targets — deadline for achieving the target", "date", {"origin": ORIGIN_BMR}),
        ("34", "GHG emission reduction targets — percentage of total Scope 1, 2 and 3 GHG emissions covered by the target", "percentage", {"origin": ORIGIN_BMR}),
        ("34", "GHG emission reduction targets — methodology used to calculate the target", "narrative", {"origin": ORIGIN_BMR}),
        ("34", "GHGs covered by the target", "semi-narrative", {"conditional": True}),
        ("35", "Whether the targets are aligned with the Paris Agreement goal of 1.5°C", "boolean"),
        ("35", "Description of the target's alignment with national and regional climate change policy frameworks", "narrative"),
        ("35", "Explanation of whether the targets have been independently legislated to achieve net zero and the extent of any transition plan", "semi-narrative"),
        ("AR24", "GHGs covered by the target and the scope of the target in relation to the value chain", "semi-narrative", {"conditional": True}),
    ]),
    ("E1", "E1-5", [
        ("37", "Energy consumption and mix — total energy consumption", "table/energy", {"origin": ORIGIN_SFDR}),
        ("37", "Fossil energy consumption", "table/energy", {"origin": ORIGIN_SFDR}),
        ("37", "Nuclear energy consumption", "table/energy"),
        ("37", "Renewable energy consumption", "table/energy"),
        ("37", "Renewable energy consumption share", "percentage"),
        ("38", "Fossil energy consumption disaggregated by sources (only high climate impact sectors)", "table/energy", {"conditional": True, "origin": ORIGIN_SFDR}),
        ("39", "Energy intensity — total energy consumption per net revenue from activities in high climate impact sectors", "table/ratio", {"origin": ORIGIN_SFDR}),
        ("40", "Revenue from activities in high climate impact sectors", "table/monetary", {"origin": ORIGIN_SFDR}),
        ("40", "Net revenue always includes the revenues from own activities", "table/monetary", {"origin": ORIGIN_SFDR}),
        ("42", "Energy intensity associated with activities in high climate impact sectors (total energy consumption per net revenue)", "table/energy", {"origin": ORIGIN_SFDR}),
        ("AR33", "Energy consumption in MWh", "table/energy"),
        ("AR34", "Energy intensity cross-reference to E1-4 targets", "table/energy", {"conditional": True}),
        ("AR40", "Value chain energy consumption", "table/energy"),
    ]),
    ("E1", "E1-6", [
        ("44", "Gross Scope 1, 2, 3 and total GHG emissions", "table/ghg", {"origin": ORIGIN_SFDR}),
        ("48", "Gross Scope 1 GHG emissions (tCO2e)", "table/ghg", {"origin": ORIGIN_SFDR}),
        ("49", "Gross Scope 2 GHG emissions — location-based (tCO2e)", "table/ghg", {"origin": ORIGIN_SFDR}),
        ("50", "Gross Scope 2 GHG emissions — market-based (tCO2e)", "table/ghg", {"origin": ORIGIN_SFDR}),
        ("51", "Gross Scope 3 GHG emissions (tCO2e)", "table/ghg", {"origin": ORIGIN_SFDR}),
        ("44", "Total gross GHG emissions (tCO2e)", "table/ghg"),
        ("52", "Total gross GHG emissions intensity", "table/ratio", {"origin": ORIGIN_SFDR}),
        ("52", "Total gross GHG emissions intensity ratio (tCO2e per net revenue)", "table/ratio", {"origin": ORIGIN_SFDR}),
        ("52", "GHG intensity — GHG emitted through the activities undertaken by the undertaking (net revenue always includes the revenues from own activities)", "table/ghg", {"origin": ORIGIN_SFDR}),
        ("53", "Biogenic emissions for Scope 1, 2 and 3", "table/ghg", {"conditional": True}),
        ("54", "Disclosure of gross GHG emissions and its reconciliation with the undertaking's financial statements", "table/ghg"),
        ("55", "Net revenue amount used for the intensity calculation", "monetary"),
        ("55", "Disclosure of reconciliation of net revenue amounts to relevant line items in the financial statements", "narrative", {"conditional": True}),
        ("AR46", "Biogenic emissions from combustion or bio-degradation", "table/ghg"),
        ("AR48", "GHG emissions calculated in accordance with ISO 14064-1:2018", "table/ghg", {"conditional": True}),
        ("AR50", "GHG emissions inventory verified (location-based)" , "boolean"),
        ("AR52", "Gross Scope 3 GHG emissions breakdown by significant category", "table/ghg", {"conditional": True}),
        ("AR42c", "Effects of significant events and changes in circumstances relevant to GHG emissions", "narrative", {"conditional": True}),
    ]),
    ("E1", "E1-7", [
        ("56", "GHG removals and GHG mitigation projects financed through carbon credits", "semi-narrative"),
        ("58", "Description of the GHG mitigation projects financed through carbon credits", "narrative", {"conditional": True}),
        ("AR57a", "Type of GHGs concerned for removal and storage activity", "semi-narrative", {"conditional": True}),
        ("AR57b", "Description of GHGs concerned for removal and storage activity, including whether the activity qualifies as a nature-based solution", "narrative", {"conditional": True}),
        ("AR59", "Net GHG emissions removals and mitigation of residual emissions", "table/ghg"),
    ]),
    ("E1", "E1-8", [
        ("59", "Internal carbon pricing schemes and their application", "semi-narrative"),
        ("61", "Whether the internal carbon pricing scheme is used to achieve the E1-4 targets", "boolean"),
        ("61", "Description of how the internal carbon price is set and applied", "narrative"),
        ("62", "Internal carbon pricing schemes are applied", "boolean", {"conditional": True}),
        ("63", "Volume of gross Scope 1 GHG emissions covered by internal carbon pricing schemes", "table/ghg", {"conditional": True}),
        ("63", "Volume of gross Scope 2 GHG emissions covered by internal carbon pricing schemes", "table/ghg", {"conditional": True}),
        ("63", "Volume of gross Scope 3 GHG emissions covered by internal carbon pricing schemes", "table/ghg", {"conditional": True}),
        ("63", "Percentage of the gross Scope 1 emissions covered by internal carbon pricing schemes", "percentage", {"conditional": True}),
        ("63", "Percentage of the gross Scope 2 emissions covered by internal carbon pricing schemes", "percentage", {"conditional": True}),
        ("63", "Percentage of the gross Scope 3 emissions covered by internal carbon pricing schemes", "percentage", {"conditional": True}),
        ("AR66", "Internal carbon prices applied in €/tCO2e and the criteria for internal pricing", "table/measure", {"conditional": True}),
    ]),
    ("E1", "E1-9", [
        ("64", "Anticipated financial effects of material physical and transition risks (qualitative)", "semi-narrative", {"phase_in": PHASE_2026}),
        ("65", "Anticipated financial effects of material physical and transition risks (quantitative)", "table/monetary", {"phase_in": PHASE_2026}),
        ("66", "Anticipated financial effects of potential for positive financial effects from opportunities (qualitative)", "semi-narrative", {"phase_in": PHASE_2026}),
        ("67", "Anticipated financial effects of potential for positive financial effects from opportunities (quantitative)", "table/monetary", {"phase_in": PHASE_2026}),
        ("AR67", "Description of the methodology used to quantify the effects", "narrative"),
        ("AR68", "Diversification made between the time horizons to prepare the disclosures (short, medium and long term)", "semi-narrative"),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS E2 — POLLUTION
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("E2", "IRO-1", [
        ("11", "Process to identify and assess material pollution-related impacts, risks and opportunities", "narrative"),
        ("11", "Description of the process to identify and assess material pollution-related impacts on the ground, in the air, and in water", "narrative"),
        ("11", "Description of the process to identify and assess the contribution of the undertaking to pollution", "narrative"),
        ("AR19", "Whether the process covers the relevant direct or indirect impact relating to the prevention and control of pollution", "narrative"),
    ]),
    ("E2", "E2-1", [
        ("13", "Policies related to pollution prevention and control", "semi-narrative"),
        ("13", "Whether the policy explicitly addresses the prevention, reduction and control of pollution", "boolean"),
        ("13", "Whether the policy extends to the undertaking's products and services and its value chain", "semi-narrative"),
    ]),
    ("E2", "E2-2", [
        ("15", "Actions and resources in relation to pollution", "semi-narrative"),
        ("15", "List of the actions taken during the reporting period with their scope", "semi-narrative"),
        ("15", "Cross-reference to the corresponding policies and targets", "semi-narrative"),
        ("15", "Financial resources allocated to the actions", "monetary"),
    ]),
    ("E2", "E2-3", [
        ("17", "Targets related to pollution", "semi-narrative"),
        ("17", "Description of the targets for the prevention and control of pollution, with the corresponding quantitative values", "semi-narrative"),
        ("17", "Whether the targets are derived from the EU annex of Regulation (EC) No 166/2006 E-PRTR", "boolean"),
        ("17", "Methodology used to calculate the targets and the baseline value", "narrative"),
    ]),
    ("E2", "E2-4", [
        ("20", "Pollution discharged to air, water and soil", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("29", "Pollutants emitted to air", "table/mass", {"origin": ORIGIN_SFDR}),
        ("30", "Pollutants emitted to water", "table/mass", {"origin": ORIGIN_SFDR}),
        ("32", "Pollutants emitted to soil", "table/mass", {"origin": ORIGIN_SFDR}),
        ("28", "Amount of each pollutant listed in Annex II of the E-PRTR Regulation (European Pollutant Release and Transfer Register) emitted to air, water and soil", "table/mass", {"origin": ORIGIN_SFDR}),
        ("AR10", "Whether the pollutants were below the thresholds imposed by the E-PRTR Regulation", "boolean", {"conditional": True}),
    ]),
    ("E2", "E2-5", [
        ("36", "Substances of concern and microplastics generated or used", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("36", "Description of the substances of concern generated during the reporting period", "semi-narrative"),
        ("37", "Amount of microplastics generated or used", "table/mass", {"conditional": True}),
        ("38", "Description of the substances of concern generated by the undertaking, disaggregated by category", "table/mass", {"conditional": True}),
    ]),
    ("E2", "E2-6", [
        ("41", "Anticipated financial effects of material pollution-related impacts, risks and opportunities", "semi-narrative", {"phase_in": PHASE_2026}),
        ("42", "Anticipated financial effects of material pollution-related impacts, risks and opportunities (quantitative)", "table/monetary", {"phase_in": PHASE_2026}),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS E3 — WATER AND MARINE RESOURCES
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("E3", "IRO-1", [
        ("AR1", "Disclosure of results of materiality assessment (water and marine resources)", "narrative"),
        ("AR2", "Description of the methodology used to identify and assess material water and marine resources-related impacts, risks and opportunities", "narrative"),
    ]),
    ("E3", "E3-1", [
        ("9", "Water and marine resources policies", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("13", "Description of the water and marine resources policies adopted", "semi-narrative"),
        ("14", "Whether the policy describes the impacts, risks and opportunities related to water and marine resources (incl. sustainable oceans and seas)", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("15", "Whether the undertaking's policy is aligned with the EU and international best practice in respect of water and marine resources", "semi-narrative"),
    ]),
    ("E3", "E3-2", [
        ("17", "Actions and resources in relation to water and marine resources", "semi-narrative"),
        ("17", "List of the actions taken during the reporting period with their scope", "semi-narrative"),
        ("17", "Financial resources allocated to the actions", "monetary"),
    ]),
    ("E3", "E3-3", [
        ("20", "Targets related to water and marine resources", "semi-narrative"),
        ("20", "Targets adopted with a clear scope in relation to the water and marine resources impacts", "semi-narrative"),
        ("20", "Location of the targets and how they are linked to the undertaking's operations", "narrative"),
        ("20", "Percentage of water withdrawn/consumed in the areas with high water stress", "percentage"),
        ("AR12", "Globally, targets for water consumption in the areas with high water stress", "semi-narrative", {"conditional": True}),
    ]),
    ("E3", "E3-4", [
        ("24", "Water consumption metrics", "table/measure", {"origin": ORIGIN_SFDR}),
        ("28", "Water withdrawals by area of water stress and from third parties", "table/volume"),
        ("29", "Water consumption in cubic metres by area with current high water stress", "table/volume"),
        ("30", "Recovered water (excluding recycled water)", "table/volume"),
        ("31", "Total water intensity of the undertaking's water consumption per net revenue in areas of water stress", "table/ratio"),
        ("31", "Total water consumption per net revenue from own operations", "table/measure"),
        ("AR29", "Whether any of the relevant water-related activities have been located in areas of water stress", "boolean"),
        ("AR31", "Water intensity — total water consumption in high water stress areas", "table/measure"),
        ("32", "Description of the data and approaches used to calculate the metrics (estimation uncertainty", "narrative"),
        ("33", "Marine resource possible indicators", "semi-narrative", {"conditional": True}),
    ]),
    ("E3", "E3-5", [
        ("35", "Anticipated financial effects of material water and marine resources-related impacts, risks and opportunities", "semi-narrative", {"phase_in": PHASE_2026}),
        ("36", "Anticipated financial effects of material water and marine resources-related impacts, risks and opportunities (quantitative)", "table/monetary", {"phase_in": PHASE_2026}),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS E4 — BIODIVERSITY AND ECOSYSTEMS
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("E4", "IRO-1", [
        ("14", "Process to identify and assess material biodiversity and ecosystem-related impacts, risks and opportunities", "narrative"),
        ("14", "Description of the process to identify biodiversity and ecosystem material impacts, risks and opportunities", "narrative"),
        ("14", "Description of the process to identify the relevant direct and indirect impacts on biodiversity", "semi-narrative"),
        ("AR9", "Criteria used to assess the net biodiversity and ecosystems impacts of the undertaking", "narrative"),
    ]),
    ("E4", "E4-1", [
        ("15", "Transition plan in relation to biodiversity and ecosystems", "semi-narrative", {"phase_in": PHASE_2025}),
        ("15", "Description of the transition plan with adequate objectives and actions (if not aligned with strategies or policies)", "semi-narrative"),
        ("15", "Whether the transition plan has been integrated into the overall strategy and business model", "boolean"),
        ("15", "Public disclosure of the transition plan and the targets", "semi-narrative"),
    ]),
    ("E4", "E4-2", [
        ("17", "Policies related to biodiversity and ecosystems", "semi-narrative"),
        ("23", "Description of the policies adopted with their scope", "semi-narrative"),
        ("24", "Whether the policy sets requirements aligned with the Convention on Biological Diversity (CBD) and relevant frameworks", "semi-narrative"),
        ("24", "Whether the policy adopts sustainable land and/or agriculture practices or policies", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("24", "Whether the policy addresses sustainable oceans and seas practices or policies", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("24", "Whether the policy sets requirements for deforestation-free products", "boolean"),
        ("25", "Whether the policy sets requirements for including the protection of biodiversity in the management of the value chain", "semi-narrative"),
    ]),
    ("E4", "E4-3", [
        ("27", "Actions and resources in relation to biodiversity and ecosystems", "semi-narrative"),
        ("28", "Description of the actions and commitments with their scope and the expected outcomes", "semi-narrative"),
        ("29", "Whether the actions are sufficiently appropriate for the achievement of the targets", "semi-narrative"),
        ("30", "Financial resources allocated to the actions (quantitative)", "monetary"),
        ("AR18", "Explanation of the relationship of significant Capex and Opex required to implement actions taken or planned with relevant line items or notes in the financial statements", "narrative"),
        ("AR18", "Explanation of the relationship of significant Capex and Opex with key performance indicators required under Commission Delegated Regulation (EU) 2021/2178", "narrative"),
        ("AR18", "Explanation of the relationship of significant Capex and Opex with the Capex plan required under Commission Delegated Regulation (EU) 2021/2178", "narrative"),
    ]),
    ("E4", "E4-4", [
        ("32", "Targets related to biodiversity and ecosystems", "semi-narrative"),
        ("33", "Quantified and time-bound targets related to material impacts, risks and opportunities (quantitative)", "semi-narrative"),
        ("33", "Targets for the parts of the value chain most affected by the material IROs", "semi-narrative"),
        ("35", "Whether the targets are based on conclusive evidence, scientific evidence and the available international framework", "semi-narrative"),
        ("35", "Whether the targets have been validated by a recognised international framework or alliance", "semi-narrative"),
    ]),
    ("E4", "E4-5", [
        ("37", "Impact metrics related to biodiversity and ecosystems change", "table/measure", {"phase_in": PHASE_2025}),
        ("37", "Number of sites located in or near biodiversity-sensitive areas", "integer"),
        ("37", "Area (in hectares) located in or near biodiversity-sensitive areas", "table/measure"),
        ("37", "Question of whether the undertaking's operations interfere with protected areas (site status)", "boolean"),
        ("38", "Land use change indicators (MSA, STAR and PST) for the area affected by the undertaking", "table/measure", {"phase_in": PHASE_2025}),
        ("39", "Number of species on the IUCN red list with habitats in areas of activity", "integer"),
        ("40", "Impact of climate change and the interlinkage with E1", "semi-narrative"),
        ("41", "Potential monetary amounts from environmental damage (protected areas)", "monetary", {"conditional": True}),
    ]),
    ("E4", "E4-6", [
        ("43", "Anticipated financial effects of material biodiversity and ecosystem-related impacts, risks and opportunities", "semi-narrative", {"phase_in": PHASE_2026}),
        ("44", "Anticipated financial effects of material biodiversity and ecosystem-related impacts, risks and opportunities (quantitative)", "table/monetary", {"phase_in": PHASE_2026}),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS E5 — RESOURCE USE AND CIRCULAR ECONOMY
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("E5", "IRO-1", [
        ("AR7a", "Disclosure of business units associated with resource use and circular economy material impacts, risks and opportunities", "narrative"),
        ("AR7b", "Disclosure of material resources used", "narrative"),
        ("AR7c", "Disclosure of the material impacts and risks of staying in a business as usual model", "narrative"),
        ("AR7d", "Disclosure of the material opportunities related to the circular economy", "narrative"),
        ("AR7e", "Disclosure of the material impacts and risks of the transition to a circular economy", "narrative"),
        ("AR7f", "Disclosure of the stages of the value chain where resource use, risks and negative impacts are concentrated", "narrative"),
    ]),
    ("E5", "E5-1", [
        ("11", "Policies related to resource use and circular economy", "semi-narrative"),
        ("12", "Whether the policies address the shift to the use of resources in a more efficient way (circular economy)", "semi-narrative"),
        ("12", "Whether the policies address the use of secondary raw materials", "semi-narrative"),
        ("12", "Whether the policies address the adoption of circular design principles", "semi-narrative"),
        ("12", "Whether the policies limit the use of virgin raw materials", "semi-narrative"),
    ]),
    ("E5", "E5-2", [
        ("14", "Actions and resources in relation to resource use and circular economy", "semi-narrative"),
        ("14", "List of the actions taken during the reporting period with their scope", "semi-narrative"),
        ("14", "Cross-reference to the corresponding policies and targets", "semi-narrative"),
        ("14", "Financial resources allocated to the actions", "monetary"),
    ]),
    ("E5", "E5-3", [
        ("16", "Targets related to resource use and the circular economy", "semi-narrative"),
        ("16", "Targets adopted with a clear scope in relation to resource use and the circular economy", "semi-narrative"),
        ("16", "Locations of the targets and how they are linked to the undertaking's operations", "narrative"),
        ("16", "Targets to reduce the consumption of raw materials in absolute value", "semi-narrative"),
        ("17", "Whether the targets use the principles of the circular economy, in particular the circular economy principles", "semi-narrative"),
    ]),
    ("E5", "E5-4", [
        ("19", "Resource inflows and recycled material", "table/measure", {"origin": ORIGIN_SFDR}),
        ("19", "Materials used during the reporting period, with their corresponding amounts", "table/mass"),
        ("19", "Mass or volume of the material inputs used during the reporting period", "table/mass"),
        ("19", "Percentage of recycled materials used", "percentage"),
        ("20", "Description of the types and amounts of materials considered relevant to the undertaking's activity", "narrative"),
        ("20", "Description of the quantity and where in the value chain the materials are used", "narrative"),
        ("20", "Whether the materials are consumed in the direct operations of the undertaking, in the upstream or downstream value chain", "semi-narrative"),
        ("20", "Whether the materials inputs originate from renewable or non-renewable sources", "semi-narrative"),
        ("20", "Energy and water used in the production of the materials (if determined)", "narrative", {"conditional": True}),
        ("20", "Whether the materials are considered to be recycled (incl. recycled content)", "semi-narrative"),
        ("20", "Whether the materials have been reused (incl. the amount)", "semi-narrative"),
    ]),
    ("E5", "E5-5", [
        ("37", "Resource outflows", "table/mass", {"origin": ORIGIN_SFDR}),
        ("37", "Products and materials leaving the undertaking's value chain", "table/mass", {"origin": ORIGIN_SFDR}),
        ("37", "Hazardous waste and non-hazardous waste generated", "table/mass"),
        ("37", "Total amount of waste generated", "table/mass"),
        ("37", "Waste diverted from disposal", "table/mass"),
        ("37", "Hazardous waste diverted from disposal — preparation for reuse", "table/mass"),
        ("37", "Hazardous waste diverted from disposal — recycling", "table/mass"),
        ("37", "Hazardous waste diverted from disposal — other recovery operations", "table/mass"),
        ("37", "Non-hazardous waste diverted from disposal — preparation for reuse", "table/mass"),
        ("37", "Non-hazardous waste diverted from disposal — recycling", "table/mass"),
        ("37", "Non-hazardous waste diverted from disposal — other recovery operations", "table/mass"),
        ("37", "Waste directed to disposal", "table/mass"),
        ("37", "Hazardous waste directed to disposal — incineration", "table/mass"),
        ("37", "Hazardous waste directed to disposal — landfill", "table/mass"),
        ("37", "Hazardous waste directed to disposal — other disposal operations", "table/mass"),
        ("37", "Non-hazardous waste directed to disposal — incineration", "table/mass"),
        ("37", "Non-hazardous waste directed to disposal — landfill", "table/mass"),
        ("37", "Non-hazardous waste directed to disposal — other disposal operations", "table/mass"),
        ("37", "Non-recycled waste", "table/mass", {"origin": ORIGIN_SFDR}),
        ("38", "Description of the durable goods sold", "semi-narrative"),
        ("38", "Description of the packaging used for dangerous goods", "semi-narrative"),
        ("39", "Description of the non-durable goods sold (in particular textiles)", "semi-narrative"),
    ]),
    ("E5", "E5-6", [
        ("41", "Anticipated financial effects of the material resource use and circular economy-related impacts, risks and opportunities", "semi-narrative", {"phase_in": PHASE_2026}),
        ("42", "Anticipated financial effects of material resource use and circular economy-related impacts, risks and opportunities (quantitative)", "table/monetary", {"phase_in": PHASE_2026}),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS S1 — OWN WORKFORCE
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("S1", "S1-1", [
        ("16", "Policies related to own workforce", "semi-narrative"),
        ("16", "Description of the policies to eliminate gender discrimination and the gender equality principle", "semi-narrative"),
        ("17", "Description of the human rights policies adopted", "semi-narrative"),
        ("18", "Undertaking's commitments on social dialogue and consultation", "semi-narrative"),
        ("18", "Whether the policies cover the human rights issues globally in the different entities", "semi-narrative"),
        ("18", "Type of engagements and the frequency of engagement with workers' representatives", "semi-narrative"),
        ("20", "Whether the undertaking has a policy on the prevention of human rights impacts in its own operations", "boolean"),
        ("20", "Whether the undertaking has a policy that commits it to include respect for the human rights of its employees", "boolean"),
        ("20", "Whether the undertaking considers in its policies the labour principles of the International Labour Organization (ILO) Declarations", "boolean"),
        ("22", "Disclosure of the internal policy on workplace violence, harassment and occupational discrimination", "semi-narrative"),
    ]),
    ("S1", "S1-2", [
        ("24", "Processes for engaging with own workforce and workers' representatives about impacts", "semi-narrative"),
        ("24", "Description of how the engagement process is structured and is effective", "narrative"),
        ("24", "Undertaking's process for identifying and assessing how the policies and processes on the engagement are managed", "semi-narrative"),
        ("27", "Disclosure of the general process for assessing the impacts on own workforce", "semi-narrative"),
    ]),
    ("S1", "S1-3", [
        ("28", "Processes to remediate negative impacts and channels for own workforce to raise concerns", "semi-narrative"),
        ("29", "Description of how the undertakings remediates negative impacts arising from its own workforce", "narrative"),
        ("29", "Disclosure of the process for remediating the negative impacts that the undertaking has caused and contributed to, and its elements and responsibilities", "semi-narrative"),
        ("30", "Whether the undertaking provides any process or mechanism to raise concerns (incl. channels to raise concerns)", "semi-narrative"),
        ("30", "Whether the undertaking tracks issues identified and how it evaluates the effectiveness", "semi-narrative"),
        ("31", "Description of the channels available to own workforce to raise concerns and its use", "narrative"),
        ("31", "Whether the undertaking has established a specific internal complaint mechanism", "semi-narrative"),
    ]),
    ("S1", "S1-4", [
        ("32", "Taking action on material impacts on own workforce, and approaches to managing material risks and pursuing material opportunities", "semi-narrative"),
        ("32", "Approaches to managing material impacts on own workforce and pursuing material opportunities", "semi-narrative"),
        ("32", "Whether the undertaking has taken actions or implemented programmes to manage the negative impacts", "semi-narrative"),
        ("33", "Actions, their expected outcomes and whether they have been implemented", "semi-narrative"),
        ("34", "Whether the undertaking has implemented all the possible actions regarding the negative impacts", "semi-narrative", {"conditional": True}),
        ("34", "Actions taken or planned to avoid or mitigate adverse impacts and their effectiveness for material positive impacts", "semi-narrative"),
        ("36", "Whether the actions cover the areas of the impact on its own workforce", "semi-narrative"),
        ("36", "Whether the undertaking is prepared to undertake safety measures to avoid the impacts", "semi-narrative"),
        ("37", "Disclosure of the general and specific approaches to addressing material negative impacts", "narrative", {"conditional": True}),
        ("38", "Initiatives aimed at contributing to additional material positive impacts", "narrative", {"conditional": True}),
        ("39", "Description of the resource allocation and how far the undertaking has progressed in efforts during the reporting period", "semi-narrative", {"conditional": True}),
        ("39", "Disclosure of aims for continued improvement", "narrative", {"conditional": True}),
        ("40", "Whether the undertaking recognizes that the actions do not prevent the material negative impacts", "boolean"),
    ]),
    ("S1", "S1-5", [
        ("41", "Targets related to managing material negative impacts, advancing positive impacts, and managing material risks and opportunities", "semi-narrative"),
        ("41", "Description of the targets, with the corresponding quantitative values", "semi-narrative"),
        ("41", "Whether the targets are part of a wider engagement and how they are linked", "semi-narrative"),
        ("41", "Cross-reference with the other relevant targets and how the undertaking monitors its progress", "boolean"),
        ("42", "Undertaking's process for monitoring progress against the targets", "semi-narrative"),
        ("42", "Whether the targets are derived from external engagement", "boolean"),
        ("43", "Methodology used to calculate the targets and the baseline value", "narrative"),
    ]),
    ("S1", "S1-6", [
        ("40", "Characteristics of the undertaking's employees", "table/measure", {"origin": ORIGIN_SFDR}),
        ("40", "Number of employees (head count) at the end of the period", "integer"),
        ("40", "Number of employees (head count) during the period", "integer"),
        ("41", "Employees by gender (female)", "table/measure"),
        ("41", "Employees by gender (male)", "table/measure"),
        ("41", "Employees by gender (diverse)", "table/measure"),
        ("42", "Employees by country (for countries with 50 or more employees)", "table/measure"),
        ("43", "Employees by region", "table/measure"),
        ("44", "Employees under fixed-term contracts", "table/measure"),
        ("44", "Employees under permanent contracts", "table/measure"),
        ("45", "Employees under full-time contracts", "table/measure"),
        ("45", "Employees under part-time contracts", "table/measure"),
        ("46", "Employee turnover rate / number of employees whose employment has ceased", "percentage"),
        ("46", "Total number of employees that have left", "integer"),
        ("50", "All people performing work for the undertaking are employees", "boolean"),
        ("AR57", "Number of employees in countries with 50 or more employees", "integer"),
        ("AR95", "Total annual employee turnover in number and percentage", "table/measure"),
        ("AR61", "Undertaking does not have non-employees in own workforce", "semi-narrative", {"conditional": True}),
    ]),
    ("S1", "S1-7", [
        ("51", "Number of non-employees in the undertaking's own workforce", "integer", {"origin": ORIGIN_SFDR}),
        ("51", "Description of the characteristics of the non-employees in the undertaking's own workforce", "semi-narrative"),
        ("AR63", "Use of common methodologies through which other workers are counted", "semi-narrative", {"conditional": True}),
    ]),
    ("S1", "S1-8", [
        ("52", "Collective bargaining coverage in percentage at undertaking and EEA level", "percentage"),
        ("52", "Collective bargaining coverage and social dialogue disaggregated by country and/or region", "percentage", {"conditional": True}),
        ("55", "Percentage of employees covered by collective bargaining agreements in the EEA (for the undertaking)", "percentage"),
        ("55", "Percentage of employees covered by collective bargaining agreements in the EEA (for the sector)", "percentage"),
        ("55", "Percentage of employees covered by collective bargaining agreements outside the EEA", "percentage"),
        ("56", "Whether the undertaking has an agreement with its employees representing them", "semi-narrative", {"conditional": True}),
        ("AR64", "Percentage of own workforce covered by collective bargaining agreements and their coverage rate", "percentage"),
        ("AR66", "Whether the undertaking has a centralised collective bargaining agreement in place", "boolean"),
    ]),
    ("S1", "S1-9", [
        ("57", "Diversity — gender distribution at the top management level", "percentage", {"origin": ORIGIN_SFDR}),
        ("57", "Percentage share of female members at the top management level", "percentage"),
        ("57", "Diversity in the top management broken down by age group (<30, 30-50, >50)", "percentage"),
        ("59", "Employees by age group, in line with the national legislation", "percentage"),
        ("AR67", "Age of the employees, disaggregated into age bandwidths", "semi-narrative"),
    ]),
    ("S1", "S1-10", [
        ("60", "Adequate wages — whether the undertaking pays its employees an adequate wage in line with benchmarks", "semi-narrative"),
        ("61", "Description of the proportion of employees whose remuneration is derived from a benchmark wage or comparable standard", "narrative"),
        ("61", "Whether the wage corresponds to the applicable reference benchmark", "semi-narrative"),
        ("AR71", "Living wage benchmark used for the S1-10 disclosures", "semi-narrative"),
    ]),
    ("S1", "S1-11", [
        ("63", "Social protection — whether the undertaking covers its workforce with social protection related to income, sickness, disability, unemployment and pensions", "semi-narrative"),
        ("63", "Description of the extent to which each of the categories of its workforce is covered by social protection", "semi-narrative"),
        ("AR77", "Whether the applicable social protection measures are provided through the undertaking, the State or a third party", "semi-narrative"),
    ]),
    ("S1", "S1-12", [
        ("65", "Percentage of persons with disabilities amongst the undertaking's employees", "percentage", {"origin": ORIGIN_SFDR}),
        ("65", "Description of the characteristics of the persons with disabilities (age, gender, region, contract type)", "narrative", {"conditional": True}),
        ("AR79", "Disclosure of the data on people with disabilities hired during the period", "table/measure", {"conditional": True}),
    ]),
    ("S1", "S1-13", [
        ("66", "Training and skills development — the level of training in the undertaking by gender", "semi-narrative"),
        ("66", "Average training hours per employee (per person)", "decimal"),
        ("66", "Average training hours per employee by gender", "table/measure"),
        ("66", "Percentage of employees participating in training, by gender", "percentage"),
        ("66", "Skills development actions and programmes in place with a clear scope", "semi-narrative"),
        ("AR80", "Skill development metrics and typical characteristics of the own workforce", "table/measure"),
    ]),
    ("S1", "S1-14", [
        ("67", "Health and safety — percentage of the own workforce covered by the own health and safety systems based on legal requirements and/or recognised standards", "percentage"),
        ("68", "Work-related injuries recorded and reported to the undertaking's own workforce", "integer"),
        ("69", "Number of recordable work-related accidents", "integer"),
        ("69", "Rate of recordable work-related accidents per million hours, in percentage", "table/ratio"),
        ("70", "Incidence of occupational diseases per million hours (per 100 employees)", "table/ratio"),
        ("71", "Number of work-related injuries of employees (fatalities)", "integer"),
        ("72", "Prevention programmes and actions described in the health and safety management systems", "semi-narrative"),
        ("73", "Whether the disclosed figures are due to the health and safety management systems in place", "boolean"),
        ("AR82", "Number of fatalities in own workforce as a result of work-related injuries", "integer"),
        ("AR82", "Number of fatalities in own workforce as a result of work-related ill health", "integer"),
        ("AR82", "Number of fatalities as a result of work-related injuries of other workers working at the undertaking's sites", "integer"),
        ("AR88", "Lost days to work-related injuries and fatalities", "integer", {"conditional": True}),
        ("AR89", "Percentage of the undertaking's own workforce covered by its health and safety management system", "percentage"),
    ]),
    ("S1", "S1-15", [
        ("74", "Work-life balance — percentage of entitled employees who took family-related leave", "percentage", {"origin": ORIGIN_SFDR}),
        ("74", "Work-life balance — benefits provided to employees and entitlements to family-related leave", "semi-narrative"),
        ("75", "Family-related leave benefits and percentage of employees taking them", "percentage"),
        ("75", "Benefits provided to employees and entitlements to family-related leave, by employee type (female and male)", "semi-narrative"),
        ("AR96", "Family-related leave and percentage of employees taking such leave", "percentage"),
    ]),
    ("S1", "S1-16", [
        ("76", "Remuneration metrics (gap and total) — gender pay gap", "percentage", {"origin": ORIGIN_SFDR}),
        ("76", "Annual total pay gap, in percentage", "percentage", {"origin": ORIGIN_SFDR}),
        ("76", "Ratio between the highest paid individual's total annual remuneration and the median for employees (excluding the highest paid individual)", "table/ratio"),
        ("76", "Gender pay gap in percentage", "percentage"),
        ("76", "Annual total compensation ratio", "table/ratio"),
        ("76", "Total remuneration ratio, in percentage", "table/ratio"),
        ("77", "Description of the undertaking's remuneration policy and how the pay gap is closed", "narrative"),
        ("78", "Whether the remuneration policy has been disclosed publicly", "boolean"),
        ("78", "Notably, including the remuneration policy for members of the management team", "boolean"),
        ("AR97", "UNDERTAKING'S remuneration policy and how the pay gap relates to it", "narrative"),
    ]),
    ("S1", "S1-17", [
        ("79", "Incidents, complaints and severe human rights impacts; processes to remedy them", "semi-narrative"),
        ("79", "Description of the incidents, complaints and severe human rights impacts", "narrative"),
        ("80", "Processes for remediation of severe negative human rights impacts", "narrative"),
        ("80", "Whether the process provides a grievance mechanism", "boolean"),
        ("81", "Number of incidents of discrimination, including harassment, reported during the reporting period", "integer"),
        ("82", "Number of complaints filed through the channels for people in the undertaking's own workforce", "integer"),
        ("82", "Number of complaints relating to the UN Guiding Principles on Business and Human Rights and OECD Guidelines", "integer"),
        ("83", "Amount of fines, penalties and compensation for damages in relation to the incidents", "monetary"),
        ("85", "Process to engage with persons in the undertaking's own workforce to identify, address and remediate the negative impacts", "semi-narrative"),
        ("86", "Description of the actual material consequences of the incidents, and how they have been remediated", "narrative"),
        ("88", "Whether there have been severe human rights issues and incidents connected to the undertaking's own workforce", "boolean", {"conditional": True}),
        ("AR98", "UNDERTAKING's capacity to continue the operations during the reporting period", "semi-narrative"),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS S2 — WORKERS IN THE VALUE CHAIN
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("S2", "S2-1", [
        ("15", "Policies related to value chain workers", "semi-narrative"),
        ("16", "Description of the human rights policy commitments to respect the human rights of value chain workers", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("17", "Whether the undertaking has a policy on the prevention of human rights impacts in its value chain", "boolean", {"origin": ORIGIN_SFDR}),
        ("17", "Existing policy that includes respect for the human rights of the value chain workers", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("17", "Commitment of the undertaking to apply the labour principles in the value chain", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("18", "Whether the undertaking has a policy that addresses the issues of its suppliers that might expose to ascending social violations", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("18", "Whether the policy respects the UN Guiding Principles and the OECD Guidelines", "boolean"),
        ("18", "Whether the policy includes the objectives of the EU legislation (for the risks of child labour and forced labour)", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("19", "Whether the undertaking has a policy addressing the risks of child and forced labour in its value chain", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("19", "Whether the policy commits to the elimination of child and forced labour", "semi-narrative"),
    ]),
    ("S2", "S2-2", [
        ("21", "Processes for engaging with value chain workers about impacts", "semi-narrative"),
        ("22", "Whether the undertaken has a process to engage with the affected stakeholders", "boolean", {"conditional": True}),
        ("23", "Description of the process for engaging with the affected value chain workers", "semi-narrative"),
        ("24", "Whether the engagement is with the directly affected value chain workers or with trade unions or similar", "semi-narrative"),
        ("24", "Undertaking's overall approach to engage with value chain workers and their representatives", "semi-narrative"),
        ("25", "Whether the undertaking cooperates with the value chain workers (Their views, perceptions and experiences)", "semi-narrative"),
    ]),
    ("S2", "S2-3", [
        ("26", "Processes to remediate negative impacts and channels for value chain workers", "semi-narrative"),
        ("27", "Description of the process to provide or cooperate in the remediation of negative impacts", "semi-narrative", {"conditional": True}),
        ("28", "Whether the undertaking provides access to remediation", "semi-narrative", {"conditional": True}),
        ("28", "How the undertaking evaluates the effectiveness of the remediation", "semi-narrative"),
        ("29", "The channel(s) available to value chain workers to raise concerns and their use", "narrative", {"conditional": True}),
    ]),
    ("S2", "S2-4", [
        ("30", "Taking action on material impacts on value chain workers, approaches to mitigating material risks, and pursuing material opportunities", "semi-narrative"),
        ("31", "Actions taken or planned to avoid or mitigate adverse impacts", "semi-narrative"),
        ("32", "Whether the actions cover the areas of the value chain workers", "semi-narrative"),
        ("33", "Disclosure of the general and specific approaches to addressing material negative impacts", "narrative", {"conditional": True}),
        ("34", "Initiatives aimed at contributing to additional material positive impacts", "narrative", {"conditional": True}),
        ("35", "How far the undertaking has progressed in efforts during the reporting period", "semi-narrative", {"conditional": True}),
        ("35", "Disclosure of aims for continued improvement", "narrative", {"conditional": True}),
    ]),
    ("S2", "S2-5", [
        ("36", "Targets related to managing material negative impacts, advancing positive impacts, and managing material risks and opportunities", "semi-narrative"),
        ("36", "Description of the targets, with the corresponding quantitative values", "semi-narrative"),
        ("36", "Whether the targets are part of a wider engagement", "semi-narrative"),
        ("37", "Disclosure of whether the targets are derived from external engagement", "boolean"),
        ("37", "Methodology used to calculate the targets and the baseline value", "narrative"),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS S3 — AFFECTED COMMUNITIES
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("S3", "S3-1", [
        ("12", "Policies related to affected communities", "semi-narrative"),
        ("13", "Description of the human rights policy commitments to respect the human rights of affected communities", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("14", "Whether the undertaking has a policy on the prevention of human rights impacts on affected communities", "boolean", {"origin": ORIGIN_SFDR}),
        ("14", "Policy that includes respect for the human rights of affected communities", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("16", "Description of the commitment of the undertaking to avoid and mitigate direct and indirect impacts", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("16", "Whether the commitment respects the UN Guiding Principles and the OECD Guidelines", "boolean"),
        ("17", "Whether the undertaking has a policy that addresses indigenous people's rights and the principle of free prior and informed consent", "semi-narrative", {"origin": ORIGIN_SFDR}),
    ]),
    ("S3", "S3-2", [
        ("19", "Processes for engaging with affected communities about impacts", "semi-narrative"),
        ("20", "Processes to engage with affected communities and to carry out the engagement", "semi-narrative"),
        ("21", "Description of the processes of the undertaking to engage with affected communities", "semi-narrative"),
        ("22", "Whether the undertaking has developed specific practices for the engagement in collective processes", "narrative"),
        ("23", "Whether the undertaken has committed to informing affected communities of potential adverse impacts", "semi-narrative", {"conditional": True}),
    ]),
    ("S3", "S3-3", [
        ("24", "Processes to remediate negative impacts and channels for affected communities", "semi-narrative"),
        ("25", "Process to provide or cooperate in the remediation of negative impacts", "semi-narrative", {"conditional": True}),
        ("26", "The process to remediate negative impacts, incl. the responsibility for the remediation", "narrative"),
        ("27", "The channel(s) available to affected communities to raise concerns, and their use", "narrative", {"conditional": True}),
    ]),
    ("S3", "S3-4", [
        ("28", "Taking action on material impacts on affected communities, approaches to managing material risks, and pursuing material opportunities", "semi-narrative"),
        ("29", "Actions taken or planned to avoid or mitigate adverse impacts", "semi-narrative"),
        ("29", "Whether the actions take into account the possible different impacts on women, men and other groups", "semi-narrative"),
        ("30", "Whether the undertaking has taken any actions to promote the positive impacts and provides an assessment", "semi-narrative"),
        ("31", "Disclosure of the general and specific approaches to addressing material negative impacts", "narrative", {"conditional": True}),
        ("32", "Social investment or other development programmes aimed at contributing to additional material positive impacts", "narrative", {"conditional": True}),
        ("33", "How far the undertaking has progressed in efforts during the reporting period", "semi-narrative", {"conditional": True}),
        ("33", "Disclosure of aims for continued improvement", "narrative", {"conditional": True}),
    ]),
    ("S3", "S3-5", [
        ("34", "Targets related to managing material negative impacts, advancing positive impacts, and managing material risks and opportunities", "semi-narrative"),
        ("34", "Description of the targets and the corresponding quantitative values", "semi-narrative"),
        ("35", "Disclosure of whether the targets are part of a wider engagement and their link to it", "boolean"),
        ("36", "Methodology used to calculate the targets and the baseline value", "narrative"),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS S4 — CONSUMERS AND END-USERS
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("S4", "S4-1", [
        ("13", "Policies related to consumers and end-users", "semi-narrative"),
        ("14", "Description of the human rights policy commitments to respect the human rights of consumers and end-users", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("15", "Whether the undertaking has a policy committed to the prevention of human rights impacts on consumers and end-users", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("16", "Whether the undertaking respects the UN Guiding Principles and the OECD Guidelines", "boolean"),
        ("17", "Policies to prevent the negative impacts on consumers and end-users, incl. the coordinated use of the UN Guiding Principles", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("18", "Whether the undertaking has a policy in place to avoid the sale of products that are legal to sell but can cause harm to people", "semi-narrative"),
    ]),
    ("S4", "S4-2", [
        ("20", "Processes for engaging with consumers and end-users about impacts", "semi-narrative"),
        ("20", "Description of the undertaking's processes to engage consumers and end-users", "semi-narrative"),
        ("21", "Whether the processes are driven by the interaction with the consumers and end-users", "semi-narrative"),
        ("22", "Description of the process for carrying out the engagement", "semi-narrative"),
        ("23", "Whether the process considers the consumers and end-users from an accessibility perspective", "boolean", {"conditional": True}),
        ("24", "Type of engagement with the consumers and end-users, including its frequency", "semi-narrative"),
    ]),
    ("S4", "S4-3", [
        ("25", "Processes to remediate negative impacts and channels for consumers and end-users", "semi-narrative"),
        ("26", "Process to provide or cooperate in the remediation of negative impacts", "semi-narrative", {"conditional": True}),
        ("27", "The process for remediating negative impacts, including the responsibility for the remediation", "narrative"),
        ("28", "The channel(s) available to consumers and end-users to raise concerns, and their use", "narrative", {"conditional": True}),
    ]),
    ("S4", "S4-4", [
        ("29", "Taking action on material impacts on consumers and end-users, approaches to managing material risks, and pursuing material opportunities", "semi-narrative"),
        ("29", "Approaches to managing material risks and pursuing material opportunities from consumers and end-users", "semi-narrative"),
        ("30", "Actions to avoid or mitigate adverse impacts", "semi-narrative"),
        ("31", "Description of the undertaken actions with their expected outcomes", "semi-narrative"),
        ("32", "Whether the undertaking has publicly documented the effectiveness and progress of the actions", "semi-narrative"),
        ("33", "Disclosure of the general and specific approaches to addressing material negative impacts", "narrative", {"conditional": True}),
        ("34", "Initiatives aimed at contributing to additional material positive impacts", "narrative", {"conditional": True}),
        ("35", "How far the undertaking has progressed in efforts during the reporting period", "semi-narrative", {"conditional": True}),
        ("35", "Disclosure of aims for continued improvement", "narrative", {"conditional": True}),
    ]),
    ("S4", "S4-5", [
        ("36", "Targets related to managing material negative impacts, advancing positive impacts, and managing material risks and opportunities", "semi-narrative"),
        ("36", "Description of the targets and the corresponding quantitative values", "semi-narrative"),
        ("37", "Disclosure of whether the targets are part of a wider engagement", "boolean"),
        ("37", "Methodology used to calculate the targets and the baseline value", "narrative"),
        ("38", "Undertaking's process for monitoring progress against the targets", "semi-narrative"),
    ]),
])

# ═══════════════════════════════════════════════════════════════════════════
# ESRS G1 — BUSINESS CONDUCT
# ═══════════════════════════════════════════════════════════════════════════
_drs([
    ("G1", "G1-1", [
        ("8", "Policies related to business conduct", "semi-narrative"),
        ("9", "Description of the business conduct policies adopted", "semi-narrative"),
        ("10", "Whether the undertaking has adopted policies on the conduct of business that address corruption and bribery", "semi-narrative"),
        ("10", "Description of the conventions that the undertaking has adopted against corruption and bribery (UN Convention against Corruption)", "semi-narrative", {"origin": ORIGIN_SFDR}),
        ("10", "Whether the undertaking has a zero-tolerance policy on corruption and bribery", "boolean"),
        ("10", "Description of the internal procedures to prevent corruption and bribery", "semi-narrative"),
        ("10", "Description of the actions taken to ensure that the undertaking prohibits the use of influence and the lobbying of public authorities", "semi-narrative"),
        ("10c", "Information about the establishment of internal whistleblower reporting channels", "narrative"),
        ("10c", "Information about measures to protect against retaliation to own workers who are whistleblowers, in accordance with applicable law transposing Directive (EU) 2019/1937", "narrative"),
        ("11", "Whether the undertaking has adopted the code of conduct for its operation", "semi-narrative"),
        ("11", "Whether the code has been aligned with the national anti-corruption framework and the OECD Convention", "semi-narrative"),
        ("11", "Whether the code of conduct is also implemented in the supply chain", "boolean"),
        ("11", "Whether the undertakings has adopted the code that is aligned with the corporate responsibility", "semi-narrative"),
        ("12", "Whether there is a policy for the protection of whistleblowers", "boolean"),
        ("12", "Whether there is an internal procedure to collect reports", "boolean"),
        ("12", "Whether there is a mechanism to protect the privacy of whistleblowers", "boolean"),
        ("13", "Description of the internal awareness raising programmes", "narrative"),
    ]),
    ("G1", "G1-2", [
        ("15", "Management of relationships with suppliers", "semi-narrative"),
        ("15", "Anticipation of the impacts of its relationships and how to manage them", "semi-narrative"),
        ("15", "Description of the general approach to the management of social and environmental issues in its relationships with suppliers", "semi-narrative"),
        ("15", "How the relationship with its suppliers is managed", "narrative"),
        ("16", "Description of the internal process of the anti-corruption and anti-bribery covers", "semi-narrative"),
        ("16", "Whether the process extends to all the relationships", "semi-narrative"),
        ("16", "Description of the inclusion of the suppliers in the engagement process", "semi-narrative"),
        ("17", "Description of the training carried out and the stakeholders involved", "narrative"),
        ("18", "Description of the escalation of the issues to the highest governance body and how", "narrative"),
        ("18", "The involvement, only where necessary, of advisory committees or other advisory bodies in the process to disclose the conclusion on the relationships", "semi-narrative", {"conditional": True}),
    ]),
    ("G1", "G1-3", [
        ("20", "Incidents of corruption or bribery", "semi-narrative"),
        ("21", "Whether there have been incidents of corruption or bribery during the reporting period", "boolean"),
        ("22", "Description of the incidents of corruption or bribery", "narrative", {"conditional": True}),
        ("23", "Number of convictions and the amount of fines paid for the violations", "integer"),
        ("23a", "Number of convictions and the amount of fines paid for the violations of anti-corruption and anti-bribery laws", "integer", {"origin": ORIGIN_SFDR}),
        ("23b", "Description of the nature of the violation and the follow-up measures undertaken", "narrative"),
        ("23c", "Whether the incident has taken place in the current or in prior periods", "semi-narrative"),
        ("23d", "Whether the undertaking has adopted any measures to improve its procedures", "boolean"),
        ("23e", "Whether the undertaking has entered into a settlement with the authorities or civil parties", "boolean"),
        ("23f", "Whether the incident has resulted in a conviction and the corresponding sanction type", "semi-narrative"),
        ("AR3", "Number of confirmed incidents in which employees were dismissed or disciplined for corruption or bribery", "integer"),
        ("AR4", "Number of confirmed incidents when contracts with business partners were terminated or not renewed", "integer"),
    ]),
    ("G1", "G1-4", [
        ("25", "Confirmed incidents in which employees were dismissed or disciplined for corruption or bribery", "integer", {"conditional": True}),
        ("26", "Number of confirmed incidents when contracts with business partners were terminated or not renewed", "integer", {"conditional": True}),
    ]),
    ("G1", "G1-5", [
        ("27", "Political influence and lobbying activities", "semi-narrative"),
        ("28", "Whether the undertaking has experienced negative political influence on the activities", "semi-narrative"),
        ("28", "The extent to which the undertaking has been engaged in the political influence", "narrative"),
        ("29", "Description of the political lobbying activities and the links", "semi-narrative"),
        ("30", "Whether the undertaking has made political contributions to political parties", "semi-narrative"),
        ("30", "Expenditure on political contributions", "monetary", {"conditional": True}),
        ("31", "Whether the undertaking has registered as a lobbyist", "boolean"),
        ("31", "Membership of the European Union Transparency Register", "boolean"),
    ]),
    ("G1", "G1-6", [
        ("33", "Payment practices", "semi-narrative"),
        ("34", "The average number of days taken to pay invoices from the date of reception of the invoice", "integer"),
        ("34", "Percentage of the payments aligned with the standard payment terms", "percentage", {"conditional": True}),
        ("34", "How many percent of the invoices paid are in line with the standard of '30/60 days'", "percentage", {"conditional": True}),
        ("36", "Whether the undertaking has faced any legal proceedings for late payments", "boolean", {"origin": ORIGIN_SFDR}),
    ]),
])

# ─── Public helpers ─────────────────────────────────────────────────────────

_STANDARD_META = {
    "2": {"code": "ESRS 2", "name": "General disclosures", "body": "EFRAG / CSRD", "order": 0},
    "E1": {"code": "ESRS E1", "name": "Climate change", "body": "EFRAG / CSRD", "order": 1},
    "E2": {"code": "ESRS E2", "name": "Pollution", "body": "EFRAG / CSRD", "order": 2},
    "E3": {"code": "ESRS E3", "name": "Water and marine resources", "body": "EFRAG / CSRD", "order": 3},
    "E4": {"code": "ESRS E4", "name": "Biodiversity and ecosystems", "body": "EFRAG / CSRD", "order": 4},
    "E5": {"code": "ESRS E5", "name": "Resource use and circular economy", "body": "EFRAG / CSRD", "order": 5},
    "S1": {"code": "ESRS S1", "name": "Own workforce", "body": "EFRAG / CSRD", "order": 6},
    "S2": {"code": "ESRS S2", "name": "Workers in the value chain", "body": "EFRAG / CSRD", "order": 7},
    "S3": {"code": "ESRS S3", "name": "Affected communities", "body": "EFRAG / CSRD", "order": 8},
    "S4": {"code": "ESRS S4", "name": "Consumers and end-users", "body": "EFRAG / CSRD", "order": 9},
    "G1": {"code": "ESRS G1", "name": "Business conduct", "body": "EFRAG / CSRD", "order": 10},
}

ESRS_STANDARDS: dict[str, dict[str, Any]] = {k: dict(v) for k, v in _STANDARD_META.items()}

# Inferred from EFRAG IG 1 (value-chain boundary focus per topical standard).
STANDARD_VALUE_CHAIN: dict[str, str] = {
    "2": "all", "E1": "all", "E2": "all", "E3": "all", "E4": "all", "E5": "all",
    "S1": "own", "S2": "all", "S3": "all", "S4": "all", "G1": "all",
}


def by_standard(standard: str | None = None) -> list[dict[str, Any]]:
    if standard:
        return [d for d in ESRS_DATAPOINTS if d["standard"] == standard]
    return list(ESRS_DATAPOINTS)


def by_dr(dr: str) -> list[dict[str, Any]]:
    return [d for d in ESRS_DATAPOINTS if d["dr"] == dr]


def by_id(dp_id: str) -> dict[str, Any] | None:
    for d in ESRS_DATAPOINTS:
        if d["id"] == dp_id:
            return d
    return None


def search(query: str, *, standard: str | None = None) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    dp = by_standard(standard) if standard else ESRS_DATAPOINTS
    if not q:
        return list(dp)
    return [
        d for d in dp
        if q in d["name"].lower() or q in d["id"].lower() or q in d["dr"].lower()
    ]


def get_drs(standard: str | None = None) -> list[str]:
    return sorted({d["dr"] for d in by_standard(standard)})


def coverage_stats(standard: str | None = None) -> dict[str, Any]:
    """Per-standard stats: total datapoints, discretionary flags, EU-law origins."""
    dp = by_standard(standard) if standard else ESRS_DATAPOINTS
    by_std: dict[str, list[dict[str, Any]]] = {}
    for d in dp:
        by_std.setdefault(d["standard"], []).append(d)
    rows = []
    for std in sorted(by_std, key=lambda s: _STANDARD_META[s]["order"]):
        items = by_std[std]
        rows.append({
            "standard": std,
            "code": _STANDARD_META[std]["code"],
            "name": _STANDARD_META[std]["name"],
            "datapoints": len(items),
            "dr_count": len({d["dr"] for d in items}),
            "mandatory": sum(1 for d in items if d["requirement"] != "may"),
            "voluntary": sum(1 for d in items if d["requirement"] == "may"),
            "conditional": sum(1 for d in items if d["conditional"]),
            "phase_in": sorted({d["phase_in"] for d in items if d["phase_in"]}),
        })
    return {
        "total_datapoints": len(dp),
        "standards": rows,
        "derived_from_eu_legislation": sorted({
            d["origin"] for d in dp if d["origin"]
        }),
    }
