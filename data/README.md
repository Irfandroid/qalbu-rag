# Data MVP

`external/indonesian-quran/` menyimpan snapshot ayat Indonesia yang dipakai sebagai artefak
referensi/seed. Runtime chat tidak membaca file ini langsung; runtime mengambil corpus
`qalbu-seed-v1` dari Supabase.

Corpus aktif `qalbu-seed-v1` mengambil ayat, terjemahan, dan tafsir dari
[API Al-Qur'an Kemenag](https://quran-api.lpmqkemenag.id/alquran/data), LPMQ Kementerian Agama RI.
Provenance disimpan pada kolom `source` dan `metadata` di `quran_documents`.

Setiap respons tetap menampilkan Arab, terjemahan, tafsir, dan provenance dari row Supabase.
Jangan menaruh credential atau percakapan pengguna di folder data.

## Taxonomy kesehatan mental

`manifests/mental_health_categories.json` memetakan kondisi emosional ke ayat yang sudah
terverifikasi di corpus aktif Kemenag. Sinkronkan label ke corpus Supabase dan re-embed chunk yang
berubah dengan:

```powershell
python -m scripts.sync_mental_health_categories --dry-run
python -m scripts.sync_mental_health_categories
```

Kategori keselamatan (`self_harm`, ide bunuh diri, psikosis, dan krisis berat) hanya dipakai oleh
safety guardrail dan tidak pernah dipakai untuk mencari atau membuat ayat. Kategori yang belum
memiliki ayat pada corpus ditandai `recommended_verse_keys` dan menunggu fetch API Kemenag; ayat
tidak boleh ditambahkan hanya berdasarkan kemiripan kata.
