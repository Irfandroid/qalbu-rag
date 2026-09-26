-- Qalbu accesses these tables only from its trusted backend.
revoke all on table public.quran_documents from anon, authenticated, public;
revoke all on table public.quran_chunks from anon, authenticated, public;
revoke all on table public.retrieval_feedback from anon, authenticated, public;

grant select, insert, update, delete on table public.quran_documents to service_role;
grant select, insert, update, delete on table public.quran_chunks to service_role;
grant select, insert, update on table public.retrieval_feedback to service_role;

drop policy if exists "Qalbu backend manages Quran documents" on public.quran_documents;
create policy "Qalbu backend manages Quran documents"
  on public.quran_documents for all to service_role
  using (true) with check (true);

drop policy if exists "Qalbu backend manages Quran chunks" on public.quran_chunks;
create policy "Qalbu backend manages Quran chunks"
  on public.quran_chunks for all to service_role
  using (true) with check (true);

drop policy if exists "Qalbu backend manages feedback" on public.retrieval_feedback;
create policy "Qalbu backend manages feedback"
  on public.retrieval_feedback for all to service_role
  using (true) with check (true);

-- Legacy helper was SECURITY DEFINER in the exposed public schema. It is not
-- used by current Qalbu runtime and must not be callable through Data API RPC.
revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
