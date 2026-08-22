import unittest
from utils.ai_client import ask, _customer_matches
import utils.repository as repo
import utils.db as db


class TestBatchAndAiFixes(unittest.TestCase):
    def test_ai_customer_matching_stops_words(self):
        fake_customer = {"name": "Anoba Const, and Dev Corp", "contact": "09171234567"}
        self.assertFalse(_customer_matches(fake_customer, "total and trends"))
        self.assertFalse(_customer_matches(fake_customer, "compare last year and this year"))
        self.assertFalse(_customer_matches(fake_customer, "how much revenue did we earn"))
        self.assertTrue(_customer_matches(fake_customer, "who is Anoba Const"))

    def test_ai_trend_and_compare_intents(self):
        res1 = ask("total and trends")
        self.assertTrue(res1.get("ok"))
        self.assertNotIn("Anoba Const", res1.get("answer", ""))

        res2 = ask("compare last year and this year")
        self.assertTrue(res2.get("ok"))
        self.assertNotIn("Anoba Const", res2.get("answer", ""))

    def test_customer_deduplication_and_merge(self):
        c1 = {"name": "Test Customer Alpha", "contact": "09171112233", "email": "alpha@example.com", "address": "Cebu City", "status": "Active"}
        c2 = {"name": "Test Customer Alpha", "contact": "09171112233", "email": "alpha_updated@example.com", "address": "Cebu City", "status": "Active"}
        id1 = repo.add_customer(c1)
        id2 = repo.add_customer(c2)
        self.assertEqual(id1, id2, "Adding customer with same name/contact should update existing instead of creating duplicate")

        # Test batch delete
        deleted = repo.delete_multiple_customers([id1])
        self.assertEqual(deleted, 1)

    def test_booking_deduplication_and_batch_delete(self):
        b1 = {
            "name": "Batch Booking Test Client",
            "contact": "09179998877",
            "occasion": "Birthday Bash",
            "date": "2026-11-20",
            "event_time": "18:00",
            "venue": "Test Grand Ballroom",
            "pax": 100,
            "total": 35000.0,
            "amount_paid": 35000.0,
            "payment_mode": "Cash",
            "status": "CONFIRMED",
        }
        res1 = repo.create_booking(b1)
        self.assertIsNotNone(res1)
        bk_id1 = res1.get("booking_id")
        bk_ref1 = res1.get("booking_ref")

        # Attempt duplicate creation of same event
        res2 = repo.create_booking(b1)
        bk_id2 = res2.get("booking_id")
        self.assertEqual(bk_id1, bk_id2, "Creating identical booking for same customer & date should return existing booking")

        # Test batch delete
        deleted = repo.delete_multiple_bookings([bk_id1])
        self.assertEqual(deleted, 1)

    def test_import_booking_dates_and_calendar(self):
        from utils.importer import execute_batch_import
        rows = [
            {
                "_row_index": 1,
                "_status": "valid",
                "_issues": [],
                "_data": {
                    "name": "Date Test Client 1",
                    "contact": "09170000001",
                    "occasion": "Future Event 1",
                    "date": "2026-10-05",
                    "pax": 50,
                    "total": 20000.0,
                    "status": "CONFIRMED",
                },
                "_raw": {}
            },
            {
                "_row_index": 2,
                "_status": "valid",
                "_issues": [],
                "_data": {
                    "name": "Date Test Client 2",
                    "contact": "09170000002",
                    "occasion": "Future Event 2",
                    "date": "2026-10-18",
                    "pax": 100,
                    "total": 40000.0,
                    "status": "CONFIRMED",
                },
                "_raw": {}
            }
        ]
        s_cnt, f_cnt, errs = execute_batch_import(rows, "bookings")
        self.assertEqual(s_cnt, 2)

    def test_menu_and_packages_batch_operations(self):
        # 1. Test menu items batch creation & batch delete
        m1 = {"item": "Batch Test Dish Alpha", "category": "Main Course", "package": "Standard", "price": 450.0, "status": "Available"}
        m2 = {"item": "Batch Test Dish Beta", "category": "Dessert", "package": "Standard", "price": 250.0, "status": "Available"}
        res1 = repo.add_menu_item(m1)
        res2 = repo.add_menu_item(m2)
        
        all_items = repo.get_all_menu_items()
        item_ids = [it["id"] for it in all_items if it.get("item") in ("Batch Test Dish Alpha", "Batch Test Dish Beta")]
        self.assertGreaterEqual(len(item_ids), 2)

        del_count = repo.delete_multiple_menu_items(item_ids)
        self.assertEqual(del_count, len(item_ids))

        # 2. Test packages batch creation & batch delete
    def test_customer_ledger_resilience(self):
        # 1. Edge case IDs
        self.assertEqual(repo.get_customer_ledger(0), [])
        self.assertEqual(repo.get_customer_ledger(None), [])
        self.assertEqual(repo.get_customer_ledger(-1), [])

        # 2. Test CustomerLedgerDialog construction with empty/null fields
        import sys
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        from ui.customers_page import CustomerLedgerDialog

        # Test with None dictionary values
        dlg1 = CustomerLedgerDialog(None, {"id": 9999, "name": None, "contact": None, "email": None, "events": None, "loyalty_tier": None})
        self.assertIsNotNone(dlg1)

        # Test with empty customer
        dlg2 = CustomerLedgerDialog(None, {})
        self.assertIsNotNone(dlg2)


if __name__ == "__main__":
    unittest.main()
