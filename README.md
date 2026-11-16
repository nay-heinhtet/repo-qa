# repo-qa

Ask questions about a code repository and get answers that cite file and line, checked against the code the model actually read.

## Run it

    ./run.sh            # back end on :8000, website on :3000; open http://localhost:3000
    ./run.sh --dev      # same, but the website reloads when you edit it

Needs `.env` with `GEMINI_API_KEY` (see `.env.example`). The Claude option uses your own `claude` login.

## How it works

1. **Index** (`repo_qa/chunker.py`, `indexer.py`): tree-sitter splits Python into functions, class headers and file overviews; Markdown into doc sections. A model writes one sentence per file. Everything goes into Chroma with file, name and line numbers.
2. **Retrieve** (`retrieve.py`): meaning search (Chroma) + keyword search (BM25), merged by reciprocal rank fusion; the other parts of a long function come along.
3. **Answer** (`answer.py`, `llm.py`): Gemini or Claude answers in a JSON schema with citations; every citation is checked to lie inside the code it was given.
4. **Agent** (`agent.py`): a LangGraph loop that may search again or open a file, up to 6 times, before answering.
5. **Web** (`api.py`, `web/`): FastAPI holds the key and serves the Next.js page.
6. **Evaluate** (`eval/`): 20 questions on RAG-Anything; results in `eval/RESULTS.md`.

Decisions and their reasons: `docs/adr/`. Terms: `GLOSSARY.md`.

## Command line

    source ~/.local/share/repo-qa/venv/bin/activate
    python -m repo_qa index test-repos/RAG-Anything
    python -m repo_qa overview test-repos/RAG-Anything
    python -m repo_qa ask test-repos/RAG-Anything "How is the LightRAG instance initialized?"
    python eval/run_eval.py --retrieval-only        # no model calls
    python -m pytest tests

The Python environment lives outside this folder (the drive is exFAT and cannot hold one).
