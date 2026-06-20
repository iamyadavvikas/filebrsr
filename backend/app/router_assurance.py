"""Carbon Assurance API (persisted, supplier-signed).

Exposes the tamper-evident Scope 3 provenance subsystem, backed by Supabase
(migration v22). Suppliers submit Ed25519-signed emission records; the backend
verifies each signature, appends it as an RFC 6962 Merkle leaf and checkpoints a
KMS-signed tree head (see :mod:`app.assurance.store`).

* ``GET  /api/assurance/profiles``           — supported regulatory report profiles
* ``POST /api/assurance/submissions``        — ingest a supplier-signed record
* ``POST /api/assurance/demo/seed``          — seed a real signed supply chain (demo)
* ``GET  /api/assurance/report``             — Scope 3 report from persisted records
* ``GET  /api/assurance/ledger``             — append-only ledger entries
* ``GET  /api/assurance/provenance``         — W3C PROV-JSON + simplified graph
* ``GET  /api/assurance/bundle/{leaf_index}``— offline-verifiable proof bundle
* ``GET  /api/assurance/verify/{leaf_index}``— server-side bundle verification

All data endpoints are org-scoped: the caller's organization is resolved from
the bearer token, so each tenant sees only its own ledger.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Header, HTTPException, Query

from app.assurance import crypto, store
from app.assurance import provenance as prov_mod
from app.assurance.factors import REGION_LABELS
from app.assurance.ledger import build_chain
from app.assurance.profiles import DEFAULT_PROFILE, PROFILES, build_report
from app.assurance.schemas import SignedSubmission, to_jsonable
from app.assurance.verify_cli import verify_bundle
from app.config import get_settings

router = APIRouter(prefix="/api/assurance", tags=["assurance"])
settings = get_settings()

_MAX_PACKS = 25


def get_supabase_admin():
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _ensure_personal_org(sb: object, user_id: str, profile: dict) -> str:
    """Provision (or adopt) a personal org for a user that has none, and link
    their profile to it.

    Assurance rows are org-scoped via an FK to ``organizations(id)``, so every
    caller must belong to exactly one org. Most platform users were never put
    through org onboarding (``profiles.org_id`` is null), which previously made
    every assurance call 403 and surfaced as "API offline". This self-heals by
    giving the user a personal org on first use, mirroring ``POST /api/org``.
    """
    existing = (
        sb.table("organizations").select("id").eq("created_by", user_id).limit(1).execute()
    )
    if existing.data:
        org_id = existing.data[0]["id"]
    else:
        name = (
            (profile.get("company_name") or "").strip()
            or (profile.get("email") or "").split("@")[0].strip()
            or "My Organization"
        )
        slug = re.sub(r"-+", "-", re.sub(r"[^a-zA-Z0-9]", "-", name.lower())).strip("-")
        slug = f"{slug or 'org'}-{user_id[:6]}"
        org = (
            sb.table("organizations")
            .insert({"name": name, "slug": slug, "plan": "free", "created_by": user_id})
            .execute()
        )
        org_id = org.data[0]["id"]
        sb.table("org_members").insert(
            {
                "org_id": org_id,
                "user_id": user_id,
                "role": "owner",
                "joined_at": datetime.utcnow().isoformat(),
                "status": "active",
            }
        ).execute()
    sb.table("profiles").update({"org_id": org_id}).eq("id", user_id).execute()
    return org_id


async def _resolve_org_id(authorization: str) -> tuple[object, str]:
    """Resolve the caller's org from the bearer token; return (supabase, org_id)."""
    token = (authorization or "").replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    try:
        import jwt as pyjwt

        user_id = pyjwt.decode(token, options={"verify_signature": False}).get("sub", token)
    except Exception:  # noqa: BLE001
        user_id = token

    sb = get_supabase_admin()
    profile = (
        sb.table("profiles")
        .select("org_id, email, company_name")
        .eq("id", user_id)
        .single()
        .execute()
    )
    data = profile.data or {}
    org_id = data.get("org_id")
    if not org_id:
        org_id = _ensure_personal_org(sb, user_id, data)
    return sb, org_id


def _validate_region(region: str) -> str:
    chosen = region.upper()
    if chosen not in REGION_LABELS:
        raise HTTPException(400, f"unsupported region '{region}'")
    return chosen


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


@router.post("/submissions", status_code=201)
async def submit_record(
    submission: SignedSubmission, authorization: str = Header(...)
) -> dict:
    """Verify a supplier-signed emission record, persist it and checkpoint the root."""
    sb, org_id = await _resolve_org_id(authorization)
    try:
        accepted = store.append_submission(sb, org_id=org_id, submission=submission)
    except store.InvalidSupplierSignature as exc:
        raise HTTPException(400, str(exc)) from exc
    except store.SupplierKeyMismatch as exc:
        raise HTTPException(409, str(exc)) from exc
    except store.DuplicateBatch as exc:
        raise HTTPException(409, str(exc)) from exc
    return to_jsonable(accepted)


