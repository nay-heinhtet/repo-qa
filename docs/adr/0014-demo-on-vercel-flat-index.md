# 0014 Demo on Vercel with a flat index

Status: accepted, 17 Nov 2026 (the main path; 0013, Cloud Run, stays as the backup)

## Context
Cloud Run (0013) needs a card on a billing account, and the user's prepaid card was refused. The user ruled out Render. Vercel needs no card and runs Python (FastAPI), but a function's code plus packages must stay under 500 MB; the demo's packages were 598 MB, mostly Chroma's dependencies (125 MB of Kubernetes client alone).

## Decision
- The demo drops Chroma for a flat index (`repo_qa/flat.py`): `embeddings.npy` (3,165 × 384) and `chunks.json`, searched by one numpy matrix product. The question is embedded with the same model (all-MiniLM-L6-v2) through ONNX Runtime, as Chroma does it. `REPO_QA_STORE=flat` switches `store.client()`; nothing else changes.
- Checked against Chroma on 8 questions: the top 20 results are identical and in the same order; embeddings differ by at most 3e-8.
- Bundle (`python deploy/build_demo.py` → `deploy/vercel-api/`): about 103 MB (90 MB is the model) plus about 295 MB of packages, under the limit.
- Two Vercel projects: `repo-qa-api` (back end) and `repo-qa` (website). The answer cache moves to `/tmp`; the visitor's address comes from `x-forwarded-for`. Steps: `deploy/deploy_vercel.sh`.
- The local tool keeps Chroma: it adds and re-indexes repos, which a flat file does not handle.

## Consequences
Vercel may run several instances, each with its own counts, so the hourly and daily caps are approximate. Cached answers reset when an instance restarts (the 4 bundled ones come back). The first request after idle waits a few seconds while the model loads. A flat index compares every vector, which stays fast up to tens of thousands of chunks.
