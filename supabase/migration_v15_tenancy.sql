-- Migration V15: Multi-tenancy (organizations) + per-tenant RLS + audit_log
-- ==========================================================================
-- Implements P0 #3 (true multi-tenancy) from the founding-engineer charter.
--
-- BEFORE: every data table was scoped per-USER (auth.uid() = user_id).
-- AFTER:  data is owned by an ORGANIZATION (tenant). Users belong to one or
--         more orgs via organization_members. India-specific corporate
--         identifiers (CIN, PAN, GSTIN[], LEI, SEBI scrip, NIC) live on the
--         org, as the charter's Week-2 schema requires.
--
-- SAFETY / NON-BREAKING:
--   * org_id columns are added NULLABLE, then backfilled with a per-user
--     "personal org" so existing rows are never orphaned.
--   * New org-scoped RLS policies are ADDED ALONGSIDE the existing per-user
--     policies. Postgres permissive policies are OR-combined, so a user keeps
--     access to their own rows AND gains access to their org's rows — no
--     existing query breaks.
--   * Fully idempotent (if not exists / drop policy if exists) → replayable.
--
-- Run AFTER migration_v14_tally_extras.sql.
-- ==========================================================================

-- ─── organizations (the tenant) ───────────────────────────────────────────

create table if not exists public.organizations (
  id                          uuid primary key default gen_random_uuid(),
  name                        text not null,
  -- India corporate identity (charter Week-2 organizations spec) -----------
  cin                         text,                 -- Corporate Identification Number (21 chars)
  pan                         text,                 -- Permanent Account Number (10 chars)
  gstins                      text[] not null default '{}',  -- one GSTIN per state of registration
  lei                         text,                 -- Legal Entity Identifier (20 chars)
  sebi_scrip_code             text,                 -- BSE/NSE scrip code
  nic_code                    text,                 -- National Industrial Classification
  -- BRSR applicability (drives mandate logic) ------------------------------
  brsr_applicable_from_fy     text,                 -- e.g. "FY2022-23"
  brsr_core_applicable_from_fy text,                -- e.g. "FY2024-25"
  -- Data residency stamp (principle #6) ------------------------------------
  data_region                 text not null default 'ap-south-1'
                                check (data_region = 'ap-south-1'),
  is_personal                 boolean not null default false,  -- backfilled solo orgs
  created_at                  timestamptz not null default now(),
  updated_at                  timestamptz not null default now()
);

-- Backfill columns onto a pre-existing organizations table. `create table if
-- not exists` above is a no-op when the table already exists (e.g. an earlier
-- partial run), so it would NOT add new columns. These guards make the
-- migration truly replayable regardless of the table's prior shape.
alter table public.organizations
  add column if not exists name                         text,
  add column if not exists cin                          text,
  add column if not exists pan                          text,
  add column if not exists gstins                       text[] not null default '{}',
  add column if not exists lei                          text,
  add column if not exists sebi_scrip_code              text,
  add column if not exists nic_code                     text,
  add column if not exists brsr_applicable_from_fy      text,
  add column if not exists brsr_core_applicable_from_fy text,
  add column if not exists data_region                  text not null default 'ap-south-1',
  add column if not exists is_personal                  boolean not null default false,
  add column if not exists created_at                   timestamptz not null default now(),
  add column if not exists updated_at                   timestamptz not null default now();

-- Ensure the residency CHECK exists (a pre-existing table may lack it).
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'organizations_data_region_check'
  ) then
    alter table public.organizations
      add constraint organizations_data_region_check check (data_region = 'ap-south-1');
  end if;
end $$;

create unique index if not exists organizations_cin_key
  on public.organizations (cin) where cin is not null;
create unique index if not exists organizations_pan_key
  on public.organizations (pan) where pan is not null;

-- ─── organization_members (user ↔ org, with role) ─────────────────────────

create table if not exists public.organization_members (
  org_id      uuid not null references public.organizations(id) on delete cascade,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  role        text not null default 'member'
                check (role in ('owner', 'admin', 'member', 'auditor')),
  created_at  timestamptz not null default now(),
  primary key (org_id, user_id)
);

-- Backfill the role column onto a pre-existing members table.
alter table public.organization_members
  add column if not exists role text not null default 'member';
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'organization_members_role_check'
  ) then
    alter table public.organization_members
      add constraint organization_members_role_check
      check (role in ('owner', 'admin', 'member', 'auditor'));
  end if;
