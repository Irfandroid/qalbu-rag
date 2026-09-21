"""A/B benchmark local Ollama models against identical grounded Qalbu cases."""

import asyncio
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.dependencies import get_rag  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.rag.context_builder import build_context  # noqa: E402
from evaluation.evaluate import criterion, evaluate_case  # noqa: E402

MODELS = ("qwen2.5:3b-instruct", "qwen3:1.7b")
CASE_QUERIES = {
    "Aku sedang menghadapi ujian.",
    "Aku sedih dan kehilangan harapan.",
    "Aku bingung dengan tujuan hidup.",
}
MAX_TOKENS = 72

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def unload_models() -> None:
    for model in MODELS:
        subprocess.run(
            ["ollama", "stop", model],
            check=False,
            capture_output=True,
            text=True,
        )


async def benchmark_model(model: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    unload_models()
    os.environ["OLLAMA_MODEL"] = model
    get_settings.cache_clear()
    rag = await get_rag()
    reports: list[dict[str, Any]] = []

    for index, case in enumerate(cases, start=1):
        total_started = time.perf_counter()
        children, documents = await rag.retrieve(case["query"], f"ab-{model}-{index}")
        query = (
            "Output language: Bahasa Indonesia. Tone: singkat. "
            f"Maximum length: {MAX_TOKENS} tokens.\n"
            "Recent history:\n[none]\n"
            f"Current user message: {case['query']}"
        )
        generation_started = time.perf_counter()
        try:
            draft = await rag.llm.generate(
                query,
                build_context(documents),
                MAX_TOKENS,
            )
            generation_ms = round((time.perf_counter() - generation_started) * 1000, 2)
            response = rag.validator.validate(draft, documents)
            report = evaluate_case(case, children, documents, response)
            # Production retrieval may replace vector candidates with reviewed
            # curated parents. Score final context seen by model, not discarded
            # vector candidates.
            final_ids = [document.id for document in documents]
            expected = set(case.get("expected_sources", []))
            rank = next(
                (position + 1 for position, value in enumerate(final_ids) if value in expected),
                None,
            )
            report["retrieved_parent_ids"] = final_ids
            report["criteria"]["retrieval_quality"] = criterion(
                5 if rank == 1 else 4 if rank else 1,
                f"Expected final parent rank: {rank}."
                if rank
                else "Expected source absent from final context.",
            )
            report["overall_score"] = round(
                statistics.mean(
                    float(value["score"]) for value in report["criteria"].values()
                ),
                2,
            )
            report.update(
                {
                    "valid_output": True,
                    "generation_ms": generation_ms,
                    "total_ms": round((time.perf_counter() - total_started) * 1000, 2),
                    "reference_count": len(response.references),
                }
            )
        except Exception as exc:  # benchmark records failures instead of aborting
            report = {
                "query": case["query"],
                "valid_output": False,
                "generation_ms": round((time.perf_counter() - generation_started) * 1000, 2),
                "total_ms": round((time.perf_counter() - total_started) * 1000, 2),
                "overall_score": 0,
                "reference_count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }
        reports.append(report)
        print(json.dumps({"model": model, **report}, ensure_ascii=False), flush=True)

    latencies = [item["generation_ms"] for item in reports]
    return {
        "model": model,
        "cases": reports,
        "summary": {
            "valid_outputs": sum(bool(item["valid_output"]) for item in reports),
            "mean_score": round(
                statistics.mean(float(item["overall_score"]) for item in reports), 2
            ),
            "mean_generation_ms": round(statistics.mean(latencies), 2),
            "median_generation_ms": round(statistics.median(latencies), 2),
            "cold_generation_ms": latencies[0],
            "warm_mean_generation_ms": round(statistics.mean(latencies[1:]), 2),
        },
    }


async def main() -> None:
    all_cases = json.loads(Path("evaluation/dataset.json").read_text(encoding="utf-8"))
    cases = [case for case in all_cases if case["query"] in CASE_QUERIES]
    results = [await benchmark_model(model, cases) for model in MODELS]
    payload = {
        "configuration": {
            "models": list(MODELS),
            "queries": len(cases),
            "max_tokens": MAX_TOKENS,
            "num_ctx": get_settings().ollama_num_ctx,
            "temperature": 0.2,
            "thinking": False,
        },
        "results": results,
    }
    output = Path("evaluation/model_ab_report.json")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output), "results": results}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
