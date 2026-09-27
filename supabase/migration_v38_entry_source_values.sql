-- Migration V38: entry source allowlist (+ai-extract, +vsme-feeder)
-- ==========================================================================
-- esrs_entries.source was CHECK-constrained (v23) to
-- ('manual', 'ai_extracted', 'imported', 'calculated'). The extract review
-- queue confirms as source='ai-extract' and the VSME feeder as
-- source='vsme-feeder' — both 500 on the constraint in production.
-- Widen the allowlist (legacy values stay valid). Safe anywhere.
-- ==========================================================================

alter table public.esrs_entries drop constraint if exists esrs_entries_source_check;
alter table public.esrs_entries add constraint esrs_entries_source_check
  check (source in ('manual', 'ai_extracted', 'imported', 'calculated', 'ai-extract', 'vsme-feeder'));
