import React, { useState } from "react";
import AgentPanel from "../components/AgentPanel.jsx";
import { api, rupees, todayLocal } from "../api.js";

const STEPS = [
  { title: "1. Easy: a routine payment", note: "Known merchant, normal amount, usual hour. The agent stops after a quick check.", txn: { merchant: "Swiggy", amount: 280, category: "Food", time: "20:15" } },
  { title: "2. Uncertain: a big purchase at a known merchant", note: "Very high amount but a familiar merchant. The agent runs everything and asks you.", txn: { merchant: "Amazon", amount: 24000, category: "Shopping", time: "21:10" } },
  { title: "3. High risk: new merchant, huge amount, 3 AM", note: "Every warning sign at once. The agent flags it as potentially unusual and explains.", txn: { merchant: "QuickLoan247", amount: 32000, category: "Entertainment", time: "03:20" } },
];

export default function DemoScenario() {
  const [runs, setRuns] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function play() {
    setBusy(true); setError(""); setRuns([]);
    try {
      await api.reset();                      // always start from the same demo data so the three paths repeat
      for (const s of STEPS) { const r = await api.process({ ...s.txn, date: todayLocal(), payment_method: "UPI", source: "manual" }); setRuns((prev) => [...prev, r]); } }
    catch (e) { setError(e.errors ? e.errors[0] : "Something went wrong."); }
    setBusy(false);
  }
  async function reset() { if (!window.confirm("Replace all transactions with fresh demo data?")) return; await api.reset(); setRuns([]); }
  const answer = (i) => async (a) => { const r = await api.answer(runs[i].txn_id, a); setRuns(runs.map((x, j) => (j === i ? r : x))); };
  return (
    <section>
      <h1>Demo scenario</h1>
      <p>Three payments walk through the three paths of the agent. Running the scenario first resets the demo data, so it plays the same way every time.</p>
      <div className="actions"><button className="btn primary" onClick={play} disabled={busy}>{busy ? "Running…" : "Run demo scenario"}</button><button className="btn" onClick={reset} disabled={busy}>Reset demo data</button></div>
      {error && <p className="error-list" role="alert">{error}</p>}
      {STEPS.map((s, i) => (
        <div key={s.title}>
          <h2>{s.title}</h2>
          <p className="muted">{s.note} ({rupees(s.txn.amount)} at {s.txn.merchant}, {s.txn.time})</p>
          {runs[i] && <AgentPanel run={runs[i]} onAnswer={answer(i)} />}
        </div>))}
    </section>
  );
}
