-- Migration V37: AI provenance on entries (extraction flywheel)
-- ==========================================================================
-- Lets the flywheel distinguish "accepted as extracted" from "edited after
-- extraction" without touching the corrections table (which requires a real
-- user FK and therefore excludes the guest sandbox):
--
--   * esrs_entries.ai_value      the value the pipeline proposed
--   * esrs_entries.ai_confidence the pipeline confidence at confirm time
--
-- A later edit (value != ai_value) is a drift signal; the mining endpoint
-- aggregates drift per datapoint/DR into the monthly miss-pattern report.
-- Purely additive. Run AFTER migration_v36.
-- ==========================================================================

alter table public.esrs_entries add column if not exists ai_value jsonb;
alter table public.esrs_entries add column if not exists ai_confidence numeric check (
  ai_confidence is null or (ai_confidence >= 0 and ai_confidence <= 1)
);

comment on column public.esrs_entries.ai_value is
  'Pipeline-proposed value at confirm time; drift vs value feeds the extraction flywheel.';
comment on column public.esrs_entries.ai_confidence is
  'Pipeline confidence at confirm time; used for confidence calibration.';
