import pytest

from repo_qa import indexer, registry


def test_private_code_is_caught_under_another_folder_name():
    assert registry.is_private("hku-room-booker-main")
    assert not registry.is_private("pet-nutrition-rag")


def test_folders_that_cannot_be_indexed_are_refused(tmp_path):
    with pytest.raises(ValueError, match="no folder"):
        indexer.check_folder(tmp_path / "missing")
    (tmp_path / "empty").mkdir()
    (tmp_path / "empty" / "data.csv").write_text("a,b")
    with pytest.raises(ValueError, match="no Python or Markdown"):
        indexer.check_folder(tmp_path / "empty")
    (tmp_path / "hku-room-booker-main").mkdir()
    (tmp_path / "hku-room-booker-main" / "auth.py").write_text("x = 1")
    with pytest.raises(ValueError, match="private"):
        indexer.check_folder(tmp_path / "hku-room-booker-main")


def test_own_projects_are_stored_with_their_full_path(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "REGISTRY", tmp_path / "repos.json")
    monkeypatch.setattr(registry.store, "client", lambda: type("C", (), {"list_collections": lambda self: []})())
    project = tmp_path / "Mine"
    project.mkdir()
    assert registry.register(project, "Mine", str(project), local=True) == "mine"
    assert registry.repos()["mine"] == {"path": str(project), "title": "Mine", "source": str(project), "local": True}
    assert registry.folder("mine") == project

    other = tmp_path / "elsewhere" / "mine"
    other.mkdir(parents=True)
    with pytest.raises(ValueError, match="already indexed"):
        registry.register(other, "mine", str(other), local=True)
