"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

export type Selection = { path: string; start?: number; end?: number; valid?: boolean; label?: string };

// Shows one file with line numbers. The selected range is marked like a highlighter stroke and
// scrolled into view; the badge says whether the citation lies in code the model was given.
export default function CodeViewer({ repo, selection }: { repo: string; selection: Selection | null }) {
  const [file, setFile] = useState<{ path: string; lines: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const firstMarked = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!selection) return;
    let cancelled = false;
    api.file(repo, selection.path)
      .then((f) => { if (!cancelled) { setFile({ path: f.path, lines: f.text.split("\n") }); setError(null); } })
      .catch((e: Error) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [repo, selection]);

  useEffect(() => {
    // Jump straight there: a smooth scroll across thousands of lines takes too long to read as an answer.
    firstMarked.current?.scrollIntoView({ block: "center" });
  }, [file, selection]);

  if (!selection) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center text-graphite">
        <p className="max-w-xs">Click a numbered source in an answer, or a file in the overview, to read the code here.</p>
      </div>
    );
  }

  const marked = (n: number) =>
    selection.start !== undefined && selection.end !== undefined && n >= selection.start && n <= selection.end;

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-rule px-4 py-3">
        <span className="font-mono text-sm break-all">
          {selection.path}
          {selection.start !== undefined && <span className="text-graphite">:{selection.start}-{selection.end}</span>}
        </span>
        {selection.valid !== undefined && (
          <span className={`text-sm ${selection.valid ? "text-ok" : "text-bad"}`}>
            {selection.valid ? "✓ inside the code the model read" : "✗ outside the code the model read"}
          </span>
        )}
      </div>
      {error && <p className="p-4 text-bad">{error}</p>}
      <div className="min-h-0 flex-1 overflow-auto py-2 font-mono text-[0.8rem] leading-[1.6]">
        {file?.path === selection.path &&
          file.lines.map((line, i) => {
            const n = i + 1;
            const isMarked = marked(n);
            return (
              <div
                key={n}
                ref={isMarked && n === selection.start ? firstMarked : undefined}
                className={`flex ${isMarked ? "line-marked" : ""}`}
              >
                <span className="w-14 shrink-0 select-none pr-4 text-right text-graphite/70">{n}</span>
                <span className="whitespace-pre pr-4">{line || " "}</span>
              </div>
            );
          })}
      </div>
    </div>
  );
}
