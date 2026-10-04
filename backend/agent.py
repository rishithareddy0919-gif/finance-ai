"""PHASE 5 - FINANCIAL INTELLIGENCE AGENT (AI concept: goal-based agent with tools).
GOAL: decide quickly and safely whether a new transaction is routine, needs a question, or is potentially unusual.
The agent perceives a transaction, then repeatedly asks choose_next_tool() what to do next, runs that tool, and
records why. choose_next_tool() is plain Python (no LLM): thresholds come from agent_config.json."""
import json
import os
from datetime import date

import analysis
import bayes
import explain
import prediction
import rules
import transactions as tx
from errors import ApiError
from gemini import call_gemini
from profile import build_profile

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.json")
QUESTION = "Was this transaction made by you? Is this merchant familiar?"
MAX_STEPS = 12


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class AgentState:
    """What the agent knows so far."""
    def __init__(self, transaction, source):
        self.transaction, self.source = transaction, source
        self.context = self.profile = self.prediction = self.quick = None
        self.facts, self.rules_fired, self.rules_level = {}, [], None
        self.evidence, self.contributions, self.probability = None, [], None
        self.predicted_overspend, self.explanation, self.explanation_source = False, None, None
        self.question, self.outcome, self.txn_id = None, None, None
        self.status = "running"                    # running -> awaiting_user | done | flagged
        self.tools_called, self.trace = [], []


# ---------------------------------------------------------------- tools (plain functions)
def get_transaction_history(ctx, st):
    st.context = analysis.build_context(ctx["conn"], st.transaction)
    seen = st.context["prior_merchant_count"]
    return {"times_merchant_seen_before_today": seen, "known_merchant": seen >= 2,
            "same_merchant_payments_today": st.context["same_merchant_count_today"]}


def get_category_statistics(ctx, st):
    st.profile = build_profile(ctx["conn"], ctx["today"])
    txn, cat = st.transaction, st.profile["categories"].get(st.transaction["category"])
    known = st.context["prior_merchant_count"] >= 2
    usual_hour = int(txn["time"][:2]) in st.profile["typical_hours"]
    if cat is None or cat["low_confidence"]:
        st.quick = {"known_merchant": known, "within_normal_range": False, "usual_hour": usual_hour, "routine": False}
        return {"low_confidence": True, "message": "Too little history in this category to call anything routine.",
                "quick_check": st.quick}
    in_range = cat["normal_low"] <= txn["amount"] <= cat["normal_high"]
    st.quick = {"known_merchant": known, "within_normal_range": in_range, "usual_hour": usual_hour,
                "routine": known and in_range and usual_hour}
    return {"mean": cat["mean"], "std": cat["std"], "normal_range": [cat["normal_low"], cat["normal_high"]],
            "quick_check": st.quick}


def check_risk_rules(ctx, st):
    st.facts = rules.compute_facts(st.transaction, st.profile, st.context)
    st.rules_fired, _ = rules.run_engine(st.facts)
    _, st.rules_level = rules.risk_level(st.rules_fired)
    return {"rules_fired": [r["id"] for r in st.rules_fired], "level": st.rules_level}


def predict_month_end(ctx, st):
    txn, today = st.transaction, ctx["today"]
    cat = st.profile["categories"].get(txn["category"])
    same_month = txn["date"][:7] == today.strftime("%Y-%m")
    st.prediction = prediction.predict_from_profile(st.profile, today, txn["category"],
                                                    extra=txn["amount"] if same_month else 0.0)
    usable = same_month and cat is not None and not cat["low_confidence"] and not st.prediction["low_confidence"]
    st.predicted_overspend = usable and st.prediction["status"] != "on track"   # raises CategoryOverspend evidence
    p = st.prediction
    return {"predicted_month_end": p["run_rate_prediction"], "usual_range": [p["normal_low"], p["normal_high"]],
            "status": p["status"], "low_confidence": p["low_confidence"], "raises_overspend_evidence": st.predicted_overspend}


def run_bayesian_analysis(ctx, st):
    overspend = any(r["id"] == "R3" for r in st.rules_fired) or st.predicted_overspend
    st.evidence = bayes.evidence_from_facts(st.facts, overspend)
    st.probability = bayes.infer(st.evidence)
    st.contributions = bayes.explain(st.evidence)
    return {"evidence": st.evidence, "probability": round(st.probability, 4)}


def generate_explanation(ctx, st):
    payload = explain.build_payload(st.transaction["category"], st.facts["amount_ratio"], st.rules_fired,
                                    st.probability, st.contributions)
    st.explanation, st.explanation_source = explain.explain(payload, ctx["gemini"])
    return {"source": st.explanation_source}


def ask_user(ctx, st):
    st.question, st.status = QUESTION, "awaiting_user"
    return {"question": QUESTION}


