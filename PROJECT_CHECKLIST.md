# Qalbu Implementation Checklist

Status against `PRD.md` and `ARSITEKTUR.md`, adapted to current decisions: Supabase pgvector, multilingual E5, and Ollama Qwen 2.5 3B only.

## Implemented

- [x] FastAPI service and static chat UI
- [x] Parent-child storage and retrieval
- [x] Full 6,236-ayah Quran.com parent corpus across 114 surahs
- [x] Parent-to-multiple-child schema for 100–120-word translation/tafsir chunks
- [x] Local 11,731-child manifest generated (6,260 translation, 5,471 tafsir)
- [ ] Verify all 11,731 active child vectors and fingerprints directly in Supabase
- [x] HNSW migration applied to Supabase pgvector
- [x] Deterministic safety check runs before retrieval and generation
- [x] Slang, repeated-letter, leetspeak, and selected hard-negative normalization
- [x] Hybrid curated plus vector retrieval for reviewed mental-health intents
- [x] Similarity threshold and parent deduplication
- [x] `accusatory` metadata filter before context reaches generator
- [x] Grounded structured-output prompt
- [x] Citation validator rejects references outside retrieved parents
- [x] SSE endpoint at `POST /api/v1/chat`
- [x] Final validated `response` carries reflection and canonical evidence atomically
- [x] Crisis, honest fallback, generator-down, validation-failed, error, and done events
- [x] Legacy JSON endpoint at `POST /api/chat`
- [x] Public health, readiness, source, evaluation, and config endpoints
- [x] Chat UI shows Arabic, translation availability, tafsir, provenance, and disclaimer
- [x] Evaluation page reads measured report data and never fills missing metrics
- [x] Response and LLM caches
- [x] Docker Compose health check
- [x] Automated unit and API tests

## Measured Sample

- Retrieval cases: 5
- Retrieval hit@5: 1.00
- Retrieval MRR: 1.00
- Crisis positive cases: 6
- Crisis recall: 1.00
- Crisis negative cases: 4
- Crisis false-positive rate: 0.00
- Warm retrieval p50: about 0.33 seconds
- Cold retrieval observed: 17 to 30 seconds due local E5 model load
- Local generation model changed to the lighter `qwen2.5:3b-instruct`; remeasurement pending

These are development samples, not release claims.

## Release Blockers

- [ ] Expand retrieval golden set from 5 to 60 labeled queries
- [ ] Expand crisis set from 10 to 80 reviewed cases
- [ ] Run full faithfulness and citation-validity generation evaluation
- [ ] Measure 20-query peak RSS and enforce the 4 GB gate
- [ ] Add verified Indonesian translation source
- [ ] Fill the 806 ayahs without community Arabic tafsir (Arabic and English translation are complete)
- [ ] Add official Kemenag source after official endpoint and token are available
- [ ] Set and independently verify `CRISIS_LINE`
- [ ] Measure and tune Qwen cold/warm latency for public demo
- [ ] Run keyboard, mobile, screen-reader, and Lighthouse accessibility checks
- [ ] Add CI workflow and deployment configuration
- [ ] Choose a code license and independently verify redistribution terms for every corpus

## Current Data Warning

The active Quran.com snapshot contains all 6,236 Arabic ayahs and attributed English Saheeh International translation. The optional Arabic tafsir layer is a separate community Kaggle mirror and is incomplete. Neither source is labeled as official Kemenag data. Qalbu must not manufacture or label a model paraphrase as official Indonesian translation.
