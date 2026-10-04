import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const pad = (n) => String(n).padStart(2, "0");
export function blankForm() {
  const now = new Date();
  return { date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    time: `${pad(now.getHours())}:${pad(now.getMinutes())}`, merchant: "", amount: "",
    category: "", payment_method: "UPI", note: "" };
}

// One form for both "add" and "edit". Mobile: single column, full-width inputs.
export default function TransactionForm({ initial, submitLabel, onSubmit, onCancel }) {
  const [values, setValues] = useState(initial || blankForm());
  const [meta, setMeta] = useState({ categories: [], payment_methods: [] });
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.meta().then(setMeta).catch(() => {}); }, []);
  const set = (k) => (e) => setValues({ ...values, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setErrors([]);
    try { await onSubmit(values); } catch (err) { setErrors(err.errors || ["Something went wrong."]); }
    setBusy(false);
  }

  return (
    <form className="form" onSubmit={submit}>
      <div className="form-grid">
        <label>Date<input type="date" value={values.date} onChange={set("date")} required /></label>
        <label>Time (24-hour)<input type="time" value={values.time} onChange={set("time")} required /></label>
        <label>Merchant<input type="text" value={values.merchant} onChange={set("merchant")} placeholder="e.g. Swiggy" required /></label>
        <label>Amount (₹)<input type="number" inputMode="decimal" min="0.01" step="0.01" value={values.amount} onChange={set("amount")} required /></label>
        <label>Category
          <select value={values.category} onChange={set("category")}>
            <option value="">Auto (from merchant)</option>
            {meta.categories.map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Payment method
          <select value={values.payment_method} onChange={set("payment_method")}>
            {meta.payment_methods.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        <label className="wide">Note (optional)<input type="text" value={values.note || ""} onChange={set("note")} /></label>
      </div>
      {errors.length > 0 && <ul className="error-list" role="alert">{errors.map((m, i) => <li key={i}>{m}</li>)}</ul>}
      <div className="actions">
        <button className="btn primary" disabled={busy}>{busy ? "Saving…" : submitLabel}</button>
        {onCancel && <button type="button" className="btn" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}
