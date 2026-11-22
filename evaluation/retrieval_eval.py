"""Offline retrieval evaluation over the local Kemenag scrape.

Rebuilds the same parent/child rows the ingestion script writes, embeds the
children with the local Ollama embedding model, and searches them with the
production ``QuranRetriever`` logic in memory. No database and no external
embedding provider required.

    python -m evaluation.retrieval_eval             # cached embeddings
    python -m evaluation.retrieval_eval --refresh   # re-embed corpus + queries
    python -m evaluation.retrieval_eval --json out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.models.quran import QuranDocument
from app.models.rag import RetrievalResult
from app.providers.embeddings.ollama import OllamaEmbeddingProvider
from app.rag.query_processing import classify_intent, enrich_query
from app.rag.retriever import QuranRetriever
from scripts.kemenag.categories import category_index, load_category_manifest
from scripts.kemenag.documents import payload_to_document

ROOT = Path(__file__).resolve().parents[1]
RAW_SCRAPE = ROOT / "data/raw/kemenag_corpus_verses_scrape.json"
CORPUS_MANIFEST = ROOT / "data/manifests/kemenag_corpus_verses.json"
CASES_PATH = ROOT / "evaluation/retrieval_cases.json"
CACHE_PATH = ROOT / "evaluation/.cache/retrieval_embeddings.json"

CORPUS = "qalbu-kemenag-v1"
EMBED_BATCH = 16
EMBED_PAUSE_SECONDS = 2.0
# Ranking ceiling: no threshold, wide top-k, so misses can be split into
# "never ranked" versus "ranked but below the production cutoff".
CEILING_PARENT_K = 10
THRESHOLDS = (0.28, 0.32, 0.36, 0.40, 0.45)


def load_corpus() -> tuple[list[QuranDocument], list[dict[str, Any]], dict[str, str]]:
    """Rebuild documents and child chunks from the local scrape, as ingestion does."""
    manifest = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("corpus") != CORPUS:
        raise RuntimeError(f"Expected corpus {CORPUS}, found {manifest.get('corpus')}")
    raw = json.loads(RAW_SCRAPE.read_text(encoding="utf-8"))
    by_verse, _ = category_index(load_category_manifest())
    documents: list[QuranDocument] = []
    chunks: list[dict[str, Any]] = []
    for row in raw["responses"]:
        key = row["verse_key"]
        document, document_chunks = payload_to_document(
            key, row, manifest, by_verse.get(key, [])
        )
        documents.append(QuranDocument.model_validate(document))
        chunks.extend(document_chunks)
    verse_by_parent = {doc.id: doc.metadata["verse_keys"][0] for doc in documents}
    return documents, chunks, verse_by_parent


def load_cases() -> list[dict[str, Any]]:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return list(payload["cases"])


class LocalRepository:
    """In-memory cosine search with the same shape as ``match_quran_chunks``."""

    def __init__(
        self,
        documents: list[QuranDocument],
        chunks: list[dict[str, Any]],
        vectors: dict[str, list[float]],
    ) -> None:
        self.documents = {document.id: document for document in documents}
        self.chunks = chunks
        self.vectors = vectors

    async def match_chunks(self, embedding: list[float], top_k: int) -> list[RetrievalResult]:
        scored = sorted(
            (
                (_cosine(embedding, self.vectors[chunk["id"]]), chunk)
                for chunk in self.chunks
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        results: list[RetrievalResult] = []
        for score, chunk in scored[:top_k]:
            document = self.documents[chunk["parent_id"]]
            results.append(
                RetrievalResult(
                    child_id=chunk["id"],
                    parent_id=chunk["parent_id"],
                    score=score,
                    chunk_type=chunk["chunk_type"],
                    surah_number=document.surah_number,
                    surah_name=document.surah_name,
                    ayah_start=document.ayah_start,
                    ayah_end=document.ayah_end,
                )
            )
        return results

    async def get_documents(self, ids: list[str]) -> list[QuranDocument]:
        return [self.documents[item] for item in ids if item in self.documents]


class CachedEmbeddings:
    """Wrap the Ollama provider with the on-disk cache used by this script."""

    def __init__(self, inner: OllamaEmbeddingProvider, cache: dict[str, Any]) -> None:
        self.inner = inner
        self.cache = cache
        self.dirty = False

    @property
    def model(self) -> str:
        return self.inner.model

    async def embed_query(self, text: str) -> list[float]:
        key = sha256(text.encode()).hexdigest()
        queries = self.cache.setdefault("queries", {})
        if key not in queries:
            for attempt in range(6):
                try:
                    queries[key] = await self.inner.embed_query(text)
                    break
                except RuntimeError:
                    if attempt == 5:
                        raise
                    await asyncio.sleep(15 * 2**attempt)
            self.dirty = True
        return queries[key]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self.inner.embed_documents(texts)


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def recall_at(ranked: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 0.0
    return len(set(ranked[:k]) & set(expected)) / len(expected)


def reciprocal_rank(ranked: list[str], expected: list[str]) -> float:
    for rank, verse in enumerate(ranked, start=1):
        if verse in expected:
            return 1.0 / rank
    return 0.0


def ndcg_at(ranked: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 0.0
    gains = [1.0 if verse in expected else 0.0 for verse in ranked[:k]]
    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal = sum(1 / math.log2(index + 2) for index in range(min(len(expected), k)))
    return dcg / ideal


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


async def _embed_missing_chunks(
    chunks: list[dict[str, Any]],
    provider: OllamaEmbeddingProvider,
    cache: dict[str, Any],
    refresh: bool,
) -> None:
    vectors = cache.setdefault("chunks", {})
    missing = [chunk for chunk in chunks if chunk["id"] not in vectors]
    if refresh:
        missing = list(chunks)
    for start in range(0, len(missing), EMBED_BATCH):
        batch = missing[start : start + EMBED_BATCH]
        embedded = await _embed_with_backoff(
            provider, [chunk["content"] for chunk in batch]
        )
        vectors.update(
            {chunk["id"]: vector for chunk, vector in zip(batch, embedded, strict=True)}
        )
        # Persist progress: free-tier rate limits routinely interrupt a cold run.
        _save_cache(cache)
        done = min(start + EMBED_BATCH, len(missing))
        print(f"embedded {done}/{len(missing)} chunks")
        if done < len(missing):
            await asyncio.sleep(EMBED_PAUSE_SECONDS)


async def _embed_with_backoff(
    provider: OllamaEmbeddingProvider, texts: list[str], attempts: int = 6
) -> list[list[float]]:
    for attempt in range(attempts):
        try:
            return await provider.embed_documents(texts)
        except RuntimeError:
            if attempt + 1 == attempts:
                raise
            delay = 15 * 2**attempt
            print(f"ollama unavailable or overloaded; retrying in {delay}s")
            await asyncio.sleep(delay)
    raise RuntimeError("Ollama embedding retries exhausted")



def _load_cache(model: str) -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {"model": model, "chunks": {}, "queries": {}}
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if cache.get("model") != model:
        return {"model": model, "chunks": {}, "queries": {}}
    return cache


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")


async def evaluate(refresh: bool = False) -> dict[str, Any]:
    settings = get_settings()
    documents, chunks, verse_by_parent = load_corpus()
    cache = _load_cache(settings.ollama_embedding_model)
    cache_preloaded = bool(cache["chunks"]) and not refresh
    inner = OllamaEmbeddingProvider(
        settings.ollama_base_url,
        settings.ollama_embedding_model,
        settings.embedding_dimensions,
        settings.request_timeout_seconds,
    )
    await _embed_missing_chunks(chunks, inner, cache, refresh)
    if refresh:
        cache["queries"] = {}
    embeddings = CachedEmbeddings(inner, cache)
    repository = LocalRepository(documents, chunks, cache["chunks"])

    def retriever(min_score: float, parent_k: int) -> QuranRetriever:
        return QuranRetriever(
            embeddings, repository, min_score, settings.top_k_retrieval, parent_k
        )

    production = retriever(settings.min_retrieval_score, settings.retrieval_parent_k)
    ceiling = retriever(0.0, CEILING_PARENT_K)

    cases = load_cases()
    # Warm query vectors first so latency reflects retrieval, not Ollama round trips.
    for case in cases:
        if classify_intent(case["query"]).requires_quran:
            await embeddings.embed_query(enrich_query(case["query"])[0])
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in cases:
        query = case["query"]
        expected = case["expected"]
        routed = classify_intent(query).requires_quran
        started = time.perf_counter()
        results = await production.search(query) if routed else []
        if routed:
            latencies.append((time.perf_counter() - started) * 1000)
        ranked = [verse_by_parent[result.parent_id] for result in results]
        wide = (
            [verse_by_parent[result.parent_id] for result in await ceiling.search(query)]
            if routed
            else []
        )
        rows.append(
            {
                "query": query,
                "expected": expected,
                "routed_to_retrieval": routed,
                "ranked": ranked,
                "wide_ranked": wide,
                "scores": [round(result.score, 4) for result in results],
                "winning_chunk_types": [result.chunk_type for result in results],
                "recall_at_1": recall_at(ranked, expected, 1),
                "recall_at_4": recall_at(ranked, expected, 4),
                "mrr": reciprocal_rank(ranked, expected),
                "ndcg_at_4": ndcg_at(ranked, expected, 4),
                "wide_recall_at_10": recall_at(wide, expected, CEILING_PARENT_K),
                "wide_mrr": reciprocal_rank(wide, expected),
            }
        )

    grounded = [row for row in rows if row["expected"]]
    refusals = [row for row in rows if not row["expected"]]
    # Retrieval quality only makes sense where routing actually called retrieval;
    # queries routed away are an end-to-end (routing) failure, not a ranking one.
    retrieved = [row for row in grounded if row["routed_to_retrieval"]]
    routed_away = [row["query"] for row in grounded if not row["routed_to_retrieval"]]
    summary = {
        "corpus": {
            "documents": len(documents),
            "chunks": len(chunks),
            "chunk_types": {
                name: sum(chunk["chunk_type"] == name for chunk in chunks)
                for name in ("arabic", "translation", "tafsir", "themes")
            },
            "tafsir_coverage": round(
                sum(bool(document.tafsir) for document in documents) / len(documents), 3
            ),
        },
        "config": {
            "model": settings.ollama_embedding_model,
            "min_score": settings.min_retrieval_score,
            "candidate_k": settings.top_k_retrieval,
            "parent_k": settings.retrieval_parent_k,
            "corpus_vectors_cached": cache_preloaded,
        },
        "cases": {"grounded": len(grounded), "refusal": len(refusals)},
        "retrieval": {
            "cases": len(retrieved),
            "recall_at_1": _mean([row["recall_at_1"] for row in retrieved]),
            "recall_at_4": _mean([row["recall_at_4"] for row in retrieved]),
            "mrr": _mean([row["mrr"] for row in retrieved]),
            "ndcg_at_4": _mean([row["ndcg_at_4"] for row in retrieved]),
            "empty_rate": round(
                sum(not row["ranked"] for row in retrieved) / max(len(retrieved), 1), 3
            ),
            "latency_p50_ms": round(_percentile(latencies, 0.5), 1),
            "latency_p95_ms": round(_percentile(latencies, 0.95), 1),
        },
        "end_to_end": {
            "recall_at_4": _mean([row["recall_at_4"] for row in grounded]),
            "routed_away": len(routed_away),
            "routed_away_queries": routed_away,
        },
        "ceiling": {
            "recall_at_10": _mean([row["wide_recall_at_10"] for row in retrieved]),
            "mrr": _mean([row["wide_mrr"] for row in retrieved]),
            "empty_rate": round(
                sum(not row["wide_ranked"] for row in retrieved) / max(len(retrieved), 1),
                3,
            ),
        },
        "routing": {
            "grounded_routed": f"{len(retrieved)}/{len(grounded)}",
            "refusals_routed_away": f"{sum(not row['routed_to_retrieval'] for row in refusals)}"
            f"/{len(refusals)}",
        },
        "threshold_sweep": {},
    }

    for threshold in THRESHOLDS:
        sweep = retriever(threshold, settings.retrieval_parent_k)
        recalls, empties = [], []
        for row in retrieved:
            results = await sweep.search(row["query"])
            ranked = [verse_by_parent[result.parent_id] for result in results]
            recalls.append(recall_at(ranked, row["expected"], 4))
            empties.append(not ranked)
        summary["threshold_sweep"][str(threshold)] = {
            "recall_at_4": _mean(recalls),
            "empty_rate": round(sum(empties) / len(empties), 3),
        }

    if embeddings.dirty:
        _save_cache(cache)

    return {
        "summary": summary,
        "cases": rows,
        "misses": [
            {
                "query": row["query"],
                "expected": row["expected"],
                "ranked": row["ranked"],
                "reason": "routed_away" if not row["routed_to_retrieval"] else "not_retrieved",
            }
            for row in grounded
            if not row["recall_at_4"]
        ],
    }


def _print_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    corpus = summary["corpus"]
    retrieval = summary["retrieval"]
    end_to_end = summary["end_to_end"]
    ceiling = summary["ceiling"]
    print(
        f"corpus: {corpus['documents']} documents, {corpus['chunks']} chunks, "
        f"tafsir coverage {corpus['tafsir_coverage']:.0%}"
    )
    print("chunks:", corpus["chunk_types"])
    print(
        f"retrieval ({retrieval['cases']} routed cases): recall@1={retrieval['recall_at_1']} "
        f"recall@4={retrieval['recall_at_4']} mrr={retrieval['mrr']} "
        f"ndcg@4={retrieval['ndcg_at_4']} empty={retrieval['empty_rate']} "
        f"p50={retrieval['latency_p50_ms']}ms p95={retrieval['latency_p95_ms']}ms"
    )
    print(
        f"end_to_end: recall@4={end_to_end['recall_at_4']} "
        f"routed_away={end_to_end['routed_away']} {end_to_end['routed_away_queries']}"
    )
    print(
        f"ceiling: recall@10={ceiling['recall_at_10']} mrr={ceiling['mrr']} "
        f"empty={ceiling['empty_rate']}"
    )
    print("routing:", summary["routing"])
    print("threshold sweep:", summary["threshold_sweep"])
    for miss in report["misses"]:
        print(
            f"miss[{miss['reason']}]: {miss['query']} "
            f"expected={miss['expected']} ranked={miss['ranked']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-embed corpus and queries")
    parser.add_argument("--json", type=Path, help="write the full report to this path")
    args = parser.parse_args()
    report = asyncio.run(evaluate(refresh=args.refresh))
    _print_report(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"report: {args.json}")


if __name__ == "__main__":
    main()
