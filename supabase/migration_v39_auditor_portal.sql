-- Migration V39: auditor portal (magic-link grants + findings loop)
-- ==========================================================================
-- Lets assurance providers work inside the platform without full accounts:
--
--   * auditor_grants — magic-link invite per (org, email): token hash (the
--     raw token is shown once at mint), read scope, expiry, single-use
--     accept, revocation. Raw tokens never touch the database.
--   * assurance_findings — auditor-raised queries threaded to resolution:
--     linked entity (KPI/datapoint/report), severity, status
--     open -> answered -> closed, append-only message thread.
--
-- RLS mirrors the org_members policies. Backend uses the service key.
-- Purely additive. Run AFTER migration_v38.
-- ==========================================================================

create table if not exists public.auditor_grants (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  email text not null,
  token_hash text not null unique,
  scope text not null default 'read'
    check (scope in ('read', 'read_assure')),
  invited_by uuid references public.profiles(id) on delete set null,
  expires_at timestamptz not null,
  accepted_at timestamptz,
  revoked boolean not null default false,
  created_at timestamptz not null default now(),
  unique (org_id, email)
);

create index if not exists auditor_grants_org_idx
  on public.auditor_grants(org_id);

create index if not exists auditor_grants_expiry_idx
  on public.auditor_grants(expires_at) where not revoked;

alter table public.auditor_grants enable row level security;

drop policy if exists "Org members can manage auditor grants"
  on public.auditor_grants;
create policy "Org members can manage auditor grants"
  on public.auditor_grants for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin')));

create table if not exists public.assurance_findings (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  financial_year text,
  raised_by_grant uuid references public.auditor_grants(id) on delete set null,
  raised_by_email text,
  entity_type text not null default 'general'
    check (entity_type in ('general', 'kpi', 'datapoint', 'report', 'workpaper')),
  entity_ref text,
  severity text not null default 'medium'
    check (severity in ('low', 'medium', 'high', 'blocking')),
  message text not null,
  status text not null default 'open'
    check (status in ('open', 'answered', 'closed')),
  thread jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists assurance_findings_org_fy_idx
  on public.assurance_findings(org_id, financial_year);

create index if not exists assurance_findings_status_idx
  on public.assurance_findings(status);

alter table public.assurance_findings enable row level security;

drop policy if exists "Org members can manage assurance findings"
  on public.assurance_findings;
create policy "Org members can manage assurance findings"
  on public.assurance_findings for all
  using (org_id in (select org_id from public.org_members
                    where user_id = auth.uid() and role in ('owner', 'admin', 'member')));

comment on table public.auditor_grants is
  'Magic-link auditor access: token hashes only, expiry-bound, revocable, single-use accept.';

comment on table public.assurance_findings is
  'Auditor-raised queries with append-only resolution threads.';
