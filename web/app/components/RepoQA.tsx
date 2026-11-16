"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Answer, api, Health, Job, Overview, Repo } from "../lib/api";
import AnswerText from "./AnswerText";
import CodeViewer, { Selection } from "./CodeViewer";
import OverviewPanel from "./OverviewPanel";

const BACKEND_NAMES: Record<string, string> = { gemini: "Gemini", "claude-cli": "Claude" };
const MODES = [
  {
    id: "single", name: "Quick",
    hint: "Quick searches the code once with your question, then the model answers from the 8 best matches. One model call, a few seconds.",
  },
  {
    id: "agent", name: "Agent",
    hint: "Agent starts with the same search, then the model may search again with new words or open a file, up to 6 times, before it answers. Better when the answer is spread across files; slower and uses more calls.",
  },
];
const BACKEND_HINTS: Record<string, string> = {
  gemini: "Gemini Flash Lite answers (free tier, 500 calls a day).",
  "claude-cli": "Claude Sonnet answers through your Claude Code login.",
};

function remembered(key: string, fallback: string) {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}
function remember(key: string, value: string) {
  try { localStorage.setItem(key, value); } catch { /* private window: not remembered */ }
}

export default function RepoQA() {
  const [health, setHealth] = useState<Health | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [repo, setRepo] = useState("");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [question, setQuestion] = useState("");
  const [backend, setBackend] = useState("gemini");
  const [mode, setMode] = useState("single");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [job, setJob] = useState<Job | null>(null);

  const loadRepos = useCallback(async (select?: string) => {
    const list = await api.repos();
    setRepos(list);
    const wanted = select ?? remembered("repo", "");
    setRepo(list.some((r) => r.name === wanted) ? wanted : list[0]?.name ?? "");
  }, []);

  useEffect(() => {
    api.health()
      .then((h) => {
        setHealth(h);
        setBackend(h.backends.includes(remembered("backend", "")) ? remembered("backend", "") : h.default_backend);
        setMode(remembered("mode", "single"));
        return loadRepos();
      })
      .catch((e: Error) => setError(e.message));
  }, [loadRepos]);

  useEffect(() => {
    if (!repo) return;
    remember("repo", repo);
    api.overview(repo).then(setOverview).catch((e: Error) => setError(e.message));
  }, [repo]);

  // Poll an index job once a second until it finishes.
  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const timer = setTimeout(() => {
      api.job(job.id).then((next) => {
        setJob(next);
        if (next.status === "done" && next.repo) loadRepos(next.repo);
      }).catch((e: Error) => setError(e.message));
    }, 1000);
    return () => clearTimeout(timer);
  }, [job, loadRepos]);

  async function ask(text: string) {
    const q = text.trim();
    if (q.length < 3 || !repo) return;
    setQuestion(q);
    setAsking(true);
    setError(null);
    setActiveCite(null);
    try {
      const result = await api.ask(repo, q, backend, mode);
      setAnswer(result);
      const first = result.citations[0];
      if (first) showCitation(result, first.chunk_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAsking(false);
    }
  }

  function showCitation(result: Answer, n: number) {
    setActiveCite(n);
    const citation = result.citations.find((c) => c.chunk_id === n);
    const chunk = result.chunks[n - 1];
    if (citation) {
      setSelection({ path: citation.file, start: citation.start, end: citation.end, valid: citation.valid });
    } else if (chunk) {
      setSelection({ path: chunk.file, start: chunk.start, end: chunk.end });
    }
  }

  async function addRepo(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setJob(await api.addRepo(repoUrl.trim()));
      setRepoUrl("");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const current = repos.find((r) => r.name === repo);

  return (
    <div className="flex min-h-screen flex-col lg:h-screen">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-3 border-b border-rule px-4 py-3 sm:px-6">
        <h1 className="text-xl font-semibold tracking-tight">repo-qa</h1>
        <label className="flex items-center gap-2">
          <span className="sr-only">Repository</span>
          <select
            value={repo}
            onChange={(e) => {
              if (e.target.value === repo) return;
              setOverview(null); setAnswer(null); setSelection(null); setRepo(e.target.value);
            }}
            className="max-w-[16rem] rounded-md border border-rule bg-sheet px-2 py-1 font-mono text-sm"
          >
            {repos.map((r) => <option key={r.name} value={r.name}>{r.title}</option>)}
          </select>
        </label>
        {current && (
          <span className="text-sm text-graphite">{current.chunks.toLocaleString()} chunks indexed</span>
        )}
        {health?.allow_add_repos && (
          <button type="button" onClick={() => setAdding(!adding)} className="text-sm underline-offset-2 hover:underline" aria-expanded={adding}>
            {adding ? "Close" : "Add a GitHub repo"}
          </button>
        )}
      </header>

      {adding && (
        <div className="border-b border-rule bg-sheet px-4 py-3 sm:px-6">
          <form onSubmit={addRepo} className="flex flex-wrap items-center gap-2">
            <input
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              aria-label="GitHub repository URL"
              className="min-w-0 flex-1 rounded-md border border-rule bg-paper px-3 py-1.5 font-mono text-sm sm:max-w-md"
            />
            <button type="submit" className="rounded-md bg-ink px-3 py-1.5 text-sm text-paper disabled:opacity-50"
              disabled={!repoUrl.trim() || job?.status === "queued" || job?.status === "running"}>
              Clone and index
            </button>
          </form>
          <p className="mt-2 text-sm text-graphite">
            Public repos only, up to 100 MB and 3,000 files. Python and Markdown files are indexed; each 10 files cost one Gemini call for their summaries.
          </p>
          {job && (
            <div className="mt-2 text-sm" aria-live="polite">
              <span className={job.status === "failed" ? "text-bad" : job.status === "done" ? "text-ok" : ""}>
                {job.status === "failed" ? `Failed: ${job.error}` : job.status === "done" ? `Indexed. ${job.step}` : `${job.status}: ${job.step}`}
              </span>
            </div>
          )}
        </div>
      )}

      <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <section className="min-h-0 overflow-y-auto px-4 py-6 sm:px-6">
          {current && (
            <div className="mb-6">
              <h2 className="font-mono text-[clamp(1.5rem,3.2vw,2.25rem)] font-semibold leading-tight tracking-tight break-words">
                <span className="text-graphite">{current.title.split("/")[0]}/</span>{current.title.split("/")[1]}
              </h2>
              <a href={current.source} target="_blank" rel="noreferrer" className="text-sm text-graphite underline-offset-2 hover:underline">
                View on GitHub
              </a>
            </div>
          )}
          <form onSubmit={(e) => { e.preventDefault(); ask(question); }} className="mb-10 border-b border-rule pb-6">
            <label htmlFor="question" className="mb-2 block font-semibold">
              Ask a question about this code
            </label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(question); } }}
              rows={2}
              placeholder="How does a document get from file to stored content?"
              className="w-full resize-y rounded-md border border-rule bg-sheet px-3 py-2 text-[1.0625rem] leading-snug"
            />
            <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
              <fieldset className="flex items-center gap-1">
                <legend className="sr-only">Model</legend>
                {(health?.backends ?? ["gemini"]).map((b) => (
                  <Toggle key={b} on={backend === b} onClick={() => { setBackend(b); remember("backend", b); }}>
                    {BACKEND_NAMES[b] ?? b}
                  </Toggle>
                ))}
              </fieldset>
              <fieldset className="flex items-center gap-1">
                <legend className="sr-only">Mode</legend>
                {MODES.map((m) => (
                  <Toggle key={m.id} on={mode === m.id} title={m.hint} onClick={() => { setMode(m.id); remember("mode", m.id); }}>
                    {m.name}
                  </Toggle>
                ))}
              </fieldset>
              <button type="submit" disabled={asking || question.trim().length < 3}
                className="ml-auto rounded-md bg-ink px-4 py-1.5 text-paper disabled:opacity-50">
                {asking ? "Reading the code…" : "Ask"}
              </button>
            </div>
            <p className="mt-3 max-w-[66ch] text-sm leading-relaxed text-graphite" aria-live="polite">
              {MODES.find((m) => m.id === mode)?.hint} {BACKEND_HINTS[backend] ?? ""}
            </p>
          </form>

          {error && <p role="alert" className="mb-6 border-l-2 border-bad pl-3 text-bad">{error}</p>}

          {answer ? (
            <AnswerPanel answer={answer} active={activeCite} onCite={(n) => showCitation(answer, n)}
              onBack={() => { setAnswer(null); setSelection(null); }} />
          ) : overview ? (
            <OverviewPanel overview={overview} onAsk={ask} onOpen={(path) => setSelection({ path })} />
          ) : (
            !error && repo && <p className="text-graphite">Loading the overview…</p>
          )}
          {!repo && !error && repos.length === 0 && health && (
            <p className="text-graphite">No repos yet. Add a public GitHub repo above to start.</p>
          )}
        </section>

        <aside className="min-h-[60vh] border-t border-rule bg-sheet lg:min-h-0 lg:border-l lg:border-t-0">
          {repo && <CodeViewer repo={repo} selection={selection} />}
        </aside>
      </main>
    </div>
  );
}

