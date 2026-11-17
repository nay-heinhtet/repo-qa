"use client";

import { useEffect, useRef, useState } from "react";
import { Flow } from "../lib/api";
import { inline } from "./AnswerText";

type Box = { x: number; y: number; w: number; h: number };
type Offset = { x: number; y: number };
type Path = { from: string; to: string; label: string; d: string; lx: number; ly: number; skips?: boolean };

const GAP = 160;  // px between columns in the full chart: room for an arrow's label

// How the key files connect. Every arrow is a real import: "A → B" means A uses B.
// - "full": columns by layer, left to right, for the landing page (inside a ZoomPan). Boxes can be
//   dragged to new places; a click still opens the file.
// - "compact": one column in reading order with arcs on the right, for the narrow rail beside the code.
// Hovering a file (or opening it) marks its arrows and, in the full chart, shows their labels in the gaps.
export default function FlowChart({ flow, variant, active, marked, onPick, onHover }: {
  flow: Flow;
  variant: "full" | "compact";
  active?: string;
  marked?: string | null;  // pointed at from outside, e.g. hovered in the reading list
  onPick: (file: string) => void;
  onHover?: (file: string | null) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const nodes = useRef(new Map<string, HTMLElement>());
  const [boxes, setBoxes] = useState(new Map<string, Box>());  // where each box sits before any drag
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [hover, setHoverState] = useState<string | null>(null);
  const [offsets, setOffsets] = useState<Record<string, Offset>>({});
  const offsetsNow = useRef(offsets);  // for the measuring code, which runs outside render
  const drag = useRef<{ file: string; x: number; y: number; moved: boolean } | null>(null);
  const justDragged = useRef(false);
  const focus = hover ?? marked ?? active ?? null;
  const number = new Map(flow.steps.map((s, i) => [s.file, i + 1]));

  useEffect(() => { offsetsNow.current = offsets; }, [offsets]);

  function setHover(file: string | null) {
    setHoverState(file);
    onHover?.(file);
  }

  // Measure where the boxes sit, in unscaled pixels and without their drag offsets; again on resize.
  useEffect(() => {
    const container = box.current;
    if (!container) return;
    const measure = () => {
      const origin = container.getBoundingClientRect();
      const k = scale(container);
      const next = new Map<string, Box>();
      for (const [file, el] of nodes.current) {
        const r = el.getBoundingClientRect(), o = offsetsNow.current[file] ?? { x: 0, y: 0 };
        next.set(file, { x: (r.left - origin.left) / k - o.x, y: (r.top - origin.top) / k - o.y, w: r.width / k, h: r.height / k });
      }
      setBoxes(next);
      setSize({ w: container.scrollWidth, h: container.scrollHeight });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    return () => observer.disconnect();
  }, [flow, variant]);

  const placed = (file: string) => {
    const b = boxes.get(file), o = offsets[file];
    return b && o ? { ...b, x: b.x + o.x, y: b.y + o.y } : b;
  };
  const paths = variant === "full" ? fullArrows(flow, placed) : compactArrows(flow, placed);

  const ref = (file: string) => (el: HTMLElement | null) => {
    if (el) nodes.current.set(file, el); else nodes.current.delete(file);
  };

  // Dragging a box (full chart only). It stops the ZoomPan from panning; a drag is never a click.
  const dragHandlers = (file: string) => variant !== "full" ? {} : {
    onPointerDown: (e: React.PointerEvent) => {
      if (e.button !== 0) return;
      e.stopPropagation();
      drag.current = { file, x: e.clientX, y: e.clientY, moved: false };
    },
    onPointerMove: (e: React.PointerEvent<HTMLElement>) => {
      const d = drag.current;
      if (!d || d.file !== file || !box.current) return;
      const dx = e.clientX - d.x, dy = e.clientY - d.y;
      if (!d.moved && Math.hypot(dx, dy) < 4) return;
      if (!d.moved) {
        d.moved = true;
        e.currentTarget.setPointerCapture(e.pointerId);
      }
      d.x = e.clientX;
      d.y = e.clientY;
      const k = scale(box.current);
      setOffsets((o) => ({ ...o, [file]: { x: (o[file]?.x ?? 0) + dx / k, y: (o[file]?.y ?? 0) + dy / k } }));
    },
    onPointerUp: () => {
      justDragged.current = !!drag.current?.moved;
      drag.current = null;
    },
    onPointerCancel: () => { drag.current = null; },
  };

  const node = (file: string, role: string, explanation: string) => {
    const name = file.split("/").pop();
    const folder = file.includes("/") ? file.slice(0, file.lastIndexOf("/") + 1) : "";
    const isActive = file === active || file === marked;
    const touched = focus !== null && flow.edges.some((e) => (e.from === focus && e.to === file) || (e.to === focus && e.from === file));
    const o = offsets[file];
    return (
      <button key={file} ref={ref(file)} type="button" aria-label={`${file}: ${explanation}`} {...dragHandlers(file)}
        onClick={() => {
          if (justDragged.current) { justDragged.current = false; return; }
          onPick(file);
        }}
        onMouseEnter={() => setHover(file)} onMouseLeave={() => setHover(null)}
        onFocus={() => setHover(file)} onBlur={() => setHover(null)}
        style={o ? { transform: `translate(${o.x}px, ${o.y}px)` } : undefined}
        className={`relative z-10 rounded-md border text-left
          ${isActive ? "border-marker-edge bg-marker" : touched ? "border-marker-edge bg-sheet" : "border-rule bg-sheet hover:border-graphite"}
          ${variant === "full" ? "w-[12.5rem] cursor-move px-3 py-2" : "w-full px-2 py-1.5"}`}>
        <span className="flex items-baseline gap-2">
          <span className="font-mono text-xs text-graphite">{number.get(file)}</span>
          <span className="min-w-0 truncate font-mono text-[0.8rem] font-semibold">{name}</span>
        </span>
        {variant === "full" && folder && <span className="block truncate pl-5 font-mono text-[0.7rem] text-graphite">{folder}</span>}
        <span className={`block pl-5 leading-snug text-ink/85 ${variant === "full" ? "mt-1 text-[0.85rem]" : "truncate text-[0.75rem]"}`}>
          {inline(role)}
        </span>
      </button>
    );
  };

  const layers: Flow["steps"][] = [];
  for (const s of flow.steps) (layers[s.layer] ??= []).push(s);
  const lit = (p: Path) => focus !== null && (p.from === focus || p.to === focus);

  return (
    <div ref={box} className={`relative ${variant === "compact" ? "pr-12" : ""}`}>
      <svg className="pointer-events-none absolute inset-0 overflow-visible" width={size.w} height={size.h} aria-hidden>
        <defs>
          <marker id={`arrow-${variant}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
          </marker>
        </defs>
        {paths.map((p) => (
          <path key={`${p.from}>${p.to}`} d={p.d} fill="none" strokeWidth={lit(p) ? 2 : 1.25} markerEnd={`url(#arrow-${variant})`}
            strokeDasharray={p.skips ? "5 4" : undefined}
            className={lit(p) ? "stroke-marker-edge" : "stroke-graphite/45"} />
        ))}
      </svg>

      {variant === "full" ? (
        <div className="flex items-center" style={{ columnGap: GAP }}>
          {layers.filter(Boolean).map((column, i) => (
            <div key={i} className="flex flex-col gap-4">
              {column.map((s) => node(s.file, s.role, s.explanation))}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {flow.steps.map((s) => node(s.file, s.role, s.explanation))}
        </div>
      )}

      {/* labels of the marked arrows, in the gap before the box they point to, above everything */}
      {variant === "full" && paths.filter(lit).map((p) => (
        <span key={`${p.from}>${p.to}`}
          className="pointer-events-none absolute top-0 left-0 z-20 max-w-[9rem] rounded border border-marker-edge bg-paper px-1.5 text-center text-[0.72rem] leading-tight text-ink"
          style={{ transform: `translate(${p.lx}px, ${p.ly}px) translate(-50%, -50%)` }}>
          {p.label}
        </span>
      ))}
    </div>
  );
}

// The ZoomPan's current zoom: screen size over layout size.
function scale(el: HTMLElement) {
  return el.getBoundingClientRect().width / el.offsetWidth || 1;
}

// Spreads the arrows leaving (or entering) each box down its side, so their ends and labels do not overlap.
function ports(flow: Flow, at: (f: string) => Box | undefined, side: "from" | "to") {
  const other = side === "from" ? "to" : "from";
  const result = new Map<string, number>();
  for (const s of flow.steps) {
    const mine = flow.edges.filter((e) => e[side] === s.file)
      .sort((a, b) => (at(a[other])?.y ?? 0) - (at(b[other])?.y ?? 0));
    const b = at(s.file);
    mine.forEach((e, i) => b && result.set(`${e.from}>${e.to}`, b.y + (b.h * (i + 1)) / (mine.length + 1)));
  }
  return result;
}

function fullArrows(flow: Flow, at: (f: string) => Box | undefined): Path[] {
  const layer = new Map(flow.steps.map((s) => [s.file, s.layer]));
  const outY = ports(flow, at, "from"), inY = ports(flow, at, "to");
  const paths: Path[] = [];
  for (const e of flow.edges) {
    const a = at(e.from), b = at(e.to);
    if (!a || !b) continue;
    const key = `${e.from}>${e.to}`;
    const y1 = outY.get(key) ?? a.y + a.h / 2, y2 = inY.get(key) ?? b.y + b.h / 2;
    // an arrow that skips a column passes behind the boxes between: dashed, so it does not seem to start there
    const skips = Math.abs((layer.get(e.to) ?? 0) - (layer.get(e.from) ?? 0)) > 1;
    if (b.x > a.x + a.w || b.x + b.w < a.x) {
      const right = b.x > a.x + a.w;
      const x1 = right ? a.x + a.w : a.x, x2 = right ? b.x - 3 : b.x + b.w + 3;
      const c = (x2 - x1) / 2;
      const curve = [x1, y1, x1 + c, y1, x2 - c, y2, x2, y2] as const;
      // the label sits in the gap just before the box it points to
      const lx = x2 - Math.sign(x2 - x1) * Math.min(GAP / 2, Math.abs(x2 - x1) / 2);
      paths.push({ ...e, d: `M ${x1} ${y1} C ${x1 + c} ${y1}, ${x2 - c} ${y2}, ${x2} ${y2}`, lx, ly: yAtX(curve, lx), skips });
    } else {
      // overlapping columns (an import cycle, or a box dragged on top): a loop to the left
      const x = Math.min(a.x, b.x);
      paths.push({ ...e, d: `M ${x} ${y1} C ${x - 40} ${y1}, ${x - 40} ${y2}, ${x - 3} ${y2}`, lx: x - 40, ly: (y1 + y2) / 2 });
    }
  }
  return paths;
}

function compactArrows(flow: Flow, at: (f: string) => Box | undefined): Path[] {
  const order = new Map(flow.steps.map((s, i) => [s.file, i]));
  const paths: Path[] = [];
  for (const e of flow.edges) {
    const a = at(e.from), b = at(e.to);
    if (!a || !b) continue;
    const x = Math.max(a.x + a.w, b.x + b.w);
    const y1 = a.y + a.h / 2, y2 = b.y + b.h / 2;
    const bulge = 14 + 7 * Math.abs((order.get(e.to) ?? 0) - (order.get(e.from) ?? 0));
    paths.push({ ...e, d: `M ${x} ${y1} C ${x + bulge} ${y1}, ${x + bulge} ${y2}, ${x + 4} ${y2}`, lx: x + bulge, ly: (y1 + y2) / 2 });
  }
  return paths;
}

// The y of a cubic Bézier curve (x always moving one way) where it reaches x, by bisection on t.
function yAtX([x0, y0, x1, y1, x2, y2, x3, y3]: readonly number[], x: number) {
  const point = (t: number, p0: number, p1: number, p2: number, p3: number) =>
    (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3;
  let lo = 0, hi = 1;
  const rising = x3 > x0;
  for (let i = 0; i < 30; i++) {
    const t = (lo + hi) / 2;
    if ((point(t, x0, x1, x2, x3) < x) === rising) lo = t; else hi = t;
  }
  return point((lo + hi) / 2, y0, y1, y2, y3);
}

// The same steps as a numbered reading list, with each file's fuller explanation. It scrolls inside
// its own area; the file marked in the chart is marked here too, and a notice points to it when it
// is scrolled out of view. Hovering an entry marks its box in the chart.
export function ReadingOrder({ flow, onPick, marked, onHover, className }: {
  flow: Flow;
  onPick: (file: string) => void;
  marked: string | null;
  onHover: (file: string) => void;
  className?: string;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const items = useRef(new Map<string, HTMLElement>());
  const [hidden, setHidden] = useState<"above" | "below" | null>(null);

  const check = () => {
    const s = scroller.current, el = marked ? items.current.get(marked) : undefined;
    if (!s || !el) return setHidden(null);
    const view = s.getBoundingClientRect(), r = el.getBoundingClientRect();
    setHidden(r.top > view.bottom - 48 ? "below" : r.bottom < view.top + 48 ? "above" : null);
  };
  useEffect(() => { queueMicrotask(check); });

  const step = marked ? flow.steps.findIndex((s) => s.file === marked) : -1;
  const notice = hidden && step >= 0 && (
    <button type="button" onClick={() => items.current.get(marked!)?.scrollIntoView({ block: "center", behavior: "smooth" })}
      className={`sticky z-10 mx-auto my-2 flex rounded-full bg-ink px-3 py-1 text-sm text-paper shadow-md ${hidden === "below" ? "bottom-3" : "top-3"}`}>
      {hidden === "below" ? "↓ Scroll down" : "↑ Scroll up"} to step {step + 1}, {marked!.split("/").pop()}
    </button>
  );

  return (
    <div ref={scroller} onScroll={check} className={className}>
      <h3 className="mb-3 font-semibold">Read them in this order</h3>
      {hidden === "above" && notice}
      <ol className="space-y-1">
        {flow.steps.map((s, i) => (
          <li key={s.file} ref={(el) => { if (el) items.current.set(s.file, el); else items.current.delete(s.file); }}
            onMouseEnter={() => onHover(s.file)}
            className={`-mx-2 grid grid-cols-[1.5rem_minmax(0,1fr)] gap-x-2 rounded-md px-2 py-1.5 transition-colors ${s.file === marked ? "bg-marker" : ""}`}>
            <span className="pt-0.5 font-mono text-sm text-graphite">{i + 1}</span>
            <div>
              <button type="button" onClick={() => onPick(s.file)} className="font-mono text-[0.85rem] font-semibold underline-offset-2 hover:underline">
                {s.file}
              </button>
              <p className="text-[0.98rem] leading-relaxed text-ink/85">{inline(withoutOwnName(s.file, s.explanation))}</p>
            </div>
          </li>
        ))}
      </ol>
      {hidden === "below" && notice}
    </div>
  );
}

// The model often starts with the file's own path, which the line above already shows.
function withoutOwnName(file: string, text: string) {
  const own = "`" + file + "` ";
  if (!text.startsWith(own)) return text;
  const rest = text.slice(own.length);
  return rest.charAt(0).toUpperCase() + rest.slice(1);
}
