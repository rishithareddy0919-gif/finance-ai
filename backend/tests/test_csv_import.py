import os
import unittest

from helpers import fresh_db
import transactions as tx
from csv_import import import_csv

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data", "sample_with_errors.csv")


class CsvTests(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def test_bad_rows_reported_and_good_rows_still_saved(self):
        with open(SAMPLE, "rb") as f:
            report = import_csv(self.conn, f.read())
        self.assertEqual((report["total_rows"], report["imported"], report["rejected"]), (7, 3, 4))
        self.assertEqual([e["row"] for e in report["errors"]], [4, 5, 6, 7])    # file line numbers
        joined = " | ".join(m for e in report["errors"] for m in e["messages"])
        for expected in ("not a real calendar date", "24-hour", "greater than 0", "merchant is required"):
            self.assertIn(expected, joined)
        saved = tx.list_transactions(self.conn)
        self.assertEqual(len(saved), 3)
        self.assertTrue(all(r["source"] == "csv" for r in saved))

    def test_missing_required_header_saves_nothing(self):
        report = import_csv(self.conn, "date,merchant,amount\n2026-09-01,Swiggy,100\n")
        self.assertEqual(report["missing_headers"], ["time"])
        self.assertEqual(tx.list_transactions(self.conn), [])

    def test_headers_are_case_insensitive_and_bom_is_ignored(self):
        data = "\ufeffDate,Time,Merchant,Amount\n2026-09-01,08:05,Canteen,45\n\n".encode("utf-8")
        report = import_csv(self.conn, data)
        self.assertEqual((report["imported"], report["rejected"]), (1, 0))

    def test_empty_file(self):
        self.assertEqual(len(import_csv(self.conn, "")["missing_headers"]), 4)


if __name__ == "__main__":
    unittest.main()
