import React, { useEffect, useState } from "react";
import { LineChart } from "../components/charts.jsx";
import { api, rupees } from "../api.js";

export const STATUS_CLASS = { "on track": "low", "above usual": "medium", "well above usual": "high" };

export default function Prediction() {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.prediction().then(setD).catch((e) => setError(e.errors[0])); }, []);
  if (error) return <p className="error-list" role="alert">{error}</p>;
  if (!d) return <p className="muted">Loading…</p>;
  const o = d.overall;
  const cats = Object.values(d.categories);
  return (
    <section>
      <h1>Month-end prediction</h1>
      {o.low_confidence && <p className="notice" role="status">{o.message}</p>}
      <div className="cards">
        <div className="card"><span className="card-label">Spent so far ({o.days_elapsed} of {o.days_in_month} days)</span><span className="card-value">{rupees(o.spent_so_far)}</span></div>
        <div className="card"><span className="card-label">Predicted month-end (run-rate)</span><span className="card-value">{rupees(o.run_rate_prediction)}</span></div>
        <div className="card"><span className="card-label">Trend line estimate (regression)</span><span className="card-value">{o.regression_prediction == null ? "n/a" : rupees(o.regression_prediction)}</span></div>
        <div className="card"><span className="card-label">Usual month</span><span className="card-value">{rupees(o.historical_average)}</span>
          <span className="muted small-text">Normal range {rupees(o.normal_low)} to {rupees(o.normal_high)}</span></div>
      </div>
      <p>Status: <span className={"badge " + STATUS_CLASS[o.status]}>{o.status}</span>{" "}
        {o.pct_diff_vs_average != null && <span className="muted">{o.pct_diff_vs_average > 0 ? "+" : ""}{o.pct_diff_vs_average}% compared with your usual month</span>}</p>
      <h2>Cumulative spending this month</h2>
      <div className="panel">
        <LineChart xLabel="Day of month" series={[
          { name: "Spent so far", color: "var(--brand)", points: d.cumulative.map((p) => ({ x: p.day, y: p.spent })) },
          { name: "Projected (run-rate)", color: "var(--accent)", dashed: true, points: d.projected.map((p) => ({ x: p.day, y: p.spent })) }]} />
      </div>
      <h2>By category</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Category</th><th className="num">So far</th><th className="num">Predicted</th><th className="num">Usual month</th><th className="num">Difference</th><th>Status</th></tr></thead>
          <tbody>{cats.map((c) => (
            <tr key={c.label}><td>{c.label}</td><td className="num">{rupees(c.spent_so_far)}</td><td className="num">{rupees(c.run_rate_prediction)}</td>
              <td className="num">{rupees(c.historical_average)}</td><td className="num">{c.pct_diff_vs_average == null ? "n/a" : (c.pct_diff_vs_average > 0 ? "+" : "") + c.pct_diff_vs_average + "%"}</td>
              <td><span className={"badge " + STATUS_CLASS[c.status]}>{c.status}</span></td></tr>))}</tbody>
        </table>
      </div>
    </section>
  );
}
