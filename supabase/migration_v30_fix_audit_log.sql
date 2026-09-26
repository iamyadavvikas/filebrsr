-- Migration V30: fix fn_audit_log so INSERTs on organizations stop failing
-- ==========================================================================
-- prod + local repro: INSERT into "organizations" raised
--   42703: record "old" has no field "org_id"
-- from the trg_audit_organizations AFTER-trigger. "organizations" is itself
-- the org and has no org_id column, so the audit function must derive org via
-- JSON (column may be absent) instead of direct record-field access, and must
-- only touch old/new record fields valid for the current TG_OP.
--
-- This blocks every new-org INSERT -- real signups AND the guest-sandbox mint.
-- The fix below is idempotent (CREATE OR REPLACE FUNCTION) and safe against
-- tables both with (calculations / provenance_records) and without
-- (organizations) an org_id column.
--
-- Local verification (Postgres 16):
--   organizations (no org_id)      : INSERT/UPDATE/DELETE OK, org_id NULL
--   provenance_records (has org_id): INSERT/UPDATE/DELETE OK, org_id captured
--   audit_log rows written with correct old/new snapshots per action.

create or replace function public.fn_audit_log()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org  uuid;
  v_pk   text;
  v_old  jsonb;
  v_new  jsonb;
begin
  if tg_op = 'DELETE' then
    v_org := (to_jsonb(old) ->> 'org_id')::uuid;
    v_pk  := to_jsonb(old) ->> 'id';
    v_old := to_jsonb(old);
  elsif tg_op = 'UPDATE' then
    v_org := (to_jsonb(new) ->> 'org_id')::uuid;
    v_pk  := to_jsonb(new) ->> 'id';
    v_old := to_jsonb(old);
    v_new := to_jsonb(new);
  else -- INSERT
    v_org := (to_jsonb(new) ->> 'org_id')::uuid;
    v_pk  := to_jsonb(new) ->> 'id';
    v_new := to_jsonb(new);
  end if;

  insert into public.audit_log (org_id, actor_id, table_name, row_pk, action, old_data, new_data)
  values (v_org, auth.uid(), tg_table_name, v_pk, tg_op, v_old, v_new);
  return null;  -- AFTER trigger
end $$;