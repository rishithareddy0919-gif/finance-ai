import React, { useEffect, useRef, useState } from "react";
import { compact } from "../api.js";

// Measures its container so the SVG is redrawn at the right size (charts resize to their container).
function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(320);
  useEffect(() => {
    if (!ref.current) return undefined;
    const update = () => setWidth(Math.max(260, Math.floor(ref.current.getBoundingClientRect().width)));
    update();
    if (typeof ResizeObserver === "undefined") { window.addEventListener("resize", update); return () => window.removeEventListener("resize", update); }
    const ro = new ResizeObserver(update);
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}
export { useWidth };

// series: [{ name, color, dashed, points: [{x, y}] }]
export function LineChart({ series, xLabel }) {
  const [ref, w] = useWidth();
  const h = w < 480 ? 220 : 280, m = { l: 46, r: 12, t: 12, b: 34 };
  const pts = series.flatMap((s) => s.points);
  const xs = pts.map((p) => p.x), maxY = Math.max(1, ...pts.map((p) => p.y));
  const x0 = Math.min(...xs), x1 = Math.max(...xs, x0 + 1);
  const sx = (x) => m.l + ((x - x0) / (x1 - x0)) * (w - m.l - m.r);
  const sy = (y) => h - m.b - (y / maxY) * (h - m.t - m.b);
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * maxY);
  const xTicks = [x0, Math.round((x0 + x1) / 2), x1];
  return (
    <div ref={ref} className="chart">
      <svg width={w} height={h} role="img" aria-label="Line chart">
        {yTicks.map((t) => (<g key={t}><line x1={m.l} x2={w - m.r} y1={sy(t)} y2={sy(t)} stroke="var(--line)" /><text x={m.l - 6} y={sy(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">{compact(t)}</text></g>))}
        {xTicks.map((t) => <text key={t} x={sx(t)} y={h - 14} textAnchor="middle" fontSize="11" fill="var(--muted)">{t}</text>)}
        {xLabel && <text x={w / 2} y={h - 1} textAnchor="middle" fontSize="11" fill="var(--muted)">{xLabel}</text>}
        {series.map((s) => (
          <polyline key={s.name} fill="none" stroke={s.color} strokeWidth="2.5" strokeDasharray={s.dashed ? "6 5" : undefined}
            points={s.points.map((p) => `${sx(p.x)},${sy(p.y)}`).join(" ")} />
        ))}
      </svg>
      <div className="legend">{series.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}</div>
    </div>
  );
}

// Vertical bars, one per item: { label, value }.
export function Columns({ items, format }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <div className="columns">
      {items.map((i) => (
        <div className="column" key={i.label}>
          <span className="column-value">{format(i.value)}</span>
          <span className="column-bar" style={{ height: Math.max(2, (i.value / max) * 100) + "%" }} />
          <span className="column-label">{i.label}</span>
        </div>
      ))}
    </div>
  );
}

// Two horizontal bars per row (current vs usual).
export function PairBars({ rows, format }) {
  const max = Math.max(1, ...rows.flatMap((r) => [r.current, r.usual]));
  return (
    <div>
      {rows.map((r) => (
        <div className="pair" key={r.label}>
          <div className="pair-label">{r.label}</div>
          <div className="pair-bars">
            <span className="pair-bar now" style={{ width: Math.max(1, (r.current / max) * 100) + "%" }}><b>{format(r.current)}</b></span>
            <span className="pair-bar usual" style={{ width: Math.max(1, (r.usual / max) * 100) + "%" }}><b>{format(r.usual)}</b></span>
          </div>
        </div>
      ))}
      <div className="legend"><span><i style={{ background: "var(--brand)" }} />This month</span><span><i style={{ background: "var(--accent)" }} />Usual month</span></div>
    </div>
  );
}
