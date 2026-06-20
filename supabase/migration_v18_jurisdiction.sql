-- Migration V18: jurisdiction tagging + publication gate for calculations
-- ==========================================================================
-- Phase F of the provenance-hardening + multi-jurisdiction work. Adds three
-- columns to public.calculations:
--
--   jurisdiction    ISO 3166-1 alpha-2 country the calculation reports under
--                   ('IN' India / CEA, 'AU' Australia / NGA). Defaults to 'IN'
--                   so existing rows keep their (India-only) meaning.
--   framework_tags  text[] of "<framework>:<ref>" tags resolved from
--                   app.jurisdiction_frameworks (e.g. 'AASB S2:AASB S2 ¶29(a)',
--                   'NGER:...'; 'BRSR Core:...', 'CCTS:...'). Mirrors the
--                   fbrsr:frameworkTags carried in the signed PROV-O graph.
--   published       boolean gate for the PUBLIC verify endpoint
--                   (app/router_verify.py). Only published calculations are
--                   resolvable by anonymous /api/verify/{id} callers; defaults
--                   to FALSE so nothing is exposed until a tenant opts in.
--
-- Idempotent (ADD COLUMN IF NOT EXISTS). Run AFTER migration_v17_merkle_ledger.sql.
-- ==========================================================================

alter table public.calculations
  add column if not exists jurisdiction   text not null default 'IN';

alter table public.calculations
  add column if not exists framework_tags text[] not null default '{}';

alter table public.calculations
  add column if not exists published      boolean not null default false;

-- Constrain jurisdiction to the supported set. Drop-then-add so re-running the
-- migration after the allow-list grows does not fail on a pre-existing check.
alter table public.calculations
  drop constraint if exists calculations_jurisdiction_chk;
alter table public.calculations
  add constraint calculations_jurisdiction_chk
  check (jurisdiction in ('IN', 'AU'));

-- The public verify endpoint filters on published; index the common path
-- (published rows looked up by id is already covered by the PK, but listing a
-- tenant's published calculations is a likely admin/report query).
create index if not exists idx_calculations_org_published
  on public.calculations (org_id, published)
  where published = true;

-- Helpful for jurisdiction-scoped reporting / benchmarks.
create index if not exists idx_calculations_org_jurisdiction
  on public.calculations (org_id, jurisdiction);

comment on column public.calculations.jurisdiction is
  'ISO 3166-1 alpha-2 reporting country (IN=CEA, AU=NGA). Default IN.';
comment on column public.calculations.framework_tags is
  'Resolved "<framework>:<ref>" regulatory tags; mirrors signed PROV-O fbrsr:frameworkTags.';
comment on column public.calculations.published is
  'When true, resolvable by the anonymous public verify endpoint (/api/verify/{id}).';
