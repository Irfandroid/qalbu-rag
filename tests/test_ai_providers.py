import json

import httpx
import pytest

from app.providers.embeddings.jina import JinaEmbeddingProvider
from app.providers.llm.gemini import GeminiProvider


@pytest.mark.asyncio
async def test_gemini_parses_structured_grounded_response():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["maxOutputTokens"] == 480
        content = json.dumps(
            {"answer": "Rasa hampa itu terasa berat.", "references": [{"parent_id": "p1"}]}
        )
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": content}]}}]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await GeminiProvider("secret", client=client).generate("hampa", "SOURCE 1")
    assert result.references[0].parent_id == "p1"


@pytest.mark.asyncio
async def test_jina_embedding_returns_expected_vector():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["task"] == "retrieval.query"
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await JinaEmbeddingProvider(
            "secret", dimensions=2, client=client
        ).embed_query("hampa")
    assert result == [0.1, 0.2]
