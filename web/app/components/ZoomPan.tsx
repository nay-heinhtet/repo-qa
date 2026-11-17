"use client";

import { ReactNode, useEffect, useRef, useState } from "react";

type View = { x: number; y: number; k: number };  // shift in pixels, then scale
const PAD = 24;
const MAX_ZOOM = 2.5;

// A window onto a diagram that you can drag around and zoom (Ctrl or ⌘ + scroll, a trackpad pinch,
// or the buttons). It opens fitted to its width, and its height is the fitted diagram's height until
// the bottom edge is dragged.
// A drag never counts as a click, so dragging from a file box does not open the file.
export default function ZoomPan({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  const port = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(null);  // the fitted diagram's height
  const [chosenHeight, setChosenHeight] = useState<number | null>(null);  // set by dragging the bottom edge
  const resize = useRef<{ y: number; height: number } | null>(null);
  const [view, setView] = useState<View>({ x: PAD, y: PAD, k: 1 });
  const fitted = useRef<View>({ x: PAD, y: PAD, k: 1 });
  const drag = useRef<{ id: number; x: number; y: number; moved: boolean } | null>(null);
  const swallowClick = useRef(false);

  // Fit the diagram to the window's width; again when either changes size.
  useEffect(() => {
    const p = port.current, c = content.current;
    if (!p || !c) return;
    const fit = () => {
      const k = Math.min(1, (p.clientWidth - 2 * PAD) / c.offsetWidth);
      fitted.current = { x: (p.clientWidth - c.offsetWidth * k) / 2, y: PAD, k };
      setHeight(Math.ceil(c.offsetHeight * k + 2 * PAD));
      setView(fitted.current);
    };
    const observer = new ResizeObserver(fit);
    observer.observe(p);
    observer.observe(c);
    return () => observer.disconnect();
  }, []);

  // Zoom keeping the point under (px, py) still.
  const zoomAt = (factor: number, px: number, py: number) =>
    setView((v) => {
      const k = Math.min(MAX_ZOOM, Math.max(fitted.current.k * 0.5, v.k * factor));
      const r = k / v.k;
      return { k, x: px - (px - v.x) * r, y: py - (py - v.y) * r };
    });

  // A plain scroll still scrolls the page; with Ctrl or ⌘ (or a pinch, which sends ctrlKey) it zooms.
  // React's onWheel cannot cancel the page's own zoom, so this listener is added by hand.
  useEffect(() => {
    const p = port.current;
    if (!p) return;
    const wheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const r = p.getBoundingClientRect();
      zoomAt(Math.exp(-e.deltaY * 0.01), e.clientX - r.left, e.clientY - r.top);
    };
    p.addEventListener("wheel", wheel, { passive: false });
    return () => p.removeEventListener("wheel", wheel);
  }, []);

  const zoomCentre = (factor: number) => {
    const p = port.current;
    if (p) zoomAt(factor, p.clientWidth / 2, p.clientHeight / 2);
  };

  return (
    <div>
      <div ref={port}
        className="relative cursor-grab touch-pan-y overflow-hidden select-none active:cursor-grabbing lg:touch-none"
        style={{ height: chosenHeight ?? height ?? "24rem" }}
        // capture phase: runs even when a box inside stops the event to drag itself
        onPointerDownCapture={() => { swallowClick.current = false; }}
        onPointerDown={(e) => {
          if (e.button === 0) drag.current = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false };
        }}
        onPointerMove={(e) => {
          const d = drag.current;
          if (!d || d.id !== e.pointerId) return;
          const dx = e.clientX - d.x, dy = e.clientY - d.y;
          if (!d.moved && Math.hypot(dx, dy) < 4) return;  // a small wobble is still a click
          if (!d.moved) {
            d.moved = true;
            port.current?.setPointerCapture(e.pointerId);
          }
          d.x = e.clientX;
          d.y = e.clientY;
          setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
        }}
        onPointerUp={() => {
          if (drag.current?.moved) swallowClick.current = true;
          drag.current = null;
        }}
        onPointerCancel={() => { drag.current = null; }}
        onClickCapture={(e) => {
          if (swallowClick.current) {
            e.stopPropagation();
            swallowClick.current = false;
          }
        }}>
        <div ref={content} className="absolute top-0 left-0 w-max origin-top-left"
          style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})` }}>
          {children}
        </div>
      </div>
      {/* the bottom edge: drag to make the window taller or shorter, double-click to fit again */}
      <div role="separator" aria-orientation="horizontal" aria-label="Resize the chart window" title="Drag to resize, double-click to fit"
        className="group flex h-4 cursor-row-resize touch-none items-center justify-center border-y border-rule bg-paper hover:bg-marker active:bg-marker"
        onPointerDown={(e) => {
          resize.current = { y: e.clientY, height: port.current?.clientHeight ?? 0 };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          const r = resize.current;
          if (r) setChosenHeight(Math.min(1600, Math.max(160, r.height + e.clientY - r.y)));
        }}
        onPointerUp={() => { resize.current = null; }}
        onDoubleClick={() => setChosenHeight(null)}>
        <span aria-hidden className="flex flex-col gap-[3px]">
          <span className="block h-[2px] w-10 rounded-full bg-graphite/60 group-hover:bg-ink" />
          <span className="block h-[2px] w-10 rounded-full bg-graphite/60 group-hover:bg-ink" />
        </span>
      </div>
      <div className="flex items-center justify-between gap-3 px-3 py-1.5">
        <div className="text-sm">{actions}</div>
        <div className="flex overflow-hidden rounded-md border border-rule text-sm">
          <button type="button" onClick={() => zoomCentre(1 / 1.25)} aria-label="Zoom out" className="px-2.5 py-0.5 hover:bg-paper">−</button>
          <button type="button" onClick={() => zoomCentre(1.25)} aria-label="Zoom in" className="border-x border-rule px-2.5 py-0.5 hover:bg-paper">+</button>
          <button type="button" onClick={() => setView(fitted.current)} className="px-2.5 py-0.5 hover:bg-paper">Fit</button>
        </div>
      </div>
    </div>
  );
}
