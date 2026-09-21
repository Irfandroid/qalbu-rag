"""Dataset catalogue. Kemenag can replace or augment this snapshot later."""

from app.models.quran import QuranDocument
from app.quran.providers.quran_com_english import QuranComEnglishProvider


async def get_active_documents() -> list[QuranDocument]:
    """Complete Arabic + English parents, optionally enriched with local Arabic tafsir."""
    return await QuranComEnglishProvider().get_documents()
