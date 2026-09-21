from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "rag": "configured" if get_settings().configured_for_rag else "configuration_required",
    }
