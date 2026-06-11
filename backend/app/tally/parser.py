"""
Tally Prime / Tally ERP 9 voucher XML parser.

Parses the canonical ``<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>...``
structure that Tally emits from "Export" → "All Masters" / "Daybook" and
that the Tally HTTP-XML interface returns. The grammar is permissive
because Tally's serialiser is highly inconsistent across versions — case
varies (``VOUCHERNUMBER`` vs ``Vouchernumber``), tags appear in any order,
and the inventory-vs-ledger split is wholly optional on cash vouchers.

We deliberately do not validate against a schema: real-world Tally exports
break every schema we have tried. Instead the parser tolerates missing
fields and returns a list of :class:`TallyLineItem` records, one per
inventory/ledger line that carries a non-tax monetary amount. GST ledgers
(CGST/SGST/IGST/Cess detected by ledger name) are aggregated onto the
parent voucher's tax buckets, never returned as separate line items.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# Tally puts everything in upper-case but downstream consumers (and humans)
# expect mixed case. Match case-insensitively and normalise via a tiny helper.

# Ledger-name patterns that mark a tax line (not a real cost line).
# Order matters: check the long ones first so "IGST" doesn't swallow "CESS".
_TAX_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cgst", re.compile(r"\bcgst\b", re.IGNORECASE)),
    ("sgst", re.compile(r"\bsgst\b", re.IGNORECASE)),
    ("igst", re.compile(r"\bigst\b", re.IGNORECASE)),
    ("cess", re.compile(r"\bcess\b", re.IGNORECASE)),
)

# Lines that are not cost-of-goods but a pure balance-sheet movement
# (party ledger of a purchase voucher, bank ledger of a payment voucher).
# These are the credit/debit "PARTY" side of every voucher and must be
# excluded from the cost line items to avoid double-counting.
_PARTY_LEDGER_HINT = re.compile(
    r"\bbank\b|\bcash\b|\bsundry\s+creditors?\b|\bsundry\s+debtors?\b|"
    r"\bcredit(or)?s?\b|\bdebtors?\b",
    re.IGNORECASE,
)


# ─── Data classes ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TallyLineItem:
    """One cost-bearing line within a Tally voucher.

    Tax (CGST/SGST/IGST/Cess) is NOT a line item — it is aggregated on the
    parent voucher and carried on this record so downstream consumers can
    persist the GST split without re-walking the XML.
    """

    # Voucher-level fields (denormalised onto every line for cheap insertion)
    voucher_guid: str
    voucher_number: str | None
    voucher_type: str | None
    posting_date: date
    party_name: str | None
    party_gstin: str | None
    narration: str | None

    # Line-level fields
    ledger_name: str | None
    hsn_code: str | None
    description: str | None
    base_value: Decimal
    quantity: Decimal | None
    uom: str | None

    # Tax aggregated at the voucher level, then carried on every line so the
    # downstream INSERT path is line-orientated.
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    cess: Decimal

    # Full voucher dict for the raw_payload audit column.
    raw_payload: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def total_value(self) -> Decimal:
        return self.base_value + self.cgst + self.sgst + self.igst + self.cess


# ─── Helpers ─────────────────────────────────────────────────────────────


def _findtext_ci(node: ET.Element, tag: str) -> str | None:
    """Case-insensitive single-tag lookup. Returns the stripped text or None.

    Tally's serialiser inconsistently casts tag names; we walk children
    rather than using XPath so we don't have to predict the casing.
    """
    target = tag.upper()
    for child in node:
        if child.tag.upper() == target:
            return (child.text or "").strip() or None
    return None


def _findall_ci(node: ET.Element, tag: str) -> list[ET.Element]:
    target = tag.upper()
    return [c for c in node if c.tag.upper() == target]


def _to_decimal(raw: str | None) -> Decimal:
    """Tally amounts come signed (``-12345.67`` for credits) and sometimes
    wrap a quantity unit (``"1000.00 Ltr"``). Strip the unit and absolute
    the value — sign is encoded by the ledger entry's role (party vs item)
    which we already separate above."""
    if raw is None:
        return Decimal(0)
    s = raw.strip()
    if not s:
        return Decimal(0)
    # Strip trailing unit ("1000 Ltr", "85,000.00 INR")
    m = re.match(r"^[\s\-]*([\d,]+(?:\.\d+)?)", s)
    if not m:
        return Decimal(0)
    try:
        return abs(Decimal(m.group(1).replace(",", "")))
    except InvalidOperation:
        return Decimal(0)


def _split_qty_uom(raw: str | None) -> tuple[Decimal | None, str | None]:
    """``"1000.00 Ltr"`` → (Decimal("1000.00"), "Ltr").  Tally also emits
    compound UoMs like ``"5 Box of 10 Nos"`` — we keep only the leading
    quantity + unit, which is sufficient for emission factor lookup."""
    if not raw:
        return None, None
    s = raw.strip()
    m = re.match(r"^[\s\-]*([\d,]+(?:\.\d+)?)\s*([A-Za-z]+)?", s)
    if not m:
        return None, None
    try:
        qty = abs(Decimal(m.group(1).replace(",", "")))
    except InvalidOperation:
        return None, None
    uom = (m.group(2) or "").strip() or None
    return qty, uom


def _parse_tally_date(raw: str | None) -> date | None:
    """Tally exports dates as ``YYYYMMDD`` (no separators)."""
    if not raw:
        return None
    s = raw.strip()
    if len(s) == 8 and s.isdigit():
        try:
            return datetime.strptime(s, "%Y%m%d").date()
        except ValueError:
            return None
    # Fall back to ISO for sources that have already normalised
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _classify_ledger_kind(ledger_name: str | None) -> str:
    """Return one of: ``"tax_cgst"``, ``"tax_sgst"``, ``"tax_igst"``,
    ``"tax_cess"``, ``"party"`` (sundry/bank), or ``"cost"``."""
    if not ledger_name:
        return "cost"
    for kind, pat in _TAX_PATTERNS:
        if pat.search(ledger_name):
            return f"tax_{kind}"
    if _PARTY_LEDGER_HINT.search(ledger_name):
        return "party"
    return "cost"


def _voucher_to_dict(voucher: ET.Element) -> dict[str, Any]:
    """Cheap recursive ET → dict for the raw_payload audit column. We don't
    need round-trip fidelity, just enough that a human can read what was
    actually in the file."""
    out: dict[str, Any] = {}
    for child in voucher:
        key = child.tag
        value: Any
        if len(child) == 0:
            value = (child.text or "").strip()
        else:
            value = _voucher_to_dict(child)
        if key in out:
            # Repeated tag → list
            existing = out[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                out[key] = [existing, value]
        else:
            out[key] = value
    return out


# ─── Main entry point ────────────────────────────────────────────────────


def parse_tally_xml(xml_bytes: bytes) -> list[TallyLineItem]:
    """Parse a Tally voucher XML export. Returns one record per cost-bearing
    line; tax lines are aggregated onto the parent voucher and merged onto
    every cost line in that voucher.

    Vouchers with no cost lines (e.g. pure cash receipts) are skipped. The
    parser never raises on a single malformed voucher — bad vouchers are
    logged and dropped so a 50k-line ledger isn't aborted by one row.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"invalid Tally XML: {exc}") from exc

    line_items: list[TallyLineItem] = []
    vouchers_seen = 0

    # The voucher node can sit at depth 4 (ENVELOPE/BODY/DATA/TALLYMESSAGE/
    # VOUCHER) or sometimes at depth 1 in stripped exports. iter() is
    # cheapest and correctness-preserving.
    for voucher in root.iter():
        if voucher.tag.upper() != "VOUCHER":
            continue
        vouchers_seen += 1
        try:
            line_items.extend(_parse_one_voucher(voucher))
        except Exception as exc:  # noqa: BLE001 — defensive: never abort a batch
            guid = _findtext_ci(voucher, "GUID") or "?"
            logger.warning("tally: skipping voucher %s — %s", guid, exc)

    logger.info(
        "tally: parsed %d cost line(s) from %d voucher(s)",
        len(line_items), vouchers_seen,
    )
    return line_items


