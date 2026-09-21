from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult
from app.quran.repository import QuranRepository


class ParentRetriever:
    def __init__(self, repository: QuranRepository) -> None:
        self.repository = repository

    async def get_parents(self, results: list[RetrievalResult]) -> list[QuranDocument]:
        parent_ids = list(dict.fromkeys(result.parent_id for result in results))
        return await self.repository.get_documents(parent_ids)
