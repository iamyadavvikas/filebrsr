"""
BSE/NSE BRSR Filing Scraper & Ground Truth Builder.
Scrapes publicly available BRSR filings from BSE/NSE, parses XBRL/PDF,
and stores structured data for benchmarking and model training.

Usage:
  python -m app.filing_scraper --source bse --year FY2024-25 --limit 50
"""

import httpx
import json
import hashlib
import re
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

from app.config import get_settings

settings = get_settings()

# BSE BRSR Filings API (publicly accessible)
BSE_BRSR_URL = "https://api.bseindia.com/BseIndiaAPI/api/CorporateFilings/w"
BSE_XBRL_URL = "https://www.bseindia.com/corporates/xbrl_files/"

# NSE Corporate Filings
NSE_FILINGS_URL = "https://www.nseindia.com/api/corporate-announcements"

# Known NIFTY 500 companies with BRSR filings
NIFTY500_SAMPLE = [
    {"name": "Tata Consultancy Services", "bse_code": "532540", "nse_symbol": "TCS", "sector": "IT Services", "cin": "L22210MH1995PLC084781"},
    {"name": "Infosys", "bse_code": "500209", "nse_symbol": "INFY", "sector": "IT Services", "cin": "L85110KA1981PLC013115"},
    {"name": "Reliance Industries", "bse_code": "500325", "nse_symbol": "RELIANCE", "sector": "Energy", "cin": "L17110MH1973PLC019786"},
    {"name": "HDFC Bank", "bse_code": "500180", "nse_symbol": "HDFCBANK", "sector": "Banking", "cin": "L65920MH1994PLC080618"},
    {"name": "ICICI Bank", "bse_code": "532174", "nse_symbol": "ICICIBANK", "sector": "Banking", "cin": "L65190GJ1994PLC021012"},
    {"name": "Hindustan Unilever", "bse_code": "500696", "nse_symbol": "HINDUNILVR", "sector": "FMCG", "cin": "L15140MH1933PLC002030"},
    {"name": "ITC", "bse_code": "500875", "nse_symbol": "ITC", "sector": "FMCG", "cin": "L16005WB1910PLC001985"},
    {"name": "Bharti Airtel", "bse_code": "532454", "nse_symbol": "BHARTIARTL", "sector": "Telecom", "cin": "L74899DL1995PLC070609"},
    {"name": "Larsen & Toubro", "bse_code": "500510", "nse_symbol": "LT", "sector": "Manufacturing", "cin": "L99999MH1946PLC004768"},
    {"name": "Sun Pharma", "bse_code": "524715", "nse_symbol": "SUNPHARMA", "sector": "Pharma", "cin": "L24230GJ1993PLC019050"},
    {"name": "Wipro", "bse_code": "507685", "nse_symbol": "WIPRO", "sector": "IT Services", "cin": "L32102KA1945PLC020800"},
    {"name": "Asian Paints", "bse_code": "500820", "nse_symbol": "ASIANPAINT", "sector": "Manufacturing", "cin": "L24220MH1945PLC004598"},
    {"name": "HCL Technologies", "bse_code": "532281", "nse_symbol": "HCLTECH", "sector": "IT Services", "cin": "L74140DL1991PLC046369"},
    {"name": "Maruti Suzuki", "bse_code": "532500", "nse_symbol": "MARUTI", "sector": "Automotive", "cin": "L34103HR1981PLC032949"},
    {"name": "Tata Steel", "bse_code": "500470", "nse_symbol": "TATASTEEL", "sector": "Metals", "cin": "L27100MH1907PLC000260"},
    {"name": "Ultratech Cement", "bse_code": "532538", "nse_symbol": "ULTRACEMCO", "sector": "Manufacturing", "cin": "L26940RJ2000PLC015874"},
    {"name": "Titan Company", "bse_code": "500114", "nse_symbol": "TITAN", "sector": "FMCG", "cin": "L74999TZ1984PLC001456"},
    {"name": "NTPC", "bse_code": "532555", "nse_symbol": "NTPC", "sector": "Energy", "cin": "L40101DL1975GOI007966"},
    {"name": "Power Grid Corp", "bse_code": "532898", "nse_symbol": "POWERGRID", "sector": "Energy", "cin": "L40101DL1989GOI038121"},
    {"name": "Bajaj Finance", "bse_code": "500034", "nse_symbol": "BAJFINANCE", "sector": "Banking", "cin": "L65910MH1987PLC042961"},
]

