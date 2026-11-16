# 0001 Chunk code by its syntax tree, not by character count

Status: accepted, 6 Nov 2026 (spec Q1-Q13, O5)

## Context
A citation is only useful if it points at a whole, meaningful piece of code. Fixed-size text chunks (500 characters with 50 overlap, as in pet-nutrition-rag) cut functions in half and have no names or line numbers.

## Decision
Parse each Python file with tree-sitter. Each function or method is a function chunk; each class gets a class header; code between definitions becomes file overviews. Markdown is split at headings into doc sections. Each file also gets a one-sentence file summary written by the model. A chunk over 1,000 characters (the embedding model reads about 256 tokens) is cut into parts at line breaks. Every chunk carries file, name, start and end line; its ID is `file:start-end`.

## Consequences
- Citations name a real function and exact lines.
- Long functions arrive as several parts; see ADR 0003 for how retrieval puts them back together.
- Only Python and Markdown are indexed for now; JavaScript/TypeScript repos get only their docs.
