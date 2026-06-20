"""Persisted, supplier-signed Carbon Assurance ledger (Supabase-backed).

This is the *real* version of the assurance subsystem (replacing the in-memory
deterministic demo in :mod:`app.assurance.ledger`). Suppliers submit Ed25519
signed :class:`~app.assurance.schemas.EmissionRecord` payloads; this module:

1. **Verifies** the supplier signature over the JCS-canonical record (a bad
   signature is rejected, never persisted).
2. **Binds** each ``supplier_id`` to the public key it first used (TOFU), so a
   leaked supplier id cannot be impersonated with a different keypair.
3. **Appends** the record as an RFC 6962 Merkle leaf in ``assurance_submissions``
   (org-scoped, append-only — see ``migration_v22_carbon_assurance.sql``).
4. **Checkpoints** the new tree head into ``assurance_roots``, signed by the
   process-wide KMS-backed Ed25519 signer (:func:`app.prov.get_signer`) — NOT a
   seeded demo key.

The leaf/canonical/Merkle primitives are reused from :mod:`app.assurance.crypto`
so a proof bundle produced here verifies with the unchanged offline verifier
(:mod:`app.assurance.verify_cli`).
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime

from app.assurance import crypto
from app.assurance.ledger import SignedEntry
from app.assurance.profiles import ReportRow
from app.assurance.schemas import (
    EmissionRecord,
    LedgerEntry,
    ProofBundle,
    ProofStepModel,
    SignedRoot,
    SignedSubmission,
    SubmissionAccepted,
)

logger = logging.getLogger("filebrsr.assurance.store")

_SUBMISSIONS = "assurance_submissions"
_ROOTS = "assurance_roots"
_SUPPLIERS = "assurance_suppliers"


class AssuranceError(Exception):
    """Base class for client-correctable ingest failures (mapped to 4xx)."""


class InvalidSupplierSignature(AssuranceError):
    """The supplier signature does not verify over the canonical record."""


class SupplierKeyMismatch(AssuranceError):
    """A supplier_id was reused with a public key different from the bound one."""


class DuplicateBatch(AssuranceError):
    """A record with this batch_id already exists for the org."""


# ── internal helpers ──────────────────────────────────────────────────────────
def _org_submissions(
    supabase, org_id: str, *, region: str | None = None
) -> list[dict]:
    """All submission rows for an org, ordered by leaf_index (ascending).

    The (optional) ``region`` filter is applied in-process so leaf_index order —
    and therefore Merkle position — is always taken over the full org tree.
    """
    resp = (
        supabase.table(_SUBMISSIONS)
        .select("*")
        .eq("org_id", org_id)
        .order("leaf_index")
        .execute()
    )
    rows = list(resp.data or [])
    if region is not None:
        rows = [r for r in rows if r["region"] == region]
    return rows


def _leaves(rows: list[dict]) -> list[bytes]:
    return [bytes.fromhex(r["record_sha256"]) for r in rows]


def _bind_supplier(supabase, org_id: str, supplier_id: str, public_key_b64: str) -> None:
    """Pin (TOFU) or enforce the supplier_id -> public key binding."""
    existing = (
        supabase.table(_SUPPLIERS)
        .select("public_key_b64")
        .eq("org_id", org_id)
        .eq("supplier_id", supplier_id)
        .limit(1)
        .execute()
    )
    rows = existing.data or []
    if rows:
        if rows[0]["public_key_b64"] != public_key_b64:
            raise SupplierKeyMismatch(
                f"supplier '{supplier_id}' is already bound to a different public key"
            )
        return
    supabase.table(_SUPPLIERS).insert(
        {"org_id": org_id, "supplier_id": supplier_id, "public_key_b64": public_key_b64}
    ).execute()


def _signed_root_model(row: dict) -> SignedRoot:
    return SignedRoot(
        root=row["merkle_root"],
        size=row["tree_size"],
        algorithm=row.get("algorithm", "sha256"),
        signature=row["root_signature_b64"],
        server_public_key=row["public_key_b64"],
        created_at=row.get("signed_at") or row.get("created_at") or datetime.now(UTC),
    )


# ── ingest ────────────────────────────────────────────────────────────────────
def append_submission(
    supabase, *, org_id: str, submission: SignedSubmission
) -> SubmissionAccepted:
    """Verify, persist and checkpoint one supplier-signed emission record.

    Raises :class:`AssuranceError` subclasses for client-correctable problems
    (bad signature, key mismatch, duplicate batch).
    """
    record = submission.record
    record_json = record.model_dump(mode="json")
    message = crypto.canonical_bytes(record_json)

    # 1. Verify the supplier signature BEFORE any write.
    if not crypto.verify_signature(
        submission.supplier_public_key, message, submission.signature
    ):
        raise InvalidSupplierSignature(
            "supplier signature does not verify over the canonical record"
        )

    # 2. Enforce supplier identity <-> key binding (TOFU).
    _bind_supplier(supabase, org_id, record.supplier_id, submission.supplier_public_key)

    # 3. Append as the next Merkle leaf (reject duplicate batch ids).
    rows = _org_submissions(supabase, org_id)
    if any(r["batch_id"] == record.batch_id for r in rows):
        raise DuplicateBatch(f"batch_id '{record.batch_id}' already submitted")

    leaf_hex = crypto.leaf_hash(record_json)
    leaf_index = len(rows)
    supabase.table(_SUBMISSIONS).insert(
        {
            "org_id": org_id,
            "leaf_index": leaf_index,
            "batch_id": record.batch_id,
            "parent_batch_id": record.parent_batch_id,
            "stage": record.stage.value,
            "supplier_id": record.supplier_id,
            "region": record.region,
            "material": record.material,
            "payload": record_json,
            "record_sha256": leaf_hex,
            "supplier_public_key": submission.supplier_public_key,
            "supplier_signature": submission.signature,
            "occurred_at": record_json["occurred_at"],
        }
    ).execute()

    # 4. Recompute the tree head over all leaves and sign it (server/KMS key).
    leaves = _leaves(rows)
    leaves.append(bytes.fromhex(leaf_hex))
    tree_size = len(leaves)
    root_hex = crypto.merkle_root(leaves).hex()

    prev = (
        supabase.table(_ROOTS)
        .select("merkle_root")
        .eq("org_id", org_id)
        .order("tree_size", desc=True)
        .limit(1)
        .execute()
    )
    prev_root = (prev.data or [{}])[0].get("merkle_root") if prev.data else None

    from app.prov import get_signer

    signer = get_signer()
    header = crypto.canonical_bytes(crypto.root_header(root_hex, tree_size, "sha256"))
    signature = base64.b64encode(signer.sign(header)).decode("ascii")
    supabase.table(_ROOTS).insert(
        {
            "org_id": org_id,
            "tree_size": tree_size,
            "merkle_root": root_hex,
            "prev_root": prev_root,
            "algorithm": "sha256",
            "root_signature_b64": signature,
            "public_key_b64": signer.public_key_b64(),
            "key_id": signer.key_id,
        }
    ).execute()

    return SubmissionAccepted(
        leaf_index=leaf_index,
        record_hash=leaf_hex,
        root=root_hex,
        size=tree_size,
        supplier_id=record.supplier_id,
        batch_id=record.batch_id,
    )


# ── reads ──────────────────────────────────────────────────────────────────────
def latest_signed_root(supabase, org_id: str) -> SignedRoot | None:
    """The most recent signed checkpoint for an org (covers all current leaves)."""
    resp = (
        supabase.table(_ROOTS)
        .select("*")
        .eq("org_id", org_id)
        .order("tree_size", desc=True)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return _signed_root_model(rows[0]) if rows else None


def signed_entries(
    supabase, org_id: str, *, region: str | None = None
) -> list[SignedEntry]:
    """Reconstruct in-order :class:`SignedEntry` objects from persisted rows."""
    entries: list[SignedEntry] = []
    for row in _org_submissions(supabase, org_id, region=region):
        entries.append(
            SignedEntry(
                record=EmissionRecord(**row["payload"]),
                supplier_public_key=row["supplier_public_key"],
                supplier_signature=row["supplier_signature"],
                leaf_hex=row["record_sha256"],
            )
        )
    return entries


def ledger_entries(
    supabase, org_id: str, *, region: str | None = None
) -> list[LedgerEntry]:
    """Read view of the append-only ledger (in leaf order)."""
    entries: list[LedgerEntry] = []
    for row in _org_submissions(supabase, org_id, region=region):
        rec = EmissionRecord(**row["payload"])
        entries.append(
            LedgerEntry(
                leaf_index=row["leaf_index"],
                stage=rec.stage.value,
                batch_id=rec.batch_id,
                parent_batch_id=rec.parent_batch_id,
                region=rec.region,
                material=rec.material,
                emissions_kg_co2e=rec.emissions_kg_co2e,
                record_hash=row["record_sha256"],
                supplier_id=rec.supplier_id,
            )
        )
    return entries


def report_rows(
    supabase, org_id: str, *, region: str | None = None
) -> list[ReportRow]:
    """Reduce persisted ledger rows to the fields the Scope 3 report needs."""
    rows: list[ReportRow] = []
    for row in _org_submissions(supabase, org_id, region=region):
        rec = EmissionRecord(**row["payload"])
        rows.append(
            ReportRow(
                stage=rec.stage.value,
                emissions_kg_co2e=rec.emissions_kg_co2e,
                energy_kwh=rec.energy_kwh,
                factor_source=rec.emission_factor_source,
            )
        )
    return rows


def build_proof_bundle(supabase, org_id: str, leaf_index: int) -> ProofBundle:
    """Self-contained, offline-verifiable proof bundle for one persisted entry."""
    rows = _org_submissions(supabase, org_id)
    if not 0 <= leaf_index < len(rows):
        raise IndexError(f"leaf index {leaf_index} out of range")
    row = rows[leaf_index]
    signed_root = latest_signed_root(supabase, org_id)
    if signed_root is None:
        raise IndexError("no signed checkpoint exists for this org")

    leaves = _leaves(rows)
    path = crypto.inclusion_path(leaves, leaf_index)
    return ProofBundle(
        record=EmissionRecord(**row["payload"]),
        leaf_index=leaf_index,
        leaf_hash=row["record_sha256"],
        inclusion_proof=[ProofStepModel(side=s.side, hash=s.hash) for s in path],
        signed_root=signed_root,
        supplier_public_key=row["supplier_public_key"],
        supplier_signature=row["supplier_signature"],
    )
