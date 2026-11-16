# 0009 Offline evaluation on 20 frozen questions

Status: accepted, 7 Nov 2026 (spec E1-E7, A7)

## Context
Changes to chunking, retrieval or prompts need a number to show whether they helped. This is a regression test, not training: nothing is learned from the questions.

## Decision
20 questions on RAG-Anything at commit 2cd2b33 (5 locate, 5 explain, 5 flow, 3 value, 2 unanswerable), each with expected line ranges and key facts. Metrics: hit@8, full coverage, citation precision, verified rate, and accuracy by an LLM judge (correct / partial / incorrect; partial counts half; an unanswerable question is correct only with `found: false`). Retrieval-only ablations cost no model calls. Each run writes `eval/results/*.json` and a row in `eval/RESULTS.md`.

## Consequences
Claude drafted the questions and checked each range against the code; the user has not yet signed them off, so results are provisional. The judge uses the same model as the answerer, which may be lenient on itself.
