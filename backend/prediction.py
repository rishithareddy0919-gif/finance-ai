"""PHASE 6 - MONTH-END PREDICTION (AI concept: prediction from learned patterns).
Two simple predictors: run-rate (spend pace so far) and linear regression on past monthly totals.
The headline "predicted month-end" is the run-rate; the regression is shown beside it as a second opinion."""
import calendar
from datetime import date

from profile import build_profile, mean, std

MIN_DAYS = 5
MIN_MONTHS = 3


def run_rate(spent, days_elapsed, days_in_month):
    return spent / days_elapsed * days_in_month


def least_squares(xs, ys):
    """Best straight line y = slope*x + intercept through the points (ordinary least squares)."""
    mx, my = mean(xs), mean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return slope, my - slope * mx


def regression_forecast(history):
    """Predict the next month from past monthly totals (needs at least 2 months)."""
    if len(history) < 2:
        return None
    slope, intercept = least_squares(list(range(len(history))), history)
    return max(0.0, slope * len(history) + intercept)


def status_for(predicted, avg, spread):
    """on track: inside mean +/- 1 std. above usual: over mean+1std. well above usual: over mean+2std."""
    if predicted > avg + 2 * spread:
        return "well above usual"
    if predicted > avg + spread:
        return "above usual"
    return "on track"


def predict_series(label, history, spent, days_elapsed, days_in_month, complete_count):
    """history = totals of completed months, oldest first."""
    low = []
    if days_elapsed < MIN_DAYS:
        low.append(f"only {days_elapsed} day(s) of this month have passed (need {MIN_DAYS})")
    if complete_count < MIN_MONTHS:
        low.append(f"only {complete_count} completed month(s) of history (need {MIN_MONTHS})")
    predicted = run_rate(spent, days_elapsed, days_in_month)
    avg = mean(history) if history else 0.0
    spread = std(history) if history else 0.0
    regression = regression_forecast(history)
    return {
        "label": label, "spent_so_far": round(spent, 2), "days_elapsed": days_elapsed, "days_in_month": days_in_month,
        "run_rate_prediction": round(predicted, 2),
        "regression_prediction": round(regression, 2) if regression is not None else None,
        "historical_average": round(avg, 2), "normal_low": round(max(0.0, avg - spread), 2),
        "normal_high": round(avg + spread, 2),
        "pct_diff_vs_average": round((predicted - avg) / avg * 100, 1) if avg > 0 else None,
        "status": status_for(predicted, avg, spread),
        "low_confidence": bool(low),
        "message": ("Low confidence: " + " and ".join(low) + ".") if low else "",
    }


def predict_from_profile(profile, today, category=None, extra=0.0):
    """category=None predicts total spend. extra adds an amount not yet saved (a transaction being analyzed)."""
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    series = profile["monthly_totals"] if category is None else profile["category_monthly_totals"].get(category, {})
    complete = [m for m in profile["complete_months"] if m < profile["current_month"]]
    history = [series.get(m, 0.0) for m in complete]
    spent = series.get(profile["current_month"], 0.0) + extra
    return predict_series(category or "All spending", history, spent, today.day, days_in_month, len(complete))


def month_to_date_points(conn, today):
    """Cumulative confirmed spending day by day this month, plus the run-rate projection line."""
    month = today.strftime("%Y-%m")
    rows = conn.execute("SELECT CAST(substr(date,9,2) AS INT) AS d, SUM(amount) AS s FROM transactions"
                        " WHERE status='confirmed' AND substr(date,1,7)=? GROUP BY d", (month,)).fetchall()
    per_day = {r["d"]: r["s"] for r in rows}
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    running, cumulative = 0.0, []
    for day in range(1, today.day + 1):
        running += per_day.get(day, 0.0)
        cumulative.append({"day": day, "spent": round(running, 2)})
    rate = running / today.day
    projected = [{"day": d, "spent": round(rate * d, 2)} for d in range(1, days_in_month + 1)]
    return cumulative, projected


def predict_all(conn, today=None):
    today = today or date.today()
    profile = build_profile(conn, today)
    cumulative, projected = month_to_date_points(conn, today)
    return {"today": today.isoformat(), "overall": predict_from_profile(profile, today),
            "categories": {c: predict_from_profile(profile, today, c) for c in profile["categories"]
                           if not profile["categories"][c]["low_confidence"]},
            "cumulative": cumulative, "projected": projected}
