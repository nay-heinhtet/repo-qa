"use client";

import { useEffect, useRef, useState } from "react";
import { Answer, api, Flow, Overview } from "../lib/api";
import { inline } from "./AnswerText";
import { Settings } from "../lib/hooks";
import AnswerPanel from "./AnswerPanel";
import AskProgress, { addEvent, Progress, startProgress } from "./AskProgress";
import AskNext from "./AskNext";
import CodeViewer, { Selection } from "./CodeViewer";
import QuestionBox from "./QuestionBox";

// Asking and reading: the question box, then the answer (or the starter questions) on the left
// and the code viewer on the right.
export default function Workspace({ repo, overview, flow, settings, onSettings, backends, initialQuestion, initialFile, onAsked }: {
  repo: string;
  overview: Overview;
  flow: Flow | null;
  initialFile?: string;
  settings: Settings;
  onSettings: (next: Settings) => void;
  backends: string[];
  initialQuestion?: string;
  onAsked?: (question: string) => void;
}) {
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [asking, setAsking] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<Selection | null>(initialFile ? { path: initialFile } : null);
  const [activeCite, setActiveCite] = useState<number | null>(null);
  const [lastQuestion, setLastQuestion] = useState(initialQuestion ?? "");
  const askedInitial = useRef(false);

  async function ask(question: string) {
    setLastQuestion(question);
    setAsking(true);
    setError(null);
    setActiveCite(null);
    setProgress(startProgress());
    onAsked?.(question);
    try {
      const result = await api.ask(repo, question, settings.backend, settings.mode,
        (event) => setProgress((p) => p && addEvent(p, event)));
      setAnswer(result);
      if (result.citations[0]) showCitation(result, result.citations[0].chunk_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAsking(false);
      setProgress(null);
    }
  }

  function showCitation(result: Answer, n: number) {
    setActiveCite(n);
    const citation = result.citations.find((c) => c.chunk_id === n);
    const chunk = result.chunks[n - 1];
    if (citation) setSelection({ path: citation.file, start: citation.start, end: citation.end, valid: citation.valid });
    else if (chunk) setSelection({ path: chunk.file, start: chunk.start, end: chunk.end });
  }

  // A question passed in the address is asked once when the page opens; repeats come from the cache.
  useEffect(() => {
    if (initialQuestion && !askedInitial.current) {
      askedInitial.current = true;
      queueMicrotask(() => ask(initialQuestion));
    }
  });

  const step = flow?.steps.find((s) => s.file === selection?.path);
  const stepNumber = step && flow ? flow.steps.indexOf(step) + 1 : 0;
  const others = overview.starter_questions.filter((q) => q !== answer?.question);

  return (
    <div className="grid h-full min-h-0 grid-cols-1 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <div className="min-h-0 overflow-y-auto px-4 py-5 sm:px-6">
        <QuestionBox key={lastQuestion} initial={lastQuestion} busy={asking} settings={settings}
          onSettings={onSettings} backends={backends} onAsk={ask} />

        {error && <p role="alert" className="mt-4 border-l-2 border-bad pl-3 text-bad">{error}</p>}

        <div className="mt-8 space-y-10">
          {step && (
            <section className="border-l-2 border-marker-edge pl-4">
              <h2 className="font-semibold">
                About this file <span className="font-normal text-graphite">(step {stepNumber} of {flow?.steps.length})</span>
              </h2>
              <p className="font-mono text-sm">{step.file}</p>
              <p className="mt-1 leading-relaxed">{inline(step.explanation)}</p>
              {step.question !== answer?.question && (
                <button type="button" onClick={() => ask(step.question)}
                  className="mt-2 border-l-2 border-rule py-1 pl-3 text-left hover:border-marker-edge hover:bg-sheet">
                  Ask: {inline(step.question)}
                </button>
              )}
            </section>
          )}
          {asking && progress && <AskProgress progress={progress} />}
          {answer && (
            <div className={asking ? "opacity-50" : ""}>
              <AnswerPanel answer={answer} active={activeCite} onCite={(n) => showCitation(answer, n)} />
            </div>
          )}
          <AskNext questions={others} onAsk={ask} title={answer ? "Ask next" : "Where to go next"} />
        </div>
      </div>

      <div className="min-h-[70vh] border-t border-rule bg-sheet lg:min-h-0 lg:border-t-0 lg:border-l">
        <CodeViewer repo={repo} selection={selection} files={overview.files} flow={flow} onOpen={(path) => setSelection({ path })} />
      </div>
    </div>
  );
}
