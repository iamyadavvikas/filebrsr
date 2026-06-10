-- Migration V11: India-specific compliance schema
-- =================================================
-- Adds the regulatory plumbing needed for real BRSR/BRSR-Core filing in India.
--
-- Scope (must-haves for the current ICP — Top-1000 listed companies):
--   1.  organizations: add CIN, PAN, LEI, GSTIN[], SEBI scrip, NIC, listing
--       status, BRSR applicability windows, financial-year end month
--   2.  fiscal_periods: explicit Apr-Mar fiscal periods, linkable from any
--       disclosure row
--   3.  brsr_disclosures: structured against the official BRSR taxonomy
--       (Principle 1-9, Essential vs Leadership), with evidence linkage
--   4.  brsr_core_kpis: the 9 SEBI-assured KPIs as first-class rows with
--       mandatory assurance_evidence_id
--   5.  csr_activities: Companies Act 2% mandate tracking (committee meetings,
--       projects, disbursements, implementing agencies, Form CSR-1/CSR-2 refs)
--   6.  dsc_signatures: DSC class, issuer, PAN of signer, document hash,
--       TSA source — adds non-repudiation on top of submission_signatures
--   7.  regulator_filings: SEBI / MCA21 / CPCB / BEE filing receipts
--   8.  rbi_fx_rates: daily RBI reference rates for MNC subsidiary
--       consolidation (replaces the env-var FX table in normalise.py)
--
-- Out of scope for v11 (additive when we land the first relevant logo):
--   PAT designated consumers, CCTS, EPR (×4), DISCOM accounts,
--   DPDPA consent log, CERT-In incident log
--
-- Notes:
--   - All money fields are INR in paise (bigint) for financial precision,
--     matching the existing subscriptions.amount convention. Convert at the
--     display layer only.
--   - Supabase Postgres does not ship the TimescaleDB extension. rbi_fx_rates
--     uses a BRIN index on (as_of_date) — plenty for the workload.
--   - All tables follow the existing RLS pattern: per-user own-rows + per-org
--     read access via org_members.
--
-- Run AFTER migration_v10_extraction_corrections.sql.

-- ============================================================
-- 1. ORGANIZATIONS — India regulatory identifiers
-- ============================================================

alter table public.organizations
  add column if not exists cin text,                          -- L65990MH1973PLC019786
  add column if not exists pan text,                          -- AAACR1234C
  add column if not exists lei text,                          -- 20-char ISO 17442
  add column if not exists gstin text[] default '{}',         -- one per state of registration
  add column if not exists sebi_scrip_code text,              -- NSE/BSE symbol or code
  add column if not exists nic_code text,                     -- National Industrial Classification (sector)
  add column if not exists listing_status text
    check (listing_status in ('NSE', 'BSE', 'NSE_BSE', 'unlisted', 'PSU')),
  add column if not exists market_cap_rank int,               -- top-1000 ranking (for BRSR applicability)
  add column if not exists fy_end_month int default 3
    check (fy_end_month between 1 and 12),                    -- 3 = March (Indian default)
  add column if not exists brsr_applicable_from_fy text,      -- 'FY2022-23' etc.
  add column if not exists brsr_core_applicable_from_fy text, -- 'FY2024-25' for top-150, 'FY2025-26' for top-250
  add column if not exists registered_address jsonb,
  add column if not exists corporate_address jsonb;

-- CIN uniqueness (a CIN identifies a single legal entity)
create unique index if not exists organizations_cin_idx
  on public.organizations(cin) where cin is not null;
create unique index if not exists organizations_pan_idx
  on public.organizations(pan) where pan is not null;
create unique index if not exists organizations_lei_idx
  on public.organizations(lei) where lei is not null;

-- ============================================================
-- 2. FISCAL_PERIODS — explicit Apr-Mar reporting windows
-- ============================================================
-- Why a table and not just a text column: every disclosure has to align to
-- a period the regulator recognises. Storing the period as a row lets us
-- attach a status (draft/submitted/locked) and a submission timestamp.

create table if not exists public.fiscal_periods (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  fy_label text not null,                                    -- 'FY2024-25'
  period_start date not null,                                -- 2024-04-01
  period_end date not null,                                  -- 2025-03-31
  is_calendar_year boolean not null default false,           -- true for MNC subs on Jan-Dec
  status text not null default 'draft'
    check (status in ('draft', 'in_review', 'submitted', 'locked')),
  submitted_at timestamptz,
  locked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(org_id, fy_label)
);

