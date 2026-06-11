"""
Tally connector HTTP endpoints (Slice 1).

Single public endpoint today: ``POST /api/tally/ingest`` — accepts a Tally
voucher XML export, parses + classifies + persists to ``raw_records``, and
returns an :class:`app.tally.IngestSummary`.

Auth: shared-bearer pattern the rest of ``/api/*`` already uses
(``Authorization: Bearer <SUPABASE_SERVICE_KEY>``). The Next.js layer
authenticates the user, verifies ownership of ``user_id``, and forwards
the request — we trust ``user_id`` from the multipart form rather than
re-extracting it from a JWT.

Future endpoints (slice 2+):
  * ``GET  /api/tally/unmapped``           — paginated list of rows that
    need human classification (drives the curator queue UI)
  * ``POST /api/tally/unmapped/{id}``      — accept a curator's HSN/scope
    correction and feed it back into the LLM training corpus
  * ``POST /api/tally/push``               — Tally HTTP-XML interface
    target (Tally pushes vouchers to us; XML body, no multipart)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.config import get_settings
from app.tally import ingest_tally_xml

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tally", tags=["tally"])
settings = get_settings()

# Conservative upload cap. A 50k-line Tally daybook XML is ~25 MB raw; 50 MB
# leaves headroom for the verbose exports while preventing accidental DoS
# from a runaway upload.
_MAX_BYTES = 50 * 1024 * 1024


def _check_auth(authorization: str) -> None:
    expected = f"Bearer {settings.SUPABASE_SERVICE_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    chunk_size: int = Form(1000),
    authorization: str = Header(...),
) -> dict:
    """Parse a Tally XML voucher export and write line items into
    ``raw_records``. Returns the :class:`IngestSummary` as JSON.

    Returns 401 on bad bearer, 400 on bad XML or oversized upload, 500 if
    Supabase rejects the insert (e.g. RLS, FK, dedup unique-key violation).
    """
    _check_auth(authorization)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"upload exceeds {_MAX_BYTES // (1024 * 1024)} MB cap",
        )

    # Lazy-import the supabase admin client so unit tests that exercise the
    # endpoint shape without a real Supabase env can monkeypatch this name.
    from app.main import get_supabase_admin  # noqa: PLC0415 — see comment

    try:
        summary = ingest_tally_xml(
            xml_bytes=content,
            user_id=user_id,
            supabase_client=get_supabase_admin(),
            chunk_size=chunk_size,
        )
    except ValueError as exc:  # invalid XML
        logger.warning("tally ingest: bad xml from user=%s: %s", user_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — bubble to client with context
        logger.error("tally ingest: persistence failed for user=%s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="ingest failed") from exc

    return {
        "status": "ok",
        "file_sha256": summary.file_sha256,
        "lines_parsed": summary.lines_parsed,
        "lines_mapped": summary.lines_mapped,
        "lines_unmapped": summary.lines_unmapped,
        "rows_inserted": summary.rows_inserted,
    }
