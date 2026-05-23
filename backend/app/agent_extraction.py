"""
Multi-Pass BRSR Extraction Agent
=================================
Splits extraction into focused passes for higher accuracy with free-tier models.

Architecture:
  Pass 1: Section A — Company details (simple factual fields)
  Pass 2: Section B — Governance & policy fields
  Pass 3: Section C, Principles 1-3 (Ethics, Products, Employees)
  Pass 4: Section C, Principles 4-6 (Stakeholders, Human Rights, Environment)
  Pass 5: Section C, Principles 7-9 (Advocacy, CSR, Consumer)
  Pass 6: Validation & gap-fill (re-extract any fields that were missed)

Uses Groq (Llama 3.3 70B) free tier — 30 RPM, 128K context.
Falls back to Bedrock Llama 3 70B if Groq fails.
"""

import json
import re
import asyncio
import time
from typing import Any
from groq import Groq
import boto3


# ──────────────────────────────────────────────────────────────────
# Per-pass focused prompts (much higher hit rate than one giant prompt)
# ──────────────────────────────────────────────────────────────────

PASS_SECTION_A = """Extract ONLY Section A (General Disclosures) from this BRSR/Annual Report text.

Return a JSON object with EXACTLY these fields (omit if not found):
{
  "company_name": "Full legal name of the entity",
  "cin": "Corporate Identity Number (L/U...)",
  "year_of_incorporation": "YYYY",
  "registered_office": "Full address",
  "corporate_office": "Full address if different",
  "email": "Contact email",
  "telephone": "Phone number",
  "website": "Company website URL",
  "financial_year": "e.g. 2023-24 or FY2024",
  "stock_exchange": "BSE/NSE",
  "paid_up_capital": "Amount in Cr/Lakhs",
  "turnover": "Revenue/Turnover in Cr",
  "net_worth": "Net worth in Cr",
  "employees_permanent_male": "Number",
  "employees_permanent_female": "Number",
  "employees_permanent_total": "Number",
  "employees_contract_male": "Number",
  "employees_contract_female": "Number",
  "employees_contract_total": "Number",
  "women_employees_pct": "Percentage",
  "differently_abled_employees": "Number",
  "workers_permanent_total": "Number",
  "workers_contract_total": "Number",
  "num_plants_national": "Number",
  "num_plants_international": "Number",
  "num_offices_national": "Number",
  "num_offices_international": "Number",
  "markets_states_uts": "Number of states/UTs served",
  "markets_countries": "Number of countries",
  "exports_pct_of_turnover": "Percentage",
  "reporting_boundary": "Standalone or Consolidated",
  "subsidiaries_count": "Number",
  "csr_applicable": "Yes/No",
  "csr_turnover_threshold": "Amount"
}

Look for tables titled "Details of the listed entity", "Products/Services", "Operations", "Employees", "Holding/Subsidiary".

Return ONLY valid JSON, no explanation.

TEXT:
{text}"""

PASS_SECTION_B = """Extract ONLY Section B (Management & Process Disclosures) from this BRSR/Annual Report text.

Return a JSON object with EXACTLY these fields (omit if not found):
{
  "policy_p1_ethics": "Yes/No - whether policy exists",
  "policy_p2_product": "Yes/No",
  "policy_p3_wellbeing": "Yes/No",
  "policy_p4_stakeholder": "Yes/No",
  "policy_p5_human_rights": "Yes/No",
  "policy_p6_environment": "Yes/No",
  "policy_p7_advocacy": "Yes/No",
  "policy_p8_inclusive": "Yes/No",
  "policy_p9_consumer": "Yes/No",
  "policies_approved_by_board": "Yes/No/Partial",
  "policies_conform_to_national_guidelines": "Yes/No",
  "policies_extended_to_value_chain": "Yes/No",
  "committee_of_board_for_esg": "Yes/No",
  "esg_committee_details": "Name, composition details",
  "compliance_violations_fines": "Amount or None",
  "complaints_sexual_harassment_filed": "Number",
  "complaints_sexual_harassment_resolved": "Number",
  "complaints_discrimination_filed": "Number",
  "complaints_child_labour_filed": "Number",
  "complaints_forced_labour_filed": "Number",
  "complaints_wages_filed": "Number",
  "grievance_redressal_mechanism": "Yes/No",
  "stakeholder_grievances_filed": "Number",
  "stakeholder_grievances_resolved": "Number",
  "directors_with_esg_training": "Number or percentage"
}

Look for sections titled "Policy and management processes", "Governance", "Disclosures", POSH complaints tables.

Return ONLY valid JSON, no explanation.

TEXT:
{text}"""

