import json

import numpy as np

from repo_qa import api, flat


class FakeCollection:
    def get(self, include):
        return {"ids": ["a.py:1-2", "b.py:1-5", "c.md:1-3"], "documents": ["a", "b", "c"],
                "metadatas": [{"file": "a.py"}, {"file": "b.py"}, {"file": "c.md"}],
                "embeddings": [[1, 0], [0.6, 0.8], [0, 1]]}


def test_flat_index_returns_the_nearest_chunks_like_chroma(tmp_path, monkeypatch):
    assert flat.export(FakeCollection(), tmp_path / "flat" / "demo") == 3
    collection = flat.FlatClient(tmp_path).get_collection("demo")
    monkeypatch.setattr(flat, "embed", lambda texts: np.array([[0.8, 0.6]], dtype=np.float32))
    assert collection.query(["q"], n_results=2)["ids"] == [["b.py:1-5", "a.py:1-2"]]
    got = collection.get(ids=["c.md:1-3", "a.py:1-2"], include=["metadatas", "embeddings"])
    assert got["ids"] == ["c.md:1-3", "a.py:1-2"] and got["metadatas"][0] == {"file": "c.md"}
    assert collection.count() == 3 and json.loads((tmp_path / "flat/demo/chunks.json").read_text())["ids"][0] == "a.py:1-2"


def test_visitor_address_comes_from_the_proxy_header(monkeypatch):
    monkeypatch.setattr(api, "CLIENT_IP_HEADER", "x-forwarded-for")
    request = type("R", (), {"headers": {"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, "client": None})()
    assert api.client_ip(request) == "9.9.9.9"
