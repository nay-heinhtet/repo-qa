"""One entry point for every model call: ask_llm(system, prompt, schema).

Backends, chosen by the `backend` argument or the LLM_BACKEND environment variable:
- gemini:     Google Gemini API, key in GEMINI_API_KEY (read from .env locally).
- claude-cli: the `claude -p` command, using your own Claude Code login. No key in this project.
LLM_BACKENDS limits which are allowed: the public demo sets it to `gemini`, since the Claude login is
personal and never goes on a server.
"""

import contextvars
import json
import os
import subprocess
import threading
import time

from dotenv import load_dotenv

load_dotenv()  # copies values from repo-qa/.env into os.environ, if the file exists

BACKENDS = tuple(os.environ.get("LLM_BACKENDS", "gemini,claude-cli").split(","))

RETRIES = 3  # for Gemini 503 (overloaded) and 429 (rate limited): waits 5, 10, 20 s

# Told about each pause before a Gemini call, as (seconds, reason), so the website can show the wait.
on_wait = contextvars.ContextVar("on_wait", default=None)

last_gemini_call = 0.0
rate_lock = threading.Lock()  # the web server answers in several threads; they share one quota


def wait_for_rate_limit():
    """Space Gemini calls so they stay under GEMINI_RPM requests per minute (free tier: 15 for Flash Lite)."""
    global last_gemini_call
    gap = 60 / float(os.environ.get("GEMINI_RPM", "12"))
    with rate_lock:
        pause = last_gemini_call + gap - time.time()
        if pause > 0:
            if pause > 0.5 and on_wait.get():
                on_wait.get()(pause, "Waiting a moment to stay under Gemini's rate limit")
            time.sleep(pause)
        last_gemini_call = time.time()


def ask_llm(system, prompt, schema, backend=None):
    """Send one prompt and return the model's reply as a dict matching `schema` (a JSON Schema)."""
    backend = backend or os.environ.get("LLM_BACKEND", "gemini")
    if backend not in BACKENDS:
        raise ValueError(f"Unknown LLM_BACKEND {backend!r}; use one of {BACKENDS}")
    if backend == "gemini":
        return ask_gemini(system, prompt, schema)
    if backend == "claude-cli":
        return ask_claude_cli(system, prompt, schema)


def ask_gemini(system, prompt, schema):
    from google import genai
    from google.genai import types

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set. Put it in repo-qa/.env (see .env.example).")
    client = genai.Client(api_key=key)
    for attempt in range(RETRIES + 1):
        wait_for_rate_limit()
        try:
            response = generate(client, types, system, prompt, schema)
            break
        except genai.errors.APIError as error:
            # 503 = model overloaded, 429 = over the per-minute limit; both pass. Others (400, 404) do not.
            if error.code not in (429, 503) or attempt == RETRIES:
                raise
            pause = 5 * 2 ** attempt
            print(f"[gemini] {error.code}, retrying in {pause} s")
            if on_wait.get():
                on_wait.get()(pause, f"Gemini is busy, trying again in {pause} s")
            time.sleep(pause)
    usage = response.usage_metadata
    if usage:
        print(f"[gemini tokens] prompt={usage.prompt_token_count} thinking={usage.thoughts_token_count} "
              f"answer={usage.candidates_token_count} total={usage.total_token_count}")
    return json.loads(response.text)


def generate(client, types, system, prompt, schema):
    return client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0,
            # How long Gemini reasons before answering: minimal, low, medium, high.
            thinking_config=types.ThinkingConfig(thinking_level=os.environ.get("GEMINI_THINKING", "low").upper()),
        ),
    )


def ask_claude_cli(system, prompt, schema):
    command = [
        "claude", "-p",
        "--model", os.environ.get("CLAUDE_MODEL", "sonnet"),
        "--system-prompt", system,
        "--json-schema", json.dumps(schema),
        "--tools", "",                  # the model cannot read files or run commands
        "--no-session-persistence",     # nothing saved to your Claude Code history
        "--output-format", "json",
    ]
    result = subprocess.run(command, input=prompt, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed: {result.stderr.strip() or result.stdout.strip()}")
    reply = json.loads(result.stdout)
    if reply.get("is_error"):
        raise RuntimeError(f"claude -p returned an error: {reply.get('result')}")
    return reply["structured_output"]


def gemini_models():
    """Names of the Gemini models this key can call with generate_content."""
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return [m.name for m in client.models.list() if "generateContent" in (m.supported_actions or [])]