def log_transaction(ctx, st):
    outcome = outcome_for(st, ctx["config"])
    status = "confirmed" if outcome in ("logged_routine", "logged_normal") else "pending_confirmation"
    note = (st.transaction.get("note") or "")
    pct = "" if st.probability is None else f" (risk {round(st.probability * 100)}%)"
    tag = {"logged_routine": "routine", "logged_normal": "normal", "awaiting_user": "waiting for your answer",
           "flagged": "potentially unusual"}[outcome]
    saved, errors = tx.add_transaction(ctx["conn"], {**st.transaction, "status": status, "note": f"{note} [agent: {tag}{pct}]".strip()},
                                       source=st.source, learn_merchant=(status == "confirmed"))
    if errors:
        raise ApiError(errors)
    st.txn_id, st.outcome = saved["id"], outcome
    st.status = "done" if outcome in ("logged_routine", "logged_normal") else st.status
    if outcome == "flagged":
        st.status = "flagged"
    return {"saved_as": status, "outcome": outcome}


TOOLS = {
    "get_transaction_history": {"description": "Look up how often this merchant appears in the history.", "fn": get_transaction_history},
    "get_category_statistics": {"description": "Read the learned normal range, typical hours and quick-check facts.", "fn": get_category_statistics},
    "check_risk_rules": {"description": "Run the forward-chaining rule engine.", "fn": check_risk_rules},
    "run_bayesian_analysis": {"description": "Compute P(unusual) with the Bayesian network.", "fn": run_bayesian_analysis},
    "predict_month_end": {"description": "Predict category month-end spend; overspend raises evidence.", "fn": predict_month_end},
    "generate_explanation": {"description": "Write a plain-language explanation (Gemini, template fallback).", "fn": generate_explanation},
    "ask_user": {"description": "Ask the user to confirm the transaction.", "fn": ask_user},
    "log_transaction": {"description": "Save the transaction with the decided status.", "fn": log_transaction},
}


# ---------------------------------------------------------------- decision logic (readable, no LLM)
def outcome_for(st, config):
    low, high = config["thresholds"]["low"], config["thresholds"]["high"]
    if st.probability is None:
        return "logged_routine"                       # quick path: no deeper analysis was needed
    if st.probability < low:
        return "logged_normal"
    if st.probability < high:
        return "awaiting_user"
    return "flagged"


def choose_next_tool(st, config):
    """Return (tool_name, reason), or None when the agent is finished."""
    called, low, high = st.tools_called, config["thresholds"]["low"], config["thresholds"]["high"]
    if "log_transaction" in called:
        return None
    if "get_transaction_history" not in called:
        return "get_transaction_history", "First I need to know if this merchant is familiar."
    if "get_category_statistics" not in called:
        return "get_category_statistics", "I need the normal range and usual hours for this category."
    if st.quick["routine"]:                           # STEP 1: quick check, stop early
        return "log_transaction", "Known merchant, amount in the normal range, usual hour: routine, so no deeper analysis."
    for tool, why in (("check_risk_rules", "Something is outside the quick check, so I run the rules."),
                      ("predict_month_end", "I check whether this pushes the category's month-end spend above usual."),
                      ("run_bayesian_analysis", "I combine all the evidence into one probability.")):
        if tool not in called:                        # STEP 2: the deeper analysis
            return tool, why
    p = st.probability
    if p < low:                                       # STEP 3
        return "log_transaction", f"Probability {p:.0%} is below {low:.0%}: log as normal."
    if p < high:                                      # STEP 4
        if "ask_user" not in called:
            return "ask_user", f"Probability {p:.0%} is uncertain (between {low:.0%} and {high:.0%}): ask the user."
        return "log_transaction", "Saving as pending until the user answers."
    if "generate_explanation" not in called:          # STEP 5
        return "generate_explanation", f"Probability {p:.0%} is above {high:.0%}: flag it and explain why."
    return "log_transaction", "Saving as potentially unusual."


def recommendations_for(outcome, category):
    if outcome != "flagged":
        return []
    return ["Review this transaction in your payment app or statement.",
            "If you do not recognise the merchant, check with the merchant or your bank.",
            f"Consider setting a spending limit for {category}."]


def risk_level_for(probability, config):
    if probability is None or probability < config["thresholds"]["low"]:
        return "Low"
    return "Medium" if probability < config["thresholds"]["high"] else "High"


# ---------------------------------------------------------------- running the agent
def process(conn, body, today=None, config=None, gemini_caller=None):
    config = config or load_config()
    source = body.get("source") or "manual"
    if source not in ("manual", "screenshot"):
        raise ApiError(["source must be manual or screenshot"])
    clean, errors = tx.validate_transaction(conn, body)
    if errors:
        raise ApiError(errors)
    st = AgentState({**clean, "status": "confirmed"}, source)
    ctx = {"conn": conn, "today": today or date.today(), "config": config, "gemini": gemini_caller or call_gemini}
    for _ in range(MAX_STEPS):
        choice = choose_next_tool(st, config)
        if choice is None:
            break
        name, why = choice
        result = TOOLS[name]["fn"](ctx, st)
        st.tools_called.append(name)
        st.trace.append({"step": len(st.trace) + 1, "tool": name, "why": why, "result": result})
    save_run(conn, st, config)
    return run_view(conn, st.txn_id)


