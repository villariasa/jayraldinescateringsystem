import unittest
import utils.db as db
import utils.repository as repo
from utils.importer import (
    auto_map_headers,
    validate_and_prepare_rows,
    execute_batch_import
)

class TestAllUIQueries(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        db.connect_sqlite()

    def test_dashboard_views_and_queries(self):
        kpis = repo.get_dashboard_kpis()
        self.assertIsInstance(kpis, dict)

        upcoming = repo.get_upcoming_events(10)
        self.assertIsInstance(upcoming, list)

        profit = repo.get_profit_summary()
        self.assertIsInstance(profit, list)
        self.assertEqual(len(profit), 12)

        activity = repo.get_recent_activity(10)
        self.assertIsInstance(activity, list)

    def test_reports_views_and_queries(self):
        rep_kpis = repo.get_report_kpis()
        self.assertIsInstance(rep_kpis, dict)

        monthly = repo.get_monthly_income()
        self.assertIsInstance(monthly, list)

        profit = repo.get_profit_summary()
        self.assertIsInstance(profit, list)

        top_occasions = repo.get_top_occasions(10)
        self.assertIsInstance(top_occasions, list)

        # Test all period filters
        filters = [
            "AND DATE(bk_event_date) = DATE('now')",
            "AND DATE(bk_event_date) >= DATE('now', 'weekday 0', '-6 days') AND DATE(bk_event_date) <= DATE('now', 'weekday 0')",
            "AND strftime('%Y-%m', bk_event_date) = strftime('%Y-%m', 'now')",
            "AND strftime('%Y', bk_event_date) = strftime('%Y', 'now')",
            "AND CAST(strftime('%Y', bk_event_date) AS INT) = CAST(strftime('%Y', 'now') AS INT) - 1",
        ]
        for f in filters:
            k = repo.get_report_kpis(period_filter=f)
            self.assertIsInstance(k, dict)
            b = repo.get_all_bookings(period_filter=f)
            self.assertIsInstance(b, list)

    def test_menu_and_kitchen_queries(self):
        menu_items = repo.get_all_menu_items()
        self.assertGreater(len(menu_items), 0)

        avail_items = repo.get_available_menu_items()
        self.assertGreater(len(avail_items), 0)

        packages = repo.get_all_packages()
        self.assertGreater(len(packages), 0)

        kitchen_orders = repo.get_all_orders()
        self.assertIsInstance(kitchen_orders, list)

    def test_importer_all_entities(self):
        # 1. Test Customer Import
        cust_rows = [{"Customer Name": "Juan Importer", "Contact": "09181112233", "Email": "juan@test.com", "Address": "Cebu"}]
        c_map = auto_map_headers(list(cust_rows[0].keys()), "customers")
        prep_c, _ = validate_and_prepare_rows(cust_rows, c_map, "customers")
        s, f, errs = execute_batch_import(prep_c, "customers")
        self.assertEqual(s, 1)

        # 2. Test Expenses Import
        exp_rows = [{"Category": "Food Cost", "Description": "Imported Veggies", "Amount": "3500", "Date": "2026-08-20"}]
        e_map = auto_map_headers(list(exp_rows[0].keys()), "expenses")
        prep_e, _ = validate_and_prepare_rows(exp_rows, e_map, "expenses")
        s, f, errs = execute_batch_import(prep_e, "expenses")
        self.assertEqual(s, 1)

        # 3. Test Menu Items Import
        mi_rows = [{"Item Name": "Crispy Calamares", "Category": "Seafood", "Price": "420", "Description": "Deep fried squid rings"}]
        m_map = auto_map_headers(list(mi_rows[0].keys()), "menu_items")
        prep_m, _ = validate_and_prepare_rows(mi_rows, m_map, "menu_items")
        s, f, errs = execute_batch_import(prep_m, "menu_items")
    def test_booking_auto_approval_and_ledger(self):
        import tempfile, os
        # 1. Create a booking (auto-approved and auto-paid)
        b_data = {
            "name": "AutoApprove Client Test",
            "contact": "09170003344",
            "email": "autoapprove@test.com",
            "address": "Cebu City",
            "occasion": "Anniversary",
            "venue": "Cebu City Club",
            "date": "2026-10-10",
            "time": "18:00",
            "pax": 80,
            "notes": "Auto approval test",
            "menu_type": "package",
            "package_id": 1,
            "menu_value": "Standard Package",
            "total": 28000.0,
            "payment_mode": "Cash",
            "amount_paid": 28000.0,
        }
        b_res = repo.create_booking(b_data)
        self.assertIsNotNone(b_res)
        bk_id = b_res["booking_id"]
        self.assertGreater(bk_id, 0)

        # 2. Check booking detail status is CONFIRMED
        detail = repo.get_booking_detail(bk_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.get("status"), "CONFIRMED")
        self.assertEqual(float(detail.get("amount_paid", 0)), 28000.0)

        # 3. Check customer ledger reflection
        cust_id = detail.get("customer_id")
        self.assertIsNotNone(cust_id)
        ledger = repo.get_customer_ledger(cust_id)
        self.assertIsInstance(ledger, list)
        self.assertGreater(len(ledger), 0)

        # 4. Test Booking CSV Template Generation
        tmp_csv = os.path.join(tempfile.gettempdir(), "test_booking_template.csv")
        from utils.importer import generate_sample_csv
        err_csv = generate_sample_csv("bookings", tmp_csv)
        self.assertIsNone(err_csv)
        self.assertTrue(os.path.exists(tmp_csv))

        # 5. Test Calendar PDF Export
        tmp_pdf = os.path.join(tempfile.gettempdir(), "test_calendar_export.pdf")
        import utils.exporter as exporter
        month_events = {
            10: [{
                "event_name": "AutoApprove Client Test",
                "pax": 80,
                "time": "6:00 PM",
                "location": "Cebu City Club",
                "ref": b_res.get("booking_ref", "BK-0001"),
                "status": "CONFIRMED",
            }]
        }
        ok_pdf = exporter.export_calendar_pdf(tmp_pdf, 2026, 10, month_events)
        # 6. Test Dashboard & Reports PDF Export with full analytics sections
        tmp_dash_pdf = os.path.join(tempfile.gettempdir(), "test_dash_export.pdf")
        sections = exporter.build_analytics_sections()
        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)

        kpis = repo.get_report_kpis()
        bookings = repo.get_all_bookings() or []
        ok_dash_pdf = exporter.export_pdf(tmp_dash_pdf, kpis, bookings, "Dashboard Report", "All Time", sections=sections)
        self.assertTrue(ok_dash_pdf)
        self.assertTrue(os.path.exists(tmp_dash_pdf))
        self.assertGreater(os.path.getsize(tmp_dash_pdf), 1000)

    def test_z_purge_data_and_reset(self):
        # 7. Test Data Counts and Selective / Full Purge Functions
        counts = repo.get_data_counts()
        self.assertIsInstance(counts, dict)
        self.assertIn("bookings", counts)
        self.assertIn("customers", counts)
        self.assertIn("expenses", counts)

        # Selective purge
        purged_sel = repo.purge_selected_data(["expenses", "calendar_events"])
        self.assertIn("expenses", purged_sel)
        self.assertIn("calendar_events", purged_sel)

        # Master reset purge
        purged_all = repo.purge_all_data()
        self.assertIn("bookings", purged_all)
        self.assertIn("customers", purged_all)
        self.assertIn("menu_items", purged_all)
        self.assertIn("packages", purged_all)

        new_counts = repo.get_data_counts()
        self.assertEqual(new_counts["bookings"], 0)
        self.assertEqual(new_counts["customers"], 0)
        self.assertEqual(new_counts["expenses"], 0)

        # Re-seed essentials for test continuity
        db.connect_sqlite()


if __name__ == "__main__":
    unittest.main()