function Toggle({ on, onClick, title, children }: { on: boolean; onClick: () => void; title?: string; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} title={title} aria-pressed={on}
      className={`rounded-md px-2.5 py-1 ${on ? "bg-ink text-paper" : "text-graphite hover:text-ink"}`}>
      {children}
    </button>
  );
}

function AnswerPanel({ answer, active, onCite, onBack }: {
  answer: Answer; active: number | null; onCite: (n: number) => void; onBack: () => void;
}) {
  const cited = [...new Set(answer.citations.map((c) => c.chunk_id))];
  return (
    <article>
      <button type="button" onClick={onBack} className="mb-4 text-sm text-graphite hover:text-ink">← Back to the overview</button>
      <h2 className="mb-3 text-xl font-semibold leading-snug">{answer.question}</h2>
      <p className={`mb-4 text-sm ${answer.verified ? "text-ok" : "text-bad"}`}>
        {!answer.found ? "The retrieved code does not answer this." :
          answer.verified ? "Verified: every citation is inside the code the model read." :
            "Unverified: at least one citation points outside the code the model read."}
        <span className="text-graphite"> {BACKEND_NAMES[answer.backend] ?? answer.backend}, {answer.mode === "agent" ? "agent" : "quick"},{" "}
          {answer.cached ? "from cache" : `${answer.seconds} s`}</span>
      </p>
      <AnswerText text={answer.answer} onCite={onCite} active={active} />

      {answer.steps && answer.steps.length > 0 && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-graphite">What the agent did ({answer.steps.length} steps)</summary>
          <ol className="mt-2 list-decimal pl-6 font-mono text-[0.8rem]">
            {answer.steps.map((s, i) => <li key={i}>{s}</li>)}
          </ol>
        </details>
      )}

      <h3 className="mt-6 mb-2 font-semibold">Sources</h3>
      <ol className="space-y-1">
        {answer.chunks.map((c, i) => {
          const n = i + 1;
          const isCited = cited.includes(n);
          return (
            <li key={c.id}>
              <button type="button" onClick={() => onCite(n)}
                className={`flex w-full items-baseline gap-3 rounded px-1 py-0.5 text-left hover:bg-sheet ${isCited ? "" : "opacity-60"}`}>
                <span className={`w-6 shrink-0 text-center font-mono text-xs ${isCited ? "rounded-[3px] bg-marker" : ""} ${active === n ? "bg-marker-edge" : ""}`}>{n}</span>
                <span className="min-w-0 shrink truncate font-mono text-[0.78rem]" title={`${c.file}:${c.start}-${c.end}`}>{c.file}:{c.start}-{c.end}</span>
                <span className="hidden min-w-0 flex-1 truncate text-sm text-graphite xl:inline">{c.name}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </article>
  );
}
