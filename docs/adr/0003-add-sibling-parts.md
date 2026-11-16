# 0003 Add a long function's other parts when one part is retrieved

Status: accepted, 16 Nov 2026 (reverses spec R4 "no expansion in v1")

## Context
The first full evaluation had 5 partial answers. Each one missed facts that sat in a part of the same function that was not retrieved. Full coverage (every expected line retrieved) was 44%.

## Decision
After hybrid retrieval picks the top 8, each chunk that is one part of a longer chunk brings its sibling parts along, in line order, up to 16 chunks in total. The ablation keeps `hybrid-no-parts` for comparison.

## Consequences
Full coverage rose from 44% to 78%, and accuracy from 78% to 90%, with the same hit@8. Prompts are about twice as long (about 5,000 tokens), which is fine for Gemini Flash Lite's 250K tokens per minute.
