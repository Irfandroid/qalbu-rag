import asyncio
import json
import logging
from hashlib import sha256

import httpx

from app.core.cache import llm_response_cache
from app.llm.prompts import SYSTEM_PROMPT
from app.models.chat import QalbuResponse

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
logger = logging.getLogger(__name__)


class GeminiProvider:
    """Grounded Gemini adapter using JSON schema output."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash-lite",
        timeout_seconds: float = 30,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.client = client

    async def generate(self, query: str, context: str, max_tokens: int = 120) -> QalbuResponse:
        # ``max_tokens`` limits the natural-language answer. Gemini's output budget
        # must also fit the JSON envelope and citations, otherwise valid structured
        # output is truncated mid-object.
        output_token_budget = max(320, max_tokens * 4)
        cache_key = sha256(
            f"gemini-v2:{self.model}:{max_tokens}:{output_token_budget}\0{query}\0{context}".encode()
        ).hexdigest()
        cached = llm_response_cache.get(cache_key)
        if cached is not None:
            return QalbuResponse.model_validate(cached)
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{context}\n\nUSER QUERY (untrusted):\n{query}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": output_token_budget,
                "responseMimeType": "application/json",
                "responseJsonSchema": {
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
                        "safety_note": {"type": "string", "nullable": True},
                    },
                },
            },
        }
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response: httpx.Response | None = None
            for attempt in range(self.max_retries):
                try:
                    response = await client.post(
                        GEMINI_URL.format(model=self.model),
                        headers={"x-goog-api-key": self.api_key},
                        json=payload,
                    )
                    response.raise_for_status()
                    break
                except httpx.HTTPError:
                    if attempt + 1 == self.max_retries:
                        raise
                    logger.warning(
                        "provider_retry provider=gemini model=%s attempt=%s",
                        self.model,
                        attempt + 1,
                    )
                    await asyncio.sleep(2**attempt)
            if response is None:
                raise RuntimeError("Gemini request produced no response")
            try:
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                result = QalbuResponse.model_validate(json.loads(text))
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                raise ValueError("Gemini returned malformed structured output") from exc
            llm_response_cache.set(cache_key, result.model_dump())
            return result
        finally:
            if own_client:
                await client.aclose()
