# Qalbu local-model A/B summary

Date: 2026-09-21
Machine: CPU-only Windows laptop, 8 GB RAM
Configuration: identical retrieved context, JSON schema, `num_ctx=2048`, `max_tokens=72`, `think=false`, `temperature=0.2`

| Metric | qwen2.5:3b-instruct | qwen3:1.7b |
|---|---:|---:|
| Model size | 1.9 GB | 1.4 GB |
| Valid structured outputs | 3/3 | 3/3 |
| Cold generation | 83.82 s | 46.09 s |
| Warm generation mean | 45.09 s | 28.96 s |
| Median generation | 45.81 s | 34.34 s |
| Mean generation | 58.00 s | 34.67 s |
| Verified citation metadata | 3/3 | 3/3 |

## Manual faithfulness review

- `qwen2.5:3b-instruct` used more retrieved parents and stayed closer to supplied passages overall, although some wording still needs stricter claim-level validation.
- `qwen3:1.7b` was about 36% faster on warm generations and about 45% faster cold.
- `qwen3:1.7b` introduced unsupported generalizations, including “Semua yang terjadi adalah untuk kebaikan” and purpose claims about “beriman, beramal, dan berakhlak” that were not directly supported by the supplied parents.
- Both models produced valid JSON and references accepted by the citation metadata validator. This reveals a current evaluation gap: valid citation IDs do not prove every answer claim is entailed by the cited text.

## Decision

Keep `qwen2.5:3b-instruct` as active model. Retain `qwen3:1.7b` as installed experimental candidate. Do not promote it until claim-level faithfulness checks and a stronger grounded prompt pass a larger evaluation set.

Raw machine-readable output: `evaluation/model_ab_report.json`.
