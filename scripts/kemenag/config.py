"""Shared paths, URLs, and batch sizes for the Kemenag corpus scripts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MANIFEST = ROOT / "data/manifests/kemenag_reflection_verses.json"
DEFAULT_RAW_CACHE = ROOT / "data/raw/kemenag_reflection_scrape.json"
DEFAULT_BASE_URL = "https://quran-api.lpmqkemenag.id/alquran/data"

CORPUS_PAGE_SIZE = 1000
EMBEDDING_BATCH_SIZE = 16
DOCUMENT_UPSERT_BATCH_SIZE = 64
CHUNK_UPSERT_BATCH_SIZE = 32
