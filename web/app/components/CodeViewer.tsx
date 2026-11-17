"use client";

import { useEffect, useRef, useState } from "react";
import { api, FileEntry, Flow } from "../lib/api";
import FlowChart from "./FlowChart";

export type Selection = { path: string; start?: number; end?: number; valid?: boolean };

// The code panel: a file tree beside one open file. The selected range is marked like a
// highlighter stroke and scrolled into view; the badge says whether the citation lies in code the
// model was given. The open file's one-line purpose (from the overview) sits under its path.
export default function CodeViewer({ repo, selection, files, flow, onOpen }: {
  repo: string;
  selection: Selection | null;
  files: FileEntry[];
  flow: Flow | null;
  onOpen: (path: string) => void;
}) {
  const hasFlow = !!flow && flow.steps.length > 0;
  const [rail, setRail] = useState<"flow" | "files">("flow");
  const [file, setFile] = useState<{ path: string; lines: string[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTree, setShowTree] = useState(true);
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

  const marked = (n: number) =>
    selection?.start !== undefined && selection.end !== undefined && n >= selection.start && n <= selection.end;
  const purpose = files.find((f) => f.file === selection?.path)?.purpose;

  return (
    <div className="flex h-full min-h-0">
      {showTree && (
        <div className="flex w-64 shrink-0 flex-col border-r border-rule">
          {hasFlow && (
            <div role="tablist" className="flex border-b border-rule text-sm">
              {([["flow", "File map"], ["files", "All files"]] as const).map(([id, name]) => (
                <button key={id} type="button" role="tab" aria-selected={rail === id} onClick={() => setRail(id)}
                  className={`flex-1 px-2 py-2 ${rail === id ? "font-semibold text-ink shadow-[inset_0_-2px_0_var(--ink)]" : "text-graphite hover:text-ink"}`}>
                  {name}
                </button>
              ))}
            </div>
          )}
          <div className="min-h-0 flex-1 overflow-y-auto">
            {hasFlow && rail === "flow"
              ? <div className="p-3"><FlowChart flow={flow} variant="compact" active={selection?.path} onPick={onOpen} /></div>
              : <FileTree files={files} open={selection?.path} onOpen={onOpen} />}
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-start gap-3 border-b border-rule px-4 py-2.5">
          <button type="button" onClick={() => setShowTree(!showTree)} aria-expanded={showTree}
            className="shrink-0 rounded border border-rule px-2 py-0.5 text-sm text-graphite hover:text-ink">
            {showTree ? "Hide map" : "Show map"}
          </button>
          {selection && (
            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline gap-x-3">
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
              {purpose && <p className="text-sm text-graphite">{purpose}</p>}
            </div>
          )}
        </div>

        {error && <p className="p-4 text-bad">{error}</p>}
        {!selection ? (
          <div className="flex flex-1 items-center justify-center p-8 text-center text-graphite">
            <p className="max-w-xs">Pick a file, or click a numbered source in an answer, to read the code here.</p>
          </div>
        ) : (
          <div className="min-h-0 flex-1 overflow-auto py-2 font-mono text-[0.8rem] leading-[1.6]">
            {file?.path === selection.path &&
              file.lines.map((line, i) => {
                const n = i + 1;
                const isMarked = marked(n);
                return (
                  <div key={n} ref={isMarked && n === selection.start ? firstMarked : undefined}
                    className={`flex ${isMarked ? "line-marked" : ""}`}>
                    <span className="w-14 shrink-0 select-none pr-4 text-right text-graphite/70">{n}</span>
                    <span className="whitespace-pre pr-4">{line || " "}</span>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </div>
  );
}

function FileTree({ files, open, onOpen }: { files: FileEntry[]; open?: string; onOpen: (path: string) => void }) {
  const folders = new Map<string, FileEntry[]>();
  for (const f of files) folders.set(f.folder, [...(folders.get(f.folder) ?? []), f]);
  const openFolder = files.find((f) => f.file === open)?.folder;

  return (
    <nav aria-label="Files" className="py-2 text-sm">
      {[...folders.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([folder, entries]) => (
        <details key={folder} open={folder === "." || folder === openFolder}>
          <summary className="cursor-pointer truncate px-3 py-1 font-mono text-[0.78rem] text-graphite hover:text-ink">
            {folder === "." ? "(top level)" : `${folder}/`}
          </summary>
          <ul>
            {entries.map((f) => (
              <li key={f.file}>
                <button type="button" onClick={() => onOpen(f.file)} title={f.purpose}
                  className={`block w-full truncate py-0.5 pr-2 pl-6 text-left font-mono text-[0.78rem] hover:bg-paper ${f.file === open ? "bg-marker/60" : ""}`}>
                  {f.file.split("/").pop()}
                </button>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </nav>
  );
}
