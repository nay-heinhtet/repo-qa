# 0006 One LLM entry point; Gemini by default, Claude as an option

Status: accepted, 14 Nov 2026; P3 settled 16 Nov 2026 (spec A2, R8, D2)

## Context
The user has no Anthropic API key. The Claude Pro plan can run `claude -p` for personal use, but not as an app's key. Gemini has a free tier (Flash Lite: 15 requests a minute, 500 a day). The user wants to compare the two.

## Decision
All model calls go through `ask_llm(system, prompt, schema, backend)`. Backends: `gemini` (default, `gemini-3.5-flash-lite`, thinking low, calls spaced to 12 a minute, retries on 503/429) and `claude-cli` (`claude -p --model sonnet --tools "" --json-schema`). Both stay; the website has a model switch. hku-room-booker code is never sent to Gemini (the API refuses it).

## Consequences
Changing model is one setting. Claude runs use the user's Pro session limits (a 38-call eval run hit the limit on 16 Nov). Gemini free-tier prompts may be used by Google, so only public code goes there.
