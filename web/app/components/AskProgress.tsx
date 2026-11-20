"use client";

import { useEffect, useState } from "react";
import { AskEvent } from "../lib/api";
import { inline } from "./AnswerText";

// plan: the kinds of step still to come ("search", "model"); current: the step running now.
export type Progress = {
  began: number;
  history: Record<string, number[]>;
  total: number | null;
  done: string[];
  plan: string[];
  current: { label: string; kind: string | null; began: number } | null;
  wait: { until: number; reason: string } | null;
};

export function startProgress(): Progress {
  return { began: Date.now(), history: {}, total: null, done: [], plan: ["search", "model"], current: null, wait: null };
}

export function addEvent(p: Progress, event: AskEvent): Progress {
  const now = Date.now();
  if ("history" in event) return { ...p, history: event.history, total: event.steps };
  if ("wait" in event) {
    // the model step starts again once the pause is over
    const until = now + event.wait * 1000;
    return { ...p, wait: { until, reason: event.reason }, current: p.current && { ...p.current, began: until } };
  }
  if (!event.done) {
    const at = event.kind ? p.plan.indexOf(event.kind) : -1;
    return { ...p, plan: at >= 0 ? p.plan.slice(at + 1) : p.plan, current: { label: event.step, kind: event.kind, began: now } };
  }
  // the agent chose to read more: one more search (or file) and one more model call to come
  const plan = event.more ? [...p.plan, "search", "model"] : p.plan;
  return { ...p, done: [...p.done, event.step], plan, current: null };
}

const middle = (xs: number[]) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)] ?? 0;

// Seconds left in a step that has run for `t` seconds: the average of how much longer the recent steps
// of its kind ran past `t`. Once it has outrun them all, a quarter of the time so far.
function remaining(history: number[], t: number) {
  const longer = history.filter((d) => d > t);
  if (longer.length === 0) return Math.max(1, t / 4);
  return longer.reduce((sum, d) => sum + d, 0) / longer.length - t;
}

export function secondsLeft(p: Progress, now: number) {
  const of = (kind: string | null) => (kind && p.history[kind]) || [];
  let left = p.plan.reduce((sum, kind) => sum + middle(of(kind)), 0);
  if (p.current) {
    left += p.wait && now < p.wait.until
      ? (p.wait.until - now) / 1000 + middle(of(p.current.kind))
      : remaining(of(p.current.kind), (now - p.current.began) / 1000);
  }
  return left;
}

// The answer being written, as a bar, the steps so far and the time left. The bar is the time so far
// against the time so far plus the estimate, so it slows down instead of stopping when a step runs long.
export default function AskProgress({ progress }: { progress: Progress }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);

  const elapsed = (now - progress.began) / 1000;
  const left = secondsLeft(progress, now);
  const percent = Math.round(Math.min(0.97, elapsed / Math.max(elapsed + left, 0.1)) * 100);
  const waiting = progress.wait && now < progress.wait.until ? progress.wait : null;
  const running = waiting
    ? `${waiting.reason.replace(/ in \d+(\.\d+)? s$/, "")} (${Math.ceil((waiting.until - now) / 1000)} s)`
    : progress.current?.label ?? (progress.done.length ? "Finishing" : "Starting");
  const count = progress.done.length;

  return (
    <div aria-live="polite">
      <div role="progressbar" aria-label="Answer progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}
        className="h-2.5 overflow-hidden rounded-full border border-rule bg-sheet">
        <div className="h-full rounded-full bg-marker-edge transition-[width] duration-500" style={{ width: `${Math.max(percent, 2)}%` }} />
      </div>
      <p className="mt-1.5 flex justify-between gap-4 text-sm text-graphite">
        <span>{progress.total ? `Step ${Math.min(count + 1, progress.total)} of ${progress.total}` : `${count} steps done`}</span>
        <span>{left >= 1 ? `about ${Math.ceil(left)} s left` : "almost done"}</span>
      </p>
      <ol className="mt-3 space-y-1 text-[0.95rem]">
        {progress.done.map((label, i) => (
          <li key={i} className="text-ink/85"><span aria-hidden className="inline-block w-5">✓</span>{inline(label)}</li>
        ))}
        <li className="text-graphite"><span aria-hidden className="inline-block w-5">…</span>{inline(running)}</li>
      </ol>
    </div>
  );
}
