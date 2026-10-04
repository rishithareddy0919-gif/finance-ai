"""Transaction rules: validation, CRUD, filters, and the dashboard summary.
Every SELECT uses PUBLIC_COLUMNS, so planted_label can never leave this module."""
import math
import re
from datetime import date

from constants import ALL_CATEGORIES, PAYMENT_METHODS, STATUSES
from knowledge_base import categorize

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")          # 24-hour HH:MM
PUBLIC_COLUMNS = "id, date, time, merchant, amount, category, payment_method, source, status, note, created_at"
EDITABLE = ("date", "time", "merchant", "amount", "category", "payment_method", "status", "note")


def _parse_amount(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("₹", "").strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def lookup_category(conn, merchant):
    row = conn.execute("SELECT category FROM merchants WHERE name = ?", (merchant,)).fetchone()
    return row["category"] if row else None


def validate_transaction(conn, data):
    """Return (clean_values, list_of_error_messages). Empty list means valid."""
    errors, clean = [], {}

    d = str(data.get("date") or "").strip()
    if not DATE_RE.match(d):
        errors.append("date must look like 2026-09-30")
    else:
        try:
            date.fromisoformat(d)
        except ValueError:
            errors.append(f"{d} is not a real calendar date")
    clean["date"] = d

    t = str(data.get("time") or "").strip()
    if not TIME_RE.match(t):
        errors.append("time must be 24-hour HH:MM, for example 14:30 or 03:05")
    clean["time"] = t

    merchant = " ".join(str(data.get("merchant") or "").split())
    if not merchant:
        errors.append("merchant is required")
    elif len(merchant) > 80:
        errors.append("merchant must be 80 characters or fewer")
    clean["merchant"] = merchant

    amount = _parse_amount(data.get("amount"))
    if amount is None or amount <= 0:
        errors.append("amount must be a number greater than 0")
    clean["amount"] = round(amount, 2) if amount else amount

    category = str(data.get("category") or "").strip()
    if category:
        match = {c.lower(): c for c in ALL_CATEGORIES}.get(category.lower())
        if match is None:
            errors.append("category must be one of: " + ", ".join(ALL_CATEGORIES))
        category = match
    elif merchant:
        category = lookup_category(conn, merchant) or categorize(merchant)   # blank: merchants table, then knowledge base
    clean["category"] = category

    method = str(data.get("payment_method") or "").strip()
    if method:
        match = {m.lower(): m for m in PAYMENT_METHODS}.get(method.lower())
        if match is None:
            errors.append("payment_method must be one of: " + ", ".join(PAYMENT_METHODS))
        method = match
    clean["payment_method"] = method or "UPI"

    status = str(data.get("status") or "confirmed").strip()
    if status not in STATUSES:
        errors.append("status must be confirmed or pending_confirmation")
    clean["status"] = status

    note = str(data.get("note") or "").strip()
    clean["note"] = note[:200] or None
    return clean, errors


def get_transaction(conn, txn_id):
    row = conn.execute(f"SELECT {PUBLIC_COLUMNS} FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    return dict(row) if row else None


def add_transaction(conn, data, source="manual", planted_label=None, learn_merchant=True):
    """Validate and insert. Returns (transaction, errors)."""
    clean, errors = validate_transaction(conn, data)
    if errors:
        return None, errors
    cur = conn.execute(
        "INSERT INTO transactions (date, time, merchant, amount, category, payment_method, source,"
        " status, note, planted_label) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (clean["date"], clean["time"], clean["merchant"], clean["amount"], clean["category"],
         clean["payment_method"], source, clean["status"], clean["note"], planted_label))
    if learn_merchant:   # remember merchant -> category for later blank-category rows
        conn.execute("INSERT OR IGNORE INTO merchants (name, category) VALUES (?, ?)",
                     (clean["merchant"], clean["category"]))
    conn.commit()
    return get_transaction(conn, cur.lastrowid), []


def update_transaction(conn, txn_id, data):
    existing = get_transaction(conn, txn_id)
    if existing is None:
        return None, ["Transaction not found"]
    merged = {**existing, **{k: v for k, v in data.items() if k in EDITABLE}}
    clean, errors = validate_transaction(conn, merged)
    if errors:
        return None, errors
    conn.execute(
        "UPDATE transactions SET date=?, time=?, merchant=?, amount=?, category=?, payment_method=?,"
        " status=?, note=? WHERE id=?",
        (clean["date"], clean["time"], clean["merchant"], clean["amount"], clean["category"],
         clean["payment_method"], clean["status"], clean["note"], txn_id))
    conn.commit()
    return get_transaction(conn, txn_id), []


def delete_transaction(conn, txn_id):
    conn.execute("DELETE FROM agent_runs WHERE txn_id = ?", (txn_id,))
    cur = conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
    conn.commit()
    return cur.rowcount > 0


def list_transactions(conn, month=None, category=None, search=None):
    sql, params = f"SELECT {PUBLIC_COLUMNS} FROM transactions WHERE 1=1", []
    if month:
        sql += " AND substr(date, 1, 7) = ?"
        params.append(month)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if search:
        sql += " AND (merchant LIKE ? OR note LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    sql += " ORDER BY date DESC, time DESC, id DESC"
    return [dict(r) for r in conn.execute(sql, params)]


def list_months(conn):
    rows = conn.execute("SELECT DISTINCT substr(date, 1, 7) AS m FROM transactions ORDER BY m DESC")
    return [r["m"] for r in rows]


def month_summary(conn, month):
    """Placeholder dashboard numbers: total and per-category spend of confirmed transactions."""
    rows = conn.execute(
        "SELECT category, ROUND(SUM(amount), 2) AS total, COUNT(*) AS count FROM transactions"
        " WHERE status = 'confirmed' AND substr(date, 1, 7) = ? GROUP BY category ORDER BY total DESC",
        (month,)).fetchall()
    total = round(sum(r["total"] for r in rows), 2)
    count = sum(r["count"] for r in rows)
    return {"month": month, "total_spend": total, "transaction_count": count,
            "average_transaction": round(total / count, 2) if count else 0,
            "categories": [dict(r) for r in rows]}
