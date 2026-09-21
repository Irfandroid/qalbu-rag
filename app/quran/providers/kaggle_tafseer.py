"""Read locally downloaded Kaggle Quran/tafsir JSON without treating it as official content."""

import json
from pathlib import Path

from app.models.quran import QuranDocument

DATASET_URL = (
    "https://www.kaggle.com/datasets/abdelrahmanahmed110/quranic-ayahs-with-tafseer-json-dataset"
)
SOURCE_LABEL = "Kaggle community mirror (CC0 listing; provenance not independently verified)"
TAFSIR_PREFERENCE = ("التفسير المختصر", "default", "تفسير السعدي", "تفسير الجلالين")


class KaggleTafseerProvider:
    """One parent per ayah from downloaded Arabic Quran and selected Arabic tafsir."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path("data/external/quran-tafseer/raw")

    async def get_documents(self) -> list[QuranDocument]:
        if not self.root.exists():
            raise FileNotFoundError(
                f"Kaggle tafsir data missing at {self.root}. "
                "Run the documented dataset download first."
            )
        documents: list[QuranDocument] = []
        for path in sorted(self.root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            surah_number = int(data["number"])
            file_number = int(path.name[:3])
            if surah_number != file_number:
                raise ValueError(f"Surah number mismatch in {path}")
            surah_name = path.stem[4:].replace("_", " ").title()
            for ayah in data["ayahs"]:
                tafsir_items = ayah.get("tafsir", [])
                selected = next(
                    (
                        item
                        for kind in TAFSIR_PREFERENCE
                        for item in tafsir_items
                        if item["type"] == kind
                    ),
                    None,
                )
                documents.append(
                    QuranDocument(
                        id=f"kaggle-tafseer-{surah_number:03d}-{int(ayah['ayah_number']):03d}",
                        surah_number=surah_number,
                        surah_name=surah_name,
                        ayah_start=int(ayah["ayah_number"]),
                        ayah_end=int(ayah["ayah_number"]),
                        arabic_text=ayah["text"].strip(),
                        tafsir=selected["text"].strip() if selected else None,
                        source={
                            "quran": SOURCE_LABEL,
                            "tafsir": selected["type"] if selected else "missing",
                        },
                        metadata={
                            "source_provider": "kaggle_tafseer",
                            "source_url": DATASET_URL,
                            "unverified_community_source": True,
                            "official_source": False,
                            "source_file": path.name,
                        },
                    )
                )
        return documents

    async def get_document(
        self, surah_number: int, ayah_start: int, ayah_end: int | None = None
    ) -> QuranDocument | None:
        end = ayah_end or ayah_start
        return next(
            (
                document
                for document in await self.get_documents()
                if (document.surah_number, document.ayah_start, document.ayah_end)
                == (surah_number, ayah_start, end)
            ),
            None,
        )
