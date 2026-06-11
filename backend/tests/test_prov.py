"""Unit + property tests for the provenance layer (``app.prov``).

Principle #3 acceptance: a calculated number can be wrapped in a signed
PROV-O graph, and an auditor can independently re-verify the canonical hash
and Ed25519 signature. Tampering must be detectable.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from app.prov import (
    CalculationProvenanceInput,
    build_calculation_graph,
    build_signed_provenance,
    canonical_hash,
    canonicalize,
    sign_graph,
    verify_signed_provenance,
)
from app.prov.signing import LocalEd25519Signer, reset_signer, verify

# A fixed 32-byte seed → reproducible signatures across runs.
_FIXED_SEED_B64 = base64.b64encode(bytes(range(32))).decode("ascii")


def _input(**overrides) -> CalculationProvenanceInput:
    base = dict(
        calculation_id="calc-1",
        org_id="org-abc",
        value=Decimal("1234.5678"),
        unit="tCO2e",
        method="location_based",
        factor_id="cea-national",
        factor_version="2024.1",
        input_record_ids=["rec-1", "rec-2"],
        calculation_timestamp=datetime(2026, 4, 1, 10, 30, tzinfo=timezone.utc),
        factor_source="CEA CO2 Baseline Database",
        factor_citation="https://cea.nic.in/cdm-co2-baseline-database",
        uncertainty={"method": "ipcc", "pct": 5},
        agent_run_id="run-xyz",
    )
    base.update(overrides)
    return CalculationProvenanceInput(**base)


# ─── Canonicalisation determinism ─────────────────────────────────────────

def test_canonicalize_is_key_order_independent():
    a = {"b": 1, "a": {"y": 2, "x": 3}}
    b = {"a": {"x": 3, "y": 2}, "b": 1}
    assert canonicalize(a) == canonicalize(b)
    assert canonical_hash(a)[1] == canonical_hash(b)[1]


def test_graph_contains_no_json_floats():
    # Numeric value must be serialised as a string in the canonical form.
    graph = build_calculation_graph(_input(value=Decimal("99.123456789")))
    canonical = canonicalize(graph).decode("utf-8")
    assert '"99.123456789"' in canonical  # quoted → string, not a float
    assert "99.123456789," not in canonical.replace('"99.123456789"', "")


# ─── PROV-O graph structure ───────────────────────────────────────────────

def test_graph_structure_links_output_activity_factor_inputs():
    graph = build_calculation_graph(_input())
    nodes = {n["@id"]: n for n in graph["@graph"]}

    output = nodes["fbrsr:calculation/calc-1"]
    assert output["wasGeneratedBy"] == "fbrsr:activity/run-xyz"
    assert output["used"] == "fbrsr:factor/cea-national@2024.1"
    assert output["wasDerivedFrom"] == ["fbrsr:record/rec-1", "fbrsr:record/rec-2"]
    assert output["fbrsr:value"] == "1234.5678"
    assert output["fbrsr:orgId"] == "org-abc"

    activity = nodes["fbrsr:activity/run-xyz"]
    assert activity["@type"] == "prov:Activity"
    assert "fbrsr:factor/cea-national@2024.1" in activity["used"]
    assert activity["wasAssociatedWith"].startswith("fbrsr:agent/filebrsr-calculator@")

    # Software agent — never an LLM (principle #1).
    agent = nodes[activity["wasAssociatedWith"]]
    assert "prov:SoftwareAgent" in agent["@type"]


def test_no_input_records_omits_derivation():
    graph = build_calculation_graph(_input(input_record_ids=[]))
    output = next(n for n in graph["@graph"] if n["@id"] == "fbrsr:calculation/calc-1")
    assert "wasDerivedFrom" not in output


# ─── Signing + verification ───────────────────────────────────────────────

def test_build_signed_provenance_verifies():
    reset_signer()
    signed = build_signed_provenance(_input())
    assert signed.algorithm == "Ed25519"
    assert verify_signed_provenance(signed) is True


def test_tampering_with_graph_fails_verification():
    reset_signer()
    signed = build_signed_provenance(_input())
    # Mutate a disclosed value after signing.
    output = next(
        n for n in signed.graph["@graph"] if n["@id"] == "fbrsr:calculation/calc-1"
    )
    output["fbrsr:value"] = "9999999"
    assert verify_signed_provenance(signed) is False


def test_tampering_with_hash_fails_verification():
    reset_signer()
    signed = build_signed_provenance(_input())
    object.__setattr__(signed, "canonical_sha256", "deadbeef")
    assert verify_signed_provenance(signed) is False


def test_wrong_public_key_rejected():
    reset_signer()
    canonical, _ = canonical_hash(build_calculation_graph(_input()))
    signer = LocalEd25519Signer.from_seed_b64(_FIXED_SEED_B64, "k1")
    sig = signer.sign(canonical)
    other = LocalEd25519Signer.ephemeral()
    assert verify(canonical, sig, signer.public_key_b64()) is True
    assert verify(canonical, sig, other.public_key_b64()) is False


def test_fixed_seed_is_reproducible():
    # Ed25519 is deterministic: same key + same message → same signature.
    s1 = LocalEd25519Signer.from_seed_b64(_FIXED_SEED_B64, "k1")
    s2 = LocalEd25519Signer.from_seed_b64(_FIXED_SEED_B64, "k1")
    canonical, _ = canonical_hash(build_calculation_graph(_input()))
    assert s1.sign(canonical) == s2.sign(canonical)
    assert s1.public_key_b64() == s2.public_key_b64()


# ─── Property-based ───────────────────────────────────────────────────────

_id_text = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122), min_size=1, max_size=20
)


@given(
    value=st.decimals(allow_nan=False, allow_infinity=False, places=4),
    record_ids=st.lists(_id_text, max_size=5),
    org_id=_id_text,
)
def test_roundtrip_signs_and_verifies(value, record_ids, org_id):
    reset_signer()
    signed = build_signed_provenance(
        _input(value=value, input_record_ids=record_ids, org_id=org_id)
    )
    assert verify_signed_provenance(signed) is True
    # Re-canonicalising the same graph yields the same digest.
    assert canonical_hash(signed.graph)[1] == signed.canonical_sha256


@given(seed=st.binary(min_size=32, max_size=32))
def test_any_valid_seed_signs_and_verifies(seed):
    signer = LocalEd25519Signer.from_seed_b64(base64.b64encode(seed).decode(), "k")
    msg = b"audit-grade-message"
    sig = signer.sign(msg)
    assert verify(msg, sig, signer.public_key_b64()) is True


def test_sign_graph_matches_build_signed_provenance_digest():
    reset_signer()
    graph = build_calculation_graph(_input())
    assert sign_graph(graph).canonical_sha256 == canonical_hash(graph)[1]
