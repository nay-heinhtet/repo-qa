# repo-qa

A tool that answers questions about a code repository and cites the file and lines each answer comes from.

## Language

**Chunk**:
One piece of code that is saved in the database and can be found by a search. Every chunk knows its file, name, start line and end line.
_Avoid_: Node, snippet, block

**Function chunk**:
A chunk holding one function, or one method of a class.
_Avoid_: Symbol chunk, method chunk

**Class header**:
A chunk holding a class from its first line down to the line before its first method: its docstring and fields. A class with methods has a class header and no chunk for the whole class. A class with no methods is one class header.
_Avoid_: Class chunk, whole-class chunk

**File overview**:
A chunk holding a stretch of a file's code that is not a function or a class: the top docstring, imports and constants. A file has one file overview per such stretch, so it can have several.
_Avoid_: File header, module chunk

**Part**:
One piece of a chunk that was too long to be read whole. All parts of a chunk keep the chunk's name and their own line range.
_Avoid_: Sub-chunk, fragment

**Doc section**:
A chunk holding one heading of a Markdown document (the README or a file under docs/) and the text below it, up to the next heading.
_Avoid_: Markdown chunk, paragraph

**File summary**:
A chunk holding one sentence on what a whole file is for, written by a model from the file's outline. Its citation is the whole file.
_Avoid_: File description, docstring

**Repo overview**:
The starting map of a repo: a short summary of what it does, every file's file summary grouped by folder, and starter questions.
_Avoid_: README summary, repo map

**Starter question**:
A question in the repo overview that a newcomer should ask next to understand how the code works.
_Avoid_: Suggested question, example query

**Citation**:
A file and line range that an answer points to as its source, written `file:start-end`.
_Avoid_: Reference, source link

**Verified answer**:
An answer whose every citation lies inside the chunks that were given to the model (a citation may cross from one part of a function into the next). Any other answer is unverified.
_Avoid_: Checked answer, grounded answer

**Hit**:
An evaluation question for which at least one retrieved chunk overlaps the expected lines.
_Avoid_: Match, recall