@router.post("/demo/seed")
async def seed_demo_chain(
    region: str = Query("EU"),
    packs: int = Query(3, ge=1, le=_MAX_PACKS),
    ore_kg: str = Query("20000"),
    authorization: str = Header(...),
) -> dict:
    """Seed a *real* signed ore->battery chain through the genuine ingest path.

    Each generated record is signed with a deterministic-but-genuine Ed25519
    supplier key, then verified and persisted exactly like an external
    submission. Re-running is safe: already-present batches are skipped.
    """
    chosen = _validate_region(region)
    try:
        ore = Decimal(ore_kg)
        if ore <= 0:
            raise ValueError
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(400, "ore_kg must be a positive number") from exc

    sb, org_id = await _resolve_org_id(authorization)

    seeded = 0
    skipped = 0
    last: object | None = None
    for pack_no in range(1, packs + 1):
        for record, _gen_priv, _gen_pub in build_chain(chosen, ore, pack_no):
            # Deterministic-but-genuine supplier key per (org, supplier_id) so
            # re-seeding keeps the TOFU binding stable.
            priv, pub = crypto.keypair_from_seed(f"{org_id}/{record.supplier_id}")
            record_json = record.model_dump(mode="json")
            signature = crypto.sign(priv, crypto.canonical_bytes(record_json))
            submission = SignedSubmission(
                record=record, supplier_public_key=pub, signature=signature
            )
            try:
                last = store.append_submission(sb, org_id=org_id, submission=submission)
                seeded += 1
            except store.DuplicateBatch:
                skipped += 1
            except store.SupplierKeyMismatch as exc:
                raise HTTPException(409, str(exc)) from exc

    root = store.latest_signed_root(sb, org_id)
    return {
        "region": chosen,
        "seeded": seeded,
        "skipped": skipped,
        "root": root.root if root else None,
        "size": root.size if root else 0,
        "last": to_jsonable(last) if last is not None else None,
    }


@router.get("/report")
async def get_report(
    profile: str = Query(DEFAULT_PROFILE),
    region: str | None = Query(None),
    authorization: str = Header(...),
) -> dict:
    """Build a cradle-to-gate Scope 3 report from the org's persisted ledger."""
    if profile.lower() not in PROFILES:
        raise HTTPException(404, f"unknown profile '{profile}'")
    region_filter = _validate_region(region) if region else None
    sb, org_id = await _resolve_org_id(authorization)
    rows = store.report_rows(sb, org_id, region=region_filter)
    report = build_report(profile, rows)
    return to_jsonable(report)


@router.get("/ledger")
async def get_ledger(
    region: str | None = Query(None),
    authorization: str = Header(...),
) -> dict:
    """Return the append-only ledger entries (in Merkle-leaf order)."""
    region_filter = _validate_region(region) if region else None
    sb, org_id = await _resolve_org_id(authorization)
    entries = store.ledger_entries(sb, org_id, region=region_filter)
    root = store.latest_signed_root(sb, org_id)
    return {
        "region": region_filter,
        "root": root.root if root else None,
        "size": root.size if root else 0,
        "entries": [to_jsonable(e) for e in entries],
    }


@router.get("/provenance")
async def get_provenance(
    region: str | None = Query(None),
    batch_id: str | None = Query(None),
    authorization: str = Header(...),
) -> dict:
    """Return the W3C PROV-JSON document, a simplified graph, and quality stats."""
    region_filter = _validate_region(region) if region else None
    sb, org_id = await _resolve_org_id(authorization)
    entries = store.signed_entries(sb, org_id, region=region_filter)
    stats = prov_mod.provenance_stats(entries)
    return {
        "prov": prov_mod.build_prov_json(entries, batch_id=batch_id),
        "graph": prov_mod.build_graph(entries, batch_id=batch_id),
        "stats": {
            "batches": stats.batches,
            "derived_edges": stats.derived_edges,
            "roots": stats.roots,
            "dangling_parents": stats.dangling_parents,
            "completeness_ratio": stats.completeness_ratio,
        },
    }


@router.get("/bundle/{leaf_index}")
async def get_bundle(leaf_index: int, authorization: str = Header(...)) -> dict:
    """Return a self-contained, offline-verifiable proof bundle for one entry."""
    sb, org_id = await _resolve_org_id(authorization)
    try:
        bundle = store.build_proof_bundle(sb, org_id, leaf_index)
    except IndexError as exc:
        raise HTTPException(404, str(exc)) from exc
    return to_jsonable(bundle)


@router.get("/verify/{leaf_index}")
async def verify_entry(leaf_index: int, authorization: str = Header(...)) -> dict:
    """Server-side verification of one entry (same logic as the offline CLI)."""
    sb, org_id = await _resolve_org_id(authorization)
    try:
        bundle = store.build_proof_bundle(sb, org_id, leaf_index)
    except IndexError as exc:
        raise HTTPException(404, str(exc)) from exc
    return verify_bundle(bundle).as_dict()
