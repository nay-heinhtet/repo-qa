"""Split Python files into chunks with tree-sitter: function chunks, class headers and file overviews.
Chunks over LIMIT characters are cut into parts at line breaks. See GLOSSARY.md for the terms."""

from pathlib import Path

import tree_sitter_python
from tree_sitter import Language, Parser

parser = Parser(Language(tree_sitter_python.language()))

# Chroma's default model reads about 1,000 characters (256 tokens); longer chunks are split into parts.
LIMIT = 1000

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__"}


def split_text(text, start, limit=LIMIT):
    """Cut text at line breaks into pieces of at most `limit` characters.
    Returns (start line, end line, text) per piece. A single line over the limit stays whole."""
    pieces = []
    current = []
    size = 0
    current_start = start
    for offset, line in enumerate(text.split("\n")):
        if current and size + 1 + len(line) > limit:
            pieces.append((current_start, start + offset - 1, "\n".join(current)))
            current = []
            size = 0
            current_start = start + offset
        size += len(line) + (1 if current else 0)
        current.append(line)
    pieces.append((current_start, start + offset, "\n".join(current)))
    return pieces


def merge(pieces, limit=LIMIT):
    """Join neighbouring pieces while the result stays within `limit` characters."""
    merged = []
    for start, end, text in pieces:
        if merged and len(merged[-1][2]) + 1 + len(text) <= limit:
            merged[-1] = (merged[-1][0], end, merged[-1][2] + "\n" + text)
        else:
            merged.append((start, end, text))
    return merged


def make_chunks(kind, file, name, pieces):
    return [
        {"kind": kind, "file": file, "name": name, "start": start, "end": end, "text": text,
         "part": number, "parts": len(pieces)}
        for number, (start, end, text) in enumerate(pieces, 1)
    ]


def definition_of(node):
    """The function or class inside a decorated_definition; any other node as is."""
    if node.type == "decorated_definition":
        inner = node.child_by_field_name("definition")
        return inner if inner else node
    return node


def name_of(node):
    name = node.child_by_field_name("name")
    return text_of(name) if name else ""


def text_of(node):
    return node.text.decode() if node.text else ""


def first_line(node):
    return node.start_point[0] + 1


def class_chunks(file, outer, node, source):
    """A class header plus one function chunk per method. `outer` includes any decorator."""
    class_name = name_of(node)
    body = node.child_by_field_name("body")
    methods = [m for m in (body.children if body else []) if definition_of(m).type == "function_definition"]

    if not methods:
        return make_chunks("class_header", file, class_name, split_text(text_of(outer), first_line(outer)))

    header_text = source[outer.start_byte:methods[0].start_byte].decode().rstrip()
    chunks = make_chunks("class_header", file, class_name, split_text(header_text, first_line(outer)))
    for method in methods:
        method_name = class_name + "." + name_of(definition_of(method))
        chunks.extend(make_chunks("function", file, method_name, split_text(text_of(method), first_line(method))))
    return chunks


def overview_chunks(file, run):
    """File overview chunks for a run of neighbouring pieces that are not functions or classes."""
    pieces = []
    for node in run:
        pieces.extend(split_text(text_of(node), first_line(node)))
    return make_chunks("file_overview", file, Path(file).name, merge(pieces))


def chunk_file(path, file):
    """Chunks of the Python file at `path`, labelled with `file` (its path relative to the repo root)."""
    source = Path(path).read_bytes()
    root = parser.parse(source).root_node
    chunks = []
    run = []

    for top in root.children:
        node = definition_of(top)
        if node.type not in ("function_definition", "class_definition"):
            run.append(top)
            continue
        chunks.extend(overview_chunks(file, run))
        run = []
        if node.type == "function_definition":
            chunks.extend(make_chunks("function", file, name_of(node), split_text(text_of(top), first_line(top))))
        else:
            chunks.extend(class_chunks(file, top, node, source))

    chunks.extend(overview_chunks(file, run))
    return chunks


def markdown_chunks(path, file):
    """Doc sections: one per heading, from the heading line down to the line before the next heading.
    Lines inside ``` code fences are never treated as headings."""
    lines = Path(path).read_text(errors="replace").split("\n")
    sections = []  # (name, start line, lines)
    in_fence = False
    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if line.startswith("#") and not in_fence or not sections:
            name = line.lstrip("#").strip() if line.startswith("#") else Path(file).name
            sections.append((name, number, []))
        sections[-1][2].append(line)

    chunks = []
    for name, start, body in sections:
        text = "\n".join(body).strip("\n")
        if text.strip():
            chunks.extend(make_chunks("doc_section", file, name, split_text("\n".join(body).rstrip("\n"), start)))
    return chunks


def skeleton(path):
    """A short outline of a file for summarising: for Python, the docstring, imports and the
    signature (plus first docstring line) of every class, method and function; for Markdown, the headings."""
    path = Path(path)
    if path.suffix == ".md":
        return "\n".join(line for line in path.read_text(errors="replace").split("\n") if line.startswith("#"))

    source = path.read_bytes()
    root = parser.parse(source).root_node
    lines = []

    def signature(node, indent):
        inner = definition_of(node)
        body = inner.child_by_field_name("body")
        header = source[node.start_byte:body.start_byte if body else node.end_byte].decode(errors="replace")
        lines.append(indent + " ".join(header.split()))
        first = body.children[0] if body and body.children else None
        if first and first.type == "expression_statement" and first.children and first.children[0].type == "string":
            doc = text_of(first).strip("\"' \n").split("\n")[0]
            lines.append(indent + '    """' + doc + '"""')
        return inner, body

    for top in root.children:
        node = definition_of(top)
        if node.type == "function_definition":
            signature(top, "")
        elif node.type == "class_definition":
            _, body = signature(top, "")
            for member in (body.children if body else []):
                if definition_of(member).type == "function_definition":
                    signature(member, "    ")
        elif top.type in ("import_statement", "import_from_statement"):
            lines.append(text_of(top))
        elif top.type == "expression_statement" and not lines:
            lines.append(text_of(top))  # module docstring
    return "\n".join(lines)


def source_files(repo):
    """Every .py file plus README.md and docs/**/*.md under `repo`, skipping SKIP_DIRS, in a stable order."""
    repo = Path(repo)
    found = list(repo.rglob("*.py")) + list((repo / "docs").rglob("*.md")) + [repo / "README.md"]
    return sorted(p for p in found if p.is_file() and not SKIP_DIRS & set(p.relative_to(repo).parts))


def chunk_repo(repo):
    chunks = []
    for path in source_files(repo):
        file = path.relative_to(repo).as_posix()
        chunks.extend(markdown_chunks(path, file) if path.suffix == ".md" else chunk_file(path, file))
    return chunks
