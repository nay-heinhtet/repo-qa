# 0008 Agent mode: a LangGraph loop whose tool calls are structured-output actions

Status: accepted, 16 Nov 2026 (spec G1-G3; settles P2)

## Context
Single-shot retrieval searches once with the user's words. Some questions need a second look: a function the first chunks call, or a name the user did not know. The plan was LangGraph with Gemini's tool-calling API. The Claude option runs through `claude -p` with tools turned off, which has no tool-calling API we control.

## Decision
`repo_qa/agent.py` is a LangGraph state graph: one free search on the question, then a loop of `decide` steps. Each `decide` is one `ask_llm` call that returns a JSON action: `search(query)`, `open_file(path, start, end)` or `answer` (with the normal answer fields). At most 6 tool calls, then it must answer. The answer goes through the same citation check.

## Consequences
The agent works with both backends and stays inside the one-entry-point rule (ADR 0006). It costs 1 to 7 model calls per question instead of 1. It is not native function calling; that would be a later change if a provider-specific feature is needed.
