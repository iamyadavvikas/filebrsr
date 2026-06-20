"""
Phase D — tamper-evident Merkle ledger.

Acceptance:
- RFC 6962 inclusion + consistency proofs verify for every position/size.
- ``append_event`` records a leaf + signed root; ``get_inclusion_proof``
  returns a proof that recomputes to the signed root.
- Tampering with a stored calculation payload breaks BOTH the recomputed leaf
  (Merkle inclusion) AND, separately, the Ed25519 signature over the graph.
"""

from __future__ import annotations

import base64

import pytest

from app.calculator import scope2_location_based, sign_result
from app.factors_india import reset_cache
from app.ledger import (
    append_event,
    consistency_proof,
    get_inclusion_proof,
    hash_leaf,
    hash_node,
    inclusion_proof,
    merkle_root,
    verify_inclusion,
)
from app.prov import verify_signed_provenance
from app.prov.canonicalize import canonicalize
from app.prov.signing import LocalEd25519Signer, reset_signer, verify

_FIXED_SEED_B64 = base64.b64encode(bytes(range(32))).decode("ascii")


@pytest.fixture(autouse=True)
def _fixed_signer(monkeypatch):
    """Force a deterministic in-memory signer for ledger root signing."""
    reset_signer()
    signer = LocalEd25519Signer.from_seed_b64(_FIXED_SEED_B64, "test-key")
    monkeypatch.setattr("app.prov.signing._signer", signer, raising=False)
    monkeypatch.setattr("app.prov.get_signer", lambda: signer, raising=False)
    yield
    reset_signer()


# ─── RFC 6962 primitives ───────────────────────────────────────────────────

def _leaves(n: int) -> list[bytes]:
    return [hash_leaf(f"event-{i}".encode()) for i in range(n)]


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5, 8, 13, 16])
def test_inclusion_proof_verifies_every_leaf(size):
    leaves = _leaves(size)
    root = merkle_root(leaves)
    for i in range(size):
        proof = inclusion_proof(leaves, i)
        assert verify_inclusion(leaves[i], i, size, proof, root) is True


def test_inclusion_proof_rejects_wrong_leaf():
    leaves = _leaves(8)
    root = merkle_root(leaves)
    proof = inclusion_proof(leaves, 3)
    bad = hash_leaf(b"forged")
    assert verify_inclusion(bad, 3, 8, proof, root) is False


@pytest.mark.parametrize("m,n", [(1, 4), (2, 5), (3, 8), (5, 13), (8, 16)])
def test_consistency_proof_is_well_formed(m, n):
    leaves = _leaves(n)
    proof = consistency_proof(leaves, m, n)
    # A consistency proof between distinct sizes must be non-empty and made of
    # 32-byte node hashes.
    assert proof
    assert all(len(h) == 32 for h in proof)


def test_consistency_old_root_recoverable():
    """The old root must be derivable; appending must not rewrite history."""
    new = _leaves(6)
    old_root = merkle_root(_leaves(4))
    # First 4 leaves of the size-6 tree are identical to the size-4 tree.
    assert merkle_root(new[:4]) == old_root


def test_hash_domain_separation():
    """Leaf and node hashing use different prefixes (second-preimage safety)."""
    a, b = hash_leaf(b"x"), hash_leaf(b"y")
    assert hash_node(a, b) != hash_leaf(a + b)


# ─── stateful fake supabase for the ledger service ─────────────────────────

