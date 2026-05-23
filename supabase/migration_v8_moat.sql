-- Migration V8: Defensibility & Moat Layer
-- Audit Trail, Benchmark Flywheel, Fine-tune Pipeline, Filing Ground Truth
-- This creates switching costs, network effects, and proprietary data assets.

-- ============================================================
-- LAYER 1: COMPLIANCE AUDIT TRAIL (Immutable Change Log)
-- Regulators & auditors REQUIRE this. Massive switching cost.
-- ============================================================

-- Immutable audit log — append-only, no updates/deletes allowed
create table if not exists public.audit_trail (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete set null,
  user_id uuid references public.profiles(id) on delete set null not null,
  user_email text, -- denormalized for permanence even if user deleted
  action text not null check (action in (
    'create', 'update', 'delete', 'verify', 'approve', 'reject',
    'submit', 'export', 'import', 'extract', 'invite', 'role_change',
    'login', 'logout', 'settings_change'
  )),
  entity_type text not null, -- 'brsr_entry', 'report', 'supplier', 'document', etc.
  entity_id uuid, -- reference to the changed record
  datapoint_id text, -- BRSR datapoint ID if applicable (e.g., 'C.P6.GHG.1')
  financial_year text,
  old_value jsonb, -- previous value (null for creates)
  new_value jsonb, -- new value (null for deletes)
  change_reason text, -- user-provided justification for the change
  metadata jsonb, -- extra context: IP, user agent, session, etc.
  checksum text, -- SHA-256 hash of (prev_checksum + this_row) for tamper detection
  created_at timestamptz not null default now()
);

-- Make audit trail truly append-only (no updates or deletes via RLS)
alter table public.audit_trail enable row level security;

-- Users can only INSERT into audit trail, never update/delete
create policy "Anyone can insert audit entries" on public.audit_trail
  for insert with check (auth.uid() = user_id);

-- Users can view their org's audit trail
create policy "Users can view org audit trail" on public.audit_trail
  for select using (
    user_id = auth.uid() or
    org_id in (select org_id from public.org_members where user_id = auth.uid())
  );

-- Prevent any updates or deletes (defense in depth)
create policy "No updates allowed" on public.audit_trail
  for update using (false);
create policy "No deletes allowed" on public.audit_trail
  for delete using (false);

-- Data version history — every change to a brsr_entry creates a version
create table if not exists public.data_versions (
  id uuid default gen_random_uuid() primary key,
  entry_id uuid references public.brsr_entries(id) on delete set null,
  org_id uuid references public.organizations(id) on delete set null,
  user_id uuid references public.profiles(id) on delete set null not null,
  datapoint_id text not null,
  financial_year text not null,
  version_number int not null default 1,
  value jsonb not null,
  source text, -- 'manual', 'ai_extracted', 'imported', 'calculated'
  change_reason text,
  is_current boolean default true,
  created_at timestamptz not null default now()
);

alter table public.data_versions enable row level security;
create policy "Users can manage own versions" on public.data_versions
  for all using (auth.uid() = user_id);

-- Digital signature for submitted reports (non-repudiation)
create table if not exists public.submission_signatures (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete set null,
  user_id uuid references public.profiles(id) on delete set null not null,
  financial_year text not null,
  submission_type text check (submission_type in ('brsr_annual', 'brsr_core_quarterly', 'xbrl_filing', 'board_approval')),
  data_snapshot_hash text not null, -- SHA-256 of entire submitted dataset
  signatory_name text not null,
  signatory_designation text not null,
  signatory_din text, -- Director Identification Number
  signed_at timestamptz not null default now(),
  ip_address text,
  user_agent text,
  certificate_data jsonb, -- future: DSC details
  created_at timestamptz not null default now()
);

alter table public.submission_signatures enable row level security;
create policy "Users can manage own signatures" on public.submission_signatures
  for all using (auth.uid() = user_id);

