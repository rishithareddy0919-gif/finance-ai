import React, { useEffect, useState } from "react";
import { api, rupees } from "../api.js";

export default function Profile() {
  const [p, setP] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api.profile().then(setP).catch((e) => setError(e.errors[0])); }, []);
  if (error) return <p className="error-list" role="alert">{error}</p>;
  if (!p) return <p className="muted">Loading…</p>;
  if (!p.overall) return <section><h1>Your financial profile</h1><p className="empty">No confirmed transactions yet.</p></section>;
  const cats = Object.values(p.categories).sort((a, b) => b.count - a.count);
  return (
    <section>
      <h1>Your financial profile</h1>
      <p className="muted">Learned from your confirmed transactions only. Monthly averages use completed months; the current month is {p.current_month}.</p>
      <div className="cards">
        <div className="card"><span className="card-label">Transactions learned from</span><span className="card-value">{p.overall.count}</span></div>
        <div className="card"><span className="card-label">Average transaction</span><span className="card-value">{rupees(p.overall.mean)}</span></div>
        <div className="card"><span className="card-label">Typical spread (std)</span><span className="card-value">{rupees(p.overall.std)}</span></div>
        <div className="card"><span className="card-label">Known merchants</span><span className="card-value">{p.known_merchants.length}</span></div>
      </div>
      <h2>By category</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Category</th><th className="num">Transactions</th><th className="num">Monthly average</th><th className="num">This month</th><th className="num">vs average</th><th>Normal range per transaction</th><th>Frequent merchants</th></tr></thead>
          <tbody>
            {cats.map((c) => c.low_confidence ? (
              <tr key={c.category}><td>{c.category}</td><td className="num">{c.count}</td><td colSpan="5" className="muted">Low confidence: {c.message}</td></tr>
            ) : (
              <tr key={c.category}><td>{c.category}</td><td className="num">{c.count}</td><td className="num">{rupees(c.monthly_average)}</td>
                <td className="num">{rupees(c.current_month_spend)}</td>
                <td className="num">{c.current_vs_average_ratio == null ? "n/a" : Math.round(c.current_vs_average_ratio * 100) + "%"}</td>
                <td>{rupees(c.normal_low)} to {rupees(c.normal_high)}</td>
                <td>{c.top_merchants.map((m) => m.merchant).join(", ")}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="two-col">
        <div><h2>Monthly totals</h2>
          <div className="table-wrap"><table><thead><tr><th>Month</th><th className="num">Total</th></tr></thead>
            <tbody>{p.months.map((m) => <tr key={m}><td>{m}{m === p.current_month ? " (so far)" : ""}</td><td className="num">{rupees(p.monthly_totals[m])}</td></tr>)}</tbody></table></div></div>
        <div><h2>Typical hours</h2>
          <div className="panel"><p>Hours that together hold 95% of your transactions:</p><p><strong>{p.typical_hours.map((h) => String(h).padStart(2, "0") + ":00").join(", ")}</strong></p></div></div>
      </div>
    </section>
  );
}
