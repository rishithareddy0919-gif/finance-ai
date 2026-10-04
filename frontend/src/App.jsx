import React, { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard.jsx";
import Transactions from "./pages/Transactions.jsx";
import AddTransaction from "./pages/AddTransaction.jsx";
import ScreenshotPage from "./pages/ScreenshotPage.jsx";
import Profile from "./pages/Profile.jsx";
import RuleTester from "./pages/RuleTester.jsx";
import BayesLab from "./pages/BayesLab.jsx";
import Prediction from "./pages/Prediction.jsx";
import Investigation from "./pages/Investigation.jsx";
import DemoScenario from "./pages/DemoScenario.jsx";
import Privacy from "./pages/Privacy.jsx";

// group: section heading in the sidebar. hidden: reachable by link only.
const PAGES = [
  { id: "dashboard", label: "Dashboard", icon: "▦", view: Dashboard, group: "Overview" },
  { id: "transactions", label: "Transactions", icon: "☰", view: Transactions, group: "Data" },
  { id: "add", label: "Add Transaction", short: "Add", icon: "＋", view: AddTransaction, group: "Data" },
  { id: "screenshot", label: "Scan Screenshot", icon: "▣", view: ScreenshotPage, group: "Data" },
  { id: "profile", label: "Profile", icon: "◔", view: Profile, group: "Intelligence" },
  { id: "rules", label: "Rule Tester", icon: "✓", view: RuleTester, group: "Intelligence" },
  { id: "bayes", label: "Bayesian Lab", icon: "◇", view: BayesLab, group: "Intelligence" },
  { id: "prediction", label: "Prediction", icon: "↗", view: Prediction, group: "Intelligence" },
  { id: "investigation", label: "Investigation", icon: "⌕", view: Investigation, group: "Intelligence" },
  { id: "demo", label: "Demo Scenario", icon: "▶", view: DemoScenario, group: "Report" },
  { id: "privacy", label: "Privacy & Ethics", icon: "⚿", view: Privacy, group: "Report" },
];
const TABS = ["dashboard", "transactions", "add"];

function route() {
  const [id, param] = window.location.hash.slice(1).split("/");
  return { page: PAGES.find((p) => p.id === id) || PAGES[0], param };
}

export default function App() {
  const [r, setR] = useState(route());
  const [more, setMore] = useState(false);
  useEffect(() => {
    const onHash = () => { setR(route()); setMore(false); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const View = r.page.view;
  const groups = [...new Set(PAGES.map((p) => p.group))];
  const link = (p, cls = "") => (
    <a key={p.id} href={"#" + p.id} className={"nav-link" + (p.id === r.page.id ? " active" : "") + cls}>
      <span className="nav-icon" aria-hidden="true">{p.icon}</span><span>{p.label}</span>
    </a>);
  return (
    <div className="shell">
      <header className="topbar">Personal Financial Intelligence</header>
      <nav className="nav" aria-label="Main">
        <div className="nav-brand">Personal Financial<br />Intelligence</div>
        <div className="side-links">
          {groups.map((g) => (<div key={g}><div className="nav-group">{g}</div>{PAGES.filter((p) => p.group === g).map((p) => link(p))}</div>))}
        </div>
        <div className="tab-links">
          {TABS.map((id) => { const p = PAGES.find((x) => x.id === id); return (
            <a key={id} href={"#" + id} className={"nav-link" + (id === r.page.id ? " active" : "")}>
              <span className="nav-icon" aria-hidden="true">{p.icon}</span><span>{p.short || p.label}</span></a>); })}
          <button className={"nav-link more" + (more || !TABS.includes(r.page.id) ? " active" : "")} aria-expanded={more} onClick={() => setMore(!more)}>
            <span className="nav-icon" aria-hidden="true">⋯</span><span>More</span></button>
        </div>
        <p className="nav-note">Demo with synthetic data. Not a banking app.</p>
      </nav>
      {more && <div className="sheet" role="menu">{PAGES.filter((p) => !TABS.includes(p.id)).map((p) => link(p))}</div>}
      <main className="content"><View param={r.param} /></main>
    </div>
  );
}
