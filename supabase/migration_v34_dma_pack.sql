-- Migration V34: DMA methodology pack (stakeholders, thresholds, IRO-DR links)
-- ==========================================================================
-- Gives the double materiality assessment an auditable methodology record:
--
--   * esrs_stakeholders — who was consulted, how, when, and how their input
--     changed the scoring (ESRS 1 Ch.3 stakeholder engagement expectation).
--   * esrs_dma_config — the threshold methodology per (org, FY): impact and
--     financial cutoffs, the written rationale, and the approval that locks
--     the scope (distinct from report attestation).
--   * iro_dr_links — each material IRO traced to the Disclosure Requirements
--     it triggers (the auditor's first request). Coverage gaps
--     ("material IRO with no DRs") are surfaced by the API, not stored.
--
-- RLS mirrors the esrs_* org-member policies (v23, via user_in_org); the
-- backend uses the service key. Guests operate inside their sandbox org.
--
-- Idempotent. Run AFTER migration_v33_value_chain.sql.
-- ==========================================================================

-- 1. Stakeholder engagement log ----------------------------------------------
create table if not exists public.esrs_stakeholders (
  id                    uuid primary key default gen_random_uuid(),
  org_id                uuid not null references public.organizations(id) on delete cascade,
  financial_year        text not null,                  -- e.g. 'FY2025'
  stakeholder_group     text not null
                          check (stakeholder_group in (
                            'own_workforce', 'value_chain_workers',
                            'affected_communities', 'consumers_end_users',
                            'investors_lenders', 'regulators',
                            'civil_society_ngos', 'suppliers_partners',
                            'customers', 'other')),
  method                text not null
                          check (method in (
                            'survey', 'interview', 'workshop', 'site_visit',
                            'grievance_review', 'desktop_research', 'other')),
  consulted_on          date,
  participants          int check (participants is null or participants >= 0),
  summary               text,                           -- what they said
  influence             text,                           -- how it changed scoring
  created_by            uuid references public.profiles(id) on delete set null,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create index if not exists esrs_stakeholders_org_year_idx
  on public.esrs_stakeholders (org_id, financial_year);

alter table public.esrs_stakeholders enable row level security;

drop policy if exists "Org members can manage esrs stakeholders" on public.esrs_stakeholders;
create policy "Org members can manage esrs stakeholders"
  on public.esrs_stakeholders for all
  using (public.user_in_org(org_id))
  with check (public.user_in_org(org_id));

-- 2. Threshold methodology + approval -----------------------------------------
create table if not exists public.esrs_dma_config (
  id                    uuid primary key default gen_random_uuid(),
  org_id                uuid not null references public.organizations(id) on delete cascade,
  financial_year        text not null,
  impact_threshold      numeric(3,2) not null default 3.00
                          check (impact_threshold between 0 and 5),
  financial_threshold   numeric(3,2) not null default 3.00
                          check (financial_threshold between 0 and 5),
  methodology           text,                           -- why these cutoffs
  sensitivity_note      text,                           -- what moves the line
  status                text not null default 'draft'
                          check (status in ('draft', 'approved')),
  approved_by           text,
  approved_at           timestamptz,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (org_id, financial_year)
);

create index if not exists esrs_dma_config_org_year_idx
  on public.esrs_dma_config (org_id, financial_year);

alter table public.esrs_dma_config enable row level security;

drop policy if exists "Org members can manage esrs dma config" on public.esrs_dma_config;
create policy "Org members can manage esrs dma config"
  on public.esrs_dma_config for all
  using (public.user_in_org(org_id))
  with check (public.user_in_org(org_id));

-- 3. IRO -> Disclosure Requirement linkage ------------------------------------
create table if not exists public.iro_dr_links (
  id                    uuid primary key default gen_random_uuid(),
  org_id                uuid not null references public.organizations(id) on delete cascade,
  financial_year        text not null,
  iro_id                uuid not null references public.esrs_materiality(id) on delete cascade,
  dr                    text not null,                  -- e.g. 'E1', 'E1-6', 'SBM-1'
  rationale             text,
  created_at            timestamptz not null default now(),
  unique (iro_id, dr)
);

create index if not exists iro_dr_links_org_year_idx
  on public.iro_dr_links (org_id, financial_year);

create index if not exists iro_dr_links_iro_idx
  on public.iro_dr_links (iro_id);

alter table public.iro_dr_links enable row level security;

drop policy if exists "Org members can manage iro dr links" on public.iro_dr_links;
create policy "Org members can manage iro dr links"
  on public.iro_dr_links for all
  using (public.user_in_org(org_id))
  with check (public.user_in_org(org_id));

-- ─── comments ──────────────────────────────────────────────────────────────

comment on table public.esrs_stakeholders is
  'DMA stakeholder engagement log: who was consulted, how, and how their input changed materiality scoring (ESRS 1 Ch.3).';

comment on table public.esrs_dma_config is
  'DMA threshold methodology per org/FY: cutoffs, rationale, and the approval that locks assessment scope.';

comment on table public.iro_dr_links is
  'Material IRO to Disclosure Requirement traceability matrix (auditor evidence for IRO-1 coverage).';
