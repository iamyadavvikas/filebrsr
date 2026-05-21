from anthropic import Anthropic
from google import genai
from groq import Groq
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


def _parse_ai_response(response_text: str) -> dict[str, Any]:
    """Parse JSON from AI response text."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"section_a": {}, "section_b": {}, "section_c": {}}


async def _extract_with_claude(text: str, api_key: str) -> dict[str, Any]:
    """Extract using Anthropic Claude."""
    client = Anthropic(api_key=api_key)

    # Claude context is 200K tokens (~800K chars)
    max_chars = 600000
    if len(text) > max_chars:
        text = text[:max_chars]

    response = await asyncio.wait_for(
        asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": BRSR_EXTRACTION_PROMPT.format(text=text)},
            ],
            temperature=0.1,
        ),
        timeout=30.0,
    )
    return _parse_ai_response(response.content[0].text)


async def _extract_with_gemini(text: str, api_key: str) -> dict[str, Any]:
    """Extract using Google Gemini."""
    client = genai.Client(api_key=api_key)

    max_chars = 900000
    if len(text) > max_chars:
        text = text[:max_chars]

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
        timeout=30.0,
    )
    return _parse_ai_response(response.text)


async def _extract_with_groq(text: str, api_key: str) -> dict[str, Any]:
    """Extract using Groq (Llama 3.3 70B)."""
    client = Groq(api_key=api_key)

    # Groq context window is 128K tokens (~500K chars)
    max_chars = 120000
    if len(text) > max_chars:
        text = text[:max_chars]

    response = await asyncio.wait_for(
        asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You extract structured data from documents. Return ONLY valid JSON."},
                {"role": "user", "content": BRSR_EXTRACTION_PROMPT.format(text=text)},
            ],
            temperature=0.1,
            max_tokens=4096,
        ),
        timeout=30.0,
    )
    return _parse_ai_response(response.choices[0].message.content or "")


async def extract_with_ai(text: str, gemini_key: str, groq_key: str = "", anthropic_key: str = "") -> dict[str, Any]:
    """Extract BRSR metrics using AI. Chain: Claude → Gemini → Groq → regex."""
    # Try Claude first (best quality)
    if anthropic_key:
        try:
            result = await _extract_with_claude(text, anthropic_key)
            if any(result.get(s) for s in ["section_a", "section_b", "section_c"]):
                print("AI extraction: Claude succeeded")
                return result
        except Exception as e:
            print(f"Claude failed: {e}")

    # Fallback to Gemini
    if gemini_key and gemini_key != "your_gemini_api_key":
        try:
            result = await _extract_with_gemini(text, gemini_key)
            if any(result.get(s) for s in ["section_a", "section_b", "section_c"]):
                print("AI extraction: Gemini succeeded")
                return result
        except Exception as e:
            print(f"Gemini failed: {e}")

    # Fallback to Groq
    if groq_key:
        try:
            result = await _extract_with_groq(text, groq_key)
            if any(result.get(s) for s in ["section_a", "section_b", "section_c"]):
                print("AI extraction: Groq succeeded")
                return result
        except Exception as e:
            print(f"Groq failed: {e}")

    print("AI extraction: all providers failed, using regex only")
    return {"section_a": {}, "section_b": {}, "section_c": {}}
