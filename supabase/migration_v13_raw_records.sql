-- Migration V13: raw_records ledger + HSN/SAC emission map (Tally connector Slice 0)
-- ==========================================================================
-- Adds two tables that unblock the apps/connector-tally roadmap:
--
--   1. hsn_emission_map  — global reference table mapping Indian HSN/SAC codes
--      to GHG-Protocol scope + Scope-3 category. Seeded from the JSON file at
--      lookups/hsn_scope3_v1.json by app.tally.classifier at import time
--      (no DB seed here — keeps the migration replayable). Treat this row set
--      as the canonical persisted view; the JSON is the source of truth.
--
--   2. raw_records       — append-only ledger of line-item records ingested
--      from any source system (Tally XML today; SAP / Zoho / Oracle later).
--      Becomes the upstream source for emissions calculations once we wire
--      app.carbon_calculator to read from here instead of free-text BRSR
--      extraction. GST splits, fiscal-year tag, voucher GUID, and a
--      file-level SHA-256 are persisted for audit-trail replayability.
--
-- Run AFTER migration_v12_chunks_pgvector.sql.

-- ─── HSN / SAC reference table ────────────────────────────────────────────

create table if not exists public.hsn_emission_map (
  hsn_code            text primary key,            -- HSN or SAC (4–8 digits, no dots)
  description         text not null,
  scope               int  not null check (scope in (1, 2, 3)),
  scope3_category     text,                        -- one of 15 GHG Scope-3 categories; null when scope != 3
  emission_basis      text not null check (emission_basis in ('quantity', 'spend')),
  default_factor_key  text,                        -- forward link into app.factors_india keys (future)
  notes               text,
  source              text not null,               -- CBIC notification / GST council ref
  version             text not null,               -- "hsn_scope3_v1" etc.
  created_at          timestamptz not null default now()
);

create index if not exists hsn_emission_map_scope_idx
  on public.hsn_emission_map (scope, scope3_category);

-- Reference data; no RLS. Service role writes, all authenticated users read.
grant select on public.hsn_emission_map to authenticated;

-- ─── raw_records ───────────────────────────────────────────────────────────

create table if not exists public.raw_records (
  id                          bigserial primary key,
  user_id                     uuid not null references public.profiles(id) on delete cascade,

  -- Source provenance --------------------------------------------------------
  source_system               text not null check (source_system in
                                ('tally', 'sap', 'zoho', 'oracle', 'manual_xlsx')),
  source_file_sha256          text not null,        -- SHA-256 of the original upload (audit trail)
  source_voucher_id           text not null,        -- Tally GUID / SAP DocEntry / etc.
  source_voucher_number       text,                 -- human-readable: "PUR/2025/0001"
  voucher_type                text,                 -- "Purchase" | "Sales" | "Journal" | "Payment" | ...

  -- Indian fiscal context ----------------------------------------------------
  fiscal_year                 text not null,        -- "FY2024-25"
  posting_date                date not null,

  -- Counterparty -------------------------------------------------------------
  vendor_name                 text,
  vendor_gstin                text,                 -- 15-char GSTIN; null for B2C / non-GST

  -- Item -------------------------------------------------------------------
  ledger_name                 text,
  hsn_code                    text,                 -- references hsn_emission_map.hsn_code (not enforced — codes evolve)
  description                 text,                 -- stock item / narration excerpt

  -- Money (all INR, GST kept split for downstream input-tax reasoning) -------
  base_value                  numeric(18, 2) not null,
  cgst                        numeric(18, 2) not null default 0,
  sgst                        numeric(18, 2) not null default 0,
  igst                        numeric(18, 2) not null default 0,
  cess                        numeric(18, 2) not null default 0,
  total_value                 numeric(18, 2) not null,

  -- Physical quantity (when present — drives quantity-basis emission calc) ---
  quantity                    numeric(18, 4),
  uom                         text,                 -- "Ltr" | "kg" | "MT" | "KWH" | ...

  -- Classification (filled by app.tally.classifier; null = needs human queue)-
  scope                       int  check (scope in (1, 2, 3)),
  scope3_category             text,
  classification_confidence   text check (classification_confidence in
                                ('high', 'medium', 'low', 'unmapped')),

  -- Audit --------------------------------------------------------------------
  raw_payload                 jsonb,                -- the original voucher node (replayable)
  created_at                  timestamptz not null default now(),

  -- Dedup: same voucher line cannot be ingested twice for the same user.
  unique (user_id, source_voucher_id, ledger_name, hsn_code)
);

create index if not exists raw_records_user_fy_idx
  on public.raw_records (user_id, fiscal_year);

-- Cheap lookup for the human-review queue.
create index if not exists raw_records_unmapped_idx
  on public.raw_records (user_id)
  where classification_confidence = 'unmapped';

-- ─── RLS ──────────────────────────────────────────────────────────────────

alter table public.raw_records enable row level security;

drop policy if exists "Users can view own raw records" on public.raw_records;
create policy "Users can view own raw records"
  on public.raw_records for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own raw records" on public.raw_records;
create policy "Users can insert own raw records"
  on public.raw_records for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete own raw records" on public.raw_records;
create policy "Users can delete own raw records"
  on public.raw_records for delete
  using (auth.uid() = user_id);

-- Service role bypasses RLS automatically; no explicit policy required.
