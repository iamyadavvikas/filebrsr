"""Regenerate the frontend BRSR datapoint mirror from the canonical catalog.

The platform keeps a hand-maintained 1:1 copy of the backend BRSR_DATAPOINTS
catalog at frontend/src/lib/brsr-datapoints.ts. That copy drifted from the
catalog (most notably the legacy `core` over-flags). This script regenerates it
from app.brsr_datapoints.BRSR_DATAPOINTS after import-time canonicalization so
the two can never diverge again.

Run from backend/:  python scripts/sync_brsr_frontend_datapoints.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.brsr_datapoints import BRSR_DATAPOINTS  # noqa: E402

OUT = BACKEND_DIR.parent / "frontend" / "src" / "lib" / "brsr-datapoints.ts"


def _ts_str(v: str | None) -> str:
    return "null" if v is None else json.dumps(v, ensure_ascii=False)


def _ts_bool(v: bool) -> str:
    return "true" if v else "false"


STATIC_SUFFIX = """\
export const SECTION_LABELS: Record<string, string> = {
  section_a: "Section A: General Disclosures",
  section_b: "Section B: Management & Process Disclosures",
  section_c: "Section C: Principle-wise Performance Disclosures",
};

export const SUBSECTION_LABELS: Record<string, string> = {
  csr_details: "Csr Details",
  details_of_entity: "Details Of Entity",
  employees: "Employees",
  governance: "Governance",
  holding_subsidiary: "Holding Subsidiary",
  operations: "Operations",
  policy_management: "Policy Management",
  principle_1: "Principle 1",
  principle_2: "Principle 2",
  principle_3: "Principle 3",
  principle_4: "Principle 4",
  principle_5: "Principle 5",
  principle_6: "Principle 6",
  principle_7: "Principle 7",
  principle_8: "Principle 8",
  principle_9: "Principle 9",
  products_services: "Products Services",
  transparency: "Transparency",
};

