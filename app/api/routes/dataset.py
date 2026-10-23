from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import (
    get_daily_verse_document,
    get_dataset_child_counts,
    get_dataset_document,
)
from app.core.config import get_settings
from app.quran.catalog import CORPUS, build_catalog, daily_date_in_timezone
from app.rag.citation_validator import CitationValidator

router = APIRouter(tags=["dataset"])


def _document_payload(document) -> dict:
    verse_key = f"{document.surah_number}:{document.ayah_start}"
    return {
        **document.model_dump(mode="json"),
        "verse_key": verse_key,
        "detail_url": f"/dataset/verse/{document.surah_number}/{document.ayah_start}",
        "source_status": CitationValidator._source_status(document),
    }


@router.get("/api/v1/dataset/verse-of-day")
async def verse_of_day(document=Depends(get_daily_verse_document)) -> dict:  # noqa: B008
    payload = _document_payload(document)
    return {
        "date": daily_date_in_timezone().isoformat(),
        "timezone": "Asia/Jakarta",
        "verse_key": payload["verse_key"],
        "surah_number": payload["surah_number"],
        "surah_name": payload["surah_name"],
        "ayah_number": payload["ayah_start"],
        "translation": payload["translation"],
        "detail_url": payload["detail_url"],
        "source_status": payload["source_status"],
    }


@router.get("/api/v1/dataset/verses/{surah}/{ayah}")
async def dataset_verse_detail(document=Depends(get_dataset_document)) -> dict:  # noqa: B008
    return _document_payload(document)


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
