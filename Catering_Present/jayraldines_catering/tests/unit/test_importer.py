"""
Unit tests for utils/importer.py Data Importer Engine.
"""
import os
import tempfile
import unittest
import utils.importer as importer


class TestImporter(unittest.TestCase):

    def test_auto_map_headers_customers(self):
        headers = ["Client Name", "Phone Number", "Email Address", "Home Address", "Notes"]
        mapping = importer.auto_map_headers(headers, "customers")
        self.assertEqual(mapping["name"], "Client Name")
        self.assertEqual(mapping["contact"], "Phone Number")
        self.assertEqual(mapping["email"], "Email Address")
        self.assertEqual(mapping["address"], "Home Address")
        self.assertEqual(mapping["notes"], "Notes")

    def test_auto_map_headers_expenses(self):
        headers = ["Fecha", "Expense Type", "Particulars", "Cost (PHP)"]
        mapping = importer.auto_map_headers(headers, "expenses")
        self.assertEqual(mapping["date"], "Fecha")
        self.assertEqual(mapping["category"], "Expense Type")
        self.assertEqual(mapping["description"], "Particulars")
        self.assertEqual(mapping["amount"], "Cost (PHP)")

    def test_normalize_amount(self):
        self.assertEqual(importer.normalize_amount("₱ 15,500.50"), 15500.50)
        self.assertEqual(importer.normalize_amount("$2,400.00"), 2400.00)
        self.assertEqual(importer.normalize_amount("1500"), 1500.0)
        self.assertEqual(importer.normalize_amount("invalid"), 0.0)

    def test_normalize_date(self):
        self.assertEqual(importer.normalize_date("2026-08-16"), "Aug 16, 2026")
        self.assertEqual(importer.normalize_date("08/16/2026"), "Aug 16, 2026")

    def test_validate_and_prepare_rows_expenses(self):
        rows = [
            {"Expense Date": "2026-08-16", "Category": "Food Cost", "Particulars": "Spices", "Cost": "₱1,500.00"},
            {"Expense Date": "2026-08-16", "Category": "", "Particulars": "Missing Category", "Cost": "500.00"},
        ]
        mapping = {"date": "Expense Date", "category": "Category", "description": "Particulars", "amount": "Cost"}
        prepared, counts = importer.validate_and_prepare_rows(rows, mapping, "expenses")

        self.assertEqual(len(prepared), 2)
        self.assertEqual(counts["valid"], 1)
        self.assertEqual(counts["error"], 1)
        self.assertEqual(prepared[0]["_status"], "valid")
        self.assertEqual(prepared[1]["_status"], "error")

    def test_generate_sample_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_path = os.path.join(tmpdir, "sample_customers.csv")
            err = importer.generate_sample_csv("customers", sample_path)
            self.assertIsNone(err)
            self.assertTrue(os.path.exists(sample_path))
            headers, data, parse_err = importer.parse_file(sample_path)
            self.assertIsNone(parse_err)
            self.assertGreaterEqual(len(headers), 4)
            self.assertGreaterEqual(len(data), 2)

    def test_parse_master_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_path = os.path.join(tmpdir, "master_file.csv")
            err = importer.generate_sample_csv("all_in_one", sample_path)
            self.assertIsNone(err)
            master_dict, parse_err = importer.parse_master_file(sample_path)
            self.assertIsNone(parse_err)
            self.assertIn("customers", master_dict)


if __name__ == "__main__":
    unittest.main()
