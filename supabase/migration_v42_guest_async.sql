-- Guest async extraction: allow anonymous (worker-processed) reports/jobs.
-- Guests have no auth.users / profiles row, so user_id must be nullable.
-- Existing rows are unaffected (all have user_id set).
alter table public.reports alter column user_id drop not null;
alter table public.reports
  add column if not exists is_guest boolean not null default false;

alter table public.extraction_jobs alter column user_id drop not null;

create index if not exists idx_reports_guest_created
  on public.reports (created_at) where is_guest;
