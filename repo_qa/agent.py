"""Agent mode: the model decides what to read before it answers (spec G1-G3, ADR 0008).

A LangGraph loop of three kinds of step:
    search(query)                 hybrid retrieval, adds up to 8 chunks
    open_file(path, start, end)   reads up to 120 lines of one file
    answer                        the final answer, in the same schema as single-shot
The loop starts with one search on the question itself (no model call), so the agent never sees
less than single-shot does. At most MAX_TOOL_CALLS tool calls; then it must answer.

Tool calling is done with structured output: each model call returns one JSON action. This works
the same through both backends (Gemini and `claude -p`), because neither needs a tools API.
"""

import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from repo_qa import answer, retrieve
from repo_qa.llm import ask_llm

MAX_TOOL_CALLS = 6
MAX_OPEN_LINES = 120
MAX_CHUNKS = 40  # the prompt keeps at most this many chunks, newest searches last

SYSTEM = answer.SYSTEM.replace(
    "You answer questions about a code repository using only the numbered code chunks given.",
    """You answer questions about a code repository. You see numbered code chunks found so far.
Each turn, choose one action:
- search: find more code with a new query (use names you have seen: functions, classes, files).
- open_file: read lines of a file you know about, e.g. a function that is called but not shown.
- answer: when the chunks hold enough to answer, or no search will help.
Prefer answering early; read more only when something the answer needs is missing.
When you choose answer, fill answer, citations and found in that same reply.
When you answer, use only the numbered code chunks given.""",
)

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string", "description": "one sentence: what is missing or why you can answer"},
        "action": {"type": "string", "enum": ["search", "open_file", "answer"]},
        "query": {"type": "string"},
        "path": {"type": "string"},
        "start": {"type": "integer"},
        "end": {"type": "integer"},
        **answer.SCHEMA["properties"],
    },
    "required": ["thought", "action"],
}


class State(TypedDict):
    repo: str
    question: str
    backend: str
    chunks: list   # every chunk seen, in the order found; numbered 1..n in the prompt
    steps: list    # what the agent did, shown on the website
    tool_calls: int
    action: dict


def add_chunks(state, new):
    seen = {c["id"] for c in state["chunks"]}
    added = [c for c in new if c["id"] not in seen]
    state["chunks"] = (state["chunks"] + added)[-MAX_CHUNKS:]
    return len(added)


def report(config):
    """The progress reporter passed to ask(), carried in the graph's config."""
    return (config or {}).get("configurable", {}).get("progress", answer.quiet)


def first_search(state: State, config=None):
    report(config)("Searching the code", done=False, kind="search")
    add_chunks(state, retrieve.hybrid(state["repo"], state["question"]))
    state["steps"].append(f'search("{state["question"]}") -> {len(state["chunks"])} chunks')
    report(config)(f'Searched the code: {len(state["chunks"])} pieces found', kind="search")
    return state


def decide(state: State, config=None):
    report(config)("Deciding whether it has enough to answer", done=False, kind="model")
    left = MAX_TOOL_CALLS - state["tool_calls"]
    prompt = (answer.build_prompt(state["question"], state["chunks"])
              + "\n\n<steps_so_far>\n" + "\n".join(state["steps"]) + "\n</steps_so_far>\n"
              + (f"You may use {left} more tool calls." if left > 0 else "No tool calls left: answer now."))
    action = ask_llm(SYSTEM, prompt, ACTION_SCHEMA, backend=state["backend"])
    if left <= 0 and action["action"] != "answer":
        action = {"action": "answer", "thought": "tool limit reached"}
    state["action"] = action
    if action["action"] == "answer":
        report(config)("Wrote the answer", kind="model")
    else:
        report(config)("Decided to read more", kind="model", more=True)
    return state


def search(state: State, config=None):
    query = state["action"].get("query") or state["question"]
    report(config)(f'Searching again for "{query}"', done=False, kind="search")
    added = add_chunks(state, retrieve.hybrid(state["repo"], query))
    state["tool_calls"] += 1
    state["steps"].append(f'search("{query}") -> {added} new chunks')
    report(config)(f'Searched again for "{query}": {added} new pieces', kind="search")
    return state


def open_file(state: State, config=None):
    action = state["action"]
    state["tool_calls"] += 1
    root = Path(state["repo"]).resolve()
    target = (root / action.get("path", "")).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        state["steps"].append(f'open_file("{action.get("path")}") -> no such file')
        return state
    lines = target.read_text(errors="replace").split("\n")
    start = max(1, action.get("start") or 1)
    end = min(len(lines), action.get("end") or start + MAX_OPEN_LINES - 1, start + MAX_OPEN_LINES - 1)
    path = target.relative_to(root).as_posix()
    chunk = {"id": f"{path}:{start}-{end}", "kind": "opened", "file": path, "name": f"lines {start}-{end}",
             "start": start, "end": end, "part": 1, "parts": 1, "score": 0.0,
             "text": "\n".join(lines[start - 1:end])}
    add_chunks(state, [chunk])
    state["steps"].append(f'open_file("{path}", {start}, {end})')
    report(config)(f"Read `{path}` lines {start}-{end}")
    return state


def route(state: State):
    return state["action"]["action"] if state["action"]["action"] in ("search", "open_file") else END


def build_graph():
    graph = StateGraph(State)
    graph.add_node("first_search", first_search)
    graph.add_node("decide", decide)
    graph.add_node("search", search)
    graph.add_node("open_file", open_file)
    graph.set_entry_point("first_search")
    graph.add_edge("first_search", "decide")
    graph.add_conditional_edges("decide", route, {"search": "search", "open_file": "open_file", END: END})
    graph.add_edge("search", "decide")
    graph.add_edge("open_file", "decide")
    return graph.compile()


GRAPH = build_graph()


def ask(repo, question, backend=None, progress=answer.quiet):
    """Same result shape as answer.ask, plus `steps`. progress(label, done) is told each step."""
    import os
    backend = backend or os.environ.get("LLM_BACKEND", "gemini")
    began = time.time()
    state = GRAPH.invoke({"repo": str(repo), "question": question, "backend": backend, "chunks": [],
                          "steps": [], "tool_calls": 0, "action": {}},
                         {"recursion_limit": 4 * MAX_TOOL_CALLS + 6, "configurable": {"progress": progress}})
    chunks, action = state["chunks"], state["action"]
    if all(k in action for k in ("answer", "citations", "found")):
        reply = {"answer": action["answer"], "citations": action["citations"], "found": action["found"]}
        verified = answer.check_citations(reply, chunks)
        progress("Checked every citation against the code")
        result = {"question": question, **reply, "verified": verified, "chunks": chunks, "backend": backend}
    else:  # the model chose to answer but left the answer fields out: one plain answer call
        result = answer.generate(question, chunks, backend, progress)
    state["steps"].append("answer")
    return {**result, "steps": state["steps"], "mode": "agent", "seconds": round(time.time() - began, 1)}
