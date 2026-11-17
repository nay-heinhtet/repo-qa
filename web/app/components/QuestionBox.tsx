"use client";

import { useState } from "react";
import { Settings } from "../lib/hooks";
import SettingsButton from "./SettingsDialog";

// The question input with the Ask button and the settings pop-up.
// To reset its text from outside, give it a new `key`.
export default function QuestionBox({ initial = "", busy, settings, onSettings, backends, onAsk, autoFocus }: {
  initial?: string;
  busy: boolean;
  settings: Settings;
  onSettings: (next: Settings) => void;
  backends: string[];
  onAsk: (question: string) => void;
  autoFocus?: boolean;
}) {
  const [question, setQuestion] = useState(initial);

  function submit() {
    if (question.trim().length >= 3 && !busy) onAsk(question.trim());
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(); }}>
      <label htmlFor="question" className="sr-only">Your question about this code</label>
      <div className="flex items-end gap-2 rounded-lg border border-rule bg-sheet p-2 focus-within:border-graphite">
        <textarea
          id="question"
          value={question}
          autoFocus={autoFocus}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          rows={2}
          placeholder="Ask about this code, e.g. how does a document get from file to stored content?"
          className="min-h-[3.2rem] flex-1 resize-none bg-transparent px-2 py-1 text-[1.0625rem] leading-snug outline-none"
        />
        <button type="submit" disabled={busy || question.trim().length < 3}
          className="rounded-md bg-ink px-4 py-2 text-paper disabled:opacity-50">
          {busy ? "Reading…" : "Ask"}
        </button>
      </div>
      <div className="mt-2">
        <SettingsButton settings={settings} onChange={onSettings} backends={backends} />
      </div>
    </form>
  );
}
