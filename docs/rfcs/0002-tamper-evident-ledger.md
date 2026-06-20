# RFC 0002 — Tamper-evident Merkle ledger

- Status: **Accepted** (Phase D of provenance hardening, 2026-06-20)
- Date: 2026-06-20
- Principle: #3 (provenance first-class)
- Author: Founding engineer

## Summary

FileBRSR's audit trail today is a plain append-only table (`audit_log`,
migration v15) plus a 1:1 signed PROV-O record per calculation
(`provenance_records`, v16). Neither is *cryptographically* tamper-evident
against an actor with write access to the database — a row can be edited and
the log entry simply not written.

This RFC adds a **transparency log**: every audit-critical event becomes an
RFC 6962 (Certificate Transparency) Merkle leaf, and each new tree head is
Ed25519-signed by the same key used for provenance (`app.prov`). Mutating any
stored row breaks both the leaf recomputation and the signed root, so an
auditor — or the public `/verify` surface — can detect it.

It **augments, not replaces**, `audit_log`/`fn_audit_log`.

## Design

- Tables (`migration_v17_merkle_ledger.sql`):
  - `ledger_leaves(org_id, leaf_index, event_type, ref_table, ref_pk,
    leaf_sha256, payload, created_at)` — one ordered leaf per event per org.
  - `ledger_roots(org_id, tree_size, merkle_root, prev_root,
    root_signature_b64, public_key_b64, key_id, signed_at, anchor)` — a signed,
    hash-chained tree head after each append.
- Hashing: RFC 6962 domain separation — leaves `SHA-256(0x00 || canonical)`,
  nodes `SHA-256(0x01 || left || right)` (`app.ledger.merkle`). Payloads are
  canonicalised with RFC 8785 (JCS), same as provenance graphs.
- Append + sign: `app.ledger.service.append_event` inserts the leaf, recomputes
  the root over all leaves, signs the head, inserts the root. Wired into the
  live calculation path via a FastAPI **background task** so it never slows the
  submit response (NFR).
- Proofs: inclusion proofs (`get_inclusion_proof`) are surfaced on the public
  `/api/verify/{id}` + `/bundle`. Consistency proofs are implemented in
  `merkle.py` for future gossip/audit.

## Threat model

| Adversary | Can they forge undetectably? |
|---|---|
| App bug / API role rewriting a calc | **No** — leaf recompute + inclusion proof fail; UPDATE/DELETE revoked + append-only trigger. |
| App role editing the ledger | **No** — `fn_ledger_append_only` trigger raises on UPDATE/DELETE. |
| DB superuser (bypasses triggers) | **Partially** — can rewrite leaves AND re-sign roots *if* they also hold the signing key. Mitigated by (a) keeping the key in KMS envelope (not in the DB), and (b) external anchoring (below). Without the key, any rewrite invalidates every signed root from that point. |
| Holder of the signing key | Can re-sign a forged history. Mitigated only by external anchoring to an append-only third party. |

So: append-only here is an **application + trigger** property, not a
cryptographic guarantee against a superuser who also holds the signing key.
The signed roots raise the bar (you must compromise KMS too); true
irreversibility requires anchoring the root somewhere the operator can't
rewrite.

## Anchoring (pluggable, future)

`ledger_roots.anchor` (jsonb) holds an external anchor for each head. The
interface is intentionally open:

1. **Phase D (now)**: Ed25519-signed roots only.
2. **Next**: RFC 3161 Timestamping Authority (TSA) token over the root — gives
   a trusted-time, operator-independent attestation.
3. **Later**: periodic public anchor (e.g. a public CT log or chain) for full
   public verifiability.

## Out of scope

- Public blockchain anchoring (interface only).
- Gossip/audit protocol between independent monitors.
- Witness co-signing of roots.
