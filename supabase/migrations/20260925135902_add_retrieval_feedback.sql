create table if not exists public.retrieval_feedback (
  id uuid primary key default gen_random_uuid(),
  request_id uuid not null unique,
  helpful boolean not null,
  reason text,
  created_at timestamptz not null default now(),
  constraint retrieval_feedback_reason_check check (
    reason is null or reason in (
      'ayat_tidak_relevan',
      'penjelasan_kurang_jelas',
      'terlalu_umum',
      'terasa_menghakimi',
      'terlalu_panjang',
      'masalah_teknis'
    )
  )
);

alter table public.retrieval_feedback enable row level security;

revoke all on table public.retrieval_feedback from anon, authenticated, public;
grant select, insert, update on table public.retrieval_feedback to service_role;

create index if not exists retrieval_feedback_created_at_idx
  on public.retrieval_feedback (created_at desc);

comment on table public.retrieval_feedback is
  'Privacy-minimized response feedback. Does not store raw user messages or model answers.';
