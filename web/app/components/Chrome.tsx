"use client";

import Link from "next/link";
import { useCallback } from "react";
import { api, Repo } from "../lib/api";
import { useJob } from "../lib/hooks";
import JobProgress from "./JobProgress";

// The thin bar on the repo page: a link home.
export function TopBar() {
  return (
    <header className="border-b border-rule px-4 py-2.5 sm:px-6">
      <Link href="/" className="text-lg font-semibold tracking-tight">repo-qa</Link>
    </header>
  );
}

// "owner/name" with the owner greyed; your own projects have just a name.
export function RepoTitle({ repo }: { repo: Repo }) {
  const [owner, name] = repo.title.includes("/") ? repo.title.split("/") : [null, repo.title];
  return <>{owner && <span className="text-graphite">{owner}/</span>}{name}</>;
}

// The repo's name as the page headline, owner in grey. Your own project gets a Re-index button.
export function RepoHeading({ repo }: { repo: Repo }) {
  return (
    <div>
      <h1 className="font-mono text-[clamp(1.75rem,4.5vw,3rem)] font-semibold leading-tight tracking-tight break-words">
        <RepoTitle repo={repo} />
      </h1>
      <p className="mt-1 text-sm text-graphite break-all">
        {repo.chunks.toLocaleString()} chunks indexed.{" "}
        {repo.local ? <>From <span className="font-mono">{repo.source}</span></> : (
          <a href={repo.source} target="_blank" rel="noreferrer" className="underline-offset-2 hover:text-ink hover:underline">View on GitHub</a>
        )}
      </p>
      {repo.local && <Reindex name={repo.name} />}
    </div>
  );
}

// Index your own project again after changing it; only changed files cost Gemini calls.
function Reindex({ name }: { name: string }) {
  const { job, error, busy, start } = useJob(useCallback(() => window.location.reload(), []));
  return (
    <div className="mt-3 max-w-md">
      <button type="button" disabled={busy} onClick={() => start(() => api.reindex(name))}
        className="rounded-md border border-rule px-3 py-1 text-sm hover:bg-paper disabled:opacity-50">
        {busy ? "Re-indexing…" : "Re-index"}
      </button>
      <span className="ml-3 text-sm text-graphite">after you change the code</span>
      {error && <p role="alert" className="mt-2 text-sm text-bad">{error}</p>}
      {job && <JobProgress job={job} openLink={false} />}
    </div>
  );
}

export function Loading({ error }: { error: string | null }) {
  return (
    <p className={`px-4 py-10 sm:px-6 ${error ? "text-bad" : "text-graphite"}`}>
      {error ?? "Loading the overview…"}
    </p>
  );
}
