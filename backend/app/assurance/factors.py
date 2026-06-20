"""Supply-chain stage model and per-region emission factors.

Ported from CarbonTrace (``carbontrace_generator.factors`` +
``carbontrace_core.schemas.Stage``). Models the
ore -> concentrate -> smelter -> battery mining-to-battery chain that underlies
the multi-jurisdiction Scope 3 report.

Factor units:
* ore / concentrate / smelter: kgCO2e per kg of material handled at that stage.
* battery: kgCO2e per kWh of cell/pack capacity produced.

Values are synthetic and rounded for demonstration; loosely aligned to public
LCA literature (ecoinvent, Argonne GREET, IEA, NGER, CEA). Each factor carries a
relative uncertainty because LCA data uncertainty is a first-class concern in
real ESG reporting — the report surfaces it rather than hiding it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Stage(StrEnum):
    """A node in the ore -> concentrate -> smelter -> battery supply chain."""

    ORE = "ore"
    CONCENTRATE = "concentrate"
    SMELTER = "smelter"
    BATTERY = "battery"


STAGE_ORDER: list[str] = [
    Stage.ORE.value,
    Stage.CONCENTRATE.value,
    Stage.SMELTER.value,
    Stage.BATTERY.value,
]

# Human material label per stage (illustrative lithium chain).
MATERIALS: dict[str, str] = {
    "ore": "spodumene ore",
    "concentrate": "lithium concentrate",
    "smelter": "battery-grade lithium",
    "battery": "Li-ion battery pack",
}

# The transformation activity that produces each batch (for the PROV graph).
ACTIVITY_LABEL: dict[str, str] = {
    "ore": "extraction",
    "concentrate": "beneficiation",
    "smelter": "smelting",
    "battery": "cell-assembly",
}


@dataclass(frozen=True)
class Factor:
    """An emission factor with its provenance and relative uncertainty."""

    value: Decimal  # kgCO2e per functional unit (per kg or per kWh)
    uncertainty: Decimal  # relative, e.g. 0.25 == ±25%
    source: str


# Region-specific factor source labels (the report cites these per profile).
_SOURCE_BY_REGION = {
    "EU": "ecoinvent 3.10 (illustrative)",
    "US": "Argonne GREET 2024 (illustrative)",
    "AU": "NGER 2024 factors (illustrative)",
    "IN": "CEA/India GHG Program (illustrative)",
}


def factors_for_region(region: str) -> dict[str, Factor]:
    """Return the per-stage factor set for a region (falls back to EU)."""
    source = _SOURCE_BY_REGION.get(region.upper(), _SOURCE_BY_REGION["EU"])
    return {
        "ore": Factor(Decimal("0.02"), Decimal("0.30"), source),
        "concentrate": Factor(Decimal("0.45"), Decimal("0.25"), source),
        "smelter": Factor(Decimal("9.0"), Decimal("0.20"), source),
        "battery": Factor(Decimal("42.0"), Decimal("0.18"), source),
    }


# Mass yield from one stage to the next (fraction of input mass that proceeds).
MASS_YIELD = {
    "ore_to_concentrate": Decimal("0.05"),  # ~5% concentrate from ore
    "concentrate_to_metal": Decimal("0.90"),  # ~90% metal recovery in smelting
}

# kWh of battery capacity produced per kg of refined metal (illustrative).
KWH_PER_KG_METAL = Decimal("1.6")

# Region code -> human label, for the UI selector.
REGION_LABELS = {
    "EU": "European Union",
    "US": "United States",
    "AU": "Australia",
    "IN": "India",
}
