#!/usr/bin/env bash
# Start repo-qa locally: the FastAPI back end on :8000 and the website on :3000.
# Open http://localhost:3000. Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

source ~/.local/share/repo-qa/venv/bin/activate
if [ ! -d web/node_modules ]; then
  # exFAT has no symlinks, so npm must not create .bin links.
  (cd web && npm install --no-bin-links --no-audit --no-fund)
fi

uvicorn repo_qa.api:app --port 8000 &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT

cd web
if [ "${1:-}" = "--dev" ]; then
  npm run dev            # reloads when you edit the front end
else
  npm run build && npm run start
fi
