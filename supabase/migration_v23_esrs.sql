-- Migration V23: CSRD / ESRS reporting workspace
-- ==========================================================================
-- Backs the CSRD platform (products + /platform/csrd workspace). The static
-- ESRS Set 1 datapoint registry lives in the backend (app/esrs_datapoints.py,
-- keyed by the standards' own paragraph references, e.g. "E1-6.44"). These
-- tables persist the ORG's live assessment:
--
--   esrs_entries      one row per (org, financial year, datapoint) — the
--                     gap-analysis status, the entered value + evidence, and
--                     the materiality link (material IRO that drives it).
--   esrs_materiality  double materiality assessment — the org's material
--                     impacts, risks and opportunities (IROs) scored for
--                     impact (inside-out) and financial (outside-in) materiality.
--   esrs_reports      artifacts of generated ESRS sustainability statements
--                     (Word / PDF / EFRAG-export), immutable snapshots.
--
-- Idempotent. Run AFTER migration_v15_tenancy.sql (user_in_org, update_updated_at).
-- ==========================================================================

-- ─── esrs_materiality (double materiality IRO register) ────────────────────
-- Each row is a material impact, risk or opportunity. severity/likelihood are
-- 1-5 scales; impact_materiality = how significant the undertaking's impact on
-- people/planet/environment IS or COULD BE (inside-out); financial_materiality =
-- how significant the IRO IS or COULD BE for the financial position (outside-in).

create table if not exists public.esrs_materiality (
  id                    uuid primary key default gen_random_uuid(),
  org_id                uuid not null references public.organizations(id) on delete cascade,
  financial_year        text not null,                  -- e.g. 'FY2025'
  iro_type              text not null
                          check (iro_type in ('impact', 'risk', 'opportunity')),
  standard              text not null,                  -- '2' | 'E1'..'G1' (registry facet)
  title                 text not null,
  description           text,
  severity              int check (severity between 1 and 5),
  likelihood            int check (likelihood between 1 and 5),
  impact_materiality    numeric(3,2) check (impact_materiality between 0 and 5),
  financial_materiality numeric(3,2) check (financial_materiality between 0 and 5),
  material              boolean not null default false, -- meets both thresholds
  status                text not null default 'draft'
                          check (status in ('draft', 'assessed', 'approved')),
  created_by            uuid references public.profiles(id) on delete set null,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create index if not exists esrs_materiality_org_year_idx
  on public.esrs_materiality (org_id, financial_year);
create index if not exists esrs_materiality_standard_idx
  on public.esrs_materiality (standard);

-- ─── esrs_entries (per-datapoint assessment + data) ────────────────────────
-- datapoint_id references the backend registry ids (e.g. 'E1-6.44',
-- 'ESRS2.GOV-1.21', 'S1-IRO-1.AR9'). status drives the gap analysis.
-- materiality_id optionally links the datapoint to the material IRO that
-- makes it reportable (non-limited datapoints).

create table if not exists public.esrs_entries (
  id                  uuid primary key default gen_random_uuid(),
  org_id              uuid not null references public.organizations(id) on delete cascade,
  user_id             uuid not null references public.profiles(id) on delete cascade,
  financial_year      text not null,
  datapoint_id        text not null,                    -- 'E1-6.44', no FK (registry is code)
  status              text not null default 'not_assessed'
                        check (status in (
                          'not_assessed', 'not_applicable', 'not_material',
                          'assessed', 'in_progress', 'reported'
                        )),
  materiality_id      uuid references public.esrs_materiality(id) on delete set null,
  value               jsonb,                            -- flexible: text, number, table, list
  evidence            text,                             -- links / doc refs supporting the value
  source              text check (source in ('manual', 'ai_extracted', 'imported', 'calculated')),
  source_document     text,
  confidence_score    decimal(3,2) check (confidence_score between 0 and 1),
  notes               text,
  verified            boolean not null default false,
  verified_by         uuid references public.profiles(id) on delete set null,
  verified_at         timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (org_id, financial_year, datapoint_id)
);

create index if not exists esrs_entries_org_year_idx
  on public.esrs_entries (org_id, financial_year, status);
create index if not exists esrs_entries_datapoint_idx
  on public.esrs_entries (datapoint_id);

-- ─── esrs_reports (generated statement artifacts, immutable snapshots) ─────

create table if not exists public.esrs_reports (
  id                uuid primary key default gen_random_uuid(),
  org_id            uuid not null references public.organizations(id) on delete cascade,
  financial_year    text not null,
  report_type       text not null check (report_type in ('word', 'pdf', 'efrag_export', 'esef')),
  status            text not null default 'queued'
                      check (status in ('queued', 'generating', 'ready', 'failed')),
  file_url          text,
  file_sha256       text,                               -- content checksum (provenance)
  file_size_bytes   bigint,
  datapoints_covered int not null default 0,
  coverage_pct      numeric(5,2),                       -- covered / registry size for the year
  error             text,
  created_by        uuid references public.profiles(id) on delete set null,
  created_at        timestamptz not null default now()
);

create index if not exists esrs_reports_org_year_idx
  on public.esrs_reports (org_id, financial_year, created_at desc);

-- ─── updated_at maintenance ────────────────────────────────────────────────

drop trigger if exists trg_esrs_materiality_updated_at on public.esrs_materiality;
create trigger trg_esrs_materiality_updated_at
  before update on public.esrs_materiality
  for each row execute function public.update_updated_at();

drop trigger if exists trg_esrs_entries_updated_at on public.esrs_entries;
create trigger trg_esrs_entries_updated_at
  before update on public.esrs_entries
  for each row execute function public.update_updated_at();

-- ─── RLS (org-scoped; writes via service role in the backend) ──────────────
-- Defence-in-depth: a direct PostgREST session can only read/write what they
-- are allowed for orgs they belong to. Mirrors v16 provenance conventions.
-- write for orgs they belong to. Mirrors v16 provenance conventions.

alter table public.esrs_materiality enable row level security;
alter table public.esrs_entries     enable row level security;
alter table public.esrs_reports     enable row level security;

drop policy if exists "Org members can manage esrs materiality" on public.esrs_materiality;
create policy "Org members can manage esrs materiality"
  on public.esrs_materiality for all
  using (public.user_in_org(org_id))
  with check (public.user_in_org(org_id));

drop policy if exists "Org members can manage esrs entries" on public.esrs_entries;
create policy "Org members can manage esrs entries"
  on public.esrs_entries for all
  using (public.user_in_org(org_id))
  with check (public.user_in_org(org_id));

drop policy if exists "Org members can read esrs reports" on public.esrs_reports;
create policy "Org members can read esrs reports"
  on public.esrs_reports for select
  using (public.user_in_org(org_id));

-- ─── comments ──────────────────────────────────────────────────────────────

comment on table public.esrs_materiality is
  'Double-materiality IRO register (impacts, risks, opportunities) scored 1-5 for impact and financial materiality.';
comment on table public.esrs_entries is
  'Per-datapoint assessment and data for the ESRS registry (gap analysis unit). datapoint_id keys into backend app/esrs_datapoints.py.';
comment on table public.esrs_reports is
  'Immutable snapshots of generated ESRS sustainability statements (Word/PDF/export).';