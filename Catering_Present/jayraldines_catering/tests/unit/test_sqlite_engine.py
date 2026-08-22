import os
import unittest
import tempfile
from pathlib import Path
from datetime import date, datetime

import utils.db as db
import utils.repository as repo
from utils.logger import setup_logging, export_diagnostic_report, get_log_dir


class TestSQLiteEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create temp database for isolation
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = Path(cls.temp_dir.name) / "test_catering.db"
        db.set_sqlite_db_path(cls.test_db_path)
        cls.connected = db.connect_sqlite()

    @classmethod
    def tearDownClass(cls):
        db.close()
        cls.temp_dir.cleanup()

    def test_01_sqlite_connection_and_engine(self):
        self.assertTrue(self.connected)
        self.assertEqual(db.get_engine_type(), "sqlite")
        self.assertTrue(db.is_available())

    def test_02_sqlite_schema_and_address_seed(self):
        addresses = repo.get_all_cebu_addresses()
        self.assertGreater(len(addresses), 0)
        mabolo_matches = repo.search_cebu_address("Mabolo Cebu")
        self.assertTrue(any("Mabolo" in r["barangay"] for r in mabolo_matches))

    def test_03_customer_crud(self):
        cust_id = repo.add_customer({
            "name": "Maria Test Santos",
            "contact": "09171234567",
            "email": "maria@test.com",
            "address": "Cebu City",
            "status": "Active",
        })
        self.assertIsNotNone(cust_id)
        self.assertGreater(cust_id, 0)

        # Query back
        all_custs = repo.get_all_customers()
        self.assertTrue(any(c["name"] == "Maria Test Santos" for c in all_custs))

        # Update
        repo.update_customer(cust_id, {
            "name": "Maria Santos Updated",
            "contact": "09179998877",
            "email": "maria.updated@test.com",
            "address": "Mandaue City",
            "status": "Active",
        })
        updated_custs = repo.get_all_customers()
        self.assertTrue(any(c["name"] == "Maria Santos Updated" for c in updated_custs))

    def test_04_expense_crud(self):
        exp_id = repo.add_expense({
            "category": "Food Cost",
            "description": "Pork Lechon Belly",
            "amount": 15000.0,
            "date": "Aug 20, 2026",
        })
        self.assertIsNotNone(exp_id)
        self.assertGreater(exp_id, 0)

        all_exp = repo.get_all_expenses()
        self.assertTrue(any(e["description"] == "Pork Lechon Belly" for e in all_exp))

    def test_05_package_crud(self):
        pkg_id = repo.add_package({
            "name": "Custom Birthday Special",
            "description": "5 Dishes with Free Dessert",
            "price_per_pax": 420.0,
            "min_pax": 40,
        })
        self.assertIsNotNone(pkg_id)
        all_pkgs = repo.get_all_packages()
        self.assertTrue(any(p["name"] == "Custom Birthday Special" for p in all_pkgs))

    def test_06_calendar_month_batch(self):
        # Create a booking
        bkg = repo.create_booking({
            "name": "Wedding Client",
            "contact": "09170001122",
            "email": "wedding@test.com",
            "address": "Grand Ballroom",
            "occasion": "Wedding",
            "venue": "Grand Ballroom",
            "date": "2026-08-25",
            "time": "6:00 PM",
            "pax": 150,
            "total": 55000.0,
            "payment_mode": "Cash",
            "amount_paid": 10000.0,
        })
        self.assertIsNotNone(bkg)
        self.assertIn("booking_id", bkg)

        # Batch month fetch
        month_events = repo.get_calendar_events_for_month(2026, 8)
        self.assertIn((2026, 8, 25), month_events)
        day_events = month_events[(2026, 8, 25)]
        self.assertTrue(any("Wedding Client" in e["name"] for e in day_events))

    def test_07_diagnostic_logger_and_report_export(self):
        logger = setup_logging()
        logger.info("Test log message for diagnostic verification.")
        
        # Test report export to temp dir
        temp_export_dir = Path(self.temp_dir.name)
        report_path = export_diagnostic_report(temp_export_dir)
        self.assertTrue(report_path.exists())
        self.assertGreater(report_path.stat().st_size, 100)

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("JAYRALDINE'S CATERING SYSTEM - DIAGNOSTIC REPORT", content)
            self.assertIn("database engine: sqlite", content.lower())


if __name__ == "__main__":
    unittest.main()
