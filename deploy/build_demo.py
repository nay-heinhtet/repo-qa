"""Fill a folder with exactly what the public demo holds, then check it for anything private.

    python deploy/build_demo.py            deploy/vercel-api/: the Vercel bundle, flat index (ADR 0014)
    python deploy/build_demo.py --docker   deploy/build/: the Docker image for Cloud Run, Chroma (ADR 0013)

What goes in: the repo_qa package, RAG-Anything's source (MIT licence) without .git, and a fresh
chroma_db holding only RAG-Anything's collection (copied with its stored embeddings, so nothing is
re-embedded and no model is called), its overview cache and the answers already cached for it.
The check fails the build if any file is named after a private repo, is a .env file, or contains the
Gemini key or a Claude token. The Vercel bundle swaps Chroma for embeddings.npy + chunks.json and
carries the embedding model's files, so it needs no Chroma at all. See deploy/README.md.
"""

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values  # noqa: E402

from repo_qa import flat, registry, store  # noqa: E402

DOCKER = "--docker" in sys.argv
BUILD = ROOT / "deploy" / ("build" if DOCKER else "vercel-api")
DEMO_REPOS = ["rag-anything"]  # ADR 0013
CODE_SKIP = {"mcp_server.py", "compare.py"}  # local-only: Claude Code tool, Claude vs Gemini comparison
BATCH = 500


def copy_code():
    (BUILD / "repo_qa").mkdir(parents=True)
    for path in (ROOT / "repo_qa").glob("*.py"):
        if path.name not in CODE_SKIP:
            shutil.copy2(path, BUILD / "repo_qa" / path.name)
    if DOCKER:
        for name in ("Dockerfile", "requirements.txt"):
            shutil.copy2(ROOT / "deploy" / name, BUILD / name)
        return
    for name in ("app.py", "requirements.txt"):
        shutil.copy2(ROOT / "deploy" / "vercel" / name, BUILD / name)
    (BUILD / ".python-version").write_text("3.14\n")
    # its own ignore list, so Vercel never applies repo-qa's .gitignore (which lists chroma_db/ and test-repos/)
    (BUILD / ".vercelignore").write_text("__pycache__/\n*.pyc\n.env*\n")
    (BUILD / "model").mkdir()
    for name in ("model.onnx", "tokenizer.json"):  # all-MiniLM-L6-v2, as Chroma downloaded it
        shutil.copy2(flat.MODEL_DIR / name, BUILD / "model" / name)


def copy_repos():
    found = registry.repos()
    listed = {}
    for name in DEMO_REPOS:
        entry = found[name]
        source = registry.folder(name)
        shutil.copytree(source, BUILD / entry["path"], ignore=shutil.ignore_patterns(".git", "__pycache__"))
        listed[name] = entry
        overview = store.DB_PATH / f"{name}-overview.json"
        shutil.copy2(overview, BUILD / "chroma_db" / overview.name)
    (BUILD / "chroma_db" / "repos.json").write_text(json.dumps(listed, indent=1))

    cache = registry.read_json(store.DB_PATH / "answers-cache.json", {})
    kept = {k: v for k, v in cache.items() if json.loads(k)[0] in DEMO_REPOS}
    (BUILD / "chroma_db" / "answers-cache.json").write_text(json.dumps(kept, indent=1))
    print(f"answers cached for the demo: {len(kept)}")


def copy_collections():
    if not DOCKER:
        for name in DEMO_REPOS:
            n = flat.export(store.client().get_collection(name), BUILD / "chroma_db" / flat.FLAT_DIR / name)
            print(f"{name}: {n} chunks exported to the flat index")
        return
    import chromadb
    source, target = store.client(), chromadb.PersistentClient(path=str(BUILD / "chroma_db"))
    for name in DEMO_REPOS:
        old = source.get_collection(name)
        data = old.get(include=["documents", "metadatas", "embeddings"])
        new = target.create_collection(name, metadata=old.metadata)
        for i in range(0, len(data["ids"]), BATCH):
            new.add(ids=data["ids"][i:i + BATCH], documents=data["documents"][i:i + BATCH],
                    metadatas=data["metadatas"][i:i + BATCH], embeddings=data["embeddings"][i:i + BATCH])
        print(f"{name}: {new.count()} chunks copied")


def check():
    """Fails on anything private. Never prints a secret, only where it was found."""
    secrets = [v for k, v in dotenv_values(ROOT / ".env").items() if v and len(v) > 12 and ("KEY" in k or "TOKEN" in k)]
    patterns = [re.compile(rb"sk-ant-[a-z0-9]+-"), re.compile(rb"AIza[0-9A-Za-z_-]{30,}")]
    problems = []
    for path in BUILD.rglob("*"):
        rel = path.relative_to(BUILD).as_posix()
        if any(registry.is_private(part) for part in path.relative_to(BUILD).parts):
            problems.append(f"private repo name: {rel}")
        if path.is_file():
            if path.name.startswith(".env"):
                problems.append(f".env file: {rel}")
            data = path.read_bytes()
            if b"hku-room-booker" in data and path.suffix not in (".py",):  # the code names it to refuse it
                problems.append(f"mentions hku-room-booker: {rel}")
            if any(s.encode() in data for s in secrets) or any(p.search(data) for p in patterns):
                problems.append(f"a key or token: {rel}")
    if problems:
        sys.exit("NOT SAFE TO DEPLOY:\n  " + "\n  ".join(problems))
    size = sum(p.stat().st_size for p in BUILD.rglob("*") if p.is_file()) / 1e6
    print(f"checked {sum(1 for _ in BUILD.rglob('*'))} paths: nothing private ({size:.0f} MB)")


if __name__ == "__main__":
    link = BUILD / ".vercel"  # which Vercel project this folder deploys to; kept across rebuilds
    kept = BUILD.parent / ".vercel-link" if link.exists() else None
    if kept:
        shutil.rmtree(kept, ignore_errors=True)
        shutil.move(link, kept)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (BUILD / "chroma_db").mkdir(parents=True)
    copy_code()
    copy_repos()
    copy_collections()
    check()
    if kept:
        shutil.move(kept, link)
    print(f"ready: {'docker build -t repo-qa-demo deploy/build' if DOCKER else 'deploy/vercel-api (see deploy/README.md)'}")
