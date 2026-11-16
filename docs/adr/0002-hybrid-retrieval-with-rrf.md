# 0002 Hybrid retrieval: dense + BM25, merged by reciprocal rank fusion

Status: accepted, 7 Nov 2026; measured 16 Nov 2026 (spec A3, R2, R3, E6)

## Context
Dense search (embeddings, finds by meaning) misses exact identifiers like `_initialize_lightrag`. Keyword search (BM25, finds by shared words) misses paraphrases. Code questions need both.

## Decision
Take the top 20 from Chroma and the top 20 from BM25, merge them with reciprocal rank fusion (each list gives a chunk `1/(60 + rank)`), keep the top 8. The BM25 tokenizer splits identifiers on `_`, `.` and camelCase, keeps the whole identifier too, and drops question words (how, does, the...).

## Consequences
On the 18 answerable eval questions: hybrid hit@8 94%, BM25 89%, dense 83% (`eval/RESULTS.md`). RRF needs no score tuning because it uses ranks only. Test files still crowd results for broad questions.
