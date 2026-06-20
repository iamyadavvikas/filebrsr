"""In-memory, deterministic mining-to-battery ledger.

Ported and adapted from CarbonTrace's synthetic generator + ingest/integrity
services. Builds a signed ore -> concentrate -> smelter -> battery supply chain,
assembles an RFC 6962 Merkle tree over the canonical leaves, and signs the root
with a server key — producing the same proof-bundle structure CarbonTrace's
offline verifier consumes.

The chain is **deterministic** for a given ``(region, packs, ore_kg)`` so the
report/ledger/provenance endpoints return stable data across calls (and the
results are cached per parameter set). Keys are derived from seeds for the demo;
in production the server key would come from KMS (see :mod:`app.prov.signing`).
"""

from __future__ import annotations

import functools
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.assurance import crypto
from app.assurance.factors import (
    KWH_PER_KG_METAL,
    MASS_YIELD,
    MATERIALS,
    Stage,
    factors_for_region,
)
from app.assurance.profiles import ReportRow
from app.assurance.schemas import (
    EmissionRecord,
    LedgerEntry,
    ProofBundle,
    ProofStepModel,
    SignedRoot,
)

# Fixed base timestamp so deterministic chains have stable occurred_at values.
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
# Server-key seed for the demo ledger (a real deployment would use KMS).
_SERVER_KEY_SEED = "filebrsr-carbon-assurance-server-key/v1"


def _seeded_keypair(seed: str) -> tuple[str, str]:
    """Derive a deterministic Ed25519 keypair from a string seed.

    The private scalar is ``sha256(seed)`` (32 bytes), which is a valid raw
    Ed25519 private key. Deterministic keys keep the demo ledger reproducible.
    """
    raw = hashlib.sha256(seed.encode("utf-8")).digest()
    private = crypto.Ed25519PrivateKey.from_private_bytes(raw)
    return (
        crypto._b64encode(raw),
        crypto._b64encode(private.public_key().public_bytes_raw()),
    )


@dataclass
class SignedEntry:
    """A ledger entry: the record plus the supplier signature over it."""

    record: EmissionRecord
    supplier_public_key: str
    supplier_signature: str
    leaf_hex: str


@dataclass
class Ledger:
    """An assembled, signed Merkle ledger for one supply chain."""

    region: str
    entries: list[SignedEntry]
    leaves: list[bytes]
    root_hex: str
    signed_root: SignedRoot


def build_chain(
    region: str, ore_kg: Decimal, pack_no: int
) -> list[tuple[EmissionRecord, str, str]]:
    """Build one full signed ore->battery chain for a single battery pack."""
    factors = factors_for_region(region)
    chain_id = hashlib.sha256(f"{region}:{ore_kg}:{pack_no}".encode()).hexdigest()[:8]

    concentrate_kg = (ore_kg * MASS_YIELD["ore_to_concentrate"]).quantize(Decimal("0.01"))
    metal_kg = (concentrate_kg * MASS_YIELD["concentrate_to_metal"]).quantize(Decimal("0.01"))
    capacity_kwh = (metal_kg * KWH_PER_KG_METAL).quantize(Decimal("0.01"))

    stages: list[tuple[Stage, Decimal, Decimal | None]] = [
        (Stage.ORE, ore_kg, None),
        (Stage.CONCENTRATE, concentrate_kg, None),
        (Stage.SMELTER, metal_kg, None),
        (Stage.BATTERY, metal_kg, capacity_kwh),
    ]

    out: list[tuple[EmissionRecord, str, str]] = []
    parent_batch_id: str | None = None
    for i, (stage, quantity_kg, energy_kwh) in enumerate(stages):
        factor = factors[stage.value]
        if stage is Stage.BATTERY:
            emissions = (factor.value * (energy_kwh or Decimal(0))).quantize(Decimal("0.01"))
        else:
            emissions = (factor.value * quantity_kg).quantize(Decimal("0.01"))

        batch_id = f"{stage.value}-{chain_id}-{pack_no}"
        record = EmissionRecord(
            batch_id=batch_id,
            parent_batch_id=parent_batch_id,
            stage=stage,
            supplier_id=f"{stage.value}-supplier-{region.lower()}",
            region=region.upper(),
            material=MATERIALS[stage.value],
            quantity_kg=quantity_kg,
            emissions_kg_co2e=emissions,
            energy_kwh=energy_kwh,
            emission_factor_source=factor.source,
            emission_factor_uncertainty=factor.uncertainty,
            occurred_at=_BASE_TIME + timedelta(hours=4 * (pack_no - 1) + i),
        )
        priv, pub = _seeded_keypair(f"supplier/{region}/{pack_no}/{stage.value}")
        out.append((record, priv, pub))
        parent_batch_id = batch_id

    return out


