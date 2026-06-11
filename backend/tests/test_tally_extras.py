"""Tests for cost-centre splitting, vendor-state derivation, and signed export."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.tally.cost_centre import split_by_cost_centre
from app.tally.export import canonical_json, sign_batch, verify_batch
from app.tally.parser import (
    CostCentreAllocation,
    TallyLineItem,
    parse_tally_xml,
)
from app.tally.vendor_master import (
    INDIAN_STATE_CODES,
    gstin_to_state_code,
    state_name_for,
)

# ─── Helpers ─────────────────────────────────────────────────────────────


def _make_line(
    base: str = "100000.00",
    cgst: str = "9000.00",
    sgst: str = "9000.00",
    igst: str = "0",
    cess: str = "0",
    quantity: str | None = "5000.00",
    allocations: tuple[CostCentreAllocation, ...] = (),
) -> TallyLineItem:
    return TallyLineItem(
        voucher_guid="g1",
        voucher_number="PUR/0001",
        voucher_type="Purchase",
        posting_date=date(2025, 6, 15),
        party_name="ACME",
        party_gstin=None,
        narration=None,
        ledger_name="Fuel",
        hsn_code="27101920",
        description="Diesel",
        base_value=Decimal(base),
        quantity=None if quantity is None else Decimal(quantity),
        uom="Ltr" if quantity else None,
        cgst=Decimal(cgst),
        sgst=Decimal(sgst),
        igst=Decimal(igst),
        cess=Decimal(cess),
        cost_centre_allocations=allocations,
    )


# ─── cost_centre.split_by_cost_centre ────────────────────────────────────


def test_no_allocations_returns_single_unallocated():
    line = _make_line()
    result = split_by_cost_centre(line)
    assert len(result) == 1
    assert result[0].cost_centre_name is None
    assert result[0].cost_centre_category is None
    assert result[0].line is line  # unchanged


def test_single_allocation_resolves_centre_and_category():
    line = _make_line(allocations=(
        CostCentreAllocation(name="Mumbai Plant", category="Manufacturing", amount=Decimal("100000")),
    ))
    [out] = split_by_cost_centre(line)
    assert out.cost_centre_name == "Mumbai Plant"
    assert out.cost_centre_category == "Manufacturing"
    assert out.line.base_value == Decimal("100000.00")


def test_two_allocations_split_proportionally():
    """₹100k split 60/40 across two centres → ₹60k + ₹40k."""
    line = _make_line(allocations=(
        CostCentreAllocation(name="Mumbai", category="Mfg", amount=Decimal("60000")),
        CostCentreAllocation(name="Delhi",  category="Mfg", amount=Decimal("40000")),
    ))
    splits = split_by_cost_centre(line)
    assert len(splits) == 2
    assert splits[0].cost_centre_name == "Mumbai"
    assert splits[1].cost_centre_name == "Delhi"
    assert splits[0].line.base_value == Decimal("60000.00")
    assert splits[1].line.base_value == Decimal("40000.00")
    # GST splits proportionally too
    assert splits[0].line.cgst == Decimal("5400.00")
    assert splits[1].line.cgst == Decimal("3600.00")


def test_split_preserves_totals_with_rounding():
    """A non-clean split (333/333/334) must still sum to original."""
    line = _make_line(
        base="1000.00", cgst="0", sgst="0", igst="0", cess="0", quantity=None,
        allocations=(
            CostCentreAllocation(name="A", category=None, amount=Decimal("1")),
            CostCentreAllocation(name="B", category=None, amount=Decimal("1")),
            CostCentreAllocation(name="C", category=None, amount=Decimal("1")),
        ),
    )
    splits = split_by_cost_centre(line)
    total = sum((s.line.base_value for s in splits), Decimal(0))
    assert total == Decimal("1000.00")
    # Last split absorbs the rounding remainder
    assert splits[0].line.base_value == Decimal("333.33")
    assert splits[1].line.base_value == Decimal("333.33")
    assert splits[2].line.base_value == Decimal("333.34")


def test_split_quantity_when_present():
    line = _make_line(
        base="10000.00", quantity="500.00", cgst="0", sgst="0", igst="0", cess="0",
        allocations=(
            CostCentreAllocation(name="A", category=None, amount=Decimal("6000")),
            CostCentreAllocation(name="B", category=None, amount=Decimal("4000")),
        ),
    )
    splits = split_by_cost_centre(line)
    assert splits[0].line.quantity == Decimal("300.00")
    assert splits[1].line.quantity == Decimal("200.00")


def test_split_handles_zero_total_amount():
    """If allocation amounts are all zero (defensive), equal-split."""
    line = _make_line(
        base="1000.00", cgst="0", sgst="0", igst="0", cess="0", quantity=None,
        allocations=(
            CostCentreAllocation(name="A", category=None, amount=Decimal("0")),
            CostCentreAllocation(name="B", category=None, amount=Decimal("0")),
        ),
    )
    splits = split_by_cost_centre(line)
    assert splits[0].line.base_value == Decimal("500.00")
    assert splits[1].line.base_value == Decimal("500.00")


def test_split_is_pure_no_mutation():
    line = _make_line(allocations=(
        CostCentreAllocation(name="A", category=None, amount=Decimal("50000")),
        CostCentreAllocation(name="B", category=None, amount=Decimal("50000")),
    ))
    original_base = line.base_value
    split_by_cost_centre(line)
    assert line.base_value == original_base


# ─── Parser extraction of cost-centre allocations (end-to-end) ───────────


def test_parser_extracts_costcentre_under_inventory():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA>
<TALLYMESSAGE><VOUCHER VCHTYPE="Purchase">
  <DATE>20250615</DATE>
  <GUID>vch-cc-1</GUID>
  <VOUCHERNUMBER>PUR/CC/0001</VOUCHERNUMBER>
  <PARTYLEDGERNAME>ACME Fuel</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>Diesel HSD</STOCKITEMNAME>
    <HSNCODE>27101920</HSNCODE>
    <AMOUNT>100000.00</AMOUNT>
    <CATEGORYALLOCATIONS.LIST>
      <CATEGORY>Plant Operations</CATEGORY>
      <COSTCENTREALLOCATIONS.LIST>
        <NAME>Mumbai Plant</NAME>
        <AMOUNT>-60000.00</AMOUNT>
      </COSTCENTREALLOCATIONS.LIST>
      <COSTCENTREALLOCATIONS.LIST>
        <NAME>Delhi Plant</NAME>
        <AMOUNT>-40000.00</AMOUNT>
      </COSTCENTREALLOCATIONS.LIST>
    </CATEGORYALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE>
</DATA></BODY></ENVELOPE>"""
    [line] = parse_tally_xml(xml)
    assert len(line.cost_centre_allocations) == 2
    names = [a.name for a in line.cost_centre_allocations]
    assert names == ["Mumbai Plant", "Delhi Plant"]
    assert line.cost_centre_allocations[0].category == "Plant Operations"
    assert line.cost_centre_allocations[0].amount == Decimal("60000.00")


