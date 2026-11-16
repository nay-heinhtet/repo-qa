"use client";

import { ReactNode } from "react";
import { Overview } from "../lib/api";
import { inline } from "./AnswerText";

// The repo overview (GLOSSARY: Repo overview) as a brief: each part has its label in the margin.
// Technical terms in the brief link down to their meaning in the Terms list.
export default function OverviewPanel({ overview, onAsk, onOpen }: {
  overview: Overview;
  onAsk: (question: string) => void;
  onOpen: (path: string) => void;
}) {
  const linkTerms = termLinker(overview.terms.map((t) => t.term));
  const text = (s: string) => inline(s, undefined, null, linkTerms);

  const folders = new Map<string, Overview["files"]>();
  for (const f of overview.files) {
    folders.set(f.folder, [...(folders.get(f.folder) ?? []), f]);
  }

  return (
    <div className="space-y-8">
      <Row label="What it does">
        <p className="text-[1.25rem] leading-[1.55]">{text(overview.what_it_does)}</p>
      </Row>

      <Row label="The problem">
        <ul className="list-disc space-y-1.5 pl-5 marker:text-graphite">
          {overview.problem.map((p) => <li key={p}>{text(p)}</li>)}
        </ul>
      </Row>

      <Row label="How it solves it">
        <dl className="space-y-3">
          {overview.features.map((f) => (
            <div key={f.name}>
              <dt className="font-semibold">{f.name}</dt>
              <dd className="text-ink/85">{text(f.how)}</dd>
            </div>
          ))}
        </dl>
      </Row>

      <Row label="Terms">
        <dl className="space-y-1.5">
          {overview.terms.map((t) => (
            <div key={t.term} id={termId(t.term)} className="term-entry -mx-2 rounded px-2 py-0.5">
              <dt className="inline font-semibold">{t.term}</dt>
              <dd className="inline text-ink/85">: {inline(t.meaning)}</dd>
            </div>
          ))}
        </dl>
      </Row>

      <Row label="Ask next">
        <div className="flex flex-col items-start gap-2">
          {overview.starter_questions.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onAsk(q)}
              className="border-l-2 border-rule py-0.5 pl-3 text-left hover:border-marker-edge hover:bg-sheet"
            >
              {inline(q)}
            </button>
          ))}
        </div>
      </Row>

      <Row label="Files">
        <div className="divide-y divide-rule border-y border-rule">
          {[...folders.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([folder, files]) => (
            <details key={folder} open={folders.size <= 3}>
              <summary className="cursor-pointer py-2 font-mono text-sm">
                {folder === "." ? "(top level)" : `${folder}/`}{" "}
                <span className="text-graphite">{files.length}</span>
              </summary>
              <ul className="pb-3">
                {files.map((f) => (
                  <li key={f.file}>
                    <button
                      type="button"
                      onClick={() => onOpen(f.file)}
                      className="grid w-full gap-x-3 rounded px-2 py-1 text-left hover:bg-sheet sm:grid-cols-[minmax(8rem,13rem)_1fr]"
                    >
                      <span className="font-mono text-[0.8rem] break-all">{f.file.split("/").pop()}</span>
                      <span className="text-[0.95rem] text-graphite">{inline(f.purpose)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </Row>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="grid gap-x-6 gap-y-2 sm:grid-cols-[8.5rem_minmax(0,1fr)]">
      <h2 className="pt-0.5 text-[0.95rem] font-semibold text-graphite sm:text-right">{label}</h2>
      <div className="max-w-[66ch] text-[1.0625rem] leading-[1.7]">{children}</div>
    </section>
  );
}

function termId(term: string) {
  return "term-" + term.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

// Wraps each mention of a known term in plain text with a link to its entry in Terms.
function termLinker(terms: string[]) {
  const sorted = [...terms].sort((a, b) => b.length - a.length);
  if (sorted.length === 0) return (plain: string) => plain;
  const escaped = sorted.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");
  const byLower = new Map(terms.map((t) => [t.toLowerCase(), t]));
  return (plain: string): ReactNode =>
    plain.split(pattern).map((part, i) => {
      const term = byLower.get(part.toLowerCase());
      return term && i % 2 === 1 ? (
        <a key={i} href={`#${termId(term)}`} title="See its meaning under Terms"
          className="underline decoration-marker-edge decoration-dotted decoration-2 underline-offset-[3px] hover:bg-marker">
          {part}
        </a>
      ) : part;
    });
}
