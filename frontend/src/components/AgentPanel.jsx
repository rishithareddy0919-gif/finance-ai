import React, { useState } from "react";
import { OUTCOME, TOOL } from "../labels.js";
import { percent } from "../api.js";

const show = (v) => (typeof v === "object" && v !== null ? JSON.stringify(v) : String(v));

// "Agent Investigation": the step timeline, risk level, explanation and (when needed) the question.
export default function AgentPanel({ run, onAnswer, alwaysAnswer = false, link = true }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function answer(a) {
    setBusy(true); setError("");
    try { await onAnswer(a); } catch (e) { setError(e.errors ? e.errors[0] : "Could not send your answer."); }
    setBusy(false);
  }
  const ask = run.question || (alwaysAnswer && onAnswer);
  return (
    <div className="panel agent">
      <div className="agent-head">
        <h2>Agent Investigation</h2>
        <span className={"badge " + run.risk_level.toLowerCase()}>{run.risk_level} risk</span>
      </div>
      <p className="agent-outcome"><strong>{OUTCOME[run.outcome]}.</strong>{" "}
        {run.probability == null ? "Quick check passed, so no deeper analysis was needed." : `Estimated chance this is unusual: ${percent(run.probability)}.`}
        {run.user_feedback && ` You answered: ${run.user_feedback === "me" ? "this was me" : "this wasn't me"}.`}</p>

      <ol className="timeline">
        {run.steps.map((s) => (
          <li key={s.step}>
            <span className="tl-tool">{s.step}. {TOOL[s.tool] || s.tool}</span>
            <span className="tl-why">{s.why}</span>
            <code className="tl-result">{Object.entries(s.result).map(([k, v]) => `${k}: ${show(v)}`).join(" · ")}</code>
          </li>
        ))}
      </ol>

      {ask && (
        <div className="question" role="group" aria-label="Question from the agent">
          <p><strong>{run.question || "Change your answer?"}</strong></p>
          <div className="actions">
            <button className="btn primary" disabled={busy} onClick={() => answer("me")}>This was me</button>
            <button className="btn danger" disabled={busy} onClick={() => answer("not_me")}>This wasn't me</button>
          </div>
          {error && <p className="error-list" role="alert">{error}</p>}
        </div>
      )}
      {run.explanation && (<><h3>Why</h3><p>{run.explanation}</p></>)}
      {run.recommendations && run.recommendations.length > 0 && (<><h3>Suggested next steps</h3><ul>{run.recommendations.map((r) => <li key={r}>{r}</li>)}</ul></>)}
      {link && run.outcome !== "logged_routine" && run.outcome !== "logged_normal" && <p><a href={"#investigation/" + run.txn_id}>Open the full investigation</a></p>}
      <p className="muted small-text">The system advises; you decide.</p>
    </div>
  );
}
