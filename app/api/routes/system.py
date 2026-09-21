import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["system"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]


@router.get("/health")
async def health_v1() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "profile": settings.qalbu_profile,
        "rag": "configured" if settings.configured_for_rag else "configuration_required",
    }


@router.get("/ready")
async def ready() -> dict[str, Any]:
    settings = get_settings()
    checks = {
        "rag_configuration": settings.configured_for_rag,
        "crisis_contact_verified": bool(settings.crisis_line),
    }
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "note": None if checks["crisis_contact_verified"] else "CRISIS_LINE belum diverifikasi.",
    }


@router.get("/sources")
async def sources() -> dict[str, Any]:
    tafsir_root = PROJECT_ROOT / "data" / "external" / "quran-tafseer" / "raw"
    quran_com_snapshot = (
        PROJECT_ROOT / "data" / "external" / "quran-com" / "saheeh-international.json"
    )
    temporary_quran = PROJECT_ROOT / "data" / "temporary" / "quran.json"
    files = list(tafsir_root.glob("*.json")) if tafsir_root.exists() else []
    available_surahs = {
        int(path.stem[:3]) for path in files if len(path.stem) >= 3 and path.stem[:3].isdigit()
    }
    missing_surahs = sorted(set(range(1, 115)) - available_surahs)
    quran_com_data = (
        json.loads(quran_com_snapshot.read_text(encoding="utf-8"))
        if quran_com_snapshot.exists()
        else None
    )
    sources_data = [
        {
            "id": "quran-com-english-snapshot",
            "label": "Quran.com Arabic and English translation snapshot",
            "status": "available" if quran_com_data else "missing",
            "ayahs": len(quran_com_data["verses"]) if quran_com_data else 0,
            "surahs_available": len(quran_com_data["chapters"]) if quran_com_data else 0,
            "translation": "Saheeh International",
            "translation_language": "en",
            "official_kemenag": False,
        },
        {
            "id": "community-quran-tafseer",
            "label": "Arabic tafsir, community dataset",
            "status": "unverified_community_source",
            "surahs_available": len(available_surahs),
            "surahs_expected": 114,
            "missing_surahs": missing_surahs,
            "complete": not missing_surahs,
            "official_kemenag": False,
        },
        {
            "id": "temporary-reference",
            "label": "Dataset referensi sementara",
            "status": "available" if temporary_quran.exists() else "missing",
            "official_kemenag": False,
        },
    ]
    return {"sources": sources_data}


@router.get("/eval/report")
async def evaluation_report() -> dict[str, Any]:
    report_path = PROJECT_ROOT / "evaluation" / "report.json"
    if not report_path.exists():
        return {"status": "not_measured", "metrics": None}
    return {"status": "measured", **json.loads(report_path.read_text(encoding="utf-8"))}


@router.get("/config/public")
async def public_config() -> dict[str, Any]:
    settings = get_settings()
    model = settings.ollama_model if settings.llm_provider == "ollama" else settings.groq_model
    return {
        "profile": settings.qalbu_profile,
        "model": model,
        "llm_provider": settings.llm_provider,
        "message_max_length": 500,
        "response_max_tokens": 72,
        "safety": "strict",
        "crisis_line_label": settings.crisis_line_label,
        "crisis_contact_verified": bool(settings.crisis_line),
    }
