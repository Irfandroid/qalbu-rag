# Laporan Audit Live Qalbu

Tanggal verifikasi: 2026-10-23 (Asia/Jakarta).

## Supabase dan provenance

Audit dilakukan read-only memakai server key dari `.env`; tidak ada insert, update, delete,
migrasi, atau perubahan konfigurasi.

| Pemeriksaan | Hasil |
|---|---:|
| Corpus aktif | `qalbu-kemenag-v1` |
| Parent sesuai manifest | 282/282 |
| ID parent cocok manifest | Ya |
| Provenance resmi Kemenag | 282/282 |
| Terjemahan tidak kosong | 282/282 |
| Child `arabic` / `translation` / `tafsir` / `themes` | 282 / 282 / 282 / 225 |
| Parent memiliki tiga child inti | 282/282 |

Endpoint live juga diverifikasi langsung melalui aplikasi:

- `GET /api/v1/dataset/verse-of-day` → HTTP 200.
- Tanggal produk: `2026-10-23`, timezone `Asia/Jakarta`.
- Ayat terpilih: `2:155`.
- Detail URL cocok dan detail mengembalikan Arab, terjemahan, serta provenance resmi.
- `GET /api/v1/dataset/verses` → HTTP 200 dengan katalog 282 parent dan child count aktual.

Ayat Hari Ini tidak memanggil Gemini, Jina, atau vector retrieval; hanya membaca parent aktif
Supabase setelah memilih key deterministik dari manifest.

## Status ingestion

`python -m scripts.scrape_kemenag_manifest --dry-run` selesai tanpa write:

```text
Manifest: 100 ranges, 201 ayat
Ready in corpus: 201; needing sync: 0
Keys needing sync: none
```

Production ingestion tidak dijalankan karena corpus live sudah lengkap dan tidak ada data pending.

## Status deployment

Deployment belum dijalankan. Repository memiliki `render.yaml`, tetapi Render MCP belum memiliki
workspace terpilih. Workspace yang tersedia adalah `Portfolio`; deploy hanya boleh dilanjutkan setelah
workspace itu dikonfirmasi dan perubahan lokal dipush ke remote yang dimaksud.

## Batasan

- Audit ini membuktikan read path dan provenance pada database yang sedang terhubung, bukan kesiapan
  secret Gemini/Jina atau kualitas retrieval end-to-end.
- Tidak ada production write yang diuji karena tidak diperlukan untuk corpus yang sudah lengkap.
- Belum ada verifikasi URL publik Render sampai workspace dan deploy dikonfirmasi.
