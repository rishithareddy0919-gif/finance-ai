"""PHASE 2 - PERSONAL FINANCIAL PROFILE (AI concept: statistical learning / learning "normal" from data).
Everything is computed from CONFIRMED transactions only, with plain arithmetic you can check by hand.
The core is profile_from_rows(), a pure function of a list of dicts, so tests need no database."""
import math
from collections import Counter, defaultdict
from datetime import date

MIN_CATEGORY_TRANSACTIONS = 5     # fewer than this -> low_confidence instead of fake statistics
RANGE_WIDTH = 1.5                 # normal range = mean +/- 1.5 x standard deviation
TOP_MERCHANTS = 3
KNOWN_MIN_SEEN = 2                # a merchant seen at least twice is "known"
HOUR_COVERAGE = 0.95              # typical hours hold 95% of transactions


def mean(values):
    return sum(values) / len(values)


def std(values):
    """Population standard deviation: sqrt(average squared distance from the mean)."""
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def typical_hours(hour_counts, coverage=HOUR_COVERAGE):
    """Busiest hours first, until together they hold `coverage` of all transactions."""
    total = sum(hour_counts.values())
    chosen, running = [], 0
    for hour, count in sorted(hour_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if running / total >= coverage:
            break
        chosen.append(hour)
        running += count
    return sorted(chosen)


def month_range(first, last):
    """Every 'YYYY-MM' from first to last inclusive (months with no spending still count as 0)."""
    y, m = int(first[:4]), int(first[5:])
    out = []
    while f"{y:04d}-{m:02d}" <= last:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def profile_from_rows(rows, today=None):
    today = today or date.today()
    current_month = today.strftime("%Y-%m")
    empty = {"as_of": today.isoformat(), "current_month": current_month, "months": [], "complete_months": [],
             "monthly_totals": {}, "category_monthly_totals": {}, "overall": None, "typical_hours": [],
             "known_merchants": [], "categories": {}}
    if not rows:
        return empty

    months = month_range(min(r["date"][:7] for r in rows), max(current_month, max(r["date"][:7] for r in rows)))
    complete = [m for m in months if m < current_month] or months     # fall back if all data is in one month
    monthly = {m: 0.0 for m in months}
    by_cat_month = defaultdict(lambda: {m: 0.0 for m in months})
    by_cat = defaultdict(list)
    merchant_names, merchant_seen = {}, Counter()
    category_merchants = defaultdict(Counter)
    for r in rows:
        month = r["date"][:7]
        monthly[month] += r["amount"]
        by_cat_month[r["category"]][month] += r["amount"]
        by_cat[r["category"]].append(r["amount"])
        key = r["merchant"].lower()
        merchant_names.setdefault(key, r["merchant"])
        merchant_seen[key] += 1
        category_merchants[r["category"]][r["merchant"]] += 1

    amounts = [r["amount"] for r in rows]
    categories = {}
    for cat, values in by_cat.items():
        if len(values) < MIN_CATEGORY_TRANSACTIONS:
            categories[cat] = low_confidence_entry(cat, len(values))
            continue
        m, s = mean(values), std(values)
        avg = sum(by_cat_month[cat][mo] for mo in complete) / len(complete)
        current = by_cat_month[cat][current_month] if current_month in by_cat_month[cat] else 0.0
        categories[cat] = {
            "category": cat, "low_confidence": False, "count": len(values),
            "mean": round(m, 2), "std": round(s, 2),
            "monthly_average": round(avg, 2),
            "normal_low": round(max(0.0, m - RANGE_WIDTH * s), 2),       # floored at 0
            "normal_high": round(m + RANGE_WIDTH * s, 2),
            "current_month_spend": round(current, 2),
            "current_vs_average_ratio": round(current / avg, 3) if avg > 0 else None,
            "top_merchants": [{"merchant": n, "count": c} for n, c in category_merchants[cat].most_common(TOP_MERCHANTS)],
        }
    return {
        "as_of": today.isoformat(), "current_month": current_month, "months": months, "complete_months": complete,
        "monthly_totals": {m: round(v, 2) for m, v in monthly.items()},
        "category_monthly_totals": {c: {m: round(v, 2) for m, v in d.items()} for c, d in by_cat_month.items()},
        "overall": {"count": len(amounts), "mean": round(mean(amounts), 2), "std": round(std(amounts), 2)},
        "typical_hours": typical_hours(Counter(int(r["time"][:2]) for r in rows)),
        "known_merchants": sorted(merchant_names[k] for k, n in merchant_seen.items() if n >= KNOWN_MIN_SEEN),
        "categories": categories,
    }


def low_confidence_entry(category, count):
    return {"category": category, "low_confidence": True, "count": count,
            "message": f"Only {count} confirmed transactions in {category}; at least {MIN_CATEGORY_TRANSACTIONS} are needed."}


def build_profile(conn, today=None, exclude_id=None, include_pending=False):
    """Load confirmed transactions from SQLite and profile them. exclude_id supports leave-one-out evaluation."""
    sql = "SELECT id, date, time, merchant, amount, category FROM transactions WHERE (status = 'confirmed' OR ?)"
    params = [include_pending]          # pending rows are used only when evaluating the "contaminated" comparison
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    return profile_from_rows([dict(r) for r in conn.execute(sql, params)], today)


def category_profile(profile, category):
    entry = profile["categories"].get(category)
    return entry if entry else low_confidence_entry(category, 0)
