import React, { useCallback, useEffect, useState } from "react";
import TransactionForm from "../components/TransactionForm.jsx";
import { api, rupees } from "../api.js";

export default function Transactions() {
  const [rows, setRows] = useState([]);
  const [months, setMonths] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState({ month: "", category: "", search: "" });
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.list(filters).then(setRows).catch((e) => setError(e.errors[0]));
    api.months().then(setMonths).catch(() => {});
  }, [filters]);
  useEffect(load, [load]);
  useEffect(() => { api.meta().then((m) => setCategories(m.categories)).catch(() => {}); }, []);

  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });
  async function remove(r) {
    if (!window.confirm(`Delete ${rupees(r.amount)} at ${r.merchant}?`)) return;
    await api.remove(r.id);
    load();
  }
  async function save(values) {
    await api.update(editing.id, values);
    setEditing(null);
    load();
  }

  return (
    <section>
      <h1>Transactions</h1>
      <div className="filters">
        <label>Month
          <select value={filters.month} onChange={set("month")}>
            <option value="">All months</option>
            {months.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        <label>Category
          <select value={filters.category} onChange={set("category")}>
            <option value="">All categories</option>
            {categories.map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Search
          <input type="search" value={filters.search} onChange={set("search")} placeholder="Merchant or note" />
        </label>
      </div>
      {error && <p className="error-list" role="alert">{error}</p>}
      <p className="muted">{rows.length} transactions</p>

      {editing && (
        <div className="panel">
          <h2>Edit transaction</h2>
          <TransactionForm initial={editing} submitLabel="Save changes" onSubmit={save} onCancel={() => setEditing(null)} />
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead><tr><th>Date</th><th>Time</th><th>Merchant</th><th className="num">Amount</th><th>Category</th><th>Method</th><th>Status</th><th>Source</th><th>Note</th><th></th></tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan="10" className="empty">No transactions match. Change the filters or add one.</td></tr>}
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.date}</td><td>{r.time}</td><td>{r.merchant}</td>
                <td className="num">{rupees(r.amount)}</td><td>{r.category}</td><td>{r.payment_method}</td>
                <td>{r.status === "pending_confirmation" ? <span className="badge medium">pending</span> : "confirmed"}</td><td>{r.source}</td><td className="wrap">{r.note}</td>
                <td className="row-actions">
                  {r.note && r.note.includes("[agent:") && <a className="btn small linkbtn" href={"#investigation/" + r.id}>Review</a>}
                  <button className="btn small" onClick={() => setEditing(r)}>Edit</button>
                  <button className="btn small danger" onClick={() => remove(r)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
