# 0013 Public demo on Cloud Run and Vercel

Status: accepted, 17 Nov 2026 (supersedes 0010; changes D4)

## Context
Every build piece except the demo was done. The plan (D4) was a Docker back end on Hugging Face Spaces, but since 2026 creating a Docker Space needs the PRO plan ($9 a month); only static Spaces are free. The back end needs about 200 to 350 MB of memory with one repo loaded.

## Decision
- Back end: the Docker image on Google Cloud Run, region asia-east1 (Taiwan, Tier 1, so the free tier applies), 512 MB, at most 1 instance, scaled to zero when idle. The Gemini key lives in Secret Manager.
- Website: Vercel Hobby (personal, non-commercial), `NEXT_PUBLIC_API_URL` pointing at Cloud Run; Cloud Run's `WEB_ORIGINS` is the Vercel address.
- Content: RAG-Anything only (MIT). The image is built from `deploy/build/`, which `deploy/build_demo.py` fills with just the code, that repo's source and a chroma_db holding only its collection, then checks for private names, `.env` files, keys and tokens.
- Limits: read-only (`ALLOW_ADD_REPOS=0`), Gemini only (`LLM_BACKENDS=gemini`; the personal Claude login never goes on a server), 10 questions an hour per visitor, 150 a day in all (`ASKS_PER_DAY`). The demo shares the owner's Gemini key by the owner's choice, so the daily cap keeps most of its 500 calls a day for personal use. Cached answers do not count.
- Steps only the owner can take (accounts, billing, signing in) are in `deploy/deploy_demo.sh`.

Alternatives: Hugging Face PRO (paid), Render free (no card, but about a minute to wake after 15 minutes idle), Koyeb (free plan unclear after its 2026 acquisition).

## Consequences
Cloud Run needs a card on a billing account even inside the free tier, so a $1 budget alert is part of the setup. The first visit after idle waits a few seconds while the container starts. Rebuilding the demo after changes: `python deploy/build_demo.py`, then wizard stages 7 and 8.
