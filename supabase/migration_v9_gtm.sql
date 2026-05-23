-- Migration v9: GTM Infrastructure — Leads + Supplier Invites (Viral Loop)
-- Phase 1: Lead capture from readiness assessment & resources
-- Phase 2: Supplier invite flow (network effects engine)

-- ═══════════════════════════════════════════════════════════════
-- LEADS TABLE — Inbound funnel
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    company_name TEXT,
    contact_name TEXT,
    source TEXT DEFAULT 'readiness_assessment',  -- readiness_assessment, resource_download, demo_request, organic
    score INTEGER,                               -- readiness score 0-100
    readiness_level TEXT,                        -- Advanced, Progressing, Early Stage, Not Ready
    tags TEXT[],                                 -- target_icp, high_value, enterprise, supplier, carbon_ready, etc.
    metadata JSONB DEFAULT '{}'::jsonb,           -- answers, phase_scores, UTM params
    status TEXT DEFAULT 'new',                   -- new, contacted, qualified, converted, lost
    notes TEXT,
    converted_user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for lead management
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at DESC);

-- ═══════════════════════════════════════════════════════════════
-- SUPPLIER INVITES TABLE — The viral network loop
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS supplier_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID,                                 -- buyer's org that invited
    invited_by UUID REFERENCES auth.users(id),   -- who sent the invite
    supplier_name TEXT NOT NULL,
    supplier_email TEXT NOT NULL,
    contact_person TEXT,
    industry TEXT,
    tier TEXT DEFAULT 'tier_1',                   -- tier_1, tier_2, tier_3
    assessment_token TEXT UNIQUE NOT NULL,        -- unique link token
    status TEXT DEFAULT 'invited',               -- invited, opened, in_progress, completed, expired
    assessment_score JSONB,                       -- { environment: 70, social: 65, governance: 80, overall: 72 }
    assessment_completed_at TIMESTAMPTZ,
    reminder_count INTEGER DEFAULT 0,
    last_reminder_at TIMESTAMPTZ,
    invited_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for supplier invite management
CREATE INDEX IF NOT EXISTS idx_supplier_invites_org ON supplier_invites(org_id);
CREATE INDEX IF NOT EXISTS idx_supplier_invites_token ON supplier_invites(assessment_token);
CREATE INDEX IF NOT EXISTS idx_supplier_invites_email ON supplier_invites(supplier_email);
CREATE INDEX IF NOT EXISTS idx_supplier_invites_status ON supplier_invites(status);
CREATE INDEX IF NOT EXISTS idx_supplier_invites_invited ON supplier_invites(invited_at DESC);

-- ═══════════════════════════════════════════════════════════════
-- SUPPLIER ASSESSMENTS — Add missing columns for Phase 2 (table already exists)
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS invite_id UUID;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS supplier_email TEXT;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS supplier_name TEXT;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS scores JSONB;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS badge_level TEXT;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS percentile INTEGER;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS scope3_estimate JSONB;
ALTER TABLE supplier_assessments ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_supplier_assessments_email ON supplier_assessments(supplier_email);
CREATE INDEX IF NOT EXISTS idx_supplier_assessments_invite ON supplier_assessments(invite_id);
CREATE INDEX IF NOT EXISTS idx_supplier_assessments_badge ON supplier_assessments(badge_level);

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_assessments ENABLE ROW LEVEL SECURITY;

-- Leads: service role full access
DROP POLICY IF EXISTS "Service role manages leads" ON leads;
CREATE POLICY "Service role manages leads" ON leads
    FOR ALL USING (true) WITH CHECK (true);

-- Supplier invites: service role full access
DROP POLICY IF EXISTS "Service role manages invites" ON supplier_invites;
CREATE POLICY "Service role manages invites" ON supplier_invites
    FOR ALL USING (true) WITH CHECK (true);

-- Supplier assessments: service role full access
DROP POLICY IF EXISTS "Service role manages assessments" ON supplier_assessments;
CREATE POLICY "Service role manages assessments" ON supplier_assessments
    FOR ALL USING (true) WITH CHECK (true);
