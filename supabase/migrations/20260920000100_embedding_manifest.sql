alter table public.quran_chunks
  add column if not exists embedding_fingerprint text;

alter table public.quran_chunks
  add column if not exists embedding_model text;

alter table public.quran_chunks
  add column if not exists embedding_dimensions smallint;

-- Current corpus was freshly indexed with this exact model before this migration.
-- Mark it atomically so future runs can distinguish resumed work from stale vectors.
update public.quran_chunks
set
  embedding_fingerprint = md5(
    'e5-manifest-v1:intfloat/multilingual-e5-base:768:passage: ' || content
  ),
  embedding_model = 'intfloat/multilingual-e5-base',
  embedding_dimensions = 768
where embedding_fingerprint is null;

-- Preserve the active provider's tafsir provenance on searchable child rows.
-- Quran.com Arabic/English remain attributed separately on their parent record.
update public.quran_chunks as child
set metadata = child.metadata || jsonb_build_object('unverified_community_source', true)
from public.quran_documents as parent
where child.parent_id = parent.id
  and child.chunk_type = 'tafsir'
  and parent.metadata ->> 'tafsir_unverified_community_source' = 'true';

alter table public.quran_chunks
  alter column embedding_fingerprint set not null;

alter table public.quran_chunks
  alter column embedding_model set not null;

alter table public.quran_chunks
  alter column embedding_dimensions set not null;
