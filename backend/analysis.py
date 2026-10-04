"""Glue used by the agent tools, the evaluation and the analyze endpoints:
database lookups for the rule facts, and the rules -> Bayesian evidence step."""
from datetime import date

import bayes
import rules
from profile import build_profile


def build_context(conn, txn, exclude_id=None, include_pending=False):
    """Database facts about one transaction. exclude_id removes the transaction itself (when it is already saved)."""
    skip = exclude_id if exclude_id is not None else -1
    ok = "(status = 'confirmed' OR ?)"          # include_pending also counts transactions awaiting review
    prior = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE " + ok + " AND id != ? AND merchant = ? COLLATE NOCASE"
        " AND date < ?", (include_pending, skip, txn["merchant"], txn["date"])).fetchone()[0]
    same_day = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE id != ? AND merchant = ? COLLATE NOCASE AND date = ? AND time <= ?",
        (skip, txn["merchant"], txn["date"], txn["time"])).fetchone()[0]
    month_spend = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE " + ok + " AND id != ? AND category = ?"
        " AND substr(date,1,7) = ? AND date <= ?", (include_pending, skip, txn["category"], txn["date"][:7], txn["date"])).fetchone()[0]
    return {"prior_merchant_count": prior, "same_merchant_count_today": same_day + 1,
            "month_to_date_category": month_spend}


def analyze(conn, txn, today=None, exclude_id=None, predicted_overspend=False, include_pending=False):
    """Profile -> facts -> rules -> Bayesian probability for one transaction (nothing is saved)."""
    today = today or date.today()
    profile = build_profile(conn, today, exclude_id, include_pending)
    context = build_context(conn, txn, exclude_id, include_pending)
    result = rules.evaluate(txn, profile, context)
    fired_ids = [r["id"] for r in result["rules_fired"]]
    evidence = bayes.evidence_from_facts(result["facts"], "R3" in fired_ids or predicted_overspend)
    return {**result, "profile": profile, "context": context, "evidence": evidence,
            "probability": bayes.infer(evidence), "contributions": bayes.explain(evidence)}
