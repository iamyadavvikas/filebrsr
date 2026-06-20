-- Migration V19: onboarding completion flag for profiles
-- ==========================================================================
-- Wires up the existing OnboardingWizard (frontend/src/app/platform/
-- OnboardingWizard.tsx). The wizard collects `sector` + `reporting_category`
-- (already added in migration_v5_settings.sql) and now records that the
-- first-run flow has been completed so it is shown exactly once per user.
--
--   onboarding_completed  boolean gate. FALSE => the platform overview renders
--                         the onboarding wizard modal on first login. The
--                         wizard sets it TRUE once the user picks sector +
--                         reporting category. Defaults FALSE so existing rows
--                         see the wizard once (they can dismiss via Settings).
--
-- Idempotent (ADD COLUMN IF NOT EXISTS). Run AFTER migration_v5_settings.sql.
-- ==========================================================================

alter table public.profiles
  add column if not exists onboarding_completed boolean not null default false;

comment on column public.profiles.onboarding_completed is
  'When false, the first-run OnboardingWizard is shown on the platform overview. Set true once the user completes sector + reporting-category setup.';