PASS_SECTION_C_P123 = """Extract ONLY Section C Principles 1, 2, and 3 from this BRSR/Annual Report text.

**Principle 1 (Ethics, Transparency & Accountability)**:
{
  "code_of_conduct_for_all": "Yes/No",
  "anti_corruption_policy": "Yes/No",
  "whistle_blower_policy": "Yes/No",
  "ethics_complaints_current_fy": "Number",
  "ethics_complaints_previous_fy": "Number",
  "conflicts_of_interest_cases": "Number",
  "disciplinary_actions_corruption": "Number",
  "anti_competitive_cases": "Number"
}

**Principle 2 (Sustainable & Safe Products/Services)**:
{
  "r_and_d_spend": "Amount in Cr or % of revenue",
  "r_and_d_capex_pct": "Percentage of total capex",
  "sustainable_sourcing_pct": "Percentage",
  "recycled_input_pct": "Percentage of inputs from recycled sources",
  "products_with_epr": "Number or percentage",
  "products_recyclable_pct": "Percentage",
  "products_reusable_pct": "Percentage",
  "lis_certification": "Yes/No - Life Cycle Assessment",
  "environmental_social_risks_assessed": "Yes/No"
}

**Principle 3 (Employee Wellbeing)**:
{
  "employee_turnover_rate": "Percentage",
  "worker_turnover_rate": "Percentage",
  "median_salary_male": "Amount",
  "median_salary_female": "Amount",
  "gross_wages_female_pct": "Percentage",
  "safety_incidents_ltifr": "Rate",
  "safety_fatalities": "Number",
  "training_hours_per_employee": "Hours",
  "training_hours_per_worker": "Hours",
  "health_insurance_coverage_pct": "Percentage",
  "maternity_benefits_pct": "Percentage of eligible",
  "paternity_benefits_pct": "Percentage",
  "disability_benefits": "Yes/No",
  "return_to_work_retention_rate": "Percentage",
  "employees_in_union_pct": "Percentage",
  "minimum_wages_paid": "Yes/No - compliance"
}

Return ONLY a single valid JSON object combining all three principles like:
{"principle_1": {...}, "principle_2": {...}, "principle_3": {...}}

No explanation. Return ONLY JSON.

TEXT:
{text}"""

