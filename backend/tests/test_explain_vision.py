import unittest

import explain
import vision
from gemini import GeminiError

PAYLOAD = explain.build_payload("Food", 6.24, [{"description": "Amount is more than 3 times the category average"}],
                                0.776, [{"variable": "NewMerchant", "state": "yes", "contribution": 0.246}])


class ExplainTests(unittest.TestCase):
    def test_payload_has_no_merchant_or_ids(self):
        self.assertEqual(set(PAYLOAD), {"category", "amount_ratio", "rules_fired", "probability_percent", "factors"})

    def test_good_gemini_text_is_used(self):
        text = "This Food payment is potentially unusual, about 78% likely. It is 6.2 times your average. Please check it."
        self.assertEqual(explain.explain(PAYLOAD, lambda p: text), (text, "gemini"))

    def test_invented_number_falls_back_to_template(self):
        out, source = explain.explain(PAYLOAD, lambda p: "This is potentially unusual, 91% likely. Check it.")
        self.assertEqual(source, "template")
        self.assertIn("78%", out)

    def test_fraud_word_and_failure_fall_back(self):
        self.assertEqual(explain.explain(PAYLOAD, lambda p: "Fraud detected at 78%.")[1], "template")
        def boom(p):
            raise GeminiError("down")
        self.assertEqual(explain.explain(PAYLOAD, boom)[1], "template")

    def test_template_numbers_all_come_from_the_payload(self):
        self.assertTrue(explain._numbers_allowed(explain.template_explanation(PAYLOAD), PAYLOAD))

    def test_prompt_does_not_contain_a_merchant(self):
        seen = []
        explain.explain(PAYLOAD, lambda p: seen.append(p) or "x")
        self.assertNotIn("Swiggy", seen[0])


GOOD = ('{"amount": {"value": "₹1,250.50", "confidence": "high"}, "currency": {"value": "INR", "confidence": "high"},'
        ' "date": {"value": "12 Sep 2026", "confidence": "medium"}, "time": {"value": "2:35 PM", "confidence": "high"},'
        ' "merchant_or_payee": {"value": "Ravi Kumar", "confidence": "low"}, "transaction_id": {"value": null, "confidence": "high"},'
        ' "payment_method": {"value": "Google Pay UPI", "confidence": "high"}, "location": {"value": null, "confidence": "low"}}')


class VisionTests(unittest.TestCase):
    def test_clean_good_response(self):
        r = vision.clean_extraction(GOOD)
        f = r["fields"]
        self.assertEqual((f["amount"]["value"], f["date"]["value"], f["time"]["value"]), (1250.5, "2026-09-12", "14:35"))
        self.assertEqual(f["payment_method"]["value"], "UPI")
        self.assertEqual(f["transaction_id"], {"value": None, "confidence": "low"})     # null is always low confidence
        self.assertTrue(r["needs_merchant_confirmation"])                                # merchant confidence is low

    def test_fenced_json_and_missing_fields(self):
        r = vision.clean_extraction('```json\n{"amount": {"value": 99, "confidence": "high"}}\n```')
        self.assertTrue(r["ok"])
        self.assertEqual(r["fields"]["amount"]["value"], 99)
        self.assertIsNone(r["fields"]["merchant_or_payee"]["value"])

    def test_malformed_and_nonsense_never_crash(self):
        for raw in ("not json at all", "", "[1, 2]", "null", '{"amount": 5'):
            r = vision.clean_extraction(raw)
            self.assertFalse(r["ok"])
            self.assertTrue(r["needs_merchant_confirmation"])
            self.assertEqual(set(r["fields"]), set(vision.FIELDS))

    def test_bad_values_become_null_with_warning(self):
        r = vision.clean_extraction('{"amount": {"value": "free", "confidence": "high"}, "date": {"value": "yesterday", "confidence": "high"},'
                                    ' "time": {"value": "25:99", "confidence": "high"}, "merchant_or_payee": {"value": "Cafe", "confidence": "banana"}}')
        self.assertIsNone(r["fields"]["amount"]["value"])
        self.assertIsNone(r["fields"]["date"]["value"])
        self.assertIsNone(r["fields"]["time"]["value"])
        self.assertEqual(len(r["warnings"]), 3)
        self.assertEqual(r["fields"]["merchant_or_payee"]["confidence"], "low")     # invalid confidence -> low

    def test_gemini_failure_still_returns_a_form(self):
        def boom(*a, **k):
            raise GeminiError("no key")
        r = vision.extract(b"\x89PNG", "image/png", boom)
        self.assertFalse(r["ok"])
        self.assertIn("no key", r["error"])
        self.assertTrue(r["needs_merchant_confirmation"])


if __name__ == "__main__":
    unittest.main()
