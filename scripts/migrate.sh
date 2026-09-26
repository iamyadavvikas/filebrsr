#!/usr/bin/env bash
# Applies supabase/migration_*.sql files in version order against the
# configured Supabase database, recording each run in supabase_migrations.
#
# Inputs (env):
#   SUPABASE_DB_URL   pooled/psql connection string for a privileged role
#
# Usage:
#   migrate.sh record    bootstrap: stamp every existing file as applied WITHOUT
#                        executing it (one-time, after the repo catches up with
#                        the manually-migrated DB) — also derives the cursor.
#   migrate.sh apply     apply files newer than the cursor; fail closed on
#                        ordering drift or checksum mismatch.
#
# A version is the integer in "migration_v<N>_...". All files with a version
# <= the last recorded one must already be recorded; an unrecorded file whose
# version is <= cursor (or tied at the cursor) aborts, because we cannot
# reconstruct the original ordering of retrospective files. New migrations must
# therefore use a strictly increasing, unique version number.

set -euo pipefail

: "${SUPABASE_DB_URL:?SUPABASE_DB_URL required}"

MODE="${1:-apply}"
MIGRATIONS_DIR="$(cd "$(dirname "$0")/../supabase" && pwd)"

# Run psql inside a throwaway postgres image (runners don't ship psql).
psql_() {
  docker run --rm -i postgres:16-alpine \
    psql -X -v ON_ERROR_STOP=1 -qAt "$@" "$SUPABASE_DB_URL"
}
# stdin is passed through for -f - cases via psql_reading().
psql_reading() {
  docker run --rm -i postgres:16-alpine \
    psql -X -v ON_ERROR_STOP=1 -qAt "$@" "$SUPABASE_DB_URL"
}

echo "→ supabase_migrations on ${SUPABASE_DB_URL%%:*//*}${SUPABASE_DB_URL#*://*@}"

psql_ <<'SQL' >/dev/null
create schema if not exists supabase_migrations;
create table if not exists supabase_migrations.versions (
  version    integer not null,
  filename   text    not null,
  checksum   text    not null,
  applied_at timestamptz not null default now(),
  primary key (version, filename)
);
SQL

CURSOR="$(psql_ -c "select coalesce(max(version), 0) from supabase_migrations.versions;")"
echo "→ recorded cursor: version $CURSOR ($(psql_ -c "select count(*) from supabase_migrations.versions;") files recorded)"

record() {
  local f v sum
  for f in "$MIGRATIONS_DIR"/migration_v*.sql; do
    [[ -e "$f" ]] || continue
    v="$(basename "$f" | sed -n 's/^migration_v\([0-9][0-9]*\).*\.sql$/\1/p')"
    [[ -n "$v" ]] || { echo "✖ cannot parse version from $(basename "$f")"; exit 1; }
    sum="$(shasum -a 256 "$f" | awk '{print $1}')"
    psql_ -c "insert into supabase_migrations.versions (version, filename, checksum)
               values ($v, '$(basename "$f")', '$sum')
               on conflict (version, filename) do update set checksum = excluded.checksum;"
    echo "   recorded $(basename "$f") (v$v)"
  done
}

if [[ "$MODE" == "record" ]]; then
  record
  echo "✓ bootstrap complete"
  exit 0
fi

[[ "$MODE" == "apply" ]] || { echo "✖ mode must be 'record' or 'apply'"; exit 2; }

# Drift check: recorded files must still match on disk.
for f in "$MIGRATIONS_DIR"/migration_v*.sql; do
  [[ -e "$f" ]] || continue
  name="$(basename "$f")"
  sum="$(shasum -a 256 "$f" | awk '{print $1}')"
  existing="$(psql_ -c "select checksum from supabase_migrations.versions where filename = '$name';")"
  if [[ -n "${existing}" && "$existing" != "$sum" ]]; then
    echo "✖ checksum drift for $name — a previously applied migration was edited. Remove the edit or record a new migration." >&2
    exit 1
  fi
done
echo "→ drift check passed"

applied=0
for f in "$MIGRATIONS_DIR"/migration_v*.sql; do
  [[ -e "$f" ]] || continue
  name="$(basename "$f")"
  v="$(sed -n 's/^migration_v\([0-9][0-9]*\).*\.sql$/\1/p' <<< "$name")"
  known="$(psql_ -c "select 1 from supabase_migrations.versions where filename = '$name';")"

  if [[ -z "$known" ]]; then
    if (( v <= CURSOR )); then
      echo "✖ $name (v$v) is not recorded but is at/below the cursor (v$CURSOR) — cannot order it retrospectively." >&2
      echo "  If this file was applied manually, record it: ./scripts/migrate.sh record" >&2
      echo "  If it is new, bump its version number above $CURSOR." >&2
      exit 1
    fi
    echo "→ applying $name (v$v)"
    psql_reading -1 -f - < "$f"
    sum="$(shasum -a 256 "$f" | awk '{print $1}')"
    psql_ -c "insert into supabase_migrations.versions (version, filename, checksum)
               values ($v, '$name', '$sum');"
    applied=$((applied + 1))
  fi
done

echo "✓ migrations $([ "$applied" -gt 0 ] && echo "applied: $applied new" || echo "up to date")"