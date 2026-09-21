import json
import re
from hashlib import sha256

import httpx

from app.core.cache import llm_response_cache
from app.llm.prompts import SYSTEM_PROMPT
from app.models.chat import QalbuDraft, QalbuResponse, QuranReference


class OllamaProvider:
    """Local Ollama chat provider. No API key leaves the host."""

    def __init__(
        self, base_url: str, model: str, num_ctx: int = 2048, keep_alive: str = "5m"
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive

    async def generate(self, query: str, context: str, max_tokens: int = 120) -> QalbuResponse:
        cache_key = sha256(
            f"ollama:grounded-v9:{self.model}:{max_tokens}\0{query}\0{context}".encode()
        ).hexdigest()
        cached = llm_response_cache.get(cache_key)
        if cached is not None:
            return self._attach_single_context_reference(
                QalbuResponse.model_validate(cached), context
            )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\nUser: {query}"},
        ]
        # `max_tokens` caps user-facing prose, while structured JSON needs room
        # for citation IDs and closing syntax. Without this overhead Qwen can
        # truncate otherwise valid JSON before CitationValidator gets it.
        output_budget = min(max_tokens + 128, 256)
        payload = {
            "model": self.model,
            "stream": False,
            "format": QalbuDraft.model_json_schema(),
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.0,
                "num_ctx": self.num_ctx,
                "num_predict": output_budget,
            },
            "messages": messages,
        }
        for attempt in range(2):
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
            try:
                text = response.json()["message"]["content"]
                draft = QalbuDraft.model_validate(json.loads(text))
                result = self._attach_single_context_reference(
                    QalbuResponse.model_validate(draft.model_dump()), context
                )
                result = result.model_copy(update={"safety_note": None})
                llm_response_cache.set(cache_key, result.model_dump())
                return result
            except (KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
                if attempt:
                    raise ValueError("Ollama returned malformed structured output") from exc
                payload["messages"] = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "Return only JSON matching supplied schema. No markdown or extra keys."
                        ),
                    },
                ]
        raise RuntimeError("Unreachable Ollama response state")

    @staticmethod
    def _attach_single_context_reference(
        response: QalbuResponse, context: str
    ) -> QalbuResponse:
        """Recover an omitted ID only for one unambiguous retrieved source."""
        if response.references:
            return response
        parent_ids = list(dict.fromkeys(re.findall(r"^PARENT_ID:\s*(\S+)$", context, re.MULTILINE)))
        if len(parent_ids) != 1:
            return response
        return response.model_copy(
            update={
                "references": [QuranReference(parent_id=parent_ids[0])]
            }
        )