@functools.lru_cache(maxsize=64)
def build_ledger(
    region: str, packs: int = 3, ore_kg: str = "20000"
) -> Ledger:
    """Assemble a deterministic, signed Merkle ledger for ``region`` (cached)."""
    region = region.upper()
    ore = Decimal(ore_kg)

    entries: list[SignedEntry] = []
    leaves: list[bytes] = []
    for pack_no in range(1, packs + 1):
        for record, priv, pub in build_chain(region, ore, pack_no):
            record_json = record.model_dump(mode="json")
            message = crypto.canonical_bytes(record_json)
            signature = crypto.sign(priv, message)
            leaf_hex = crypto.leaf_hash(record_json)
            entries.append(
                SignedEntry(
                    record=record,
                    supplier_public_key=pub,
                    supplier_signature=signature,
                    leaf_hex=leaf_hex,
                )
            )
            leaves.append(bytes.fromhex(leaf_hex))

    root = crypto.merkle_root(leaves)
    root_hex = root.hex()
    server_priv, server_pub = _seeded_keypair(_SERVER_KEY_SEED)
    header = crypto.canonical_bytes(crypto.root_header(root_hex, len(leaves), "sha256"))
    signed_root = SignedRoot(
        root=root_hex,
        size=len(leaves),
        algorithm="sha256",
        signature=crypto.sign(server_priv, header),
        server_public_key=server_pub,
        created_at=_BASE_TIME,
    )
    return Ledger(
        region=region,
        entries=entries,
        leaves=leaves,
        root_hex=root_hex,
        signed_root=signed_root,
    )


def ledger_entries(ledger: Ledger) -> list[LedgerEntry]:
    """Read view of the append-only ledger (in leaf order)."""
    return [
        LedgerEntry(
            leaf_index=i,
            stage=e.record.stage.value,
            batch_id=e.record.batch_id,
            parent_batch_id=e.record.parent_batch_id,
            region=e.record.region,
            material=e.record.material,
            emissions_kg_co2e=e.record.emissions_kg_co2e,
            record_hash=e.leaf_hex,
            supplier_id=e.record.supplier_id,
        )
        for i, e in enumerate(ledger.entries)
    ]


def report_rows(ledger: Ledger) -> list[ReportRow]:
    """Reduce ledger entries to the fields the Scope 3 report needs."""
    return [
        ReportRow(
            stage=e.record.stage.value,
            emissions_kg_co2e=e.record.emissions_kg_co2e,
            energy_kwh=e.record.energy_kwh,
            factor_source=e.record.emission_factor_source,
        )
        for e in ledger.entries
    ]


def proof_bundle(ledger: Ledger, leaf_index: int) -> ProofBundle:
    """Build a self-contained, offline-verifiable proof bundle for an entry."""
    if not 0 <= leaf_index < len(ledger.entries):
        raise IndexError(f"leaf index {leaf_index} out of range")
    entry = ledger.entries[leaf_index]
    path = crypto.inclusion_path(ledger.leaves, leaf_index)
    return ProofBundle(
        record=entry.record,
        leaf_index=leaf_index,
        leaf_hash=entry.leaf_hex,
        inclusion_proof=[ProofStepModel(side=s.side, hash=s.hash) for s in path],
        signed_root=ledger.signed_root,
        supplier_public_key=entry.supplier_public_key,
        supplier_signature=entry.supplier_signature,
    )


def verify_entry(ledger: Ledger, leaf_index: int) -> dict:
    """Server-side convenience verification of one entry."""
    entry = ledger.entries[leaf_index]
    sr = ledger.signed_root
    record_json = entry.record.model_dump(mode="json")

    leaf_ok = crypto.leaf_hash(record_json) == entry.leaf_hex
    path = crypto.inclusion_path(ledger.leaves, leaf_index)
    inclusion_ok = crypto.verify_inclusion(entry.leaf_hex, sr.root, path)
    header = crypto.canonical_bytes(crypto.root_header(sr.root, sr.size, sr.algorithm))
    root_sig_ok = crypto.verify_signature(sr.server_public_key, header, sr.signature)
    supplier_ok = crypto.verify_signature(
        entry.supplier_public_key,
        crypto.canonical_bytes(record_json),
        entry.supplier_signature,
    )
    valid = leaf_ok and inclusion_ok and root_sig_ok and supplier_ok
    return {
        "valid": valid,
        "checks": {
            "leaf_hash": leaf_ok,
            "inclusion_proof": inclusion_ok,
            "root_signature": root_sig_ok,
            "supplier_signature": supplier_ok,
        },
        "root": sr.root,
        "size": sr.size,
        "leaf_index": leaf_index,
    }
