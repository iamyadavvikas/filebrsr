"""Data-connector APIs: utility-bill ingestion (more connectors plug in here).

v1 accepts OCR/plain text (produce it with ``app.ocr`` for scans, or paste
from a bill portal) and returns parsed activity plus a Scope 2 estimate
priced through the versioned grid factor. Pure compute: no DB, no auth —
same posture as the framework/registry surfaces.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import energy_bill

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


class BillParseIn(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    jurisdiction: str = "IN"
    grid_region: str | None = None
    price: bool = True


@router.post("/utility-bill")
async def parse_utility_bill(body: BillParseIn) -> dict[str, Any]:
    """Parse bill text; optionally price the kWh through the grid factor."""
    parsed = energy_bill.parse_bill_text(body.text)
    out: dict[str, Any] = {"parsed": parsed}
    if body.price:
        if parsed.get("kwh") is None:
            out["scope2"] = None
            out["warning"] = "no kWh figure parsed — scope 2 not estimated"
        else:
            try:
                out["scope2"] = energy_bill.bill_to_scope2(
                    parsed, jurisdiction=body.jurisdiction, grid_region=body.grid_region
                )
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            except Exception as exc:  # noqa: BLE001 - factor lookup failures surface as 422
                raise HTTPException(422, f"grid factor unavailable: {exc}") from exc
    return out
