# Public demo

Read-only demo of RAG-Anything.

## Main path: all on Vercel, no card (ADR 0014)
- Deploy: `bash deploy/deploy_vercel.sh` from the repo-qa folder (6 stages). It builds `deploy/vercel-api/` and deploys two Vercel projects: `repo-qa-api` (back end) and `repo-qa` (website).
- The bundle uses a flat index (`repo_qa/flat.py`: `embeddings.npy` + `chunks.json`) instead of Chroma, to fit Vercel's 500 MB limit.
- Run the bundle locally: `cd deploy/vercel-api && GEMINI_API_KEY=... uvicorn app:app --port 8091` (in a venv with `deploy/vercel/requirements.txt` and uvicorn).

## Backup: Cloud Run (ADR 0013)
- Needs a card that Google Cloud billing accepts. `bash deploy/deploy_demo.sh` (10 stages), image from `python deploy/build_demo.py --docker`.

## Both
`deploy/build_demo.py` refuses to finish if it finds a private repo name, a `.env` file, a key or a token in what it is about to ship.
