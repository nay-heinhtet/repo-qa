# repo-qa

Ask questions about a code repository and get answers with file and line citations.

Planned pipeline:
1. Index: clone a repo, parse Python and JavaScript into functions and classes (tree-sitter), store them in Chroma with file path, name and line numbers.
2. Retrieve: meaning-based search plus keyword search, merged.
3. Answer: send the retrieved functions to an LLM and return the answer with citations.
4. Evaluate: 20 questions with known answers, measuring answer accuracy and retrieval hit rate.

Test data lives in `test-repos/` (not committed). First test repo: hku-room-booker.

## Environment
The Python environment lives outside this folder (the drive is exFAT and cannot hold one):

    source ~/.local/share/repo-qa/venv/bin/activate
