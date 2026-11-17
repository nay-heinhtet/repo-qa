# Evaluation results

20 questions on RAG-Anything at commit 2cd2b33 (`eval/questions.json`). Accuracy counts a partial as half.

| Run | Mode | Answer model | Retrieval | hit@8 | Full coverage | Citation precision | Verified | Correct / partial / incorrect | Accuracy |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-16 08:23 | retrieval only | - | hybrid | 94% | 44% | - | - | - | - |
| 2026-11-16 08:23 | retrieval only | - | dense | 83% | 28% | - | - | - | - |
| 2026-11-16 08:23 | retrieval only | - | bm25 | 89% | 50% | - | - | - | - |
| 2026-11-16 08:23 | single | gemini-3.5-flash-lite | hybrid | 89% | 44% | 96% | 90% | 13 / 5 / 0 (+2 errors) | 78% |
| 2026-11-16 08:27 | single | gemini-3.5-flash-lite | hybrid | 94% | 78% | 88% | 85% | 16 / 4 / 0 | 90% |
| 2026-11-16 14:02 | single | gemini-3.5-flash-lite | hybrid | 94% | 78% | 86% | 100% | 13 / 7 / 0 | 82% |
| 2026-11-16 14:07 | agent | gemini-3.5-flash-lite | hybrid | 94% | 78% | 90% | 100% | 16 / 4 / 0 | 90% |

Notes on the 16 Nov rows:
- 08:23 rows: retrieval without sibling parts (ADR 0003); two answers failed on Gemini 503 errors (retries added after).
- 08:27: sibling parts on; old citation rule (one named chunk), so 85% verified.
- 14:02 and 14:07: final code (widened citation rule, ADR 0005). Single-shot vs agent on the same questions.
- The same single-shot setup scored 16/4/0 and 13/7/0 in two runs: model and judge vary by about 3 questions, so differences smaller than that are noise.
- These rows used the questions before the user's check (see 17 Nov).
| 2026-11-17 23:31 | retrieval only | - | hybrid | 94% | 78% | - | - | - | - |
| 2026-11-17 23:31 | retrieval only | - | hybrid-no-parts | 94% | 44% | - | - | - | - |
| 2026-11-17 23:31 | retrieval only | - | dense | 83% | 28% | - | - | - | - |
| 2026-11-17 23:31 | retrieval only | - | bm25 | 89% | 44% | - | - | - | - |
| 2026-11-17 23:32 | single | gemini-3.5-flash-lite | hybrid | 67% | 56% | 88% | 75% | 9 / 6 / 0 (+5 errors) | 60% |
| 2026-11-17 23:48 | agent | gemini-3.5-flash-lite | hybrid | 89% | 78% | 91% | 95% | 15 / 4 / 0 (+1 errors) | 85% |
| 2026-11-18 00:04 | single (errors re-run) | gemini-3.5-flash-lite | hybrid | 89% | 72% | 88% | 95% | 11 / 8 / 0 (+1 errors) | 75% |
| 2026-11-18 00:05 | agent (errors re-run) | gemini-3.5-flash-lite | hybrid | 94% | 78% | 92% | 100% | 16 / 4 / 0 | 90% |
| 2026-11-18 00:05 | single (errors re-run) | gemini-3.5-flash-lite | hybrid | 94% | 78% | 88% | 100% | 11 / 9 / 0 | 78% |

Notes on the 17 Nov rows (the current results):
- Questions drafted by Claude and checked by the user one by one against the code; three expected line ranges were corrected (q01, q03, q08).
- Gemini was overloaded (503 errors) during the answer runs; errored questions count as wrong, so the 23:32 and 23:48 rows understate. `--retry-errors` re-ran only those questions and merged them in: the "errors re-run" rows are the results to quote.
- Final: single-shot 78% (11 correct, 9 partial, 0 incorrect); agent 90% (16 / 4 / 0) with every citation verified. Hybrid retrieval finds the right code for 94% of answerable questions, against 83% for meaning search alone and 89% for keyword search alone.
- 20 questions on one repo, and the same model family answers and judges; runs vary by about 3 questions, so treat these as a benchmark on this set, not a general accuracy figure.
