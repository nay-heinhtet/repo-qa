"use client";

import { inline } from "./AnswerText";

// Starter questions (GLOSSARY: Starter question) as a list you can click to ask.
export default function AskNext({ questions, onAsk, title = "Ask next" }: {
  questions: string[];
  onAsk: (question: string) => void;
  title?: string;
}) {
  return (
    <div>
      <h2 className="mb-3 font-semibold">{title}</h2>
      <ul className="space-y-2">
        {questions.map((q) => (
          <li key={q}>
            <button type="button" onClick={() => onAsk(q)}
              className="w-full border-l-2 border-rule py-1 pl-3 text-left leading-snug hover:border-marker-edge hover:bg-sheet">
              {inline(q)}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
