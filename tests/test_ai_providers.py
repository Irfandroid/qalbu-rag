import json

import httpx
import pytest

from app.providers.llm.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_parses_structured_grounded_response():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["stream"] is False
        assert payload["format"]["required"] == ["answer", "references"]
        assert payload["options"]["num_predict"] == 480
        assert payload["messages"][0]["role"] == "system"
        content = json.dumps(
            {"answer": "Rasa hampa itu terasa berat.", "references": [{"parent_id": "p1"}]}
        )
        return httpx.Response(200, json={"message": {"content": content}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OllamaProvider(client=client).generate("hampa", "SOURCE 1")
    assert result.references[0].parent_id == "p1"


@pytest.mark.asyncio
async def test_ollama_rejects_malformed_structured_output():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "bukan json"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            await OllamaProvider(client=client).generate("kosong", "SOURCE 1")
