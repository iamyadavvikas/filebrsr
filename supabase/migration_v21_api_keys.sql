-- Migration v21: API keys (B2B programmatic access)
-- ==========================================================================
-- Backs the existing app/api_keys.py auth layer, which looks up keys by
-- sha256(key) in `api_keys` and meters per-day calls in `api_usage`. Those
-- tables were referenced in code but never created — this migration adds them.
--
-- Keys are owned by a USER (and optionally their ORG for shared visibility).
-- Only the sha256 hash is stored; the raw key is shown to the user exactly
-- once at creation time (handled in the API layer, never persisted).
--
-- Idempotent. Run AFTER migration_v15_tenancy.sql (organizations exist).
-- ==========================================================================

-- ─── api_keys ──────────────────────────────────────────────────────────────
create table if not exists public.api_keys (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  org_id      uuid references public.organizations(id) on delete cascade,
  name        text not null default 'API key',
  key_prefix  text not null,                       -- e.g. "fbrsr_1a2b3c…" for display only
  key_hash    text not null unique,                -- sha256(raw_key); raw key never stored
  tier        text not null default 'free'
                check (tier in ('free', 'pro', 'enterprise')),
  active      boolean not null default true,
  last_used_at timestamptz,
  created_at  timestamptz not null default now()
);

create index if not exists api_keys_user_id_idx on public.api_keys (user_id);
create index if not exists api_keys_key_hash_idx on public.api_keys (key_hash);

-- ─── api_usage (per-key, per-day request counter) ──────────────────────────
create table if not exists public.api_usage (
  id            uuid primary key default gen_random_uuid(),
  key_id        uuid not null references public.api_keys(id) on delete cascade,
  date          date not null default current_date,
  request_count int not null default 0,
  created_at    timestamptz not null default now(),
  unique (key_id, date)
);

create index if not exists api_usage_key_id_date_idx on public.api_usage (key_id, date);

-- ─── RLS ───────────────────────────────────────────────────────────────────
-- The API layer reads/writes with the service key (bypasses RLS). These
-- policies are defence-in-depth so a user with a normal session can only ever
-- see their OWN keys/usage if querying directly via PostgREST.
alter table public.api_keys enable row level security;
alter table public.api_usage enable row level security;

drop policy if exists "Users manage own api keys" on public.api_keys;
create policy "Users manage own api keys"
  on public.api_keys for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users view own api usage" on public.api_usage;
create policy "Users view own api usage"
  on public.api_usage for select
  using (
    exists (
      select 1 from public.api_keys k
      where k.id = api_usage.key_id and k.user_id = auth.uid()
    )
  );

comment on table public.api_keys is
  'B2B programmatic access keys. Only sha256(key) is stored (key_hash); raw key shown once at creation.';
comment on table public.api_usage is
  'Per-key per-day request counter enforcing API_TIERS[tier].requests_per_day.';