create index if not exists fiscal_periods_org_idx on public.fiscal_periods(org_id);

alter table public.fiscal_periods enable row level security;

create policy "Org members can view fiscal periods"
  on public.fiscal_periods for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create policy "Org members can manage fiscal periods"
  on public.fiscal_periods for all
  using (org_id in (select org_id from public.org_members
                     where user_id = auth.uid() and role in ('owner','admin','member')));

-- ============================================================
-- 3. BRSR_DISCLOSURES — taxonomy-keyed disclosures with evidence
-- ============================================================
-- Replaces the free-form jsonb in brsr_entries.value for the rows that
-- have to map cleanly to the official BRSR taxonomy. brsr_entries is kept
-- for fast extraction-time writes; disclosures is the "ready to file" view.

create table if not exists public.brsr_disclosures (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  fiscal_period_id uuid references public.fiscal_periods(id) on delete cascade not null,
  section text not null
    check (section in ('section_a', 'section_b', 'section_c')),
  principle int check (principle between 1 and 9),           -- null for section A/B
  indicator_code text not null,                              -- 'C.P6.1', 'A.III.4.a', etc.
  indicator_type text not null
    check (indicator_type in ('essential', 'leadership')),
  is_quantitative boolean not null default true,
  value_numeric numeric,                                     -- for quantitative indicators
  value_unit text,                                           -- 'tCO2e', 'kL', 'INR_crore', '%'
  value_text text,                                           -- for narrative indicators
  value_table jsonb,                                         -- for tabular indicators
  prior_year_value numeric,                                  -- BRSR requires PY restatement
  prior_year_unit text,
  computation_source jsonb,                                  -- which brsr_core_kpis / brsr_entries fed this
  evidence_document_id uuid references public.documents(id), -- supporting PDF / Excel / cert
  evidence_page int,
  notes text,
  created_by uuid references public.profiles(id),
  updated_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(org_id, fiscal_period_id, indicator_code)
);

create index if not exists brsr_disclosures_org_idx on public.brsr_disclosures(org_id);
create index if not exists brsr_disclosures_period_idx on public.brsr_disclosures(fiscal_period_id);
create index if not exists brsr_disclosures_principle_idx on public.brsr_disclosures(principle)
  where principle is not null;

alter table public.brsr_disclosures enable row level security;

create policy "Org members can view disclosures"
  on public.brsr_disclosures for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create policy "Org members can manage disclosures"
  on public.brsr_disclosures for all
  using (org_id in (select org_id from public.org_members
                     where user_id = auth.uid() and role in ('owner','admin','member')));

-- ============================================================
-- 4. BRSR_CORE_KPIS — the 9 SEBI-assured KPIs
-- ============================================================
-- These are the indicators SEBI mandates third-party assurance on. Treated
-- as first-class rows so we can enforce the assurance_evidence_id NOT NULL
-- constraint before allowing submission.

create table if not exists public.brsr_core_kpis (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  fiscal_period_id uuid references public.fiscal_periods(id) on delete cascade not null,
  kpi_code text not null
    check (kpi_code in (
      'ghg_intensity_per_crore_turnover',      -- tCO2e / INR Cr
      'water_intensity_per_crore_turnover',    -- kL / INR Cr
      'energy_intensity_per_crore_turnover',   -- GJ / INR Cr
      'wages_complaints_resolved_pct',         -- %
      'gender_diversity_workforce_pct',        -- %
      'gender_diversity_board_pct',            -- %
      'training_coverage_pct',                 -- %
      'directors_renumeration_to_median_ratio',
      'csr_spend_pct_of_pat'                   -- %
    )),
  value numeric not null,
  unit text not null,
  numerator numeric,                                         -- show our work
  denominator numeric,
  computation_method text,                                   -- 'GHG Protocol Scope 1+2', etc.
  assurance_evidence_id uuid references public.documents(id),
  assurance_provider text,                                   -- 'Deloitte', 'BSI', etc.
  assurance_type text check (assurance_type in ('reasonable', 'limited', 'none')),
  assured_at date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(org_id, fiscal_period_id, kpi_code)
);