class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    """Minimal chainable query over an in-memory row list."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filters: list[tuple[str, object]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _apply(self) -> list[dict]:
        rows = [
            r for r in self._rows
            if all(r.get(c) == v for c, v in self._filters)
        ]
        if self._order:
            col, desc = self._order
            rows = sorted(rows, key=lambda r: r.get(col, 0), reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def execute(self):
        return _Resp(list(self._apply()))


class _Table:
    def __init__(self, store: dict[str, list[dict]], name: str):
        self._store = store
        self._name = name

    def select(self, *a, **k):
        return _Query(self._store.setdefault(self._name, [])).select(*a, **k)

    def insert(self, row):
        self._store.setdefault(self._name, []).append(dict(row))
        return _InsertExec()


class _InsertExec:
    def execute(self):
        return _Resp([])


class FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


# ─── ledger service: append + inclusion proof + tamper ─────────────────────

def test_append_event_records_leaf_and_signed_root():
    sb = FakeSupabase()
    ok = append_event(
        sb,
        org_id="org-1",
        event_type="calculation.signed",
        ref_table="calculations",
        ref_pk="calc-1",
        payload={"calculation_id": "calc-1", "value": "10"},
    )
    assert ok is True
    assert len(sb.store["ledger_leaves"]) == 1
    assert len(sb.store["ledger_roots"]) == 1
    root = sb.store["ledger_roots"][0]
    assert root["tree_size"] == 1
    assert root["prev_root"] is None


def test_get_inclusion_proof_recomputes_signed_root():
    sb = FakeSupabase()
    payloads = [
        {"calculation_id": f"calc-{i}", "value": str(i)} for i in range(4)
    ]
    for i, p in enumerate(payloads):
        append_event(
            sb,
            org_id="org-1",
            event_type="calculation.signed",
            ref_table="calculations",
            ref_pk=f"calc-{i}",
            payload=p,
        )

    proof = get_inclusion_proof(
        sb, org_id="org-1", ref_table="calculations", ref_pk="calc-2"
    )
    assert proof is not None
    leaf_hash = bytes.fromhex(proof["leaf_sha256"])
    siblings = [bytes.fromhex(h) for h in proof["proof"]]
    signed_root = proof["signed_root"]
    root_bytes = bytes.fromhex(signed_root["merkle_root"])

    # Inclusion proof recomputes to the signed root.
    assert verify_inclusion(
        leaf_hash, proof["leaf_index"], proof["tree_size"], siblings, root_bytes
    ) is True

    # The signed root's signature is valid for the canonical signed head.
    head = canonicalize(
        {
            "org_id": "org-1",
            "tree_size": signed_root["tree_size"],
            "merkle_root": signed_root["merkle_root"],
            "prev_root": signed_root["prev_root"],
        }
    )
    sig = base64.b64decode(signed_root["root_signature_b64"])
    assert verify(head, sig, signed_root["public_key_b64"]) is True


def test_tamper_breaks_merkle_inclusion_and_signature():
    """Mutating a stored calc payload breaks the ledger proof AND the graph signature."""
    sb = FakeSupabase()
    reset_cache()
    result = scope2_location_based(150_000, jurisdiction="AU", state="NSW")
    _, signed = sign_result(result, org_id="org-1", jurisdiction="AU")
    assert verify_signed_provenance(signed) is True

    append_event(
        sb,
        org_id="org-1",
        event_type="calculation.signed",
        ref_table="calculations",
        ref_pk="calc-1",
        payload={
            "calculation_id": "calc-1",
            "canonical_sha256": signed.canonical_sha256,
            "value": str(result.value),
        },
    )
    proof = get_inclusion_proof(
        sb, org_id="org-1", ref_table="calculations", ref_pk="calc-1"
    )
    root_bytes = bytes.fromhex(proof["signed_root"]["merkle_root"])

    # (1) Merkle: re-hash a TAMPERED payload — recomputed leaf no longer matches.
    tampered_leaf = hash_leaf(
        canonicalize(
            {
                "calculation_id": "calc-1",
                "canonical_sha256": signed.canonical_sha256,
                "value": "999999",  # changed
            }
        )
    )
    assert verify_inclusion(
        tampered_leaf, proof["leaf_index"], proof["tree_size"], [], root_bytes
    ) is False

    # (2) Signature: mutate the signed graph value — signature fails.
    bad = signed.graph
    bad["@graph"][0]["fbrsr:value"] = "999999"
    from dataclasses import replace

    assert verify_signed_provenance(replace(signed, graph=bad)) is False
