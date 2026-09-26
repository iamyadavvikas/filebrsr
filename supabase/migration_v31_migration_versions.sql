-- Migration V31: migration runner ledger
-- ==========================================================================
-- Records which supabase/migration_*.sql files have been applied, their
-- content checksum (drift detection) and order (monotonic version cursor).
-- Written by scripts/migrate.sh; the table itself must exist before the
-- runner's ledger works, so bootstrap the schema via migrate.sh once.
--
--   ./scripts/migrate.sh record   # one-time: stamp already-applied files
--   ./scripts/migrate.sh apply    # CI: apply new files before deploy
--
-- Manual dashboard pasting can stop once this is live.

create schema if not exists supabase_migrations;

create table if not exists supabase_migrations.versions (
  version    integer     not null,
  filename   text        not null,
  checksum   text        not null,
  applied_at timestamptz not null default now(),
  primary key (version, filename)
);