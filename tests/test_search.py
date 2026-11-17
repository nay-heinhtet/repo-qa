import pytest

from repo_qa import registry, search


def chunk(id, start, end, parts=1, name="f", kind="function"):
    return {"id": id, "file": "a.py", "name": name, "kind": kind, "start": start, "end": end, "parts": parts,
            "text": "", "score": 0.5}


def test_parts_of_a_long_function_come_back_whole():
    merged = search.whole([chunk("1", 10, 40, parts=2), chunk("2", 41, 70, parts=2), chunk("3", 80, 90, name="g")])
    assert [(c["start"], c["end"]) for c in merged] == [(10, 70), (80, 90)]


def test_reading_outside_the_repo_is_refused(tmp_path):
    (tmp_path / "repo").mkdir()
    (tmp_path / "secret.txt").write_text("x")
    with pytest.raises(ValueError):
        search.lines_of(tmp_path / "repo", "../secret.txt", 1, None)


def test_lines_are_capped_and_numbered(tmp_path):
    (tmp_path / "a.py").write_text("\n".join(f"line {n}" for n in range(1, 1001)))
    start, end, code = search.lines_of(tmp_path, "a.py", 5, None)
    assert (start, end) == (5, 5 + search.MAX_READ_LINES - 1)
    assert search.numbered("x\ny", 9).split("\n") == [" 9 │ x", "10 │ y"]


def test_private_repos_are_never_searchable(monkeypatch):
    monkeypatch.setattr(registry, "repos", lambda: {"hku-room-booker": {}, "mine": {}})
    assert search.searchable() == ["mine"]
    with pytest.raises(ValueError):
        search.searchable("hku-room-booker")


def test_the_claude_code_tool_refuses_files_outside_a_repo(monkeypatch, tmp_path):
    from repo_qa import mcp_server
    (tmp_path / "repo").mkdir()
    monkeypatch.setattr(registry, "repos", lambda: {"mine": {"path": str(tmp_path / "repo")}})
    assert mcp_server.read_code("mine", "../secret.txt") == "no file '../secret.txt' in this repo"
    assert mcp_server.read_code("hku-room-booker", "auth.py").startswith("no indexed repo")
