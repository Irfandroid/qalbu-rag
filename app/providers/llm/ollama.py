import asyncio
import json
import logging
from hashlib import sha256

import httpx

from app.core.cache import llm_response_cache
from app.llm.prompts import SYSTEM_PROMPT
from app.models.chat import QalbuResponse

logger = logging.getLogger(__name__)

RESPONSE_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["answer", "references"],
    "properties": {
        "answer": {"type": "string"},
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["parent_id"],
                "properties": {"parent_id": {"type": "string"}},
            },
        },
        "safety_note": {"type": "string"},
    },
}


class OllamaProvider:
    """Grounded local Ollama adapter using JSON schema output."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b-instruct",
        timeout_seconds: float = 90,
        max_retries: int = 3,
        num_ctx: int = 4096,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.num_ctx = num_ctx
        self.client = client

    async def generate(self, query: str, context: str, max_tokens: int = 120) -> QalbuResponse:
        # ``max_tokens`` limits the natural-language answer; the output budget also
        # has to fit the JSON envelope and citations or the object is truncated.
        output_token_budget = max(320, max_tokens * 4)
        cache_key = sha256(
            f"ollama-v1:{self.model}:{max_tokens}:{output_token_budget}:{self.num_ctx}"
            f"\0{query}\0{context}".encode()
        ).hexdigest()
        cached = llm_response_cache.get(cache_key)
        if cached is not None:
            return QalbuResponse.model_validate(cached)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"{context}\n\nUSER QUERY (untrusted):\n{query}",
                },
            ],
            "stream": False,
            "format": RESPONSE_SCHEMA,
            "options": {
                "temperature": 0.2,
                "num_predict": output_token_budget,
                "num_ctx": self.num_ctx,
            },
        }
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response: httpx.Response | None = None
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    response.raise_for_status()
                    break
                except httpx.HTTPError:
                    if attempt + 1 == self.max_retries:
                        raise
                    logger.warning(
                        "provider_retry provider=ollama model=%s attempt=%s",
                        self.model,
                        attempt + 1,
                    )
                    await asyncio.sleep(2**attempt)
            if response is None:
                raise RuntimeError("Ollama request produced no response")
            try:
                text = response.json()["message"]["content"]
                result = QalbuResponse.model_validate(json.loads(text))
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise ValueError("Ollama returned malformed structured output") from exc
            llm_response_cache.set(cache_key, result.model_dump())
            return result
        finally:
            if own_client:
                await client.aclose()
