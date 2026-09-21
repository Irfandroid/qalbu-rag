from typing import Protocol

from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult


class QuranRepository(Protocol):
    async def match_chunks(self, embedding: list[float], top_k: int) -> list[RetrievalResult]: ...

    async def get_documents(self, ids: list[str]) -> list[QuranDocument]: ...
