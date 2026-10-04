"""CHECKPOINT - EVALUATION. Runs every seeded transaction through rules + Bayesian engine and compares the
result with the hidden planted_label. Each transaction is scored LEAVE-ONE-OUT: the profile is learned from
the data WITHOUT that transaction, as if it had just arrived. Month-end prediction is not used here (it needs
a live "today"); CategoryOverspend comes from rule R3 only.
planted_label is read here for scoring and appears ONLY in this report (as a plain-language group)."""
from datetime import date

import analysis

THRESHOLD_SETS = [(0.3, 0.6), (0.4, 0.7), (0.5, 0.8)]
GROUPS = {"anomaly": "planted anomaly", "tricky_legit": "tricky legitimate purchase", None: "normal"}
NOTE = ("The data is synthetic, so these numbers show the system works as designed on this data. They do not "
        "show it would work on real bank data.")


def score_all(conn, today, include_pending):
    rows = conn.execute("SELECT id, date, time, merchant, amount, category, planted_label FROM transactions "
                        "ORDER BY date, time, id").fetchall()
    scored = []
    for r in rows:
        txn = {k: r[k] for k in ("date", "time", "merchant", "amount", "category")}
        a = analysis.analyze(conn, txn, today, exclude_id=r["id"], include_pending=include_pending)
        scored.append({"id": r["id"], "date": r["date"], "time": r["time"], "merchant": r["merchant"],
                       "amount": r["amount"], "category": r["category"], "group": GROUPS[r["planted_label"]],
                       "probability": round(a["probability"], 4), "rules": [x["id"] for x in a["rules_fired"]],
                       "evidence": a["evidence"], "z_score": a["facts"]["z_score"]})
    return scored


def decide(p, low, high):
    return "flagged" if p >= high else "asked" if p >= low else "normal"


def summarize(scored, low, high):
    for r in scored:
        r["decision"] = decide(r["probability"], low, high)
    anomalies = [r for r in scored if r["group"] == "planted anomaly"]
    tricky = [r for r in scored if r["group"] == "tricky legitimate purchase"]
    normal = [r for r in scored if r["group"] == "normal"]
    legit = tricky + normal
    count = lambda rows, d: sum(1 for r in rows if r["decision"] == d)
    confusion = lambda alert: {"true_positive": sum(1 for r in anomalies if alert(r)),
                               "false_negative": sum(1 for r in anomalies if not alert(r)),
                               "false_positive": sum(1 for r in legit if alert(r)),
                               "true_negative": sum(1 for r in legit if not alert(r))}
    pick = lambda rows, *d: [dict(r) for r in rows if r["decision"] in d]
    return {
        "low": low, "high": high,
        "anomalies": {"total": len(anomalies), "flagged": count(anomalies, "flagged"),
                      "asked": count(anomalies, "asked"), "missed": count(anomalies, "normal")},
        "normal": {"total": len(normal), "wrongly_flagged": count(normal, "flagged"), "wrongly_asked": count(normal, "asked")},
        "tricky": [dict(r) for r in tricky],
        "confusion_flag_only": confusion(lambda r: r["decision"] == "flagged"),
        "confusion_flag_or_ask": confusion(lambda r: r["decision"] != "normal"),
        "misses": pick(anomalies, "normal"), "anomalies_only_asked": pick(anomalies, "asked"),
        "false_alarms": pick(legit, "flagged"), "unneeded_questions": pick(normal, "asked"),
        "anomaly_rows": [dict(r) for r in anomalies],
    }


def run_evaluation(conn, today=None):
    today = today or date.today()
    modes = {}
    for name, include_pending, title in (
            ("confirmed_only", False, "Profile learned from confirmed transactions only (the real system)"),
            ("contaminated", True, "Profile also learned from the planted anomalies (shows why that matters)")):
        scored = score_all(conn, today, include_pending)
        modes[name] = {"title": title, "total_scored": len(scored),
                       "threshold_sets": [summarize([dict(r) for r in scored], lo, hi) for lo, hi in THRESHOLD_SETS]}
    return {"note": NOTE, "default_thresholds": {"low": 0.4, "high": 0.7}, "modes": modes}


if __name__ == "__main__":
    from db import get_conn, init_db
    c = get_conn(); init_db(c)
    report = run_evaluation(c)
    for name, mode in report["modes"].items():
        print("\n==", mode["title"])
        for s in mode["threshold_sets"]:
            print(f"  thresholds {s['low']}/{s['high']}: anomalies {s['anomalies']}, normal {s['normal']}, "
                  f"confusion {s['confusion_flag_only']}")
            for r in s["misses"]:
                print("     MISS", r["merchant"], r["amount"], r["probability"], r["rules"])
            for r in s["false_alarms"]:
                print("     FALSE ALARM", r["merchant"], r["amount"], r["probability"], r["rules"])
    print("\n" + report["note"])
