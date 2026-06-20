"""Carbon Assurance API.

Exposes the tamper-evident Scope 3 provenance subsystem:

* ``GET /api/assurance/profiles``            — supported regulatory report profiles
* ``GET /api/assurance/report``              — Scope 3 report for a profile/region
* ``GET /api/assurance/ledger``              — append-only ledger entries
* ``GET /api/assurance/provenance``          — W3C PROV-JSON + simplified graph
* ``GET /api/assurance/bundle/{leaf_index}`` — offline-verifiable proof bundle
* ``GET /api/assurance/verify/{leaf_index}`` — server-side bundle verification

The ledger is deterministic per ``(region, packs, ore_kg)`` and self-contained
(no database), so these endpoints work even if the rest of the platform's data
stores are unavailable.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, Query

from app.assurance import ledger as ledger_mod
from app.assurance import provenance as prov_mod
from app.assurance.factors import REGION_LABELS
from app.assurance.profiles import DEFAULT_PROFILE, PROFILES, build_report
from app.assurance.schemas import to_jsonable
from app.assurance.verify_cli import verify_bundle

router = APIRouter(prefix="/api/assurance", tags=["assurance"])

_MAX_PACKS = 25


def _resolve_region(profile_code: str, region: str | None) -> str:
    profile = PROFILES.get(profile_code.lower())
    if profile is None:
        raise HTTPException(404, f"unknown profile '{profile_code}'")
    chosen = (region or profile.default_region).upper()
    if chosen not in REGION_LABELS:
        raise HTTPException(400, f"unsupported region '{chosen}'")
    return chosen


def _validate_ore(ore_kg: str) -> str:
    try:
        if Decimal(ore_kg) <= 0:
            raise ValueError
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(400, "ore_kg must be a positive number") from exc
    return ore_kg


@router.get("/profiles")
def list_profiles() -> dict:
    """List the supported regulatory report profiles and region labels."""
    return {
        "profiles": [
            {
                "code": p.code,
                "name": p.name,
                "region_focus": p.region_focus,
                "framework": p.framework,
                "default_region": p.default_region,
            }
            for p in PROFILES.values()
        ],
        "regions": REGION_LABELS,
        "default_profile": DEFAULT_PROFILE,
    }


@router.get("/report")
def get_report(
    profile: str = Query(DEFAULT_PROFILE),
    region: str | None = Query(None),
    packs: int = Query(3, ge=1, le=_MAX_PACKS),
    ore_kg: str = Query("20000"),
) -> dict:
    """Build a cradle-to-gate Scope 3 report for the given regulatory profile."""
    chosen = _resolve_region(profile, region)
    _validate_ore(ore_kg)
    led = ledger_mod.build_ledger(chosen, packs, ore_kg)
    report = build_report(profile, ledger_mod.report_rows(led))
    return to_jsonable(report)


@router.get("/ledger")
def get_ledger(
    region: str = Query("EU"),
    packs: int = Query(3, ge=1, le=_MAX_PACKS),
    ore_kg: str = Query("20000"),
) -> dict:
    """Return the append-only ledger entries (in Merkle-leaf order)."""
    if region.upper() not in REGION_LABELS:
        raise HTTPException(400, f"unsupported region '{region}'")
    _validate_ore(ore_kg)
    led = ledger_mod.build_ledger(region, packs, ore_kg)
    return {
        "region": led.region,
        "root": led.root_hex,
        "size": led.signed_root.size,
        "entries": [to_jsonable(e) for e in ledger_mod.ledger_entries(led)],
    }


@router.get("/provenance")
def get_provenance(
    region: str = Query("EU"),
    packs: int = Query(3, ge=1, le=_MAX_PACKS),
    ore_kg: str = Query("20000"),
    batch_id: str | None = Query(None),
) -> dict:
    """Return the W3C PROV-JSON document, a simplified graph, and quality stats."""
    if region.upper() not in REGION_LABELS:
        raise HTTPException(400, f"unsupported region '{region}'")
    _validate_ore(ore_kg)
    led = ledger_mod.build_ledger(region, packs, ore_kg)
    stats = prov_mod.provenance_stats(led.entries)
    return {
        "prov": prov_mod.build_prov_json(led.entries, batch_id=batch_id),
        "graph": prov_mod.build_graph(led.entries, batch_id=batch_id),
        "stats": {
            "batches": stats.batches,
            "derived_edges": stats.derived_edges,
            "roots": stats.roots,
            "dangling_parents": stats.dangling_parents,
            "completeness_ratio": stats.completeness_ratio,
        },
    }


@router.get("/bundle/{leaf_index}")
def get_bundle(
    leaf_index: int,
    region: str = Query("EU"),
    packs: int = Query(3, ge=1, le=_MAX_PACKS),
    ore_kg: str = Query("20000"),
) -> dict:
    """Return a self-contained, offline-verifiable proof bundle for one entry."""
    if region.upper() not in REGION_LABELS:
        raise HTTPException(400, f"unsupported region '{region}'")
    _validate_ore(ore_kg)
    led = ledger_mod.build_ledger(region, packs, ore_kg)
    try:
        bundle = ledger_mod.proof_bundle(led, leaf_index)
    except IndexError as exc:
        raise HTTPException(404, str(exc)) from exc
    return to_jsonable(bundle)


@router.get("/verify/{leaf_index}")
def verify_entry(
    leaf_index: int,
    region: str = Query("EU"),
    packs: int = Query(3, ge=1, le=_MAX_PACKS),
    ore_kg: str = Query("20000"),
) -> dict:
    """Server-side verification of one entry (same logic as the offline CLI)."""
    if region.upper() not in REGION_LABELS:
        raise HTTPException(400, f"unsupported region '{region}'")
    _validate_ore(ore_kg)
    led = ledger_mod.build_ledger(region, packs, ore_kg)
    try:
        bundle = ledger_mod.proof_bundle(led, leaf_index)
    except IndexError as exc:
        raise HTTPException(404, str(exc)) from exc
    return verify_bundle(bundle).as_dict()
