from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult


class SupabaseQuranRepository:
    def __init__(self, client, corpus: str = "qalbu-seed-v1") -> None:
        self.client = client
        self.corpus = corpus

    async def match_chunks(self, embedding: list[float], top_k: int) -> list[RetrievalResult]:
        result = await self.client.rpc(
            "match_quran_chunks",
            {
                "query_embedding": embedding,
                "match_count": top_k,
                "corpus_filter": self.corpus,
            },
        ).execute()
        return [RetrievalResult.model_validate(row) for row in result.data]

    async def get_documents(self, ids: list[str]) -> list[QuranDocument]:
        if not ids:
            return []
        result = (
            await self.client.table("quran_documents")
            .select("*")
            .eq("corpus", self.corpus)
            .in_("id", ids)
            .execute()
        )
        docs = [QuranDocument.model_validate(row) for row in result.data]
        by_id = {doc.id: doc for doc in docs}
        return [by_id[document_id] for document_id in ids if document_id in by_id]
