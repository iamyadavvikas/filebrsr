"""Pydantic wire/proof schemas for the Carbon Assurance subsystem.

Ported from CarbonTrace ``carbontrace_core.schemas`` +
``reporting.profiles``. These are the contract between the in-memory ledger
(producer), the API, and the offline verifier (consumer).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.assurance.factors import Stage


class EmissionRecord(BaseModel):
    """The canonical payload that gets hashed into the Merkle tree."""

    model_config = ConfigDict(extra="forbid")

    batch_id: str
    parent_batch_id: str | None = None
    stage: Stage
    supplier_id: str
    region: str
    material: str
    quantity_kg: Decimal = Field(gt=0)
    emissions_kg_co2e: Decimal = Field(ge=0)
    energy_kwh: Decimal | None = Field(default=None, ge=0)
    emission_factor_source: str
    emission_factor_uncertainty: Decimal | None = Field(default=None, ge=0)
    occurred_at: datetime


class ProofStepModel(BaseModel):
    """Serializable form of a Merkle audit-path step."""

    side: str = Field(pattern="^[LR]$")
    hash: str


class SignedRoot(BaseModel):
    """A Merkle checkpoint root signed by the server key."""

    root: str
    size: int = Field(ge=1)
    algorithm: str = "sha256"
    signature: str
    server_public_key: str
    created_at: datetime


class ProofBundle(BaseModel):
    """Everything needed to verify one record's integrity OFFLINE."""

    record: EmissionRecord
    leaf_index: int = Field(ge=0)
    leaf_hash: str
    inclusion_proof: list[ProofStepModel]
    signed_root: SignedRoot
    supplier_public_key: str | None = None
    supplier_signature: str | None = None


class LedgerEntry(BaseModel):
    """A read view of one append-only ledger row."""

    leaf_index: int
    stage: str
    batch_id: str
    parent_batch_id: str | None
    region: str
    material: str
    emissions_kg_co2e: Decimal
    record_hash: str
    supplier_id: str


class StageBreakdown(BaseModel):
    """Emissions attributable to one supply-chain stage."""

    stage: str
    regulatory_stage: str
    emissions_kg_co2e: Decimal
    share_pct: float


class Scope3Report(BaseModel):
    """Auditor-facing cradle-to-gate Scope 3 report for one regulatory profile."""

    profile: str
    profile_name: str
    region_focus: str
    framework: str
    ghg_scope: str = "Scope 3, Category 1 (Purchased goods & services)"
    boundary: str = "Cradle-to-gate (raw material acquisition through main production)"
    functional_unit: str = "kgCO2e per kWh of battery capacity"
    total_emissions_kg_co2e: Decimal
    battery_capacity_kwh: Decimal
    carbon_intensity_kg_co2e_per_kwh: Decimal | None
    record_count: int
    stages: list[StageBreakdown]
    regulatory_notes: list[str]
    factor_sources: list[str]
    generated_at: datetime


def to_jsonable(model: BaseModel) -> dict[str, Any]:
    """Dump a model to a JSON-safe dict (Decimals -> str, datetimes -> ISO)."""
    return model.model_dump(mode="json")
