import math
import unittest
from datetime import date

import prediction as pr


class PredictionTests(unittest.TestCase):
    def test_run_rate(self):                 # 5000 spent in 10 days of a 30-day month -> 500/day -> 15000
        self.assertEqual(pr.run_rate(5000, 10, 30), 15000)

    def test_least_squares_and_regression(self):
        slope, intercept = pr.least_squares([0, 1, 2], [100, 200, 300])
        self.assertAlmostEqual(slope, 100)
        self.assertAlmostEqual(intercept, 100)
        self.assertAlmostEqual(pr.regression_forecast([100, 200, 300]), 400)     # next point x=3
        self.assertIsNone(pr.regression_forecast([100]))

    def test_status_and_pct_difference(self):
        # history 100,200,300: average 200, population std sqrt(20000/3) = 81.65 -> range 118.35..281.65
        p = pr.predict_series("t", [100, 200, 300], 400, 10, 10, 3)            # 10 of 10 days: run rate = 400
        self.assertEqual(p["status"], "well above usual")                       # 400 > 200 + 2*81.65 = 363.3
        self.assertEqual(p["pct_diff_vs_average"], 100.0)
        self.assertEqual((p["normal_low"], p["normal_high"]), (118.35, 281.65))
        self.assertEqual(pr.predict_series("t", [100, 200, 300], 250, 10, 10, 3)["status"], "on track")
        self.assertEqual(pr.predict_series("t", [100, 200, 300], 300, 10, 10, 3)["status"], "above usual")

    def test_low_confidence_messages(self):
        a = pr.predict_series("t", [100, 200, 300], 100, 3, 30, 3)
        self.assertTrue(a["low_confidence"])
        self.assertIn("3 day(s)", a["message"])
        b = pr.predict_series("t", [100, 200], 100, 10, 30, 2)
        self.assertTrue(b["low_confidence"])
        self.assertIn("2 completed month(s)", b["message"])
        self.assertFalse(pr.predict_series("t", [100, 200, 300], 100, 5, 30, 3)["low_confidence"])

    def test_predict_from_profile_with_extra_amount(self):
        profile = {"monthly_totals": {"2026-07": 100, "2026-08": 200, "2026-09": 300, "2026-10": 500},
                   "category_monthly_totals": {"Food": {"2026-07": 10, "2026-08": 20, "2026-09": 30, "2026-10": 50}},
                   "complete_months": ["2026-07", "2026-08", "2026-09"], "current_month": "2026-10"}
        p = pr.predict_from_profile(profile, date(2026, 10, 10))              # 500 / 10 * 31 = 1550
        self.assertEqual(p["run_rate_prediction"], 1550)
        c = pr.predict_from_profile(profile, date(2026, 10, 10), "Food", extra=50)    # (50+50)/10*31 = 310
        self.assertEqual(c["run_rate_prediction"], 310)


if __name__ == "__main__":
    unittest.main()
