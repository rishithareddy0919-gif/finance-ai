import React, { useCallback, useEffect, useState } from "react";
import AgentPanel from "../components/AgentPanel.jsx";
import ContribBars from "../components/ContribBars.jsx";
import { api, percent, rupees } from "../api.js";

export default function Investigation({ param }) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => { setError(""); api.run(param).then(setRun).catch((e) => setError(e.errors[0])); }, [param]);
  useEffect(load, [load]);
  if (!param) return <section><h1>Investigation</h1><p className="empty">Open a transaction from the dashboard alerts or the Transactions page.</p></section>;
  if (error) return <section><h1>Investigation</h1><p className="error-list" role="alert">{error}</p></section>;
  if (!run) return <p className="muted">Loading…</p>;
  const t = run.transaction;
  async function answer(a) { setRun(await api.answer(run.txn_id, a)); }
  return (
    <section>
      <h1>Investigation</h1>
      <div className="cards three">
        <div className="card"><span className="card-label">Transaction</span><span className="card-value">{rupees(t.amount)}</span><span>{t.merchant} · {t.category}</span><span className="muted small-text">{t.date} {t.time} · {t.payment_method} · {t.source}</span></div>
        <div className="card"><span className="card-label">Risk</span><span className={"badge " + run.risk_level.toLowerCase()}>{run.risk_level}</span><span className="card-value">{percent(run.probability)}</span><span className="muted small-text">Status: {t.status.replace("_", " ")}</span></div>
        <div className="card"><span className="card-label">Rule-based level</span><span className="card-value">{run.rules_level || "n/a"}</span><span className="muted small-text">{run.rules_fired.length} rule(s) fired</span></div>
      </div>
      <div className="two-col">
        <div className="panel"><h2>Bayesian contributions</h2>
          {run.contributions.length ? <ContribBars items={run.contributions} /> : <p className="muted">The quick check passed, so no Bayesian analysis was run.</p>}</div>
        <div className="panel"><h2>Rules fired</h2>
          {run.rules.length ? <ul>{run.rules.map((r) => <li key={r.id}><strong>{r.id}</strong> {r.description}</li>)}</ul> : <p className="muted">No risk rules fired.</p>}</div>
      </div>
      <AgentPanel run={run} onAnswer={answer} alwaysAnswer link={false} />
    </section>
  );
}
