# The public demo's back end (ADR 0013). Built from deploy/build/, which deploy/build_demo.py fills with
# only what the demo needs: the code, RAG-Anything's source and its index. Nothing else is in the image.
FROM python:3.14-slim

RUN useradd --create-home app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

USER app
# The embedding model (all-MiniLM-L6-v2, ~80 MB) is downloaded now, so the first visitor does not wait for it.
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as E; E()(['warm up'])"
COPY --chown=app . .

# Read-only, Gemini only, 10 questions an hour per visitor, 150 a day in all. GEMINI_API_KEY and
# WEB_ORIGINS are set when deploying, never here.
ENV ALLOW_ADD_REPOS=0 LLM_BACKENDS=gemini LLM_BACKEND=gemini ASKS_PER_HOUR=10 ASKS_PER_DAY=150 PORT=8080
# --proxy-headers: Cloud Run sits in front, so the visitor's address comes from X-Forwarded-For.
CMD uvicorn repo_qa.api:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
