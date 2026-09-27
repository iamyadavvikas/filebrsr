"""Climate scenario + target API (IFRS S2 resilience, SBTi math).

All endpoints are pure compute (no DB, no auth) — the same posture as the
BRSR framework/registry surfaces. Assumption provenance (illustrative
defaults vs user-provided scenarios) is returned on every response.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import climate_scenarios as cs

router = APIRouter(prefix="/api/climate", tags=["climate-scenarios"])


class TransitionIn(BaseModel):
    emissions_tco2e: float = Field(ge=0)
    revenue: float = Field(gt=0)
    year: int = 2030
    scenario: Any = None


class PhysicalIn(BaseModel):
    assets: list[dict[str, Any]] = []


class BudgetIn(BaseModel):
    base_year_emissions: float = Field(gt=0)
    current_emissions: float = Field(ge=0)
    base_year: int
    current_year: int
    target_year: int = 2050
    remaining_budget_tco2e: float | None = Field(None, gt=0)


class SBTIIn(BaseModel):
    base_emissions: float = Field(gt=0)
    base_year: int
    target_year: int = 2030
    ambition: str = "1.5C"
    stated_target_pct: float | None = None


class ResilienceIn(BaseModel):
    emissions_tco2e: float = Field(ge=0)
    revenue: float = Field(gt=0)
    assets: list[dict[str, Any]] = []
    scenario: Any = None
    year: int = 2030


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/scenarios")
async def scenarios() -> dict:
    """Named pathways with provenance (defaults flagged)."""
    return {"horizons": list(cs.HORIZONS), "scenarios": cs.list_scenarios()}


@router.post("/transition-exposure")
async def transition_exposure(body: TransitionIn) -> dict:
    return _safe(cs.transition_exposure, body.emissions_tco2e, body.revenue, body.year, body.scenario)


@router.post("/physical-screen")
async def physical_screen(body: PhysicalIn) -> dict:
    return _safe(cs.physical_screen, body.assets)


@router.post("/budget-alignment")
async def budget_alignment(body: BudgetIn) -> dict:
    return _safe(
        cs.budget_alignment,
        body.base_year_emissions, body.current_emissions,
        body.base_year, body.current_year, body.target_year,
        body.remaining_budget_tco2e,
    )


@router.post("/sbti-target")
async def sbti_target(body: SBTIIn) -> dict:
    return _safe(
        cs.sbti_target,
        body.base_emissions, body.base_year, body.target_year,
        body.ambition, body.stated_target_pct,
    )


@router.post("/resilience")
async def resilience(body: ResilienceIn) -> dict:
    return _safe(
        cs.resilience_summary,
        body.emissions_tco2e, body.revenue, body.assets, body.scenario, body.year,
    )
