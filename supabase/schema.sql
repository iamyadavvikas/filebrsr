-- Supabase SQL Schema for FileBRSR
-- Run this in the Supabase SQL Editor

-- Profiles table (extends auth.users)
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  email text not null,
  full_name text,
  company_name text,
  plan text not null default 'free' check (plan in ('free', 'starter', 'pro', 'enterprise')),
  credits_remaining int not null default 3,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Enable RLS
alter table public.profiles enable row level security;

create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  return new;
end;
$$ language plpgsql security definer;

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Reports table
create table if not exists public.reports (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  file_name text not null,
  file_url text,
  status text not null default 'processing' check (status in ('processing', 'completed', 'failed')),
  extracted_data jsonb,
  confidence_scores jsonb,
  company_name text,
  financial_year text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.reports enable row level security;

create policy "Users can view own reports"
  on public.reports for select
  using (auth.uid() = user_id);

create policy "Users can insert own reports"
  on public.reports for insert
  with check (auth.uid() = user_id);

create policy "Users can update own reports"
  on public.reports for update
  using (auth.uid() = user_id);

-- Payments table
create table if not exists public.payments (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  razorpay_order_id text not null,
  razorpay_payment_id text,
  razorpay_signature text,
  amount int not null,
  currency text not null default 'INR',
  plan text not null,
  status text not null default 'created' check (status in ('created', 'paid', 'failed')),
  created_at timestamptz not null default now()
);

alter table public.payments enable row level security;

create policy "Users can view own payments"
  on public.payments for select
  using (auth.uid() = user_id);

-- Storage bucket for BRSR PDFs
insert into storage.buckets (id, name, public)
values ('brsr-reports', 'brsr-reports', false)
on conflict do nothing;

create policy "Users can upload own files"
  on storage.objects for insert
  with check (
    bucket_id = 'brsr-reports' and
    auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "Users can read own files"
  on storage.objects for select
  using (
    bucket_id = 'brsr-reports' and
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Updated_at trigger
create or replace function public.update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function public.update_updated_at();

create trigger reports_updated_at
  before update on public.reports
  for each row execute function public.update_updated_at();
