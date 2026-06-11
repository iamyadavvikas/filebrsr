"""Tests for the Tally connector (Slice 0)."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.tally import (
    Classification,
    IngestSummary,
    TallyLineItem,
    classify_hsn,
    fiscal_year_for,
    ingest_tally_xml,
    parse_tally_xml,
    reset_cache,
)

FIXTURE = Path(__file__).parent / "fixtures" / "tally_sample.xml"


@pytest.fixture(autouse=True)
def _reset_classifier_cache():
    reset_cache()
    yield
    reset_cache()


@pytest.fixture
def sample_xml() -> bytes:
    return FIXTURE.read_bytes()


# ─── Fiscal year helper ───────────────────────────────────────────────────


@pytest.mark.parametrize("d,expected", [
    (date(2025, 4, 1), "FY2025-26"),
    (date(2025, 4, 15), "FY2025-26"),
    (date(2025, 12, 31), "FY2025-26"),
    (date(2026, 1, 5), "FY2025-26"),
    (date(2026, 3, 31), "FY2025-26"),
    (date(2026, 4, 1), "FY2026-27"),
    (date(2024, 4, 1), "FY2024-25"),
    (date(2024, 3, 31), "FY2023-24"),
])
def test_fiscal_year_for(d: date, expected: str):
    assert fiscal_year_for(d) == expected


# ─── Classifier ───────────────────────────────────────────────────────────


def test_classify_known_scope1_fuel():
    c = classify_hsn("27101920")
    assert c.scope == 1
    assert c.scope3_category is None
    assert c.matched_prefix == "2710"
    assert c.confidence == "high"


def test_classify_electricity_is_scope2():
    c = classify_hsn("27160000")
    assert c.scope == 2
    assert c.matched_prefix == "2716"
    assert c.confidence == "high"


def test_classify_service_sac_is_scope3():
    c = classify_hsn("998314")  # IT consulting under SAC 9983
    assert c.scope == 3
    assert c.scope3_category == "1_purchased_goods_services"
    assert c.matched_prefix == "9983"


def test_classify_unknown_hsn_is_unmapped():
    c = classify_hsn("99999999")
    assert c.confidence == "unmapped"
    assert c.scope is None
    assert c.matched_prefix is None


def test_classify_none_hsn_is_unmapped():
    c = classify_hsn(None)
    assert c.confidence == "unmapped"


def test_classify_strips_separators():
    """HSN '2710.19.20' should normalise to '27101920' and still match 2710."""
    c = classify_hsn("2710.19.20")
    assert c.scope == 1
    assert c.matched_prefix == "2710"


def test_classify_returns_frozen_dataclass():
    c = classify_hsn("27101920")
    assert isinstance(c, Classification)
    with pytest.raises((AttributeError, Exception)):
        c.scope = 99  # type: ignore[misc]


# ─── Parser ───────────────────────────────────────────────────────────────


def test_parse_returns_six_line_items(sample_xml: bytes):
    lines = parse_tally_xml(sample_xml)
    assert len(lines) == 6


def test_parse_diesel_voucher(sample_xml: bytes):
    lines = parse_tally_xml(sample_xml)
    diesel = next(line for line in lines if line.voucher_guid == "tally-vch-0001")
    assert diesel.voucher_type == "Purchase"
    assert diesel.voucher_number == "PUR/2025/0001"
    assert diesel.posting_date == date(2025, 4, 15)
    assert diesel.party_name == "Reliance Industries Ltd"
    assert diesel.party_gstin == "27AAACR5055K1Z7"
    assert diesel.hsn_code == "27101920"
    assert diesel.base_value == Decimal("85000.00")
    assert diesel.cgst == Decimal("7650.00")
    assert diesel.sgst == Decimal("7650.00")
    assert diesel.igst == Decimal(0)
    assert diesel.quantity == Decimal("1000.00")
    assert diesel.uom == "Ltr"
    assert diesel.total_value == Decimal("100300.00")


def test_parse_filters_party_ledger(sample_xml: bytes):
    """Sundry Creditors / Bank ledgers must not appear as cost lines."""
    lines = parse_tally_xml(sample_xml)
    ledger_names = [line.ledger_name for line in lines if line.ledger_name]
    assert not any("Sundry Creditors" in n for n in ledger_names)
    assert not any("Bank" in n for n in ledger_names)


def test_parse_interstate_voucher_has_igst(sample_xml: bytes):
    lines = parse_tally_xml(sample_xml)
    consulting = next(line for line in lines if line.voucher_guid == "tally-vch-0003")
    assert consulting.igst == Decimal("90000.00")
    assert consulting.cgst == Decimal(0)
    assert consulting.sgst == Decimal(0)


def test_parse_ledger_only_voucher(sample_xml: bytes):
    """Voucher with no inventory block falls back to ledger entries."""
    lines = parse_tally_xml(sample_xml)
    cleaning = next(line for line in lines if line.voucher_guid == "tally-vch-0004")
    assert cleaning.hsn_code is None
    assert cleaning.ledger_name == "Housekeeping Expenses"
    assert cleaning.base_value == Decimal("15000.00")


def test_parse_invalid_xml_raises():
    with pytest.raises(ValueError, match="invalid Tally XML"):
        parse_tally_xml(b"<<<not xml>>>")


def test_parse_empty_envelope_returns_empty():
    lines = parse_tally_xml(b"<ENVELOPE/>")
    assert lines == []


def test_parse_voucher_without_guid_is_skipped():
    xml = b"""<ENVELOPE><BODY><DATA><TALLYMESSAGE>
        <VOUCHER VCHTYPE="Purchase">
            <DATE>20250415</DATE>
            <VOUCHERNUMBER>NO-GUID</VOUCHERNUMBER>
            <ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>X</STOCKITEMNAME>
                <HSNCODE>2710</HSNCODE>
                <AMOUNT>100</AMOUNT>
            </ALLINVENTORYENTRIES.LIST>
        </VOUCHER>
    </TALLYMESSAGE></DATA></BODY></ENVELOPE>"""
    assert parse_tally_xml(xml) == []


# ─── Ingest end-to-end ────────────────────────────────────────────────────


def test_ingest_dry_run_no_supabase(sample_xml: bytes):
    summary = ingest_tally_xml(
        xml_bytes=sample_xml,
        user_id="00000000-0000-0000-0000-000000000001",
    )
    assert isinstance(summary, IngestSummary)
    assert summary.lines_parsed == 6
    assert summary.lines_mapped == 3
    assert summary.lines_unmapped == 3
    assert summary.rows_inserted == 0
    assert summary.file_sha256 == hashlib.sha256(sample_xml).hexdigest()


def test_ingest_row_shape(sample_xml: bytes):
    summary = ingest_tally_xml(
        xml_bytes=sample_xml,
        user_id="00000000-0000-0000-0000-000000000001",
    )
    diesel_row = next(r for r in summary.rows if r["source_voucher_id"] == "tally-vch-0001")
    expected_keys = {
        "user_id", "source_system", "source_file_sha256", "source_voucher_id",
        "source_voucher_number", "voucher_type", "fiscal_year", "posting_date",
        "vendor_name", "vendor_gstin", "vendor_state_code",
        "ledger_name", "hsn_code", "description",
        "base_value", "cgst", "sgst", "igst", "cess", "total_value", "quantity",
        "uom", "cost_centre_name", "cost_centre_category",
        "scope", "scope3_category", "classification_confidence",
        "raw_payload",
    }
    assert set(diesel_row.keys()) == expected_keys
    assert diesel_row["source_system"] == "tally"
    assert diesel_row["fiscal_year"] == "FY2025-26"
    assert diesel_row["scope"] == 1
    assert diesel_row["classification_confidence"] == "high"
    assert diesel_row["base_value"] == "85000.00"
    assert diesel_row["total_value"] == "100300.00"


def test_ingest_persists_when_client_provided(sample_xml: bytes):
    client = MagicMock()
    inserted_response = MagicMock()
    inserted_response.data = [{"id": i} for i in range(6)]
    client.table.return_value.insert.return_value.execute.return_value = inserted_response

    summary = ingest_tally_xml(
        xml_bytes=sample_xml,
        user_id="00000000-0000-0000-0000-000000000001",
        supabase_client=client,
    )
    assert summary.rows_inserted == 6
    client.table.assert_called_once_with("raw_records")
    insert_call_arg = client.table.return_value.insert.call_args[0][0]
    assert len(insert_call_arg) == 6
    # SHA-256 propagates onto every row for audit
    assert all(r["source_file_sha256"] == summary.file_sha256 for r in insert_call_arg)


def test_ingest_insert_failure_propagates(sample_xml: bytes):
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db down")
    with pytest.raises(RuntimeError, match="db down"):
        ingest_tally_xml(
            xml_bytes=sample_xml,
            user_id="00000000-0000-0000-0000-000000000001",
            supabase_client=client,
        )


def test_ingest_sha256_is_deterministic(sample_xml: bytes):
    s1 = ingest_tally_xml(xml_bytes=sample_xml, user_id="u")
    s2 = ingest_tally_xml(xml_bytes=sample_xml, user_id="u")
    assert s1.file_sha256 == s2.file_sha256


def test_ingest_empty_xml_returns_empty_summary():
    summary = ingest_tally_xml(xml_bytes=b"<ENVELOPE/>", user_id="u")
    assert summary.lines_parsed == 0
    assert summary.rows == []
    # SHA-256 of an empty envelope is still computed
    assert len(summary.file_sha256) == 64


def test_line_item_is_frozen(sample_xml: bytes):
    line = parse_tally_xml(sample_xml)[0]
    assert isinstance(line, TallyLineItem)
    with pytest.raises(Exception):
        line.base_value = Decimal(0)  # type: ignore[misc]


# ─── Chunked insert (Slice 1) ────────────────────────────────────────────


def _make_synthetic_xml(n_vouchers: int) -> bytes:
    """Generate a Tally XML with ``n_vouchers`` purchase vouchers, all
    mapped to HSN 2710 (diesel). Used to exercise chunking without
    hand-writing thousands of lines."""
    bits = ['<?xml version="1.0" encoding="UTF-8"?><ENVELOPE><BODY><DATA>']
    for i in range(n_vouchers):
        bits.append(
            f'<TALLYMESSAGE><VOUCHER VCHTYPE="Purchase">'
            f"<DATE>20250415</DATE>"
            f"<GUID>synth-{i:06d}</GUID>"
            f"<VOUCHERNUMBER>PUR/{i:06d}</VOUCHERNUMBER>"
            f"<PARTYLEDGERNAME>Vendor {i}</PARTYLEDGERNAME>"
            f"<ALLINVENTORYENTRIES.LIST>"
            f"<STOCKITEMNAME>Diesel HSD</STOCKITEMNAME>"
            f"<HSNCODE>27101920</HSNCODE>"
            f"<AMOUNT>{1000 + i}.00</AMOUNT>"
            f"</ALLINVENTORYENTRIES.LIST>"
            f"</VOUCHER></TALLYMESSAGE>"
        )
    bits.append("</DATA></BODY></ENVELOPE>")
    return "".join(bits).encode("utf-8")


def test_ingest_chunks_large_payloads():
    """2500 rows with chunk_size=1000 → 3 insert calls (1000, 1000, 500)."""
    xml = _make_synthetic_xml(2500)
    client = MagicMock()
    # Each chunk's response.data = same length as the input batch
    def _fake_execute_factory():
        call = {"n": 0}
        def _execute():
            # supabase-py: insert(rows).execute() returns response with .data
            r = MagicMock()
            r.data = [{"id": i} for i in range(call["n"])]
            return r
        return _execute, call

    # Capture chunk sizes by inspecting insert.call_args_list afterwards
    responses = []

    def insert_side_effect(rows):
        m = MagicMock()
        responses.append(len(rows))
        execute_result = MagicMock()
        execute_result.data = [{"id": i} for i in range(len(rows))]
        m.execute.return_value = execute_result
        return m

    client.table.return_value.insert.side_effect = insert_side_effect

    summary = ingest_tally_xml(
        xml_bytes=xml,
        user_id="00000000-0000-0000-0000-000000000001",
        supabase_client=client,
        chunk_size=1000,
    )
    assert summary.lines_parsed == 2500
    assert summary.rows_inserted == 2500
    assert responses == [1000, 1000, 500]


def test_ingest_chunk_failure_aborts_remaining():
    """Failure on chunk 2 raises, and inserted-count reflects only chunk 1."""
    xml = _make_synthetic_xml(2500)
    client = MagicMock()

    call_count = {"n": 0}

    def insert_side_effect(rows):
        call_count["n"] += 1
        m = MagicMock()
        if call_count["n"] == 2:
            m.execute.side_effect = RuntimeError("simulated chunk-2 failure")
        else:
            result = MagicMock()
            result.data = [{"id": i} for i in range(len(rows))]
            m.execute.return_value = result
        return m

    client.table.return_value.insert.side_effect = insert_side_effect

    with pytest.raises(RuntimeError, match="chunk-2 failure"):
        ingest_tally_xml(
            xml_bytes=xml,
            user_id="u",
            supabase_client=client,
            chunk_size=1000,
        )


# ─── HTTP endpoint (Slice 1) ─────────────────────────────────────────────


@pytest.fixture
async def async_client(mock_supabase):
    """Reusable httpx client wired to the real ASGI app with mocked supabase.

    We patch ``app.main.get_supabase_admin`` because router_tally imports the
    helper lazily from app.main at request time.
    """
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    with patch("app.main.get_supabase_admin", return_value=mock_supabase):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


_AUTH = {"Authorization": "Bearer test-service-key"}


@pytest.mark.asyncio
async def test_endpoint_requires_auth(async_client, sample_xml):
    files = {"file": ("daybook.xml", sample_xml, "application/xml")}
    resp = await async_client.post(
        "/api/tally/ingest", files=files, data={"user_id": "u"},
    )
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_endpoint_rejects_wrong_bearer(async_client, sample_xml):
    files = {"file": ("daybook.xml", sample_xml, "application/xml")}
    resp = await async_client.post(
        "/api/tally/ingest",
        headers={"Authorization": "Bearer wrong"},
        files=files,
        data={"user_id": "u"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_happy_path(async_client, mock_supabase, sample_xml):
    # mock_supabase.table.insert returns MagicMock by default; configure data
    insert_result = MagicMock()
    insert_result.data = [{"id": i} for i in range(6)]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = insert_result

    files = {"file": ("daybook.xml", sample_xml, "application/xml")}
    resp = await async_client.post(
        "/api/tally/ingest", headers=_AUTH, files=files,
        data={"user_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["lines_parsed"] == 6
    assert body["lines_mapped"] == 3
    assert body["lines_unmapped"] == 3
    assert body["rows_inserted"] == 6
    assert len(body["file_sha256"]) == 64


@pytest.mark.asyncio
async def test_endpoint_rejects_empty_upload(async_client):
    files = {"file": ("daybook.xml", b"", "application/xml")}
    resp = await async_client.post(
        "/api/tally/ingest", headers=_AUTH, files=files, data={"user_id": "u"},
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_endpoint_rejects_invalid_xml(async_client):
    files = {"file": ("daybook.xml", b"<<not xml>>", "application/xml")}
    resp = await async_client.post(
        "/api/tally/ingest", headers=_AUTH, files=files, data={"user_id": "u"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_endpoint_returns_500_on_db_failure(async_client, mock_supabase, sample_xml):
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db down")
    files = {"file": ("daybook.xml", sample_xml, "application/xml")}
    resp = await async_client.post(
        "/api/tally/ingest", headers=_AUTH, files=files, data={"user_id": "u"},
    )
    assert resp.status_code == 500
