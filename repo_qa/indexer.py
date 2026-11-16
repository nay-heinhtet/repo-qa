"""Index a repo: chunk it, add file summaries, store everything in Chroma. Used by the CLI and the API."""

from collections import Counter

from repo_qa import chunker, overview, retrieve, store


def index_repo(repo, progress=print):
    """Rebuild the repo's collection. Returns the number of chunks stored."""
    progress(f"chunking {len(chunker.source_files(repo))} files")
    chunks = chunker.chunk_repo(repo)
    if not chunks:
        raise ValueError("no Python or Markdown files to index")

    chunks += overview.summary_chunks(repo, overview.file_purposes(repo, progress))
    progress(f"chunk kinds: {dict(Counter(c['kind'] for c in chunks))}")

    ids = [store.chunk_id(c) for c in chunks]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    if duplicates:
        raise ValueError(f"{len(duplicates)} duplicate chunk IDs, e.g. {duplicates[:3]}")

    progress(f"embedding and storing {len(chunks)} chunks")
    collection = store.save(repo, chunks)
    retrieve.forget(repo)
    return collection.count()