def test_parser_extracts_costcentre_without_category_wrapper():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA>
<TALLYMESSAGE><VOUCHER VCHTYPE="Purchase">
  <DATE>20250615</DATE>
  <GUID>vch-cc-2</GUID>
  <VOUCHERNUMBER>PUR/CC/0002</VOUCHERNUMBER>
  <PARTYLEDGERNAME>ACME Fuel</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>Electricity</STOCKITEMNAME>
    <HSNCODE>27160000</HSNCODE>
    <AMOUNT>50000.00</AMOUNT>
    <COSTCENTREALLOCATIONS.LIST>
      <NAME>Head Office</NAME>
      <AMOUNT>-50000.00</AMOUNT>
    </COSTCENTREALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE>
</DATA></BODY></ENVELOPE>"""
    [line] = parse_tally_xml(xml)
    assert len(line.cost_centre_allocations) == 1
    assert line.cost_centre_allocations[0].name == "Head Office"
    assert line.cost_centre_allocations[0].category is None


# ─── vendor_master.gstin_to_state_code ───────────────────────────────────


def test_gstin_to_state_code_valid_maharashtra():
    # Real-format example: 27 = Maharashtra
    assert gstin_to_state_code("27AAACR5055K1ZK") == "27"


def test_gstin_to_state_code_valid_karnataka():
    assert gstin_to_state_code("29AABCT1332L1Z2") == "29"


def test_gstin_to_state_code_normalises_whitespace_and_case():
    assert gstin_to_state_code("  27aaacr5055k1zk  ") == "27"


def test_gstin_to_state_code_rejects_short():
    assert gstin_to_state_code("27AAA") is None


def test_gstin_to_state_code_rejects_garbage():
    assert gstin_to_state_code("XXXXXXXXXXXXXXX") is None


def test_gstin_to_state_code_rejects_none_and_empty():
    assert gstin_to_state_code(None) is None
    assert gstin_to_state_code("") is None
    assert gstin_to_state_code("   ") is None


def test_gstin_to_state_code_rejects_unknown_state_prefix():
    # 50 isn't an allocated state code — even with a structurally-valid GSTIN
    # we should reject it rather than silently produce nonsense rollups.
    assert gstin_to_state_code("50AAACR5055K1ZK") is None


def test_state_name_for_known_codes():
    assert state_name_for("27") == "Maharashtra"
    assert state_name_for("29") == "Karnataka"
    assert state_name_for("37") == "Andhra Pradesh"


def test_state_name_for_unknown_returns_none():
    assert state_name_for("99X") is None
    assert state_name_for(None) is None


def test_state_codes_covers_all_indian_states():
    # Sanity check the table is reasonably complete
    assert len(INDIAN_STATE_CODES) >= 36


# ─── export.sign_batch / verify_batch ────────────────────────────────────


_SAMPLE_ROWS: list[dict] = [
    {"id": 1, "vendor": "A", "amount": "100.00"},
    {"id": 2, "vendor": "B", "amount": "200.00"},
]


def test_canonical_json_is_deterministic():
    a = canonical_json([{"b": 2, "a": 1}, {"d": 4, "c": 3}])
    b = canonical_json([{"a": 1, "b": 2}, {"c": 3, "d": 4}])
    assert a == b
    # No spaces (compact)
    assert b" " not in a


def test_canonical_json_handles_decimal_via_default_str():
    payload = canonical_json([{"x": Decimal("100.00")}])
    assert b"100.00" in payload


def test_sign_batch_produces_full_envelope():
    envelope = sign_batch(_SAMPLE_ROWS, signing_key=b"my-secret-key", key_id="k1")
    assert envelope["rows"] == _SAMPLE_ROWS
    assert envelope["key_id"] == "k1"
    assert envelope["algorithm"] == "HMAC-SHA256"
    assert envelope["version"] == "tally-export-v1"
    assert len(envelope["sha256"]) == 64
    assert len(envelope["hmac_sha256"]) == 64
    # signed_at is ISO-8601 UTC
    datetime.fromisoformat(envelope["signed_at"])


def test_sign_batch_accepts_string_key():
    envelope = sign_batch(_SAMPLE_ROWS, signing_key="str-secret", key_id="k2")
    assert envelope["hmac_sha256"]


def test_sign_batch_uses_env_when_no_key_passed(monkeypatch):
    monkeypatch.setenv("TALLY_EXPORT_SIGNING_KEY", "env-secret")
    envelope = sign_batch(_SAMPLE_ROWS, key_id="k3")
    assert envelope["hmac_sha256"]
    assert verify_batch(envelope, signing_key="env-secret")


def test_sign_batch_raises_when_no_key_available(monkeypatch):
    monkeypatch.delenv("TALLY_EXPORT_SIGNING_KEY", raising=False)
    with pytest.raises(RuntimeError, match="signing key"):
        sign_batch(_SAMPLE_ROWS, key_id="k4")


def test_sign_batch_raises_on_empty_key():
    with pytest.raises(RuntimeError, match="signing key"):
        sign_batch(_SAMPLE_ROWS, signing_key=b"", key_id="k5")


def test_sign_batch_deterministic_with_fixed_timestamp():
    fixed = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    e1 = sign_batch(_SAMPLE_ROWS, signing_key=b"k", key_id="x", signed_at=fixed)
    e2 = sign_batch(_SAMPLE_ROWS, signing_key=b"k", key_id="x", signed_at=fixed)
    assert e1 == e2


def test_verify_batch_accepts_valid():
    envelope = sign_batch(_SAMPLE_ROWS, signing_key=b"k", key_id="x")
    assert verify_batch(envelope, signing_key=b"k") is True


def test_verify_batch_rejects_wrong_key():
    envelope = sign_batch(_SAMPLE_ROWS, signing_key=b"k", key_id="x")
    assert verify_batch(envelope, signing_key=b"different") is False


def test_verify_batch_rejects_tampered_rows():
    envelope = sign_batch(_SAMPLE_ROWS, signing_key=b"k", key_id="x")
    envelope["rows"][0]["amount"] = "99999.00"
    assert verify_batch(envelope, signing_key=b"k") is False


def test_verify_batch_rejects_tampered_sha():
    envelope = sign_batch(_SAMPLE_ROWS, signing_key=b"k", key_id="x")
    envelope["sha256"] = "0" * 64
    assert verify_batch(envelope, signing_key=b"k") is False


def test_verify_batch_rejects_missing_fields():
    assert verify_batch({}, signing_key=b"k") is False
    assert verify_batch({"rows": []}, signing_key=b"k") is False


# ─── Ingest integration: cost-centre + state-code populated ──────────────


def test_ingest_populates_state_and_cost_centre():
    from app.tally.ingest import ingest_tally_xml

    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA>
<TALLYMESSAGE><VOUCHER VCHTYPE="Purchase">
  <DATE>20250615</DATE>
  <GUID>vch-cc-int-1</GUID>
  <VOUCHERNUMBER>PUR/INT/0001</VOUCHERNUMBER>
  <PARTYLEDGERNAME>ACME Fuel</PARTYLEDGERNAME>
  <PARTYGSTIN>27AAACR5055K1ZK</PARTYGSTIN>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>Diesel HSD</STOCKITEMNAME>
    <HSNCODE>27101920</HSNCODE>
    <AMOUNT>100000.00</AMOUNT>
    <COSTCENTREALLOCATIONS.LIST>
      <NAME>Mumbai Plant</NAME>
      <AMOUNT>-60000.00</AMOUNT>
    </COSTCENTREALLOCATIONS.LIST>
    <COSTCENTREALLOCATIONS.LIST>
      <NAME>Delhi Plant</NAME>
      <AMOUNT>-40000.00</AMOUNT>
    </COSTCENTREALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE>
</DATA></BODY></ENVELOPE>"""

    summary = ingest_tally_xml(
        xml_bytes=xml, user_id="00000000-0000-0000-0000-000000000001",
    )
    # 1 voucher line → 2 cost-centre rows
    assert summary.lines_parsed == 2
    by_centre = {r["cost_centre_name"]: r for r in summary.rows}
    assert by_centre["Mumbai Plant"]["base_value"] == "60000.00"
    assert by_centre["Delhi Plant"]["base_value"] == "40000.00"
    # Both rows carry the vendor's state code derived from GSTIN
    assert by_centre["Mumbai Plant"]["vendor_state_code"] == "27"
    assert by_centre["Delhi Plant"]["vendor_state_code"] == "27"


def test_ingest_handles_lines_without_cost_centres():
    """Existing fixture has no cost-centre allocations → fields are None."""
    from pathlib import Path

    from app.tally.ingest import ingest_tally_xml

    sample = Path(__file__).parent / "fixtures" / "tally_sample.xml"
    summary = ingest_tally_xml(
        xml_bytes=sample.read_bytes(),
        user_id="00000000-0000-0000-0000-000000000001",
    )
    for row in summary.rows:
        assert row["cost_centre_name"] is None
        assert row["cost_centre_category"] is None
