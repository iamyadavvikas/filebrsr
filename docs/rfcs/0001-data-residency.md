# RFC 0001 — Data Residency: AWS Mumbai (ap-south-1) only

- Status: **Accepted** (founder committed to AWS Mumbai, 2026-06-11)
- Date: 2026-06-11
- Principle: #6 (Data sovereignty by default)
- Author: Founding engineer

## Summary

All data-bearing infrastructure for FileBRSR must reside in **AWS
`ap-south-1` (Mumbai)**. This RFC records the decision, the current
deviation, and the migration required to comply.

## Why this needs founder approval

The charter lists "Changes to the data residency or auth stack" as an
`[APPROVAL NEEDED]` decision, and data sovereignty is one of the seven
non-negotiable principles. The pitch ("priced for the mid-cap segment…
audit-grade for PSU/banking customers under RBI / SEBI / DPDPA 2023")
depends on single-region isolation in India. Customers in regulated sectors
will reject a vendor whose data leaves India.

## Current state (the deviation)

- `deploy-gcp.sh` and `docker-compose.prod.yml` target **GCP Cloud Run** in
  `asia-south1` (Mumbai). Data is geographically in India, but on **GCP, not
  AWS** — so it does not satisfy the charter's AWS `ap-south-1` + KMS posture.
- Supabase project region is **not pinned/confirmed** to an India region.
- No region assertion existed at runtime.

This contradicts principle #6 (AWS Mumbai, customer-held KMS, single-region
isolation for PSU/banking). Note: GCP `asia-south1` is *physically* Mumbai,
so this is a cloud-vendor migration, not a geographic one.

## Decision

1. **Target region:** AWS `ap-south-1` for all compute, object storage,
   database, queues, and KMS. Single-region full isolation must be
   achievable for PSU/banking tenants.
2. **Database:** Supabase project pinned to an India region (`ap-south-1`),
   or self-hosted Postgres on AWS Mumbai. If Supabase cannot guarantee
   `ap-south-1`, migrate to RDS/Aurora Postgres in Mumbai.
3. **Object storage:** S3 in `ap-south-1` (MinIO locally).
4. **Signing keys:** AWS KMS in `ap-south-1`; customer-held KMS keys
   supported for isolated tenants (see RFC 0002).

## Implemented in this change (Phase-1 scaffolding)

- `Settings.DATA_REGION` (default `ap-south-1`) in `backend/app/config.py`.
- `organizations.data_region` column **CHECK-constrained to `ap-south-1`**
  (`migration_v15_tenancy.sql`).
- Startup guard `_assert_data_residency()` in `backend/app/main.py`:
  **raises in production**, warns in dev, if `DATA_REGION != ap-south-1`.

## Migration plan (post-approval, not in this change)

1. Confirm/relocate Supabase to `ap-south-1` (or plan RDS migration).
2. Replace `deploy-gcp.sh` with AWS Mumbai deploy (ECS/EKS + S3 + KMS).
3. Provision AWS KMS Ed25519 (or asymmetric) key in `ap-south-1`; set
   `PROV_SIGNING_KMS_KEY_ID` and wire `KmsSigner` in `app/prov/signing.py`.
4. Verify backups (daily PG snapshot → S3, 30-day retention) stay in-region.

## Open questions for the founder

1. Is the GCP deploy intentional/temporary, or do we commit to AWS Mumbai now?
2. Is the current Supabase project already in an India region? If not, do we
   migrate Supabase or move to RDS/Aurora in `ap-south-1`?
3. Do any near-term target customers require **customer-held KMS keys** /
   single-tenant isolation in V1, or can that wait for Phase 5?