end $$;

create index if not exists organization_members_user_idx
  on public.organization_members (user_id);

-- ─── RLS helper: is the current user a member of this org? ─────────────────
-- SECURITY DEFINER + stable so it can be used inside RLS USING clauses
-- without recursive policy evaluation on organization_members.

create or replace function public.user_in_org(target_org uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.organization_members m
    where m.org_id = target_org and m.user_id = auth.uid()
  );
$$;

-- ─── Propagate org_id onto existing data tables (nullable + indexed) ───────
-- Add to the tables that actually hold tenant data today. Each is guarded so
-- the migration is safe if a table does not exist in a given environment.

do $$
declare
  t text;
  data_tables text[] := array[
    'reports', 'raw_records', 'brsr_entries', 'documents',
    'extraction_corrections', 'extraction_chunks'
  ];
begin
  foreach t in array data_tables loop
    if to_regclass(format('public.%I', t)) is not null then
      execute format(
        'alter table public.%I add column if not exists org_id uuid '
        || 'references public.organizations(id) on delete cascade', t);
      execute format(
        'create index if not exists %I on public.%I (org_id)',
        t || '_org_id_idx', t);
    end if;
  end loop;
end $$;

-- ─── Backfill: one personal org per existing user, then claim their rows ───

do $$
declare
  p record;
  new_org uuid;
  t text;
  has_slug boolean;
  has_created_by boolean;
  org_name text;
  ins_cols text;
  ins_vals text;
  c record;
  data_tables text[] := array[
    'reports', 'raw_records', 'brsr_entries', 'documents',
    'extraction_corrections', 'extraction_chunks'
  ];
begin
  -- A pre-existing organizations table (e.g. from the teams/GTM migrations)
  -- may carry NOT NULL columns with no default that this migration is unaware
  -- of (observed: `slug`, `created_by`). Detect the known ones so the
  -- personal-org backfill can supply sane values instead of failing. The
  -- insert column list is built dynamically and only references columns that
  -- actually exist.
  select exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'organizations'
      and column_name = 'slug'
  ) into has_slug;
  select exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'organizations'
      and column_name = 'created_by'
  ) into has_created_by;

  for p in select id, coalesce(company_name, full_name, email) as nm
           from public.profiles loop
    -- Skip if this user already owns a personal org.
    select o.id into new_org
    from public.organizations o
    join public.organization_members m on m.org_id = o.id
    where m.user_id = p.id and o.is_personal
    limit 1;

    if new_org is null then
      org_name := coalesce(nullif(p.nm, ''), 'My Organization');
      ins_cols := 'name, is_personal';
      ins_vals := format('%L, true', org_name);
      if has_slug then
        ins_cols := ins_cols || ', slug';
        ins_vals := ins_vals || ', ' || format('%L', 'personal-' || p.id::text);
      end if;
      if has_created_by then
        ins_cols := ins_cols || ', created_by';
        ins_vals := ins_vals || ', ' || format('%L', p.id::text);
      end if;

      -- Safety net: satisfy any OTHER NOT NULL / no-default columns the legacy
      -- table may have, with type-appropriate placeholders. uuid columns get
      -- the user id (best guess for owner/creator-style FKs); text gets a
      -- per-user-unique stub (avoids unique-constraint collisions); etc.
      for c in
        select column_name, data_type
        from information_schema.columns
        where table_schema = 'public' and table_name = 'organizations'
          and is_nullable = 'NO'
          and column_default is null
          and (is_generated is null or is_generated = 'NEVER')
          and column_name not in ('id', 'name', 'is_personal', 'slug', 'created_by')
      loop
        ins_cols := ins_cols || ', ' || quote_ident(c.column_name);
        ins_vals := ins_vals || ', ' || case
          when c.data_type = 'uuid' then format('%L', p.id::text)
          when c.data_type = 'boolean' then 'false'
          when c.data_type in ('integer', 'bigint', 'smallint', 'numeric',
                               'double precision', 'real') then '0'
          when c.data_type in ('json', 'jsonb') then format('%L', '{}')
          when c.data_type = 'ARRAY' then format('%L', '{}')
          when c.data_type in ('timestamp with time zone',
                               'timestamp without time zone', 'date') then 'now()'
          else format('%L', c.column_name || '-' || p.id::text)
        end;
      end loop;

      execute format(
        'insert into public.organizations (%s) values (%s) returning id',
        ins_cols, ins_vals
      ) into new_org;

      insert into public.organization_members (org_id, user_id, role)
      values (new_org, p.id, 'owner')
      on conflict do nothing;
    end if;

    -- Claim this user's existing rows for their personal org.
    foreach t in array data_tables loop
      if to_regclass(format('public.%I', t)) is not null then
        execute format(
          'update public.%I set org_id = $1 where user_id = $2 and org_id is null',
          t) using new_org, p.id;
      end if;
    end loop;
  end loop;
