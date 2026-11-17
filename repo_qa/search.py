"""Code search across every indexed repo, with no model calls: the matching code itself, with file:line.

    search(query, repo=None, top=5, docs=False) -> [{repo, title, file, start, end, kind, name, purpose, code, score, match}]
    read_code(repo, file, start=1, end=None) -> {repo, file, start, end, code}
    as_text(hits, short=False)                -> the matches as `repoqa search` prints them

Used by `repoqa search` and the Claude Code tool (mcp_server.py). Each repo is searched with the
website's hybrid search (meaning + keywords, merged by RRF), which picks its candidates. RRF scores only
rank within one repo (every repo's best match scores about the same, however weak), so candidates from
several repos are ranked together by meaning: the cosine similarity between the query's embedding and
the chunk's, from the same model in every repo. That similarity is also returned as `match` (0 to 1) so a
weak match can be told from a strong one. A function split into parts comes back whole. Code is
read from the file on disk, so it is exactly what is there now. Docs sections only with docs=True.
"""

from pathlib import Path

import numpy as np
from repo_qa import overview, registry, retrieve, store

TOP = 5
EXTRA = 3            # taken per repo beyond `top` (at least TOP), since file summaries and overlaps are dropped
MAX_READ_LINES = 400
SHORT_LINES = 10

KINDS = {"function": "function", "class_header": "class", "file_overview": "top of file",
         "doc_section": "docs section"}


def similarity(folder, query, chunks):
    """{chunk id: cosine similarity to the query}, from the embeddings already stored in Chroma."""
    q = np.asarray(store.embed([query])[0])
    stored = retrieve.load(folder)["collection"].get(ids=[c["id"] for c in chunks], include=["embeddings"])
    return {i: float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v)))
            for i, v in zip(stored["ids"], np.asarray(stored["embeddings"]))}


def searchable(repo=None):
    names = [n for n in registry.repos() if not registry.is_private(n)]
    if repo is None:
        return names
    if repo not in names:
        raise ValueError(f"no indexed repo called {repo!r}; indexed: {', '.join(names)}")
    return [repo]


def whole(chunks):
    """Merges the parts of a long function (consecutive, from with_sibling_parts) into one span."""
    merged = {}
    for c in chunks:
        key = (c["file"], c["name"], c["kind"]) if c["parts"] > 1 else c["id"]
        if key in merged:
            m = merged[key]
            m["start"], m["end"] = min(m["start"], c["start"]), max(m["end"], c["end"])
        else:
            merged[key] = dict(c)
    return list(merged.values())


def lines_of(folder, file, start, end):
    path = (folder / file).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():
        raise ValueError(f"no file {file!r} in this repo")
    lines = path.read_text(errors="replace").split("\n")
    end = min(end or len(lines), len(lines), start + MAX_READ_LINES - 1)
    return start, end, "\n".join(lines[start - 1:end])


def search(query, repo=None, top=TOP, docs=False):
    names = searchable(repo)
    hits = []
    for name in names:
        folder = registry.folder(name)
        title = registry.repos()[name]["title"]
        purposes = {f: v.get("purpose", "") for f, v in overview.load_cache(folder)["files"].items()}
        skip = {"file_summary"} | (set() if docs else {"doc_section"})  # summaries are model-written, not code
        chunks = [c for c in whole(retrieve.hybrid(folder, query, top_k=max(top, TOP) + EXTRA)) if c["kind"] not in skip]
        close = similarity(folder, query, chunks) if chunks else {}
        chunks = [{**c, "match": close.get(c["id"], 0.0)} for c in chunks]
        if len(names) > 1:
            chunks = [{**c, "score": c["match"]} for c in chunks]
        for c in chunks:
            try:
                start, end, code = lines_of(folder, c["file"], c["start"], c["end"])
            except (ValueError, OSError):
                start, end, code = c["start"], c["end"], c["text"]  # file gone since indexing
            hits.append({"repo": name, "title": title, "file": c["file"], "start": start, "end": end,
                         "kind": KINDS.get(c["kind"], c["kind"]), "name": c["name"],
                         "purpose": purposes.get(c["file"], ""), "code": code, "score": c["score"], "match": c["match"]})

    hits.sort(key=lambda h: h["score"], reverse=True)
    kept = []
    for h in hits:  # drop a hit inside one already kept, e.g. a class header within its whole class
        if not any(k["repo"] == h["repo"] and k["file"] == h["file"] and k["start"] <= h["start"] and h["end"] <= k["end"]
                   for k in kept):
            kept.append(h)
    return kept[:top]


def read_code(repo, file, start=1, end=None):
    """Lines of one file in an indexed repo (at most MAX_READ_LINES), e.g. the rest of a class."""
    name = searchable(repo)[0]
    start, end, code = lines_of(Path(registry.folder(name)), file, max(1, start), end)
    return {"repo": name, "file": file, "start": start, "end": end, "code": code}


def numbered(code, start):
    width = len(str(start + code.count("\n")))
    return "\n".join(f"{n:>{width}} │ {line}" for n, line in enumerate(code.split("\n"), start))


def strength(match):
    """A word for the meaning similarity (0 to 1). From test queries: an unrelated query ("bake a chocolate
    cake") stays under 0.2, the right code for a clear query is usually 0.45 or more. Useful code can still
    score lower, since the model sees only the first ~256 tokens of a chunk."""
    return "strong" if match >= 0.45 else "fair" if match >= 0.25 else "weak"


def as_text(hits, short=False):
    if not hits:
        return "No matches."
    out = []
    for n, h in enumerate(hits, 1):
        out.append(f'{n}. {h["title"]}   {h["file"]}:{h["start"]}-{h["end"]}   match {h["match"]:.2f} ({strength(h["match"])})')
        out.append(f'   {h["kind"]} {h["name"]}  [repo: {h["repo"]}]')
        if h["purpose"]:
            out.append(f'   File: {h["purpose"]}')
        lines = h["code"].split("\n")
        code = "\n".join(lines[:SHORT_LINES]) if short else h["code"]
        out.extend("   " + line for line in numbered(code, h["start"]).split("\n"))
        if short and len(lines) > SHORT_LINES:
            out.append(f"   ... {len(lines) - SHORT_LINES} more lines")
        out.append("")
    return "\n".join(out)