create index if not exists brsr_core_kpis_org_idx on public.brsr_core_kpis(org_id);

alter table public.brsr_core_kpis enable row level security;

create policy "Org members can view core KPIs"
  on public.brsr_core_kpis for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create policy "Org members can manage core KPIs"
  on public.brsr_core_kpis for all
  using (org_id in (select org_id from public.org_members
                     where user_id = auth.uid() and role in ('owner','admin','member')));

-- ============================================================
-- 5. CSR_ACTIVITIES — Companies Act §135 2% mandate tracking
-- ============================================================

create table if not exists public.csr_committee_meetings (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  fiscal_period_id uuid references public.fiscal_periods(id) on delete cascade not null,
  meeting_date date not null,
  agenda jsonb,
  attendees jsonb,                                           -- [{din, name, role, present}]
  minutes_document_id uuid references public.documents(id),
  created_at timestamptz not null default now()
);

alter table public.csr_committee_meetings enable row level security;
create policy "Org members manage CSR meetings"
  on public.csr_committee_meetings for all
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create table if not exists public.csr_implementing_agencies (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  name text not null,
  pan text,
  registration_type text
    check (registration_type in ('section_8', 'trust', 'society', 'self_implemented')),
  section_80g_registration_number text,                      -- required by rule
  csr_1_registration_number text,                            -- MCA Form CSR-1
  csr_1_filed_on date,
  created_at timestamptz not null default now(),
  unique(org_id, pan)
);

alter table public.csr_implementing_agencies enable row level security;
create policy "Org members manage implementing agencies"
  on public.csr_implementing_agencies for all
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create table if not exists public.csr_projects (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  fiscal_period_id uuid references public.fiscal_periods(id) on delete cascade not null,
  project_name text not null,
  schedule_vii_item text not null,                           -- '(i) eradicating hunger', etc.
  local_area boolean default false,
  state text,
  district text,
  implementing_agency_id uuid references public.csr_implementing_agencies(id),
  project_duration_months int,
  budget_paise bigint not null,                              -- INR paise
  committed_paise bigint default 0,
  disbursed_paise bigint default 0,
  ongoing boolean default true,
  unspent_account_transferred_paise bigint default 0,        -- §135(6)
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists csr_projects_org_idx on public.csr_projects(org_id);
create index if not exists csr_projects_period_idx on public.csr_projects(fiscal_period_id);

alter table public.csr_projects enable row level security;
create policy "Org members manage CSR projects"
  on public.csr_projects for all
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

create table if not exists public.csr_disbursements (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.csr_projects(id) on delete cascade not null,
  org_id uuid references public.organizations(id) on delete cascade not null,
  amount_paise bigint not null,
  disbursed_on date not null,
  mode text check (mode in ('bank_transfer', 'cheque', 'in_kind', 'other')),
  utilization_certificate_document_id uuid references public.documents(id),
  created_at timestamptz not null default now()
);

create index if not exists csr_disbursements_project_idx on public.csr_disbursements(project_id);

alter table public.csr_disbursements enable row level security;
create policy "Org members manage CSR disbursements"
  on public.csr_disbursements for all
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

-- Administrative overhead (capped at 5% per CSR Rules)
create table if not exists public.csr_administrative_overhead (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  fiscal_period_id uuid references public.fiscal_periods(id) on delete cascade not null,
  total_csr_obligation_paise bigint not null,
  admin_overhead_paise bigint not null,
  csr_2_filed_on date,                                       -- MCA Form CSR-2
  csr_2_acknowledgment text,
  created_at timestamptz not null default now(),
  unique(org_id, fiscal_period_id),
  -- 5% statutory cap on admin overhead
  check (admin_overhead_paise <= (total_csr_obligation_paise * 5 / 100))
);

alter table public.csr_administrative_overhead enable row level security;
create policy "Org members manage CSR overhead"
  on public.csr_administrative_overhead for all
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));

-- ============================================================
-- 6. DSC_SIGNATURES — Digital Signature Certificate records
-- ============================================================
-- Distinct from submission_signatures (which is our internal non-repudiation
-- record). This is the DSC actually used to sign the document delivered to
-- the regulator.

