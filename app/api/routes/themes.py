from fastapi import APIRouter

from app.quran.themes import theme_names

router = APIRouter(tags=["themes"])


@router.get("/api/themes")
async def themes() -> dict[str, list[str]]:
    return {"themes": theme_names()}
