// All calls to the FastAPI backend live here.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options) {
  const res = await fetch(API_BASE + "/api" + path, options);
  let body = null;

  try {
    body = await res.json();
  } catch {
    /* empty body */
  }

  if (!res.ok) {
    const detail = body && body.detail;
    const err = new Error("Request failed");
    err.errors =
      (detail && detail.errors) ||
      (typeof detail === "string"
        ? detail
        : "Something went wrong. Try again.");
    throw err;
  }

  return body;
}
const json = (method, data) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

export const api = {
  meta: () => request("/meta"),
  months: () => request("/transactions/months"),
  list: ({ month, category, search }) => {
    const q = new URLSearchParams();
    if (month) q.set("month", month);
    if (category) q.set("category", category);
    if (search) q.set("search", search);
    return request("/transactions?" + q.toString());
  },
  add: (data) => request("/transactions", json("POST", data)),
  update: (id, data) => request("/transactions/" + id, json("PUT", data)),
  remove: (id) => request("/transactions/" + id, { method: "DELETE" }),
  summary: () => request("/dashboard/summary"),
  overview: () => request("/dashboard/overview"),
  profile: () => request("/profile"),
  categoryProfile: (c) => request("/profile/" + encodeURIComponent(c)),
  rules: () => request("/rules"),
  analyzeRules: (d) => request("/analyze/rules", json("POST", d)),
  bayesStructure: () => request("/bayes/structure"),
  analyzeBayes: (d) => request("/analyze/bayes", json("POST", d)),
  process: (d) => request("/agent/process", json("POST", d)),
  answer: (txn_id, answer) => request("/agent/answer", json("POST", { txn_id, answer })),
  run: (id) => request("/agent/runs/" + id),
  prediction: () => request("/prediction"),
  evaluation: () => request("/evaluation"),
  extract: (file) => { const f = new FormData(); f.append("file", file); return request("/extract", { method: "POST", body: f }); },
  reset: () => request("/demo/reset", { method: "POST" }),
};

export const rupees = (n) => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

// Compact rupee labels for charts: 1.2L, 45k.
export const compact = (n) => (n >= 1e5 ? (n / 1e5).toFixed(1) + "L" : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + "k" : String(Math.round(n)));
export const percent = (p) => (p == null ? "n/a" : Math.round(p * 100) + "%");
export const todayLocal = () => { const d = new Date(); const p = (n) => String(n).padStart(2, "0"); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; };