create table if not exists public.dsc_signatures (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  signer_name text not null,
  signer_pan text not null,
  signer_din text,                                           -- Director Identification Number, if director
  signer_designation text,
  dsc_class text not null check (dsc_class in ('Class_2', 'Class_3')),
  dsc_issuer text not null
    check (dsc_issuer in ('eMudhra', 'Sify', 'nCode', 'Capricorn', 'IDsign', 'other')),
  certificate_serial_number text not null,
  certificate_thumbprint text,                               -- SHA-1 hex
  valid_from timestamptz not null,
  valid_to timestamptz not null,
  signed_document_id uuid references public.documents(id),
  signed_document_hash text not null,                        -- SHA-256 of signed bytes
  signature_format text check (signature_format in ('PKCS7', 'PAdES', 'XAdES', 'CAdES')),
  time_stamp_source text,                                    -- TSA URL (e.g., CCA-RA timestamp)
  time_stamp_at timestamptz,
  signed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  check (valid_to > valid_from)
);

create index if not exists dsc_signatures_org_idx on public.dsc_signatures(org_id);
create index if not exists dsc_signatures_pan_idx on public.dsc_signatures(signer_pan);

alter table public.dsc_signatures enable row level security;
create policy "Org members view DSC signatures"
  on public.dsc_signatures for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));
create policy "Org admins insert DSC signatures"
  on public.dsc_signatures for insert
  with check (org_id in (select org_id from public.org_members
                          where user_id = auth.uid() and role in ('owner','admin')));

-- ============================================================
-- 7. REGULATOR_FILINGS — tracked submissions to SEBI/MCA21/CPCB/BEE
-- ============================================================

