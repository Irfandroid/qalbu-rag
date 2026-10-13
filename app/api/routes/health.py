from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "rag": "configured" if settings.configured_for_rag else "configuration_required",
        "corpus": settings.quran_corpus,
    }
