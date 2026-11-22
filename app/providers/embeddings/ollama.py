import asyncio
from hashlib import sha256

import httpx

from app.core.cache import query_embedding_cache

OLLAMA_EMBEDDING_MANIFEST_VERSION = "ollama-manifest-v1"


def embedding_fingerprint(model_name: str, dimensions: int, content: str) -> str:
    source = (
        f"{OLLAMA_EMBEDDING_MANIFEST_VERSION}:{model_name}:{dimensions}"
        f":search_document:{content}"
    )
    return sha256(source.encode()).hexdigest()


def _query_input(text: str) -> str:
    """EmbeddingGemma expects an explicit retrieval task prefix."""
    return f"task: search result | query: {text}"


def _document_input(text: str) -> str:
    return f"title: none | text: {text}"


class OllamaEmbeddingProvider:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "embeddinggemma",
        dimensions: int = 768,
        timeout_seconds: float = 90,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client = client

    async def embed_query(self, text: str) -> list[float]:
        key = sha256(
            f"ollama:q:{self.model}:{self.dimensions}:{text}".encode()
        ).hexdigest()
        cached = query_embedding_cache.get(key)
        if cached is not None:
            return cached
        vectors = await self._embed([_query_input(text)])
        query_embedding_cache.set(key, vectors[0])
        return vectors[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._embed([_document_input(text) for text in texts])

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self.model, "input": texts, "truncate": True}
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(f"{self.base_url}/api/embed", json=payload)
                    response.raise_for_status()
                    vectors: list[list[float]] = response.json()["embeddings"]
                    if len(vectors) != len(texts) or any(
                        len(vector) != self.dimensions for vector in vectors
                    ):
                        raise ValueError("Ollama returned unexpected embedding dimensions")
                    return vectors
                except (httpx.HTTPError, KeyError, TypeError) as exc:
                    if attempt + 1 == self.max_retries:
                        raise RuntimeError("Ollama embedding request failed") from exc
                    await asyncio.sleep(2**attempt)
        finally:
            if own_client:
                await client.aclose()
        raise RuntimeError("Unreachable Ollama embedding state")
