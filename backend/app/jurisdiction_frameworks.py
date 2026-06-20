"""
Jurisdiction-aware regulatory framework mapping.

Maps the core emissions/ESG datapoints FileBRSR computes to the disclosure
obligations that apply in each supported jurisdiction:

- ``IN`` (India): SEBI BRSR Core, the Carbon Credit Trading Scheme (CCTS),
  and CBAM reporting for EU-bound exporters.
- ``AU`` (Australia): AASB S2 (the Australian adoption of IFRS S2 Climate),
  NGER (National Greenhouse and Energy Reporting), the Safeguard Mechanism,
  and Climate Active carbon-neutral certification.

This is intentionally separate from :mod:`app.cross_framework_mapping` (which
bridges BRSR ↔ ESRS ↔ GRI ↔ TCFD ↔ ISSB at the *disclosure-line* level). Here
we answer a narrower, operational question: "for this computed datapoint, in
this jurisdiction, which regulation governs it and what is the citing clause?"
so a provenance graph / verify bundle can be tagged with the right references.

All references are curated and may be approximate; ``_placeholder`` flags the
ones a domain reviewer still needs to confirm against the primary source.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FrameworkRef:
    """One regulatory reference for a datapoint in a jurisdiction."""

    framework: str          # e.g. "AASB S2", "NGER", "BRSR Core", "CCTS"
    ref: str                # clause / table / indicator identifier
    label: str              # human description
    citation_url: str
    placeholder: bool = False


@dataclass(frozen=True)
class DatapointFrameworks:
    """All applicable framework references for a datapoint, by jurisdiction."""

    datapoint: str          # stable key, e.g. "scope2_location_based"
    description: str
    applicable_jurisdictions: tuple[str, ...]
    refs: dict[str, tuple[FrameworkRef, ...]] = field(default_factory=dict)


# ─── Reference building blocks ─────────────────────────────────────────────

_AASB_S2_URL = "https://standards.aasb.gov.au/aasb-s2"
_NGER_URL = "https://www.cleanenergyregulator.gov.au/NGER"
_SAFEGUARD_URL = "https://www.cleanenergyregulator.gov.au/NGER/The-safeguard-mechanism"
_CLIMATE_ACTIVE_URL = "https://www.climateactive.org.au/"
_BRSR_CORE_URL = "https://www.sebi.gov.in/legal/circulars/jul-2023/brsr-core-framework-for-assurance-and-esg-disclosures-for-value-chain_73854.html"
_CCTS_URL = "https://beeindia.gov.in/en/programmes/carbon-credit-trading-scheme-ccts"
_CBAM_URL = "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"


def _au_scope_refs(scope_label: str, *, safeguard: bool) -> tuple[FrameworkRef, ...]:
    refs = [
        FrameworkRef(
            framework="AASB S2",
            ref="AASB S2 ¶29(a)",
            label=f"{scope_label} gross GHG emissions (tCO2-e)",
            citation_url=_AASB_S2_URL,
            placeholder=True,
        ),
        FrameworkRef(
            framework="NGER",
            ref="NGER (Measurement) Determination",
            label=f"{scope_label} emissions, NGER measurement methods",
            citation_url=_NGER_URL,
            placeholder=True,
        ),
    ]
    if safeguard:
        refs.append(
            FrameworkRef(
                framework="Safeguard Mechanism",
                ref="Safeguard covered emissions",
                label="Covered Scope 1 emissions vs facility baseline",
                citation_url=_SAFEGUARD_URL,
                placeholder=True,
            )
        )
    refs.append(
        FrameworkRef(
            framework="Climate Active",
            ref="Climate Active carbon inventory",
            label=f"{scope_label} in carbon-neutral inventory",
            citation_url=_CLIMATE_ACTIVE_URL,
            placeholder=True,
        )
    )
    return tuple(refs)


def _in_scope_refs(scope_label: str, *, cbam: bool) -> tuple[FrameworkRef, ...]:
    refs = [
        FrameworkRef(
            framework="BRSR Core",
            ref="BRSR Core — GHG emissions intensity",
            label=f"{scope_label} GHG emissions (BRSR Core attribute)",
            citation_url=_BRSR_CORE_URL,
            placeholder=True,
        ),
        FrameworkRef(
            framework="CCTS",
            ref="CCTS GHG emission intensity",
            label="Compliance emission intensity under Carbon Credit Trading Scheme",
            citation_url=_CCTS_URL,
            placeholder=True,
        ),
    ]
    if cbam:
        refs.append(
            FrameworkRef(
                framework="CBAM",
                ref="CBAM embedded emissions",
                label="Embedded emissions for EU-bound goods (CBAM transitional)",
                citation_url=_CBAM_URL,
                placeholder=True,
            )
        )
    return tuple(refs)


# ─── Master datapoint → framework registry ─────────────────────────────────

_REGISTRY: dict[str, DatapointFrameworks] = {
    "scope1_stationary_combustion": DatapointFrameworks(
        datapoint="scope1_stationary_combustion",
        description="Scope 1 direct emissions from stationary fuel combustion",
        applicable_jurisdictions=("IN", "AU"),
        refs={
            "AU": _au_scope_refs("Scope 1", safeguard=True),
            "IN": _in_scope_refs("Scope 1", cbam=True),
        },
    ),
    "scope2_location_based": DatapointFrameworks(
        datapoint="scope2_location_based",
        description="Scope 2 indirect emissions from purchased electricity (location-based)",
        applicable_jurisdictions=("IN", "AU"),
        refs={
            "AU": _au_scope_refs("Scope 2", safeguard=False),
            "IN": _in_scope_refs("Scope 2", cbam=True),
        },
    ),
    "scope3_category": DatapointFrameworks(
        datapoint="scope3_category",
        description="Scope 3 value-chain emissions (category-specific)",
        applicable_jurisdictions=("IN", "AU"),
        refs={
            "AU": _au_scope_refs("Scope 3", safeguard=False),
            "IN": _in_scope_refs("Scope 3", cbam=False),
        },
    ),
}


# ─── Public API ────────────────────────────────────────────────────────────

_SUPPORTED_JURISDICTIONS = frozenset({"IN", "AU"})


class FrameworkNotFound(LookupError):
    """No framework mapping for the requested datapoint / jurisdiction."""


def supported_jurisdictions() -> frozenset[str]:
    return _SUPPORTED_JURISDICTIONS


def get_frameworks(datapoint: str, jurisdiction: str) -> tuple[FrameworkRef, ...]:
    """Return the framework references for ``datapoint`` in ``jurisdiction``.

    Raises :class:`FrameworkNotFound` if the datapoint is unknown or the
    jurisdiction does not apply to it.
    """
    if jurisdiction not in _SUPPORTED_JURISDICTIONS:
        raise FrameworkNotFound(
            f"unsupported jurisdiction {jurisdiction!r}; "
            f"supported: {sorted(_SUPPORTED_JURISDICTIONS)}"
        )
    entry = _REGISTRY.get(datapoint)
    if entry is None:
        raise FrameworkNotFound(
            f"unknown datapoint {datapoint!r}; known: {sorted(_REGISTRY)}"
        )
    refs = entry.refs.get(jurisdiction)
    if not refs:
        raise FrameworkNotFound(
            f"datapoint {datapoint!r} has no mapping for jurisdiction "
            f"{jurisdiction!r}; applies to {entry.applicable_jurisdictions}"
        )
    return refs


def framework_tags(datapoint: str, jurisdiction: str) -> list[str]:
    """Flat list of ``"<framework>:<ref>"`` tags for provenance/ledger payloads.

    Returns an empty list (rather than raising) when no mapping exists, so
    callers can attach tags best-effort without guarding every call.
    """
    try:
        refs = get_frameworks(datapoint, jurisdiction)
    except FrameworkNotFound:
        return []
    return [f"{r.framework}:{r.ref}" for r in refs]


def list_datapoints() -> tuple[str, ...]:
    return tuple(_REGISTRY)
