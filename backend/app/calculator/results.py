"""
Result types and shared constants for the deterministic emissions calculator.

This package (``app.calculator``) is the **pure-Python** calculation spine
mandated by architectural principle #1: LLMs never compute numbers. Every
function here is deterministic, uses :class:`~decimal.Decimal` (never float),
raises :class:`FactorNotFoundError` on a missing factor (never substitutes),
and returns a :class:`CalculationResult` carrying full factor lineage so the
provenance layer (:mod:`app.prov`) can sign it.

The legacy ``app.carbon_calculator`` float-based helpers remain for existing
router endpoints; new work should target this package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.factors_india import FactorNotFound


class FactorNotFoundError(FactorNotFound):
    """No emission factor exists for the requested inputs.

    Subclasses :class:`app.factors_india.FactorNotFound` so callers can catch
    either name. Raising (never silently substituting a default) is a
    non-negotiable: principle #2, "Emission factors are sacred."
    """


# Global Warming Potentials (GWP-100). Kept at the AR5 values currently used
# by app.carbon_calculator so this package does not silently change any
# disclosed number. Switching the default to IPCC AR6 is an
# [APPROVAL NEEDED] decision (charter: "Changes to emission factor sources or
# default versions") and is therefore offered but NOT defaulted.
GWP_SETS: dict[str, dict[str, Decimal]] = {
    "AR5": {"CO2": Decimal("1"), "CH4": Decimal("28"), "N2O": Decimal("265")},
    # AR6 GWP-100 (IPCC, 2021). Do not make default without founder approval.
    "AR6": {"CO2": Decimal("1"), "CH4": Decimal("27.9"), "N2O": Decimal("273")},
}
DEFAULT_GWP_SET = "AR5"

# Quantum for emission results — 6 dp of a tonne (1 gram) is ample precision.
_EMISSION_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class CalculationResult:
    """Deterministic output of one emission calculation.

    Mirrors the charter's ``CalculationResult`` contract and feeds directly
    into :class:`app.prov.CalculationProvenanceInput`.
    """

    scope: int
    category: str
    method: str
    value: Decimal
    unit: str
    factor_id: str
    factor_version: str
    factor_source: str | None = None
    factor_citation: str | None = None
    input_record_ids: list[str] = field(default_factory=list)
    uncertainty: dict[str, Any] | None = None
    agent_run_id: str | None = None
    calculation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def to_decimal(value: Any, *, field_name: str = "quantity") -> Decimal:
    """Coerce ``value`` to Decimal via str (avoids binary-float artefacts)."""
    try:
        return Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"{field_name} is not a valid number: {value!r}") from exc


def require_non_negative(value: Decimal, *, field_name: str = "quantity") -> Decimal:
    """Raise ValueError for negative inputs; zero is allowed (returns 0 result)."""
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative, got {value}")
    return value


def quantize_emissions(value: Decimal) -> Decimal:
    """Quantize a tCO2e value to the standard emission quantum."""
    return value.quantize(_EMISSION_QUANTUM)
