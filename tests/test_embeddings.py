import json

import httpx
import pytest

from app.providers.embeddings.jina import JinaEmbeddingProvider, embedding_fingerprint


@pytest.mark.asyncio
async def test_jina_uses_asymmetric_tasks_and_validates_dimensions():
    tasks: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        tasks.append(payload["task"])
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": index, "embedding": [0.1, 0.2]}
                    for index, _ in enumerate(payload["input"])
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = JinaEmbeddingProvider("secret", dimensions=2, client=client)
        assert len(await provider.embed_query("kecemasan")) == 2
        assert len(await provider.embed_documents(["Ar-Ra'd 13:28"])) == 1
    assert tasks == ["retrieval.query", "retrieval.passage"]


def test_embedding_fingerprint_changes_with_input_or_model():
    current = embedding_fingerprint("jina-model", 768, "Terjemahan")
    assert current == embedding_fingerprint("jina-model", 768, "Terjemahan")
    assert current != embedding_fingerprint("jina-model", 768, "Berubah")
    assert current != embedding_fingerprint("another-model", 768, "Terjemahan")
