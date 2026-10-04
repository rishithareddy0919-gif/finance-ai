import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_conn, init_db  # noqa: E402


def fresh_db():
    conn = get_conn(":memory:")
    init_db(conn)
    return conn


GOOD = {"date": "2026-09-10", "time": "13:30", "merchant": "Swiggy", "amount": 250,
        "category": "Food", "payment_method": "UPI"}
