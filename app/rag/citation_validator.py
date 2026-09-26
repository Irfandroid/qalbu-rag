from app.models.chat import QalbuResponse, QuranEvidence, QuranReference
from app.models.quran import QuranDocument


class CitationValidator:
    def validate(
        self,
        response: QalbuResponse,
        retrieved: list[QuranDocument],
    ) -> QalbuResponse:
        allowed = {document.id: document for document in retrieved}
        valid: list[QuranReference] = []
        for reference in response.references:
            document = allowed.get(reference.parent_id)
            if not document:
                continue
            supplied = (
                reference.surah_number,
                reference.surah_name,
                reference.ayah_start,
                reference.ayah_end,
            )
            canonical = (
                document.surah_number,
                document.surah_name,
                document.ayah_start,
                document.ayah_end,
            )
            # A missing field is completed only from the retrieved parent.
            # A supplied conflicting field rejects the citation outright.
            matches_parent = all(
                value is None or value == expected
                for value, expected in zip(supplied, canonical, strict=True)
            )
            if matches_parent:
                valid.append(
                    QuranReference(
                        parent_id=document.id,
                        surah_number=document.surah_number,
                        surah_name=document.surah_name,
                        ayah_start=document.ayah_start,
                        ayah_end=document.ayah_end,
                    )
                )
        evidence = [
            QuranEvidence(
                parent_id=reference.parent_id,
                surah_number=reference.surah_number,
                surah_name=reference.surah_name,
                ayah_start=reference.ayah_start,
                ayah_end=reference.ayah_end,
                arabic_text=allowed[reference.parent_id].arabic_text,
                translation=allowed[reference.parent_id].translation,
                translation_language=allowed[reference.parent_id].metadata.get(
                    "translation_language", "id"
                ),
                translation_name=(
                    allowed[reference.parent_id].metadata.get("translation_name")
                    or "Terjemahan Indonesia"
                ),
                tafsir=allowed[reference.parent_id].tafsir,
                source_status=(
                    "Dataset komunitas; bukan sumber resmi Kemenag."
                    if allowed[reference.parent_id].metadata.get("unverified_community_source")
                    else "Sumber terverifikasi dalam basis pengetahuan Qalbu."
                ),
            )
            for reference in valid
        ]
        safety_note = response.safety_note
        if valid and any(
            allowed[reference.parent_id].metadata.get("unverified_community_source")
            or allowed[reference.parent_id].metadata.get(
                "tafsir_unverified_community_source"
            )
            for reference in valid
        ):
            safety_note = (
                "Rujukan berasal dari dataset komunitas nonresmi. "
                "Verifikasi terjemahan dan tafsir melalui sumber resmi atau ahli tepercaya."
            )
        return response.model_copy(
            update={"references": valid, "evidence": evidence, "safety_note": safety_note}
        )
