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

## Manifest ayat dan tafsir Kemenag

Daftar 100 rentang ayat yang diminta ada di
`manifests/kemenag_reflection_verses.json`. Periksa coverage terhadap corpus:

```powershell
python -m scripts.scrape_kemenag_manifest --dry-run
```

Checklist hasil retrieval yang sudah diverifikasi ada di
`manifests/kemenag_retrieved_verses.json` (`201/201` ayat, `missing_verses: 0`).

Untuk mengambil ayat yang belum ada, isi `KEMENAG_USERNAME`, `KEMENAG_PASSWORD`, dan
`KEMENAG_TOKEN` di `.env`, lalu jalankan:

```powershell
python -m scripts.scrape_kemenag_manifest
```

Script memakai endpoint `getAyat` dan `getAyatTafsir`, menyimpan cache mentah lokal yang di-ignore
Git, memvalidasi provenance Kemenag, membuat embedding Jina, lalu memasukkan parent document dan
child chunk ke corpus `qalbu-seed-v1`.
