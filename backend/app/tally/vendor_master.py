"""
Vendor-master derivation utilities (Tally Slice 5).

Today: derive the 2-digit Indian state code from a vendor GSTIN.

Indian GSTIN format is 15 characters::

    [2-digit state code][10-char PAN][1-char entity][1-char Z][1-char check]

We persist the leading 2 digits on every ``raw_records`` row so the
BRSR Principle-6 cut "intra-state vs inter-state procurement spend"
becomes a SUM/GROUP BY query, not a Python-side post-processing step.

A future slice will read the ``<LEDGER>`` master nodes that some Tally
exports include alongside vouchers, to enrich vendor metadata (legal
name, MSME registration, payment terms). For now we only need the
state code derived from the GSTIN that's already on the voucher.
"""

from __future__ import annotations

import re

# Map of state code → state name. Used for human-friendly reporting.
# Source: GST Council notification, official state code list.
INDIAN_STATE_CODES: dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman and Diu",          # merged into 26 UT in 2020 but old data persists
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "28": "Andhra Pradesh (old)",   # split in 2014; new AP is 37
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",        # SEZ / oil exploration zones
    "99": "Other Country",          # foreign vendor with Indian temp GSTIN
}

# Valid GSTIN: 2 digits, 5 letters, 4 digits, 1 letter, 1 digit/letter,
# 1 letter (default "Z"), 1 digit/letter (check). We use a permissive
# regex — the state-code derivation only needs the first 2 chars to be
# a recognised numeric code.
_GSTIN_PATTERN = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][A-Z][0-9A-Z]$",
    re.IGNORECASE,
)


def gstin_to_state_code(gstin: str | None) -> str | None:
    """Return the 2-digit state code from a GSTIN, or ``None`` when the
    input isn't a recognisable GSTIN or the prefix isn't a known state.

    Permissive on whitespace and case; the GST portal validators
    sometimes return GSTINs with a leading/trailing space in CSV
    exports."""
    if not gstin:
        return None
    cleaned = gstin.strip().upper()
    if not _GSTIN_PATTERN.match(cleaned):
        return None
    code = cleaned[:2]
    if code not in INDIAN_STATE_CODES:
        return None
    return code


def state_name_for(code: str | None) -> str | None:
    """Human-readable state name for a 2-digit code, or ``None``."""
    if not code:
        return None
    return INDIAN_STATE_CODES.get(code)


__all__ = [
    "INDIAN_STATE_CODES",
    "gstin_to_state_code",
    "state_name_for",
]
