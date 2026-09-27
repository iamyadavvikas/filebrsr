#!/usr/bin/env bash
# Migration gate: prove every Supabase migration applies cleanly, in order,
# on a fresh database. Used by CI (postgres service) and locally via Docker.
#
# Usage:
#   ./scripts/migrate-check.sh            # spins up pgvector/pgvector:pg15 locally
#   PGHOST=... PGUSER=... PGPASSWORD=... PGDATABASE=... ./scripts/migrate-check.sh --no-docker
#
# Exit nonzero on the first failing statement (psql ON_ERROR_STOP=1).
set -euo pipefail

IMAGE="${PG_IMAGE:-pgvector/pgvector:pg15}"
CONTAINER="${PG_CONTAINER:-filebrsr-migrate-check}"
DB="${PGDATABASE:-filebrsr_migrate_check}"
USER="${PGUSER:-postgres}"
PASS="${PGPASSWORD:-postgres}"
PORT="${PGPORT:-55433}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUPA="$ROOT/supabase"

# Canonical application order (README "Database" + numeric tail).
ORDER=(
  schema.sql
  migration_v2.sql
  migration_v3_plan_tiers.sql
  migration_v3_platform.sql
  migration_v3_rls_admin.sql
  migration_v4_advanced.sql
  migration_v5_settings.sql
  migration_v6_fix_entries.sql
  migration_v7_teams_analytics.sql
  migration_v8_moat.sql
  migration_v9_gtm.sql
  migration_v10_extraction_corrections.sql
  migration_v11_india_compliance.sql
  migration_v12_chunks_pgvector.sql
  migration_v13_raw_records.sql
  migration_v14_tally_extras.sql
  migration_v15_tenancy.sql
  migration_v16_provenance.sql
  migration_v17_merkle_ledger.sql
  migration_v18_jurisdiction.sql
  migration_v19_onboarding.sql
  migration_v20_self_serve_billing.sql
  migration_v21_api_keys.sql
  migration_v22_carbon_assurance.sql
  migration_v23_esrs.sql
  migration_v24_esrs_profiles.sql
  migration_v25_esrs_filing.sql
  migration_v26_esrs_validator.sql
  migration_v27_esrs_oam_ack.sql
  migration_v28_esrs_attestation.sql
  migration_v29_esrs_guest_sessions.sql
  migration_v30_fix_audit_log.sql
  migration_v32_brsr_core_assurance.sql
  migration_v33_value_chain.sql
  migration_v34_dma_pack.sql
  migration_v35_assurance_registry.sql
  migration_v36_audit_trail_columns.sql
  migration_v37_entry_ai_provenance.sql
  migration_v38_entry_source_values.sql
)

STARTED_CONTAINER=0
HAVE_LOCAL_PSQL=0
if command -v psql >/dev/null 2>&1; then
  HAVE_LOCAL_PSQL=1
fi
if [[ "${1:-}" == "--no-docker" && "$HAVE_LOCAL_PSQL" == "0" ]]; then
  echo "--no-docker requires a local psql client" >&2
  exit 2
fi
if [[ "${1:-}" == "--no-docker" ]]; then
  # CI service path: ensure the target database exists.
  DB="${PGDATABASE:-filebrsr_migrate_check}"
  export PGDATABASE="$DB"
  psql -d postgres -c "drop database if exists \"$DB\"" -c "create database \"$DB\"" >/dev/null
