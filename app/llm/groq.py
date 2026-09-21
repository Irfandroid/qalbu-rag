import json
from hashlib import sha256

import httpx

from app.core.cache import llm_response_cache
from app.llm.prompts import SYSTEM_PROMPT
from app.models.chat import QalbuResponse


class GroqProvider:
    """Groq OpenAI-compatible chat endpoint, server-side only."""

    def __init__(self, api_key: str, model: str = "openai/gpt-oss-20b") -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, query: str, context: str, max_tokens: int = 120) -> QalbuResponse:
        cache_key = sha256(
            f"groq:{self.model}:{max_tokens}\0{query}\0{context}".encode()
        ).hexdigest()
        cached = llm_response_cache.get(cache_key)
        if cached is not None:
            return QalbuResponse.model_validate(cached)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{context}\n\nUser: {query}"},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        try:
            text = response.json()["choices"][0]["message"]["content"]
            result = QalbuResponse.model_validate(json.loads(text))
            llm_response_cache.set(cache_key, result.model_dump())
            return result
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Groq returned malformed structured output") from exc
