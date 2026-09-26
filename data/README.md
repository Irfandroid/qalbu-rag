# Data MVP

`external/indonesian-quran/` menyimpan snapshot ayat Indonesia yang dipakai sebagai artefak
referensi/seed. Runtime chat tidak membaca file ini langsung; runtime mengambil corpus
`qalbu-seed-v1` dari Supabase.

Setiap respons tetap menampilkan Arab, terjemahan, tafsir, dan provenance dari row Supabase.
Jangan menaruh credential atau percakapan pengguna di folder data.
