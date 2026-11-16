"""The back end for the website. Run from the repo-qa folder:

    uvicorn repo_qa.api:app --port 8000

Endpoints (spec W1):
    GET  /health
    GET  /repos                       repos you can ask about
    POST /repos {url}                 clone a public GitHub repo and index it, as a background job
    GET  /jobs/{id}                   progress of that job
    GET  /repos/{name}/overview       summary, file map, starter questions
    POST /ask {repo, question, backend?, mode?}
    GET  /file?repo=&path=            one file's text, for the code viewer

The LLM key stays here: llm.py reads it from .env. The browser only ever talks to this server.
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from repo_qa import answer, indexer, overview, retrieve, store
from repo_qa.llm import BACKENDS

ROOT = Path(__file__).resolve().parent.parent
CLONES = ROOT / "repos"
REGISTRY = store.DB_PATH / "repos.json"
ANSWER_CACHE = store.DB_PATH / "answers-cache.json"

GITHUB_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
MAX_REPO_MB = 100
MAX_REPO_FILES = 3000
MAX_FILE_BYTES = 1_000_000
ASKS_PER_HOUR = int(os.environ.get("ASKS_PER_HOUR", "60"))  # per IP; the public demo would use 10 (D3)
ALLOW_ADD_REPOS = os.environ.get("ALLOW_ADD_REPOS", "1") == "1"  # 0 for a read-only demo (D1)

# Code that must never reach the Gemini free tier, whose prompts Google may use (CLAUDE.md).
PRIVATE_NAMES = {"hku-room-booker"}

app = FastAPI(title="repo-qa")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("WEB_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

lock = threading.Lock()                 # guards the registry, jobs and the answer cache
worker = ThreadPoolExecutor(max_workers=1)  # one index job at a time: shared Gemini quota and Chroma writes
jobs = {}
asks = defaultdict(deque)               # IP -> times of recent /ask calls


# ---------- storage helpers ----------

def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path, data):
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    tmp.replace(path)


def registry():
    """{name: {path, title, source}}. RAG-Anything is registered on first start if it is indexed."""
    repos = read_json(REGISTRY, {})
    default = ROOT / "test-repos" / "RAG-Anything"
    if not repos and default.exists() and "rag-anything" in [c.name for c in store.client().list_collections()]:
        repos["rag-anything"] = {"path": str(default.relative_to(ROOT)), "title": "HKUDS/RAG-Anything",
                                 "source": "https://github.com/HKUDS/RAG-Anything"}
        write_json(REGISTRY, repos)
    return repos


def repo_path(name):
    repo = registry().get(name)
    if not repo:
        raise HTTPException(404, f"unknown repo {name!r}")
    return ROOT / repo["path"]


# ---------- repos and index jobs ----------

class AddRepo(BaseModel):
    url: str = Field(max_length=200)


def folder_size(path):
    files = [p for p in path.rglob("*") if p.is_file() and ".git" not in p.parts]
    return len(files), sum(p.stat().st_size for p in files) / 1e6


def run_index_job(job_id, url, owner, name):
    job = jobs[job_id]

    def step(text):
        job["steps"].append(text)
        job["step"] = text

    job["status"] = "running"
    key = f"{owner}-{name}".lower()
    target = CLONES / key
    try:
        step("cloning")
        if target.exists():
            shutil.rmtree(target)
        CLONES.mkdir(exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", url, str(target)],
            check=True, capture_output=True, text=True, timeout=180,
            # never prompt for a login, never download large LFS files
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"},
        )
        count, megabytes = folder_size(target)
        if count > MAX_REPO_FILES or megabytes > MAX_REPO_MB:
            raise ValueError(f"repo too big: {count} files, {megabytes:.0f} MB "
                             f"(limit {MAX_REPO_FILES} files, {MAX_REPO_MB} MB)")
        step(f"cloned: {count} files, {megabytes:.1f} MB")

        chunks = indexer.index_repo(target, progress=step)
        step("writing the repo summary")
        overview.overview(target)
        with lock:
            repos = read_json(REGISTRY, {})
            repos[store.collection_name(target)] = {"path": str(target.relative_to(ROOT)),
                                                    "title": f"{owner}/{name}", "source": f"https://github.com/{owner}/{name}"}
            write_json(REGISTRY, repos)
            clear_cached_answers(store.collection_name(target))
        job.update(status="done", repo=store.collection_name(target), chunks=chunks)
        step(f"done: {chunks} chunks")
    except subprocess.CalledProcessError as error:
        job.update(status="failed", error=f"git clone failed: {error.stderr.strip()[-300:]}")
    except Exception as error:
        job.update(status="failed", error=str(error)[:300])
    job["finished"] = time.time()


@app.get("/health")
def health():
    return {"ok": True, "backends": BACKENDS, "default_backend": os.environ.get("LLM_BACKEND", "gemini"),
            "allow_add_repos": ALLOW_ADD_REPOS}


@app.get("/repos")
def list_repos():
    collections = {c.name: c for c in store.client().list_collections()}
    return [{"name": name, "title": r["title"], "source": r["source"],
             "chunks": collections[name].count() if name in collections else 0}
            for name, r in registry().items()]


@app.post("/repos", status_code=202)
def add_repo(body: AddRepo):
    if not ALLOW_ADD_REPOS:
        raise HTTPException(403, "adding repos is turned off on this server")
    match = GITHUB_URL.match(body.url.strip())
    if not match:
        raise HTTPException(400, "only public repos as https://github.com/<owner>/<repo>")
    owner, name = match.groups()
    if name.lower() in PRIVATE_NAMES:
        raise HTTPException(400, "this repo is kept private and is not indexed through the website")
    with lock:
        running = [j for j in jobs.values() if j["url"] == body.url and j["status"] in ("queued", "running")]
        if running:
            return running[0]
        job_id = uuid.uuid4().hex[:12]
        jobs[job_id] = {"id": job_id, "url": body.url, "status": "queued", "step": "waiting", "steps": [],
                        "error": None, "repo": None, "created": time.time()}
    worker.submit(run_index_job, job_id, f"https://github.com/{owner}/{name}.git", owner, name)
    return jobs[job_id]


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "unknown job")
    return jobs[job_id]


@app.get("/repos/{name}/overview")
def get_overview(name: str):
    return overview.overview(repo_path(name))


# ---------- asking ----------

class Ask(BaseModel):
    repo: str
    question: str = Field(min_length=3, max_length=500)
    backend: str | None = None
    mode: str = "single"


def cache_key(body):
    return json.dumps([body.repo, " ".join(body.question.lower().split()), body.backend, body.mode])


def clear_cached_answers(repo):
    cache = read_json(ANSWER_CACHE, {})
    write_json(ANSWER_CACHE, {k: v for k, v in cache.items() if json.loads(k)[0] != repo})


def check_rate_limit(ip):
    now = time.time()
    recent = asks[ip]
    while recent and recent[0] < now - 3600:
        recent.popleft()
    if len(recent) >= ASKS_PER_HOUR:
        wait = int(recent[0] + 3600 - now) // 60 + 1
        raise HTTPException(429, f"limit of {ASKS_PER_HOUR} questions per hour reached; try again in {wait} min")
    recent.append(now)


def public_chunk(chunk):
    """What the browser needs to list a chunk; it fetches the code itself through /file."""
    return {k: chunk[k] for k in ("id", "kind", "file", "name", "start", "end", "part", "parts", "score")}


@app.post("/ask")
def ask(body: Ask, request: Request):
    body.backend = body.backend or os.environ.get("LLM_BACKEND", "gemini")
    if body.backend not in BACKENDS:
        raise HTTPException(400, f"backend must be one of {BACKENDS}")
    if body.mode not in ("single", "agent"):
        raise HTTPException(400, "mode must be single or agent")
    path = repo_path(body.repo)
    if body.backend == "gemini" and (body.repo in PRIVATE_NAMES or path.name.lower() in PRIVATE_NAMES):
        raise HTTPException(400, "this repo's code is never sent to Gemini; use claude-cli")

    key = cache_key(body)
    with lock:
        cached = read_json(ANSWER_CACHE, {}).get(key)
    if cached:
        return {**cached, "cached": True}

    check_rate_limit(request.client.host if request.client else "unknown")
    try:
        if body.mode == "agent":
            from repo_qa import agent
            result = agent.ask(path, body.question, backend=body.backend)
        else:
            result = answer.ask(path, body.question, backend=body.backend)
    except Exception as error:
        message = str(error)
        status = 429 if "429" in message or "RESOURCE_EXHAUSTED" in message else 502
        raise HTTPException(status, f"the model call failed: {message[:300]}")

    result = {**result, "chunks": [public_chunk(c) for c in result["chunks"]],
              "repo": body.repo, "mode": body.mode, "cached": False}
    with lock:
        cache = read_json(ANSWER_CACHE, {})
        cache[key] = result
        write_json(ANSWER_CACHE, cache)
    return result


# ---------- files ----------

@app.get("/file")
def get_file(repo: str, path: str):
    root = repo_path(repo).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root) or ".git" in target.relative_to(root).parts:
        raise HTTPException(400, "path is outside the repo")
    if not target.is_file():
        raise HTTPException(404, "no such file")
    if target.stat().st_size > MAX_FILE_BYTES:
        raise HTTPException(413, "file too large to show")
    return {"repo": repo, "path": target.relative_to(root).as_posix(),
            "text": target.read_text(errors="replace")}
