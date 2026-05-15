-- Migration: Multi-tenant orgs + Razorpay subscriptions
-- Run this AFTER the base schema.sql

-- ============================================================
-- ORGANIZATIONS (multi-tenant support for consultants)
-- ============================================================
create table if not exists public.organizations (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  slug text unique not null,
  plan text not null default 'starter' check (plan in ('starter', 'professional', 'enterprise')),
  max_reports_per_month int not null default 5,
  subscription_id text, -- Razorpay subscription ID
  subscription_status text default 'inactive' check (subscription_status in ('inactive', 'active', 'paused', 'cancelled', 'expired')),
  billing_cycle_start timestamptz,
  reports_this_cycle int not null default 0,
  created_by uuid references public.profiles(id) not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.organizations enable row level security;

-- Org members table
create table if not exists public.org_members (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  role text not null default 'member' check (role in ('owner', 'admin', 'member', 'viewer')),
  invited_at timestamptz not null default now(),
  joined_at timestamptz,
  unique(org_id, user_id)
);

alter table public.org_members enable row level security;

-- Add org_id to profiles and reports
alter table public.profiles add column if not exists org_id uuid references public.organizations(id);
alter table public.reports add column if not exists org_id uuid references public.organizations(id);
alter table public.reports add column if not exists benchmark_data jsonb;
alter table public.reports add column if not exists sector text;

-- ============================================================
-- SUBSCRIPTIONS (Razorpay recurring billing)
-- ============================================================
create table if not exists public.subscriptions (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade,
  org_id uuid references public.organizations(id) on delete cascade,
  razorpay_subscription_id text unique not null,
  razorpay_plan_id text not null,
  plan text not null check (plan in ('starter', 'professional', 'enterprise', 'pay_per_report')),
  status text not null default 'created' check (status in ('created', 'authenticated', 'active', 'paused', 'pending', 'halted', 'cancelled', 'completed', 'expired')),
  amount int not null, -- in paise
  currency text not null default 'INR',
  billing_period text not null default 'yearly' check (billing_period in ('monthly', 'yearly')),
  current_start timestamptz,
  current_end timestamptz,
  total_count int, -- total billing cycles
  paid_count int default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.subscriptions enable row level security;

-- ============================================================
-- USAGE METERING
-- ============================================================
create table if not exists public.usage_events (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) not null,
  org_id uuid references public.organizations(id),
  event_type text not null check (event_type in ('extraction', 'pdf_report', 'benchmark_compare', 'api_call')),
  report_id uuid references public.reports(id),
  metadata jsonb,
  created_at timestamptz not null default now()
);

alter table public.usage_events enable row level security;

-- ============================================================
-- RLS POLICIES
-- ============================================================

-- Organizations: members can view their org
create policy "Org members can view their org"
  on public.organizations for select
  using (
    id in (select org_id from public.org_members where user_id = auth.uid())
  );

create policy "Owners can update their org"
  on public.organizations for update
  using (
    id in (select org_id from public.org_members where user_id = auth.uid() and role in ('owner', 'admin'))
  );

-- Org members: members can view their org's members
create policy "Members can view org members"
  on public.org_members for select
  using (
    org_id in (select org_id from public.org_members where user_id = auth.uid())
  );

create policy "Admins can manage org members"
  on public.org_members for all
  using (
    org_id in (select org_id from public.org_members where user_id = auth.uid() and role in ('owner', 'admin'))
  );

-- Reports: org members can view org reports
create policy "Org members can view org reports"
  on public.reports for select
  using (
    org_id in (select org_id from public.org_members where user_id = auth.uid())
  );

-- Subscriptions: users/orgs can view their own
create policy "Users can view own subscriptions"
  on public.subscriptions for select
  using (auth.uid() = user_id);

-- Usage events: users can view their own
create policy "Users can view own usage"
  on public.usage_events for select
  using (auth.uid() = user_id);

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

-- Check if user can extract (has credits or active subscription)
create or replace function public.can_extract(p_user_id uuid)
returns boolean as $$
declare
  v_credits int;
  v_active_sub boolean;
begin
  select credits_remaining into v_credits from public.profiles where id = p_user_id;
  if v_credits > 0 then return true; end if;
  
  select exists(
    select 1 from public.subscriptions 
    where (user_id = p_user_id or org_id in (select org_id from public.org_members where user_id = p_user_id))
    and status = 'active'
  ) into v_active_sub;
  
  return v_active_sub;
end;
$$ language plpgsql security definer;

-- Decrement credits after extraction
create or replace function public.use_credit(p_user_id uuid)
returns void as $$
begin
  update public.profiles
  set credits_remaining = greatest(credits_remaining - 1, 0)
  where id = p_user_id;
end;
$$ language plpgsql security definer;

-- Triggers
create trigger organizations_updated_at
  before update on public.organizations
  for each row execute function public.update_updated_at();

create trigger subscriptions_updated_at
  before update on public.subscriptions
  for each row execute function public.update_updated_at();
