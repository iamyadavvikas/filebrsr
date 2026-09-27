-- Migration V29: open-to-all guest sandbox sessions
-- ==========================================================================
-- Lets logged-out visitors explore the full CSRD workspace by provisioning a
-- throwaway sandbox organisation scoped to an opaque session token. Guests
-- can seed / assess / generate / validate / attest and submit in sandbox
-- mode, but never file with a real OAM and never hold provenances that
-- require a real Supabase user.
--
-- Schema choices:
--   * esrs_guest_sessions maps a token to its sandbox org + expiry. Expired
--     rows are purged at mint time; deleting a row cascades to the org and
--     every esrs_* row it owns.
--   * The provenance FKs are relaxed to nullable so sandbox rows (created by
--     nobody) can exist. Real organisations are unaffected.
--
-- Idempotent. Run AFTER migration_v28_esrs_attestation.sql.
-- ==========================================================================

-- 1. Relax provenance FKs so sandbox rows need no real auth user ------------
-- organizations.created_by / esrs_entries.user_id remain NOT NULL for real
-- orgs (the org router always supplies them); guest sandbox orgs and entries
-- simply set them to NULL.

alter table public.organizations
  alter column created_by drop not null;

alter table public.esrs_entries
  alter column user_id drop not null;

-- 2. Guest session ledger ----------------------------------------------------
-- token   opaque bearer (guest_<random>) presented as the Bearer credential;
-- org_id  the sandbox organisation that holds this guest's esrs_* rows.
-- A single guest session = a single sandbox org: rows are never shared, so
-- two guests can never see each other's data (defence-in-depth on top of the
-- backend's org scoping), and expiry + cascade gives automatic retention.

create table if not exists public.esrs_guest_sessions (
  token      text primary key,
  org_id     uuid not null references public.organizations(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create index if not exists esrs_guest_sessions_expiry_idx
  on public.esrs_guest_sessions (expires_at);

alter table public.esrs_guest_sessions enable row level security;

-- No client policies: sessions are held server-side only. With RLS enabled
-- and no policy, PostgREST (even with the anon key) can read/write nothing;
-- the service key (which bypasses RLS) is the only way to touch this table.

comment on table public.esrs_guest_sessions is
  'Opaque guest session tokens for the open CSRD sandbox. Expired rows are purged on mint; deleting a row cascades to the sandbox org and all its esrs_* rows.';