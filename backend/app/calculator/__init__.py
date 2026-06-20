"""
``app.calculator`` — deterministic, Decimal-based emission calculation spine.

Pure Python (principle #1: LLMs never compute numbers). Factors are looked up
strictly and raise :class:`FactorNotFoundError` on miss (principle #2). Every
result carries factor lineage and can be signed into a PROV-O graph via
:func:`sign_result` (principle #3).
"""

from __future__ import annotations

from app.calculator.engine import (
    scope1_stationary_combustion,
    scope2_location_based,
    scope3_category,
)
from app.calculator.provenance import (
    persist_calculation,
    result_to_prov_input,
    sign_result,
)
from app.calculator.results import (
    DEFAULT_GWP_SET,
    GWP_SETS,
    CalculationResult,
    FactorNotFoundError,
)

__all__ = [
    "CalculationResult",
    "FactorNotFoundError",
    "GWP_SETS",
    "DEFAULT_GWP_SET",
    "scope1_stationary_combustion",
    "scope2_location_based",
    "scope3_category",
    "result_to_prov_input",
    "sign_result",
    "persist_calculation",
]