def _parse_one_voucher(voucher: ET.Element) -> list[TallyLineItem]:
    guid = _findtext_ci(voucher, "GUID")
    if not guid:
        # No GUID → can't dedup; skip rather than insert duplicate rows on
        # replay. Tally always emits GUID on real exports.
        return []

    voucher_number = _findtext_ci(voucher, "VOUCHERNUMBER")
    voucher_type = (
        voucher.attrib.get("VCHTYPE")
        or voucher.attrib.get("vchType")
        or _findtext_ci(voucher, "VOUCHERTYPENAME")
    )
    posting_date = _parse_tally_date(_findtext_ci(voucher, "DATE"))
    if posting_date is None:
        return []
    party_name = _findtext_ci(voucher, "PARTYLEDGERNAME") or _findtext_ci(voucher, "PARTYNAME")
    party_gstin = _findtext_ci(voucher, "PARTYGSTIN")
    narration = _findtext_ci(voucher, "NARRATION")
    raw_payload = _voucher_to_dict(voucher)

    # ── First pass: walk LEDGERENTRIES.LIST to aggregate tax buckets and
    # identify the cost ledger entries (some vouchers have NO inventory
    # block, only ledger entries — that's the common "expense voucher"
    # pattern in MSME books).
    cgst = sgst = igst = cess = Decimal(0)
    cost_ledger_entries: list[ET.Element] = []
    for entry in _findall_ci(voucher, "LEDGERENTRIES.LIST"):
        ledger_name = _findtext_ci(entry, "LEDGERNAME")
        amount = _to_decimal(_findtext_ci(entry, "AMOUNT"))
        kind = _classify_ledger_kind(ledger_name)
        if kind == "tax_cgst":
            cgst += amount
        elif kind == "tax_sgst":
            sgst += amount
        elif kind == "tax_igst":
            igst += amount
        elif kind == "tax_cess":
            cess += amount
        elif kind == "party":
            continue
        else:
            cost_ledger_entries.append(entry)

    # ── Second pass: ALLINVENTORYENTRIES.LIST (preferred — has HSN + qty +
    # stock item name). When present we use these as the line items and
    # ignore the duplicate cost ledger entries.
    inventory_entries = _findall_ci(voucher, "ALLINVENTORYENTRIES.LIST")

    results: list[TallyLineItem] = []
    if inventory_entries:
        for inv in inventory_entries:
            stock_name = _findtext_ci(inv, "STOCKITEMNAME")
            hsn = _findtext_ci(inv, "HSNCODE") or _findtext_ci(inv, "GSTHSNCODE")
            qty, uom = _split_qty_uom(
                _findtext_ci(inv, "ACTUALQTY") or _findtext_ci(inv, "BILLEDQTY")
            )
            amount = _to_decimal(_findtext_ci(inv, "AMOUNT"))
            if amount == 0:
                continue
            results.append(_make_line(
                guid=guid, voucher_number=voucher_number, voucher_type=voucher_type,
                posting_date=posting_date, party_name=party_name, party_gstin=party_gstin,
                narration=narration, ledger_name=stock_name, hsn_code=hsn,
                description=stock_name, base_value=amount, quantity=qty, uom=uom,
                cgst=cgst, sgst=sgst, igst=igst, cess=cess, raw_payload=raw_payload,
            ))
    else:
        for entry in cost_ledger_entries:
            ledger_name = _findtext_ci(entry, "LEDGERNAME")
            amount = _to_decimal(_findtext_ci(entry, "AMOUNT"))
            if amount == 0:
                continue
            results.append(_make_line(
                guid=guid, voucher_number=voucher_number, voucher_type=voucher_type,
                posting_date=posting_date, party_name=party_name, party_gstin=party_gstin,
                narration=narration, ledger_name=ledger_name, hsn_code=None,
                description=ledger_name, base_value=amount, quantity=None, uom=None,
                cgst=cgst, sgst=sgst, igst=igst, cess=cess, raw_payload=raw_payload,
            ))

    # If a voucher has multiple cost lines, the aggregated tax buckets
    # belong proportionally — but slice 0 keeps it simple and lets the
    # caller see the full GST on the first line (downstream emission calc
    # ignores tax, so this is information-only). Multi-line GST allocation
    # is a slice-1 concern.
    if results and len(results) > 1:
        zero = Decimal(0)
        results = [results[0]] + [
            _make_line(
                guid=r.voucher_guid, voucher_number=r.voucher_number,
                voucher_type=r.voucher_type, posting_date=r.posting_date,
                party_name=r.party_name, party_gstin=r.party_gstin,
                narration=r.narration, ledger_name=r.ledger_name,
                hsn_code=r.hsn_code, description=r.description,
                base_value=r.base_value, quantity=r.quantity, uom=r.uom,
                cgst=zero, sgst=zero, igst=zero, cess=zero,
                raw_payload=r.raw_payload,
            )
            for r in results[1:]
        ]
    return results


def _make_line(**kw: Any) -> TallyLineItem:
    """Tiny wrapper so the two construction sites above stay readable."""
    return TallyLineItem(
        voucher_guid=kw["guid"],
        voucher_number=kw["voucher_number"],
        voucher_type=kw["voucher_type"],
        posting_date=kw["posting_date"],
        party_name=kw["party_name"],
        party_gstin=kw["party_gstin"],
        narration=kw["narration"],
        ledger_name=kw["ledger_name"],
        hsn_code=kw["hsn_code"],
        description=kw["description"],
        base_value=kw["base_value"],
        quantity=kw["quantity"],
        uom=kw["uom"],
        cgst=kw["cgst"],
        sgst=kw["sgst"],
        igst=kw["igst"],
        cess=kw["cess"],
        raw_payload=kw["raw_payload"],
    )


# ─── Fiscal-year helper ──────────────────────────────────────────────────


def fiscal_year_for(d: date) -> str:
    """Indian fiscal year: April–March. ``date(2025, 4, 1) → "FY2025-26"``."""
    if d.month >= 4:
        return f"FY{d.year}-{(d.year + 1) % 100:02d}"
    return f"FY{d.year - 1}-{d.year % 100:02d}"
