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
- Questions are drafted by Claude and not yet checked by the user: provisional.
