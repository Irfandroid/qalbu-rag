# Data MVP

`external/indonesian-quran/` menyimpan snapshot ayat Indonesia yang dipakai sebagai artefak
referensi/seed. Runtime chat tidak membaca file ini langsung; runtime mengambil corpus
`qalbu-seed-v1` dari Supabase.

Corpus aktif `qalbu-seed-v1` mengambil ayat, terjemahan, dan tafsir dari
[API Al-Qur'an Kemenag](https://quran-api.lpmqkemenag.id/alquran/data), LPMQ Kementerian Agama RI.
Provenance disimpan pada kolom `source` dan `metadata` di `quran_documents`.

Setiap respons tetap menampilkan Arab, terjemahan, tafsir, dan provenance dari row Supabase.
Jangan menaruh credential atau percakapan pengguna di folder data.
