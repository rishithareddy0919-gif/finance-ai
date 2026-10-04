import statistics
import unittest
from datetime import date

from helpers import fresh_db
from seed import reset_demo_data
import transactions as tx

TODAY = date(2026, 10, 3)


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()
        reset_demo_data(self.conn, TODAY)

    def labels(self):
        return [r[0] for r in self.conn.execute("SELECT planted_label FROM transactions")]

    def test_total_count_and_planted_counts(self):
        n = len(self.labels())
        self.assertTrue(200 <= n <= 250, n)
        self.assertEqual(self.labels().count("anomaly"), 9)           # 8 to 10 odd ones
        self.assertEqual(self.labels().count("tricky_legit"), 3)

    def test_all_six_categories_and_regular_merchants_present(self):
        cats = {r[0] for r in self.conn.execute("SELECT DISTINCT category FROM transactions")}
        self.assertTrue({"Food", "Travel", "Shopping", "Bills", "Entertainment", "Education"} <= cats)
        names = {r[0] for r in self.conn.execute("SELECT DISTINCT merchant FROM transactions")}
        for m in ("Swiggy", "Zomato", "Uber", "Amazon", "Jio", "College Canteen", "Hostel Mess"):
            self.assertIn(m, names)

    def test_normal_rows_are_small_and_in_normal_hours(self):
        rows = self.conn.execute(
            "SELECT amount, time FROM transactions WHERE planted_label IS NULL").fetchall()
        amounts = [r["amount"] for r in rows]
        self.assertLess(statistics.median(amounts), 300)
        self.assertLessEqual(max(amounts), 1800)
        self.assertTrue(all(8 <= int(r["time"][:2]) <= 22 for r in rows))

    def test_planted_rows_are_odd(self):
        night = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE planted_label='anomaly' AND CAST(substr(time,1,2) AS INT) < 6"
        ).fetchone()[0]
        self.assertGreaterEqual(night, 5)
        big = self.conn.execute("SELECT MIN(amount) FROM transactions WHERE planted_label='tricky_legit'").fetchone()[0]
        self.assertGreaterEqual(big, 7800)

    def test_three_full_months_plus_current(self):
        self.assertEqual(tx.list_months(self.conn), ["2026-10", "2026-09", "2026-08", "2026-07"])
        self.assertTrue(all(r["date"] <= "2026-10-03" for r in tx.list_transactions(self.conn)))

    def test_reset_is_repeatable_and_planted_label_hidden(self):
        before = len(self.labels())
        self.assertEqual(reset_demo_data(self.conn, TODAY), before)    # same data again, no duplicates
        self.assertTrue(all("planted_label" not in r for r in tx.list_transactions(self.conn)))

    def test_planted_anomalies_wait_for_review_and_tricky_ones_are_confirmed(self):
        rows = self.conn.execute("SELECT planted_label AS l, status AS s FROM transactions WHERE planted_label IS NOT NULL").fetchall()
        self.assertTrue(all(r["s"] == "pending_confirmation" for r in rows if r["l"] == "anomaly"))
        self.assertTrue(all(r["s"] == "confirmed" for r in rows if r["l"] == "tricky_legit"))

    def test_unusual_merchants_are_not_in_known_merchants_table(self):
        known = {r[0] for r in self.conn.execute("SELECT name FROM merchants")}
        self.assertNotIn("FastBet247", known)
        self.assertIn("Swiggy", known)


if __name__ == "__main__":
    unittest.main()
