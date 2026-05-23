-- Migration V3: Full Platform - Greenomy-equivalent for Indian ESG Compliance
-- Run AFTER migration_v2.sql

-- ============================================================
-- BRSR DATA ENTRIES (Manual data collection hub)
-- ============================================================
create table if not exists public.brsr_entries (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  financial_year text not null, -- e.g., 'FY2024-25'
  section text not null check (section in ('section_a', 'section_b', 'section_c')),
  subsection text not null, -- e.g., 'details_of_entity', 'products_services', etc.
  datapoint_id text not null, -- references BRSR_DATAPOINTS id like 'A.I.1'
  value jsonb not null, -- flexible: can be text, number, table, etc.
  source text check (source in ('manual', 'ai_extracted', 'imported', 'calculated')),
  source_document text, -- reference to uploaded file
  confidence_score decimal(3,2), -- 0.00 to 1.00
  notes text,
  verified boolean default false,
  verified_by uuid references public.profiles(id),
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(org_id, user_id, financial_year, datapoint_id)
);

alter table public.brsr_entries enable row level security;

create policy "Users can manage own entries"
  on public.brsr_entries for all
  using (auth.uid() = user_id);

create policy "Org members can view org entries"
  on public.brsr_entries for select
  using (
    org_id in (select org_id from public.org_members where user_id = auth.uid())
  );

