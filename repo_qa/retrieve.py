"""Find the chunks that best match a question: dense search (Chroma), keyword search (BM25), merged by RRF.

    hybrid(repo, question)      the default: dense top 20 + BM25 top 20, merged, top 8, plus sibling parts
    dense(repo, question)       meaning only (for the ablations)
    keyword(repo, question)     BM25 only (for the ablations)

Each result is a dict: id, kind, file, name, start, end, part, parts, text, score.
"""

import re
import time

from rank_bm25 import BM25Okapi

from repo_qa import store

CANDIDATES = 20  # taken from each search before merging
TOP_K = 8        # chunks given to the model
RRF_K = 60       # damping constant in 1/(RRF_K + rank); 60 is the value from the original RRF paper
MAX_CHUNKS = 16  # cap after adding sibling parts

# Question words that match almost every chunk and only add noise to keyword scores.
STOPWORDS = set("""a an and are as at be by can do does for from how i if in is it its of on or
should the this that to was what when where which who why with you your""".split())

# One BM25 index per collection, built the first time the repo is searched in this process.
indexes = {}


def tokens(text):
    """Lowercased words, with identifiers also split into their parts:
    `_initialize_lightrag` -> initialize_lightrag, initialize, lightrag
    `ImageModalProcessor`  -> imagemodalprocessor, image, modal, processor
    `self.config.parser`   -> self, config, parser
    Keeping the whole identifier too lets an exact name score higher than its parts scattered around."""
    words = []
    for identifier in re.findall(r"[A-Za-z0-9_]+", text):
        whole = identifier.strip("_").lower()
        parts = [p.lower() for piece in identifier.split("_") for p in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", piece)]
        if whole:
            words.append(whole)
        if len(parts) > 1:
            words.extend(parts)
    return words


def chunk_text(document):
    """Stored documents start with the label line (`file · name`); the code is everything after it."""
    return document.split("\n", 1)[1] if "\n" in document else ""


def load(repo):
    """The repo's collection plus a BM25 index over all its documents, built once per process."""
    name = store.collection_name(repo)
    if name not in indexes:
        began = time.time()
        collection = store.open_collection(repo)
        data = collection.get(include=["documents", "metadatas"])
        chunks = [{"id": i, **meta, "text": chunk_text(doc)} for i, doc, meta in
                  zip(data["ids"], data["documents"], data["metadatas"])]
        bm25 = BM25Okapi([tokens(doc) for doc in data["documents"]])
        parts = {}
        for c in chunks:
            if c["parts"] > 1:
                parts.setdefault((c["file"], c["name"]), []).append(c)
        indexes[name] = {"collection": collection, "chunks": chunks, "parts": parts,
                         "by_id": {c["id"]: c for c in chunks}, "bm25": bm25}
        print(f"[retrieve] BM25 over {len(chunks)} chunks of '{name}' built in {time.time() - began:.2f} s")
    return indexes[name]


def forget(repo):
    """Drop the in-memory index after a repo is re-indexed, so the next search rebuilds it."""
    indexes.pop(store.collection_name(repo), None)


def dense_ids(repo, question, n=CANDIDATES):
    result = load(repo)["collection"].query(query_texts=[question], n_results=n)
    return result["ids"][0]


def keyword_ids(repo, question, n=CANDIDATES):
    index = load(repo)
    scores = index["bm25"].get_scores([t for t in tokens(question) if t not in STOPWORDS])
    best = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
    return [index["chunks"][i]["id"] for i in best if scores[i] > 0]


def rrf(rankings, k=RRF_K):
    """Reciprocal rank fusion: each list gives a chunk 1/(k + rank); a chunk high in both lists wins."""
    scores = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, 1):
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def results(repo, scored, top_k):
    by_id = load(repo)["by_id"]
    return [{**by_id[chunk_id], "score": round(score, 4)} for chunk_id, score in scored[:top_k]]


def with_sibling_parts(repo, chunks, limit=MAX_CHUNKS):
    """When a retrieved chunk is one part of a long function, add the function's other parts,
    in line order, right after the best-ranked one. A part alone often cuts off half the logic."""
    parts = load(repo)["parts"]
    out, seen = [], set()
    for chunk in chunks:
        group = sorted(parts.get((chunk["file"], chunk["name"]), [chunk]), key=lambda c: c["start"])
        if chunk["parts"] <= 1:
            group = [chunk]
        for c in group:
            if c["id"] not in seen and (c["id"] == chunk["id"] or len(out) < limit):
                seen.add(c["id"])
                out.append({**c, "score": chunk["score"]} if c["id"] != chunk["id"] else chunk)
    return out


def hybrid(repo, question, top_k=TOP_K, expand=True):
    chunks = results(repo, rrf([dense_ids(repo, question), keyword_ids(repo, question)]), top_k)
    return with_sibling_parts(repo, chunks) if expand else chunks


def hybrid_no_parts(repo, question, top_k=TOP_K):
    return hybrid(repo, question, top_k, expand=False)


def dense(repo, question, top_k=TOP_K):
    return results(repo, rrf([dense_ids(repo, question, top_k)]), top_k)


def keyword(repo, question, top_k=TOP_K):
    return results(repo, rrf([keyword_ids(repo, question, top_k)]), top_k)


METHODS = {"hybrid": hybrid, "hybrid-no-parts": hybrid_no_parts, "dense": dense, "bm25": keyword}
