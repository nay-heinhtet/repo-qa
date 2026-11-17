"""Command line:
    python -m repo_qa index <repo-path>      chunk, summarise and store a repo in Chroma, then list it
                                             (website and search; a folder outside repo-qa is "your project")
    python -m repo_qa overview <repo-path>   print the repo summary, file map and starter questions
    python -m repo_qa ask <repo-path> "question" [--backend gemini|claude-cli] [--method hybrid|dense|bm25]
    python -m repo_qa search "what you need" [--repo NAME] [--top 5] [--short] [--docs] [--verbose]
                                             the matching code in every indexed repo, no model calls

From any folder, `repoqa` runs the same commands (a launcher in ~/.local/bin).
"""

import argparse
import time
from pathlib import Path
from collections import defaultdict

from repo_qa import answer, indexer, overview, registry, retrieve, search, store
from repo_qa.llm import BACKENDS

SANITY_QUESTIONS = [
    "What does this repo do?",
    "How is the LightRAG instance initialized?",
    "How are images inside a document processed?",
]


def index(repo):
    began = time.time()
    folder = Path(repo).resolve()
    old = registry.repos().get(store.collection_name(folder), {})
    title, source = old.get("title", folder.name), old.get("source", str(folder))
    local = old.get("local", not folder.is_relative_to(registry.ROOT))
    try:
        name, count = indexer.index_and_list(folder, title, source, local)
    except ValueError as error:
        raise SystemExit(error)
    print(f"stored {count} chunks as '{name}' in {time.time() - began:.1f} s")

    # Sanity check: the top 3 chunks for a few questions, by meaning only.
    for question in SANITY_QUESTIONS:
        print(f"\n{question}")
        result = collection.query(query_texts=[question], n_results=3)
        for meta, distance in zip(result["metadatas"][0], result["distances"][0]):
            print(f'  {distance:.3f}  {meta["file"]}:{meta["start"]}-{meta["end"]}  {meta["kind"]}  {meta["name"]}')


def show_overview(repo):
    data = overview.overview(repo)
    points = data["what_it_does"]
    print("\nWHAT IT DOES")
    for point in [points] if isinstance(points, str) else points:  # a string in caches written before 17 Nov
        print(f"  - {point}")
    print("\nPROBLEM IT SOLVES")
    for point in data["problem"]:
        print(f"  - {point}")
    print("\nFEATURES")
    for feature in data["features"]:
        where = f' ({feature["file"]})' if feature.get("file") else ""
        print(f'  - {feature["name"]}: {feature["how"]}{where}')
    print("\nTERMS")
    for term in data["terms"]:
        print(f'  - {term["term"]}: {term["meaning"]}')

    print("\nFILES")
    by_folder = defaultdict(list)
    for f in data["files"]:
        by_folder[f["folder"]].append(f)
    for folder in sorted(by_folder):
        print(f"\n  {folder}/")
        for f in by_folder[folder]:
            print(f'    {f["file"].split("/")[-1]:<34} {f["purpose"]}')

    print("\nSTARTER QUESTIONS")
    for number, question in enumerate(data["starter_questions"], 1):
        print(f"  {number}. {question}")


def ask(repo, question, backend, method):
    result = answer.ask(repo, question, backend=backend, method=method)
    print(f'\n{result["answer"]}\n')
    for n, chunk in enumerate(result["chunks"], 1):
        print(f'  [{n}] {chunk["file"]}:{chunk["start"]}-{chunk["end"]}  {chunk["name"]}')
    print("\nCITATIONS")
    for c in result["citations"]:
        print(f'  [{c["chunk_id"]}] {c["file"]}:{c["start"]}-{c["end"]}  {"ok" if c["valid"] else "OUTSIDE ITS CHUNK"}')
    status = "verified" if result["verified"] else "UNVERIFIED"
    print(f'\nfound={result["found"]}  {status}  {result["backend"]}  {result["seconds"]} s')


def show_search(query, repo, top, short, docs, verbose):
    retrieve.LOG = verbose
    try:
        hits = search.search(query, repo, top, docs)
    except ValueError as error:
        raise SystemExit(error)
    print(search.as_text(hits, short))


def main():
    parser = argparse.ArgumentParser(prog="python -m repo_qa")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in [("index", "chunk, summarise and store a repo in Chroma"),
                            ("overview", "print the repo summary, file map and starter questions")]:
        commands.add_parser(name, help=help_text).add_argument("repo", help="path to the repo folder")
    asker = commands.add_parser("ask", help="answer a question with file:line citations")
    asker.add_argument("repo", help="path to the repo folder (indexed first)")
    asker.add_argument("question")
    asker.add_argument("--backend", choices=BACKENDS, help="default: LLM_BACKEND from .env")
    asker.add_argument("--method", choices=list(retrieve.METHODS), default="hybrid")
    searcher = commands.add_parser("search", help="the matching code in every indexed repo, no model calls")
    searcher.add_argument("query", help='what you are looking for, e.g. "parse tables from PDFs"')
    searcher.add_argument("--repo", help="search one repo only, by its name (see the home page or list_repos)")
    searcher.add_argument("--top", type=int, default=search.TOP, help=f"how many matches (default {search.TOP})")
    searcher.add_argument("--short", action="store_true", help=f"only the first {search.SHORT_LINES} lines of each match")
    searcher.add_argument("--docs", action="store_true", help="also search README and docs sections (code only by default)")
    searcher.add_argument("--verbose", action="store_true", help="also print how long each repo's keyword index took to build")
    args = parser.parse_args()

    if args.command == "index":
        index(args.repo)
    elif args.command == "overview":
        show_overview(args.repo)
    elif args.command == "ask":
        ask(args.repo, args.question, args.backend, args.method)
    elif args.command == "search":
        show_search(args.query, args.repo, args.top, args.short, args.docs, args.verbose)
