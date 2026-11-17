"""The public demo's back end on Vercel (ADR 0014): repo-qa's FastAPI app, configured for the demo.

Vercel loads `app` from this file. The settings travel with the code; only GEMINI_API_KEY and
WEB_ORIGINS are set in the Vercel project. Read-only, Gemini only, the flat index instead of Chroma,
answers cached in /tmp (the only writable folder).
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
for key, value in {
    "REPO_QA_STORE": "flat",
    "MODEL_DIR": str(HERE / "model"),
    "ANSWER_CACHE": "/tmp/answers-cache.json",
    "CLIENT_IP_HEADER": "x-forwarded-for",
    "ALLOW_ADD_REPOS": "0",
    "LLM_BACKENDS": "gemini",
    "LLM_BACKEND": "gemini",
    "ASKS_PER_HOUR": "10",
    "ASKS_PER_DAY": "150",
}.items():
    os.environ.setdefault(key, value)

from repo_qa.api import app  # noqa: E402,F401