def save_run(conn, st, config):
    trace = {"steps": st.trace, "facts": st.facts, "evidence": st.evidence, "contributions": st.contributions,
             "rules": [{"id": r["id"], "description": r["description"]} for r in st.rules_fired],
             "rules_level": st.rules_level, "base_probability": st.probability, "quick_check": st.quick,
             "prediction": st.prediction, "explanation": st.explanation, "explanation_source": st.explanation_source,
             "question": st.question, "recommendations": recommendations_for(st.outcome, st.transaction["category"])}
    conn.execute("INSERT INTO agent_runs (txn_id, trace_json, rules_fired, probability, risk_level, outcome)"
                 " VALUES (?,?,?,?,?,?)",
                 (st.txn_id, json.dumps(trace), json.dumps([r["id"] for r in st.rules_fired]), st.probability,
                  risk_level_for(st.probability, config), st.outcome))
    conn.commit()


def run_view(conn, txn_id):
    row = conn.execute("SELECT * FROM agent_runs WHERE txn_id = ? ORDER BY id DESC LIMIT 1", (txn_id,)).fetchone()
    if row is None:
        raise ApiError(["No agent run for this transaction"], 404)
    trace = json.loads(row["trace_json"])
    transaction = tx.get_transaction(conn, txn_id)
    return {"txn_id": txn_id, "transaction": transaction, "outcome": row["outcome"], "probability": row["probability"],
            "risk_level": row["risk_level"], "rules_fired": json.loads(row["rules_fired"]),
            "rules": trace["rules"], "rules_level": trace["rules_level"], "user_feedback": row["user_feedback"],
            "created_at": row["created_at"], "status": transaction["status"], "steps": trace["steps"],
            "facts": trace["facts"], "evidence": trace["evidence"], "contributions": trace["contributions"],
            "explanation": trace["explanation"], "explanation_source": trace["explanation_source"],
            "question": trace["question"], "recommendations": trace["recommendations"],
            "quick_check": trace["quick_check"], "prediction": trace["prediction"]}


def answer(conn, txn_id, user_answer, config=None, gemini_caller=None):
    """The user's answer is new evidence: the odds are updated from the ORIGINAL probability, then re-decided."""
    config = config or load_config()
    ratios = config["feedback_likelihood_ratio"]
    if user_answer not in ratios:
        raise ApiError(["answer must be 'me' or 'not_me'"])
    row = conn.execute("SELECT * FROM agent_runs WHERE txn_id = ? ORDER BY id DESC LIMIT 1", (txn_id,)).fetchone()
    if row is None:
        raise ApiError(["No agent run for this transaction"], 404)
    trace = json.loads(row["trace_json"])
    base = trace["base_probability"] if trace["base_probability"] is not None else bayes.infer({})
    new_p = bayes.update_with_feedback(base, user_answer, ratios)
    outcome = "logged_user_confirmed" if user_answer == "me" else "flagged"
    status = "confirmed" if user_answer == "me" else "pending_confirmation"
    word = "was the user's" if user_answer == "me" else "was NOT the user's"
    trace["steps"].append({"step": len(trace["steps"]) + 1, "tool": "user_answer", "why": "The user answered the question.",
                           "result": {"answer": user_answer}})
    trace["steps"].append({"step": len(trace["steps"]) + 1, "tool": "run_bayesian_analysis",
                           "why": f"Bayesian update: the user said it {word}, so the odds are multiplied by {ratios[user_answer]}.",
                           "result": {"probability_before": round(base, 4), "probability_after": round(new_p, 4)}})
    trace["question"] = None
    transaction = tx.get_transaction(conn, txn_id)
    if outcome == "flagged":
        trace["recommendations"] = recommendations_for("flagged", transaction["category"])
        if not trace["explanation"] and trace["facts"]:
            payload = explain.build_payload(transaction["category"], trace["facts"]["amount_ratio"],
                                            trace["rules"], new_p, trace["contributions"])
            trace["explanation"], trace["explanation_source"] = explain.explain(payload, gemini_caller or call_gemini)
    conn.execute("UPDATE agent_runs SET trace_json=?, probability=?, risk_level=?, outcome=?, user_feedback=? WHERE id=?",
                 (json.dumps(trace), new_p, risk_level_for(new_p, config), outcome, user_answer, row["id"]))
    conn.execute("UPDATE transactions SET status = ? WHERE id = ?", (status, txn_id))
    conn.commit()
    return run_view(conn, txn_id)
