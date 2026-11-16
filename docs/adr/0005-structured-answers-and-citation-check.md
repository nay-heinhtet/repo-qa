# 0005 Structured answers with a citation check

Status: accepted, 7 Nov 2026; check widened 16 Nov 2026 (spec R5-R7, A4)

## Context
A model can cite lines it never saw. The website needs citations as data, not prose, to highlight them.

## Decision
The model must reply in a JSON schema: `{answer, citations: [{chunk_id, file, start, end}], found}`. Chunks are numbered 1 to n, shown with line numbers, and marked as untrusted data. `found: false` means "the code given does not answer this". After the reply, every citation is checked: it is valid only if every cited line lies inside the chunks the model was given, in that file. One invalid citation makes the answer unverified.

The first rule demanded that a citation fit inside the one chunk it named. With sibling parts (ADR 0003) the model cites ranges that cross from one part into the next, which are still grounded, so the rule was widened. `chunk_match` still records the strict result.

## Consequences
The website can show "verified" honestly. Hallucinated line numbers outside the retrieved code are caught; a wrong claim about lines that were given is not (that is what the judge in ADR 0009 measures).
