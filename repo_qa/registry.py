"""The list of indexed repos the website, `repoqa search` and the Claude Code tool all use.

    repos()                     -> {name: {path, title, source, local}}   (chroma_db/repos.json)
    folder(name)                -> the repo's folder, or None
    register(folder, title, source, local=False) -> the name it is listed under
    is_private(name)            -> True for code that must never be searched or sent to Gemini

`path` is relative to the repo-qa folder for clones (repos/..., test-repos/...) and absolute for
your own projects indexed where they are (local=True, source = the folder).
"""

import json
from pathlib import Path

from repo_qa import store

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = store.DB_PATH / "repos.json"

# Someone else's unlicensed code: never sent to the Gemini free tier, never offered to search (CLAUDE.md).
# Matched as a prefix, so copies such as hku-room-booker-main are caught too.
PRIVATE_NAMES = {"hku-room-booker"}


def is_private(name):
    return name.lower().startswith(tuple(PRIVATE_NAMES))


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path, data):
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    tmp.replace(path)


def repos():
    """{name: {path, title, source}}. RAG-Anything is registered on first use if it is indexed."""
    found = read_json(REGISTRY, {})
    default = ROOT / "test-repos" / "RAG-Anything"
    if not found and default.exists() and "rag-anything" in [c.name for c in store.client().list_collections()]:
        found["rag-anything"] = {"path": str(default.relative_to(ROOT)), "title": "HKUDS/RAG-Anything",
                                 "source": "https://github.com/HKUDS/RAG-Anything"}
        write_json(REGISTRY, found)
    return found


def folder(name):
    repo = repos().get(name)
    return ROOT / repo["path"] if repo else None  # an absolute path stays absolute


def stored_path(folder):
    folder = Path(folder).resolve()
    return str(folder.relative_to(ROOT)) if folder.is_relative_to(ROOT) else str(folder)


def register(folder, title, source, local=False):
    """List an indexed folder under its collection name. Refuses a name already used by another folder."""
    name = store.collection_name(folder)
    found = repos()
    old = found.get(name)
    if old and (ROOT / old["path"]).resolve() != Path(folder).resolve():
        raise ValueError(f"a repo called {name!r} is already indexed from {old['path']}; rename the folder")
    found[name] = {"path": stored_path(folder), "title": title, "source": source, **({"local": True} if local else {})}
    write_json(REGISTRY, found)
    return name
