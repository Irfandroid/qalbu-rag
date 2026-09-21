"""Read complete build-time Quran.com snapshot with attributed English translation."""

import html
import json
import re
from pathlib import Path

from app.models.quran import QuranDocument

SNAPSHOT_PATH = Path("data/external/quran-com/saheeh-international.json")
TAFSIR_ROOT = Path("data/external/quran-tafseer/raw")
SOURCE_URL = "https://quran.com"
TAFSIR_SOURCE_URL = (
    "https://www.kaggle.com/datasets/abdelrahmanahmed110/quranic-ayahs-with-tafseer-json-dataset"
)
TAFSIR_PREFERENCE = ("التفسير المختصر", "default", "تفسير السعدي", "تفسير الجلالين")


def plain_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    return " ".join(html.unescape(without_tags).split())


class QuranComEnglishProvider:
    """One complete ayah parent; search children point back to this record."""

    def __init__(
        self,
        snapshot_path: Path | None = None,
        tafsir_root: Path | None = None,
    ) -> None:
        self.snapshot_path = snapshot_path or SNAPSHOT_PATH
        self.tafsir_root = tafsir_root or TAFSIR_ROOT

    def _tafsir_by_key(self) -> dict[str, tuple[str, str]]:
        tafsir: dict[str, tuple[str, str]] = {}
        if not self.tafsir_root.exists():
            return tafsir
        for path in sorted(self.tafsir_root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            surah_number = int(data["number"])
            for ayah in data["ayahs"]:
                items = ayah.get("tafsir", [])
                selected = next(
                    (item for kind in TAFSIR_PREFERENCE for item in items if item["type"] == kind),
                    None,
                )
                if selected:
                    key = f"{surah_number}:{int(ayah['ayah_number'])}"
                    tafsir[key] = (selected["text"].strip(), selected["type"])
        return tafsir

    async def get_documents(self) -> list[QuranDocument]:
        if not self.snapshot_path.exists():
            raise FileNotFoundError(
                f"Quran.com snapshot missing at {self.snapshot_path}. "
                "Run `python scripts/fetch_quran_com.py`."
            )
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        chapters = {int(item["id"]): item for item in payload["chapters"]}
        tafsir = self._tafsir_by_key()
        documents: list[QuranDocument] = []
        for verse in payload["verses"]:
            surah_number, ayah_number = (int(value) for value in verse["verse_key"].split(":"))
            tafsir_entry = tafsir.get(verse["verse_key"])
            documents.append(
                QuranDocument(
                    id=f"quran-com-en-{surah_number:03d}-{ayah_number:03d}",
                    surah_number=surah_number,
                    surah_name=chapters[surah_number]["name_simple"],
                    ayah_start=ayah_number,
                    ayah_end=ayah_number,
                    arabic_text=verse["text_uthmani"],
                    translation=plain_text(verse["translation"]),
                    tafsir=tafsir_entry[0] if tafsir_entry else None,
                    source={
                        "quran": "Quran.com Uthmani text",
                        "translation": "Saheeh International, Quran.com resource 20",
                        "tafsir": (
                            f"Community Kaggle mirror: {tafsir_entry[1]}"
                            if tafsir_entry
                            else "not available"
                        ),
                    },
                    metadata={
                        "source_provider": "quran_com_english_snapshot",
                        "source_url": SOURCE_URL,
                        "translation_language": "en",
                        "translation_resource_id": 20,
                        "translation_name": "Saheeh International",
                        "translation_verified_source": True,
                        "tafsir_source_url": TAFSIR_SOURCE_URL if tafsir_entry else None,
                        "tafsir_language": "ar" if tafsir_entry else None,
                        "tafsir_name": tafsir_entry[1] if tafsir_entry else None,
                        "tafsir_unverified_community_source": bool(tafsir_entry),
                        "snapshot_sha256": payload["source"].get("content_sha256"),
                    },
                )
            )
        if len(documents) != 6236:
            raise RuntimeError(f"Expected 6236 ayah parents, found {len(documents)}")
        return documents
