# Arsitektur MVP

```mermaid
flowchart TD
  Browser --> FastAPI
  FastAPI --> Safety[SafetyGuardrails]
  Safety -->|krisis| Fixed[Respons tetap]
  Safety -->|aman| Embed[JinaEmbeddingProvider]
  Embed --> RPC[Supabase match_quran_chunks]
  RPC --> Docs[quran_documents parent]
  Docs --> Context[Context builder]
  Context --> Gemini[GeminiProvider]
  Gemini --> Validator[CitationValidator + quality gate]
  Validator --> Browser
```

Satu jalur chat memakai corpus `qalbu-seed-v1`. Child chunk hanya indeks vector; parent menyimpan
Arab, terjemahan, tafsir, tema, dan provenance. Tidak ada English route, reranker, scraper,
feedback, history, atau persistence percakapan di runtime.
