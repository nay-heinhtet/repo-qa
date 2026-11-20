"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, Health, Job, Repo } from "../lib/api";
import { useJob } from "../lib/hooks";
import { RepoTitle } from "./Chrome";
import JobProgress from "./JobProgress";

const README = "https://github.com/nay-heinhtet/repo-qa#run-it-locally";

// The home page: your own projects, the GitHub repos, and forms to add either with a progress bar.
export default function Home() {
  const [repos, setRepos] = useState<Repo[] | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => { api.repos().then(setRepos).catch((e: Error) => setError(e.message)); }, []);
  useEffect(() => {
    load();
    api.health().then(setHealth).catch(() => {});
  }, [load]);

  const mine = repos?.filter((r) => r.local) ?? [];
  const github = repos?.filter((r) => !r.local) ?? [];

  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-20">
      <h1 className="text-[clamp(2rem,5vw,3rem)] font-semibold leading-tight tracking-tight">repo-qa</h1>
      <p className="mt-2 max-w-[56ch] text-lg text-graphite">
        Ask questions about a codebase. Every answer points to the file and lines it came from, checked against the code the model read.
      </p>

      {error && <p role="alert" className="mt-6 border-l-2 border-bad pl-3 text-bad">{error}</p>}

      {/* the public demo (adding turned off) has no projects of yours, so the heading would only say "none" */}
      {(mine.length > 0 || health?.allow_add_repos) && <>
        <h2 className="mt-12 mb-3 text-xl font-semibold">Your projects</h2>
        {repos === null ? <p className="text-graphite">Loading…</p> : mine.length === 0 ? (
          <p className="text-graphite">None yet. Add a folder on this computer below.</p>
        ) : <RepoList repos={mine} />}
      </>}

      <h2 className="mt-12 mb-3 text-xl font-semibold">GitHub repos</h2>
      {repos === null ? <p className="text-graphite">Loading…</p> : github.length === 0 ? (
        <p className="text-graphite">None yet.{health?.allow_add_repos && " Add a public GitHub repo below."}</p>
      ) : <RepoList repos={github} />}

      {/* the public demo turns adding off (ADR 0014): say so where the forms would be */}
      {health && !health.allow_add_repos && (
        <p className="mt-6 border-l-2 border-rule pl-3 text-graphite">
          This demo has one repo. To add your own, run repo-qa locally (see
          the <a href={README} className="text-ink underline underline-offset-2">README</a>).
        </p>
      )}

      {health?.allow_add_repos && (
        <>
          <AddForm title="Add a folder on this computer" label="Full path of the folder" button="Index this folder"
            placeholder="/mnt/shared/projects/my-project" queue={api.addFolder} onDone={load}
            note="Indexed where it is; nothing is copied. Up to 3,000 Python and Markdown files. Summaries cost one Gemini call per 10 files." />
          <AddForm title="Add a GitHub repo" label="GitHub repository URL" button="Clone and index"
            placeholder="https://github.com/owner/repo" queue={api.addRepo} onDone={load}
            note="Public repos only, up to 100 MB and 3,000 Python and Markdown files (only those are indexed). Summaries cost one Gemini call per 10 files." />
        </>
      )}
    </main>
  );
}

function RepoList({ repos }: { repos: Repo[] }) {
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {repos.map((r) => (
        <li key={r.name} className="py-4">
          <Link href={`/${r.name}`} className="font-mono text-lg font-semibold break-all hover:underline">
            <RepoTitle repo={r} />
          </Link>
          <p className="text-sm text-graphite break-all">
            {r.chunks.toLocaleString()} chunks indexed{r.local && <> from <span className="font-mono">{r.source}</span></>}
          </p>
        </li>
      ))}
    </ul>
  );
}

function AddForm({ title, label, button, placeholder, note, queue, onDone }: {
  title: string; label: string; button: string; placeholder: string; note: string;
  queue: (value: string) => Promise<Job>; onDone: () => void;
}) {
  const [value, setValue] = useState("");
  const { job, error, busy, start } = useJob(onDone);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await start(() => queue(value.trim()))) setValue("");
  }

  return (
    <section className="mt-12">
      <h2 className="mb-3 text-xl font-semibold">{title}</h2>
      <form onSubmit={submit} className="flex flex-wrap gap-2">
        <input value={value} onChange={(e) => setValue(e.target.value)} placeholder={placeholder} aria-label={label}
          className="min-w-0 flex-1 rounded-md border border-rule bg-sheet px-3 py-2 font-mono text-sm" />
        <button type="submit" disabled={!value.trim() || busy}
          className="rounded-md bg-ink px-4 py-2 text-paper disabled:opacity-50">{button}</button>
      </form>
      <p className="mt-2 text-sm text-graphite">{note}</p>
      {error && <p role="alert" className="mt-2 text-sm text-bad">{error}</p>}
      {job && <JobProgress job={job} />}
    </section>
  );
}
