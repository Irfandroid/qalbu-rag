# Panduan implementasi dan operasi Qalbu

## Keputusan teknis aktif

- API/UI: FastAPI menyajikan endpoint dan static frontend pada origin yang sama.
- Database/vector store: Supabase Postgres + pgvector.
- Retrieval: search child kecil, ambil parent ayat lengkap.
- Embedding: lokal `intfloat/multilingual-e5-base`, normalized 768-dim E5 vectors.
- Generator: Ollama `qwen2.5:3b-instruct`; profil CPU/RAM 8 GB.
- Bahasa sumber sementara: Arabic Uthmani + attributed English Saheeh International.
- Tafsir: dataset Arabic komunitas yang tidak lengkap dan tidak boleh dilabeli Kemenag.

Supabase tetap dipakai karena pola child vector → parent document sudah tercakup tanpa menambah vector database kedua.

## Setup native

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen2.5:3b-instruct
```

`.env.example` ditujukan ke Docker-to-host. Untuk native Windows, set:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Tambahkan `SUPABASE_URL` dan `SUPABASE_SECRET_KEY`. Gunakan secret/server key hanya pada backend. Start:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Database

Terapkan SQL di `supabase/migrations/` secara berurutan. Migration mengatur:

- table parent `quran_documents`;
- table child `quran_chunks`;
- pgvector 768 dimensi;
- HNSW cosine index;
- RPC `match_quran_chunks`;
- manifest embedding yang dipakai proses resumable.

Setelah migration:

```powershell
python scripts/fetch_quran_com.py
python scripts/seed.py
python scripts/chunk.py
python scripts/embed.py
python scripts/reconcile_chunks.py
```

Aturan operasi:

1. Jangan reconcile sebelum embedding selesai; script memang menolak bila expected child masih hilang.
2. Jangan mencampur vector dari model/dimensi berbeda.
3. Jangan menjalankan legacy prune tanpa backup dan verifikasi semua expected parent/child.
4. Bump `RAG_CACHE_VERSION` setelah source, prompt, atau routing berubah.

## Mengganti sumber data

Provider baru harus menghasilkan model parent yang sama, tetapi mempertahankan identity dan provenance sendiri.

Untuk Kemenag:

1. Implementasikan provider terpisah di `app/quran/providers/`.
2. Simpan nama provider, versi, URL, license/permission, language, dan official status.
3. Jangan overwrite atau relabel Quran.com/community record.
4. Tambahkan translation sebagai searchable child.
5. Re-run full indexing dan evaluation.
6. Review display attribution sebelum release.

## Mengganti embedding model

Perubahan model dengan dimensi tetap tetap memerlukan re-embedding semua child. Perubahan dimensi memerlukan coordinated migration:

1. kolom vector;
2. HNSW index;
3. RPC signature/query;
4. application settings/validation;
5. full re-index;
6. retrieval evaluation.

Qalbu sengaja menolak `EMBEDDING_DIMENSIONS` selain 768 sampai semua bagian tersebut dimigrasikan bersama.

## Quality gate respons

Draft model tidak langsung dikirim ke browser. Pipeline:

```text
LLM JSON draft
  → citation canonicalization
  → contextual relevance
  → tafsir/evidence support
  → unsupported-claim and quote guard
  → length/format guard
  → pass OR reviewed fallback OR one repair OR fail closed
```

Curated safe response hanya berlaku untuk intent exact yang telah direview. Query umum tidak boleh dipaksa memakai template yang tidak cocok.

## Test dan evaluasi

```powershell
python -m pytest -q
python -m ruff check app tests scripts evaluation
python -m mypy app
python evaluation/evaluate.py
```

Sebelum klaim full embedding, verifikasi row count, non-null embedding, model, dimensi, dan fingerprint langsung di database. Manifest lokal saja belum cukup.

## Release gate minimum

- Hak pakai dan attribution source jelas.
- Terjemahan/tafsir dan theme label direview ahli konten Islam.
- Crisis wording dan alur bahaya segera direview profesional kesehatan mental.
- `CRISIS_LINE` benar dan diverifikasi independen.
- Golden set retrieval dan grounded generation diperluas.
- Negative query, citation rejection, prompt injection, rate limiting, dan model outage diuji.
- Shared limiter/cache dipasang sebelum multi-replica.
- Secret scan, accessibility, load/RAM, backup, logging, dan incident procedure siap.
- Production runtime tidak memakai Uvicorn reload/bind mount development.
