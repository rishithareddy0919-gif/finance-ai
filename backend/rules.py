"""PHASE 3 - FORWARD-CHAINING RULE ENGINE (AI concept: production system / expert system).
Rules are DATA, not if-statements. The engine keeps firing rules whose conditions are true until nothing new
fires (forward chaining). A rule's conclusion becomes a new fact, so later rules can build on earlier ones."""
import math
import operator

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq}

# id, description, conditions (ALL must hold), conclusion, weight (risk points added to the score)
RULES = [
    {"id": "R1", "description": "Amount is more than 3 times the category average",
     "conditions": [{"fact": "amount_ratio", "op": ">", "value": 3}],
     "conclusion": "amount_anomaly", "weight": 2},
    {"id": "R2", "description": "New merchant and the amount is above the normal range",
     "conditions": [{"fact": "is_new_merchant", "op": "==", "value": True},
                    {"fact": "above_normal_range", "op": "==", "value": True}],
     "conclusion": "new_merchant_high_amount", "weight": 2},
    {"id": "R3", "description": "Category spending this month is above 1.5 times the usual monthly average",
     "conditions": [{"fact": "category_spend_ratio", "op": ">", "value": 1.5}],
     "conclusion": "overspending", "weight": 1},
    {"id": "R4", "description": "Transaction hour is outside your typical hours",
     "conditions": [{"fact": "is_unusual_hour", "op": "==", "value": True}],
     "conclusion": "unusual_time", "weight": 1},
    {"id": "R5", "description": "Three or more payments to the same new merchant today",
     "conditions": [{"fact": "is_new_merchant", "op": "==", "value": True},
                    {"fact": "same_merchant_count_today", "op": ">=", "value": 3}],
     "conclusion": "repeated_new_merchant", "weight": 2},
    {"id": "R6", "description": "Amount is within the normal range and the merchant is known",
     "conditions": [{"fact": "within_normal_range", "op": "==", "value": True},
                    {"fact": "is_new_merchant", "op": "==", "value": False}],
     "conclusion": "routine", "weight": 0},
]
LEVELS = [(3, "High"), (1, "Medium"), (0, "Low")]      # score at or above the number -> level


def z_score(amount, mean, std):
    if std > 0:
        return (amount - mean) / std
    return 0.0 if amount == mean else math.copysign(99.0, amount - mean)   # no spread at all: any difference is huge


def compute_facts(txn, profile, context):
    """Turn a transaction + the learned profile into facts the rules can read.
    context carries database lookups: prior_merchant_count, same_merchant_count_today, month_to_date_category."""
    cat = profile["categories"].get(txn["category"])
    if cat and not cat["low_confidence"]:
        stats, source = cat, "category"
    else:                                              # too little data in this category: use all spending instead
        overall = profile["overall"] or {"mean": 0.0, "std": 0.0}
        stats = {"mean": overall["mean"], "std": overall["std"], "monthly_average": None,
                 "normal_low": max(0.0, overall["mean"] - 1.5 * overall["std"]),
                 "normal_high": overall["mean"] + 1.5 * overall["std"]}
        source = "overall"
    amount, hour = txn["amount"], int(txn["time"][:2])
    avg = stats["monthly_average"]
    month_spend = context["month_to_date_category"] + amount
    return {
        "amount": amount, "category": txn["category"], "hour": hour, "stats_source": source,
        "amount_ratio": round(amount / stats["mean"], 3) if stats["mean"] > 0 else 0.0,
        "z_score": round(z_score(amount, stats["mean"], stats["std"]), 3),
        "normal_low": stats["normal_low"], "normal_high": stats["normal_high"],
        "above_normal_range": amount > stats["normal_high"],
        "within_normal_range": stats["normal_low"] <= amount <= stats["normal_high"],
        "is_new_merchant": context["prior_merchant_count"] < 2,
        "is_unusual_hour": hour not in profile["typical_hours"],
        "category_spend_ratio": round(month_spend / avg, 3) if avg else 0.0,
        "same_merchant_count_today": context["same_merchant_count_today"],
    }


def condition_holds(cond, facts):
    value = facts.get(cond["fact"])
    return value is not None and OPS[cond["op"]](value, cond["value"])


def run_engine(facts, rules=RULES):
    """Forward chaining: loop until a full pass fires no new rule."""
    facts = dict(facts)
    fired, done = [], set()
    progress = True
    while progress:
        progress = False
        for rule in rules:
            if rule["id"] in done:
                continue
            if all(condition_holds(c, facts) for c in rule["conditions"]):
                done.add(rule["id"])
                facts[rule["conclusion"]] = True           # the conclusion is now a fact
                fired.append({"id": rule["id"], "description": rule["description"],
                              "conclusion": rule["conclusion"], "weight": rule["weight"]})
                progress = True
    return fired, facts


def risk_level(fired):
    score = sum(r["weight"] for r in fired)
    return score, next(name for floor, name in LEVELS if score >= floor)


def evaluate(txn, profile, context, rules=RULES):
    facts = compute_facts(txn, profile, context)
    fired, _ = run_engine(facts, rules)
    score, level = risk_level(fired)
    return {"facts": facts, "rules_fired": fired, "conclusions": [r["conclusion"] for r in fired],
            "score": score, "level": level}
