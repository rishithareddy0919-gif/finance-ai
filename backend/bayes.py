"""PHASE 4 - BAYESIAN RISK ENGINE (AI concept: probabilistic reasoning under uncertainty). No probability library.

Network:  AmountDeviation, NewMerchant, CategoryOverspend, UnusualTime  --->  UnusualTransaction
The four parents are independent a priori. infer() answers P(UnusualTransaction = yes | evidence); any parent
that is missing from the evidence is summed out ("marginalized") using its prior probability."""
import itertools
import json
import os

CPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bayes_cpt.json")
PARENTS = ["AmountDeviation", "NewMerchant", "CategoryOverspend", "UnusualTime"]
CHILD = "UnusualTransaction"
STATES = {"AmountDeviation": ["normal", "high", "very_high"], "NewMerchant": ["yes", "no"],
          "CategoryOverspend": ["yes", "no"], "UnusualTime": ["yes", "no"]}
HIGH_Z, VERY_HIGH_Z = 1.5, 3.0


def load_model(path=CPT_PATH):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    cpt = {}
    for group in raw["cpt_groups"]:
        for row in group["rows"]:
            key = (group["AmountDeviation"], row["NewMerchant"], row["CategoryOverspend"], row["UnusualTime"])
            cpt[key] = row["p"]
    priors = {v: raw["priors"][v] for v in PARENTS}
    if len(cpt) != 24:
        raise ValueError(f"CPT must have 24 rows, found {len(cpt)}")
    for v in PARENTS:
        if abs(sum(priors[v].values()) - 1.0) > 1e-9:
            raise ValueError(f"Priors for {v} must add up to 1")
    return {"priors": priors, "cpt": cpt}


MODEL = load_model()


def clean_evidence(evidence):
    """Keep only known variables with a value; reject unknown names or states."""
    clean = {}
    for var, state in (evidence or {}).items():
        if state is None:
            continue
        if var not in STATES or state not in STATES[var]:
            raise ValueError(f"Invalid evidence {var}={state}")
        clean[var] = state
    return clean


def infer(evidence, model=None):
    """P(UnusualTransaction=yes | evidence), summing over every combination of the missing parents."""
    model = model or MODEL
    known = clean_evidence(evidence)
    missing = [v for v in PARENTS if v not in known]
    total = 0.0
    for combo in itertools.product(*[STATES[v] for v in missing]):
        guess = dict(zip(missing, combo))
        weight = 1.0
        for var, state in guess.items():
            weight *= model["priors"][var][state]            # probability of this guess for the missing parents
        full = {**known, **guess}
        total += weight * model["cpt"][tuple(full[v] for v in PARENTS)]
    return total


def explain(evidence, model=None):
    """Contribution of each evidence item = P(with it) - P(with that item removed / set to unknown)."""
    known = clean_evidence(evidence)
    base = infer(known, model)
    out = []
    for var, state in known.items():
        without = {k: v for k, v in known.items() if k != var}
        out.append({"variable": var, "state": state, "contribution": base - infer(without, model)})
    return sorted(out, key=lambda c: -abs(c["contribution"]))


def evidence_from_facts(facts, overspend):
    """Turn rule-engine facts into Bayesian evidence."""
    z = facts["z_score"]
    amount = "very_high" if z > VERY_HIGH_Z else "high" if z >= HIGH_Z else "normal"
    return {"AmountDeviation": amount,
            "NewMerchant": "yes" if facts["is_new_merchant"] else "no",
            "CategoryOverspend": "yes" if overspend else "no",
            "UnusualTime": "yes" if facts["is_unusual_hour"] else "no"}


def update_with_feedback(probability, answer, ratios):
    """User answer as new evidence, using odds: new_odds = old_odds x likelihood_ratio.
    'me' has a ratio below 1 (lowers risk); 'not_me' has a ratio above 1 (raises risk)."""
    odds = probability / (1 - probability) if probability < 1 else 1e9
    odds *= ratios[answer]
    return odds / (1 + odds)


def network_structure(model=None):
    """Everything the Bayesian Lab needs to draw the network and the table."""
    model = model or MODEL
    rows = []
    for key, p in model["cpt"].items():
        row = dict(zip(PARENTS, key))
        row["p"] = p
        rows.append(row)
    return {"nodes": PARENTS + [CHILD], "edges": [[p, CHILD] for p in PARENTS], "states": STATES,
            "priors": model["priors"], "cpt": rows}
