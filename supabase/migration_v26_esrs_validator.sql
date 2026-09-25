-- Migration V26: CSRD / ESRS filing — ESEF pre-flight validation & retry
-- ==========================================================================
-- Persists the outcome of the ESEF pre-flight validator on generated reports
-- (submission now requires validation_status = 'pass') and tracks webhook
-- retry/error state on regulator submissions (one submission per report).
-- Idempotent. Run AFTER migration_v25_esrs_filing.sql.
-- ==========================================================================

-- 1. Validation outcome on esrs_reports -----------------------------
alter table public.esrs_reports
  add column if not exists validation_status text not null default 'unvalidated'
    check (validation_status in ('unvalidated', 'pass', 'fail')),
  add column if not exists validation_summary jsonb not null default '{}'::jsonb,
  add column if not exists validated_at     timestamptz;

-- 2. Retry / error state on esrs_submissions ------------------------
alter table public.esrs_submissions
  add column if not exists retry_count int not null default 0,
  add column if not exists last_error  text;

-- One submission per report (idempotent re-submission + retry key).
create unique index if not exists esrs_submissions_report_uq
  on public.esrs_submissions(report_id);

-- Backfill: already-submitted rows were implicitly "passing" (they predate
-- the validator) — leave statuses as-is and only mark old queued_local rows.
update public.esrs_reports
   set validation_status = 'unvalidated'
 where validation_status is null;

comment on column public.esrs_reports.validation_status is
  'Outcome of the ESEF pre-flight validation ('"'"'pass'"'"' required before submit).';