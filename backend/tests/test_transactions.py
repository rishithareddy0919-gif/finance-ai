import unittest

from helpers import GOOD, fresh_db
import transactions as tx


class CrudTests(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def test_add_returns_row_without_planted_label(self):
        row, errors = tx.add_transaction(self.conn, GOOD, planted_label="anomaly")
        self.assertEqual(errors, [])
        self.assertEqual(row["merchant"], "Swiggy")
        self.assertEqual(row["status"], "confirmed")           # default
        self.assertNotIn("planted_label", row)
        for listed in tx.list_transactions(self.conn):
            self.assertNotIn("planted_label", listed)

    def test_invalid_values_are_rejected_with_clear_messages(self):
        cases = {"date": "2026-02-31", "time": "25:00", "amount": "-5", "merchant": "   "}
        for field, bad in cases.items():
            row, errors = tx.add_transaction(self.conn, {**GOOD, field: bad})
            self.assertIsNone(row, field)
            self.assertTrue(any(field in e for e in errors), (field, errors))
        self.assertEqual(tx.list_transactions(self.conn), [])  # nothing saved

    def test_amount_zero_and_text_rejected(self):
        for bad in (0, "abc", None):
            _, errors = tx.add_transaction(self.conn, {**GOOD, "amount": bad})
            self.assertTrue(errors, bad)

    def test_blank_category_uses_merchants_table_then_other(self):
        tx.add_transaction(self.conn, GOOD)                     # teaches Swiggy -> Food
        row, _ = tx.add_transaction(self.conn, {**GOOD, "category": ""})
        self.assertEqual(row["category"], "Food")
        row, _ = tx.add_transaction(self.conn, {**GOOD, "merchant": "Unknown Shop", "category": ""})
        self.assertEqual(row["category"], "Other")

    def test_edit_and_delete(self):
        row, _ = tx.add_transaction(self.conn, GOOD)
        updated, errors = tx.update_transaction(self.conn, row["id"], {"amount": 300, "note": "dinner"})
        self.assertEqual((errors, updated["amount"], updated["note"]), ([], 300, "dinner"))
        _, errors = tx.update_transaction(self.conn, row["id"], {"time": "99:99"})
        self.assertTrue(errors)
        self.assertEqual(tx.get_transaction(self.conn, row["id"])["amount"], 300)   # unchanged after bad edit
        self.assertTrue(tx.delete_transaction(self.conn, row["id"]))
        self.assertFalse(tx.delete_transaction(self.conn, row["id"]))

    def test_filters_month_category_search(self):
        tx.add_transaction(self.conn, GOOD)
        tx.add_transaction(self.conn, {**GOOD, "date": "2026-08-02", "merchant": "Uber", "category": "Travel"})
        tx.add_transaction(self.conn, {**GOOD, "date": "2026-08-03", "note": "birthday treat"})
        self.assertEqual(len(tx.list_transactions(self.conn, month="2026-08")), 2)
        self.assertEqual(len(tx.list_transactions(self.conn, category="Travel")), 1)
        self.assertEqual(len(tx.list_transactions(self.conn, search="birthday")), 1)
        self.assertEqual(len(tx.list_transactions(self.conn, month="2026-08", category="Food")), 1)
        self.assertEqual(tx.list_months(self.conn), ["2026-09", "2026-08"])

    def test_month_summary(self):
        tx.add_transaction(self.conn, GOOD)                                              # 250 Food
        tx.add_transaction(self.conn, {**GOOD, "amount": 150})                           # 150 Food
        tx.add_transaction(self.conn, {**GOOD, "merchant": "Uber", "category": "Travel", "amount": 100})
        tx.add_transaction(self.conn, {**GOOD, "amount": 999, "status": "pending_confirmation"})  # not counted
        s = tx.month_summary(self.conn, "2026-09")
        self.assertEqual((s["total_spend"], s["transaction_count"]), (500, 3))
        self.assertEqual(s["categories"][0]["category"], "Food")
        self.assertEqual(s["categories"][0]["total"], 400)


if __name__ == "__main__":
    unittest.main()
