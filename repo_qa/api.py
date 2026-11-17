"""The back end for the website. Run from the repo-qa folder:

    uvicorn repo_qa.api:app --port 8000

Endpoints (spec W1):
    GET  /health
    GET  /repos                       repos you can ask about
    POST /repos {url}                 clone a public GitHub repo and index it, as a background job
    POST /folders {path}              index your own project where it is, as a background job
    POST /repos/{name}/reindex        index your own project again after changing it
    GET  /jobs/{id}                   progress of that job
    GET  /repos/{name}/overview       summary, file map, starter questions
    GET  /repos/{name}/flow           key files in reading order and how they connect
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

from repo_qa import answer, chunker, flow, indexer, overview, retrieve, store
from repo_qa.registry import ROOT, is_private, read_json, repos, write_json
from repo_qa.llm import BACKENDS

CLONES = ROOT / "repos"
ANSWER_CACHE = store.DB_PATH / "answers-cache.json"
# On a read-only disk (the Vercel demo) answers are cached in a writable place instead, starting from
# the answers that came with the build.
if os.environ.get("ANSWER_CACHE"):
    _seed, ANSWER_CACHE = ANSWER_CACHE, Path(os.environ["ANSWER_CACHE"])
    if not ANSWER_CACHE.exists() and _seed.exists():
        shutil.copy(_seed, ANSWER_CACHE)
# Behind a proxy (Vercel) the visitor's address is in this header, e.g. x-forwarded-for.
CLIENT_IP_HEADER = os.environ.get("CLIENT_IP_HEADER", "").lower()

GITHUB_URL = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")
MAX_REPO_MB = 100  # a clone's whole size; your own folders are limited only by indexer.MAX_FILES
CLONE_TIMEOUT = 600  # seconds; a big repo on a slow drive needs a while
NICENESS = 10  # index jobs run at low priority, so the laptop stays responsive while one runs
MAX_FILE_BYTES = 1_000_000
ASKS_PER_HOUR = int(os.environ.get("ASKS_PER_HOUR", "60"))  # per IP; the public demo uses 10 (D3)
# For everyone together, per UTC day; 0 = no cap. The demo shares the owner's Gemini key (500 calls a
# day), and an Agent question can take several calls, so the demo caps it to leave the owner's quota.
ASKS_PER_DAY = int(os.environ.get("ASKS_PER_DAY", "0"))
ALLOW_ADD_REPOS = os.environ.get("ALLOW_ADD_REPOS", "1") == "1"  # 0 for a read-only demo (D1)

app = FastAPI(title="repo-qa")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("WEB_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

lock = threading.Lock()                 # guards the registry, jobs and the answer cache
CLONE_PROGRESS = re.compile(r"(Receiving objects|Updating files):\s+(\d+)%")
worker = ThreadPoolExecutor(max_workers=1)  # one index job at a time: shared Gemini quota and Chroma writes
jobs = {}
asks = defaultdict(deque)               # IP -> times of recent /ask calls
asks_today = {"day": None, "count": 0}  # every IP together, for ASKS_PER_DAY


# ---------- storage helpers ----------

registry = repos  # {name: {path, title, source}}


def repo_path(name):
    repo = registry().get(name)
    if not repo:
        raise HTTPException(404, f"unknown repo {name!r}")
    return ROOT / repo["path"]


# ---------- repos and index jobs ----------

class AddRepo(BaseModel):
    url: str = Field(max_length=200)


def folder_size(path):
    """(files that would be indexed, MB of the whole clone without .git)"""
    files = [p for p in path.rglob("*") if p.is_file() and ".git" not in p.parts]
    return len(chunker.source_files(path)), sum(p.stat().st_size for p in files) / 1e6


def clone(url, target, step):
    """git clone, reporting git's own percentages on the bar (0 to 5%). Raises CalledProcessError, or
    TimeoutExpired when it runs past CLONE_TIMEOUT (checked whenever git reports progress)."""
    # ionice: the clone's disk writes also wait for other programs'
    command = (["ionice", "-c", "2", "-n", "7"] if shutil.which("ionice") else []) + [
        "git", "clone", "--progress", "--depth", "1", "--single-branch", "--no-tags", url, str(target)]
    process = subprocess.Popen(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        # never prompt for a login, never download large LFS files
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"},
    )
    began, tail, line = time.time(), deque(maxlen=20), ""
    while (char := process.stderr.read(1)):  # git redraws its progress line with \r
        if char not in "\r\n":
            line += char
            continue
        tail.append(line)
        if (match := CLONE_PROGRESS.search(line)):
            done = int(match.group(2)) / 100  # downloading is most of the wait, writing the files the rest
            fraction = 0.04 * done if match.group(1) == "Receiving objects" else 0.04 + 0.01 * done
            step(f"cloning: {match.group(1).lower()} {match.group(2)}%", fraction)
        line = ""
        if time.time() - began > CLONE_TIMEOUT:
            process.kill()
            raise subprocess.TimeoutExpired(command, CLONE_TIMEOUT)
    if process.wait() != 0:
        raise subprocess.CalledProcessError(process.returncode, command, stderr="\n".join(tail))


def run_job(job_id, work):
    """Runs work(step) -> (repo name, chunks) at low priority, recording its steps and progress."""
    job = jobs[job_id]

    def step(text, fraction=None):
        if job["step"] != text:
            job["steps"].append(text)
        job["step"] = text
        if fraction is not None:
            job["progress"] = round(fraction, 3)

    job["status"] = "running"
    try:
        # Low priority for this thread and everything it starts (git, the embedding threads): Linux
        # gives new threads and processes their creator's niceness.
        os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), NICENESS)
        name, chunks = work(step)
        with lock:
            clear_cached_answers(name)
        job.update(status="done", repo=name, chunks=chunks)
        step(f"done: {chunks} chunks", 1)
    except subprocess.CalledProcessError as error:
        job.update(status="failed", error=f"git clone failed: {(error.stderr or '').strip()[-300:]}")
    except subprocess.TimeoutExpired:
        job.update(status="failed", error=f"cloning took over {CLONE_TIMEOUT // 60} minutes; the repo may be too big, "
                                          "or the computer too busy")
    except Exception as error:
        job.update(status="failed", error=str(error)[:300])
    job["finished"] = time.time()


def clone_and_index(url, owner, name):
    """The work of a GitHub job. The bar: cloning 0-5%, then indexing, brief and file map 5-100%."""
    def work(step):
        target = CLONES / f"{owner}-{name}".lower()
        step("cloning", 0)
        if target.exists():
            shutil.rmtree(target)
        CLONES.mkdir(exist_ok=True)
        clone(url, target, step)
        count, megabytes = folder_size(target)
        if count > indexer.MAX_FILES or megabytes > MAX_REPO_MB:
            raise ValueError(f"repo too big: {count} Python and Markdown files, {megabytes:.0f} MB "
                             f"(limit {indexer.MAX_FILES} files, {MAX_REPO_MB} MB)")
        step(f"cloned: {count} files to index, {megabytes:.1f} MB", 0.05)
        return indexer.index_and_list(target, f"{owner}/{name}", f"https://github.com/{owner}/{name}",
                                      progress=lambda text, f=None: step(text, None if f is None else 0.05 + 0.95 * f))
    return work


def index_folder(folder):
    """The work of a job for your own project: indexed where it is, nothing copied."""
    return lambda step: indexer.index_and_list(folder, Path(folder).name, str(folder), local=True, progress=step)


def start_job(label, work):
    """Queues a job, or returns the one already running for the same repo or folder."""
    with lock:
        running = [j for j in jobs.values() if j["url"] == label and j["status"] in ("queued", "running")]
        if running:
            return running[0]
        job_id = uuid.uuid4().hex[:12]
        jobs[job_id] = {"id": job_id, "url": label, "status": "queued", "step": "waiting", "steps": [], "progress": 0,
                        "error": None, "repo": None, "created": time.time()}
    worker.submit(run_job, job_id, work)
    return jobs[job_id]


@app.get("/health")
def health():
    return {"ok": True, "backends": BACKENDS, "default_backend": os.environ.get("LLM_BACKEND", "gemini"),
            "allow_add_repos": ALLOW_ADD_REPOS}


@app.get("/repos")
def list_repos():
    collections = {c.name: c for c in store.client().list_collections()}
    return [{"name": name, "title": r["title"], "source": r["source"], "local": r.get("local", False),
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
    if is_private(name):
        raise HTTPException(400, "this repo is kept private and is not indexed through the website")
    return start_job(body.url, clone_and_index(f"https://github.com/{owner}/{name}.git", owner, name))


class AddFolder(BaseModel):
    path: str = Field(max_length=500)


@app.post("/folders", status_code=202)
def add_folder(body: AddFolder):
    """Your own project, indexed where it is. Refused at once if it cannot be indexed."""
    if not ALLOW_ADD_REPOS:
        raise HTTPException(403, "adding repos is turned off on this server")
    folder = Path(body.path.strip()).expanduser()
    if not folder.is_absolute():
        raise HTTPException(400, "give the full path, e.g. /mnt/shared/projects/pet-nutrition-rag")
    try:
        indexer.check_folder(folder)
    except ValueError as error:
        raise HTTPException(400, str(error))
    return start_job(str(folder.resolve()), index_folder(folder.resolve()))


@app.post("/repos/{name}/reindex", status_code=202)
def reindex(name: str):
    """Index your own project again after you change it. Only changed files are summarised again."""
    if not ALLOW_ADD_REPOS:
        raise HTTPException(403, "adding repos is turned off on this server")
    if not registry().get(name, {}).get("local"):
        raise HTTPException(400, "only your own projects can be re-indexed")
    folder = repo_path(name).resolve()
    return start_job(str(folder), index_folder(folder))


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "unknown job")
    return jobs[job_id]


@app.get("/repos/{name}/overview")
def get_overview(name: str):
    return overview.overview(repo_path(name))


@app.get("/repos/{name}/flow")
def get_flow(name: str):
    """The key files in reading order and the imports between them, for the flowchart."""
    return flow.flow(repo_path(name))


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
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    if asks_today["day"] != day:
        asks_today.update(day=day, count=0)
    if ASKS_PER_DAY and asks_today["count"] >= ASKS_PER_DAY:
        raise HTTPException(429, "this demo has answered its questions for today; questions already "
                                 "asked still work, and new ones open again at 08:00 Hong Kong time")
    recent = asks[ip]
    while recent and recent[0] < now - 3600:
        recent.popleft()
    if len(recent) >= ASKS_PER_HOUR:
        wait = int(recent[0] + 3600 - now) // 60 + 1
        raise HTTPException(429, f"limit of {ASKS_PER_HOUR} questions per hour reached; try again in {wait} min")
    recent.append(now)
    asks_today["count"] += 1


def client_ip(request):
    forwarded = request.headers.get(CLIENT_IP_HEADER) if CLIENT_IP_HEADER else None
    if forwarded:
        return forwarded.split(",")[0].strip()  # the first address is the visitor's
    return request.client.host if request.client else "unknown"


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
    if body.backend == "gemini" and (is_private(body.repo) or is_private(path.name)):
        raise HTTPException(400, "this repo's code is never sent to Gemini; use claude-cli")

    key = cache_key(body)
    with lock:
        cached = read_json(ANSWER_CACHE, {}).get(key)
    if cached:
        return {**cached, "cached": True}

    check_rate_limit(client_ip(request))
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
