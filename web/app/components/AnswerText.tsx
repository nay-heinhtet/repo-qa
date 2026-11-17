"use client";

import { Fragment, ReactNode } from "react";

// Renders the model's answer: line breaks become paragraphs or list items, `code` becomes <code>,
// and each [n] becomes a highlighter tab that opens the cited lines.
export default function AnswerText({ text, onCite, active }: {
  text: string;
  onCite: (n: number) => void;
  active: number | null;
}) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const items: { kind: "p" | "li"; text: string }[] = lines.map((line) => {
    const match = line.match(/^(\d+)[.)]\s+(.*)$/);
    return match ? { kind: "li", text: match[2] } : { kind: "p", text: line };
  });

  const blocks: ReactNode[] = [];
  for (let i = 0; i < items.length; i++) {
    if (items[i].kind === "p") {
      blocks.push(<p key={i} className="mb-3">{inline(items[i].text, onCite, active)}</p>);
      continue;
    }
    const list: ReactNode[] = [];
    while (i < items.length && items[i].kind === "li") {
      list.push(<li key={i} className="mb-2 pl-1">{inline(items[i].text, onCite, active)}</li>);
      i++;
    }
    i--;
    blocks.push(<ol key={`ol${i}`} className="mb-3 list-decimal pl-6 marker:text-graphite">{list}</ol>);
  }
  return <div className="text-[1.0625rem] leading-[1.7]">{blocks}</div>;
}

export function inline(
  text: string,
  onCite: (n: number) => void = () => {},
  active: number | null = null,
  decorate: (plain: string) => ReactNode = (plain) => plain,
): ReactNode {
  // Split on `code` spans, **bold** words and [n] / [n, m] markers, keeping them.
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[\d+(?:\s*,\s*\d+)*\])/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i} className="font-semibold">{decorate(part.slice(2, -2))}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code key={i} className="rounded-sm bg-rule/50 px-1 font-mono text-[0.85em]">{part.slice(1, -1)}</code>;
    }
    const cite = part.match(/^\[(.+)\]$/);
    if (cite && /^[\d,\s]+$/.test(cite[1])) {
      return (
        <Fragment key={i}>
          {cite[1].split(",").map((n) => Number(n.trim())).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onCite(n)}
              aria-label={`Show source ${n}`}
              className={`mx-0.5 inline-block min-w-[1.6em] rounded-[3px] px-1 align-[0.1em] font-mono text-[0.72em] font-semibold leading-[1.5] text-ink
                ${active === n ? "bg-marker-edge" : "bg-marker hover:bg-marker-edge"}`}
            >
              {n}
            </button>
          ))}
        </Fragment>
      );
    }
    return <Fragment key={i}>{decorate(part)}</Fragment>;
  });
}
