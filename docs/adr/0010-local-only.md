# 0010 Run locally only for now

Status: accepted, 16 Nov 2026 (settles P1; issue 11 deferred)

## Context
The tool is for the user's own use. A public demo needs a Hugging Face and a Vercel account, a hosted secret, and a read-only mode.

## Decision
`./run.sh` starts the back end on :8000 and the website on :3000. `/ask` allows 60 questions an hour per IP locally (`ASKS_PER_HOUR`). The public-demo switches exist but are off: `ALLOW_ADD_REPOS=0` makes it read-only, and `WEB_ORIGINS` sets the allowed site.

## Consequences
Nothing is public. Issue 11 (deploy) can be done later without code changes beyond a Dockerfile.
