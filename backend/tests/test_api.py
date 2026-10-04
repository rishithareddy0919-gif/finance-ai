"""API-level tests. Skipped automatically if FastAPI is not installed."""
import os
import tempfile
import unittest

from helpers import GOOD  # noqa: F401  (also puts backend/ on sys.path)

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi not installed")
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["FINANCE_DB"] = os.path.join(self.tmp, "t.db")
        import importlib
        import db, main
        importlib.reload(db)
        importlib.reload(main)
        self.client = TestClient(main.app)
        self.client.__enter__()                                  # runs the startup event

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_reset_then_no_planted_label_in_any_response(self):
        self.assertEqual(self.client.post("/api/demo/reset").status_code, 200)
        rows = self.client.get("/api/transactions").json()
        self.assertGreater(len(rows), 150)
        self.assertNotIn("planted_label", rows[0])
        self.assertNotIn("planted_label", self.client.get("/api/transactions?search=Swiggy").text)

    def test_add_edit_delete_and_validation(self):
        created = self.client.post("/api/transactions", json=GOOD)
        self.assertEqual(created.status_code, 201)
        tid = created.json()["id"]
        self.assertEqual(self.client.put(f"/api/transactions/{tid}", json={"amount": 99}).json()["amount"], 99)
        self.assertEqual(self.client.post("/api/transactions", json={**GOOD, "time": "27:00"}).status_code, 422)
        self.assertEqual(self.client.delete(f"/api/transactions/{tid}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/transactions/{tid}").status_code, 404)

    def test_ai_endpoints_and_hidden_label(self):
        self.client.post("/api/demo/reset")
        self.assertIn("categories", self.client.get("/api/profile").json())
        self.assertEqual(len(self.client.get("/api/rules").json()), 6)
        self.assertEqual(len(self.client.get("/api/bayes/structure").json()["cpt"]), 24)
        r = self.client.post("/api/analyze/bayes", json={"evidence": {"AmountDeviation": "very_high", "NewMerchant": "yes"}}).json()
        self.assertAlmostEqual(r["probability"], 0.776185, places=6)
        run = self.client.post("/api/agent/process", json={**GOOD, "merchant": "QuickLoan247", "amount": 32000, "time": "03:20", "category": "Entertainment"}).json()
        self.assertEqual(run["outcome"], "flagged")
        self.assertEqual(self.client.get(f"/api/agent/runs/{run['txn_id']}").status_code, 200)
        self.assertEqual(self.client.post("/api/agent/answer", json={"txn_id": run["txn_id"], "answer": "me"}).json()["outcome"], "logged_user_confirmed")
        self.assertEqual(self.client.get("/api/agent/runs/99999").status_code, 404)
        self.assertEqual(self.client.post("/api/extract", files={"file": ("x.gif", b"GIF89a", "image/gif")}).status_code, 415)
        for path in ("/api/prediction", "/api/evaluation", "/api/dashboard/overview"):
            text = self.client.get(path).text
            self.assertNotIn("planted_label", text)

    def test_csv_upload_reports_bad_rows(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data", "sample_with_errors.csv")
        with open(path, "rb") as f:
            report = self.client.post("/api/transactions/import", files={"file": ("s.csv", f, "text/csv")}).json()
        self.assertEqual((report["imported"], report["rejected"]), (3, 4))


if __name__ == "__main__":
    unittest.main()