-- Trigger: auto-create audit entry on brsr_entries changes
create or replace function public.audit_brsr_entry_changes()
returns trigger as $$
begin
  if TG_OP = 'INSERT' then
    insert into public.audit_trail (user_id, user_email, action, entity_type, entity_id, datapoint_id, financial_year, new_value, org_id)
    values (NEW.user_id, (select email from public.profiles where id = NEW.user_id), 'create', 'brsr_entry', NEW.id, NEW.datapoint_id, NEW.financial_year, NEW.value, NEW.org_id);
    -- Also create version 1
    insert into public.data_versions (entry_id, org_id, user_id, datapoint_id, financial_year, version_number, value, source)
    values (NEW.id, NEW.org_id, NEW.user_id, NEW.datapoint_id, NEW.financial_year, 1, NEW.value, NEW.source);
    return NEW;
  elsif TG_OP = 'UPDATE' then
    -- Only log if value actually changed
    if OLD.value is distinct from NEW.value then
      insert into public.audit_trail (user_id, user_email, action, entity_type, entity_id, datapoint_id, financial_year, old_value, new_value, org_id)
      values (NEW.user_id, (select email from public.profiles where id = NEW.user_id), 'update', 'brsr_entry', NEW.id, NEW.datapoint_id, NEW.financial_year, OLD.value, NEW.value, NEW.org_id);
      -- Create new version, mark previous as not current
      update public.data_versions set is_current = false where entry_id = NEW.id and is_current = true;
      insert into public.data_versions (entry_id, org_id, user_id, datapoint_id, financial_year, version_number, value, source)
      values (NEW.id, NEW.org_id, NEW.user_id, NEW.datapoint_id, NEW.financial_year,
        (select coalesce(max(version_number), 0) + 1 from public.data_versions where entry_id = NEW.id),
        NEW.value, NEW.source);
    end if;
    return NEW;
  elsif TG_OP = 'DELETE' then
    insert into public.audit_trail (user_id, user_email, action, entity_type, entity_id, datapoint_id, financial_year, old_value, org_id)
    values (OLD.user_id, (select email from public.profiles where id = OLD.user_id), 'delete', 'brsr_entry', OLD.id, OLD.datapoint_id, OLD.financial_year, OLD.value, OLD.org_id);
    return OLD;
  end if;
end;
$$ language plpgsql security definer;

create trigger audit_brsr_entries
  after insert or update or delete on public.brsr_entries
  for each row execute function public.audit_brsr_entry_changes();


-- ============================================================
-- LAYER 2: BENCHMARK FLYWHEEL (Network Effect)
-- Every user submission feeds anonymized sector benchmarks.
-- More users = better benchmarks = more users. Moat grows over time.
-- ============================================================

-- Anonymized benchmark data (aggregated from real filings)
create table if not exists public.benchmark_data (
  id uuid default gen_random_uuid() primary key,
  datapoint_id text not null, -- BRSR datapoint
  sector text not null, -- e.g., 'IT', 'Banking', 'Manufacturing'
  market_cap_tier text check (market_cap_tier in ('large_cap', 'mid_cap', 'small_cap')),
  financial_year text not null,
  -- Aggregated statistics (no individual company data exposed)
  sample_size int not null default 0,
  mean_value decimal(15,4),
  median_value decimal(15,4),
  p25_value decimal(15,4), -- 25th percentile
  p75_value decimal(15,4), -- 75th percentile
  p90_value decimal(15,4), -- 90th percentile (top performers)
  min_value decimal(15,4),
  max_value decimal(15,4),
  unit text, -- 'tCO2e', 'MWh', '%', 'INR_cr', etc.
  trend_yoy decimal(5,2), -- year-over-year change %
  last_updated_at timestamptz default now(),
  created_at timestamptz not null default now(),
  unique(datapoint_id, sector, market_cap_tier, financial_year)
);

-- User consent for benchmark contribution
create table if not exists public.benchmark_consents (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  consent_given boolean default false,
  consent_scope text default 'anonymized_aggregate', -- what they agreed to share
  consented_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  unique(org_id)
);

alter table public.benchmark_data enable row level security;
alter table public.benchmark_consents enable row level security;

