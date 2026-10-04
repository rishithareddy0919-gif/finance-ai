import React from "react";

export default function Privacy() {
  const items = [
    ["Your data stays local", "Transactions live in a SQLite file on the machine running the backend. Nothing is uploaded to a cloud database. All data in this demo is synthetic."],
    ["Screenshots are not stored", "A payment screenshot is read into memory, sent to Gemini to extract the details, and discarded. It is never written to disk or the database."],
    ["What Gemini sees", "Only two things: the screenshot you choose to upload, and for explanations, a short summary with the category, amount ratio, rules that fired, probability and factor contributions. No merchant names or transaction ids are sent. Gemini never calculates risk."],
    ["The math is yours to inspect", "Statistics, rules, Bayesian inference, prediction and the agent's decisions are plain Python you can read. The probability table is an editable JSON file."],
    ["You confirm everything", "Screenshot details are saved only after you confirm them. Transactions the agent is unsure about wait for your answer and are not used to learn what is normal."],
    ["The system advises, you decide", "Results say \"potentially unusual\" or \"risky\". They are estimates, not verdicts. You choose what to do next."],
    ["Not a banking app", "This is a course project. It cannot move money, block payments or contact a bank, and it should not be used as a real fraud service."],
  ];
  return (
    <section>
      <h1>Privacy and ethics</h1>
      {items.map(([t, b]) => <div className="panel" key={t}><h2>{t}</h2><p>{b}</p></div>)}
    </section>
  );
}
