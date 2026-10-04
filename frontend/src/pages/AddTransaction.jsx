import React, { useState } from "react";
import TransactionForm, { blankForm } from "../components/TransactionForm.jsx";
import AgentPanel from "../components/AgentPanel.jsx";
import { api } from "../api.js";

// The form sends the transaction to the agent, which decides what to do and saves it.
export default function AddTransaction() {
  const [run, setRun] = useState(null);
  const [formKey, setFormKey] = useState(0);
  async function submit(values) {
    setRun(await api.process({ ...values, source: "manual" }));
    setFormKey(formKey + 1);
  }
  async function answer(a) { setRun(await api.answer(run.txn_id, a)); }
  return (
    <section>
      <h1>Add transaction</h1>
      <div className="panel"><TransactionForm key={formKey} initial={blankForm()} submitLabel="Save and analyze" onSubmit={submit} /></div>
      {run && <AgentPanel run={run} onAnswer={answer} />}
    </section>
  );
}
