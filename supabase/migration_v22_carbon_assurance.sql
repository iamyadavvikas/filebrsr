-- Migration V22: persisted Carbon Assurance ledger (supplier-signed, append-only)
-- ==========================================================================
-- Makes the Carbon Assurance subsystem REAL instead of an in-memory demo.
-- Suppliers submit Ed25519-signed emission records; the backend verifies the
-- signature, appends the record as a domain-separated (RFC 6962) Merkle leaf,
-- recomputes the tree head and signs it with app.prov's KMS-backed Ed25519
-- signer (NOT a seeded demo key). Any later mutation of a stored row breaks
-- both the leaf recomputation AND the signed checkpoint.
--
-- Mirrors the v17 tamper-evident ledger conventions (org-scoped, append-only
-- via trigger + revoked grants, org-member read RLS) but stores externally
-- supplied, supplier-signed records rather than internal calculation events.
--
-- Run AFTER migration_v17_merkle_ledger.sql.
-- ==========================================================================

-- ─── assurance_suppliers (TOFU supplier-identity -> public-key binding) ─────
-- First submission for a (org, supplier_id) pins the supplier's public key.
-- Later submissions claiming the same supplier_id must present the same key,
-- so a stolen supplier_id can't be impersonated with a different keypair.

create table if not exists public.assurance_suppliers (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references public.organizations(id) on delete cascade,
  supplier_id    text not null,
  public_key_b64 text not null,                -- raw Ed25519 public key, base64
  created_at     timestamptz not null default now(),
  unique (org_id, supplier_id)
);

create index if not exists assurance_suppliers_org_idx
  on public.assurance_suppliers (org_id, supplier_id);

-- ─── assurance_submissions (one signed record per Merkle leaf, per org) ─────

create table if not exists public.assurance_submissions (
  id                 uuid primary key default gen_random_uuid(),
  org_id             uuid not null references public.organizations(id) on delete cascade,
  leaf_index         bigint not null,          -- 0-based, sequential per org
  batch_id           text not null,            -- supply-chain batch identifier
  parent_batch_id    text,                     -- upstream batch (provenance edge)
  stage              text not null,            -- ore | concentrate | smelter | battery
  supplier_id        text not null,
  region             text not null,
  material           text not null,
  payload            jsonb not null,           -- canonical EmissionRecord that was hashed/signed
  record_sha256      text not null,            -- hex RFC6962 leaf = sha256(0x00 || canonical(payload))
  supplier_public_key text not null,           -- raw Ed25519 public key, base64
  supplier_signature  text not null,           -- Ed25519 signature over canonical(payload), base64
  occurred_at        timestamptz not null,
  created_at         timestamptz not null default now(),
  unique (org_id, leaf_index),
  unique (org_id, batch_id)
);

create index if not exists assurance_submissions_org_idx
  on public.assurance_submissions (org_id, leaf_index);
create index if not exists assurance_submissions_batch_idx
  on public.assurance_submissions (org_id, batch_id);

-- ─── assurance_roots (server-signed Merkle checkpoint after each append) ────

create table if not exists public.assurance_roots (
  id                 uuid primary key default gen_random_uuid(),
  org_id             uuid not null references public.organizations(id) on delete cascade,
  tree_size          bigint not null,          -- number of leaves covered (= leaf_index+1)
  merkle_root        text not null,            -- hex RFC6962 root over leaves [0, tree_size)
  prev_root          text,                     -- previous root hex (hash-chained heads)
  algorithm          text not null default 'sha256',
  root_signature_b64 text not null,            -- Ed25519 signature over canonical root header
  public_key_b64     text not null,            -- server (app.prov) public key, base64
  key_id             text not null,
  signed_at          timestamptz not null default now(),
  created_at         timestamptz not null default now(),
  unique (org_id, tree_size)
);

create index if not exists assurance_roots_org_idx
  on public.assurance_roots (org_id, tree_size desc);

-- ─── Append-only enforcement (layer 1: trigger) ────────────────────────────

create or replace function public.fn_assurance_append_only()
returns trigger
language plpgsql
as $$
begin
  raise exception 'carbon assurance ledger is append-only: % on % is not permitted',
    tg_op, tg_table_name;
  return null;
end;
$$;

drop trigger if exists trg_assurance_submissions_append_only on public.assurance_submissions;
create trigger trg_assurance_submissions_append_only
  before update or delete on public.assurance_submissions
  for each row execute function public.fn_assurance_append_only();

drop trigger if exists trg_assurance_roots_append_only on public.assurance_roots;
create trigger trg_assurance_roots_append_only
  before update or delete on public.assurance_roots
  for each row execute function public.fn_assurance_append_only();

-- ─── RLS (org-scoped, read-only for members; writes via service role) ──────

alter table public.assurance_suppliers   enable row level security;
alter table public.assurance_submissions enable row level security;
alter table public.assurance_roots       enable row level security;

drop policy if exists "Org members can read assurance suppliers" on public.assurance_suppliers;
create policy "Org members can read assurance suppliers"
  on public.assurance_suppliers for select
  using (public.user_in_org(org_id));

drop policy if exists "Org members can read assurance submissions" on public.assurance_submissions;
create policy "Org members can read assurance submissions"
  on public.assurance_submissions for select
  using (public.user_in_org(org_id));

drop policy if exists "Org members can read assurance roots" on public.assurance_roots;
create policy "Org members can read assurance roots"
  on public.assurance_roots for select
  using (public.user_in_org(org_id));

-- ─── Append-only enforcement (layer 2: revoke UPDATE/DELETE) ───────────────
-- Service role (backend) bypasses RLS but is still subject to the trigger
-- above. Revoke UPDATE/DELETE from the API roles as defence in depth.

revoke update, delete on public.assurance_suppliers   from anon, authenticated;
revoke update, delete on public.assurance_submissions from anon, authenticated;
revoke update, delete on public.assurance_roots       from anon, authenticated;
