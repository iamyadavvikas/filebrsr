-- Migration V5: Add organization settings columns to profiles
-- These support the Settings page (sector, CIN, listing, BRSR config)

alter table public.profiles add column if not exists cin text;
alter table public.profiles add column if not exists sector text;
alter table public.profiles add column if not exists listed_on text default 'BSE + NSE';
alter table public.profiles add column if not exists reporting_category text default 'Top 1000 (BRSR Full)';
alter table public.profiles add column if not exists default_financial_year text default 'FY2024-25';
alter table public.profiles add column if not exists assurance_provider text;
