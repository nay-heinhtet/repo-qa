# 0004 Build BM25 in memory from Chroma; never save it

Status: accepted, 7 Nov 2026 (spec W6)

## Context
BM25 needs an index of every chunk's words. It could be saved next to Chroma, but then two stores must be kept in step after every re-index.

## Decision
Chroma is the only store. The first search on a repo in a process reads all its documents from Chroma and builds BM25 in memory (0.7 s for 3,165 chunks). Re-indexing drops the in-memory copy.

## Consequences
No stale keyword index is possible. Each server start pays under a second per repo on its first question.