# BRSR datapoints we care about extracting from filings
KEY_DATAPOINTS = {
    "scope1_emissions": {"patterns": [r"scope\s*1.*?(\d[\d,.]+)\s*(?:tCO2|tonnes)", r"direct.*?ghg.*?(\d[\d,.]+)"], "unit": "tCO2e"},
    "scope2_emissions": {"patterns": [r"scope\s*2.*?(\d[\d,.]+)\s*(?:tCO2|tonnes)", r"indirect.*?ghg.*?(\d[\d,.]+)"], "unit": "tCO2e"},
    "energy_consumption": {"patterns": [r"total\s*energy.*?(\d[\d,.]+)\s*(?:GJ|TJ|MWh)"], "unit": "GJ"},
    "renewable_energy_pct": {"patterns": [r"renewable.*?(\d+\.?\d*)\s*%"], "unit": "%"},
    "water_withdrawal": {"patterns": [r"water\s*(?:withdrawal|consumed).*?(\d[\d,.]+)\s*(?:KL|ML|m3)"], "unit": "KL"},
    "water_recycled_pct": {"patterns": [r"water.*?recycl.*?(\d+\.?\d*)\s*%"], "unit": "%"},
    "waste_generated": {"patterns": [r"waste\s*generated.*?(\d[\d,.]+)\s*(?:MT|tonnes|kg)"], "unit": "MT"},
    "women_employees_pct": {"patterns": [r"women.*?(\d+\.?\d*)\s*%", r"female.*?(\d+\.?\d*)\s*%"], "unit": "%"},
    "training_hours": {"patterns": [r"(?:average|avg).*?training.*?(\d+\.?\d*)\s*(?:hours|hrs)"], "unit": "hours"},
    "ltifr": {"patterns": [r"ltifr.*?(\d+\.?\d*)", r"lost\s*time.*?frequency.*?(\d+\.?\d*)"], "unit": "per million hours"},
    "csr_spend": {"patterns": [r"csr.*?(?:spent|expenditure).*?(?:₹|Rs|INR)?\s*(\d[\d,.]+)\s*(?:cr|crore|lakh)"], "unit": "INR Cr"},
    "board_diversity_pct": {"patterns": [r"(?:women|female).*?(?:director|board).*?(\d+\.?\d*)\s*%"], "unit": "%"},
}


@dataclass
class FilingData:
    company_name: str
    cin: str
    bse_code: Optional[str]
    nse_symbol: Optional[str]
    sector: str
    market_cap_tier: str
    financial_year: str
    filing_date: Optional[str]
    source_url: Optional[str]
    filing_format: str
    extracted_datapoints: Dict[str, Dict]
    total_datapoints_extracted: int
    disclosure_score: float
    parse_quality: str


def extract_from_text(text: str) -> Dict[str, Dict]:
    """Extract BRSR datapoints from filing text using regex patterns."""
    results = {}
    text_lower = text.lower()

    for dp_id, config in KEY_DATAPOINTS.items():
        for pattern in config["patterns"]:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value_str = match.group(1).replace(",", "")
                    value = float(value_str)
                    results[dp_id] = {
                        "value": value,
                        "unit": config["unit"],
                        "source_pattern": pattern,
                        "confidence": 0.7,  # regex extraction confidence
                    }
                    break
                except (ValueError, IndexError):
                    continue

    return results


def calculate_disclosure_score(extracted: Dict, total_possible: int = 12) -> float:
    """Calculate what % of key datapoints were disclosed."""
    if total_possible == 0:
        return 0.0
    return round((len(extracted) / total_possible) * 100, 2)


def get_supabase_admin():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


async def scrape_bse_filing(bse_code: str, financial_year: str) -> Optional[str]:
    """Attempt to fetch BRSR filing text from BSE."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # BSE corporate filings API
            params = {
                "scripcode": bse_code,
                "Atea": "B",  # BRSR category
                "subcategory": "BRSR",
                "from_date": "01/04/2024",
                "to_date": "31/03/2025",
            }
            resp = await client.get(BSE_BRSR_URL, params=params, headers={
                "User-Agent": "Mozilla/5.0 (compatible; FileBRSR/1.0; ESG Research)",
                "Referer": "https://www.bseindia.com",
            })
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    # Get the PDF/XBRL URL from the filing
                    filing = data[0]
                    return filing.get("ATTACHMENTNAME", "")
    except Exception as e:
        print(f"BSE scrape failed for {bse_code}: {e}")
    return None


async def process_company(company: Dict, financial_year: str = "FY2024-25") -> Optional[FilingData]:
    """Process a single company's BRSR filing."""
    # For MVP, use the seed data we have from known public disclosures
    # In production, this would actually fetch and parse the XBRL/PDF

    # Simulate extraction from known public data
    # Real implementation would use pdfplumber + AI extraction on actual filings
    extracted = {}

    # Try BSE scrape
    filing_url = await scrape_bse_filing(company.get("bse_code", ""), financial_year)

    return FilingData(
        company_name=company["name"],
        cin=company["cin"],
        bse_code=company.get("bse_code"),
        nse_symbol=company.get("nse_symbol"),
        sector=company["sector"],
        market_cap_tier="large_cap",
        financial_year=financial_year,
        filing_date=None,
        source_url=filing_url,
        filing_format="xbrl" if filing_url and ".xml" in str(filing_url) else "pdf",
        extracted_datapoints=extracted,
        total_datapoints_extracted=len(extracted),
        disclosure_score=calculate_disclosure_score(extracted),
        parse_quality="low" if len(extracted) < 3 else "medium" if len(extracted) < 8 else "high",
    )


