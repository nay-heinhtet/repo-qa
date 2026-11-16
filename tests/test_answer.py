"""Checks that need no model call. Run: python -m pytest tests  (or python tests/test_answer.py)"""

from repo_qa.answer import check_citations
from repo_qa.retrieve import rrf, tokens

CHUNKS = [
    {"file": "a.py", "start": 10, "end": 20, "kind": "function", "name": "f", "text": ""},
    {"file": "b.py", "start": 1, "end": 5, "kind": "function", "name": "g", "text": ""},
    {"file": "a.py", "start": 21, "end": 30, "kind": "function", "name": "f", "text": ""},
]


def reply(*citations, found=True):
    return {"answer": "x", "found": found,
            "citations": [{"chunk_id": n, "file": f, "start": s, "end": e} for n, f, s, e in citations]}


def test_citation_inside_its_chunk_is_verified():
    assert check_citations(reply((1, "a.py", 12, 15), (2, "b.py", 1, 5)), CHUNKS)


def test_citation_outside_the_given_chunks_is_unverified():
    r = reply((1, "a.py", 12, 15), (1, "a.py", 28, 35))
    assert not check_citations(r, CHUNKS)
    assert [c["valid"] for c in r["citations"]] == [True, False]


def test_citation_across_neighbouring_parts_is_valid_but_not_a_chunk_match():
    r = reply((1, "a.py", 18, 25))
    assert check_citations(r, CHUNKS)
    assert r["citations"][0]["chunk_match"] is False


def test_wrong_file_is_unverified():
    assert not check_citations(reply((2, "b.py", 4, 9)), CHUNKS)
    assert not check_citations(reply((1, "c.py", 12, 15)), CHUNKS)


def test_found_without_citations_is_unverified_but_abstaining_is_fine():
    assert not check_citations(reply(), CHUNKS)
    assert check_citations(reply(found=False), CHUNKS)


def test_tokens_split_identifiers():
    assert tokens("_initialize_lightrag") == ["initialize_lightrag", "initialize", "lightrag"]
    assert tokens("ImageModalProcessor")[1:] == ["image", "modal", "processor"]


def test_rrf_prefers_chunks_high_in_both_lists():
    assert rrf([["a", "b", "c"], ["b", "c", "a"]])[0][0] == "b"


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
