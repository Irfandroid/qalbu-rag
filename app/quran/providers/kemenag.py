from app.models.quran import QuranDocument


class KemenagQuranProvider:
    """Adapter boundary. Implement only after official endpoint/schema is supplied."""

    async def get_documents(self) -> list[QuranDocument]:
        raise NotImplementedError(
            "Kemenag adapter needs official API documentation and credentials"
        )

    async def get_document(
        self, surah_number: int, ayah_start: int, ayah_end: int | None = None
    ) -> QuranDocument | None:
        raise NotImplementedError(
            "Kemenag adapter needs official API documentation and credentials"
        )
