import unittest

import rules

# Hand-written profile: Food mean 100, std 20 -> normal range 70..130; monthly average 1000; typical hours 12-14.
PROFILE = {"typical_hours": [12, 13, 14], "overall": {"mean": 100, "std": 20},
           "categories": {"Food": {"low_confidence": False, "mean": 100, "std": 20, "monthly_average": 1000,
                                   "normal_low": 70, "normal_high": 130},
                          "Bills": {"low_confidence": True, "count": 2}}}
CONTEXT = {"prior_merchant_count": 5, "same_merchant_count_today": 1, "month_to_date_category": 0}


def ev(amount=100, hour="13:00", category="Food", **ctx):
    txn = {"amount": amount, "time": hour, "category": category}
    return rules.evaluate(txn, PROFILE, {**CONTEXT, **ctx})


def fired(result):
    return [r["id"] for r in result["rules_fired"]]


class RuleTests(unittest.TestCase):
    def test_r1_amount_over_three_times_mean(self):
        self.assertIn("R1", fired(ev(amount=301)))       # 301/100 = 3.01
        self.assertNotIn("R1", fired(ev(amount=300)))     # exactly 3 is not "more than"

    def test_r2_new_merchant_and_above_range(self):
        self.assertIn("R2", fired(ev(amount=131, prior_merchant_count=0)))
        self.assertNotIn("R2", fired(ev(amount=131, prior_merchant_count=5)))     # known merchant
        self.assertNotIn("R2", fired(ev(amount=120, prior_merchant_count=0)))     # inside range

    def test_r3_category_overspending(self):
        self.assertIn("R3", fired(ev(amount=100, month_to_date_category=1450)))   # (1450+100)/1000 = 1.55
        self.assertNotIn("R3", fired(ev(amount=100, month_to_date_category=1300)))  # 1.4

    def test_r4_unusual_hour(self):
        self.assertIn("R4", fired(ev(hour="03:10")))
        self.assertNotIn("R4", fired(ev(hour="14:59")))

    def test_r5_repeated_new_merchant(self):
        self.assertIn("R5", fired(ev(prior_merchant_count=0, same_merchant_count_today=3)))
        self.assertNotIn("R5", fired(ev(prior_merchant_count=0, same_merchant_count_today=2)))
        self.assertNotIn("R5", fired(ev(prior_merchant_count=9, same_merchant_count_today=3)))   # not new

    def test_r6_routine_only(self):
        r = ev(amount=100)
        self.assertEqual(fired(r), ["R6"])
        self.assertEqual(r["level"], "Low")
        self.assertNotIn("R6", fired(ev(amount=100, prior_merchant_count=1)))     # seen once = still new

    def test_levels_and_forward_chaining(self):
        r = ev(amount=900, hour="03:00", prior_merchant_count=0, month_to_date_category=2000)
        self.assertEqual(fired(r), ["R1", "R2", "R3", "R4"])
        self.assertEqual((r["score"], r["level"]), (6, "High"))
        self.assertEqual(r["conclusions"], ["amount_anomaly", "new_merchant_high_amount", "overspending", "unusual_time"])
        self.assertEqual(ev(hour="03:00")["level"], "Medium")         # R4 alone: score 1

    def test_rules_are_data_and_engine_chains(self):
        chain = [{"id": "A", "description": "a", "conditions": [{"fact": "x", "op": ">", "value": 1}], "conclusion": "big", "weight": 0},
                 {"id": "B", "description": "b", "conditions": [{"fact": "big", "op": "==", "value": True}], "conclusion": "huge", "weight": 1}]
        out, _ = rules.run_engine({"x": 5}, list(reversed(chain)))        # order does not matter: B fires after A
        self.assertEqual(sorted(r["id"] for r in out), ["A", "B"])

    def test_low_confidence_category_falls_back_to_overall(self):
        r = ev(amount=100, category="Bills")
        self.assertEqual(r["facts"]["stats_source"], "overall")


if __name__ == "__main__":
    unittest.main()
