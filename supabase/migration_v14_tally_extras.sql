-- Migration V14: cost-centre + vendor-state columns on raw_records (Tally Slice 5 partial)
-- ==========================================================================
-- Adds three nullable columns so the Tally connector can persist:
--
--   * cost_centre_name      — Tally Cost Centre allocation (e.g. "Plant-Mumbai")
--                             used downstream to roll emissions up by facility.
--   * cost_centre_category  — Tally Cost Centre Category (the parent grouping,
--                             e.g. "Manufacturing"). Persisting both means we
--                             don't have to re-derive the hierarchy at query time.
--   * vendor_state_code     — 2-digit state code derived from vendor_gstin
--                             (positions 1-2 of a valid 15-char GSTIN).
--                             Enables intra- vs inter-state spend analysis
--                             and Scope-3 upstream-transport distance proxies.
--
-- All three are nullable + indexed-on-demand only. No data backfill — older
-- raw_records rows simply carry NULL until they're re-ingested.
--
-- Run AFTER migration_v13_raw_records.sql.

alter table public.raw_records
  add column if not exists cost_centre_name      text,
  add column if not exists cost_centre_category  text,
  add column if not exists vendor_state_code     text;

-- Lightweight index for facility-level rollups. Partial index so we don't
-- bloat storage on rows where cost-centre tagging was never captured (e.g.
-- single-plant SMEs).
create index if not exists raw_records_cost_centre_idx
  on public.raw_records (user_id, fiscal_year, cost_centre_name)
  where cost_centre_name is not null;

-- Intra- vs inter-state breakdown is a common BRSR Principle-6 cut.
create index if not exists raw_records_vendor_state_idx
  on public.raw_records (user_id, fiscal_year, vendor_state_code)
  where vendor_state_code is not null;
