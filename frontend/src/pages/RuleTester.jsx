import React, { useEffect, useState } from "react";
import TransactionForm, { blankForm } from "../components/TransactionForm.jsx";
import { api, rupees } from "../api.js";

export default function RuleTester() {
  const [result, setResult] = useState(null);
  const [rules, setRules] = useState([]);
  useEffect(() => { api.rules().then(setRules).catch(() => {}); }, []);
  async function test(values) { setResult(await api.analyzeRules(values)); }
  const fired = new Set(result ? result.rules_fired.map((r) => r.id) : []);
  const f = result && result.facts;
  const rows = f ? [["Category used", result.category_used], ["Amount ratio (amount / category average)", f.amount_ratio], ["Z-score", f.z_score],
    ["Normal range", `${rupees(f.normal_low)} to ${rupees(f.normal_high)}`], ["New merchant", String(f.is_new_merchant)], ["Unusual hour", String(f.is_unusual_hour)],
    ["Category spend ratio (this month / usual month)", f.category_spend_ratio], ["Same merchant payments today", f.same_merchant_count_today],
    ["Statistics from", f.stats_source === "category" ? "this category" : "all spending (too little category data)"]] : [];
  return (
    <section>
      <h1>Rule Tester</h1>
      <p className="muted">Try a transaction against the rules. Nothing is saved.</p>
      <div className="panel"><TransactionForm initial={blankForm()} submitLabel="Test rules" onSubmit={test} /></div>
      {result && (
        <>
          <div className="cards three">
            <div className="card"><span className="card-label">Rule-based level</span><span className={"card-value level-" + result.level.toLowerCase()}>{result.level}</span></div>
            <div className="card"><span className="card-label">Risk points</span><span className="card-value">{result.score}</span></div>
            <div className="card"><span className="card-label">Rules fired</span><span className="card-value">{result.rules_fired.length}</span></div>
          </div>
          <h2>Facts computed</h2>
          <div className="table-wrap"><table><tbody>{rows.map(([k, v]) => <tr key={k}><td>{k}</td><td className="num">{String(v)}</td></tr>)}</tbody></table></div>
        </>
      )}
      <h2>Rules</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Id</th><th>Rule</th><th>Conditions</th><th>Result</th></tr></thead>
          <tbody>{rules.map((r) => (
            <tr key={r.id} className={fired.has(r.id) ? "fired" : ""}>
              <td>{r.id}</td><td className="wrap">{r.description}</td>
              <td className="wrap">{r.conditions.map((c) => `${c.fact} ${c.op} ${c.value}`).join(" AND ")}</td>
              <td>{result ? (fired.has(r.id) ? "Fired" : "No") : ""}</td></tr>))}</tbody>
        </table>
      </div>
    </section>
  );
}
