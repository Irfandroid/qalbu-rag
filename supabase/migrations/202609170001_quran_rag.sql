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
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.quran_chunks (
  id text primary key,
  parent_id text not null references public.quran_documents(id) on delete cascade,
  chunk_type text not null check (chunk_type in ('arabic', 'translation', 'tafsir', 'themes')),
  content text not null check (length(trim(content)) > 0),
  embedding vector(768) not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(parent_id, chunk_type)
);

create index if not exists quran_chunks_embedding_idx on public.quran_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
alter table public.quran_documents enable row level security;
alter table public.quran_chunks enable row level security;

create or replace function public.match_quran_chunks(query_embedding vector(768), match_count integer)
returns table(child_id text, parent_id text, score float, chunk_type text, surah_number smallint, surah_name text, ayah_start smallint, ayah_end smallint)
language sql stable set search_path = public as $$
  select c.id, c.parent_id, 1 - (c.embedding <=> query_embedding), c.chunk_type, d.surah_number, d.surah_name, d.ayah_start, d.ayah_end
  from quran_chunks c join quran_documents d on d.id = c.parent_id
  order by c.embedding <=> query_embedding limit match_count;
$$;

revoke all on function public.match_quran_chunks(vector, integer) from public;
grant execute on function public.match_quran_chunks(vector, integer) to service_role;
