-- Migration V16: calculations + signed provenance records (PROV-O storage)
-- ==========================================================================
-- Implements P0 #2 (provenance first-class) from the founding-engineer
-- charter. Pairs with the backend package app.prov, which builds the W3C
-- PROV-O graph, canonicalises it (RFC 8785), SHA-256 hashes it, and signs it
-- with Ed25519. This migration persists the calculated number AND its signed
-- provenance so an auditor can independently re-verify every disclosed value.
--
-- AUDIT-CRITICAL tables (per charter): calculations, provenance_records.
-- Schema changes here require a migration plan + restatement impact analysis.
--
-- All emissions/quantities are NUMERIC (never float). Money lives in paise as
-- bigint elsewhere; emission values are numeric(38,12) for headroom.
--
-- Run AFTER migration_v15_tenancy.sql.
-- ==========================================================================

-- ─── calculations (deterministic output of app.calculator) ─────────────────

create table if not exists public.calculations (
  id                     uuid primary key default gen_random_uuid(),
  org_id                 uuid not null references public.organizations(id) on delete cascade,
  user_id                uuid references public.profiles(id) on delete set null,

  -- What was calculated -----------------------------------------------------
  scope                  int not null check (scope in (1, 2, 3)),
  category               text not null,             -- e.g. "electricity_purchased"
  method                 text not null,             -- "location_based" | "market_based" | ...
  value                  numeric(38, 12) not null,  -- NEVER float (principle: NUMERIC only)
  unit                   text not null,             -- "tCO2e", "GJ", ...

  -- Factor lineage (forward link into app.factors_india) --------------------
  factor_id              text not null,
  factor_version         text not null,
  factor_source          text,
  factor_citation        text,

  -- Inputs + uncertainty + agent ------------------------------------------
  input_record_ids       bigint[] not null default '{}',  -- raw_records.id list
  uncertainty            jsonb,
  agent_run_id           text,                      -- ties to agent_runs (future)
  calculated_by          text not null default 'filebrsr-calculator',
  calculated_by_version  text not null,
  calculation_timestamp  timestamptz not null default now(),

  -- Versioning / restatement ------------------------------------------------
  superseded_by          uuid references public.calculations(id) on delete set null,
  created_at             timestamptz not null default now()
);

create index if not exists calculations_org_idx
  on public.calculations (org_id, scope, calculation_timestamp desc);
create index if not exists calculations_factor_idx
  on public.calculations (factor_id, factor_version);

-- ─── provenance_records (signed PROV-O graph, 1:1 with a calculation) ──────

create table if not exists public.provenance_records (
  id                 uuid primary key default gen_random_uuid(),
  calculation_id     uuid not null references public.calculations(id) on delete cascade,
  org_id             uuid not null references public.organizations(id) on delete cascade,

  prov_graph         jsonb not null,                -- W3C PROV-O JSON-LD
  canonical_sha256   text not null,                 -- hex SHA-256 of RFC-8785 canonical form
  algorithm          text not null default 'Ed25519',
  signature_b64      text not null,                 -- server-side Ed25519 signature
  public_key_b64     text not null,                 -- key used (verify against this)
  key_id             text not null,                 -- KMS key id / local key id
  signed_at          timestamptz not null default now(),

  -- DSC (eMudhra/Sify) browser-side dual signature — Phase 5; null for now.
  dsc_signature      jsonb,

  created_at         timestamptz not null default now(),
  unique (calculation_id)
);

create index if not exists provenance_records_org_idx
  on public.provenance_records (org_id, signed_at desc);
create index if not exists provenance_records_hash_idx
  on public.provenance_records (canonical_sha256);

-- ─── RLS (org-scoped) ──────────────────────────────────────────────────────

alter table public.calculations enable row level security;
alter table public.provenance_records enable row level security;

drop policy if exists "Org members can read calculations" on public.calculations;
create policy "Org members can read calculations"
  on public.calculations for select
  using (public.user_in_org(org_id));

drop policy if exists "Org members can insert calculations" on public.calculations;
create policy "Org members can insert calculations"
  on public.calculations for insert
  with check (public.user_in_org(org_id));

drop policy if exists "Org members can read provenance" on public.provenance_records;
create policy "Org members can read provenance"
  on public.provenance_records for select
  using (public.user_in_org(org_id));

drop policy if exists "Org members can insert provenance" on public.provenance_records;
create policy "Org members can insert provenance"
  on public.provenance_records for insert
  with check (public.user_in_org(org_id));

-- ─── Audit triggers on the audit-critical tables (fn_audit_log from V15) ───

drop trigger if exists trg_audit_calculations on public.calculations;
create trigger trg_audit_calculations
  after insert or update or delete on public.calculations
  for each row execute function public.fn_audit_log();

drop trigger if exists trg_audit_provenance on public.provenance_records;
create trigger trg_audit_provenance
  after insert or update or delete on public.provenance_records
  for each row execute function public.fn_audit_log();

drop trigger if exists trg_audit_organizations on public.organizations;
create trigger trg_audit_organizations
  after insert or update or delete on public.organizations
  for each row execute function public.fn_audit_log();
