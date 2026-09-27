-- Migration V35: assurance providers + ISAE 3000 workpapers (BRSR Core)
-- ==========================================================================
-- Unlocks assurance revenue: who assures, and the workpaper trail behind
-- every limited/reasonable opinion.
--
--   * assurance_providers — firms/partners per org: registration, peer-review
--     validity, independence declaration, rotation clock (partner rotation
--     per CA Act norms), status.
--   * assurance_workpapers — per (org, FY, KPI, checkpoint) ISAE 3000 trail:
--     status open/closed/na, evidence reference, preparer/reviewer, close
--     timestamp. Checkpoint catalog lives in app/brsr_workpapers.py.
--   * brsr_core_assurance.provider_id — optional link from a KPI row to its
--     provider (provider_name stays as the display label).
--
-- RLS mirrors the org_members policies (v32/v33). Additive + idempotent.
-- Run AFTER migration_v34_dma_pack.sql.
-- ==========================================================================

-- 1. Providers ---------------------------------------------------------------
create table if not exists public.assurance_providers (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  firm_name text not null,
  partner_name text,
  registration_no text,
  peer_review_valid_until date,
  independence_declared_on date,
  rotation_started_on date,
  contact_email text,
  status text not null default 'active'
    check (status in ('active', 'rotated', 'suspended')),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, firm_name, partner_name)
);

create index if not exists assurance_providers_org_idx
  on public.assurance_providers(org_id);

alter table public.assurance_providers enable row level security;

drop policy if exists "Org members can view assurance providers"
  on public.assurance_providers;
create policy "Org members can view assurance providers"
  on public.assurance_providers for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

drop policy if exists "Org members can manage assurance providers"
  on public.assurance_providers;
create policy "Org members can manage assurance providers"
  on public.assurance_providers for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));

-- 2. Workpapers --------------------------------------------------------------
create table if not exists public.assurance_workpapers (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  financial_year text not null check (financial_year ~ '^FY[0-9]{4}-[0-9]{2}$'),
  kpi_code text not null check (kpi_code ~ '^BRSC-[0-9]+\.[0-9]+$'),
  checkpoint text not null,
  detail text,
  status text not null default 'open'
    check (status in ('open', 'closed', 'not_applicable')),
  evidence_ref text,
  prepared_by text,
  reviewed_by text,
  closed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, financial_year, kpi_code, checkpoint)
);

create index if not exists assurance_workpapers_org_fy_idx
  on public.assurance_workpapers(org_id, financial_year);

create index if not exists assurance_workpapers_status_idx
  on public.assurance_workpapers(status);

alter table public.assurance_workpapers enable row level security;

drop policy if exists "Org members can view assurance workpapers"
  on public.assurance_workpapers;
create policy "Org members can view assurance workpapers"
  on public.assurance_workpapers for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

drop policy if exists "Org members can manage assurance workpapers"
  on public.assurance_workpapers;
create policy "Org members can manage assurance workpapers"
  on public.assurance_workpapers for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));

-- 3. Link KPI rows to providers ----------------------------------------------
alter table public.brsr_core_assurance
  add column if not exists provider_id uuid references public.assurance_providers(id) on delete set null;

comment on table public.assurance_providers is
  'Assurance firms/partners per org: registration, peer review, independence, rotation clock.';

comment on table public.assurance_workpapers is
  'ISAE 3000 workpaper trail per BRSR Core KPI checkpoint (catalog in app/brsr_workpapers.py).';
