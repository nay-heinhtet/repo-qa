"use client";

import { Answer } from "../lib/api";
import AnswerText from "./AnswerText";

const BACKEND_NAMES: Record<string, string> = { gemini: "Gemini", "claude-cli": "Claude" };

// One answer: the verified status, the text with [n] tabs, the agent's steps, and the numbered sources.
export default function AnswerPanel({ answer, active, onCite }: {
  answer: Answer; active: number | null; onCite: (n: number) => void;
}) {
  const cited = [...new Set(answer.citations.map((c) => c.chunk_id))];
  return (
    <article>
      <h2 className="mb-2 text-xl font-semibold leading-snug">{answer.question}</h2>
      <p className={`mb-4 text-sm ${answer.verified ? "text-ok" : "text-bad"}`}>
        {!answer.found ? "The code found does not answer this." :
          answer.verified ? "Verified: every citation is inside the code the model read." :
            "Unverified: a citation points outside the code the model read."}
        <span className="text-graphite"> {answer.mode === "agent" ? "Agent" : "Quick answer"} with {BACKEND_NAMES[answer.backend] ?? answer.backend},{" "}
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
