# 0007 FastAPI back end holds the key; Next.js front end is a client of it

Status: accepted, 14 Nov 2026 (spec W1-W6, D3, D5)

## Context
An API key in browser code can be read by anyone who opens the page. The Python retrieval code already exists.

## Decision
FastAPI wraps the Python package: `/repos`, `/jobs/{id}`, `/repos/{name}/overview`, `/ask`, `/file`. It reads `GEMINI_API_KEY` from `.env` and is the only thing that calls a model. The Next.js front end (App Router, TypeScript, Tailwind) is one client page that calls FastAPI over CORS and knows only `NEXT_PUBLIC_API_URL`. Adding a repo clones only `https://github.com/<owner>/<repo>`, depth 1, max 100 MB / 3,000 files, and never runs its code. `/file` refuses paths outside the repo. `/ask` has a per-IP limit and an answer cache on disk.

## Consequences
A search for `GEMINI` or `AIza` over the front-end build finds nothing (checked 16 Nov 2026). The front end could be swapped without touching the Python code.
