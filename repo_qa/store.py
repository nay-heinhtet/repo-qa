"""Save chunks in Chroma: one collection per repo, rebuilt from scratch on every index run.

With REPO_QA_STORE=flat (the public demo), client() is a read-only flat index instead (flat.py), so
the demo runs without Chroma; everything else calls the same client and collection methods.
"""

import os
from functools import cache
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"
BATCH = 500
FLAT = os.environ.get("REPO_QA_STORE") == "flat"


def client():
    if FLAT:
        return flat_client()
    import chromadb
    return chromadb.PersistentClient(path=str(DB_PATH))


@cache
def flat_client():
    from repo_qa import flat
    return flat.FlatClient(DB_PATH)


def embed(texts):
    """The embedding model every collection uses (all-MiniLM-L6-v2), for a question."""
    if FLAT:
        from repo_qa import flat
        return flat.embed(texts)
    return [list(v) for v in chroma_embedder()(list(texts))]


@cache
def chroma_embedder():
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    return DefaultEmbeddingFunction()  # loads the model once per process


def collection_name(repo):
    """The repo folder's name, lowercased: test-repos/RAG-Anything -> rag-anything."""
    return Path(repo).resolve().name.lower()


def chunk_id(chunk):
    if chunk["kind"] == "file_summary":
        return f'{chunk["file"]}:summary'  # covers the whole file, so its line range could clash with a chunk's
    return f'{chunk["file"]}:{chunk["start"]}-{chunk["end"]}'


def embedded_text(chunk):
    """One label line above the code, so the file and name are part of what gets embedded."""
    label = f'{chunk["file"]} · {chunk["name"]}'
    if chunk["parts"] > 1:
        label += f' (part {chunk["part"]} of {chunk["parts"]})'
    return label + "\n" + chunk["text"]


def save(repo, chunks, progress=None):
    """Delete the repo's collection if it exists, then store every chunk. Returns the collection.
    progress(fraction) is called before each batch."""
    db = client()
    name = collection_name(repo)
    if name in [c.name for c in db.list_collections()]:
        db.delete_collection(name)
    collection = db.create_collection(name)

    for i in range(0, len(chunks), BATCH):
        if progress:
            progress(i / len(chunks))
        batch = chunks[i:i + BATCH]
        collection.add(
            ids=[chunk_id(c) for c in batch],
            documents=[embedded_text(c) for c in batch],
            metadatas=[{k: c[k] for k in ("kind", "file", "name", "start", "end", "part", "parts")} for c in batch],
        )
    return collection


def open_collection(repo):
    return client().get_collection(collection_name(repo))
