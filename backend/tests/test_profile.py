import math
import unittest
from datetime import date

from helpers import fresh_db
import profile as P
import transactions as tx
from knowledge_base import categorize, categorize_with_reason

# Hand-made data. Today = 2026-10-10, so Aug and Sep are complete months and Oct is the current one.
ROWS = [
    ("2026-08-03", "10:00", "Swiggy", 100, "Food"), ("2026-08-04", "10:30", "Swiggy", 100, "Food"),
    ("2026-08-05", "09:00", "Uber", 50, "Travel"), ("2026-08-06", "09:30", "Uber", 50, "Travel"),
    ("2026-09-03", "10:00", "Swiggy", 100, "Food"), ("2026-09-04", "10:15", "Swiggy", 100, "Food"),
    ("2026-09-05", "11:00", "Uber", 80, "Travel"), ("2026-10-02", "22:00", "Zomato", 200, "Food"),
]
ROWS = [dict(zip(("date", "time", "merchant", "amount", "category"), r)) for r in ROWS]
TODAY = date(2026, 10, 10)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.p = P.profile_from_rows(ROWS, TODAY)

    def test_monthly_totals(self):      # Aug 100+100+50+50, Sep 100+100+80, Oct 200
        self.assertEqual(self.p["monthly_totals"], {"2026-08": 300, "2026-09": 280, "2026-10": 200})

    def test_category_statistics_for_food(self):
        food = self.p["categories"]["Food"]
        # amounts 100,100,100,100,200: mean = 600/5 = 120. Distances: four of -20 and one of +80.
        # variance = (4*20^2 + 80^2)/5 = (1600 + 6400)/5 = 1600, so std = 40.
        self.assertEqual((food["count"], food["mean"], food["std"]), (5, 120, 40))
        self.assertEqual((food["normal_low"], food["normal_high"]), (60, 180))        # 120 -/+ 1.5*40
        # monthly average over COMPLETE months: Aug 200, Sep 200 -> 200. Current month Oct = 200 -> ratio 1.0
        self.assertEqual((food["monthly_average"], food["current_month_spend"], food["current_vs_average_ratio"]), (200, 200, 1.0))
        self.assertEqual(food["top_merchants"][0], {"merchant": "Swiggy", "count": 4})

    def test_normal_range_floored_at_zero(self):
        rows = [{"date": "2026-09-01", "time": "10:00", "merchant": "A", "amount": a, "category": "Food"} for a in (10, 10, 10, 10, 500)]
        self.assertEqual(P.profile_from_rows(rows, TODAY)["categories"]["Food"]["normal_low"], 0)

    def test_low_confidence_below_five_transactions(self):
        travel = self.p["categories"]["Travel"]
        self.assertTrue(travel["low_confidence"])
        self.assertNotIn("mean", travel)
        self.assertEqual(P.category_profile(self.p, "Bills")["count"], 0)

    def test_overall_statistics(self):    # 8 amounts, mean 97.5, variance 15350/8 = 1918.75
        self.assertEqual(self.p["overall"]["mean"], 97.5)
        self.assertAlmostEqual(self.p["overall"]["std"], round(math.sqrt(1918.75), 2))

    def test_known_merchants_seen_twice(self):
        self.assertEqual(self.p["known_merchants"], ["Swiggy", "Uber"])      # Zomato seen once

    def test_typical_hours_hold_95_percent(self):
        # 12:50, 13:45, 3:5 of 100. 12 holds 50%, adding 13 reaches 95%, so hour 3 is NOT typical.
        self.assertEqual(P.typical_hours({12: 50, 13: 45, 3: 5}), [12, 13])
        self.assertEqual(self.p["typical_hours"], [9, 10, 11, 22])

    def test_database_profile_ignores_pending_and_supports_leave_one_out(self):
        conn = fresh_db()
        for r in ROWS:
            tx.add_transaction(conn, {**r, "payment_method": "UPI"})
        tx.add_transaction(conn, {"date": "2026-09-09", "time": "03:00", "merchant": "X", "amount": 9999,
                                  "category": "Food", "status": "pending_confirmation"})
        self.assertEqual(P.build_profile(conn, TODAY)["categories"]["Food"]["count"], 5)
        self.assertEqual(P.build_profile(conn, TODAY, include_pending=True)["categories"]["Food"]["count"], 6)
        first = conn.execute("SELECT id FROM transactions ORDER BY id LIMIT 1").fetchone()[0]
        self.assertEqual(P.build_profile(conn, TODAY, exclude_id=first)["categories"]["Food"]["count"], 4)


class KnowledgeBaseTests(unittest.TestCase):
    def test_categorize(self):
        for name, cat in [("Swiggy", "Food"), ("ZOMATO", "Food"), ("Uber", "Travel"), ("IRCTC", "Travel"),
                          ("Flipkart", "Shopping"), ("Jio", "Bills")]:
            self.assertEqual(categorize(name), cat)
        self.assertEqual(categorize_with_reason("Sharma Biryani House")[0], "Food")
        self.assertEqual(categorize_with_reason("City Broadband")[1], "keyword:broadband")
        self.assertEqual(categorize_with_reason("Xyzzy Corp"), ("Other", "fallback"))


if __name__ == "__main__":
    unittest.main()
