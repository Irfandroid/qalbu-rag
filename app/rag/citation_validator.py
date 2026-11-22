"""Trust boundary: citations and evidence may only come from retrieved rows."""

from app.models.chat import QalbuResponse, QuranEvidence, QuranReference
from app.models.quran import QuranDocument


def source_status(document: QuranDocument) -> str:
    """Human-readable provenance label shown next to a verse."""
    metadata = document.metadata
    if metadata.get("unverified_community_source"):
        return "Dataset komunitas; bukan sumber resmi Kemenag."
    if is_official_kemenag(metadata):
        return "Sumber: API Al-Qur'an Kemenag · LPMQ Kementerian Agama RI."
    return "Sumber terverifikasi dalam basis pengetahuan Qalbu."


def is_official_kemenag(metadata: dict) -> bool:
    return metadata.get("source_provider") == "official_portal" and (
        "kementerian agama" in str(metadata.get("source_authority", "")).casefold()
    )


class CitationValidator:
    def validate(
        self,
        response: QalbuResponse,
        retrieved: list[QuranDocument],
    ) -> QalbuResponse:
        allowed = {document.id: document for document in retrieved}
        valid = [
            self._canonical_reference(allowed[reference.parent_id])
            for reference in response.references
            if self._citation_matches_parent(reference, allowed.get(reference.parent_id))
        ]
        evidence = [
            self._build_evidence(reference, allowed[reference.parent_id])
            for reference in valid
        ]
        return response.model_copy(
            update={
                "references": valid,
                "evidence": evidence,
                "safety_note": self._safety_note(response, valid, allowed),
            }
        )

    @staticmethod
    def _canonical_reference(document: QuranDocument) -> QuranReference:
        return QuranReference(
            parent_id=document.id,
            surah_number=document.surah_number,
            surah_name=document.surah_name,
            ayah_start=document.ayah_start,
            ayah_end=document.ayah_end,
        )

    @staticmethod
    def _citation_matches_parent(
        reference: QuranReference, document: QuranDocument | None
    ) -> bool:
        """A missing field is completed from the parent; a conflicting one rejects it."""
        if document is None:
            return False
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
        return all(
            value is None or value == expected
            for value, expected in zip(supplied, canonical, strict=True)
        )

    @staticmethod
    def _build_evidence(
        reference: QuranReference, document: QuranDocument
    ) -> QuranEvidence:
        return QuranEvidence(
            parent_id=document.id,
            surah_number=document.surah_number,
            surah_name=document.surah_name,
            ayah_start=document.ayah_start,
            ayah_end=document.ayah_end,
            arabic_text=document.arabic_text,
            translation=document.translation,
            translation_language=document.metadata.get("translation_language", "id"),
            translation_name=document.metadata.get("translation_name")
            or "Terjemahan Indonesia",
            tafsir=document.tafsir,
            source_status=source_status(document),
        )

    @staticmethod
    def _safety_note(
        response: QalbuResponse,
        valid: list[QuranReference],
        allowed: dict[str, QuranDocument],
    ) -> str | None:
        uses_community_data = any(
            allowed[reference.parent_id].metadata.get("unverified_community_source")
            or allowed[reference.parent_id].metadata.get(
                "tafsir_unverified_community_source"
            )
            for reference in valid
        )
        if valid and uses_community_data:
            return (
                "Rujukan berasal dari dataset komunitas nonresmi. "
                "Verifikasi terjemahan dan tafsir melalui sumber resmi atau ahli tepercaya."
            )
        return response.safety_note
