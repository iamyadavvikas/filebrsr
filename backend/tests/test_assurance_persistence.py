"""Carbon Assurance — persisted, supplier-signed ledger (migration v22).

Acceptance:
- A supplier-signed record is verified, persisted as a Merkle leaf, and a
  KMS-signed checkpoint is written.
- An invalid supplier signature is rejected and nothing is persisted.
- A supplier_id reused with a different key (impersonation) is rejected (TOFU).
- A duplicate batch_id is rejected.
- A proof bundle built from persisted rows verifies OFFLINE (all four checks),
  and tampering with a stored payload breaks the bundle.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.assurance import crypto, store
from app.assurance.factors import Stage
from app.assurance.schemas import EmissionRecord, SignedSubmission
from app.assurance.verify_cli import verify_bundle
from app.prov.signing import LocalEd25519Signer, reset_signer

_FIXED_SEED_B64 = base64.b64encode(bytes(range(32))).decode("ascii")


@pytest.fixture(autouse=True)
def _fixed_signer(monkeypatch):
    """Force a deterministic in-memory server signer for checkpoint roots."""
    reset_signer()
    signer = LocalEd25519Signer.from_seed_b64(_FIXED_SEED_B64, "test-key")
    monkeypatch.setattr("app.prov.signing._signer", signer, raising=False)
    yield
    reset_signer()


# ─── stateful fake supabase (mirrors tests/test_phase_d_ledger.py) ─────────

class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
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
        rows = [r for r in self._rows if all(r.get(c) == v for c, v in self._filters)]
        if self._order:
            col, desc = self._order
            rows = sorted(rows, key=lambda r: r.get(col, 0), reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return rows

    def execute(self):
        return _Resp(list(self._apply()))


class _InsertExec:
    def execute(self):
        return _Resp([])


class _Table:
    def __init__(self, store_dict: dict[str, list[dict]], name: str):
        self._store = store_dict
        self._name = name

    def select(self, *a, **k):
        return _Query(self._store.setdefault(self._name, [])).select(*a, **k)

    def insert(self, row):
        self._store.setdefault(self._name, []).append(dict(row))
        return _InsertExec()


class FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _Table(self.store, name)


# ─── helpers ────────────────────────────────────────────────────────────────

def _record(batch_id: str, supplier_id: str, parent: str | None = None) -> EmissionRecord:
    return EmissionRecord(
        batch_id=batch_id,
        parent_batch_id=parent,
        stage=Stage.ORE,
        supplier_id=supplier_id,
        region="EU",
        material="nickel ore",
        quantity_kg=Decimal("20000"),
        emissions_kg_co2e=Decimal("1234.50"),
        energy_kwh=None,
        emission_factor_source="illustrative",
        emission_factor_uncertainty=Decimal("0.1"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _submission(record: EmissionRecord, seed: str) -> SignedSubmission:
    priv, pub = crypto.keypair_from_seed(seed)
    message = crypto.canonical_bytes(record.model_dump(mode="json"))
    return SignedSubmission(
        record=record,
        supplier_public_key=pub,
        signature=crypto.sign(priv, message),
    )


# ─── tests ──────────────────────────────────────────────────────────────────

def test_append_submission_persists_and_checkpoints():
    sb = FakeSupabase()
    rec = _record("ore-1", "ore-supplier")
    accepted = store.append_submission(
        sb, org_id="org-1", submission=_submission(rec, "ore-supplier")
    )
    assert accepted.leaf_index == 0
    assert accepted.size == 1
    assert len(sb.store["assurance_submissions"]) == 1
    assert len(sb.store["assurance_roots"]) == 1
    assert len(sb.store["assurance_suppliers"]) == 1
    assert sb.store["assurance_roots"][0]["prev_root"] is None


def test_invalid_signature_rejected_and_not_persisted():
    sb = FakeSupabase()
    rec = _record("ore-1", "ore-supplier")
    sub = _submission(rec, "ore-supplier")
    # Corrupt the signature.
    bad = SignedSubmission(
        record=rec,
        supplier_public_key=sub.supplier_public_key,
        signature=base64.b64encode(b"\x00" * 64).decode("ascii"),
    )
    with pytest.raises(store.InvalidSupplierSignature):
        store.append_submission(sb, org_id="org-1", submission=bad)
    assert sb.store.get("assurance_submissions", []) == []
    assert sb.store.get("assurance_suppliers", []) == []


def test_supplier_key_mismatch_rejected():
    sb = FakeSupabase()
    first = _record("ore-1", "ore-supplier")
    store.append_submission(sb, org_id="org-1", submission=_submission(first, "key-a"))
    # Same supplier_id, different (validly signed) key — impersonation attempt.
    second = _record("ore-2", "ore-supplier")
    with pytest.raises(store.SupplierKeyMismatch):
        store.append_submission(sb, org_id="org-1", submission=_submission(second, "key-b"))
    assert len(sb.store["assurance_submissions"]) == 1


def test_duplicate_batch_rejected():
    sb = FakeSupabase()
    rec = _record("ore-1", "ore-supplier")
    store.append_submission(sb, org_id="org-1", submission=_submission(rec, "ore-supplier"))
    again = _record("ore-1", "ore-supplier")
    with pytest.raises(store.DuplicateBatch):
        store.append_submission(sb, org_id="org-1", submission=_submission(again, "ore-supplier"))
    assert len(sb.store["assurance_submissions"]) == 1


def test_proof_bundle_verifies_offline():
    sb = FakeSupabase()
    parent = None
    for i in range(4):
        rec = _record(f"ore-{i}", f"supplier-{i}", parent=parent)
        store.append_submission(sb, org_id="org-1", submission=_submission(rec, f"supplier-{i}"))
        parent = f"ore-{i}"

    bundle = store.build_proof_bundle(sb, "org-1", 2)
    result = verify_bundle(bundle)
    assert result.valid is True
    assert result.leaf_hash_ok is True
    assert result.inclusion_ok is True
    assert result.root_signature_ok is True
    assert result.supplier_signature_ok is True
    assert result.size == 4


def test_tamper_payload_breaks_bundle():
    sb = FakeSupabase()
    for i in range(3):
        rec = _record(f"ore-{i}", f"supplier-{i}")
        store.append_submission(sb, org_id="org-1", submission=_submission(rec, f"supplier-{i}"))

    # Mutate a stored payload after the fact (simulating DB tampering).
    sb.store["assurance_submissions"][1]["payload"]["emissions_kg_co2e"] = "999999.99"
    bundle = store.build_proof_bundle(sb, "org-1", 1)
    result = verify_bundle(bundle)
    assert result.valid is False
    # The recomputed leaf no longer matches the stored leaf hash.
    assert result.leaf_hash_ok is False
