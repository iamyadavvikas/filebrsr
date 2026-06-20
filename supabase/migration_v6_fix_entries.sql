-- Migration V6: Fix brsr_entries unique constraint for autofill to work
-- The original constraint includes org_id which is nullable, causing upsert failures
-- APPLIED: 2025-05-23

-- Drop old constraint
ALTER TABLE public.brsr_entries DROP CONSTRAINT brsr_entries_org_id_user_id_financial_year_datapoint_id_key;

-- Add new unique constraint that works without org_id
ALTER TABLE public.brsr_entries ADD CONSTRAINT brsr_entries_user_fy_dp_unique 
  UNIQUE (user_id, financial_year, datapoint_id);

-- Note: source check constraint already allows 'ai_extracted' - verified via pg_get_constraintdef
