"use client";

import Link from "next/link";
import { Job } from "../lib/api";

// The index job as a bar: cloning, then summarising and storing, then the summary and file map.
export default function JobProgress({ job, openLink = true }: { job: Job; openLink?: boolean }) {
  const percent = Math.round((job.status === "done" ? 1 : job.progress ?? 0) * 100);
  const failed = job.status === "failed";
  return (
    <div className="mt-4" aria-live="polite">
      <div role="progressbar" aria-label="Indexing progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}
        className="h-2.5 overflow-hidden rounded-full border border-rule bg-sheet">
        <div className={`h-full rounded-full transition-[width] duration-700 ${failed ? "bg-bad" : job.status === "done" ? "bg-ok" : "bg-marker-edge"}`}
          style={{ width: `${Math.max(percent, 2)}%` }} />
      </div>
      <p className={`mt-1.5 flex justify-between gap-4 text-sm ${failed ? "text-bad" : "text-graphite"}`}>
        <span>
          {failed ? `Failed: ${job.error}` : job.status === "done" ? "Indexed. " : job.status === "queued" ? "Waiting to start" : job.step}
          {job.status === "done" && openLink && job.repo && <Link href={`/${job.repo}`} className="text-ink underline underline-offset-2">Open it</Link>}
        </span>
        {!failed && <span className="font-mono">{percent}%</span>}
      </p>
    </div>
  );
}
