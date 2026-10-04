import unittest
from datetime import date

from helpers import fresh_db
import evaluate
import seed
import services
from errors import ApiError

TODAY = date(2026, 10, 3)


class EvaluateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = fresh_db()
        seed.reset_demo_data(cls.conn, TODAY)
        cls.report = evaluate.run_evaluation(cls.conn, TODAY)

    def test_every_anomaly_is_flagged_asked_or_listed_as_a_miss(self):
        for mode in self.report["modes"].values():
            for s in mode["threshold_sets"]:
                a = s["anomalies"]
                self.assertEqual(a["flagged"] + a["asked"] + a["missed"], a["total"], a["total"])
                self.assertEqual(len(s["misses"]), a["missed"])
                self.assertEqual(len(s["anomaly_rows"]), 9)
                self.assertEqual(len(s["tricky"]), 3)

    def test_confusion_matrix_adds_up(self):
        s = self.report["modes"]["confirmed_only"]["threshold_sets"][1]
        c = s["confusion_flag_only"]
        self.assertEqual(sum(c.values()), 214)
        self.assertEqual(c["true_positive"] + c["false_negative"], 9)
        self.assertEqual(len(s["false_alarms"]), c["false_positive"])

    def test_confirmed_only_profile_catches_most_anomalies(self):
        s = self.report["modes"]["confirmed_only"]["threshold_sets"][1]
        self.assertGreaterEqual(s["anomalies"]["flagged"] + s["anomalies"]["asked"], 8)
        self.assertEqual(s["normal"]["wrongly_flagged"], 0)

    def test_report_never_exposes_the_raw_label_and_has_the_synthetic_note(self):
        self.assertNotIn("planted_label", str(self.report))
        self.assertIn("synthetic", self.report["note"])


class ServicesTests(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()
        seed.reset_demo_data(self.conn, TODAY)
        self.good = {"date": "2026-10-03", "time": "13:00", "merchant": "Swiggy", "amount": 250, "category": "Food"}

    def test_analyze_rules_does_not_save(self):
        before = self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        r = services.analyze_rules(self.conn, self.good, TODAY)
        self.assertEqual([x["id"] for x in r["rules_fired"]], ["R6"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], before)
        with self.assertRaises(ApiError):
            services.analyze_rules(self.conn, {**self.good, "amount": -1}, TODAY)

    def test_analyze_bayes_both_input_styles(self):
        e = services.analyze_bayes(self.conn, {"evidence": {"AmountDeviation": "very_high", "NewMerchant": "yes"}})
        self.assertAlmostEqual(e["probability"], 0.776185, places=9)
        t = services.analyze_bayes(self.conn, {"transaction": {**self.good, "amount": 40000, "merchant": "Unknown Co", "time": "03:00"}}, TODAY)
        self.assertGreater(t["probability"], 0.85)
        with self.assertRaises(ApiError):
            services.analyze_bayes(self.conn, {"evidence": {"NewMerchant": "maybe"}})

    def test_dashboard_overview(self):
        import agent
        from gemini import GeminiError
        def off(*a, **k):
            raise GeminiError("x")
        agent.process(self.conn, {**self.good, "merchant": "QuickLoan247", "amount": 32000, "time": "03:20", "category": "Entertainment"},
                      today=TODAY, gemini_caller=off)
        o = services.dashboard_overview(self.conn, TODAY)
        self.assertEqual((o["unusual_count"], o["pending_count"]), (1, 0))
        self.assertEqual(len(o["recent_alerts"]), 1)
        self.assertEqual([t["month"] for t in o["trend"]], ["2026-07", "2026-08", "2026-09", "2026-10"])
        self.assertTrue(o["category_comparison"] and o["cumulative"] and o["projected"])


if __name__ == "__main__":
    unittest.main()
