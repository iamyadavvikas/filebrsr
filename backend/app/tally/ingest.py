"""
Tally ingest orchestrator — XML bytes → classified records → raw_records.

Slice 0 entry point: a single function that takes a Tally XML export and
either persists the parsed/classified line items into the ``raw_records``
table (when a Supabase client is provided) or returns them for inspection
(dry-run / test mode).

The function is intentionally synchronous and stateless: no retries, no
batching, no transaction. The first failure surfaces to the caller. A
later slice will add chunked inserts (Supabase REST caps at ~1000 rows)
and a resumable cursor stored alongside the file SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.tally.classifier import classify_hsn
from app.tally.parser import TallyLineItem, fiscal_year_for, parse_tally_xml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestSummary:
    """What ``ingest_tally_xml`` returns."""

    file_sha256: str
    lines_parsed: int
    lines_mapped: int                          # confidence in {high, medium, low}
    lines_unmapped: int                        # confidence == "unmapped"
    rows_inserted: int                         # zero on dry-run
    rows: list[dict[str, Any]]                 # the row dicts handed to Supabase


def _decimal_to_str(value: Decimal | None) -> str | None:
    """jsonb columns happily accept strings for numerics, and Decimal isn't
    JSON-serialisable. We keep the precision by serialising as string; the
    Supabase numeric column casts on insert."""
    if value is None:
        return None
    return f"{value:f}"


def _row_for(
    line: TallyLineItem, *, user_id: str, file_sha256: str,
) -> dict[str, Any]:
    """Build the dict that maps 1:1 to a row in ``raw_records``."""
    classification = classify_hsn(line.hsn_code)
    return {
        "user_id": user_id,
        "source_system": "tally",
        "source_file_sha256": file_sha256,
        "source_voucher_id": line.voucher_guid,
        "source_voucher_number": line.voucher_number,
        "voucher_type": line.voucher_type,
        "fiscal_year": fiscal_year_for(line.posting_date),
        "posting_date": line.posting_date.isoformat(),
        "vendor_name": line.party_name,
        "vendor_gstin": line.party_gstin,
        "ledger_name": line.ledger_name,
        "hsn_code": line.hsn_code,
        "description": line.description,
        "base_value": _decimal_to_str(line.base_value),
        "cgst": _decimal_to_str(line.cgst),
        "sgst": _decimal_to_str(line.sgst),
        "igst": _decimal_to_str(line.igst),
        "cess": _decimal_to_str(line.cess),
        "total_value": _decimal_to_str(line.total_value),
        "quantity": _decimal_to_str(line.quantity),
        "uom": line.uom,
        "scope": classification.scope,
        "scope3_category": classification.scope3_category,
        "classification_confidence": classification.confidence,
        # Postgres jsonb accepts a JSON string or a dict via supabase-py; we
        # pre-serialise to be explicit (avoids surprises with Decimal inside
        # raw_payload from older Tally versions).
        "raw_payload": json.dumps(line.raw_payload, default=str),
    }


def ingest_tally_xml(
    *,
    xml_bytes: bytes,
    user_id: str,
    supabase_client: Any | None = None,
    chunk_size: int = 1000,
) -> IngestSummary:
    """Parse + classify a Tally XML export, optionally persisting to
    ``raw_records``.

    Parameters
    ----------
    xml_bytes
        Raw bytes of the Tally export file. We compute SHA-256 over these
        bytes for audit-trail replayability — anyone re-fetching the file
        can prove byte-for-byte equivalence.
    user_id
        UUID of the owning profile. Required by the ``raw_records.user_id``
        FK and by RLS on inserts.
    supabase_client
        Optional. When ``None``, the function is a pure parse/classify
        dry-run — useful in tests and the curator preview UI. When given,
        the rows are inserted via ``client.table("raw_records").insert(rows)``.
    chunk_size
        Rows per insert request. Defaults to 1000 — PostgREST refuses payloads
        much larger than this, and a 50k-line ledger needs ~50 round-trips.

    Returns
    -------
    IngestSummary
        Counts + the row dicts (whether or not they were persisted).

    Raises
    ------
    ValueError
        If the XML doesn't parse (forwarded from
        :func:`app.tally.parser.parse_tally_xml`).
    """
    file_sha256 = hashlib.sha256(xml_bytes).hexdigest()
    line_items = parse_tally_xml(xml_bytes)

    rows = [_row_for(line, user_id=user_id, file_sha256=file_sha256) for line in line_items]
    unmapped = sum(1 for r in rows if r["classification_confidence"] == "unmapped")
    mapped = len(rows) - unmapped

    rows_inserted = 0
    if supabase_client is not None and rows:
        # Chunk to stay under PostgREST's row-count cap and to limit blast
        # radius on partial failures (one bad chunk doesn't lose the rest).
        for offset in range(0, len(rows), chunk_size):
            batch = rows[offset:offset + chunk_size]
            try:
                response = supabase_client.table("raw_records").insert(batch).execute()
            except Exception as exc:  # noqa: BLE001 — surface with context
                logger.error(
                    "tally ingest: insert failed for user=%s sha256=%s "
                    "chunk_offset=%d chunk_size=%d: %s",
                    user_id, file_sha256, offset, len(batch), exc,
                )
                raise
            inserted = getattr(response, "data", None) or []
            rows_inserted += len(inserted)

    logger.info(
        "tally ingest: sha256=%s parsed=%d mapped=%d unmapped=%d inserted=%d "
        "chunks=%d",
        file_sha256, len(rows), mapped, unmapped, rows_inserted,
        (len(rows) + chunk_size - 1) // chunk_size if rows else 0,
    )
    return IngestSummary(
        file_sha256=file_sha256,
        lines_parsed=len(rows),
        lines_mapped=mapped,
        lines_unmapped=unmapped,
        rows_inserted=rows_inserted,
        rows=rows,
    )
