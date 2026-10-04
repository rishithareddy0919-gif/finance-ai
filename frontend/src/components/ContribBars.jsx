import React from "react";
import { factorLabel } from "../labels.js";

// Bayesian contribution of each evidence item: how much P(unusual) changes when the item is removed.
export default function ContribBars({ items }) {
  if (!items || items.length === 0) return <p className="muted">No evidence selected yet.</p>;
  const max = Math.max(0.01, ...items.map((i) => Math.abs(i.contribution)));
  return (
    <div>
      {items.map((i) => {
        const pts = Math.round(i.contribution * 100);
        return (
          <div className="contrib" key={i.variable}>
            <span className="contrib-label">{factorLabel(i.variable, i.state)}</span>
            <span className="contrib-track"><span className={"contrib-fill " + (pts < 0 ? "down" : "up")} style={{ width: (Math.abs(i.contribution) / max) * 100 + "%" }} /></span>
            <span className="contrib-pts">{pts > 0 ? "+" : ""}{pts} pts</span>
          </div>
        );
      })}
    </div>
  );
}
