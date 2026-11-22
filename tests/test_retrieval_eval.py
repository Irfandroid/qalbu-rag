import math

import pytest

from app.models.quran import QuranDocument
from evaluation.retrieval_eval import (
    LocalRepository,
    load_cases,
    load_corpus,
    ndcg_at,
    recall_at,
    reciprocal_rank,
)


def test_recall_mrr_and_ndcg_match_known_rankings():
    ranked = ["1:1", "2:2", "3:3"]
    assert recall_at(ranked, ["2:2"], 1) == 0.0
    assert recall_at(ranked, ["2:2", "3:3"], 2) == 0.5
    assert recall_at(ranked, ["2:2", "3:3"], 3) == 1.0
    assert reciprocal_rank(ranked, ["3:3"]) == pytest.approx(1 / 3)
    assert reciprocal_rank(ranked, ["9:9"]) == 0.0
    assert ndcg_at(ranked, ["2:2"], 3) == pytest.approx(1 / math.log2(3))
    assert ndcg_at(ranked, ["1:1", "2:2"], 2) == 1.0


async def test_local_repository_orders_children_by_cosine_and_keeps_metadata():
    documents = [
        QuranDocument(
            id="corpus-001-001",
            surah_number=1,
            surah_name="Al-Fatihah",
            ayah_start=1,
            ayah_end=1,
            source={"quran": "test"},
            metadata={"verse_keys": ["1:1"]},
        ),
        QuranDocument(
            id="corpus-002-001",
            surah_number=2,
            surah_name="Al-Baqarah",
            ayah_start=1,
            ayah_end=1,
            source={"quran": "test"},
            metadata={"verse_keys": ["2:1"]},
        ),
    ]
    chunks = [
        {"id": "a", "parent_id": "corpus-001-001", "chunk_type": "tafsir", "content": ""},
        {"id": "b", "parent_id": "corpus-002-001", "chunk_type": "translation", "content": ""},
    ]
    repository = LocalRepository(documents, chunks, {"a": [1.0, 0.0], "b": [0.0, 1.0]})

    results = await repository.match_chunks([0.9, 0.1], 10)

    assert [result.parent_id for result in results] == ["corpus-001-001", "corpus-002-001"]
    assert results[0].chunk_type == "tafsir"
    assert results[0].score == pytest.approx(0.9939, abs=1e-4)


def test_local_corpus_rebuilds_every_verse_with_tafsir():
    documents, chunks, verse_by_parent = load_corpus()

    assert len(documents) == 282
    assert len(verse_by_parent) == 282
    assert all(document.tafsir and document.translation for document in documents)
    assert {chunk["chunk_type"] for chunk in chunks} <= {
        "arabic",
        "translation",
        "tafsir",
        "themes",
    }


def test_every_label_is_answerable_in_the_local_corpus():
    _, _, verse_by_parent = load_corpus()
    corpus_keys = set(verse_by_parent.values())
    cases = load_cases()

    assert len(cases) >= 30
    assert len({case["query"] for case in cases}) == len(cases)
    grounded = [case for case in cases if case["expected"]]
    refusals = [case for case in cases if not case["expected"]]
    assert grounded and refusals
    for case in grounded:
        assert 1 <= len(case["expected"]) <= 3, case["query"]
        assert set(case["expected"]) <= corpus_keys, case["query"]
