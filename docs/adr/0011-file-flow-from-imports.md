# 0011 The file flowchart is built from real imports; the model only picks and explains

Status: accepted, 16 Nov 2026

## Context
A newcomer needs to see how the files connect and in what order to read them. A model asked to draw that freely could invent connections that do not exist in the code.

## Decision
`repo_qa/flow.py` reads every `import` between the repo's own Python files with Python's `ast` module (free and exact). One model call, cached with the overview, picks 8 to 10 key files, writes a role, an explanation and a suggested question for each, and labels the connections. Any connection without a real import behind it is dropped; a reversed one is flipped. Steps are numbered by import layers, so step 1 is the file that uses the others. Tests and docs are left out.

## Consequences
Every arrow on the diagram is a real import. Connections that are not imports (a function passed as an argument, a plugin registered by name) do not show. Only Python files are covered.
