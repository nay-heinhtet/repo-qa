# 0012 Indexed repos are a code library: search returns code, no model writes it

Status: accepted, 17 Nov 2026

## Context
The user wants to build features in their own projects by borrowing from repos repo-qa has already indexed, and to ask about their own projects. They do not want repo-qa to write code or build projects; they want the indexed code itself, reachable while they (or Claude Code) build. The website keeps all its current features.

## Decision
One search function, `repo_qa/search.py`, reached two ways:
- `repoqa search "..."` in any terminal (a launcher in `~/.local/bin`).
- A read-only Claude Code tool (MCP server, user scope) with `search_code`, `read_code` and `list_repos`.

Each repo is searched with the existing hybrid search; candidates from several repos are ranked together by cosine similarity of their stored embeddings to the query, because RRF scores only rank within one repo. Code only by default (`--docs` adds README and docs sections). The code is read from the file on disk. No model calls. hku-room-booker is never searchable.

The user's own projects are indexed from their folders in place (path stored absolute in the registry), with a re-index button; Gemini writes their file summaries like any public repo (the user accepted this, 17 Nov 2026).

## Consequences
Search is free, offline and about a second. Results are only as good as the small embedding model and BM25; there is no model to reword a vague query. A file edited since indexing may have shifted lines until it is re-indexed.
