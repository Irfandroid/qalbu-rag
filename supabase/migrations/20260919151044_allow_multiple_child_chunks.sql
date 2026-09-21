alter table public.quran_chunks
  drop constraint if exists quran_chunks_parent_id_chunk_type_key;

create index if not exists quran_chunks_parent_type_idx
  on public.quran_chunks(parent_id, chunk_type);
