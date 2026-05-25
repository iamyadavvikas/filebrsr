-- Migration v3: Add is_admin column + Row Level Security for multi-tenant isolation
-- Run this in Supabase SQL Editor

-- ═══════════════════════════════════════════════════════════════
-- 1. Add is_admin column to profiles
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;

-- NOTE: Admin assignment is NOT done in this migration.
-- Run the separate, ungitted script `supabase/admin_grants.sql.local` (gitignored)
-- to grant admin to specific emails. Example template:
--   UPDATE profiles SET is_admin = true WHERE email = 'your-admin@example.com';
-- This keeps personal emails out of the public repository.

-- ═══════════════════════════════════════════════════════════════
-- 2. Enable RLS on all user-facing tables
-- ═══════════════════════════════════════════════════════════════

-- REPORTS table
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users see own reports" ON reports;
CREATE POLICY "Users see own reports" ON reports
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users insert own reports" ON reports;
CREATE POLICY "Users insert own reports" ON reports
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own reports" ON reports;
CREATE POLICY "Users update own reports" ON reports
  FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users delete own reports" ON reports;
CREATE POLICY "Users delete own reports" ON reports
  FOR DELETE USING (auth.uid() = user_id);

-- Service role bypasses RLS (for backend operations)
DROP POLICY IF EXISTS "Service role full access reports" ON reports;
CREATE POLICY "Service role full access reports" ON reports
  FOR ALL USING (auth.role() = 'service_role');

-- BRSR_ENTRIES table
ALTER TABLE brsr_entries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users see own entries" ON brsr_entries;
CREATE POLICY "Users see own entries" ON brsr_entries
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users insert own entries" ON brsr_entries;
CREATE POLICY "Users insert own entries" ON brsr_entries
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own entries" ON brsr_entries;
CREATE POLICY "Users update own entries" ON brsr_entries
  FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users delete own entries" ON brsr_entries;
CREATE POLICY "Users delete own entries" ON brsr_entries
  FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access brsr_entries" ON brsr_entries;
CREATE POLICY "Service role full access brsr_entries" ON brsr_entries
  FOR ALL USING (auth.role() = 'service_role');

-- PROFILES table (users see only their own profile)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users see own profile" ON profiles;
CREATE POLICY "Users see own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users update own profile" ON profiles;
CREATE POLICY "Users update own profile" ON profiles
  FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Service role full access profiles" ON profiles;
CREATE POLICY "Service role full access profiles" ON profiles
  FOR ALL USING (auth.role() = 'service_role');

-- PAYMENTS table
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users see own payments" ON payments;
CREATE POLICY "Users see own payments" ON payments
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access payments" ON payments;
CREATE POLICY "Service role full access payments" ON payments
  FOR ALL USING (auth.role() = 'service_role');

-- ANALYTICS_EVENTS table (only service role can read all)
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users insert own events" ON analytics_events;
CREATE POLICY "Users insert own events" ON analytics_events
  FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access analytics" ON analytics_events;
CREATE POLICY "Service role full access analytics" ON analytics_events
  FOR ALL USING (auth.role() = 'service_role');

-- SUPPLIERS table (if exists)
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'suppliers') THEN
    EXECUTE 'ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS "Users see own suppliers" ON suppliers';
    EXECUTE 'CREATE POLICY "Users see own suppliers" ON suppliers FOR SELECT USING (auth.uid() = user_id)';
    EXECUTE 'DROP POLICY IF EXISTS "Users manage own suppliers" ON suppliers';
    EXECUTE 'CREATE POLICY "Users manage own suppliers" ON suppliers FOR ALL USING (auth.uid() = user_id)';
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access suppliers" ON suppliers';
    EXECUTE 'CREATE POLICY "Service role full access suppliers" ON suppliers FOR ALL USING (auth.role() = ''service_role'')';
  END IF;
END $$;

-- AUDIT_LOG table (if exists)
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'audit_log') THEN
    EXECUTE 'ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS "Users see own audit logs" ON audit_log';
    EXECUTE 'CREATE POLICY "Users see own audit logs" ON audit_log FOR SELECT USING (auth.uid() = user_id)';
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access audit_log" ON audit_log';
    EXECUTE 'CREATE POLICY "Service role full access audit_log" ON audit_log FOR ALL USING (auth.role() = ''service_role'')';
  END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════
-- 3. Create extraction_jobs table for background processing
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS extraction_jobs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  file_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status ON extraction_jobs(status) WHERE status = 'queued';
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_user ON extraction_jobs(user_id);

ALTER TABLE extraction_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users see own jobs" ON extraction_jobs;
CREATE POLICY "Users see own jobs" ON extraction_jobs
  FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role full access jobs" ON extraction_jobs;
CREATE POLICY "Service role full access jobs" ON extraction_jobs
  FOR ALL USING (auth.role() = 'service_role');
