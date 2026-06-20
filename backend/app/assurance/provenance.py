"""W3C PROV provenance graph from the assurance ledger.

Ported from CarbonTrace's ``provenance.builder`` but emits PROV-JSON **manually**
(plain dict-building) so FileBRSR doesn't take a dependency on the ``prov`` /
``lxml`` / ``rdflib`` / ``graphviz`` stack. The PROV data model mapping is the
same:

* **Entity**   — a material *batch* at a stage (ore lot, concentrate, refined
  metal, cell/pack), carrying stage/material/quantity/emissions attributes.
* **Activity** — the *transformation* that produced the batch.
* **Agent**    — the *supplier* organisation responsible.

Edges: ``wasGeneratedBy`` (batch ← activity), ``wasAssociatedWith``
(activity ← supplier), ``used`` (activity ← upstream batch) and
``wasDerivedFrom`` (batch ← upstream batch) — the chain an auditor follows.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.assurance.factors import ACTIVITY_LABEL
from app.assurance.ledger import SignedEntry

CT_NS = "https://filebrsr.com/prov#"
CT_PREFIX = "ct"


def _q(local: str) -> str:
    return f"{CT_PREFIX}:{local}"


@dataclass(frozen=True)
class ProvenanceStats:
    """Data-quality summary of the provenance graph."""

    batches: int
    derived_edges: int
    roots: int
    dangling_parents: int
    completeness_ratio: float


def _lineage(entries: list[SignedEntry], batch_id: str) -> list[SignedEntry]:
    """Return ``batch_id`` and all of its transitive ancestors (upstream chain)."""
    by_batch = {e.record.batch_id: e for e in entries}
    chain: list[SignedEntry] = []
    seen: set[str] = set()
    cursor: str | None = batch_id
    while cursor and cursor in by_batch and cursor not in seen:
        seen.add(cursor)
        entry = by_batch[cursor]
        chain.append(entry)
        cursor = entry.record.parent_batch_id
    return chain


def build_prov_json(
    entries: list[SignedEntry], *, batch_id: str | None = None
) -> dict:
    """Build a W3C PROV-JSON document for the whole ledger or a single lineage."""
    selected = _lineage(entries, batch_id) if batch_id else list(entries)
    present = {e.record.batch_id for e in selected}

    doc: dict[str, dict] = {
        "prefix": {CT_PREFIX: CT_NS},
        "entity": {},
        "activity": {},
        "agent": {},
        "wasGeneratedBy": {},
        "wasAssociatedWith": {},
        "used": {},
        "wasDerivedFrom": {},
    }

    for n, e in enumerate(selected):
        r = e.record
        ent_id = _q(f"batch/{r.batch_id}")
        act_id = _q(f"{ACTIVITY_LABEL.get(r.stage.value, r.stage.value)}/{r.batch_id}")
        agent_id = _q(f"org/{r.supplier_id}")

        doc["entity"][ent_id] = {
            _q("stage"): r.stage.value,
            _q("material"): r.material,
            _q("quantityKg"): str(r.quantity_kg),
            _q("emissionsKgCO2e"): str(r.emissions_kg_co2e),
            _q("region"): r.region,
            _q("recordHash"): e.leaf_hex,
        }
        doc["activity"][act_id] = {}
        doc["agent"][agent_id] = {_q("role"): "supplier"}
        doc["wasGeneratedBy"][f"_:gen{n}"] = {
            "prov:entity": ent_id,
            "prov:activity": act_id,
        }
        doc["wasAssociatedWith"][f"_:assoc{n}"] = {
            "prov:activity": act_id,
            "prov:agent": agent_id,
        }
        if r.parent_batch_id and r.parent_batch_id in present:
            parent_id = _q(f"batch/{r.parent_batch_id}")
            doc["used"][f"_:used{n}"] = {"prov:activity": act_id, "prov:entity": parent_id}
            doc["wasDerivedFrom"][f"_:der{n}"] = {
                "prov:generatedEntity": ent_id,
                "prov:usedEntity": parent_id,
            }

    return doc


def build_graph(entries: list[SignedEntry], *, batch_id: str | None = None) -> dict:
    """Simplified nodes/edges view for direct UI rendering."""
    selected = _lineage(entries, batch_id) if batch_id else list(entries)
    present = {e.record.batch_id for e in selected}
    nodes = [
        {
            "id": e.record.batch_id,
            "stage": e.record.stage.value,
            "material": e.record.material,
            "supplier": e.record.supplier_id,
            "emissions_kg_co2e": str(e.record.emissions_kg_co2e),
            "region": e.record.region,
            "record_hash": e.leaf_hex[:16],
        }
        for e in selected
    ]
    edges = [
        {"from": e.record.parent_batch_id, "to": e.record.batch_id, "rel": "wasDerivedFrom"}
        for e in selected
        if e.record.parent_batch_id and e.record.parent_batch_id in present
    ]
    return {"nodes": nodes, "edges": edges}


def provenance_stats(entries: list[SignedEntry]) -> ProvenanceStats:
    """Completeness = fraction of non-root batches whose parent is present."""
    present = {e.record.batch_id for e in entries}
    with_parent = [e for e in entries if e.record.parent_batch_id]
    roots = len(entries) - len(with_parent)
    dangling = sum(1 for e in with_parent if e.record.parent_batch_id not in present)
    resolvable = len(with_parent) - dangling
    ratio = (resolvable / len(with_parent)) if with_parent else 1.0
    return ProvenanceStats(
        batches=len(entries),
        derived_edges=resolvable,
        roots=roots,
        dangling_parents=dangling,
        completeness_ratio=round(ratio, 4),
    )