-- ============================================================
-- CARBON DATA (Scope 1, 2, 3 emissions tracking)
-- ============================================================
create table if not exists public.carbon_entries (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  financial_year text not null,
  scope text not null check (scope in ('scope_1', 'scope_2', 'scope_3')),
  category text not null, -- e.g., 'stationary_combustion', 'mobile_combustion', 'purchased_electricity', etc.
  subcategory text, -- further breakdown
  activity_data decimal(15,4), -- amount of activity (e.g., liters diesel, kWh)
  activity_unit text, -- unit of measurement
  emission_factor decimal(12,6), -- tCO2e per unit
  emission_factor_source text, -- e.g., 'CEA 2024', 'IPCC AR6', 'GHG Protocol'
  total_emissions decimal(15,4), -- tCO2e (calculated)
  uncertainty_percent decimal(5,2),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.carbon_entries enable row level security;

create policy "Users can manage own carbon data"
  on public.carbon_entries for all
  using (auth.uid() = user_id);

-- ============================================================
-- ACTION PLANS (AI-generated improvement roadmap)
-- ============================================================
create table if not exists public.action_plans (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  financial_year text not null,
  report_id uuid references public.reports(id),
  title text not null,
  description text,
  category text not null check (category in ('environment', 'social', 'governance', 'general')),
  priority text not null check (priority in ('critical', 'high', 'medium', 'low')),
  effort text check (effort in ('quick_win', 'short_term', 'medium_term', 'long_term')),
  estimated_cost_inr decimal(15,2),
  impact_score int check (impact_score between 1 and 10), -- 1-10 impact rating
  principle text, -- NGRBC principle P1-P9
  datapoint_ids text[], -- which BRSR datapoints this addresses
  status text not null default 'proposed' check (status in ('proposed', 'approved', 'in_progress', 'completed', 'deferred')),
  due_date date,
  assigned_to uuid references public.profiles(id),
  completion_notes text,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.action_plans enable row level security;

create policy "Users can manage own action plans"
  on public.action_plans for all
  using (auth.uid() = user_id);

-- ============================================================
-- COMPLIANCE CALENDAR
-- ============================================================
create table if not exists public.compliance_events (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  title text not null,
  description text,
  event_type text not null check (event_type in ('filing_deadline', 'audit', 'board_review', 'data_collection', 'custom')),
  regulatory_body text, -- 'SEBI', 'BSE', 'NSE', 'MCA', etc.
  due_date date not null,
  reminder_days int[] default '{30, 7, 1}', -- days before to remind
  status text not null default 'upcoming' check (status in ('upcoming', 'in_progress', 'completed', 'overdue', 'skipped')),
  financial_year text,
  recurring boolean default false,
  recurring_pattern text, -- 'annual', 'quarterly', 'monthly'
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.compliance_events enable row level security;

create policy "Users can manage own calendar"
  on public.compliance_events for all
  using (auth.uid() = user_id);

-- ============================================================
-- GENERATED REPORTS (BRSR format reports)
-- ============================================================
create table if not exists public.generated_reports (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  financial_year text not null,
  report_type text not null check (report_type in ('brsr_full', 'brsr_core', 'brsr_lite', 'gap_analysis', 'action_plan', 'carbon_report')),
  title text not null,
  content jsonb, -- structured report content
  file_url text, -- stored PDF/DOCX URL
  format text check (format in ('pdf', 'docx', 'xlsx', 'xbrl')),
  version int not null default 1,
  status text not null default 'draft' check (status in ('draft', 'review', 'approved', 'filed')),
  approved_by uuid references public.profiles(id),
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.generated_reports enable row level security;

create policy "Users can manage own generated reports"
  on public.generated_reports for all
  using (auth.uid() = user_id);

-- ============================================================
-- MATERIALITY ASSESSMENT
-- ============================================================
create table if not exists public.materiality_topics (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references public.profiles(id) on delete cascade not null,
  financial_year text not null,
  topic text not null, -- e.g., 'Climate Change', 'Water Management', 'Human Rights'
  category text not null check (category in ('environmental', 'social', 'governance')),
  impact_significance decimal(3,2), -- 0-1 scale (impact materiality)
  financial_significance decimal(3,2), -- 0-1 scale (financial materiality)
  stakeholder_relevance decimal(3,2), -- 0-1 relevance to stakeholders
  brsr_principles text[], -- which NGRBC principles this maps to
  description text,
  risks text,
  opportunities text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.materiality_topics enable row level security;

create policy "Users can manage own materiality"
  on public.materiality_topics for all
  using (auth.uid() = user_id);

-- ============================================================
-- AUDIT TRAIL (full data lineage)
-- ============================================================
create table if not exists public.audit_trail (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id),
  user_id uuid references public.profiles(id) not null,
  entity_type text not null, -- 'brsr_entry', 'carbon_entry', 'action_plan', etc.
  entity_id uuid not null,
  action text not null check (action in ('create', 'update', 'delete', 'verify', 'approve', 'export')),
  old_value jsonb,
  new_value jsonb,
  ip_address inet,
  user_agent text,
  created_at timestamptz not null default now()
);

alter table public.audit_trail enable row level security;

create policy "Users can view own audit trail"
  on public.audit_trail for select
  using (auth.uid() = user_id);

-- ============================================================
-- INDEXES for performance
-- ============================================================
create index if not exists idx_brsr_entries_fy on public.brsr_entries(financial_year);
create index if not exists idx_brsr_entries_user on public.brsr_entries(user_id);
create index if not exists idx_brsr_entries_org_fy on public.brsr_entries(org_id, financial_year);
create index if not exists idx_brsr_entries_datapoint on public.brsr_entries(datapoint_id);
create index if not exists idx_carbon_entries_fy on public.carbon_entries(financial_year, scope);
create index if not exists idx_action_plans_status on public.action_plans(status, priority);
create index if not exists idx_compliance_events_due on public.compliance_events(due_date, status);
create index if not exists idx_audit_trail_entity on public.audit_trail(entity_type, entity_id);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-update updated_at timestamp
create or replace function public.update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Apply to all new tables
create trigger update_brsr_entries_updated_at before update on public.brsr_entries for each row execute function public.update_updated_at();
create trigger update_carbon_entries_updated_at before update on public.carbon_entries for each row execute function public.update_updated_at();
create trigger update_action_plans_updated_at before update on public.action_plans for each row execute function public.update_updated_at();
create trigger update_compliance_events_updated_at before update on public.compliance_events for each row execute function public.update_updated_at();
create trigger update_generated_reports_updated_at before update on public.generated_reports for each row execute function public.update_updated_at();
create trigger update_materiality_topics_updated_at before update on public.materiality_topics for each row execute function public.update_updated_at();

-- Calculate completion percentage for a financial year
create or replace function public.get_brsr_completion(p_user_id uuid, p_financial_year text)
returns json as $$
declare
  total_mandatory int;
  filled_mandatory int;
  total_core int;
  filled_core int;
begin
  -- Count from actual entries
  select count(*) into filled_mandatory
  from public.brsr_entries
  where user_id = p_user_id and financial_year = p_financial_year;
  
  -- Total mandatory datapoints (hardcoded based on BRSR framework)
  total_mandatory := 216;
  total_core := 78;
  
  select count(*) into filled_core
  from public.brsr_entries
  where user_id = p_user_id 
    and financial_year = p_financial_year
    and datapoint_id like any(array['A.I%', 'A.II%', 'B.%', 'C.P1%', 'C.P2%', 'C.P3%']);
    
  return json_build_object(
    'total_mandatory', total_mandatory,
    'filled_mandatory', filled_mandatory,
    'completion_percent', round((filled_mandatory::decimal / total_mandatory) * 100, 1),
    'total_core', total_core,
    'filled_core', filled_core,
    'core_completion_percent', round((filled_core::decimal / total_core) * 100, 1)
  );
end;
$$ language plpgsql security definer;
