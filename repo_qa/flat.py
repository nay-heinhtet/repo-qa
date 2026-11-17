"""A flat index: the public demo's stand-in for Chroma (ADR 0014). Read-only, no database.

    export(collection, folder)   save a Chroma collection as embeddings.npy + chunks.json (demo build)
    FlatClient(path)             what store.client() returns when REPO_QA_STORE=flat
    embed(texts)                 all-MiniLM-L6-v2 run directly with ONNX Runtime, as Chroma runs it

A search compares the question's embedding with every stored one (one matrix product): exact, and
about a millisecond for a few thousand chunks. The vectors are normalised, so ranking by dot product
is the same as Chroma's L2 ranking. Only the calls the rest of repo_qa makes are here: get, query, count.
"""

import json
import os
from functools import cache
from pathlib import Path

import numpy as np

# Where Chroma keeps the model locally; the demo bundles a copy and points MODEL_DIR at it.
MODEL_DIR = Path(os.environ.get("MODEL_DIR", Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx"))
MAX_TOKENS = 256  # what Chroma uses for this model
FLAT_DIR = "flat"  # chroma_db/flat/<collection>/


@cache
def model():
    import onnxruntime
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=MAX_TOKENS)
    tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", length=MAX_TOKENS)
    options = onnxruntime.SessionOptions()
    options.log_severity_level = 3  # errors only
    session = onnxruntime.InferenceSession(str(MODEL_DIR / "model.onnx"), options,
                                           providers=["CPUExecutionProvider"])
    return tokenizer, session


def embed(texts):
    """One normalised 384-number vector per text: mean of the token vectors, ignoring padding."""
    tokenizer, session = model()
    encoded = tokenizer.encode_batch(list(texts))
    ids = np.array([e.ids for e in encoded], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
    hidden = session.run(None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)})[0]
    weights = mask[:, :, None].astype(np.float32)
    vectors = (hidden * weights).sum(1) / np.clip(weights.sum(1), 1e-9, None)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return (vectors / np.where(norms == 0, 1e-12, norms)).astype(np.float32)


def export(collection, folder):
    data = collection.get(include=["documents", "metadatas", "embeddings"])
    folder.mkdir(parents=True, exist_ok=True)
    np.save(folder / "embeddings.npy", np.asarray(data["embeddings"], dtype=np.float32))
    (folder / "chunks.json").write_text(json.dumps(
        {"ids": data["ids"], "documents": data["documents"], "metadatas": data["metadatas"]}))
    return len(data["ids"])


class FlatCollection:
    def __init__(self, folder):
        self.name = folder.name
        self.embeddings = np.load(folder / "embeddings.npy")
        data = json.loads((folder / "chunks.json").read_text())
        self.ids, self.documents, self.metadatas = data["ids"], data["documents"], data["metadatas"]
        self.row = {i: n for n, i in enumerate(self.ids)}

    def count(self):
        return len(self.ids)

    def get(self, ids=None, include=("documents", "metadatas")):
        rows = range(len(self.ids)) if ids is None else [self.row[i] for i in ids if i in self.row]
        out = {"ids": [self.ids[r] for r in rows]}
        for field in include:
            if field == "embeddings":
                out[field] = self.embeddings[list(rows)]
            else:
                out[field] = [getattr(self, field)[r] for r in rows]
        return out

    def query(self, query_texts, n_results=10):
        scores = embed(query_texts) @ self.embeddings.T  # cosine similarity, since all are normalised
        best = np.argsort(-scores, axis=1)[:, :n_results]
        return {"ids": [[self.ids[r] for r in row] for row in best],
                "distances": [[float(2 - 2 * scores[q, r]) for r in row] for q, row in enumerate(best)]}


class FlatClient:
    """The two client calls repo_qa makes: list_collections and get_collection."""

    def __init__(self, path):
        self.folder = Path(path) / FLAT_DIR

    @cache
    def get_collection(self, name):
        return FlatCollection(self.folder / name)

    def list_collections(self):
        return [self.get_collection(p.name) for p in sorted(self.folder.iterdir()) if p.is_dir()]
