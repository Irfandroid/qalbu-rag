from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Small process-local LRU cache. Never persists user prompts to disk."""

    def __init__(self, ttl_seconds: int, max_entries: int) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> T | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry.value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._entries[key] = CacheEntry(value, monotonic() + self.ttl_seconds)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)


query_embedding_cache: TTLCache[list[float]] = TTLCache(ttl_seconds=900, max_entries=500)
llm_response_cache: TTLCache[dict[str, object]] = TTLCache(ttl_seconds=3600, max_entries=500)
rag_response_cache: TTLCache[dict[str, object]] = TTLCache(ttl_seconds=900, max_entries=500)
