-- Migration V12: pgvector chunk index for per-datapoint retrieval (Phase 3)
-- ==========================================================================
-- Persists the layout-aware chunks emitted by app/pdf_parser.py + app/ocr.py
-- together with their Gemini text-embedding-004 vectors. Enables:
--   1. Per-field retrieval during extraction (top-k cosine search per
--      datapoint label, then a small targeted Gemini call per ~5-field batch)
--   2. "Chat with your filing" follow-up Qs without re-parsing the PDF
--   3. Re-extraction on validation failure (Phase 5.2) without re-OCR
--
-- Embedding dimensions:
--   gemini text-embedding-004 → 768d  (matches vector(768) below)
--   If we ever swap to text-embedding-005 (3072d) this column needs to be
--   re-created — pgvector does not support ALTER COLUMN dimensions.
--
-- Indexing:
--   ivfflat with cosine ops. lists=100 is the sweet spot for the expected
--   row count (≤ 1M chunks ≈ 20k filings × 50 chunks). Re-tune with REINDEX
--   once we cross 5M rows.
--
-- Run AFTER migration_v11_india_compliance.sql.

create extension if not exists vector;

-- ─── Table ────────────────────────────────────────────────────────────────

create table if not exists public.extraction_chunks (
  id              bigserial primary key,
  report_id       uuid not null references public.reports(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  chunk_id        text not null,                 -- pN-cI / pN-tI / pN-ocr
  page_number     int  not null,
  kind            text not null check (kind in ('text', 'table')),
  heading         text,
  content         text not null,
  total_chars     int  not null,
  embedding       vector(768),                   -- nullable: persisted before embed
  embedding_model text,
  created_at      timestamptz not null default now(),
  unique (report_id, chunk_id)
);

-- One row per report can be looked up cheaply
create index if not exists extraction_chunks_report_idx
  on public.extraction_chunks (report_id);

-- Cosine similarity search. Build only after first insert batch in prod for
-- a better centroid; harmless on an empty table.
create index if not exists extraction_chunks_embedding_ivf
  on public.extraction_chunks
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- ─── RLS ──────────────────────────────────────────────────────────────────

alter table public.extraction_chunks enable row level security;

drop policy if exists "Users can view own chunks" on public.extraction_chunks;
create policy "Users can view own chunks"
  on public.extraction_chunks for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own chunks" on public.extraction_chunks;
create policy "Users can insert own chunks"
  on public.extraction_chunks for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete own chunks" on public.extraction_chunks;
create policy "Users can delete own chunks"
  on public.extraction_chunks for delete
  using (auth.uid() = user_id);

-- Service role bypasses RLS automatically; no explicit policy required.

-- ─── Retrieval RPC ────────────────────────────────────────────────────────
-- Called from app/retrieval.py SupabaseChunkIndex via supabase.rpc().
-- Returns the top-N most-similar chunks for one report scoped to the caller.
-- Caller already holds report_id (own row), so we don't need to re-verify
-- ownership inside the function — the RLS predicate on the select does it.

create or replace function public.match_extraction_chunks(
  query_embedding vector(768),
  match_report_id uuid,
  match_count     int default 3
)
returns table (
  chunk_id    text,
  page_number int,
  kind        text,
  heading     text,
  content     text,
  similarity  float
)
language sql
stable
as $$
  select
    chunk_id,
    page_number,
    kind,
    heading,
    content,
    1 - (embedding <=> query_embedding) as similarity
  from public.extraction_chunks
  where report_id = match_report_id
    and embedding is not null
  order by embedding <=> query_embedding
  limit match_count;
$$;

-- Expose the RPC to authenticated users (RLS still applies to the underlying
-- select on extraction_chunks).
grant execute on function public.match_extraction_chunks(vector, uuid, int)
  to authenticated, service_role;
