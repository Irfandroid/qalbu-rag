from typing import Protocol

from app.models.chat import QalbuResponse


class LLMProvider(Protocol):
    async def generate(self, query: str, context: str, max_tokens: int = 120) -> QalbuResponse: ...
