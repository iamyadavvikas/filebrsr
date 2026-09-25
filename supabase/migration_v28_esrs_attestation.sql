-- Migration V28: CSRD / ESRS filing — auditor attestation & QES signature
-- ==========================================================================
-- An auditor attests the ESEF report before it may be submitted (gate in
-- /reports/{id}/submit). The delivered package then carries a detached QES
-- (Ed25519) signature over the manifest digest so the OAM can verify the
-- bundle's integrity without a live signing gateway.
-- Idempotent. Run AFTER migration_v27_esrs_oam_ack.sql.
-- ==========================================================================

alter table public.esrs_reports
  add column if not exists attested_by          text,
  add column if not exists attested_at          timestamptz,
  add column if not exists attestation_statement text;

alter table public.esrs_submissions
  add column if not exists qes_algorithm       text,
  add column if not exists qes_key_id          text,
  add column if not exists qes_signature_b64   text,
  add column if not exists qes_public_key_b64  text,
  add column if not exists qes_manifest_digest text;

comment on column public.esrs_reports.attested_by is
  'Auditor/principal who attested the ESEF report (gate for submission).';
comment on column public.esrs_submissions.qes_signature_b64 is
  'Detached Ed25519 signature over the manifest digest (SHA-256 of manifest.json inside the package).';
comment on column public.esrs_submissions.qes_manifest_digest is
  'SHA-256 of manifest.json — the exact bytes covered by qes_signature_b64.';