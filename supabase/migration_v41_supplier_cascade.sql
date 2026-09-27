-- Migration V41: supplier cascade (invites, questionnaires, responses)
-- ==========================================================================
-- Lets clients pull Scope 3 / S2 data from their value chain instead of
-- estimating it:
--
--   * cascade_suppliers — per client-org vendor with a magic-link
--     (token hash only, like auditor_grants), tier and spend band for
--     prioritisation.
--   * cascade_responses — one row per (supplier, FY, questionnaire):
--     answers JSONB, status draft -> submitted, submitted_at. Prefill
--     into workspace entries happens on explicit confirm (review
--     queue pattern), never automatically.
--
-- Questionnaire definitions live in app/supplier_questions.py (BRSR
-- Section A.V set + ESRS S2 set). RLS mirrors org_members policies.
-- Purely additive. Run AFTER migration_v40.
-- ==========================================================================

create table if not exists public.cascade_suppliers (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  name text not null,
  email text,
  token_hash text unique,
  tier text not null default 'tier_1'
    check (tier in ('tier_1', 'tier_2', 'tier_3')),
  spend_band text
    check (spend_band in ('high', 'medium', 'low')),
  expires_at timestamptz,
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (org_id, name)
);

create index if not exists cascade_suppliers_org_idx
  on public.cascade_suppliers(org_id);

alter table public.cascade_suppliers enable row level security;

drop policy if exists "Org members can manage cascade suppliers"
  on public.cascade_suppliers;
create policy "Org members can manage cascade suppliers"
  on public.cascade_suppliers for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));

create table if not exists public.cascade_responses (
  id uuid default gen_random_uuid() primary key,
  supplier_id uuid references public.cascade_suppliers(id) on delete cascade not null,
  org_id uuid references public.organizations(id) on delete cascade not null,
  financial_year text not null,
  questionnaire text not null default 'brsr_a5'
    check (questionnaire in ('brsr_a5', 'esrs_s2')),
  answers jsonb not null default '{}'::jsonb,
  status text not null default 'draft'
    check (status in ('draft', 'submitted')),
  submitted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (supplier_id, financial_year, questionnaire)
);

create index if not exists cascade_responses_org_fy_idx
  on public.cascade_responses(org_id, financial_year);

alter table public.cascade_responses enable row level security;

drop policy if exists "Org members can manage cascade responses"
  on public.cascade_responses;
create policy "Org members can manage cascade responses"
  on public.cascade_responses for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));

comment on table public.cascade_suppliers is
  'Client value-chain vendors with magic-link credentials for questionnaire response.';

comment on table public.cascade_responses is
  'Supplier questionnaire answers; prefill into entries happens only on explicit client confirm.';
