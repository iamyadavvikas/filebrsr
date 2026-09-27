-- Migration V25: CSRD / ESRS filing — assurance & OAM submission
-- ==========================================================================
-- Adds a limited/reasonable assurance opinion to generated ESRS reports
-- (required precondition for filing under CSRD) and persists regulator
-- (OAM) submissions of the ESEF single-file artifact.
-- Idempotent. Run AFTER migration_v24_esrs_profiles.sql.
-- ==========================================================================

-- 1. Assurance opinion columns on esrs_reports ----------------------------
alter table public.esrs_reports
  add column if not exists assurance_status   text not null default 'none'
    check (assurance_status in ('none', 'limited', 'reasonable')),
  add column if not exists assurance_firm     text,
  add column if not exists assurance_date     text,
  add column if not exists assurance_statement text;

-- 2. Submission log -------------------------------------------------------
create table if not exists public.esrs_submissions (
  id               uuid primary key default gen_random_uuid(),
  org_id           uuid not null references public.organizations(id) on delete cascade,
  report_id        uuid not null references public.esrs_reports(id) on delete cascade,
  financial_year   text not null,
  status           text not null default 'queued_local',  -- queued_local | submitted | webhook_failed:*
  submission_ref   text not null,                         -- OAM filing reference when acknowledged
  manifest_sha256  text not null,                         -- sha256 of the packaged zip
  package_sha256   text not null,                         -- sha256 of the esrs_statement.html inside
  submitted_by     uuid references public.profiles(id),
  created_at       timestamptz not null default now()
);

create index if not exists esrs_submissions_org_fy_idx
  on public.esrs_submissions(org_id, financial_year, created_at desc);

alter table public.esrs_submissions enable row level security;

drop policy if exists "Org members can read esrs submissions" on public.esrs_submissions;
create policy "Org members can read esrs submissions"
  on public.esrs_submissions for select
  using (public.user_in_org(org_id));

drop policy if exists "Org members can insert esrs submissions" on public.esrs_submissions;
create policy "Org members can insert esrs submissions"
  on public.esrs_submissions for insert
  with check (public.user_in_org(org_id));

comment on table public.esrs_submissions is
  'Regulator (OAM) submissions of ESEF single-file reports with assurance opinion.';