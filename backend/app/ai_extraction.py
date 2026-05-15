from google import genai
import json
import re
import asyncio
from typing import Any


BRSR_EXTRACTION_PROMPT = """You are an expert at extracting BRSR (Business Responsibility and Sustainability Reporting) metrics from Indian listed company annual reports.

Extract ALL available metrics from the following text and return them as structured JSON with three sections:

1. **section_a** (General Disclosures): CIN, company_name, year_of_incorporation, registered_office, corporate_office, email, telephone, website, financial_year, stock_exchange, paid_up_capital, turnover, employees_permanent, employees_contract, women_employees_pct

2. **section_b** (Management & Process): policy_available, policy_approved_by_board, policy_web_link, grievance_mechanism

3. **section_c** (Principle-wise Performance):
   - Principle 1 (Ethics): code_of_conduct, anti_corruption_policy, complaints_ethics
   - Principle 2 (Products): r_and_d_spend, sustainable_sourcing_pct, recycled_input_pct
   - Principle 3 (Employee Wellbeing): employee_turnover_rate, safety_incidents, training_hours_per_employee, median_salary_male, median_salary_female
   - Principle 4 (Stakeholders): stakeholder_groups_identified
   - Principle 5 (Human Rights): human_rights_training_pct, child_labor_complaints
   - Principle 6 (Environment): energy_consumption_total, renewable_energy_pct, water_withdrawal, ghg_scope1, ghg_scope2, waste_generated, waste_recycled_pct
   - Principle 7 (Policy Advocacy): trade_associations
   - Principle 8 (Inclusive Growth): csr_spend, community_beneficiaries
   - Principle 9 (Consumer): consumer_complaints, data_privacy_complaints, product_recalls

Return ONLY valid JSON. If a metric is not found, omit it. Use the exact field names above.

TEXT:
{text}
"""


async def extract_with_ai(text: str, api_key: str) -> dict[str, Any]:
    """Extract BRSR metrics using Google Gemini."""
    if not api_key or api_key == "your_gemini_api_key":
        return {"section_a": {}, "section_b": {}, "section_c": {}}

    client = genai.Client(api_key=api_key)

    # Truncate text to fit within context window
    max_chars = 900000  # Gemini supports ~1M tokens
    if len(text) > max_chars:
        text = text[:max_chars]

    # Run with timeout to avoid hanging on rate limits
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=BRSR_EXTRACTION_PROMPT.format(text=text),
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            ),
            timeout=15.0,
        )

        response_text = response.text

        # Extract JSON from response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                return json.loads(json_match.group())
            return {"section_a": {}, "section_b": {}, "section_c": {}}

    except (asyncio.TimeoutError, Exception) as e:
        print(f"AI extraction skipped: {e}")
        return {"section_a": {}, "section_b": {}, "section_c": {}}