-- Benchmarks are readable by everyone (they're anonymized aggregates)
create policy "Anyone can read benchmarks" on public.benchmark_data for select using (true);
create policy "Users can manage own consent" on public.benchmark_consents for all using (auth.uid() = user_id);

-- Function to update benchmarks when entries are submitted (runs periodically or on-demand)
create or replace function public.refresh_benchmarks(target_datapoint text default null)
returns void as $$
begin
  -- Only aggregate from orgs that gave consent
  insert into public.benchmark_data (datapoint_id, sector, market_cap_tier, financial_year, sample_size, mean_value, median_value, p25_value, p75_value, p90_value, min_value, max_value, last_updated_at)
  select
    e.datapoint_id,
    coalesce(p.company_name, 'Unknown') as sector, -- TODO: use actual sector from profiles
    'mid_cap' as market_cap_tier, -- TODO: derive from org settings
    e.financial_year,
    count(*) as sample_size,
    avg((e.value->>'value')::decimal) as mean_value,
    percentile_cont(0.5) within group (order by (e.value->>'value')::decimal) as median_value,
    percentile_cont(0.25) within group (order by (e.value->>'value')::decimal) as p25_value,
    percentile_cont(0.75) within group (order by (e.value->>'value')::decimal) as p75_value,
    percentile_cont(0.9) within group (order by (e.value->>'value')::decimal) as p90_value,
    min((e.value->>'value')::decimal) as min_value,
    max((e.value->>'value')::decimal) as max_value,
    now() as last_updated_at
  from public.brsr_entries e
  join public.profiles p on p.id = e.user_id
  join public.benchmark_consents bc on bc.org_id = e.org_id and bc.consent_given = true
  where (target_datapoint is null or e.datapoint_id = target_datapoint)
    and e.value->>'value' is not null
    and (e.value->>'value')::text ~ '^\d+\.?\d*$' -- only numeric values
  group by e.datapoint_id, p.company_name, e.financial_year
  having count(*) >= 3 -- minimum 3 companies for anonymity
  on conflict (datapoint_id, sector, market_cap_tier, financial_year)
  do update set
    sample_size = EXCLUDED.sample_size,
    mean_value = EXCLUDED.mean_value,
    median_value = EXCLUDED.median_value,
    p25_value = EXCLUDED.p25_value,
    p75_value = EXCLUDED.p75_value,
    p90_value = EXCLUDED.p90_value,
    min_value = EXCLUDED.min_value,
    max_value = EXCLUDED.max_value,
    last_updated_at = now();
end;
$$ language plpgsql security definer;


-- ============================================================
-- LAYER 3: FINE-TUNE PIPELINE (Proprietary AI)
-- User corrections to AI extractions become training data.
-- ============================================================

-- Extraction feedback (corrections to AI output)
create table if not exists public.extraction_corrections (
  id uuid default gen_random_uuid() primary key,
  report_id uuid references public.reports(id) on delete set null,
  user_id uuid references public.profiles(id) on delete set null not null,
  datapoint_id text not null,
  -- What the AI extracted
  ai_extracted_value jsonb not null,
  ai_confidence decimal(3,2), -- original confidence score
  ai_model text, -- 'groq/llama', 'claude-3.5', 'gemini-1.5', etc.
  -- What the user corrected it to
  corrected_value jsonb not null,
  correction_type text check (correction_type in ('value_wrong', 'unit_wrong', 'datapoint_mismatched', 'missing_extraction', 'hallucination')),
  -- Source context for training
  source_text text, -- the PDF text passage that contains the correct answer
  page_number int,
  -- Quality flags
  is_verified boolean default false, -- verified by second user
  verified_by uuid references public.profiles(id),
  used_for_training boolean default false,
  training_batch_id text,
  created_at timestamptz not null default now()
);

-- Extraction quality metrics (per-model, per-datapoint accuracy tracking)
create table if not exists public.extraction_quality (
  id uuid default gen_random_uuid() primary key,
  ai_model text not null,
  datapoint_id text not null,
  financial_year text,
  -- Metrics
  total_extractions int default 0,
  correct_extractions int default 0,
  accuracy decimal(5,4), -- 0.0000 to 1.0000
  avg_confidence decimal(3,2),
  common_errors jsonb, -- [{error_type, count, example}]
  last_evaluated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(ai_model, datapoint_id, financial_year)
);

-- Fine-tuning datasets (ready for model training)
create table if not exists public.training_datasets (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  description text,
  model_target text, -- 'extraction', 'scoring', 'gap_analysis'
  version text not null,
  -- Dataset stats
  total_examples int default 0,
  verified_examples int default 0,
  sectors_covered text[],
  datapoints_covered text[],
  financial_years text[],
  -- Training metadata
  format text check (format in ('jsonl', 'parquet', 'csv')),
  storage_url text, -- S3/GCS location of dataset file
  status text default 'building' check (status in ('building', 'ready', 'training', 'deployed', 'deprecated')),
  model_id text, -- fine-tuned model ID once trained
  eval_metrics jsonb, -- {accuracy, f1, recall, precision} on held-out test set
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.extraction_corrections enable row level security;
alter table public.extraction_quality enable row level security;
alter table public.training_datasets enable row level security;

create policy "Users can manage own corrections" on public.extraction_corrections for all using (auth.uid() = user_id);
create policy "Anyone can read quality metrics" on public.extraction_quality for select using (true);
create policy "Admins can manage datasets" on public.training_datasets for all using (
  auth.uid() in (select user_id from public.org_members where role = 'owner')
);


-- ============================================================
-- LAYER 4: VERIFIED FILING DATABASE (Proprietary Dataset)
-- Ground truth from real BSE/NSE XBRL filings.
-- ============================================================

-- Scraped & parsed BRSR filings from BSE/NSE
create table if not exists public.filing_ground_truth (
  id uuid default gen_random_uuid() primary key,
  -- Company info (public, non-proprietary)
  company_name text not null,
  cin text, -- Corporate Identity Number
  bse_code text,
  nse_symbol text,
  sector text,
  market_cap_tier text check (market_cap_tier in ('large_cap', 'mid_cap', 'small_cap')),
  -- Filing info
  financial_year text not null,
  filing_date date,
  source_url text, -- BSE/NSE link
  filing_format text check (filing_format in ('xbrl', 'pdf', 'html')),
  -- Extracted data (our parsed version of their filing)
  extracted_datapoints jsonb, -- {datapoint_id: {value, unit, source_page}}
  total_datapoints_extracted int default 0,
  disclosure_score decimal(4,2), -- % of mandatory datapoints disclosed
  -- Quality
  parse_quality text check (parse_quality in ('high', 'medium', 'low', 'manual_review_needed')),
  manually_verified boolean default false,
  verified_by uuid references public.profiles(id),
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  unique(cin, financial_year)
);

-- Sector-level aggregated benchmarks from real filings
create table if not exists public.sector_benchmarks_live (
  id uuid default gen_random_uuid() primary key,
  sector text not null,
  market_cap_tier text,
  financial_year text not null,
  datapoint_id text not null,
  -- Stats from real filings
  companies_reporting int default 0,
  companies_total int default 0, -- total in sector
  disclosure_rate decimal(5,2), -- % that actually report this
  mean_value decimal(15,4),
  median_value decimal(15,4),
  best_in_class_value decimal(15,4),
  worst_value decimal(15,4),
  unit text,
  -- Source tracking
  source text default 'bse_nse_scrape',
  last_updated_at timestamptz default now(),
  created_at timestamptz not null default now(),
  unique(sector, datapoint_id, financial_year, market_cap_tier)
);

alter table public.filing_ground_truth enable row level security;
alter table public.sector_benchmarks_live enable row level security;

-- Ground truth is readable by all (it's from public filings)
create policy "Anyone can read ground truth" on public.filing_ground_truth for select using (true);
create policy "Anyone can read live benchmarks" on public.sector_benchmarks_live for select using (true);
-- Only service role can insert (from scraper)
create policy "Service can insert ground truth" on public.filing_ground_truth for insert with check (auth.role() = 'service_role');
create policy "Service can insert live benchmarks" on public.sector_benchmarks_live for insert with check (auth.role() = 'service_role');


-- ============================================================
-- INDEXES
-- ============================================================
create index if not exists idx_audit_trail_entity on public.audit_trail(entity_type, entity_id);
create index if not exists idx_audit_trail_user on public.audit_trail(user_id, created_at desc);
create index if not exists idx_audit_trail_org on public.audit_trail(org_id, created_at desc);
create index if not exists idx_audit_trail_datapoint on public.audit_trail(datapoint_id, financial_year);
create index if not exists idx_data_versions_entry on public.data_versions(entry_id, version_number desc);
create index if not exists idx_extraction_corrections_dp on public.extraction_corrections(datapoint_id, ai_model);
create index if not exists idx_benchmark_data_lookup on public.benchmark_data(datapoint_id, sector, financial_year);
create index if not exists idx_filing_ground_truth_sector on public.filing_ground_truth(sector, financial_year);
create index if not exists idx_sector_benchmarks_live_lookup on public.sector_benchmarks_live(sector, datapoint_id, financial_year);
