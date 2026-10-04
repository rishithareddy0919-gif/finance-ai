"""Route logic that is not already in agent.py / prediction.py / evaluate.py. Kept out of main.py so it can be tested."""
from datetime import date

import analysis
import bayes
import rules
import transactions as tx
from errors import ApiError
from profile import build_profile


def _validated(conn, body):
    clean, errors = tx.validate_transaction(conn, body)
    if errors:
        raise ApiError(errors)
    return clean


def analyze_rules(conn, body, today=None):
    """POST /analyze/rules: the transaction is NOT saved."""
    txn = _validated(conn, body)
    today = today or date.today()
    result = rules.evaluate(txn, build_profile(conn, today), analysis.build_context(conn, txn))
    return {"category_used": txn["category"], **result}


def analyze_bayes(conn, body, today=None):
    """POST /analyze/bayes: either {"evidence": {...}} (Bayesian Lab) or {"transaction": {...}} (what-if simulator)."""
    if body.get("transaction"):
        txn = _validated(conn, body["transaction"])
        a = analysis.analyze(conn, txn, today or date.today())
        return {"evidence": a["evidence"], "probability": a["probability"], "contributions": a["contributions"],
                "rules_fired": [r["id"] for r in a["rules_fired"]], "z_score": a["facts"]["z_score"]}
    try:
        evidence = bayes.clean_evidence(body.get("evidence") or {})
    except ValueError as e:
        raise ApiError([str(e)])
    return {"evidence": evidence, "probability": bayes.infer(evidence), "contributions": bayes.explain(evidence)}


def dashboard_overview(conn, today=None):
    import prediction
    today = today or date.today()
    profile = build_profile(conn, today)
    pred = prediction.predict_all(conn, today)
    month = today.strftime("%Y-%m")
    summary = tx.month_summary(conn, month)
    count = lambda outcome: conn.execute("SELECT COUNT(*) FROM agent_runs WHERE outcome = ?", (outcome,)).fetchone()[0]
    alerts = conn.execute(
        "SELECT r.txn_id, r.probability, r.risk_level, r.outcome, t.merchant, t.amount, t.date, t.category FROM agent_runs r"
        " JOIN transactions t ON t.id = r.txn_id WHERE r.outcome IN ('flagged', 'awaiting_user') ORDER BY r.id DESC LIMIT 6"
    ).fetchall()
    return {
        "month": month, "total_spend": summary["total_spend"], "prediction": pred["overall"],
        "cumulative": pred["cumulative"], "projected": pred["projected"],
        "unusual_count": count("flagged"), "pending_count": count("awaiting_user"),
        "trend": [{"month": m, "total": profile["monthly_totals"][m]} for m in profile["months"]],
        "category_comparison": [{"category": c, "current": e["current_month_spend"], "usual": e["monthly_average"]}
                                for c, e in profile["categories"].items() if not e["low_confidence"]],
        "recent_alerts": [dict(a) for a in alerts],
    }