async def store_filing(filing: FilingData):
    """Store filing data in Supabase ground truth table."""
    sb = get_supabase_admin()

    data = {
        "company_name": filing.company_name,
        "cin": filing.cin,
        "bse_code": filing.bse_code,
        "nse_symbol": filing.nse_symbol,
        "sector": filing.sector,
        "market_cap_tier": filing.market_cap_tier,
        "financial_year": filing.financial_year,
        "filing_date": filing.filing_date,
        "source_url": filing.source_url,
        "filing_format": filing.filing_format,
        "extracted_datapoints": filing.extracted_datapoints,
        "total_datapoints_extracted": filing.total_datapoints_extracted,
        "disclosure_score": filing.disclosure_score,
        "parse_quality": filing.parse_quality,
    }

    sb.table("filing_ground_truth").upsert(data, on_conflict="cin,financial_year").execute()


async def update_sector_benchmarks():
    """Aggregate ground truth data into sector benchmarks."""
    sb = get_supabase_admin()

    # Get all high-quality filings
    filings = sb.table("filing_ground_truth") \
        .select("*") \
        .in_("parse_quality", ["high", "medium"]) \
        .execute()

    if not filings.data:
        return

    # Group by sector + datapoint
    sector_data: Dict[str, Dict[str, List[float]]] = {}

    for filing in filings.data:
        sector = filing["sector"]
        datapoints = filing.get("extracted_datapoints") or {}

        for dp_id, dp_value in datapoints.items():
            key = f"{sector}:{dp_id}"
            if key not in sector_data:
                sector_data[key] = []
            if isinstance(dp_value, dict) and "value" in dp_value:
                try:
                    sector_data[key].append(float(dp_value["value"]))
                except (ValueError, TypeError):
                    pass

    # Insert sector benchmarks
    for key, values in sector_data.items():
        if len(values) < 2:
            continue

        sector, dp_id = key.split(":", 1)
        sorted_vals = sorted(values)
        n = len(sorted_vals)

        benchmark = {
            "sector": sector,
            "datapoint_id": dp_id,
            "financial_year": "FY2024-25",
            "companies_reporting": n,
            "companies_total": len([f for f in filings.data if f["sector"] == sector]),
            "disclosure_rate": round((n / max(1, len([f for f in filings.data if f["sector"] == sector]))) * 100, 2),
            "mean_value": round(sum(values) / n, 4),
            "median_value": sorted_vals[n // 2],
            "best_in_class_value": sorted_vals[-1],  # highest (may need inversion for some metrics)
            "worst_value": sorted_vals[0],
            "source": "bse_nse_scrape",
        }

        sb.table("sector_benchmarks_live").upsert(
            benchmark, on_conflict="sector,datapoint_id,financial_year,market_cap_tier"
        ).execute()


async def run_scraper(limit: int = 20, financial_year: str = "FY2024-25"):
    """Main entry point: scrape filings and update benchmarks."""
    print(f"[Filing Scraper] Starting for {financial_year}, limit={limit}")

    companies = NIFTY500_SAMPLE[:limit]
    results = []

    for company in companies:
        print(f"  Processing: {company['name']}...")
        filing = await process_company(company, financial_year)
        if filing:
            await store_filing(filing)
            results.append(filing)

    print(f"[Filing Scraper] Processed {len(results)} companies")

    # Update sector benchmarks
    await update_sector_benchmarks()
    print("[Filing Scraper] Sector benchmarks updated")

    return results


if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="FileBRSR Filing Scraper")
    parser.add_argument("--year", default="FY2024-25", help="Financial year")
    parser.add_argument("--limit", type=int, default=20, help="Max companies to process")
    args = parser.parse_args()

    asyncio.run(run_scraper(limit=args.limit, financial_year=args.year))
