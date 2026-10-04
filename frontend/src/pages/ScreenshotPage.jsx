import React, { useEffect, useState } from "react";
import AgentPanel from "../components/AgentPanel.jsx";
import { api, todayLocal } from "../api.js";

const FIELD_FOR = { amount: "amount", date: "date", time: "time", merchant: "merchant_or_payee", payment_method: "payment_method" };

export default function ScreenshotPage() {
  const [meta, setMeta] = useState({ categories: [], payment_methods: [] });
  const [extraction, setExtraction] = useState(null);
  const [values, setValues] = useState(null);
  const [run, setRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState([]);
  useEffect(() => { api.meta().then(setMeta).catch(() => {}); }, []);

  async function pick(e) {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true); setErrors([]); setRun(null);
    try {
      const r = await api.extract(file);
      setExtraction(r);
      const f = r.fields, v = (k) => (f[k].value == null ? "" : f[k].value);
      setValues({ amount: v("amount"), date: v("date") || todayLocal(), time: v("time"), merchant: v("merchant_or_payee"),
        payment_method: v("payment_method") || "UPI", category: "", note: "" });
    } catch (err) {
      setErrors(err.errors || ["Upload failed."]);
      setExtraction(null); setValues(null);
    }
    setBusy(false);
  }
  const low = (name) => { const f = extraction && extraction.fields[FIELD_FOR[name]]; return f && (f.value == null || f.confidence === "low"); };
  const set = (k) => (e) => setValues({ ...values, [k]: e.target.value });

  async function confirm(e) {
    e.preventDefault();
    setBusy(true); setErrors([]);
    try { setRun(await api.process({ ...values, source: "screenshot" })); setExtraction(null); setValues(null); }
    catch (err) { setErrors(err.errors || ["Could not save."]); }
    setBusy(false);
  }
  async function answer(a) { setRun(await api.answer(run.txn_id, a)); }

  return (
    <section>
      <h1>Scan a payment screenshot</h1>
      <p className="notice">Privacy: the image is sent to Gemini only to read the details, kept in memory, and discarded. It is never stored on disk or in the database. Nothing is saved until you confirm.</p>
      <div className="panel">
        <label>Payment screenshot (PNG or JPG)<input type="file" accept="image/*" onChange={pick} disabled={busy} /></label>
        {busy && <p className="muted">Working…</p>}
      </div>
      {errors.length > 0 && <ul className="error-list" role="alert">{errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
      {extraction && !extraction.ok && <p className="error-list" role="alert">{extraction.error} You can still fill the form below.</p>}
      {extraction && extraction.warnings.length > 0 && <ul className="error-list">{extraction.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
      {values && (
        <form className="panel form" onSubmit={confirm}>
          <h2>Check the details</h2>
          {extraction.needs_merchant_confirmation && <p className="notice" role="status">I couldn't confidently identify the merchant. Please confirm.</p>}
          <p className="muted small-text">Highlighted fields were not clearly visible or had low confidence.</p>
          <div className="form-grid">
            <label className={low("amount") ? "low" : ""}>Amount (₹)<input type="number" inputMode="decimal" min="0.01" step="0.01" value={values.amount} onChange={set("amount")} required /></label>
            <label className={low("merchant") ? "low" : ""}>Merchant<input type="text" value={values.merchant} onChange={set("merchant")} required /></label>
            <label className={low("date") ? "low" : ""}>Date<input type="date" value={values.date} onChange={set("date")} required /></label>
            <label className={low("time") ? "low" : ""}>Time (24-hour)<input type="time" value={values.time} onChange={set("time")} required /></label>
            <label className={low("payment_method") ? "low" : ""}>Payment method
              <select value={values.payment_method} onChange={set("payment_method")}>{meta.payment_methods.map((m) => <option key={m}>{m}</option>)}</select></label>
            <label>Category<select value={values.category} onChange={set("category")}><option value="">Auto (from merchant)</option>{meta.categories.map((c) => <option key={c}>{c}</option>)}</select></label>
          </div>
          <div className="actions"><button className="btn primary" disabled={busy}>Confirm and analyze</button></div>
        </form>
      )}
      {run && <AgentPanel run={run} onAnswer={answer} />}
    </section>
  );
}
