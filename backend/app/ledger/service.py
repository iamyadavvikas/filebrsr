"""
Tamper-evident ledger service (Phase D).

Appends audit-critical events as RFC 6962 Merkle leaves and signs the new tree
head after every append (reusing the Ed25519 signer from :mod:`app.prov`).
Verifiers recompute a leaf from the stored payload, walk the inclusion proof to
the signed root, and check the root signature — so any post-hoc mutation of a
stored row breaks verification.

Writes go through the Supabase **service role** (RLS-exempt) but remain subject
to the append-only trigger from migration v17. Persistence is best-effort: a
failure to anchor must never block the user-facing calculation submit (NFR), so
callers typically invoke :func:`append_event` from a background task.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from app.ledger.merkle import (
    hash_leaf,
    inclusion_proof,
    merkle_root,
)
from app.prov.canonicalize import canonicalize, sha256_hex

logger = logging.getLogger("filebrsr.ledger")


def _signed_head_bytes(org_id: str, tree_size: int, root_hex: str, prev_hex: str | None) -> bytes:
    """Canonical bytes of the signed tree head (what the signature covers)."""
    return canonicalize(
        {
            "org_id": org_id,
            "tree_size": tree_size,
            "merkle_root": root_hex,
            "prev_root": prev_hex,
        }
    )


def _leaf_hashes_for_org(supabase, org_id: str) -> list[bytes]:
    """All leaf hashes for an org, ordered by leaf_index (bytes)."""
    resp = (
        supabase.table("ledger_leaves")
        .select("leaf_index, leaf_sha256")
        .eq("org_id", org_id)
        .order("leaf_index")
        .execute()
    )
    rows = resp.data or []
    return [bytes.fromhex(r["leaf_sha256"]) for r in rows]


def append_event(
    supabase,
    *,
    org_id: str,
    event_type: str,
    ref_table: str,
    ref_pk: str,
    payload: dict[str, Any],
) -> bool:
    """Append one event to the org's ledger and sign the new root.

    Best-effort: returns True on success; logs and returns False if the ledger
    tables are missing (pre-v17) or any write fails, so the caller can proceed.
    """
    try:
        canonical = canonicalize(payload)
        leaf_hash = hash_leaf(canonical)
        leaf_hex = leaf_hash.hex()

        # Next leaf_index for this org.
        last = (
            supabase.table("ledger_leaves")
            .select("leaf_index")
            .eq("org_id", org_id)
            .order("leaf_index", desc=True)
            .limit(1)
            .execute()
        )
        next_index = ((last.data or [{}])[0].get("leaf_index", -1) + 1) if last.data else 0

        supabase.table("ledger_leaves").insert(
            {
                "org_id": org_id,
                "leaf_index": next_index,
                "event_type": event_type,
                "ref_table": ref_table,
                "ref_pk": str(ref_pk),
                "leaf_sha256": leaf_hex,
                "payload": payload,
            }
        ).execute()

        # Recompute the root over all leaves [0, next_index].
        leaves = _leaf_hashes_for_org(supabase, org_id)
        tree_size = len(leaves)
        root_hex = merkle_root(leaves).hex()

        prev = (
            supabase.table("ledger_roots")
            .select("merkle_root, tree_size")
            .eq("org_id", org_id)
            .order("tree_size", desc=True)
            .limit(1)
            .execute()
        )
        prev_hex = (prev.data or [{}])[0].get("merkle_root") if prev.data else None

        from app.prov import get_signer

        signer = get_signer()
        signature = signer.sign(_signed_head_bytes(org_id, tree_size, root_hex, prev_hex))

        supabase.table("ledger_roots").insert(
            {
                "org_id": org_id,
                "tree_size": tree_size,
                "merkle_root": root_hex,
                "prev_root": prev_hex,
                "root_signature_b64": base64.b64encode(signature).decode("ascii"),
                "public_key_b64": signer.public_key_b64(),
                "key_id": signer.key_id,
            }
        ).execute()
        from app.metrics import record_ledger_append

        record_ledger_append(ok=True)
        return True
    except Exception as exc:  # noqa: BLE001
        from app.metrics import record_ledger_append

        record_ledger_append(ok=False)
        logger.warning(
            "ledger append skipped (migration v17 applied?): %s", exc
        )
        return False


def get_inclusion_proof(supabase, *, org_id: str, ref_table: str, ref_pk: str) -> dict | None:
    """Return an inclusion proof + latest signed root for a referenced row.

    Returns ``None`` if the event is not in the ledger. The proof is a list of
    hex sibling hashes; combined with the leaf payload + signed root it lets an
    auditor recompute the tree head independently.
    """
    try:
        leaf = (
            supabase.table("ledger_leaves")
            .select("*")
            .eq("org_id", org_id)
            .eq("ref_table", ref_table)
            .eq("ref_pk", str(ref_pk))
            .order("leaf_index")
            .limit(1)
            .execute()
        )
        if not leaf.data:
            return None
        leaf_row = leaf.data[0]
        index = leaf_row["leaf_index"]

        leaves = _leaf_hashes_for_org(supabase, org_id)
        tree_size = len(leaves)
        proof = inclusion_proof(leaves, index)

        root = (
            supabase.table("ledger_roots")
            .select("*")
            .eq("org_id", org_id)
            .order("tree_size", desc=True)
            .limit(1)
            .execute()
        )
        root_row = (root.data or [None])[0]

        return {
            "leaf_index": index,
            "tree_size": tree_size,
            "leaf_sha256": leaf_row["leaf_sha256"],
            "payload": leaf_row["payload"],
            "proof": [h.hex() for h in proof],
            "signed_root": root_row,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("ledger inclusion proof lookup failed: %s", exc)
        return None
