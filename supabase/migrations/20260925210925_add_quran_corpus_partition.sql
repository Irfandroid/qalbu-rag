alter table public.quran_documents
  add column if not exists corpus text not null default 'full-quran-v1'
  check (length(trim(corpus)) > 0);

alter table public.quran_chunks
  add column if not exists corpus text not null default 'full-quran-v1'
  check (length(trim(corpus)) > 0);

create index if not exists quran_documents_corpus_idx
  on public.quran_documents (corpus, id);

create index if not exists quran_chunks_corpus_parent_idx
  on public.quran_chunks (corpus, parent_id);

drop function if exists public.match_quran_chunks(vector(768), integer);

create function public.match_quran_chunks(
  query_embedding vector(768),
  match_count integer,
  corpus_filter text default 'full-quran-v1'
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

revoke all on function public.match_quran_chunks(vector(768), integer, text) from public;
revoke execute on function public.match_quran_chunks(vector(768), integer, text)
  from anon, authenticated;
grant execute on function public.match_quran_chunks(vector(768), integer, text)
  to service_role;