export const FIELD_TO_DATAPOINT_MAP: Record<string, string[]> = {
  cin: ["A.I.1"],
  company_name: ["A.I.2"],
  year_of_incorporation: ["A.I.3"],
  registered_office: ["A.I.4"],
  corporate_office: ["A.I.5"],
  email: ["A.I.6"],
  telephone: ["A.I.7"],
  website: ["A.I.8"],
  financial_year: ["A.I.9"],
  stock_exchange: ["A.I.10"],
  paid_up_capital: ["A.I.11"],
  contact_person: ["A.I.12"],
  reporting_boundary: ["A.I.13"],
  assurance_provider: ["A.I.14"],
  assurance_type: ["A.I.15"],
  business_activities: ["A.II.1"],
  products_services: ["A.II.2"],
  nic_codes: ["A.II.3"],
  num_plants_national: ["A.III.1"],
  num_plants_international: ["A.III.2"],
  num_offices_national: ["A.III.3"],
  num_offices_international: ["A.III.4"],
  markets_states_uts: ["A.III.5"],
  markets_countries: ["A.III.6"],
  exports_pct_of_turnover: ["A.III.7"],
  types_of_customers: ["A.III.8"],
  employees_permanent_male: ["A.IV.1"],
  employees_permanent_female: ["A.IV.2"],
  employees_permanent_total: ["A.IV.3"],
  employees_permanent: ["A.IV.3"],
  employees_contract_male: ["A.IV.4"],
  employees_contract_female: ["A.IV.5"],
  employees_contract_total: ["A.IV.6"],
  employees_contract: ["A.IV.6"],
  workers_permanent_male: ["A.IV.7"],
  workers_permanent_female: ["A.IV.8"],
  workers_permanent_total: ["A.IV.9"],
  workers_contract_male: ["A.IV.10"],
  workers_contract_female: ["A.IV.11"],
  workers_contract_total: ["A.IV.12"],
  differently_abled_employees: ["A.IV.13"],
  women_employees_pct: ["A.IV.2", "A.IV.1"],
  turnover: ["A.V.1"],
  net_worth: ["A.V.2"],
  subsidiaries_count: ["A.V.3"],
  csr_applicable: ["A.V.4"],
  csr_turnover_threshold: ["A.V.4"],
  policy_p1_ethics: ["B.1"],
  policy_p2_product: ["B.1"],
  policy_p3_wellbeing: ["B.1"],
  policy_p4_stakeholder: ["B.1"],
  policy_p5_human_rights: ["B.1"],
  policy_p6_environment: ["B.1"],
  policy_p7_advocacy: ["B.1"],
  policy_p8_inclusive: ["B.1"],
  policy_p9_consumer: ["B.1"],
  policy_available: ["B.1"],
  policies_approved_by_board: ["B.2"],
  policy_approved_by_board: ["B.2"],
  policy_board_approved: ["B.2"],
  policies_conform_to_national_guidelines: ["B.3"],
  policies_extended_to_value_chain: ["B.4"],
  policy_extends_value_chain: ["B.4"],
  committee_of_board_for_esg: ["B.5"],
  sustainability_committee: ["B.5"],
  esg_committee_details: ["B.5"],
  compliance_violations_fines: ["B.6"],
  complaints_sexual_harassment_filed: ["B.7"],
  complaints_sexual_harassment_resolved: ["B.7"],
  complaints_discrimination_filed: ["B.8"],
  complaints_child_labour_filed: ["B.9"],
  complaints_forced_labour_filed: ["B.10"],
  complaints_wages_filed: ["B.11"],
  grievance_redressal_mechanism: ["B.12"],
  grievance_mechanism: ["B.12"],
  stakeholder_grievances_filed: ["B.13"],
  stakeholder_grievances_resolved: ["B.13"],
  directors_with_esg_training: ["B.14"],
  policy_web_link: ["B.1"],
  policy_translated_to_procedures: ["B.3"],
  ngrbc_review_frequency: ["B.3"],
  code_of_conduct: ["C.P1.E.1"],
  code_of_conduct_for_all: ["C.P1.E.1"],
  anti_corruption_policy: ["C.P1.E.2"],
  whistle_blower_policy: ["C.P1.E.3"],
  ethics_complaints_current_fy: ["C.P1.E.4"],
  ethics_complaints_previous_fy: ["C.P1.E.4"],
  complaints_ethics: ["C.P1.E.4"],
  conflicts_of_interest_cases: ["C.P1.E.5"],
  disciplinary_actions_corruption: ["C.P1.E.6"],
  anti_competitive_cases: ["C.P1.E.7"],
  r_and_d_spend: ["C.P2.E.1"],
  r_and_d_capex_pct: ["C.P2.E.1"],
  sustainable_sourcing_pct: ["C.P2.E.2"],
  recycled_input_pct: ["C.P2.E.3"],
  products_with_epr: ["C.P2.E.4"],
  products_recyclable_pct: ["C.P2.E.5"],
  products_reusable_pct: ["C.P2.E.5"],
  lis_certification: ["C.P2.E.6"],
  environmental_social_risks_assessed: ["C.P2.E.7"],
  employee_turnover_rate: ["C.P3.E.1"],
  worker_turnover_rate: ["C.P3.E.1"],
  median_salary_male: ["C.P3.E.2"],
  median_salary_female: ["C.P3.E.2"],
  gross_wages_female_pct: ["C.P3.E.3"],
  safety_incidents_ltifr: ["C.P3.E.4"],
  safety_incidents: ["C.P3.E.4"],
  safety_fatalities: ["C.P3.E.5"],
  training_hours_per_employee: ["C.P3.E.6"],
  training_hours_per_worker: ["C.P3.E.6"],
  health_insurance_coverage_pct: ["C.P3.E.7"],
  maternity_benefits_pct: ["C.P3.E.8"],
  paternity_benefits_pct: ["C.P3.E.8"],
  disability_benefits: ["C.P3.E.9"],
  return_to_work_retention_rate: ["C.P3.E.10"],
  employees_in_union_pct: ["C.P3.E.11"],
  minimum_wages_paid: ["C.P3.E.12"],
  stakeholder_groups_identified: ["C.P4.E.1"],
  stakeholder_engagement_frequency: ["C.P4.E.2"],
  vulnerable_groups_identified: ["C.P4.E.3"],
  special_initiatives_vulnerable: ["C.P4.E.4"],
  human_rights_training_employees_pct: ["C.P5.E.1"],
  human_rights_training_workers_pct: ["C.P5.E.1"],
  human_rights_training_pct: ["C.P5.E.1"],
  minimum_wage_compliance: ["C.P5.E.2"],
  child_labor_complaints: ["C.P5.E.3"],
  forced_labor_complaints: ["C.P5.E.4"],
  wages_complaints: ["C.P5.E.5"],
  human_rights_due_diligence: ["C.P5.E.6"],
  remediation_mechanisms: ["C.P5.E.7"],
  energy_consumption_total: ["C.P6.E.1"],
  energy_consumption_total_gj: ["C.P6.E.1"],
  energy_from_renewable_gj: ["C.P6.E.2"],
  renewable_energy_pct: ["C.P6.E.3"],
  energy_intensity_per_rupee: ["C.P6.E.4"],
  pat_scheme_participation: ["C.P6.E.5"],
  water_withdrawal: ["C.P6.E.6"],
  water_withdrawal_kl: ["C.P6.E.6"],
  water_recycled_kl: ["C.P6.E.7"],
  water_recycled_pct: ["C.P6.E.8"],
  zero_liquid_discharge: ["C.P6.E.9"],
  ghg_scope1: ["C.P6.E.10"],
  ghg_scope1_tco2e: ["C.P6.E.10"],
  ghg_scope2: ["C.P6.E.11"],
  ghg_scope2_tco2e: ["C.P6.E.11"],
  ghg_scope3_tco2e: ["C.P6.L.7"],
  ghg_intensity_per_rupee: ["C.P6.E.12"],
  waste_generated: ["C.P6.E.13"],
  waste_generated_mt: ["C.P6.E.13"],
  waste_recycled_mt: ["C.P6.E.14"],
  waste_recycled_pct: ["C.P6.E.15"],
  hazardous_waste_mt: ["C.P6.E.16"],
  single_use_plastic_reduced: ["C.P6.E.17"],
  biodiversity_impact_assessed: ["C.P6.E.18"],
  air_emissions_nox: ["C.P6.E.19"],
  air_emissions_sox: ["C.P6.E.20"],
  air_emissions_pm: ["C.P6.E.21"],
  environmental_compliance_violations: ["C.P6.E.75"],
  trade_associations: ["C.P7.E.1"],
  trade_associations_member: ["C.P7.E.1"],
  advocacy_on_public_policy: ["C.P7.E.2"],
  anti_competitive_conduct_cases: ["C.P7.E.4"],
  public_policy_positions: ["C.P7.E.2"],
  csr_spend: ["C.P8.E.1"],
  csr_spend_current_fy: ["C.P8.E.1"],
  csr_spend_previous_fy: ["C.P8.E.1"],
  csr_obligation: ["C.P8.E.2"],
  community_beneficiaries: ["C.P8.E.3"],
  local_procurement_pct: ["C.P8.E.4"],
  input_from_msme_pct: ["C.P8.E.5"],
  input_from_small_producers_pct: ["C.P8.E.6"],
  csr_projects_count: ["C.P8.E.7"],
  social_impact_assessments: ["C.P8.L.1"],
  rehabilitation_resettlement: ["C.P8.L.2"],
  consumer_complaints: ["C.P9.E.1"],
  consumer_complaints_current_fy: ["C.P9.E.1"],
  consumer_complaints_resolved_pct: ["C.P9.E.2"],
  consumer_complaints_pending: ["C.P9.E.3"],
  product_recalls: ["C.P9.E.4"],
  data_privacy_complaints: ["C.P9.E.5"],
  data_breaches: ["C.P9.E.19"],
  cyber_security_policy: ["C.P9.E.6"],
  advertising_complaints: ["C.P9.E.7"],
  product_quality_certifications: ["C.P9.E.8"],
  customer_satisfaction_survey: ["C.P9.L.7"],
};
"""


def _ts_entry(dp: dict) -> str:
    return (
        "  { id: "
        + _ts_str(dp["id"])
        + ", label: "
        + _ts_str(dp["label"])
        + ", data_type: "
        + _ts_str(dp["data_type"])
        + ", mandatory: "
        + _ts_bool(dp["mandatory"])
        + ", core: "
        + _ts_bool(dp["core"])
        + ", indicator_type: "
        + _ts_str(dp["indicator_type"])
        + ", section: "
        + _ts_str(dp["section"])
        + ", subsection: "
        + _ts_str(dp["subsection"])
        + ", esrs_ref: "
        + _ts_str(dp["esrs_ref"])
        + ", paragraph_ref: "
        + _ts_str(dp["paragraph_ref"])
        + ", conditional: "
        + _ts_bool(dp["conditional"])
        + " },"
    )

lines = [
    "// Auto-generated from SEBI BRSR Annexure II "
    f"({len(BRSR_DATAPOINTS)} mandatory + voluntary datapoints)",
    "// Source: SEBI Circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122",
    "// Cross-referenced with EFRAG IG 3 (ESRS) methodology",
    '// REGENERATE with: python scripts/sync_brsr_frontend_datapoints.py',
    "",
    "export interface BRSRDatapoint {",
    "  id: string;",
    "  label: string;",
    "  data_type: string;",
    "  mandatory: boolean;",
    "  core: boolean;",
    "  indicator_type: string;",
    "  section: string;",
    "  subsection: string;",
    "  esrs_ref: string | null;",
    "  paragraph_ref: string;",
    "  conditional: boolean;",
    "}",
    "",
    "export const BRSR_DATAPOINTS: BRSRDatapoint[] = [",
]
for dp in BRSR_DATAPOINTS:
    lines.append(_ts_entry(dp))
lines.append("];")
lines.append("")
lines.append(STATIC_SUFFIX)

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {len(BRSR_DATAPOINTS)} datapoints -> {OUT}")

core_count = sum(1 for dp in BRSR_DATAPOINTS if dp["core"])
print(f"core flags: {core_count}")