create table if not exists public.regulator_filings (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  fiscal_period_id uuid references public.fiscal_periods(id) on delete cascade,
  regulator text not null check (regulator in ('SEBI', 'MCA21', 'CPCB', 'BEE', 'NSE', 'BSE', 'RBI')),
  filing_type text not null,                                 -- 'BRSR', 'BRSR_Core', 'XBRL', 'CSR-2', 'PAT_M&V', etc.
  form_number text,                                          -- 'AOC-4', 'CSR-2', 'MR-3'
  submission_method text check (submission_method in ('portal_upload', 'email', 'physical', 'api')),
  submitted_document_id uuid references public.documents(id),
  submitted_at timestamptz not null,
  acknowledgment_number text,
  acknowledgment_document_id uuid references public.documents(id),
  status text not null default 'submitted'
    check (status in ('draft', 'submitted', 'under_review', 'accepted', 'rejected', 'returned_for_revision')),
  status_updated_at timestamptz,
  rejection_reason text,
  dsc_signature_id uuid references public.dsc_signatures(id),
  filing_fee_paise bigint default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists regulator_filings_org_idx on public.regulator_filings(org_id);
create index if not exists regulator_filings_status_idx on public.regulator_filings(status);
create index if not exists regulator_filings_regulator_idx on public.regulator_filings(regulator);

alter table public.regulator_filings enable row level security;
create policy "Org members view filings"
  on public.regulator_filings for select
  using (org_id in (select org_id from public.org_members where user_id = auth.uid()));
create policy "Org admins manage filings"
  on public.regulator_filings for all
  using (org_id in (select org_id from public.org_members
                     where user_id = auth.uid() and role in ('owner','admin')));

-- ============================================================
-- 8. RBI_FX_RATES — daily reference rates for MNC consolidation
-- ============================================================
-- Replaces the hard-coded FX env vars in backend/app/normalise.py. Loaded
-- daily from the RBI reference-rate API. Global (not per-org) — every
-- tenant uses the same rates.

create table if not exists public.rbi_fx_rates (
  as_of_date date not null,
  currency_code text not null,                               -- ISO 4217: 'USD', 'EUR', 'GBP'
  rate_inr numeric(18,6) not null,                           -- 1 unit of currency in INR
  source text not null default 'RBI_reference',
  fetched_at timestamptz not null default now(),
  primary key (as_of_date, currency_code),
  check (rate_inr > 0)
);

-- BRIN index is ideal here — rows are inserted in date order, table grows
-- linearly with time. Gives Timescale-like time-range scan speed without
-- the extension.
create index if not exists rbi_fx_rates_date_brin_idx
  on public.rbi_fx_rates using brin (as_of_date);

-- Read-only for all authenticated users; only service role writes.
alter table public.rbi_fx_rates enable row level security;
create policy "Any authenticated user can read FX rates"
  on public.rbi_fx_rates for select
  using (auth.role() = 'authenticated' or auth.role() = 'service_role');

-- Helper view: latest rate per currency (for quick lookup from app code)
create or replace view public.rbi_fx_rates_latest as
select distinct on (currency_code)
  currency_code, as_of_date, rate_inr, fetched_at
from public.rbi_fx_rates
order by currency_code, as_of_date desc;

-- ============================================================
-- SEED — Bharat Steel Ltd (sample tenant)
-- ============================================================
-- Demonstrates a realistic configuration: NSE-listed, BRSR Core applicable
-- from FY24-25, FY ending 31 March, Iron & Steel sector (NIC 24109).
-- Wrap in a DO block so seed is idempotent — if the org already exists, skip.

do $$
declare
  v_org_id uuid;
  v_fy24_id uuid;
  v_fy25_id uuid;
begin
  -- Skip seed entirely if CIN already present (idempotent re-runs)
  if exists (select 1 from public.organizations where cin = 'L27100MH1907PLC000260') then
    return;
  end if;

  -- The seed only runs in an environment with at least one profile, since
  -- created_by is NOT NULL. Pick the first profile as the placeholder owner.
  if not exists (select 1 from public.profiles limit 1) then
    raise notice 'Skipping Bharat Steel seed — no profiles exist yet';
    return;
  end if;

  insert into public.organizations (
    name, slug, plan, created_by,
    cin, pan, lei, gstin, sebi_scrip_code, nic_code,
    listing_status, market_cap_rank, fy_end_month,
    brsr_applicable_from_fy, brsr_core_applicable_from_fy,
    registered_address, corporate_address
  ) values (
    'Bharat Steel Ltd',
    'bharat-steel',
    'enterprise',
    (select id from public.profiles order by created_at limit 1),
    'L27100MH1907PLC000260',
    'AABCB1234D',
    '335800XYZABCDE123456',
    array['27AABCB1234D1Z5', '24AABCB1234D2Z4', '06AABCB1234D1Z9'],
    'BHARATSTEEL',
    '24109',                                                 -- mfr of basic iron & steel
    'NSE_BSE',
    47,
    3,
    'FY2022-23',                                             -- top-1000 cohort
    'FY2024-25',                                             -- top-150 cohort
    jsonb_build_object(
      'line1', 'Bombay House',
      'line2', '24, Homi Mody Street',
      'city', 'Mumbai',
      'state', 'Maharashtra',
      'pin', '400001',
      'country', 'IN'
    ),
    jsonb_build_object(
      'line1', 'Bharat Steel Plant',
      'city', 'Jamshedpur',
      'state', 'Jharkhand',
      'pin', '831001',
      'country', 'IN'
    )
  ) returning id into v_org_id;

  insert into public.fiscal_periods (org_id, fy_label, period_start, period_end, status)
  values (v_org_id, 'FY2023-24', '2023-04-01', '2024-03-31', 'submitted')
  returning id into v_fy24_id;

  insert into public.fiscal_periods (org_id, fy_label, period_start, period_end, status)
  values (v_org_id, 'FY2024-25', '2024-04-01', '2025-03-31', 'in_review')
  returning id into v_fy25_id;

  -- Seed two of the nine assured Core KPIs for FY2024-25
  insert into public.brsr_core_kpis (
    org_id, fiscal_period_id, kpi_code, value, unit,
    numerator, denominator, computation_method,
    assurance_provider, assurance_type, assured_at
  ) values
    (v_org_id, v_fy25_id, 'ghg_intensity_per_crore_turnover',
     2.41, 'tCO2e/INR_Cr', 245000, 101660, 'GHG Protocol Scope 1+2 market-based',
     'Deloitte Haskins & Sells LLP', 'reasonable', '2025-05-30'),
    (v_org_id, v_fy25_id, 'water_intensity_per_crore_turnover',
     18.7, 'kL/INR_Cr', 1901000, 101660, 'Direct withdrawal + third-party',
     'Deloitte Haskins & Sells LLP', 'reasonable', '2025-05-30');

  raise notice 'Seeded Bharat Steel Ltd (org_id=%)', v_org_id;
end $$;
