-- Local PostgreSQL + pgvector schema for the Qalbu Quran corpus.
-- Mounted into the postgres container's docker-entrypoint-initdb.d, so it
-- runs once when the data volume is first created.

create extension if not exists vector;

create table if not exists public.quran_documents (
  id text primary key,
  surah_number smallint not null check (surah_number between 1 and 114),
  surah_name text not null,
  ayah_start smallint not null check (ayah_start > 0),
  ayah_end smallint not null check (ayah_end >= ayah_start),
  arabic_text text,
  translation text,
  tafsir text,
  themes jsonb not null default '[]'::jsonb,
  source jsonb not null,
  metadata jsonb not null default '{}'::jsonb,
  corpus text not null default 'qalbu-kemenag-v1'
    check (length(trim(corpus)) > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.quran_chunks (
  id text primary key,
  parent_id text not null
    references public.quran_documents(id) on delete cascade,
  chunk_type text not null
    check (chunk_type in ('arabic', 'translation', 'tafsir', 'themes')),
  content text not null check (length(trim(content)) > 0),
  embedding vector(768) not null,
  metadata jsonb not null default '{}'::jsonb,
  corpus text not null default 'qalbu-kemenag-v1'
    check (length(trim(corpus)) > 0),
  embedding_provider text,
  embedding_model text,
  embedding_version text,
  embedding_dimensions integer,
  embedding_fingerprint text,
  created_at timestamptz not null default now()
);

create index if not exists quran_documents_corpus_idx
  on public.quran_documents (corpus, id);

create index if not exists quran_chunks_corpus_parent_idx
  on public.quran_chunks (corpus, parent_id);

create index if not exists quran_chunks_parent_id_idx
  on public.quran_chunks (parent_id);

create index if not exists quran_chunks_parent_type_idx
  on public.quran_chunks (parent_id, chunk_type);

create index if not exists quran_chunks_embedding_hnsw_idx
  on public.quran_chunks using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

create or replace function public.match_quran_chunks(
  query_embedding vector(768),
  match_count integer,
  corpus_filter text default 'qalbu-kemenag-v1'
)
returns table(
  child_id text,
  parent_id text,
  score float,
  chunk_type text,
  surah_number smallint,
  surah_name text,
  ayah_start smallint,
  ayah_end smallint
)
language sql
stable
set search_path = public
set hnsw.ef_search = 100
as $$
  select
    c.id,
    c.parent_id,
    1 - (c.embedding <=> query_embedding),
    c.chunk_type,
    d.surah_number,
    d.surah_name,
    d.ayah_start,
    d.ayah_end
  from public.quran_chunks c
  join public.quran_documents d on d.id = c.parent_id
  where c.corpus = corpus_filter
    and d.corpus = corpus_filter
  order by c.embedding <=> query_embedding
  limit least(greatest(match_count, 1), 100);
$$;
