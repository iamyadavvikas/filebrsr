"""Utility-bill connector: bill text -> metered activity -> Scope 2.

Takes OCR/plain text of an electricity bill (Indian DISCOM layouts first)
and extracts the metered consumption + billing period, then prices it
through the versioned CEA grid factor via :func:`scope2_location_based`
— never a hardcoded factor. Image/PDF OCR itself stays in ``app.ocr``
(pass its text output here); this module owns the energy-domain parsing.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

KWH_PATTERNS = [
    # "Total Consumption : 245 kWh", "Units Consumed - 1,234.5 Units"
    re.compile(r"(?:total\s+consumption|units?\s+consumed|consumption|current\s+consumption)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(kwh|units?)", re.I),
    re.compile(r"([\d,]+(?:\.\d+)?)\s*kwh\s*(?:consumed|consumption|billed)?", re.I),
]

# "01-Jan-2025 to 31-Jan-2025", "01/01/2025 - 31/01/2025", "Period: Jan 2025"
PERIOD_PATTERNS = [
    re.compile(
        r"(\d{1,2}[-/]\w{3,9}[-/]\d{2,4})\s*(?:to|-|–|—)\s*(\d{1,2}[-/]\w{3,9}[-/]\d{2,4})",
        re.I,
    ),
    re.compile(
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*(?:to|-|–|—)\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
    ),
]

METER_PATTERNS = [
    re.compile(r"meter\s*(?:no|number|id)\s*[:\-]?\s*([A-Z0-9\-/]+)", re.I),
    re.compile(r"consumer\s*(?:no|number|id)\s*[:\-]?\s*([A-Z0-9\-/]+)", re.I),
]

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_date(raw: str) -> str | None:
    raw = raw.strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%y", "%d/%m/%y"):
        try:
            from datetime import datetime

            dt = datetime.strptime(raw[: len(fmt) + 4], fmt)
            if dt.year < 100:
                dt = dt.replace(year=2000 + dt.year)
            return dt.date().isoformat()
        except ValueError:
            continue
    m = re.match(r"(\d{1,2})[-/](\w{3,9})[-/](\d{2,4})$", raw)
    if m:
        day, mon, yr = int(m.group(1)), _MONTHS.get(m.group(2)[:3].lower()), int(m.group(3))
        if mon:
            if yr < 100:
                yr += 2000
            return date(yr, mon, day).isoformat()
    return None


def parse_bill_text(text: str) -> dict[str, Any]:
    """Extract metered consumption + billing period from bill text.

    Returns {kwh, unit, period_start, period_end, meter_no, confidence,
    notes}. ``confidence`` is high/medium/low based on which signals fired;
    ``kwh`` is None when nothing parseable was found (caller decides).
    """
    text = text or ""
    kwh: float | None = None
    for pat in KWH_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                kwh = float(m.group(1).replace(",", ""))
                break
            except ValueError:
                continue
    period_start = period_end = None
    for pat in PERIOD_PATTERNS:
        m = pat.search(text)
        if m:
            period_start = _parse_date(m.group(1))
            period_end = _parse_date(m.group(2))
            if period_start and period_end:
                break
            period_start = period_end = None
    meter_no = None
    for pat in METER_PATTERNS:
        m = pat.search(text)
        if m:
            meter_no = m.group(1).strip()
            break
    signals = sum(x is not None for x in (kwh, period_start, meter_no))
    confidence = "high" if signals >= 2 and kwh is not None else "medium" if kwh is not None else "low"
    notes = []
    if kwh is None:
        notes.append("No consumption figure matched; check scan quality or layout.")
    if period_start is None:
        notes.append("No billing period matched; period left open.")
    return {
        "kwh": kwh,
        "unit": "kWh" if kwh is not None else None,
        "period_start": period_start,
        "period_end": period_end,
        "meter_no": meter_no,
        "confidence": confidence,
        "notes": notes,
    }


def bill_to_scope2(
    parsed: dict[str, Any],
    *,
    jurisdiction: str = "IN",
    grid_region: str | None = None,
) -> dict[str, Any]:
    """Price parsed consumption through the versioned grid factor.

    Raises ValueError when no kWh was parsed.
    """
    if parsed.get("kwh") is None:
        raise ValueError("bill text yielded no kWh figure — nothing to price")
    from app.calculator import scope2_location_based

    period = None
    if parsed.get("period_start") and parsed.get("period_end"):
        period = (parsed["period_start"], parsed["period_end"])
    result = scope2_location_based(
        parsed["kwh"],
        jurisdiction=jurisdiction,
        grid_region=grid_region,
        reporting_period=period,
    )
    return {
        "kwh": parsed["kwh"],
        "period": period,
        "meter_no": parsed.get("meter_no"),
        "parse_confidence": parsed.get("confidence"),
        "emissions_tco2e": float(result.value),
        "factor": {
            "id": result.factor_id,
            "version": result.factor_version,
            "source": result.factor_source,
            "citation": result.factor_citation,
        },
    }
