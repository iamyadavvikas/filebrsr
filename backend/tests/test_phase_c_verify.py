"""
Phase C — public verification surface (``/api/verify``).

Acceptance:
- A published, untampered calculation verifies → ``status == "PASS"``.
- A tampered stored graph → HTTP 200 with ``status == "FAIL"`` (verification
  fails, the endpoint does not crash).
- An unpublished calculation is hidden (404), so internal drafts can't be
  enumerated. Pre-v18 (no ``published`` column) the gate is skipped.
"""

from __future__ import annotations

import base64
import copy
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.calculator import scope2_location_based, sign_result
from app.factors_india import reset_cache
from app.main import app
from app.prov.signing import LocalEd25519Signer, reset_signer

_FIXED_SEED_B64 = base64.b64encode(bytes(range(1, 33))).decode("ascii")


@pytest.fixture(autouse=True)
def _fixed_signer(monkeypatch):
    reset_signer()
    reset_cache()
    signer = LocalEd25519Signer.from_seed_b64(_FIXED_SEED_B64, "verify-test-key")
    monkeypatch.setattr("app.prov.signing._signer", signer, raising=False)
    yield
    reset_signer()
    reset_cache()


def _signed_record(*, published: bool | None):
    """Build a real signed calc and the (prov_record, calc) rows verify reads."""
    result = scope2_location_based(150_000, jurisdiction="AU", state="NSW")
    calc_id, signed = sign_result(result, org_id="org-1", jurisdiction="AU")
    prov = {
        "calculation_id": calc_id,
        "org_id": "org-1",
        "prov_graph": signed.graph,
        "canonical_sha256": signed.canonical_sha256,
        "algorithm": signed.algorithm,
        "signature_b64": signed.signature_b64,
        "public_key_b64": signed.public_key_b64,
        "key_id": signed.key_id,
        "signed_at": signed.signed_at,
    }
    calc = {
        "id": calc_id,
        "org_id": "org-1",
        "value": str(result.value),
        "unit": result.unit,
        "scope": result.scope,
        "method": result.method,
        "jurisdiction": "AU",
        "factor_id": result.factor_id,
        "factor_version": result.factor_version,
        "factor_source": result.factor_source,
        "factor_citation": result.factor_citation,
    }
    if published is not None:
        calc["published"] = published
    return calc_id, prov, calc


class _Resp:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, data):
        self._data = data

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def single(self):
        return self

    def execute(self):
        return _Resp(self._data)


class _FakeVerifySupabase:
    """Returns the prov record / calc row by table; ledger tables empty."""

    def __init__(self, prov: dict, calc: dict):
        self._prov = prov
        self._calc = calc

    def table(self, name: str):
        if name == "provenance_records":
            return _Q(self._prov)
        if name == "calculations":
            return _Q(self._calc)
        # ledger_leaves / ledger_roots → empty (no inclusion proof)
        return _Q(None)


async def _get(calc_id: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(f"/api/verify/{calc_id}")


async def test_published_untampered_passes():
    calc_id, prov, calc = _signed_record(published=True)
    fake = _FakeVerifySupabase(prov, calc)
    with patch("app.router_verify.get_supabase_admin", return_value=fake):
        resp = await _get(calc_id)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PASS"
    assert body["verified"] is True
    assert body["jurisdiction"] == "AU"
    assert body["factor"]["id"] == "nga/nsw"


async def test_tampered_graph_returns_fail():
    calc_id, prov, calc = _signed_record(published=True)
    tampered = copy.deepcopy(prov)
    tampered["prov_graph"]["@graph"][0]["fbrsr:value"] = "999999"
    fake = _FakeVerifySupabase(tampered, calc)
    with patch("app.router_verify.get_supabase_admin", return_value=fake):
        resp = await _get(calc_id)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "FAIL"
    assert body["verified"] is False


async def test_unpublished_is_hidden():
    calc_id, prov, calc = _signed_record(published=False)
    fake = _FakeVerifySupabase(prov, calc)
    with patch("app.router_verify.get_supabase_admin", return_value=fake):
        resp = await _get(calc_id)
    assert resp.status_code == 404


async def test_pre_v18_no_published_column_is_visible():
    """Without a published column (pre-migration) the gate is skipped."""
    calc_id, prov, calc = _signed_record(published=None)
    fake = _FakeVerifySupabase(prov, calc)
    with patch("app.router_verify.get_supabase_admin", return_value=fake):
        resp = await _get(calc_id)
    assert resp.status_code == 200
    assert resp.json()["status"] == "PASS"
