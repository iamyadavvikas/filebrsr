-- Migration V24: CSRD / ESRS value-chain scope profile
-- ==========================================================================
-- Persists each org's declared value-chain boundary (which segments of the
-- value chain the undertaking reports on). Gap analysis uses it to only
-- count datapoints inside that boundary (see backend app/router_csrd.py).
-- Idempotent. Run AFTER migration_v23_esrs.sql.
-- ==========================================================================

create table if not exists public.esrs_profiles (
  org_id              uuid primary key references public.organizations(id) on delete cascade,
  value_chain_scope   text[] not null
                        default array['own_operations', 'upstream', 'downstream'],
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

alter table public.esrs_profiles enable row level security;

drop policy if exists "Org members can read esrs profile" on public.esrs_profiles;
create policy "Org members can read esrs profile"
  on public.esrs_profiles for select
  using (public.user_in_org(org_id));

drop policy if exists "Org members can insert esrs profile" on public.esrs_profiles;
create policy "Org members can insert esrs profile"
  on public.esrs_profiles for insert
  with check (public.user_in_org(org_id));

drop policy if exists "Org members can update esrs profile" on public.esrs_profiles;
create policy "Org members can update esrs profile"
  on public.esrs_profiles for update
  using (public.user_in_org(org_id))
  with check (public.user_in_org(org_id));

drop trigger if exists trg_esrs_profiles_updated_at on public.esrs_profiles;
create trigger trg_esrs_profiles_updated_at
  before update on public.esrs_profiles
  for each row execute function public.update_updated_at();

comment on table public.esrs_profiles is
  'Org scoping profile: declared value-chain boundary used by CSRD gap analysis.';