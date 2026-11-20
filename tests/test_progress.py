import json
import time

from fastapi.testclient import TestClient

from repo_qa import answer, api

CHUNK = {"id": "a.py:1-3", "kind": "function", "file": "a.py", "name": "f", "start": 1, "end": 3,
         "part": 1, "parts": 1, "score": 1.0, "text": "def f():\n    return 1\n"}


def test_a_streamed_answer_reports_each_step_then_the_result(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "repo_path", lambda name: tmp_path)
    monkeypatch.setattr(api, "ANSWER_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(api, "check_rate_limit", lambda ip: None)
    api.recent_steps.clear()
    monkeypatch.setattr(answer.retrieve, "METHODS", {"hybrid": lambda repo, q: [CHUNK]})
    monkeypatch.setattr(answer, "ask_llm", lambda *a, **k: {
        "answer": "It returns 1 [1].", "citations": [{"chunk_id": 1, "file": "a.py", "start": 1, "end": 2}],
        "found": True})

    response = TestClient(api.app).post("/ask", json={"repo": "demo", "question": "what does f return?",
                                                       "backend": "gemini", "stream": True})
    events = [json.loads(line) for line in response.text.splitlines()]

    assert events[0]["steps"] == answer.STEPS and events[0]["history"]["model"]
    assert [e["step"] for e in events[1:-1]] == [
        "Searching the code", "Searched the code: 1 pieces found", "Writing the answer", "Wrote the answer",
        "Checked every citation against the code"]
    assert sum(e["done"] for e in events[1:-1]) == answer.STEPS
    assert events[-1]["result"]["verified"] is True
    assert [e["kind"] for e in events[1:-1]] == ["search", "search", "model", "model", None]
    assert len(api.recent_steps["model"]) == 1  # the model step was timed for the next estimate


def test_a_pause_for_gemini_is_streamed_and_left_out_of_the_timing(monkeypatch, tmp_path):
    from repo_qa import llm

    def busy_then_answer(*args, **kwargs):
        llm.on_wait.get()(0.5, "Gemini is busy, trying again in 0.5 s")  # what ask_gemini does on a 503
        time.sleep(0.5)
        return {"answer": "No.", "citations": [], "found": False}

    monkeypatch.setattr(api, "repo_path", lambda name: tmp_path)
    monkeypatch.setattr(api, "ANSWER_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(api, "check_rate_limit", lambda ip: None)
    monkeypatch.setattr(answer.retrieve, "METHODS", {"hybrid": lambda repo, q: [CHUNK]})
    monkeypatch.setattr(answer, "ask_llm", busy_then_answer)
    api.recent_steps.clear()

    response = TestClient(api.app).post("/ask", json={"repo": "demo", "question": "is f slow?",
                                                       "backend": "gemini", "stream": True})
    events = [json.loads(line) for line in response.text.splitlines()]

    assert {"wait": 0.5, "reason": "Gemini is busy, trying again in 0.5 s"} in events
    assert 0 <= api.recent_steps["model"][0] < 0.3  # the 0.5 s were a wait, not the model working
