"""Index a repo: chunk it, add file summaries, store everything in Chroma. Used by the CLI and the API.

    index_repo(repo)                                     the chunks, summaries and Chroma collection
    index_and_list(folder, title, source, local=False)   all of that, plus the brief and file map, then
                                                         listed in the registry (website and search)
"""

from collections import Counter
from pathlib import Path

from repo_qa import chunker, flow, overview, registry, retrieve, store

MAX_FILES = 3000  # Python and Markdown files; images, data and JS do not count


def index_repo(repo, progress=overview.say):
    """Rebuild the repo's collection. Returns the number of chunks stored.
    progress(text, fraction) reports each step; fraction runs from 0 to 1 over the whole index."""
    progress(f"chunking {len(chunker.source_files(repo))} files", 0)
    chunks = chunker.chunk_repo(repo)
    if not chunks:
        raise ValueError("no Python or Markdown files to index")

    chunks += overview.summary_chunks(repo, overview.file_purposes(
        repo, lambda text, f=None: progress(text, None if f is None else 0.05 + 0.65 * f)))
    progress(f"chunk kinds: {dict(Counter(c['kind'] for c in chunks))}")

    ids = [store.chunk_id(c) for c in chunks]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    if duplicates:
        raise ValueError(f"{len(duplicates)} duplicate chunk IDs, e.g. {duplicates[:3]}")

    storing = f"embedding and storing {len(chunks)} chunks"
    collection = store.save(repo, chunks, lambda f: progress(storing, 0.7 + 0.3 * f))
    retrieve.forget(repo)
    return collection.count()


def check_folder(folder):
    """Refuses a folder that is missing, private, too big, or has nothing to index. Returns its file count."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"no folder at {folder}")
    if registry.is_private(store.collection_name(folder)):
        raise ValueError("this code is kept private and is never indexed")  # summaries would go to Gemini
    count = len(chunker.source_files(folder))
    if count == 0:
        raise ValueError(f"no Python or Markdown files in {folder}")
    if count > MAX_FILES:
        raise ValueError(f"too big: {count} Python and Markdown files (limit {MAX_FILES:,})")
    return count


def index_and_list(folder, title, source, local=False, progress=overview.say):
    """Index the folder, write its brief and file map, and list it. Returns (name, chunks stored).
    The bar: indexing 0-80%, brief 80-90%, file map 90-100%. Unchanged files are not summarised again."""
    folder = Path(folder).resolve()
    check_folder(folder)
    chunks = index_repo(folder, lambda text, f=None: progress(text, None if f is None else 0.8 * f))
    progress("writing the repo summary", 0.8)
    overview.overview(folder)
    progress("drawing the file map", 0.9)
    try:
        flow.flow(folder)
    except Exception:  # the map is extra; the repo page works without it and retries on open
        pass
    return registry.register(folder, title, source, local), chunks
