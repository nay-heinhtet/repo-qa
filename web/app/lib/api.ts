// Every call to the FastAPI back end. The browser only knows the back end's address;
// the LLM key lives in the back end's .env and never reaches this code.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// local: your own project, indexed where it is (source is its folder); otherwise a GitHub clone
export type Repo = { name: string; title: string; source: string; local: boolean; chunks: number };

export type FileEntry = { file: string; folder: string; purpose: string };
export type Overview = {
  what_it_does: string | string[];  // a string in caches written before 17 Nov
  problem: string[];
  features: { name: string; how: string; file?: string }[];
  terms: { term: string; meaning: string }[];
  files: FileEntry[];
  starter_questions: string[];
};

export type FlowStep = { file: string; role: string; explanation: string; question: string; layer: number };
export type Flow = { steps: FlowStep[]; edges: { from: string; to: string; label: string }[] };

export type Citation = { chunk_id: number; file: string; start: number; end: number; valid: boolean };
export type Chunk = {
  id: string; kind: string; file: string; name: string;
  start: number; end: number; part: number; parts: number; score: number;
};
export type Answer = {
  question: string; answer: string; citations: Citation[]; found: boolean; verified: boolean;
  chunks: Chunk[]; backend: string; mode: string; seconds: number; cached: boolean;
  steps?: string[];
};

export type Job = {
  id: string; url: string; status: "queued" | "running" | "done" | "failed";
  step: string; steps: string[]; progress?: number; error: string | null; repo: string | null;
};

export type Health = { backends: string[]; default_backend: string; allow_add_repos: boolean };

// What the back end says while it answers: first how long recent steps took, per kind (and, for a
// single-shot answer, how many steps there are); then each step as it starts (done: false) and ends
// (done: true), and any pause before a Gemini call (a retry when it is busy, or its rate limit).
export type AskEvent =
  | { history: Record<string, number[]>; steps: number | null }
  | { step: string; done: boolean; kind: string | null; more: boolean }
  | { wait: number; reason: string };

async function send(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error(API_URL.includes("localhost")
      ? `The back end at ${API_URL} is not answering. Start it with ./run.sh.`
      : "The server is not answering. It may be waking up: try again in a few seconds.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  return (await (await send(path, init)).json().catch(() => ({}))) as T;
}

// Asks with the steps streamed, one JSON line each; a cached answer comes back as plain JSON at once.
async function askStreamed(repo: string, question: string, backend: string, mode: string,
                           onEvent: (event: AskEvent) => void): Promise<Answer> {
  const response = await send("/ask", {
    method: "POST", body: JSON.stringify({ repo, question, backend, mode, stream: true }),
  });
  if (!response.headers.get("content-type")?.includes("ndjson") || !response.body) return response.json();
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    buffer += value ?? "";
    const lines = buffer.split("\n");
    buffer = done ? "" : lines.pop()!;
    for (const line of lines.filter((l) => l.trim())) {
      const event = JSON.parse(line);
      if ("result" in event) return event.result as Answer;
      if ("error" in event) throw new Error(event.error);
      onEvent(event);
    }
    if (done) throw new Error("The answer stopped before it finished. Try again.");
  }
}

export const api = {
  health: () => call<Health>("/health"),
  repos: () => call<Repo[]>("/repos"),
  overview: (repo: string) => call<Overview>(`/repos/${encodeURIComponent(repo)}/overview`),
  flow: (repo: string) => call<Flow>(`/repos/${encodeURIComponent(repo)}/flow`),
  addRepo: (url: string) => call<Job>("/repos", { method: "POST", body: JSON.stringify({ url }) }),
  addFolder: (path: string) => call<Job>("/folders", { method: "POST", body: JSON.stringify({ path }) }),
  reindex: (repo: string) => call<Job>(`/repos/${encodeURIComponent(repo)}/reindex`, { method: "POST" }),
  job: (id: string) => call<Job>(`/jobs/${id}`),
  ask: askStreamed,
  file: (repo: string, path: string) =>
    call<{ path: string; text: string }>(`/file?repo=${encodeURIComponent(repo)}&path=${encodeURIComponent(path)}`),
};
