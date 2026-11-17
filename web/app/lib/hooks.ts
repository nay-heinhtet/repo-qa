"use client";

import { useCallback, useEffect, useState } from "react";
import { api, Flow, Health, Job, Overview, Repo } from "./api";

function remembered(key: string, fallback: string) {
  try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
}
function remember(key: string, value: string) {
  try { localStorage.setItem(key, value); } catch { /* private window: not remembered */ }
}

export type Settings = { backend: string; mode: string };

// How to search (Quick or Agent) and which model answers; remembered per browser.
export function useSettings(): [Settings, (next: Settings) => void, Health | null] {
  const [health, setHealth] = useState<Health | null>(null);
  const [settings, setSettings] = useState<Settings>({ backend: "gemini", mode: "single" });

  useEffect(() => {
    api.health().then((h) => {
      setHealth(h);
      const backend = remembered("backend", h.default_backend);
      setSettings({
        backend: h.backends.includes(backend) ? backend : h.default_backend,
        mode: remembered("mode", "single") === "agent" ? "agent" : "single",
      });
    }).catch(() => { /* the page shows the back end error itself */ });
  }, []);

  const update = useCallback((next: Settings) => {
    setSettings(next);
    remember("backend", next.backend);
    remember("mode", next.mode);
  }, []);

  return [settings, update, health];
}

// One repo's listing entry and overview.
export function useRepo(name: string) {
  const [repo, setRepo] = useState<Repo | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [flow, setFlow] = useState<Flow | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.repos()
      .then((list) => {
        const found = list.find((r) => r.name === name);
        if (cancelled) return;
        if (!found) throw new Error(`No indexed repo called "${name}". Add it from the home page.`);
        setRepo(found);
        // The flow is extra: if it fails, the page still works without the diagram.
        api.flow(name).then((f) => { if (!cancelled) setFlow(f); }).catch(() => {});
        return api.overview(name).then((o) => { if (!cancelled) setOverview(o); });
      })
      .catch((e: Error) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [name]);

  return { repo, overview, flow, error };
}

// An index job, polled once a second until it finishes. start() takes the call that queues it.
export function useJob(onDone: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") return;
    const timer = setTimeout(() => {
      api.job(job.id).then((next) => { setJob(next); if (next.status === "done") onDone(next); })
        .catch((e: Error) => setError(e.message));
    }, 1000);
    return () => clearTimeout(timer);
  }, [job, onDone]);

  const start = useCallback(async (queue: () => Promise<Job>) => {
    setError(null);
    try { setJob(await queue()); return true; } catch (e) { setError((e as Error).message); return false; }
  }, []);

  const busy = job?.status === "queued" || job?.status === "running";
  return { job, error, busy, start };
}
