"""
W3C PROV-O graph builder for calculated emission figures.

Builds a JSON-LD PROV-O document that asserts, for one calculated number:

* the **output** entity (the emission figure) ``wasGeneratedBy`` the
  calculation **activity**, ``wasDerivedFrom`` each raw-record input entity,
  and ``used`` the versioned emission-factor entity;
* the activity ``wasAssociatedWith`` the software agent (the deterministic
  calculator, by version) — never an LLM (principle #1);
* every numeric quantity is serialised as a **string** so the canonical form
  carries no JSON float (see :mod:`app.prov.canonicalize`).

The resulting graph is canonicalised (RFC 8785), SHA-256 hashed, and
Ed25519-signed via :mod:`app.prov.signing`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.prov.canonicalize import canonical_hash
from app.prov.models import CalculationProvenanceInput, SignedProvenance
from app.prov.signing import get_signer

# JSON-LD context. ``fbrsr`` is our tenant-namespaced identifier base.
PROV_CONTEXT: dict[str, Any] = {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "fbrsr": "https://filebrsr.com/prov#",
    "wasGeneratedBy": {"@id": "prov:wasGeneratedBy", "@type": "@id"},
    "wasDerivedFrom": {"@id": "prov:wasDerivedFrom", "@type": "@id"},
    "wasAssociatedWith": {"@id": "prov:wasAssociatedWith", "@type": "@id"},
    "wasAttributedTo": {"@id": "prov:wasAttributedTo", "@type": "@id"},
    "used": {"@id": "prov:used", "@type": "@id"},
    "startedAtTime": {"@id": "prov:startedAtTime", "@type": "xsd:dateTime"},
    "endedAtTime": {"@id": "prov:endedAtTime", "@type": "xsd:dateTime"},
}


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


def build_calculation_graph(inp: CalculationProvenanceInput) -> dict[str, Any]:
    """Construct the PROV-O JSON-LD graph for one calculation (unsigned)."""
    calc_iri = f"fbrsr:calculation/{inp.calculation_id}"
    activity_iri = f"fbrsr:activity/{inp.agent_run_id or inp.calculation_id}"
    factor_iri = f"fbrsr:factor/{inp.factor_id}@{inp.factor_version}"
    agent_iri = f"fbrsr:agent/{inp.software_agent}@{inp.software_agent_version}"
    ts = _iso(inp.calculation_timestamp)

    input_iris = [f"fbrsr:record/{rid}" for rid in inp.input_record_ids]

    output_entity: dict[str, Any] = {
        "@id": calc_iri,
        "@type": "prov:Entity",
        "fbrsr:value": str(inp.value),
        "fbrsr:unit": inp.unit,
        "fbrsr:method": inp.method,
        "fbrsr:orgId": inp.org_id,
        "wasGeneratedBy": activity_iri,
        "wasAttributedTo": agent_iri,
        "used": factor_iri,
    }
    if input_iris:
        output_entity["wasDerivedFrom"] = input_iris
    if inp.uncertainty is not None:
        output_entity["fbrsr:uncertainty"] = _stringify(inp.uncertainty)

    factor_entity: dict[str, Any] = {
        "@id": factor_iri,
        "@type": "prov:Entity",
        "fbrsr:factorId": inp.factor_id,
        "fbrsr:factorVersion": inp.factor_version,
    }
    if inp.factor_source:
        factor_entity["fbrsr:source"] = inp.factor_source
    if inp.factor_citation:
        factor_entity["fbrsr:citationUrl"] = inp.factor_citation

    activity: dict[str, Any] = {
        "@id": activity_iri,
        "@type": "prov:Activity",
        "startedAtTime": ts,
        "endedAtTime": ts,
        "used": [factor_iri, *input_iris],
        "wasAssociatedWith": agent_iri,
    }

    agent = {
        "@id": agent_iri,
        "@type": ["prov:SoftwareAgent", "prov:Agent"],
        "fbrsr:name": inp.software_agent,
        "fbrsr:version": inp.software_agent_version,
    }

    record_entities = [
        {"@id": iri, "@type": "prov:Entity", "fbrsr:kind": "raw_record"}
        for iri in input_iris
    ]

    return {
        "@context": PROV_CONTEXT,
        "@graph": [output_entity, factor_entity, activity, agent, *record_entities],
    }


def _stringify(obj: Any) -> Any:
    """Recursively coerce numbers to strings so the canonical form has no floats."""
    if isinstance(obj, dict):
        return {k: _stringify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return str(obj)
    return obj


def sign_graph(graph: dict[str, Any]) -> SignedProvenance:
    """Canonicalise, hash, and Ed25519-sign a PROV-O graph."""
    canonical, digest_hex = canonical_hash(graph)
    signer = get_signer()
    signature = signer.sign(canonical)
    import base64

    return SignedProvenance(
        graph=graph,
        canonical_sha256=digest_hex,
        signature_b64=base64.b64encode(signature).decode("ascii"),
        public_key_b64=signer.public_key_b64(),
        algorithm="Ed25519",
        key_id=signer.key_id,
        signed_at=_iso(datetime.now(timezone.utc)),
    )


def build_signed_provenance(inp: CalculationProvenanceInput) -> SignedProvenance:
    """End-to-end: build the PROV-O graph for a calculation and sign it."""
    graph = build_calculation_graph(inp)
    return sign_graph(graph)
