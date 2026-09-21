-- The API uses only a server-side Supabase key. Keep vector search non-public
-- even if a later RLS policy accidentally exposes Quran tables.
revoke all on function public.match_quran_chunks(vector(768), integer) from public;
revoke execute on function public.match_quran_chunks(vector(768), integer) from anon;
revoke execute on function public.match_quran_chunks(vector(768), integer) from authenticated;
grant execute on function public.match_quran_chunks(vector(768), integer) to service_role;
