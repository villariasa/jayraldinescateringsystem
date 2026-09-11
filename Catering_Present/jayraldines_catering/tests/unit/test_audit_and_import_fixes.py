"""
Unit tests verifying fixes for:
1. Cash flow import deduplication (preventing repeat entries).
2. Billing / Booking import status & amount paid retention (Paid/Partial instead of Pending/Unpaid).
3. Confirm booking dialog fixed footer & scrollable content layout for laptop screens.
"""
import os
import sys
import unittest
from datetime import date, datetime

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
import utils.repository as repo
import utils.importer as importer
from components.confirm_booking_dialog import ConfirmBookingDialog, BatchConfirmBookingDialog

# Ensure QApplication instance exists for GUI tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestAuditAndImportFixes(unittest.TestCase):

    def setUp(self):
        self.test_prefix = f"Test_{int(datetime.now().timestamp() * 1000)}"

    def test_cash_flow_deduplication_in_repository(self):
        """Verify repo.find_duplicate_cash_flow correctly detects existing transactions."""
        t_date = date.today().isoformat()
        particulars = f"Supplier Payment {self.test_prefix}"
        withdrawal = 4500.0
        deposit = 0.0
        check_no = f"CHK-{self.test_prefix}"

        # 1. Initially should not find any duplicate
        dup = repo.find_duplicate_cash_flow(t_date, particulars, deposit, withdrawal, 0.0, check_no)
        self.assertIsNone(dup)

        # 2. Add cash flow transaction
        cf_id = repo.add_cash_flow_transaction({
            "date": t_date,
            "particulars": particulars,
            "withdrawal": withdrawal,
            "deposit": deposit,
            "actual_sales": 0.0,
            "check_no": check_no,
            "source": "manual",
        })
        self.assertTrue(cf_id)

        # 3. Now duplicate should be detected by check_no + date
        dup = repo.find_duplicate_cash_flow(t_date, "Any particulars", deposit, withdrawal, 0.0, check_no)
        self.assertIsNotNone(dup)
        self.assertGreater(dup["cft_id"], 0)

        # 4. Duplicate should also be detected by date + particulars + amount even without check_no
        dup2 = repo.find_duplicate_cash_flow(t_date, particulars, deposit, withdrawal, 0.0, "")
        self.assertIsNotNone(dup2)
        self.assertEqual(dup2["cft_id"], dup["cft_id"])

    def test_cash_flow_deduplication_in_batch_import(self):
        """Verify execute_batch_import skips already imported cash flow rows."""
        t_date = date.today().isoformat()
        particulars = f"Catering Supplies {self.test_prefix}"
        rows = [
            {
                "date": t_date,
                "particulars": particulars,
                "withdrawal": 3200.0,
                "deposit": 0.0,
                "actual_sales": 0.0,
                "check_no": f"CK-{self.test_prefix}",
                "_status": "valid",
            }
        ]

        # First import: should insert 1 row
        inserted1, failed1, errs1 = importer.execute_batch_import(rows, "cash_flow")
        self.assertEqual(inserted1, 1)

        # Second import with identical data: should be skipped, not duplicated
        inserted2, failed2, errs2 = importer.execute_batch_import(rows, "cash_flow")
        self.assertEqual(inserted2, 0)
        self.assertTrue(any("Already exists in database, skipped duplicate" in e for e in errs2))

    def test_billing_schema_and_header_aliases(self):
        """Verify billing entity schema and alias mappings for payment status and amount paid."""
        self.assertEqual(importer.normalize_entity_type("billing"), "billings")
        self.assertEqual(importer.normalize_entity_type("billings"), "billings")
        self.assertEqual(importer.normalize_entity_type("invoice"), "billings")
        self.assertEqual(importer.normalize_entity_type("invoices"), "billings")

        headers = ["Client Name", "Event Date", "Total Cost", "Paid Amount", "Balance Due", "Payment Status"]
        mapping = importer.auto_map_headers(headers, "billings")
        self.assertEqual(mapping.get("customer_name"), "Client Name")
        self.assertEqual(mapping.get("total_amount"), "Total Cost")
        self.assertEqual(mapping.get("amount_paid"), "Paid Amount")
        self.assertEqual(mapping.get("status"), "Payment Status")

    def test_billing_import_status_and_paid_retention(self):
        """Verify importing billings or bookings retains Partial/Paid status and amount_paid."""
        cust_name = f"Client_{self.test_prefix}"
        unique_contact = f"09{int(datetime.now().timestamp() * 1000) % 1000000000:09d}"
        evt_date = date.today().isoformat()

        # Import a booking with 50% down payment
        rows = [
            {
                "name": cust_name,
                "contact": unique_contact,
                "date": evt_date,
                "event_type": "Wedding",
                "occasion": f"Event_{self.test_prefix}",
                "venue": "Grand Hall",
                "pax": 100,
                "total": 50000.0,
                "amount_paid": 25000.0,
                "payment_status": "Partial",
                "status": "CONFIRMED",
                "_status": "valid",
            }
        ]

        inserted, failed, errs = importer.execute_batch_import(rows, "bookings")
        self.assertEqual(inserted, 1)

        # Verify invoice reflects Partial status and ₱25,000 paid amount
        inv = repo.db.fetchone("""
            SELECT * FROM invoices
            WHERE inv_customer_name = %s
            ORDER BY inv_id DESC LIMIT 1
        """, (cust_name,))
        self.assertIsNotNone(inv)
        self.assertEqual(float(inv["inv_total_amount"]), 50000.0)
        self.assertEqual(float(inv["inv_amount_paid"]), 25000.0)
        self.assertEqual(float(inv["inv_balance"]), 25000.0)
        self.assertEqual(inv["inv_status"].capitalize(), "Partial")

    def test_confirm_booking_dialog_layout_and_fixed_footer(self):
        """Verify ConfirmBookingDialog has pinned footer, scrollable body, and maximum height constraint."""
        booking_data = {
            "id": 999,
            "ref": "BK-2026-TEST",
            "name": "Maria Santos",
            "date": "2026-09-15",
            "total": 45000.0,
            "amount_paid": 10000.0,
            "color_theme": "#2563EB",
        }
        dlg = ConfirmBookingDialog(booking_data)
        
        # Sizing constraints for laptop screens
        self.assertLessEqual(dlg.maximumHeight(), 640)
        self.assertGreaterEqual(dlg.maximumHeight(), 420)

        # Confirm button must exist and be accessible
        self.assertIsNotNone(dlg.btn_confirm)
        self.assertEqual(dlg.btn_confirm.text().strip(), "Confirm & Approve Booking")

        # Select custom down payment option
        dlg.rb_custom.setChecked(True)
        self.assertFalse(dlg._pay_options_frame.isHidden())
        self.assertEqual(dlg.get_action_mode(), "downpayment")

        # Select full payment option
        dlg.rb_full.setChecked(True)
        self.assertEqual(dlg.get_action_mode(), "full")
        self.assertEqual(dlg.get_payment_amount(), 35000.0)

        dlg.close()

    def test_batch_confirm_booking_dialog_layout_and_fixed_footer(self):
        """Verify BatchConfirmBookingDialog has pinned footer, scrollable body, and height constraint."""
        bookings = [
            {"id": 101, "ref": "BK-001", "name": "Customer A", "total": 20000.0, "amount_paid": 5000.0},
            {"id": 102, "ref": "BK-002", "name": "Customer B", "total": 30000.0, "amount_paid": 0.0},
        ]
        dlg = BatchConfirmBookingDialog(bookings)

        # Sizing constraints for laptop screens
        self.assertLessEqual(dlg.maximumHeight(), 640)
        self.assertGreaterEqual(dlg.maximumHeight(), 420)

        # Pinned confirm button
        self.assertIsNotNone(dlg.btn_confirm)
        self.assertIn("Confirm 2 Booking(s)", dlg.btn_confirm.text())

        # Select custom down payment option
        dlg.rb_custom.setChecked(True)
        self.assertFalse(dlg._pay_options_frame.isHidden())
        self.assertEqual(dlg.get_action_mode(), "downpayment")

        dlg.close()


if __name__ == "__main__":
    unittest.main()
