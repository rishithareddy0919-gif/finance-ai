import unittest
from datetime import date

from helpers import fresh_db
import agent
import transactions as tx
from errors import ApiError
from gemini import GeminiError

TODAY = date(2026, 10, 15)


def no_gemini(*a, **k):
    raise GeminiError("offline in tests")


def history_db():
    """Hand-made history: 12 Food payments a month (Jul, Aug, Sep) at Swiggy/Zomato, amounts 100-140, hours 12-14."""
    conn = fresh_db()
    for month in (7, 8, 9):
        for i in range(12):
            tx.add_transaction(conn, {"date": f"2026-{month:02d}-{i + 1:02d}", "time": f"{12 + i % 3}:15",
                                      "merchant": ["Swiggy", "Zomato"][i % 2], "amount": 100 + (i % 5) * 10, "category": "Food"})
    return conn


def run(conn, merchant, amount, time, date_="2026-10-15"):
    return agent.process(conn, {"date": date_, "time": time, "merchant": merchant, "amount": amount, "category": "Food"},
                         today=TODAY, gemini_caller=no_gemini)


class AgentTests(unittest.TestCase):
    def test_easy_case_uses_few_tools_and_stops(self):
        r = run(history_db(), "Swiggy", 120, "13:00")
        self.assertEqual([s["tool"] for s in r["steps"]], ["get_transaction_history", "get_category_statistics", "log_transaction"])
        self.assertEqual((r["outcome"], r["risk_level"], r["status"]), ("logged_routine", "Low", "confirmed"))
        self.assertIsNone(r["probability"])
        self.assertTrue(all(s["why"] for s in r["steps"]))

    def test_hard_case_uses_all_tools_and_flags(self):
        r = run(history_db(), "ShadyStore", 9000, "03:00")
        tools = [s["tool"] for s in r["steps"]]
        self.assertEqual(tools, ["get_transaction_history", "get_category_statistics", "check_risk_rules", "predict_month_end",
                                 "run_bayesian_analysis", "generate_explanation", "log_transaction"])
        self.assertEqual((r["outcome"], r["risk_level"], r["status"]), ("flagged", "High", "pending_confirmation"))
        self.assertGreater(r["probability"], 0.7)
        self.assertEqual(r["explanation_source"], "template")              # Gemini was offline
        self.assertIn("potentially unusual", r["explanation"])
        self.assertTrue(r["recommendations"])
        self.assertNotIn("fraud", r["explanation"].lower())

    def test_uncertain_case_asks_the_user_and_updates(self):
        conn = history_db()
        r = run(conn, "Swiggy", 900, "13:00")                  # known merchant, usual hour, but a very high amount
        self.assertEqual([s["tool"] for s in r["steps"]][-2:], ["ask_user", "log_transaction"])
        self.assertEqual((r["outcome"], r["status"]), ("awaiting_user", "pending_confirmation"))
        self.assertIn("Was this transaction made by you?", r["question"])
        self.assertTrue(0.4 <= r["probability"] < 0.7)
        base = r["probability"]
        me = agent.answer(conn, r["txn_id"], "me")
        self.assertEqual((me["outcome"], me["status"], me["user_feedback"]), ("logged_user_confirmed", "confirmed", "me"))
        self.assertLess(me["probability"], base)
        self.assertIsNone(me["question"])
        not_me = agent.answer(conn, r["txn_id"], "not_me")                  # changing the answer starts from the original probability
        self.assertEqual((not_me["outcome"], not_me["status"]), ("flagged", "pending_confirmation"))
        self.assertGreater(not_me["probability"], 0.7)
        self.assertTrue(not_me["explanation"] and not_me["recommendations"])

    def test_pending_and_flagged_rows_do_not_change_the_profile(self):
        conn = history_db()
        run(conn, "ShadyStore", 9000, "03:00")
        from profile import build_profile
        self.assertEqual(build_profile(conn, TODAY)["categories"]["Food"]["count"], 36)

    def test_thresholds_come_from_config(self):
        cfg = {"thresholds": {"low": 0.01, "high": 0.99}, "feedback_likelihood_ratio": {"me": 0.2, "not_me": 8}}
        r = agent.process(history_db(), {"date": "2026-10-15", "time": "13:00", "merchant": "Swiggy", "amount": 900,
                                         "category": "Food"}, today=TODAY, config=cfg, gemini_caller=no_gemini)
        self.assertEqual(r["outcome"], "awaiting_user")
        cfg["thresholds"]["low"] = 0.9                      # now 0.6 is "below low": log as normal
        r = agent.process(history_db(), {"date": "2026-10-15", "time": "13:00", "merchant": "Swiggy", "amount": 900,
                                         "category": "Food"}, today=TODAY, config=cfg, gemini_caller=no_gemini)
        self.assertEqual(r["outcome"], "logged_normal")

    def test_validation_and_run_lookup_errors(self):
        conn = history_db()
        with self.assertRaises(ApiError):
            agent.process(conn, {"date": "bad", "time": "13:00", "merchant": "X", "amount": 5})
        with self.assertRaises(ApiError):
            agent.run_view(conn, 999)
        with self.assertRaises(ApiError):
            agent.answer(conn, 1, "maybe")

    def test_trace_saved_and_listed_in_agent_runs(self):
        conn = history_db()
        r = run(conn, "Swiggy", 120, "13:00")
        row = conn.execute("SELECT * FROM agent_runs WHERE txn_id = ?", (r["txn_id"],)).fetchone()
        self.assertEqual((row["outcome"], row["risk_level"]), ("logged_routine", "Low"))
        self.assertEqual(agent.run_view(conn, r["txn_id"])["steps"], r["steps"])


if __name__ == "__main__":
    unittest.main()
