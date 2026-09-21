-- HNSW supports incremental inserts, unlike the previous IVF index whose sparse
-- lists could return no candidates while the corpus was still being embedded.
drop index if exists public.quran_chunks_embedding_idx;

create index quran_chunks_embedding_hnsw_idx
  on public.quran_chunks
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

create index if not exists quran_chunks_parent_id_idx
  on public.quran_chunks (parent_id);

create or replace function public.match_quran_chunks(
  query_embedding vector(768),
  match_count integer
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
set hnsw.ef_search = 40
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
  order by c.embedding <=> query_embedding
  limit least(greatest(match_count, 1), 50);
$$;

revoke all on function public.match_quran_chunks(vector(768), integer) from public;
grant execute on function public.match_quran_chunks(vector(768), integer) to service_role;
