-- Migration V40: FY rollover log
-- ==========================================================================
-- Year-rollover copies workspace state forward (entries, IROs, DMA config)
-- without ever overwriting the target year: reruns only fill gaps. This
-- table records each run for idempotency and the audit record.
--
-- Variance itself is computed live (prior vs current values); restatement
-- justifications ride the audit_trail.change_reason on edit. No entry
-- schema change needed.
--
-- Purely additive. Run AFTER migration_v39.
-- ==========================================================================

create table if not exists public.fy_rollovers (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  from_fy text not null,
  to_fy text not null,
  entries_copied int not null default 0,
  entries_skipped int not null default 0,
  iros_copied int not null default 0,
  run_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (org_id, from_fy, to_fy)
);

create index if not exists fy_rollovers_org_idx
  on public.fy_rollovers(org_id);

alter table public.fy_rollovers enable row level security;

drop policy if exists "Org members can manage fy rollovers"
  on public.fy_rollovers;
create policy "Org members can manage fy rollovers"
  on public.fy_rollovers for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));

comment on table public.fy_rollovers is
  'FY rollover runs: what was carried forward, idempotent per (org, from, to).';