PASS_SECTION_C_P456 = """Extract ONLY Section C Principles 4, 5, and 6 from this BRSR/Annual Report text.

**Principle 4 (Stakeholder Engagement)**:
{
  "stakeholder_groups_identified": "List: Investors, Employees, Community, etc.",
  "stakeholder_engagement_frequency": "Quarterly/Annual/Regular",
  "vulnerable_groups_identified": "Yes/No",
  "special_initiatives_vulnerable": "Description"
}

**Principle 5 (Human Rights)**:
{
  "human_rights_training_employees_pct": "Percentage trained",
  "human_rights_training_workers_pct": "Percentage trained",
  "minimum_wage_compliance": "Yes/No",
  "child_labor_complaints": "Number",
  "forced_labor_complaints": "Number",
  "wages_complaints": "Number",
  "human_rights_due_diligence": "Yes/No",
  "remediation_mechanisms": "Yes/No"
}

**Principle 6 (Environment)**:
{
  "energy_consumption_total_gj": "GigaJoules total",
  "energy_from_renewable_gj": "GigaJoules from renewable",
  "renewable_energy_pct": "Percentage",
  "energy_intensity_per_rupee": "GJ per Cr turnover",
  "pat_scheme_participation": "Yes/No",
  "water_withdrawal_kl": "KiloLitres total",
  "water_recycled_kl": "KiloLitres",
  "water_recycled_pct": "Percentage",
  "zero_liquid_discharge": "Yes/No",
  "ghg_scope1_tco2e": "Tonnes CO2e - direct emissions",
  "ghg_scope2_tco2e": "Tonnes CO2e - indirect (electricity)",
  "ghg_scope3_tco2e": "Tonnes CO2e - value chain (if disclosed)",
  "ghg_intensity_per_rupee": "tCO2e per Cr turnover",
  "waste_generated_mt": "Metric Tonnes total",
  "waste_recycled_mt": "Metric Tonnes recycled",
  "waste_recycled_pct": "Percentage",
  "hazardous_waste_mt": "Metric Tonnes",
  "single_use_plastic_reduced": "Yes/No",
  "biodiversity_impact_assessed": "Yes/No",
  "air_emissions_nox": "Amount",
  "air_emissions_sox": "Amount",
  "air_emissions_pm": "Amount",
  "environmental_compliance_violations": "Number"
}

Return ONLY a single valid JSON object:
{"principle_4": {...}, "principle_5": {...}, "principle_6": {...}}

No explanation. Return ONLY JSON.

TEXT:
{text}"""

PASS_SECTION_C_P789 = """Extract ONLY Section C Principles 7, 8, and 9 from this BRSR/Annual Report text.

**Principle 7 (Policy Advocacy)**:
{
  "trade_associations_member": "List of associations",
  "advocacy_on_public_policy": "Yes/No",
  "anti_competitive_conduct_cases": "Number",
  "public_policy_positions": "Description if any"
}

**Principle 8 (Inclusive Growth & Equitable Development)**:
{
  "csr_spend_current_fy": "Amount in Cr",
  "csr_spend_previous_fy": "Amount in Cr",
  "csr_obligation": "Amount in Cr (2% of avg net profit)",
  "community_beneficiaries": "Number of people benefited",
  "local_procurement_pct": "Percentage from local/small suppliers",
  "input_from_msme_pct": "Percentage from MSMEs",
  "input_from_small_producers_pct": "Percentage",
  "csr_projects_count": "Number of projects",
  "social_impact_assessments": "Yes/No",
  "rehabilitation_resettlement": "Yes/No or Number affected"
}

**Principle 9 (Consumer Value)**:
{
  "consumer_complaints_current_fy": "Number received",
  "consumer_complaints_resolved_pct": "Percentage resolved",
  "consumer_complaints_pending": "Number",
  "product_recalls": "Number of recalls",
  "data_privacy_complaints": "Number",
  "data_breaches": "Number",
  "cyber_security_policy": "Yes/No",
  "advertising_complaints": "Number",
  "product_quality_certifications": "ISO etc.",
  "customer_satisfaction_survey": "Yes/No or Score"
}

Return ONLY a single valid JSON object:
{"principle_7": {...}, "principle_8": {...}, "principle_9": {...}}

No explanation. Return ONLY JSON.

TEXT:
{text}"""


# ──────────────────────────────────────────────────────────────────
# Agent core
# ──────────────────────────────────────────────────────────────────

