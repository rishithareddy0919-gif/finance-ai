import React, { useEffect, useState } from "react";
import ContribBars from "../components/ContribBars.jsx";
import { useWidth } from "../components/charts.jsx";
import { api } from "../api.js";
import { VARIABLE } from "../labels.js";

const SHORT = { AmountDeviation: ["Amount", "deviation"], NewMerchant: ["New", "merchant"], CategoryOverspend: ["Category", "overspend"], UnusualTime: ["Unusual", "time"], UnusualTransaction: ["Unusual", "transaction"] };

// Network diagram: four parents point at UnusualTransaction. Laid out from the container width.
function Diagram({ nodes, evidence }) {
  const [ref, w] = useWidth();
  const parents = nodes.slice(0, 4), nw = Math.min(110, (w - 30) / 4), h = 190;
  const px = (i) => 10 + i * ((w - 20 - nw) / 3);
  const cx = w / 2;
  const box = (x, y, key, strong) => { const bw = strong ? nw + 30 : nw; return (
    <g key={key}>
      <rect x={x} y={y} width={bw} height="46" rx="8" fill={strong ? "var(--brand)" : evidence[key] ? "var(--brand-soft)" : "#fff"} stroke="var(--brand)" strokeWidth="2" />
      {SHORT[key].map((t, i) => <text key={i} x={x + bw / 2} y={y + 19 + i * 14} textAnchor="middle" fontSize="11" fontWeight="600" fill={strong ? "#fff" : "var(--ink)"}>{t}</text>)}
    </g>); };
  return (
    <div ref={ref} className="chart">
      <svg width={w} height={h} role="img" aria-label="Bayesian network: four parent nodes point to Unusual transaction">
        <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="var(--brand)" /></marker></defs>
        {parents.map((k, i) => <line key={k} x1={px(i) + nw / 2} y1="46" x2={cx} y2={h - 52} stroke="var(--brand)" strokeWidth="1.5" markerEnd="url(#arrow)" />)}
        {parents.map((k, i) => box(px(i), 0, k, false))}
        {box(cx - nw / 2 - 15, h - 48, "UnusualTransaction", true)}
      </svg>
    </div>);
}

export default function BayesLab() {
  const [structure, setStructure] = useState(null);
  const [evidence, setEvidence] = useState({});
  const [out, setOut] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.bayesStructure().then(setStructure).catch((e) => setError(e.errors[0])); }, []);
  useEffect(() => { api.analyzeBayes({ evidence }).then(setOut).catch((e) => setError(e.errors[0])); }, [evidence]);
  if (error) return <p className="error-list" role="alert">{error}</p>;
  if (!structure) return <p className="muted">Loading…</p>;
  const vars = structure.nodes.slice(0, 4);
  const set = (v) => (e) => setEvidence({ ...evidence, [v]: e.target.value || null });
  return (
    <section>
      <h1>Bayesian Lab</h1>
      <p className="muted">Choose what you know. Anything left as unknown is averaged using its prior probability.</p>
      <div className="panel"><Diagram nodes={structure.nodes} evidence={evidence} /></div>
      <div className="two-col">
        <div className="panel">
          <h2>Evidence</h2>
          <div className="form-grid">
            {vars.map((v) => (
              <label key={v}>{VARIABLE[v]}
                <select value={evidence[v] || ""} onChange={set(v)}>
                  <option value="">Unknown (use prior)</option>
                  {structure.states[v].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                </select></label>))}
          </div>
          <div className="actions"><button className="btn" onClick={() => setEvidence({})}>Clear evidence</button></div>
        </div>
        <div className="panel">
          <h2>Probability unusual</h2>
          <p className="big" data-testid="probability">{out ? out.probability.toFixed(4) : "…"}</p>
          <p className="muted">{out ? Math.round(out.probability * 1000) / 10 + "%" : ""} P(UnusualTransaction = yes | evidence)</p>
          <h2>Contribution of each item</h2>
          <ContribBars items={out ? out.contributions : []} />
        </div>
      </div>
      <h2>Priors</h2>
      <div className="table-wrap"><table><thead><tr><th>Variable</th><th>Prior probabilities</th></tr></thead>
        <tbody>{vars.map((v) => <tr key={v}><td>{VARIABLE[v]}</td><td>{Object.entries(structure.priors[v]).map(([s, p]) => `${s.replace("_", " ")} ${p}`).join(" · ")}</td></tr>)}</tbody></table></div>
    </section>
  );
}
