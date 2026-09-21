import csv
import json
from pathlib import Path

from app.models.quran import QuranDocument

TEMPORARY_REFERENCE_SOURCE = "[TEMPORARY USER-SUPPLIED REFERENCE: Kemenag content pending]"


class TemporaryQuranProvider:
    """Local metadata-only dataset. Never treats placeholders as scripture."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/temporary/quran.json")

    @property
    def references_path(self) -> Path:
        return self.path.with_name("mental_health_references.csv")

    async def get_documents(self) -> list[QuranDocument]:
        records = json.loads(self.path.read_text(encoding="utf-8"))
        docs = [QuranDocument.model_validate(record) for record in records]
        if self.references_path.exists():
            with self.references_path.open(encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    start, end = int(row["ayah_start"]), int(row["ayah_end"])
                    slug = row["surah_name"].lower().replace("'", "").replace(" ", "-")
                    reference = f"{row['surah_name']}:{start}" + (f"-{end}" if end != start else "")
                    docs.append(
                        QuranDocument(
                            id=f"sample-{slug}-{start}-{end}",
                            surah_number=int(row["surah_number"]),
                            surah_name=row["surah_name"],
                            ayah_start=start,
                            ayah_end=end,
                            themes=["mental-health", "temporary-reference-only", reference],
                            source={"quran": TEMPORARY_REFERENCE_SOURCE},
                            metadata={"temporary": True, "needs_official_content": True},
                        )
                    )
        return list({doc.id: doc for doc in docs}.values())

    async def get_document(
        self, surah_number: int, ayah_start: int, ayah_end: int | None = None
    ) -> QuranDocument | None:
        for document in await self.get_documents():
            if (document.surah_number, document.ayah_start, document.ayah_end) == (
                surah_number,
                ayah_start,
                ayah_end or ayah_start,
            ):
                return document
        return None
