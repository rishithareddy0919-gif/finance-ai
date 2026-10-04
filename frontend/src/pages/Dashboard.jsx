import React, { useCallback, useEffect, useState } from "react";
import { LineChart, Columns, PairBars } from "../components/charts.jsx";
import { STATUS_CLASS } from "./Prediction.jsx";
import { api, compact, percent, rupees } from "../api.js";

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api.overview().then(setD).catch((e) => setError(e.errors[0])); }, []);
  useEffect(load, [load]);
  async function reset() {
    if (!window.confirm("Replace all transactions with fresh demo data?")) return;
    setBusy(true);
    try { await api.reset(); load(); } catch (e) { setError(e.errors[0]); }
    setBusy(false);
  }
  if (error) return <p className="error-list" role="alert">{error}</p>;
  if (!d) return <p className="muted">Loading…</p>;
  const p = d.prediction;
  return (
    <section>
      <div className="page-head">
        <h1>Dashboard <span className="muted small-text">{d.month}</span></h1>
        <div className="actions tight"><a className="btn primary linkbtn" href="#demo">Run demo scenario</a><button className="btn" onClick={reset} disabled={busy}>{busy ? "Resetting…" : "Reset demo data"}</button></div>
      </div>
      <div className="cards">
        <div className="card"><span className="card-label">Spent this month</span><span className="card-value">{rupees(d.total_spend)}</span></div>
        <div className="card"><span className="card-label">Predicted month-end</span><span className="card-value">{rupees(p.run_rate_prediction)}</span>
          <span><span className={"badge " + STATUS_CLASS[p.status]}>{p.status}</span>{p.low_confidence && <span className="muted small-text"> low confidence</span>}</span></div>
        <div className="card"><span className="card-label">Potentially unusual</span><span className="card-value bad">{d.unusual_count}</span></div>
        <div className="card"><span className="card-label">Waiting for your answer</span><span className="card-value">{d.pending_count}</span></div>
      </div>
      <div className="two-col">
        <div className="panel"><h2>This month vs usual</h2>
          <p className="muted">Spent {rupees(p.spent_so_far)} · predicted {rupees(p.run_rate_prediction)} · usual {rupees(p.historical_average)}</p>
          {p.low_confidence && <p className="muted small-text">{p.message}</p>}
          <LineChart xLabel="Day of month" series={[
            { name: "Spent so far", color: "var(--brand)", points: d.cumulative.map((x) => ({ x: x.day, y: x.spent })) },
            { name: "Projected", color: "var(--accent)", dashed: true, points: d.projected.map((x) => ({ x: x.day, y: x.spent })) }]} /></div>
        <div className="panel"><h2>Spending trend</h2><Columns items={d.trend.map((t) => ({ label: t.month.slice(2), value: t.total }))} format={compact} /></div>
      </div>
      <div className="two-col">
        <div className="panel"><h2>Categories: current vs usual</h2>
          <PairBars rows={d.category_comparison.map((c) => ({ label: c.category, current: c.current, usual: c.usual }))} format={compact} /></div>
        <div className="panel"><h2>Recent alerts</h2>
          {d.recent_alerts.length === 0 && <p className="muted">No alerts yet. Add a transaction or run the demo scenario.</p>}
          <ul className="alerts">{d.recent_alerts.map((a) => (
            <li key={a.txn_id}><a href={"#investigation/" + a.txn_id}><strong>{rupees(a.amount)}</strong> at {a.merchant}</a>
              <span className="muted small-text">{a.date} · {a.category}</span>
              <span className={"badge " + a.risk_level.toLowerCase()}>{a.outcome === "awaiting_user" ? "needs your answer" : "potentially unusual"} · {percent(a.probability)}</span></li>))}</ul></div>
      </div>
    </section>
  );
}
