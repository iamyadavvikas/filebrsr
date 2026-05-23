-- Migration V4: Advanced Platform Features
-- Supply Chain, Document Library, Workflows, Multi-framework, XBRL, Regulatory

-- ============================================================
-- SUPPLY CHAIN ESG (Vendor/Supplier assessments)
-- ============================================================
create table if not exists public.suppliers (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  category text check (category in ('tier_1', 'tier_2', 'tier_3', 'service_provider')),
  industry text,
  location_state text,
  location_country text default 'India',
  annual_spend_inr decimal(15,2),
  contact_name text,
  contact_email text,
  esg_score decimal(4,2), -- 0-100
  risk_level text check (risk_level in ('low', 'medium', 'high', 'critical')),
  last_assessed_at timestamptz,
  status text default 'active' check (status in ('active', 'inactive', 'blacklisted', 'pending_assessment')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.supplier_assessments (
  id uuid default gen_random_uuid() primary key,
  supplier_id uuid references public.suppliers(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  financial_year text not null,
  assessment_type text check (assessment_type in ('self_declaration', 'audit', 'questionnaire', 'document_review')),
  environment_score decimal(4,2),
  social_score decimal(4,2),
  governance_score decimal(4,2),
  overall_score decimal(4,2),
  responses jsonb, -- questionnaire answers
  findings text,
  corrective_actions text,
  assessed_at timestamptz default now(),
  created_at timestamptz not null default now()
);

alter table public.suppliers enable row level security;
alter table public.supplier_assessments enable row level security;

create policy "Users can manage own suppliers" on public.suppliers for all using (auth.uid() = user_id);
create policy "Users can manage own assessments" on public.supplier_assessments for all using (auth.uid() = user_id);

-- ============================================================
-- DOCUMENT EVIDENCE LIBRARY
-- ============================================================
create table if not exists public.documents (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  file_name text not null,
  file_url text not null,
  file_size_bytes bigint,
  mime_type text,
  category text check (category in ('policy', 'certificate', 'audit_report', 'data_source', 'board_resolution', 'photograph', 'other')),
  description text,
  financial_year text,
  linked_datapoints text[], -- BRSR datapoint IDs this supports
  linked_principles text[], -- P1-P9
  tags text[],
  uploaded_at timestamptz default now(),
  verified boolean default false,
  verified_by uuid references public.profiles(id),
  verified_at timestamptz,
  expiry_date date, -- for certificates
  created_at timestamptz not null default now()
);

alter table public.documents enable row level security;
create policy "Users can manage own documents" on public.documents for all using (auth.uid() = user_id);

-- ============================================================
-- WORKFLOW APPROVALS (Maker-Checker)
-- ============================================================
create table if not exists public.workflow_templates (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  entity_type text not null, -- 'brsr_entry', 'report', 'action_plan', 'carbon_entry'
  steps jsonb not null, -- [{role: 'reviewer', approver_id: uuid}, {role: 'approver', approver_id: uuid}]
  is_active boolean default true,
  created_at timestamptz not null default now()
);

create table if not exists public.workflow_instances (
  id uuid default gen_random_uuid() primary key,
  template_id uuid references public.workflow_templates(id),
  entity_type text not null,
  entity_id uuid not null,
  initiated_by uuid references public.profiles(id) not null,
  current_step int default 0,
  status text default 'pending' check (status in ('pending', 'in_review', 'approved', 'rejected', 'cancelled')),
  comments jsonb default '[]', -- [{user_id, comment, timestamp, action}]
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.workflow_templates enable row level security;
alter table public.workflow_instances enable row level security;
create policy "Users can manage own workflows" on public.workflow_templates for all using (auth.uid() = user_id);
create policy "Users can view own workflow instances" on public.workflow_instances for all using (auth.uid() = initiated_by);

-- ============================================================
-- MULTI-FRAMEWORK MAPPING (GRI, CDP, TCFD, SASB)
-- ============================================================
create table if not exists public.framework_mappings (
  id uuid default gen_random_uuid() primary key,
  brsr_datapoint_id text not null, -- e.g., 'C.P6.GHG.1'
  framework text not null check (framework in ('gri', 'cdp', 'tcfd', 'sasb', 'ungc', 'sdg')),
  framework_reference text not null, -- e.g., 'GRI 305-1', 'CDP C6.1'
  framework_description text,
  mapping_notes text,
  created_at timestamptz not null default now()
);

-- Pre-populate key mappings
insert into public.framework_mappings (brsr_datapoint_id, framework, framework_reference, framework_description) values
-- GHG Emissions
('C.P6.GHG.1', 'gri', 'GRI 305-1', 'Direct (Scope 1) GHG emissions'),
('C.P6.GHG.2', 'gri', 'GRI 305-2', 'Energy indirect (Scope 2) GHG emissions'),
('C.P6.GHG.3', 'gri', 'GRI 305-3', 'Other indirect (Scope 3) GHG emissions'),
('C.P6.GHG.1', 'cdp', 'C6.1', 'Gross global Scope 1 emissions'),
('C.P6.GHG.2', 'cdp', 'C6.3', 'Gross global Scope 2 emissions'),
('C.P6.GHG.1', 'tcfd', 'Metrics-a', 'Scope 1, 2, 3 GHG emissions'),
('C.P6.GHG.1', 'sasb', 'IF-EU-110a.1', 'Gross global Scope 1 emissions'),
-- Energy
('C.P6.Energy.1', 'gri', 'GRI 302-1', 'Energy consumption within the organization'),
('C.P6.Energy.1', 'cdp', 'C8.2a', 'Total energy consumption'),
('C.P6.Energy.2', 'gri', 'GRI 302-3', 'Energy intensity'),
-- Water
('C.P6.Water.1', 'gri', 'GRI 303-3', 'Water withdrawal'),
('C.P6.Water.1', 'cdp', 'W1.2b', 'Total water withdrawals'),
-- Waste
('C.P6.Waste.1', 'gri', 'GRI 306-3', 'Waste generated'),
-- Employment
('C.P3.Emp.1', 'gri', 'GRI 401-1', 'New employee hires and turnover'),
('C.P3.Safety.1', 'gri', 'GRI 403-9', 'Work-related injuries'),
('C.P3.Training.1', 'gri', 'GRI 404-1', 'Average hours of training per year'),
-- Diversity
('C.P3.Diversity.1', 'gri', 'GRI 405-1', 'Diversity of governance bodies and employees'),
-- Human Rights
('C.P5.HR.1', 'gri', 'GRI 412-1', 'Operations subject to human rights reviews'),
('C.P5.HR.1', 'ungc', 'Principle 1', 'Support and respect human rights'),
-- Anti-corruption
('C.P1.Ethics.1', 'gri', 'GRI 205-2', 'Communication and training on anti-corruption'),
('C.P1.Ethics.1', 'ungc', 'Principle 10', 'Work against corruption'),
-- SDG Mapping
('C.P6.GHG.1', 'sdg', 'SDG 13', 'Climate Action'),
('C.P6.Energy.1', 'sdg', 'SDG 7', 'Affordable and Clean Energy'),
('C.P6.Water.1', 'sdg', 'SDG 6', 'Clean Water and Sanitation'),
('C.P3.Emp.1', 'sdg', 'SDG 8', 'Decent Work and Economic Growth'),
('C.P4.Stakeholder.1', 'sdg', 'SDG 17', 'Partnerships for the Goals'),
('C.P8.CSR.1', 'sdg', 'SDG 1', 'No Poverty')
on conflict do nothing;

-- ============================================================
-- XBRL FILING DATA
-- ============================================================
create table if not exists public.xbrl_filings (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  financial_year text not null,
  filing_type text check (filing_type in ('brsr_annual', 'brsr_core_quarterly', 'csr_form2')),
  exchange text check (exchange in ('bse', 'nse', 'both')),
  xbrl_content text, -- generated XBRL XML
  validation_status text check (validation_status in ('draft', 'validated', 'errors', 'filed')),
  validation_errors jsonb,
  filed_at timestamptz,
  filing_reference text, -- exchange acknowledgment number
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.xbrl_filings enable row level security;
create policy "Users can manage own filings" on public.xbrl_filings for all using (auth.uid() = user_id);

-- ============================================================
-- REGULATORY COMPLIANCE TRACKER
-- ============================================================
create table if not exists public.regulatory_compliance (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  regulation text not null check (regulation in ('pat_scheme', 'epr', 'posh', 'lodr', 'companies_act_135', 'factories_act', 'water_act', 'air_act', 'env_clearance')),
  financial_year text not null,
  status text default 'not_started' check (status in ('not_started', 'in_progress', 'compliant', 'non_compliant', 'not_applicable')),
  compliance_data jsonb, -- regulation-specific structured data
  due_date date,
  filed_date date,
  filing_reference text,
  documents uuid[], -- references to documents table
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.regulatory_compliance enable row level security;
create policy "Users can manage own compliance" on public.regulatory_compliance for all using (auth.uid() = user_id);

-- ============================================================
-- ESG RATING READINESS
-- ============================================================
create table if not exists public.esg_ratings (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  agency text not null check (agency in ('crisil', 'icra', 'sp_global', 'sustainalytics', 'msci', 'cdp')),
  financial_year text not null,
  current_rating text,
  target_rating text,
  readiness_score decimal(4,2), -- 0-100
  gap_areas jsonb, -- [{area, current_status, required_status, action}]
  last_assessed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.esg_ratings enable row level security;
create policy "Users can manage own ratings" on public.esg_ratings for all using (auth.uid() = user_id);

-- ============================================================
-- STAKEHOLDER ENGAGEMENT
-- ============================================================
create table if not exists public.stakeholder_surveys (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  title text not null,
  stakeholder_type text check (stakeholder_type in ('employee', 'investor', 'community', 'supplier', 'customer', 'regulator')),
  questions jsonb not null, -- [{id, question, type: 'rating'|'text'|'mcq', options}]
  responses_count int default 0,
  responses_data jsonb, -- aggregated responses
  status text default 'draft' check (status in ('draft', 'active', 'closed', 'archived')),
  share_link text,
  closes_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.stakeholder_surveys enable row level security;
create policy "Users can manage own surveys" on public.stakeholder_surveys for all using (auth.uid() = user_id);

-- ============================================================
-- INDEXES
-- ============================================================
create index if not exists idx_suppliers_org on public.suppliers(org_id, risk_level);
create index if not exists idx_documents_datapoints on public.documents using gin(linked_datapoints);
create index if not exists idx_framework_mappings_brsr on public.framework_mappings(brsr_datapoint_id);
create index if not exists idx_framework_mappings_fw on public.framework_mappings(framework);
create index if not exists idx_regulatory_compliance_reg on public.regulatory_compliance(regulation, financial_year);
create index if not exists idx_workflow_instances_status on public.workflow_instances(status, entity_type);

-- Apply updated_at triggers
create trigger update_suppliers_updated_at before update on public.suppliers for each row execute function public.update_updated_at();
create trigger update_workflow_instances_updated_at before update on public.workflow_instances for each row execute function public.update_updated_at();
create trigger update_xbrl_filings_updated_at before update on public.xbrl_filings for each row execute function public.update_updated_at();
create trigger update_regulatory_compliance_updated_at before update on public.regulatory_compliance for each row execute function public.update_updated_at();
create trigger update_esg_ratings_updated_at before update on public.esg_ratings for each row execute function public.update_updated_at();
