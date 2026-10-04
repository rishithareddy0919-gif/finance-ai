import unittest

import bayes


class BayesTests(unittest.TestCase):
    def test_worked_example_by_hand(self):
        """Evidence: AmountDeviation = very_high, NewMerchant = yes. CategoryOverspend and UnusualTime are unknown.
        Priors: CategoryOverspend yes .15 / no .85 ; UnusualTime yes .07 / no .93
        CPT rows for (very_high, NewMerchant yes): (CO no, UT no) .75 ; (no, yes) .85 ; (yes, no) .88 ; (yes, yes) .95
        P = .85*.93*.75 + .85*.07*.85 + .15*.93*.88 + .15*.07*.95
          = 0.592875   + 0.050575    + 0.12276     + 0.009975
          = 0.776185   (shown as 0.7762 / 77.6%)"""
        self.assertAlmostEqual(bayes.infer({"AmountDeviation": "very_high", "NewMerchant": "yes"}), 0.776185, places=9)

    def test_all_normal_is_about_three_percent(self):
        e = {"AmountDeviation": "normal", "NewMerchant": "no", "CategoryOverspend": "no", "UnusualTime": "no"}
        self.assertAlmostEqual(bayes.infer(e), 0.03, places=9)

    def test_full_evidence_reads_the_cpt_row(self):
        e = {"AmountDeviation": "very_high", "NewMerchant": "yes", "CategoryOverspend": "yes", "UnusualTime": "no"}
        self.assertAlmostEqual(bayes.infer(e), 0.88, places=9)

    def test_no_evidence_marginalizes_to_a_valid_probability(self):
        self.assertTrue(0 < bayes.infer({}) < 0.2)
        self.assertEqual(bayes.infer({"NewMerchant": None}), bayes.infer({}))

    def test_explain_is_change_when_item_removed(self):
        e = {"AmountDeviation": "very_high", "NewMerchant": "yes"}
        # Removing NewMerchant leaves only very_high. Summing all 8 combinations of the other three variables
        # (weights .85*.85*.93 ... .15*.15*.07 times their CPT rows) gives P(very_high alone) = 0.52977425.
        # NewMerchant contribution = 0.776185 - 0.52977425 = 0.24641075
        got = {c["variable"]: c["contribution"] for c in bayes.explain(e)}
        self.assertAlmostEqual(bayes.infer({"AmountDeviation": "very_high"}), 0.52977425, places=9)
        self.assertAlmostEqual(got["NewMerchant"], 0.24641075, places=9)
        self.assertEqual(bayes.explain(e)[0]["variable"], "AmountDeviation")      # biggest contributor first

    def test_cpt_file_has_24_rows_and_structure(self):
        s = bayes.network_structure()
        self.assertEqual(len(s["cpt"]), 24)
        self.assertEqual(len(s["edges"]), 4)
        self.assertTrue(all(0 <= r["p"] <= 1 for r in s["cpt"]))
        self.assertGreaterEqual(bayes.infer({"AmountDeviation": "very_high", "NewMerchant": "yes", "CategoryOverspend": "yes"}), 0.85)

    def test_invalid_evidence_rejected(self):
        with self.assertRaises(ValueError):
            bayes.infer({"NewMerchant": "maybe"})
        with self.assertRaises(ValueError):
            bayes.infer({"Weather": "yes"})

    def test_evidence_from_facts_thresholds(self):
        f = lambda z: {"z_score": z, "is_new_merchant": True, "is_unusual_hour": False}
        self.assertEqual(bayes.evidence_from_facts(f(1.4), False)["AmountDeviation"], "normal")
        self.assertEqual(bayes.evidence_from_facts(f(1.5), False)["AmountDeviation"], "high")
        self.assertEqual(bayes.evidence_from_facts(f(3.0), False)["AmountDeviation"], "high")
        self.assertEqual(bayes.evidence_from_facts(f(3.01), True)["AmountDeviation"], "very_high")

    def test_feedback_update_uses_odds(self):
        # p=0.5 -> odds 1. 'me' ratio 0.2 -> odds 0.2 -> p = 0.2/1.2 = 0.1667 ; 'not_me' ratio 8 -> 8/9 = 0.8889
        r = {"me": 0.2, "not_me": 8.0}
        self.assertAlmostEqual(bayes.update_with_feedback(0.5, "me", r), 1 / 6)
        self.assertAlmostEqual(bayes.update_with_feedback(0.5, "not_me", r), 8 / 9)


if __name__ == "__main__":
    unittest.main()
