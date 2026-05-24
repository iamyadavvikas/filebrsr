-- Migration: Update plan check constraint to include new tier names
-- Run in Supabase SQL Editor

-- Drop old constraint and add new one with all valid plan names
ALTER TABLE public.profiles
DROP CONSTRAINT IF EXISTS profiles_plan_check;

ALTER TABLE public.profiles
ADD CONSTRAINT profiles_plan_check
CHECK (plan IN ('free', 'starter', 'pro', 'growth', 'scale', 'enterprise'));

-- Add extractions_this_month and month_reset_at if not present
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS extractions_this_month int NOT NULL DEFAULT 0;

ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS month_reset_at timestamptz NOT NULL DEFAULT (date_trunc('month', now()) + interval '1 month');

-- Add supplier_limit column for custom overrides (NULL = use plan default)
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS supplier_limit int DEFAULT NULL;
