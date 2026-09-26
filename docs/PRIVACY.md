# Privasi MVP

- Percakapan tidak disimpan ke database.
- Cache hanya in-memory per proses dan punya TTL; restart service menghapusnya.
- Credential Gemini, Jina, dan Supabase hanya dibaca backend dari environment.
- Jangan memasukkan data pribadi yang tidak perlu ke prompt.
- Supabase secret/service key tidak boleh dikirim ke browser.
