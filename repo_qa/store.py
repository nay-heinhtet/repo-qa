"""Save chunks in Chroma: one collection per repo, rebuilt from scratch on every index run."""

from pathlib import Path

import chromadb

DB_PATH = Path(__file__).resolve().parent.parent / "chroma_db"
BATCH = 500


def client():
    return chromadb.PersistentClient(path=str(DB_PATH))


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


def save(repo, chunks):
    """Delete the repo's collection if it exists, then store every chunk. Returns the collection."""
    db = client()
    name = collection_name(repo)
    if name in [c.name for c in db.list_collections()]:
        db.delete_collection(name)
    collection = db.create_collection(name)

    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        collection.add(
            ids=[chunk_id(c) for c in batch],
            documents=[embedded_text(c) for c in batch],
            metadatas=[{k: c[k] for k in ("kind", "file", "name", "start", "end", "part", "parts")} for c in batch],
        )
    return collection


def open_collection(repo):
    return client().get_collection(collection_name(repo))