end $$;

-- ─── RLS on the new tenancy tables ─────────────────────────────────────────

alter table public.organizations enable row level security;
alter table public.organization_members enable row level security;

drop policy if exists "Members can view their orgs" on public.organizations;
create policy "Members can view their orgs"
  on public.organizations for select
  using (public.user_in_org(id));

drop policy if exists "Owners/admins can update their org" on public.organizations;
create policy "Owners/admins can update their org"
  on public.organizations for update
  using (exists (
    select 1 from public.organization_members m
    where m.org_id = id and m.user_id = auth.uid() and m.role in ('owner', 'admin')
  ));

drop policy if exists "Members can view their memberships" on public.organization_members;
create policy "Members can view their memberships"
  on public.organization_members for select
  using (user_id = auth.uid() or public.user_in_org(org_id));

-- ─── Org-scoped policies ADDED ALONGSIDE existing per-user policies ────────
-- Permissive (OR) — additive, non-breaking. Service role bypasses RLS.

do $$
declare
  t text;
  data_tables text[] := array[
    'reports', 'raw_records', 'brsr_entries', 'documents',
    'extraction_corrections', 'extraction_chunks'
  ];
begin
  foreach t in array data_tables loop
    if to_regclass(format('public.%I', t)) is not null then
      execute format('alter table public.%I enable row level security', t);
      execute format('drop policy if exists "Org members can read" on public.%I', t);
      execute format(
        'create policy "Org members can read" on public.%I for select '
        || 'using (org_id is not null and public.user_in_org(org_id))', t);
      execute format('drop policy if exists "Org members can write" on public.%I', t);
      execute format(
        'create policy "Org members can write" on public.%I for insert '
        || 'with check (org_id is not null and public.user_in_org(org_id))', t);
    end if;
  end loop;
end $$;

-- ─── audit_log (audit-critical; append-only) ───────────────────────────────

create table if not exists public.audit_log (
  id            bigserial primary key,
  org_id        uuid references public.organizations(id) on delete set null,
  actor_id      uuid,                               -- auth.uid() at time of change
  table_name    text not null,
  row_pk        text,
  action        text not null check (action in ('INSERT', 'UPDATE', 'DELETE')),
  changed_at    timestamptz not null default now(),
  old_data      jsonb,
  new_data      jsonb
);

create index if not exists audit_log_org_time_idx
  on public.audit_log (org_id, changed_at desc);
create index if not exists audit_log_table_idx
  on public.audit_log (table_name, changed_at desc);

create or replace function public.fn_audit_log()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org uuid;
  v_pk  text;
begin
  v_org := coalesce(
    (case when tg_op = 'DELETE' then old.org_id else new.org_id end),
    null);
  v_pk := coalesce(
    (case when tg_op = 'DELETE' then old.id::text else new.id::text end),
    null);

  insert into public.audit_log (org_id, actor_id, table_name, row_pk, action, old_data, new_data)
  values (
    v_org,
    auth.uid(),
    tg_table_name,
    v_pk,
    tg_op,
    case when tg_op in ('UPDATE', 'DELETE') then to_jsonb(old) else null end,
    case when tg_op in ('UPDATE', 'INSERT') then to_jsonb(new) else null end
  );
  return null;  -- AFTER trigger
end $$;

-- audit_log itself is service-role / definer-written; authenticated users may
-- read only their org's entries.
alter table public.audit_log enable row level security;
drop policy if exists "Org members can read audit log" on public.audit_log;
create policy "Org members can read audit log"
  on public.audit_log for select
  using (org_id is not null and public.user_in_org(org_id));
