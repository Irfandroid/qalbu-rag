from typing import Protocol

from app.models.quran import QuranDocument


class QuranDataProvider(Protocol):
    async def get_documents(self) -> list[QuranDocument]: ...

    async def get_document(
        self, surah_number: int, ayah_start: int, ayah_end: int | None = None
    ) -> QuranDocument | None: ...