class BRSRExtractionAgent:
    """Multi-pass extraction agent using focused prompts for high accuracy."""

    def __init__(self, groq_key: str = "", bedrock_region: str = "ap-south-1"):
        self.groq_key = groq_key
        self.bedrock_region = bedrock_region
        self._groq_client = Groq(api_key=groq_key) if groq_key else None
        self._call_count = 0
        self._last_call_time = 0.0

    async def _call_llm(self, prompt: str, text: str, max_chars: int = 100000) -> dict[str, Any]:
        """Call LLM with rate limiting. Tries Groq first, falls back to Bedrock."""
        # Truncate text for context window
        if len(text) > max_chars:
            text = text[:max_chars]

        formatted_prompt = prompt.replace("{text}", text)

        # Rate limit: max 25 RPM for Groq free tier (leave margin)
        self._call_count += 1
        elapsed = time.time() - self._last_call_time
        if elapsed < 2.5:  # At least 2.5s between calls
            await asyncio.sleep(2.5 - elapsed)
        self._last_call_time = time.time()

        # Try Groq first
        if self._groq_client:
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._groq_client.chat.completions.create,
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "You are a BRSR compliance data extractor. Return ONLY valid JSON. Never include explanations, markdown, or code blocks."},
                            {"role": "user", "content": formatted_prompt},
                        ],
                        temperature=0.05,
                        max_tokens=4096,
                        response_format={"type": "json_object"},
                    ),
                    timeout=30.0,
                )
                result = _parse_json(response.choices[0].message.content or "")
                if result:
                    return result
            except Exception as e:
                print(f"  Agent: Groq call {self._call_count} failed: {e}")

        # Fallback to Bedrock Llama
        try:
            client = boto3.client("bedrock-runtime", region_name=self.bedrock_region)
            llama_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nYou are a BRSR data extractor. Return ONLY valid JSON.<|eot_id|><|start_header_id|>user<|end_header_id|>\n{formatted_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"

            body = json.dumps({"prompt": llama_prompt[:120000], "max_gen_len": 4096, "temperature": 0.05})
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.invoke_model,
                    modelId="meta.llama3-70b-instruct-v1:0",
                    contentType="application/json",
                    accept="application/json",
                    body=body,
                ),
                timeout=45.0,
            )
            response_body = json.loads(response["body"].read())
            result = _parse_json(response_body.get("generation", ""))
            if result:
                return result
        except Exception as e:
            print(f"  Agent: Bedrock fallback failed: {e}")

        return {}

    async def extract(self, text: str) -> dict[str, Any]:
        """Run full multi-pass extraction pipeline."""
        print("Agent: Starting multi-pass BRSR extraction...")

        # Run passes (sequential to respect rate limits)
        print("  Pass 1/5: Section A (Company Details)")
        section_a = await self._call_llm(PASS_SECTION_A, text, max_chars=80000)

        print("  Pass 2/5: Section B (Governance & Policy)")
        section_b = await self._call_llm(PASS_SECTION_B, text, max_chars=80000)

        print("  Pass 3/5: Section C - Principles 1,2,3")
        p123 = await self._call_llm(PASS_SECTION_C_P123, text, max_chars=100000)

        print("  Pass 4/5: Section C - Principles 4,5,6")
        p456 = await self._call_llm(PASS_SECTION_C_P456, text, max_chars=100000)

        print("  Pass 5/5: Section C - Principles 7,8,9")
        p789 = await self._call_llm(PASS_SECTION_C_P789, text, max_chars=100000)

        # Merge Section C from all principle passes
        section_c = {}
        for principles in [p123, p456, p789]:
            for key, val in principles.items():
                if isinstance(val, dict):
                    section_c.update(val)
                else:
                    section_c[key] = val

        # Flatten any nested principle dicts into section_c
        merged = {
            "section_a": section_a,
            "section_b": section_b,
            "section_c": section_c,
        }

        total_fields = sum(len(v) for v in merged.values() if isinstance(v, dict))
        print(f"Agent: Extraction complete — {total_fields} fields extracted across all sections")

        return merged


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict[str, Any]:
    """Robust JSON parser that handles markdown code blocks and partial JSON."""
    if not text:
        return {}

    # Strip markdown code blocks
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    return {}


async def extract_with_agent(text: str, groq_key: str = "") -> dict[str, Any]:
    """Main entry point: run multi-pass extraction agent."""
    agent = BRSRExtractionAgent(groq_key=groq_key)
    return await agent.extract(text)
