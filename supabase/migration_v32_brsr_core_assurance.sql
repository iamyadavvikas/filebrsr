-- ============================================================
-- BRSR Core — per-KPI assurance tracking (Phase-in aware).
-- ============================================================
-- Canonical tracker for the 43 BRSC-* KPIs (sebi_doc/brsr_core_text.txt,
-- nine-attribute BRSR Core). Each (org, financial_year, kpi_code) row records
-- the assurance state machine for that KPI:
--
--     unassured -> evidence -> limited -> reasonable
--                       \-----------------^        ^----- (back to lower state)
--   not_applicable       (outside assurance universe / sector N/A)
--
-- limited / reasonable require an evidence document or provider before the
-- state can be set (enforced at the API layer, brsr_core_assurance.py).
-- `target_mode` records the mode the entity *should* hold for the row's FY
-- given market-cap tier (see brsr_core.assurance_mode_for); the app layer
-- computes and stores it so reporting compares attained vs required.
--
-- Migration is additive and org-scoped; row-level security mirrors the legacy
-- brsr_core_kpis policy (organizations / org_members from migration v15).

create table if not exists public.brsr_core_assurance (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  financial_year text not null check (financial_year ~ '^FY[0-9]{4}-[0-9]{2}$'),
  kpi_code text not null check (kpi_code ~ '^BRSC-[0-9]+\.[0-9]+$'),
  assurance_state text not null default 'unassured'
    check (assurance_state in ('unassured', 'evidence', 'limited', 'reasonable', 'not_applicable')),
  target_mode text check (target_mode in ('limited', 'reasonable', 'none', '')),
  provider_name text,
  provider_details jsonb not null default '{}'::jsonb,
  statement_short text,
  evidence_id uuid references public.documents(id),
  evidence_note text,
  ppp_adjusted boolean not null default false,
  output_denominator text,
  value_chain boolean not null default false,
  assessed_value numeric,
  unit text,
  assessed_on date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, financial_year, kpi_code)
);

create index if not exists brsr_core_assurance_org_fy_idx
  on public.brsr_core_assurance(org_id, financial_year);

create index if not exists brsr_core_assurance_state_idx
  on public.brsr_core_assurance(assurance_state);

alter table public.brsr_core_assurance enable row level security;

create policy "Org members can view BRSR Core assurance"
  on public.brsr_core_assurance for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create policy "Org members can manage BRSR Core assurance"
  on public.brsr_core_assurance for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));