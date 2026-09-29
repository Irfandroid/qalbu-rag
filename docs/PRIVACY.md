# Privasi MVP

- Riwayat chat disimpan lokal di browser untuk fitur New Chat; server tidak menyimpan percakapan.
- Hapus data situs/browser untuk menghapus history lokal. Jangan gunakan history lokal pada perangkat bersama.
- Cache hanya in-memory per proses dan punya TTL; restart service menghapusnya.
- Credential Gemini, Jina, dan Supabase hanya dibaca backend dari environment.
- Jangan memasukkan data pribadi yang tidak perlu ke prompt.
- Supabase secret/service key tidak boleh dikirim ke browser.