fi
if [[ "${1:-}" != "--no-docker" ]]; then
  if ! docker info >/dev/null 2>&1; then
    echo "docker is unavailable and --no-docker was not passed (set PGHOST/PGUSER/PGPASSWORD/PGDATABASE)" >&2
    exit 2
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  echo "-> starting $IMAGE as $CONTAINER"
  docker run -d --rm --name "$CONTAINER" -e POSTGRES_PASSWORD="$PASS" -p "$PORT:5432" \
    -v "$SUPA:/migrations:ro" "$IMAGE" >/dev/null
  STARTED_CONTAINER=1
  if [[ "$HAVE_LOCAL_PSQL" == "1" ]]; then
    export PGHOST=localhost PGPORT="$PORT" PGUSER="$USER" PGPASSWORD="$PASS" PGDATABASE=postgres
    for _ in $(seq 1 30); do
      if psql -c "select 1" >/dev/null 2>&1; then break; fi
      sleep 1
    done
    psql -c "select 1" >/dev/null || { echo "postgres did not start" >&2; exit 2; }
    psql -c "drop database if exists \"$DB\"" -c "create database \"$DB\"" >/dev/null
    export PGDATABASE="$DB"
  else
    for _ in $(seq 1 30); do
      if docker exec "$CONTAINER" psql -U "$USER" -c "select 1" >/dev/null 2>&1; then break; fi
      sleep 1
    done
    docker exec "$CONTAINER" psql -U "$USER" -c "select 1" >/dev/null \
      || { echo "postgres did not start" >&2; exit 2; }
    docker exec "$CONTAINER" psql -U "$USER" -c "drop database if exists \"$DB\"" -c "create database \"$DB\"" >/dev/null
  fi
fi

cleanup() {
  if [[ "$STARTED_CONTAINER" == "1" ]]; then
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

export PGSSLMODE="${PGSSLMODE:-prefer}"

# psql front-end: local binary when present, else the server container's own
# client (migration files are mounted at /migrations in that case).
psql_run() {
  if [[ "$HAVE_LOCAL_PSQL" == "1" || "$STARTED_CONTAINER" == "0" ]]; then
    psql -v ON_ERROR_STOP=1 -q "$@"
  else
    docker exec -i "$CONTAINER" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1 -q "$@"
  fi
}

psql_file() {
  if [[ "$HAVE_LOCAL_PSQL" == "1" || "$STARTED_CONTAINER" == "0" ]]; then
    psql -v ON_ERROR_STOP=1 -q -f "$1"
  else
    docker exec -i "$CONTAINER" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1 -q -f "/migrations/$(basename "$1")"
  fi
}

echo "-> preamble: extensions + auth.uid() stub (Supabase-provided in prod)"
psql_run -c "create extension if not exists pgcrypto;" \
         -c "create extension if not exists vector;" \
         -c "create schema if not exists auth;" \
         -c "create table if not exists auth.users (id uuid primary key);" \
         -c "create or replace function auth.uid() returns uuid language sql stable return null::uuid;" \
         -c "create or replace function auth.role() returns text language sql stable return 'anon';" \
         -c "do \$\$ begin
               if not exists (select from pg_roles where rolname = 'anon') then create role anon nologin; end if;
               if not exists (select from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
               if not exists (select from pg_roles where rolname = 'service_role') then create role service_role nologin; end if;
             end \$\$;" \
         -c "create schema if not exists storage;" \
         -c "create table if not exists storage.buckets (id text primary key, name text, public boolean);" \
         -c "create table if not exists storage.objects (id uuid primary key default gen_random_uuid(), bucket_id text, name text);" \
         -c "create or replace function storage.foldername(name text) returns text[] language sql immutable return string_to_array(name, '/');" >/dev/null

for f in "${ORDER[@]}"; do
  if [[ ! -f "$SUPA/$f" ]]; then
    echo "MISSING migration file: $f" >&2
    exit 1
  fi
  echo "-> applying $f"
  if ! out="$(psql_file "$SUPA/$f" 2>&1)"; then
    echo "FAILED: $f" >&2
    echo "$out" | tail -5 >&2
    exit 1
  fi
  if echo "$out" | grep -Ei "^(ERROR|FATAL)" >/dev/null; then
    echo "FAILED (reported error): $f" >&2
    echo "$out" | grep -Ei "^(ERROR|FATAL)" | head -5 >&2
    exit 1
  fi
done

echo "-> post-checks"
for t in esrs_stakeholders esrs_dma_config iro_dr_links assurance_providers assurance_workpapers esrs_guest_sessions brsr_core_assurance value_chain_partners esrs_reports; do
  got="$(psql_run -tAc "select to_regclass('public.$t')")"
  if [[ "$got" != "$t" ]]; then
    echo "MISSING table after migrations: public.$t" >&2
    exit 1
  fi
done
count="$(psql_run -tAc "select count(*) from pg_tables where schemaname='public'")"
echo "-> OK: all ${#ORDER[@]} files applied, $count public tables present"
