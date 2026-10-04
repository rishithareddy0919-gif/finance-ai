"""Synthetic demo data: an Indian student's spending. Run `python seed.py` or use the Reset button.
Deterministic (fixed random seed) so the numbers are the same every time."""
import calendar
import random
from datetime import date, timedelta

from db import get_conn, init_db
from transactions import add_transaction

# merchant, category, min amount, max amount, usual hours, payment method, weight (how often)
ROUTINE = [
    ("College Canteen", "Food", 30, 90, [8, 9, 13, 16], "UPI", 5),
    ("Hostel Mess", "Food", 60, 80, [8, 13, 20], "UPI", 4),
    ("Swiggy", "Food", 150, 450, [13, 20, 21, 22], "UPI", 3),
    ("Zomato", "Food", 180, 500, [13, 20, 21, 22], "UPI", 3),
    ("Uber", "Travel", 80, 300, [8, 9, 18, 19, 21], "UPI", 3),
    ("Metro Card Recharge", "Travel", 100, 300, [8, 9, 18], "UPI", 1),
    ("Amazon", "Shopping", 299, 1500, [12, 18, 20, 21], "Card", 1),
    ("Myntra", "Shopping", 499, 1800, [19, 20, 21], "Card", 0.5),
    ("Campus Stationery", "Education", 40, 400, [10, 11, 15], "Cash", 1),
    ("BookMyShow", "Entertainment", 250, 450, [17, 18, 19], "UPI", 0.5),
]
# merchant, category, amount low, amount high, day of month, time, payment method
MONTHLY = [
    ("Jio", "Bills", 299, 299, 5, "10:15", "UPI"),
    ("Spotify", "Entertainment", 119, 119, 8, "09:00", "UPI"),
    ("Udemy", "Education", 449, 449, 15, "14:00", "Card"),
    ("PG Electricity", "Bills", 400, 700, 20, "11:00", "UPI"),
]
# month_offset (0 = current month), day, time, merchant, amount, category, payment, label, note
PLANTED = [
    (-3, 9, "15:30", "Croma Electronics", 48000, "Shopping", "Card", "anomaly", None),
    (-3, 21, "03:12", "QuickCash Wallet", 25000, "Shopping", "UPI", "anomaly", None),
    (-2, 6, "14:05", "Swiggy", 6500, "Food", "UPI", "anomaly", None),
    (-2, 17, "03:40", "Uber", 4200, "Travel", "UPI", "anomaly", None),
    (-1, 11, "01:05", "TopUpZone", 1499, "Entertainment", "UPI", "anomaly", None),
    (-1, 11, "01:12", "TopUpZone", 1499, "Entertainment", "UPI", "anomaly", None),
    (-1, 11, "01:20", "TopUpZone", 1499, "Entertainment", "UPI", "anomaly", None),
    (-1, 25, "04:05", "Amazon", 18900, "Shopping", "Card", "anomaly", None),
    (0, 2, "02:30", "FastBet247", 7500, "Entertainment", "UPI", "anomaly", None),
    # legitimate but large: a good system should not panic about these
    (-3, 14, "19:45", "Amazon", 28500, "Shopping", "Card", "tricky_legit", "Laptop (planned purchase)"),
    (-2, 26, "11:00", "University Fee Portal", 45000, "Education", "Net Banking", "tricky_legit", "Semester fee"),
    (-1, 4, "09:10", "IndiGo Airlines", 7800, "Travel", "Card", "tricky_legit", "Flight home for Diwali"),
]


def _shift_month(day, offset):
    """First day of the month that is `offset` months from `day`'s month."""
    index = day.year * 12 + (day.month - 1) + offset
    return date(index // 12, index % 12 + 1, 1)


def seed(conn, today=None):
    today = today or date.today()
    rng = random.Random(42)
    start = _shift_month(today, -3)

    # 1. everyday spending: small amounts, regular merchants, normal hours
    day = start
    while day <= today:
        for _ in range(rng.choice([0, 1, 2, 2, 3, 3, 4])):
            name, cat, low, high, hours, method, _w = rng.choices(ROUTINE, weights=[r[6] for r in ROUTINE])[0]
            when = f"{rng.choice(hours):02d}:{rng.randint(0, 59):02d}"
            add_transaction(conn, {"date": day.isoformat(), "time": when, "merchant": name,
                                   "amount": rng.randint(low, high), "category": cat,
                                   "payment_method": method}, source="manual")
        day += timedelta(days=1)

    # 2. bills and subscriptions that repeat every month
    for offset in (-3, -2, -1, 0):
        first = _shift_month(today, offset)
        for name, cat, low, high, dom, when, method in MONTHLY:
            when_date = first.replace(day=dom)
            if when_date <= today:
                add_transaction(conn, {"date": when_date.isoformat(), "time": when, "merchant": name,
                                       "amount": rng.randint(low, high), "category": cat,
                                       "payment_method": method})

    # 3. planted rows, marked in the hidden planted_label column (used only by the evaluation checkpoint)
    for offset, dom, when, name, amount, cat, method, label, note in PLANTED:
        first = _shift_month(today, offset)
        dom = min(dom, calendar.monthrange(first.year, first.month)[1])
        when_date = min(first.replace(day=dom), today)
        # Suspicious rows wait for the user's review (pending_confirmation), so they do not distort what the
        # system learns as "normal". Legitimate large purchases were confirmed by the user.
        status = "pending_confirmation" if label == "anomaly" else "confirmed"
        add_transaction(conn, {"date": when_date.isoformat(), "time": when, "merchant": name,
                               "amount": amount, "category": cat, "payment_method": method, "note": note,
                               "status": status},
                        planted_label=label, learn_merchant=False)   # odd merchants stay "unknown"
    # known merchants table = the regular ones only
    for name, cat, *_ in ROUTINE + MONTHLY:
        conn.execute("INSERT OR IGNORE INTO merchants (name, category) VALUES (?, ?)", (name, cat))
    conn.commit()


def reset_demo_data(conn, today=None):
    conn.execute("DELETE FROM agent_runs")
    conn.execute("DELETE FROM transactions")
    conn.execute("DELETE FROM merchants")
    conn.execute("DELETE FROM sqlite_sequence WHERE name = 'transactions'")
    conn.commit()
    seed(conn, today)
    return conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


if __name__ == "__main__":
    connection = get_conn()
    init_db(connection)
    print("Seeded", reset_demo_data(connection), "transactions")
