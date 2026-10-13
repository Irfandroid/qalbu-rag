from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_dataset_child_counts
from app.core.config import get_settings
from app.quran.catalog import CORPUS, build_catalog

router = APIRouter(tags=["dataset"])


@router.get("/api/v1/dataset/verses")
def list_dataset_verses(
    search: str | None = Query(default=None, max_length=100),
    surah: int | None = Query(default=None, ge=1, le=114),
    category: str | None = Query(default=None, max_length=80),
    child_counts: dict[str, int] | None = Depends(get_dataset_child_counts),  # noqa: B008
) -> dict:
    settings = get_settings()
    if settings.quran_corpus != CORPUS:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATASET_CATALOG_UNAVAILABLE",
                "message": f"Dataset catalog requires active corpus {CORPUS}.",
            },
        )
    catalog = build_catalog(child_counts)
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
