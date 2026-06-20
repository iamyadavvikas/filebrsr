# RFC 0003 — Privacy-preserving (zero-knowledge) verification

- Status: **Draft / design-only** (Phase E scaffold landed 2026-06-20)
- Date: 2026-06-20
- Principle: #3 (provenance first-class) + confidentiality of value-chain data
- Author: Founding engineer

## Problem

The public `/verify` surface (RFC 0002 / Phase C) proves a disclosed *aggregate*
is authentic. But customers want to prove **claims about confidential inputs**
without revealing them:

- A buyer wants to prove "our verified Scope-3 reduction is ≥ 20% YoY" to a
  regulator/rating agency without publishing supplier-level figures.
- A supplier wants to prove "my emission intensity is within the buyer's
  threshold" without revealing absolute volumes (commercially sensitive).

Today the provenance graph would have to embed the raw input to be verifiable —
which leaks it. We need to verify a *statement* about the value, not the value.

## Approach

1. **Commit, don't reveal.** Store a binding+hiding **commitment** to each
   confidential input in the provenance graph instead of the raw number.
   - `app.zk.commitments.hash_commit` — `SHA-256(blinding || value)`. Production
     usable now for "reveal later" / selective disclosure.
   - `pedersen_commit` — additively homomorphic, needed for range/sum proofs.
     **Stub** (raises) until the curve + generators are fixed below.
2. **Prove statements over commitments.** `app.zk.claims` fixes the statement
   types and the `Prover`/`Verifier` interface:
   - `RangeClaim` — committed value ∈ [lower, upper].
   - `ReductionClaim` — `(baseline − current)/baseline ≥ min_fraction`.
   - `Proof` — opaque blob + public inputs, tagged with the proving system.

## Proving-system options (decision pending)

| System | Pros | Cons | Fit |
|---|---|---|---|
| **Bulletproofs** | No trusted setup; compact range proofs; good for "≥ X" | Prover/verifier slower than SNARKs at scale | **Leading candidate** for range/reduction claims |
| **Groth16** | Tiny proofs, fast verify | Per-circuit trusted setup (ceremony) | Good if circuits stabilise |
| **PLONK / Halo2** | Universal/updatable setup | Heavier tooling | Future if circuits proliferate |

Recommendation: start with **Bulletproofs** over a NUMS-generator Ristretto255
group for range/reduction claims (no trusted setup — important for a compliance
vendor's credibility), revisit SNARKs only if proof size/verify cost matters.

## Reveal-vs-hide policy

- **Aggregates** an entity discloses publicly (e.g. total Scope 1+2): revealed,
  signed, on `/verify` as today.
- **Value-chain inputs** (supplier-level): committed on-graph; revealed only to
  authorised auditors (bundle) or proven in zero-knowledge to third parties.
- The provenance builder will gain an option to substitute a `Commitment` for a
  raw `input_record` when the input is flagged confidential.

## Scope of Phase E (this RFC)

- ✅ Hash commitments (usable), Pedersen + Prover/Verifier interfaces (stubs).
- ✅ Statement dataclasses (`RangeClaim`, `ReductionClaim`).
- ❌ NOT in scope: production circuits, trusted-setup ceremony, on-graph
  commitment substitution wiring. Those follow once the system above is chosen.
