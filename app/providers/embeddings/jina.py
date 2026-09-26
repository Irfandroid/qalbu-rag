import asyncio
from hashlib import sha256

import httpx

from app.core.cache import query_embedding_cache

JINA_EMBEDDINGS_URL = "https://api.jina.ai/v1/embeddings"
EMBEDDING_MANIFEST_VERSION = "jina-manifest-v1"


def embedding_fingerprint(model_name: str, dimensions: int, content: str) -> str:
    source = f"{EMBEDDING_MANIFEST_VERSION}:{model_name}:{dimensions}:retrieval.passage:{content}"
    return sha256(source.encode()).hexdigest()


class JinaEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "jina-embeddings-v5-text-small",
        dimensions: int = 768,
        timeout_seconds: float = 20,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client = client

    async def embed_query(self, text: str) -> list[float]:
        key = sha256(f"jina:q:{self.model}:{self.dimensions}:{text}".encode()).hexdigest()
        cached = query_embedding_cache.get(key)
        if cached is not None:
            return cached
        vectors = await self._embed([text], "retrieval.query")
        query_embedding_cache.set(key, vectors[0])
        return vectors[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await self._embed(texts, "retrieval.passage")

    async def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        payload = {
            "model": self.model,
            "task": task,
            "dimensions": self.dimensions,
            "normalized": True,
            "input": texts,
        }
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        JINA_EMBEDDINGS_URL,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    response.raise_for_status()
                    rows = sorted(response.json()["data"], key=lambda row: row["index"])
                    vectors = [row["embedding"] for row in rows]
                    if len(vectors) != len(texts) or any(
                        len(vector) != self.dimensions for vector in vectors
                    ):
                        raise ValueError("Jina returned unexpected embedding dimensions")
                    return vectors
                except (httpx.HTTPError, KeyError, TypeError) as exc:
                    if attempt + 1 == self.max_retries:
                        raise RuntimeError("Jina embedding request failed") from exc
                    await asyncio.sleep(2**attempt)
        finally:
            if own_client:
                await client.aclose()
        raise RuntimeError("Unreachable Jina embedding state")
