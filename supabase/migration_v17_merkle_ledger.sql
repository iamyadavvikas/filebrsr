-- Migration V17: tamper-evident Merkle ledger (append-only)
-- ==========================================================================
-- Phase D of the provenance-hardening work. AUGMENTS (does NOT replace) the
-- plain append-only audit_log + fn_audit_log from V15. Adds a cryptographic
-- transparency log: every audit-critical event becomes a domain-separated
-- (RFC 6962) Merkle leaf; the tree head is Ed25519-signed (reusing app.prov's
-- signer) after each append, so any later mutation of a stored row breaks both
-- the leaf recomputation AND the signed root.
--
-- Append-only is enforced at TWO layers: a BEFORE UPDATE/DELETE trigger that
-- raises, and revoked UPDATE/DELETE grants. This stops the application role
-- from rewriting history; a DB superuser can still bypass triggers, which is
-- why roots are signed and (later) externally anchored — see
-- docs/rfcs/0002-tamper-evident-ledger.md.
--
-- Run AFTER migration_v16_provenance.sql.
-- ==========================================================================

-- ─── ledger_leaves (one row per logged event, ordered per org) ─────────────

create table if not exists public.ledger_leaves (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  leaf_index    bigint not null,                 -- 0-based, sequential per org
  event_type    text not null,                   -- e.g. "calculation.signed"
  ref_table     text not null,                   -- source table, e.g. "calculations"
  ref_pk        text not null,                   -- source row pk (uuid/text)
  leaf_sha256   text not null,                   -- hex SHA-256 of RFC6962 0x00||canonical(payload)
  payload       jsonb not null,                  -- canonical event payload that was hashed
  created_at    timestamptz not null default now(),
  unique (org_id, leaf_index)
);

create index if not exists ledger_leaves_org_idx
  on public.ledger_leaves (org_id, leaf_index);
create index if not exists ledger_leaves_ref_idx
  on public.ledger_leaves (ref_table, ref_pk);

-- ─── ledger_roots (signed tree head after each append) ─────────────────────

create table if not exists public.ledger_roots (
  id                 uuid primary key default gen_random_uuid(),
  org_id             uuid not null references public.organizations(id) on delete cascade,
  tree_size          bigint not null,            -- number of leaves covered (= leaf_index+1)
  merkle_root        text not null,              -- hex RFC6962 root over leaves [0, tree_size)
  prev_root          text,                       -- previous root hex (hash-chained heads)
  root_signature_b64 text not null,              -- Ed25519 signature over the signed-head bytes
  public_key_b64     text not null,
  key_id             text not null,
  signed_at          timestamptz not null default now(),
  anchor             jsonb,                       -- external anchor (RFC3161 TSA / public) — future
  created_at         timestamptz not null default now(),
  unique (org_id, tree_size)
);

create index if not exists ledger_roots_org_idx
  on public.ledger_roots (org_id, tree_size desc);

-- ─── Append-only enforcement (layer 1: trigger) ────────────────────────────

create or replace function public.fn_ledger_append_only()
returns trigger
language plpgsql
as $$
begin
  raise exception 'ledger is append-only: % on % is not permitted',
    tg_op, tg_table_name;
  return null;
end;
$$;

drop trigger if exists trg_ledger_leaves_append_only on public.ledger_leaves;
create trigger trg_ledger_leaves_append_only
  before update or delete on public.ledger_leaves
  for each row execute function public.fn_ledger_append_only();

drop trigger if exists trg_ledger_roots_append_only on public.ledger_roots;
create trigger trg_ledger_roots_append_only
  before update or delete on public.ledger_roots
  for each row execute function public.fn_ledger_append_only();

-- ─── RLS (org-scoped, read-only for members; writes via service role) ──────

alter table public.ledger_leaves enable row level security;
alter table public.ledger_roots enable row level security;

drop policy if exists "Org members can read ledger leaves" on public.ledger_leaves;
create policy "Org members can read ledger leaves"
  on public.ledger_leaves for select
  using (public.user_in_org(org_id));

drop policy if exists "Org members can read ledger roots" on public.ledger_roots;
create policy "Org members can read ledger roots"
  on public.ledger_roots for select
  using (public.user_in_org(org_id));

-- ─── Append-only enforcement (layer 2: revoke UPDATE/DELETE) ───────────────
-- Service role (used by the backend) bypasses RLS but is still subject to the
-- trigger above. Revoke UPDATE/DELETE from the API roles as defence in depth.

revoke update, delete on public.ledger_leaves from anon, authenticated;
revoke update, delete on public.ledger_roots from anon, authenticated;
