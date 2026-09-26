-- Track which remote model produced each vector. Existing columns are kept
-- compatible with prior installations and populated during idempotent upsert.
alter table public.quran_chunks
  add column if not exists embedding_provider text,
  add column if not exists embedding_model text,
  add column if not exists embedding_version text,
  add column if not exists embedding_dimensions integer,
  add column if not exists embedding_fingerprint text;

create index if not exists quran_chunks_parent_id_idx
  on public.quran_chunks (parent_id);

create index if not exists quran_chunks_embedding_hnsw_idx
  on public.quran_chunks using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

comment on column public.quran_chunks.embedding_provider is
  'External embedding provider used to create this vector.';
