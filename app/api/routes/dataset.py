from fastapi import APIRouter, Query

from app.quran.catalog import build_catalog

router = APIRouter(tags=["dataset"])


@router.get("/api/v1/dataset/verses")
def list_dataset_verses(
    search: str | None = Query(default=None, max_length=100),
    surah: int | None = Query(default=None, ge=1, le=114),
    category: str | None = Query(default=None, max_length=80),
) -> dict:
    catalog = build_catalog()
    normalized_search = search.strip().casefold() if search else ""
    verses = [
        verse
        for verse in catalog["verses"]
        if surah is None or verse["surah_number"] == surah
        if not normalized_search
        or normalized_search in verse["verse_key"].casefold()
        or normalized_search in verse["surah_name"].casefold()
        if category is None or any(item["id"] == category for item in verse["categories"])
    ]
    return {
        **{key: value for key, value in catalog.items() if key != "verses"},
        "matched_verses": len(verses),
        "verses": verses,
    }
