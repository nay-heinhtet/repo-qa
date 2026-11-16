"""API checks that need no model call: input validation and path safety."""

from fastapi.testclient import TestClient

from repo_qa.api import app

client = TestClient(app)


def test_health_and_repos():
    assert client.get("/health").json()["ok"]
    names = [r["name"] for r in client.get("/repos").json()]
    assert "rag-anything" in names
    assert "hku-room-booker" not in names


def test_add_repo_rejects_non_github_urls():
    for url in ["http://github.com/a/b", "https://gitlab.com/a/b", "https://github.com/a/b/../c",
                "https://github.com/a", "file:///etc", "https://github.com/a/b; rm -rf /"]:
        assert client.post("/repos", json={"url": url}).status_code == 400, url


def test_file_rejects_paths_outside_the_repo():
    for path in ["../README.md", "../../.env", "/etc/passwd", ".git/config"]:
        assert client.get("/file", params={"repo": "rag-anything", "path": path}).status_code == 400, path


def test_file_returns_text():
    reply = client.get("/file", params={"repo": "rag-anything", "path": "raganything/parse_options.py"})
    assert reply.status_code == 200 and "def relevant_parser_kwargs" in reply.json()["text"]


def test_ask_validates_input():
    assert client.post("/ask", json={"repo": "nope", "question": "what is this"}).status_code == 404
    assert client.post("/ask", json={"repo": "rag-anything", "question": "hi there", "mode": "x"}).status_code == 400
    assert client.post("/ask", json={"repo": "rag-anything", "question": "what is this", "backend": "gpt"}).status_code == 400
    assert client.post("/ask", json={"repo": "rag-anything", "question": "hi"}).status_code == 422  # too short


def test_rate_limit_and_cache(monkeypatch, tmp_path):
    """The 11th new question in an hour from one IP is refused; a repeated question comes from the cache."""
    from repo_qa import api

    calls = []

    def fake_ask(path, question, backend=None):
        calls.append(question)
        return {"question": question, "answer": "x", "citations": [], "found": False, "verified": True,
                "chunks": [], "backend": backend, "seconds": 0.0}

    monkeypatch.setattr(api.answer, "ask", fake_ask)
    monkeypatch.setattr(api, "ASKS_PER_HOUR", 10)
    monkeypatch.setattr(api, "ANSWER_CACHE", tmp_path / "cache.json")
    api.asks.clear()

    for i in range(10):
        assert client.post("/ask", json={"repo": "rag-anything", "question": f"question {i}"}).status_code == 200
    again = client.post("/ask", json={"repo": "rag-anything", "question": "Question  0"})
    assert again.status_code == 200 and again.json()["cached"]  # same words, different case and spacing
    assert client.post("/ask", json={"repo": "rag-anything", "question": "question 11"}).status_code == 429
    assert len(calls) == 10
