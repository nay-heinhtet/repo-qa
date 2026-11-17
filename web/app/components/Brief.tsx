"use client";

import { MouseEvent, ReactNode, useState } from "react";
import { Flow, Overview } from "../lib/api";
import { inline } from "./AnswerText";
import FlowChart, { ReadingOrder } from "./FlowChart";
import ZoomPan from "./ZoomPan";

// The repo overview (GLOSSARY: Repo overview) as a brief: each part has its label in the margin.
// Technical terms in the brief link down to their meaning in the Terms list, which then offers a
// way back to the sentence you were reading.
export default function Brief({ overview, flow, onPickFile }: {
  overview: Overview;
  flow: Flow | null;
  onPickFile: (file: string) => void;
}) {
  const [marked, setMarked] = useState<string | null>(null);  // the file hovered in the chart or the list
  const [layout, setLayout] = useState(0);  // bumped to put dragged boxes back
  const [cameFrom, setCameFrom] = useState<{ term: string; link: HTMLElement } | null>(null);
  const linkTerms = termLinker(overview.terms.map((t) => t.term),
    (term, e) => setCameFrom({ term, link: e.currentTarget }));

  function goBack() {
    if (!cameFrom) return;
    const { link } = cameFrom;
    link.scrollIntoView({ block: "center" });
    link.focus({ preventScroll: true });
    // drop the #term from the address so its entry is no longer marked
    history.replaceState(history.state, "", location.pathname + location.search);
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
      link.animate([{ backgroundColor: "var(--marker)" }, { backgroundColor: "transparent" }], { duration: 1500, easing: "ease-out" });
    }
    setCameFrom(null);
  }
  const text = (s: string) => inline(s, undefined, null, linkTerms);
  const points = typeof overview.what_it_does === "string" ? [overview.what_it_does] : overview.what_it_does;
  const problem = overview.problem[0];  // one; older cached overviews have two or three

  return (
    <div className="space-y-8">
      <Row label="What it does">
        <ul className="list-disc space-y-2 pl-5 text-[1.125rem] leading-[1.6] marker:text-graphite">
          {points.map((p) => <li key={p}>{text(p)}</li>)}
        </ul>
      </Row>

      {problem && (
        <Row label="The problem">
          <p>{text(problem)}</p>
        </Row>
      )}

      <Row label="How it solves it" wide>
        <div className="overflow-x-auto rounded-lg border border-rule bg-sheet">
          <table className="w-full border-collapse text-left">
            <thead className="text-[0.95rem] text-graphite">
              <tr className="border-b border-rule">
                <th scope="col" className="px-4 py-2 font-semibold">Feature</th>
                <th scope="col" className="px-4 py-2 font-semibold">How the code does it</th>
                <th scope="col" className="px-4 py-2 font-semibold">File</th>
              </tr>
            </thead>
            <tbody>
              {overview.features.map((f) => (
                <tr key={f.name} className="border-b border-rule align-top last:border-b-0">
                  <th scope="row" className="px-4 py-2.5 font-semibold sm:w-[22%]">{text(f.name)}</th>
                  <td className="px-4 py-2.5 text-ink/85">{text(f.how)}</td>
                  <td className="px-4 py-2.5 sm:w-[26%]">
                    {f.file && (
                      <button type="button" onClick={() => onPickFile(f.file!)} title="Open the code and ask about it"
                        className="rounded-sm bg-rule/50 px-1 text-left font-mono text-[0.85em] break-all hover:bg-marker">
                        {f.file}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Row>

      {flow && flow.steps.length > 0 && (
        <Row label="How the files connect" wide>
          {/* 80% of the window wide, centred on the page; the list's column is as tall as the chart and scrolls inside.
              The marked file stays marked while the pointer moves from the chart over to the list. */}
          <div onMouseLeave={() => setMarked(null)}
            className="relative left-1/2 grid w-[max(100%,80vw)] -translate-x-1/2 overflow-hidden rounded-lg border border-rule bg-sheet lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <div className="min-w-0 border-b border-rule lg:border-r lg:border-b-0">
              <ZoomPan actions={<button type="button" onClick={() => setLayout(layout + 1)} className="text-graphite underline-offset-2 hover:text-ink hover:underline">Reset boxes</button>}>
                <FlowChart key={layout} flow={flow} variant="full" marked={marked} onPick={onPickFile} onHover={(f) => f && setMarked(f)} />
              </ZoomPan>
            </div>
            <div className="relative min-h-0">
              <ReadingOrder flow={flow} onPick={onPickFile} marked={marked} onHover={setMarked}
                className="max-h-[28rem] overflow-y-auto px-5 py-4 lg:absolute lg:inset-0 lg:max-h-none" />
            </div>
          </div>
        </Row>
      )}

      <Row label="Terms">
        <dl className="space-y-1.5">
          {overview.terms.map((t) => (
            <div key={t.term} id={termId(t.term)} className="term-entry -mx-2 rounded px-2 py-0.5">
              <dt className="inline font-semibold">{t.term}</dt>
              <dd className="inline text-ink/85">: {inline(t.meaning)}</dd>
              {cameFrom?.term === t.term && (
                <button type="button" onClick={goBack}
                  className="ml-2 rounded border border-marker-edge bg-sheet px-1.5 text-sm whitespace-nowrap hover:bg-paper">
                  ↑ Back to where you were
                </button>
              )}
            </div>
          ))}
        </dl>
      </Row>

    </div>
  );
}

// A wide row puts its label above and uses the full width.
export function Row({ label, children, wide }: { label: string; children: ReactNode; wide?: boolean }) {
  if (wide) return (
    <section>
      <h2 className="mb-2 text-[0.95rem] font-semibold text-graphite">{label}</h2>
      <div className="min-w-0 text-[1.0625rem] leading-[1.7]">{children}</div>
    </section>
  );
  return (
    <section className="grid gap-x-6 gap-y-2 sm:grid-cols-[8.5rem_minmax(0,1fr)]">
      <h2 className="pt-0.5 text-[0.95rem] font-semibold text-graphite sm:text-right">{label}</h2>
      <div className="max-w-[66ch] min-w-0 text-[1.0625rem] leading-[1.7]">{children}</div>
    </section>
  );
}

function termId(term: string) {
  return "term-" + term.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

// Wraps each mention of a known term in plain text with a link to its entry in Terms.
function termLinker(terms: string[], onFollow: (term: string, e: MouseEvent<HTMLAnchorElement>) => void) {
  const sorted = [...terms].sort((a, b) => b.length - a.length);
  if (sorted.length === 0) return (plain: string) => plain;
  const escaped = sorted.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");
  const byLower = new Map(terms.map((t) => [t.toLowerCase(), t]));
  return (plain: string): ReactNode =>
    plain.split(pattern).map((part, i) => {
      const term = byLower.get(part.toLowerCase());
      return term && i % 2 === 1 ? (
        <a key={i} href={`#${termId(term)}`} title="See its meaning under Terms" onClick={(e) => onFollow(term, e)}
          className="underline decoration-marker-edge decoration-dotted decoration-2 underline-offset-[3px] hover:bg-marker">
          {part}
        </a>
      ) : part;
    });
}
