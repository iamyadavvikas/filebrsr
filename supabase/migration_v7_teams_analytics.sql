-- Migration V7: Team Invites + Analytics Events + Activity Log
-- Enhances multi-tenancy and adds product analytics infrastructure

-- ============================================================
-- ORG INVITES (email-based team invitations)
-- ============================================================
create table if not exists public.org_invites (
  id uuid default gen_random_uuid() primary key,
  org_id uuid references public.organizations(id) on delete cascade not null,
  invited_by uuid references public.profiles(id) on delete cascade not null,
  email text not null,
  role text not null default 'member' check (role in ('admin', 'member', 'viewer')),
  status text not null default 'pending' check (status in ('pending', 'accepted', 'expired', 'revoked')),
  token text unique not null default encode(gen_random_bytes(32), 'hex'),
  expires_at timestamptz not null default (now() + interval '7 days'),
  accepted_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.org_invites enable row level security;

create policy "Org admins can manage invites"
  on public.org_invites for all
  using (
    invited_by = auth.uid()
    or org_id in (
      select org_id from public.org_members
      where user_id = auth.uid() and role in ('owner', 'admin')
    )
  );

create policy "Invited users can view own invites"
  on public.org_invites for select
  using (
    email in (select email from public.profiles where id = auth.uid())
  );

create index if not exists idx_org_invites_email on public.org_invites(email, status);
create index if not exists idx_org_invites_token on public.org_invites(token);
create index if not exists idx_org_invites_org on public.org_invites(org_id, status);

-- ============================================================
-- ANALYTICS EVENTS (product usage tracking)
-- ============================================================
create table if not exists public.analytics_events (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete set null,
  org_id uuid references public.organizations(id) on delete set null,
  event_name text not null, -- 'page_view', 'extraction_started', 'data_entry_saved', etc.
  event_category text not null check (event_category in ('auth', 'extraction', 'data_entry', 'report', 'billing', 'navigation', 'team', 'export')),
  properties jsonb default '{}', -- event-specific data
  session_id text, -- browser session tracking
  page_path text,
  referrer text,
  user_agent text,
  created_at timestamptz not null default now()
);

-- No RLS on analytics — only backend writes via service key
alter table public.analytics_events enable row level security;

create policy "Service role can insert analytics"
  on public.analytics_events for insert
  with check (true);

create policy "Service role can read analytics"
  on public.analytics_events for select
  using (true);

create index if not exists idx_analytics_events_name on public.analytics_events(event_name, created_at desc);
create index if not exists idx_analytics_events_user on public.analytics_events(user_id, created_at desc);
create index if not exists idx_analytics_events_category on public.analytics_events(event_category, created_at desc);

-- ============================================================
-- DAILY METRICS (materialized daily rollups for dashboard)
-- ============================================================
create table if not exists public.daily_metrics (
  id uuid default gen_random_uuid() primary key,
  date date not null unique,
  total_users int default 0,
  new_signups int default 0,
  active_users int default 0, -- users who did any action
  extractions_started int default 0,
  extractions_completed int default 0,
  data_entries_saved int default 0,
  reports_generated int default 0,
  paid_conversions int default 0,
  revenue_inr decimal(12,2) default 0,
  created_at timestamptz not null default now()
);

alter table public.daily_metrics enable row level security;

create policy "Service role can manage metrics"
  on public.daily_metrics for all
  using (true);

-- ============================================================
-- ENHANCE ORG_MEMBERS (add more useful columns)
-- ============================================================
alter table public.org_members add column if not exists department text;
alter table public.org_members add column if not exists title text;
alter table public.org_members add column if not exists last_active_at timestamptz;
alter table public.org_members add column if not exists status text default 'active' check (status in ('active', 'inactive', 'suspended'));

-- ============================================================
-- AUTO-CREATE ORG ON FIRST COMPANY SAVE
-- ============================================================
create or replace function public.auto_create_org_on_company_update()
returns trigger as $$
begin
  -- If user sets company_name and doesn't have an org yet, create one
  if new.company_name is not null and new.company_name != '' and new.org_id is null then
    declare
      new_org_id uuid;
      org_slug text;
    begin
      -- Generate slug from company name
      org_slug := lower(regexp_replace(new.company_name, '[^a-zA-Z0-9]', '-', 'g'));
      org_slug := regexp_replace(org_slug, '-+', '-', 'g');
      org_slug := trim(both '-' from org_slug);
      -- Add random suffix to avoid collisions
      org_slug := org_slug || '-' || substr(encode(gen_random_bytes(4), 'hex'), 1, 6);

      insert into public.organizations (name, slug, created_by)
      values (new.company_name, org_slug, new.id)
      returning id into new_org_id;

      -- Add user as owner
      insert into public.org_members (org_id, user_id, role, joined_at)
      values (new_org_id, new.id, 'owner', now());

      -- Set org_id on profile
      new.org_id := new_org_id;
    end;
  end if;
  return new;
end;
$$ language plpgsql security definer;

-- Drop trigger if exists, then recreate
drop trigger if exists auto_create_org on public.profiles;
create trigger auto_create_org
  before update on public.profiles
  for each row execute function public.auto_create_org_on_company_update();

-- ============================================================
-- HELPER VIEW: org dashboard (for team overview)
-- ============================================================
create or replace view public.org_team_view as
select
  om.org_id,
  om.user_id,
  om.role,
  om.department,
  om.title,
  om.joined_at,
  om.last_active_at,
  om.status,
  p.email,
  p.full_name,
  o.name as org_name,
  o.plan as org_plan
from public.org_members om
join public.profiles p on p.id = om.user_id
join public.organizations o on o.id = om.org_id;
