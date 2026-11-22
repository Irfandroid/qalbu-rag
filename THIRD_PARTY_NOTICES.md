# Third-party notices

- FastAPI serves the API and the dataset fallback pages; lighttpd fronts it in the Compose stack.
- PostgreSQL + pgvector stores the Quran corpus and performs cosine search locally.
- Ollama runs the local embedding (EmbeddingGemma) and chat (Qwen) models; review the model
  licenses before deployment.
- The Quran corpus is sourced from the LPMQ Kementerian Agama RI portal; attribution is shown in
  the UI and stored in document metadata.
- The frontend is plain HTML/CSS/ES modules; no third-party runtime is bundled.
