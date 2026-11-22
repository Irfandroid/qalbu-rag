# Privasi MVP

- Riwayat chat disimpan lokal di browser untuk fitur New Chat; server tidak menyimpan percakapan.
- Hapus data situs/browser untuk menghapus history lokal. Jangan gunakan history lokal pada perangkat bersama.
- Cache hanya in-memory per proses dan punya TTL; restart service menghapusnya.
- Prompt, konteks retrieval, dan embedding diproses di mesin sendiri (Ollama + PostgreSQL lokal).
  Tidak ada provider AI eksternal yang menerima isi percakapan.
- Credential database dan konfigurasi Ollama hanya dibaca backend dari environment.
- Jangan memasukkan data pribadi yang tidak perlu ke prompt.
- Akses publik tanpa TLS membuat isi chat bisa dibaca operator jaringan. Aktifkan HTTPS sebelum
  dipakai orang lain.
