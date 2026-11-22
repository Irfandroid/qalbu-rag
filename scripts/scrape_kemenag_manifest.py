"""Fetch the requested Kemenag verses and upsert them into the active corpus.

The implementation lives in :mod:`scripts.kemenag`; this module keeps the
historical import path and the command-line entry point.
"""

from app.quran.catalog import expand_ranges
from scripts.kemenag.cache import load_cache, save_cache
from scripts.kemenag.config import DEFAULT_MANIFEST, DEFAULT_RAW_CACHE
from scripts.kemenag.documents import (
    keys_needing_sync,
    payload_to_document,
    validate_chunk_rows,
)
from scripts.kemenag.parsing import parse_payload
from scripts.kemenag.sync import main, run

# Kept as aliases for callers and tests that use the original MVP manifest.
MANIFEST = DEFAULT_MANIFEST
RAW_CACHE = DEFAULT_RAW_CACHE

__all__ = [
    "MANIFEST",
    "RAW_CACHE",
    "expand_ranges",
    "keys_needing_sync",
    "load_cache",
    "main",
    "parse_payload",
    "payload_to_document",
    "run",
    "save_cache",
    "validate_chunk_rows",
]


if __name__ == "__main__":
    main()
