-- Migration v20: Self-serve billing support
-- Adds subscription tracking columns to profiles so individual users can view
-- and cancel their Razorpay subscription from Settings (no email-to-support needed).
-- Idempotent. Safe to run after migration_v2.sql / schema.sql.

alter table public.profiles
  add column if not exists subscription_id text;

alter table public.profiles
  add column if not exists subscription_status text
    default 'inactive'
    check (subscription_status in ('inactive', 'active', 'paused', 'cancelled', 'expired'));

comment on column public.profiles.subscription_id is
  'Razorpay subscription id for the user-level plan (set by billing webhook on activation).';
comment on column public.profiles.subscription_status is
  'Lifecycle status of the user-level Razorpay subscription.';
