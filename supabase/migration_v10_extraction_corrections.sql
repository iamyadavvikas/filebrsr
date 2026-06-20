-- Migration v10: extraction_corrections
-- Captures user-supplied fixes to BRSR fields the extractor got wrong
-- or missed entirely. Drives a feedback loop for prompt tuning and a
-- future supervised eval set (no human labels exist today; this is how
-- we'll grow one organically).

-- ═══════════════════════════════════════════════════════════════
-- TABLE
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.extraction_corrections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       UUID NOT NULL REFERENCES public.reports(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- "section_a" | "section_b" | "section_c"
    section         TEXT NOT NULL CHECK (section IN ('section_a', 'section_b', 'section_c')),
    -- Field name inside the section, e.g. "turnover", "ghg_scope1".
    field_path      TEXT NOT NULL,
    -- Stored as text so we don't lose unit hints ("\u20b91,234 Cr"); the
    -- normaliser can re-parse on read if a canonical number is needed.
    original_value  TEXT,
    corrected_value TEXT NOT NULL,
    -- 1-indexed PDF page the correction relates to, when the user
    -- points at one in the UI; null if unknown.
    source_page     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_extraction_corrections_report
    ON public.extraction_corrections(report_id);
CREATE INDEX IF NOT EXISTS idx_extraction_corrections_user
    ON public.extraction_corrections(user_id);
CREATE INDEX IF NOT EXISTS idx_extraction_corrections_created
    ON public.extraction_corrections(created_at DESC);

-- ═══════════════════════════════════════════════════════════════
-- RLS
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE public.extraction_corrections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own corrections"
    ON public.extraction_corrections;
CREATE POLICY "Users can view own corrections"
    ON public.extraction_corrections
    FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own corrections"
    ON public.extraction_corrections;
CREATE POLICY "Users can insert own corrections"
    ON public.extraction_corrections
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Service role (used by the FastAPI backend via SUPABASE_SERVICE_KEY)
-- bypasses RLS automatically; no explicit policy needed.
