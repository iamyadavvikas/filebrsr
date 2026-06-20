"""Multi-jurisdiction Scope 3 report profiles.

Ported from CarbonTrace ``reporting.profiles``. A single jurisdiction-neutral
provenance core (GHG Protocol + ISSB/IFRS S2; upstream mining is Scope 3
Category 1; functional unit = kgCO2e per kWh, cradle-to-gate) is mapped into
different regulatory framings via a pluggable :class:`ReportProfile`.

Supply-chain stage -> regulatory life-cycle stage:

==============  ============================================
supply stage    life-cycle stage (EU Battery Reg style)
==============  ============================================
ore             raw material acquisition & pre-processing
concentrate     raw material acquisition & pre-processing
smelter         main production
battery         main production
==============  ============================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.assurance.factors import STAGE_ORDER, Stage
from app.assurance.schemas import Scope3Report, StageBreakdown

_LIFECYCLE_STAGE = {
    Stage.ORE.value: "Raw material acquisition & pre-processing",
    Stage.CONCENTRATE.value: "Raw material acquisition & pre-processing",
    Stage.SMELTER.value: "Main production",
    Stage.BATTERY.value: "Main production",
}


@dataclass(frozen=True)
class ReportProfile:
    """A regulatory framing for the universal provenance data."""

    code: str
    name: str
    region_focus: str
    framework: str
    default_region: str
    notes: list[str] = field(default_factory=list)


PROFILES: dict[str, ReportProfile] = {
    "eu": ReportProfile(
        code="eu",
        name="EU Battery Regulation",
        region_focus="European Union",
        framework="Regulation (EU) 2023/1542 — Carbon Footprint of Batteries; Battery Passport",
        default_region="EU",
        notes=[
            "Functional unit per Annex II: kgCO2e per kWh of total energy delivered "
            "over service life.",
            "Carbon footprint declaration covers raw material acquisition & pre-processing, "
            "main production, distribution and end-of-life (recycling stage = stub here).",
            "Feeds the Digital Battery Passport mandatory from February 2027.",
            "Imported metals may also fall under CBAM embedded-emissions reporting.",
        ],
    ),
    "us": ReportProfile(
        code="us",
        name="US — California SB 253 / IRA critical minerals",
        region_focus="United States",
        framework="California SB 253 (Scope 1/2/3); IRA §45X/§30D critical-mineral provenance (FEOC)",
        default_region="US",
        notes=[
            "Upstream mineral emissions reported as GHG Protocol Scope 3 Category 1.",
            "IRA §30D/§45X require provenance of critical minerals (Foreign Entity of "
            "Concern screening) — satisfied by the wasDerivedFrom provenance chain.",
            "Emission factors aligned to Argonne GREET where applicable.",
        ],
    ),
    "au": ReportProfile(
        code="au",
        name="Australia — ASRS / AASB S2",
        region_focus="Australia",
        framework="AASB S2 (ISSB-aligned) climate disclosures; NGER factors",
        default_region="AU",
        notes=[
            "AASB S2 directly adopts ISSB IFRS S2; Scope 3 value-chain emissions disclosed.",
            "Emission factors aligned to the National Greenhouse and Energy Reporting "
            "(NGER) scheme.",
        ],
    ),
    "in": ReportProfile(
        code="in",
        name="India — BRSR Core",
        region_focus="India",
        framework="SEBI BRSR Core value-chain assurance; CBAM export exposure",
        default_region="IN",
        notes=[
            "BRSR Core requires value-chain (Scope 3) intensity disclosure with assurance.",
            "Exporters of metals/batteries to the EU face CBAM embedded-emissions reporting.",
        ],
    ),
}

DEFAULT_PROFILE = "eu"


@dataclass
class ReportRow:
    """One ledger row reduced to the fields a report needs."""

    stage: str
    emissions_kg_co2e: Decimal
    energy_kwh: Decimal | None
    factor_source: str


def build_report(profile_code: str, rows: list[ReportRow]) -> Scope3Report:
    """Aggregate ledger rows into a Scope 3 report under ``profile_code``."""
    profile = PROFILES.get(profile_code.lower())
    if profile is None:
        raise KeyError(f"unknown report profile '{profile_code}'")

    totals: dict[str, Decimal] = {s: Decimal(0) for s in STAGE_ORDER}
    capacity = Decimal(0)
    sources: list[str] = []
    for row in rows:
        totals[row.stage] = totals.get(row.stage, Decimal(0)) + row.emissions_kg_co2e
        if row.energy_kwh:
            capacity += row.energy_kwh
        if row.factor_source and row.factor_source not in sources:
            sources.append(row.factor_source)

    total_emissions = sum(totals.values(), Decimal(0))
    intensity = (
        (total_emissions / capacity).quantize(Decimal("0.0001")) if capacity > 0 else None
    )

    stages = [
        StageBreakdown(
            stage=stage,
            regulatory_stage=_LIFECYCLE_STAGE.get(stage, "Other"),
            emissions_kg_co2e=totals[stage],
            share_pct=round(float(totals[stage] / total_emissions * 100), 2)
            if total_emissions > 0
            else 0.0,
        )
        for stage in STAGE_ORDER
        if totals.get(stage)
    ]

    return Scope3Report(
        profile=profile.code,
        profile_name=profile.name,
        region_focus=profile.region_focus,
        framework=profile.framework,
        total_emissions_kg_co2e=total_emissions,
        battery_capacity_kwh=capacity,
        carbon_intensity_kg_co2e_per_kwh=intensity,
        record_count=len(rows),
        stages=stages,
        regulatory_notes=profile.notes,
        factor_sources=sources,
        generated_at=datetime.now(UTC),
    )
