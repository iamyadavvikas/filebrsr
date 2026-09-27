-- Migration V36: audit_trail backfill columns
-- ==========================================================================
-- v3_platform created audit_trail lean; v8_moat declared the full shape but
-- its CREATE TABLE IF NOT EXISTS is a no-op where v3 already ran — so fresh
-- databases got the columns (via v8's idempotent ALTERs, added with the
-- migration gate) while long-lived projects may lack them. This migration
-- converges both: every column the CSRD audit writer needs, IF NOT EXISTS.
--
-- Safe to run anywhere, including production (purely additive).
-- ==========================================================================

alter table public.audit_trail add column if not exists datapoint_id text;
alter table public.audit_trail add column if not exists financial_year text;
alter table public.audit_trail add column if not exists user_email text;
alter table public.audit_trail add column if not exists change_reason text;
alter table public.audit_trail add column if not exists metadata jsonb;
alter table public.audit_trail add column if not exists checksum text;
