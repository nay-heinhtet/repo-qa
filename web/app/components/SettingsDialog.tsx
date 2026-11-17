"use client";

import { useRef } from "react";
import { Settings } from "../lib/hooks";

const MODES = [
  {
    id: "single", name: "Quick answer",
    detail: "Searches once, then answers. About 3 seconds. Good for “where is X?” or “what does X do?”.",
  },
  {
    id: "agent", name: "Agent",
    detail: "Can search again or open files before it answers. 10 to 30 seconds. Good when the answer is spread across files.",
  },
];

const BACKENDS: Record<string, { name: string; detail: string }> = {
  gemini: {
    name: "Gemini",
    detail: "Google's free tier. Fast. Only public code is sent to it.",
  },
  "claude-cli": {
    name: "Claude",
    detail: "Uses your own Claude login and its Pro plan limits.",
  },
};

export function settingsLabel(s: Settings) {
  return `${s.mode === "agent" ? "Agent" : "Quick answer"} with ${BACKENDS[s.backend]?.name ?? s.backend}`;
}

// A button naming the current settings; it opens a dialog with each choice and a line on what it does.
export default function SettingsButton({ settings, onChange, backends }: {
  settings: Settings;
  onChange: (next: Settings) => void;
  backends: string[];
}) {
  const dialog = useRef<HTMLDialogElement>(null);

  return (
    <>
      <button type="button" onClick={() => dialog.current?.showModal()}
        className="rounded-md border border-rule px-2.5 py-1 text-sm text-graphite hover:border-graphite hover:text-ink">
        {settingsLabel(settings)} <span aria-hidden>▾</span>
      </button>

      <dialog ref={dialog}
        className="m-auto w-[min(40rem,calc(100vw-2rem))] rounded-lg border border-rule bg-sheet p-0 text-ink backdrop:bg-ink/40">
        <form method="dialog" className="max-h-[85vh] overflow-y-auto p-6">
          <h2 className="mb-4 text-xl font-semibold">How to answer</h2>

          <fieldset className="mb-6 space-y-2">
            <legend className="mb-2 font-semibold text-graphite">How to search the code</legend>
            {MODES.map((m) => (
              <Choice key={m.id} name="mode" checked={settings.mode === m.id} title={m.name} detail={m.detail}
                onSelect={() => onChange({ ...settings, mode: m.id })} />
            ))}
          </fieldset>

          <fieldset className="mb-6 space-y-2">
            <legend className="mb-2 font-semibold text-graphite">Which model answers</legend>
            {backends.filter((b) => BACKENDS[b]).map((b) => (
              <Choice key={b} name="backend" checked={settings.backend === b} title={BACKENDS[b].name} detail={BACKENDS[b].detail}
                onSelect={() => onChange({ ...settings, backend: b })} />
            ))}
          </fieldset>

          <div className="flex justify-end">
            <button className="rounded-md bg-ink px-4 py-1.5 text-paper">Done</button>
          </div>
        </form>
      </dialog>
    </>
  );
}

function Choice({ name, checked, title, detail, onSelect }: {
  name: string; checked: boolean; title: string; detail: string; onSelect: () => void;
}) {
  return (
    <label className={`flex cursor-pointer gap-3 rounded-md border p-3 ${checked ? "border-marker-edge bg-marker/40" : "border-rule hover:border-graphite"}`}>
      <input type="radio" name={name} checked={checked} onChange={onSelect} className="mt-1.5 self-start accent-ink" />
      <span>
        <span className="block font-semibold">{title}</span>
        <span className="mt-0.5 block text-[0.95rem] leading-relaxed text-ink/85">{detail}</span>
      </span>
    </label>
  );
}
