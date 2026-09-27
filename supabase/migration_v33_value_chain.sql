-- ============================================================
-- BRSR Core — value-chain partners (CIR/2025/42).
-- ============================================================
-- Top-250 listed entities disclose their BRSR Core KPIs for value-chain
-- partners that are individually a top upstream/downstream partner comprising
-- >=2% of the entity's purchases/sales (by value), capped at 75% cumulative
-- coverage (CIR/2023/122 cl.4 as revised by CIR/2025/42, effective
-- FY2024-25 onwards). Disclosures are voluntary from FY2025-26 and
-- assessment/assurance voluntary from FY2026-27.
--
-- `value_chain_partners`: one row per (org, fy, partner, direction); the
-- direction-relevant percentage (purchases_pct for upstream, sales_pct for
-- downstream) drives scope + coverage in app/brsr_value_chain.py. `disclosed`
-- marks partners for which the entity actually provided ESG disclosure
-- (CIR/2025/42 cl.3.6 requires stating the % of purchases/sales covered).
--
-- `value_chain_entries`: attributed value-chain KPI state per partner, sharing
-- the BRSR Core assurance state machine so assessment/assurance of VC
-- disclosures can be tracked per partner from FY2026-27.
--
-- Additive + org-scoped; RLS mirrors the legacy org_members policies (v15).

create table if not exists public.value_chain_partners (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  financial_year text not null check (financial_year ~ '^FY[0-9]{4}-[0-9]{2}$'),
  partner_name text not null,
  direction text not null check (direction in ('upstream', 'downstream')),
  purchases_pct numeric check (purchases_pct is null or
    (purchases_pct >= 0 and purchases_pct <= 100)),
  sales_pct numeric check (sales_pct is null or
    (sales_pct >= 0 and sales_pct <= 100)),
  disclosed boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, financial_year, partner_name, direction)
);

create index if not exists value_chain_partners_org_fy_idx
  on public.value_chain_partners(org_id, financial_year);

create index if not exists value_chain_partners_dir_idx
  on public.value_chain_partners(direction);

create table if not exists public.value_chain_entries (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  financial_year text not null check (financial_year ~ '^FY[0-9]{4}-[0-9]{2}$'),
  partner_id uuid references public.value_chain_partners(id)
    on delete cascade not null,
  kpi_code text not null check (kpi_code ~ '^BRSC-[0-9]+\.[0-9]+$'),
  assurance_state text not null default 'unassured'
    check (assurance_state in ('unassured', 'evidence', 'limited', 'reasonable', 'not_applicable')),
  provider_name text,
  provider_details jsonb not null default '{}'::jsonb,
  evidence_id uuid references public.documents(id),
  evidence_note text,
  assessed_value numeric,
  unit text,
  assessed_on date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, financial_year, partner_id, kpi_code)
);

create index if not exists value_chain_entries_org_fy_idx
  on public.value_chain_entries(org_id, financial_year);

create index if not exists value_chain_entries_partner_idx
  on public.value_chain_entries(partner_id);

alter table public.value_chain_partners enable row level security;
alter table public.value_chain_entries enable row level security;

create policy "Org members can view value chain partners"
  on public.value_chain_partners for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create policy "Org members can manage value chain partners"
  on public.value_chain_partners for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));

create policy "Org members can view value chain entries"
  on public.value_chain_entries for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create policy "Org members can manage value chain entries"
  on public.value_chain_entries for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));