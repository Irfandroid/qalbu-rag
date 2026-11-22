import json

import httpx
import pytest

from app.providers.embeddings.ollama import (
    OllamaEmbeddingProvider,
    embedding_fingerprint,
)


@pytest.mark.asyncio
async def test_ollama_embeddings_use_retrieval_prefixes_and_validate_dimensions():
    inputs: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/embed"
        inputs.extend(payload["input"])
        return httpx.Response(
            200,
            json={"embeddings": [[0.1, 0.2] for _ in payload["input"]]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OllamaEmbeddingProvider(dimensions=2, client=client)
        assert len(await provider.embed_query("kecemasan")) == 2
        assert len(await provider.embed_documents(["Ar-Ra'd 13:28"])) == 1
    assert inputs == [
        "task: search result | query: kecemasan",
        "title: none | text: Ar-Ra'd 13:28",
    ]


@pytest.mark.asyncio
async def test_ollama_embeddings_reject_wrong_dimensions():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OllamaEmbeddingProvider(dimensions=768, client=client)
        with pytest.raises(ValueError):
            await provider.embed_documents(["Ar-Ra'd 13:28"])


def test_embedding_fingerprint_changes_with_input_or_model():
    current = embedding_fingerprint("embeddinggemma", 768, "Terjemahan")
    assert current == embedding_fingerprint("embeddinggemma", 768, "Terjemahan")
    assert current != embedding_fingerprint("embeddinggemma", 768, "Berubah")
    assert current != embedding_fingerprint("another-model", 768, "Terjemahan")
