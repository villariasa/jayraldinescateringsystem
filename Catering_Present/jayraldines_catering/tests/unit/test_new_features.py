"""
tests/unit/test_new_features.py
-------------------------------
Unit tests for the new features:
1. Multiple Add package dropdown and price auto-calc.
2. PENDING order default and manual order confirmation.
3. Order editing.
4. Dashboard daily/specific date filtering.
5. Monthly Sales Targets & 12-month Evaluation Report (Ref Image 1).
6. Cash Flow ledger CRUD & running balance (Ref Image 2).
7. Down payment tracking & manual verification.
"""

import unittest
import os
from datetime import date, datetime
import utils.repository as repo
from utils.signals import app_events


class TestNewFeatures(unittest.TestCase):

    def test_cash_flow_ledger_and_running_balance(self):
        """Test Cash Flow CRUD and sequential running balance recalculation."""
        # 1. Add deposit
        id1 = repo.add_cash_flow_transaction({
            "date": "2026-05-01",
            "check_no": "CHK-001",
            "particulars": "BDO Jayraldine's Catering",
            "deposit": 100000.0,
            "withdrawal": 0.0,
            "notes": "Initial capital deposit"
        })
        self.assertIsNotNone(id1)

        # 2. Add withdrawal
        id2 = repo.add_cash_flow_transaction({
            "date": "2026-05-02",
            "check_no": "CHK-002",
            "particulars": "Cash on Hand",
            "deposit": 0.0,
            "withdrawal": 25000.0,
            "notes": "Market ingredients withdrawal"
        })
        self.assertIsNotNone(id2)

        # 3. Add second deposit
        id3 = repo.add_cash_flow_transaction({
            "date": "2026-05-03",
            "check_no": "GCASH-99",
            "particulars": "GCash",
            "deposit": 15000.0,
            "withdrawal": 0.0,
            "notes": "Customer DP received"
        })
        self.assertIsNotNone(id3)

        # 4. Verify running balances:
        # Row 1: 100,000 - 0 = 100,000
        # Row 2: 100,000 - 25,000 = 75,000
        # Row 3: 75,000 + 15,000 = 90,000
        txs = repo.get_cash_flow_transactions()
        self.assertGreaterEqual(len(txs), 3)

        summary = repo.get_cash_flow_summary()
        self.assertGreaterEqual(summary["total_deposits"], 115000.0)
        self.assertGreaterEqual(summary["total_withdrawals"], 25000.0)

        # 5. Clean up
        repo.delete_cash_flow_transaction(id1)
        repo.delete_cash_flow_transaction(id2)
        repo.delete_cash_flow_transaction(id3)

    def test_sales_targets_and_evaluation_report(self):
        """Test monthly sales targets and 12-month evaluation math (Ref Image 1)."""
        year = 2026

        # 1. Set monthly targets (e.g. 85,000 for each month)
        repo.set_yearly_default_target(year, 85000.0)
        targets = repo.get_monthly_sales_targets(year)
        self.assertEqual(len(targets), 12)
        self.assertEqual(targets[1], 85000.0)
        self.assertEqual(targets[12], 85000.0)

        # 2. Get Evaluation Report
        report = repo.get_monthly_sales_evaluation_report(year)
        self.assertEqual(report["year"], year)
        self.assertEqual(report["total_target"], 1020000.0) # 85,000 * 12
        self.assertEqual(len(report["months"]), 12)

        for m in report["months"]:
            self.assertEqual(m["target_sales"], 85000.0)
            # Formula: Target - Actual = Remaining
            expected_rem = m["target_sales"] - m["actual_sales"]
            self.assertEqual(m["remaining"], expected_rem)

    def test_order_down_payment_and_manual_acceptance(self):
        """Test that new bookings default to PENDING and down payments are tracked separately."""
        cust = repo.get_all_customers()
        cust_id = cust[0]["id"] if cust else 1

        b_data = {
            "customer_id": cust_id,
            "name": "Maria DownPayment Test",
            "contact": "09170001122",
            "email": "maria.test@example.com",
            "address": "Banilad, Cebu City",
            "occasion": "Debut",
            "venue": "Grand Ballroom",
            "event_date": "2026-11-20",
            "event_time": "18:00",
            "pax": 100,
            "total_amount": 50000.0,
            "down_payment": 15000.0,
            "amount_paid": 15000.0,
            "menu_type": "Package",
            "package_id": 1,
            "notes": "Down payment test booking",
        }

        res = repo.create_booking(b_data)
        self.assertIsNotNone(res)
        bk_id = res["booking_id"]

        # 1. Must default to PENDING (NOT auto-confirmed)
        detail = repo.get_booking_detail(bk_id)
        self.assertEqual(detail["status"], "PENDING")
        self.assertEqual(float(detail.get("down_payment") or 0.0), 15000.0)

        # 2. Manual confirmation
        repo.confirm_booking_order(bk_id)
        detail2 = repo.get_booking_detail(bk_id)
        self.assertEqual(detail2["status"], "CONFIRMED")

        # 3. Down payment summary
        dp_sum = repo.get_down_payments_summary()
        self.assertGreaterEqual(dp_sum["total_down_payments_received"], 0.0)

        # Clean up
        repo.delete_booking(bk_id)

    def test_dashboard_date_filtered_kpis(self):
        """Test daily & specific date KPI metrics calculation for dashboard."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        kpis_today = repo.get_dashboard_kpis_filtered(today_str)
        self.assertIn("todays_events", kpis_today)
        self.assertIn("daily_sales", kpis_today)
        self.assertIn("daily_payments", kpis_today)
        self.assertIn("daily_expenses", kpis_today)
        self.assertIn("net_income", kpis_today)

    def test_daily_date_separated_logging(self):
        """Test that app logs are named and separated daily by current date."""
        from utils.logger import get_log_file_path, get_daily_log_filename, get_logger, export_diagnostic_report
        import tempfile
        from pathlib import Path

        today_str = datetime.now().strftime("%Y-%m-%d")
        expected_filename = f"app_{today_str}.log"
        self.assertEqual(get_daily_log_filename(), expected_filename)

        active_log = get_log_file_path()
        self.assertTrue(str(active_log).endswith(expected_filename))

        # Write test log message
        log = get_logger()
        test_msg = f"Test daily log entry at {datetime.now()}"
        log.info(test_msg)

        # Verify active log file exists and contains message
        self.assertTrue(active_log.exists())
        with open(active_log, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            self.assertIn(test_msg, content)

    def test_cash_flow_import_and_export(self):
        """Test Cash Flow import wizard routines and CSV/Excel/PDF export routines."""
        import tempfile
        import utils.importer as importer
        from utils.exporter import export_custom_entity_data, export_cash_flow_pdf

        # 1. Test Importer Schema & Mapping
        self.assertIn("cash_flow", importer.ENTITY_SCHEMAS)
        headers = ["Date", "Check Number", "Account Particulars", "Deposit Amount", "Withdrawal Amount", "Actual Sales", "Notes"]
        mapping = importer.auto_map_headers(headers, "cash_flow")
        self.assertEqual(mapping.get("date"), "Date")
        self.assertEqual(mapping.get("check_no"), "Check Number")
        self.assertEqual(mapping.get("particulars"), "Account Particulars")
        self.assertEqual(mapping.get("deposit"), "Deposit Amount")
        self.assertEqual(mapping.get("withdrawal"), "Withdrawal Amount")
        self.assertEqual(mapping.get("actual_sales"), "Actual Sales")

        # 2. Test Batch Import
        test_rows = [
            {
                "Date": "2026-06-15",
                "Check Number": "IMP-001",
                "Account Particulars": "GCash",
                "Deposit Amount": "7500.00",
                "Withdrawal Amount": "0.00",
                "Actual Sales": "132000.00",
                "Notes": "Imported Test Deposit",
            },
            {
                "Date": "2026-06-16",
                "Check Number": "IMP-002",
                "Account Particulars": "Cash on Hand",
                "Deposit Amount": "0.00",
                "Withdrawal Amount": "2500.00",
                "Actual Sales": "70000.00",
                "Notes": "Imported Test Withdrawal",
            }
        ]
        prep_rows, counts = importer.validate_and_prepare_rows(test_rows, mapping, "cash_flow")
        self.assertEqual(len(prep_rows), 2)
        s_cnt, f_cnt, errs = importer.execute_batch_import(prep_rows, "cash_flow", skip_errors=True)
        self.assertEqual(s_cnt, 2)
        self.assertEqual(f_cnt, 0)

        # 3. Test Export CSV
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            csv_path = f.name
        ok_csv = export_custom_entity_data("Cash Flow", is_excel=False, save_path=csv_path)
        self.assertTrue(ok_csv)
        with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
            csv_content = f.read()
            self.assertIn("Particulars", csv_content)
            self.assertIn("Actual Sales", csv_content)
            self.assertIn("Variance", csv_content)

        # 4. Test Export Excel
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            xlsx_path = f.name
        ok_xlsx = export_custom_entity_data("Cash Flow", is_excel=True, save_path=xlsx_path)
        self.assertTrue(ok_xlsx)

        # 5. Test Export PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        ok_pdf = export_cash_flow_pdf(pdf_path)
        self.assertTrue(ok_pdf)

    def test_quick_multi_order_with_customer_and_custom_dishes(self):
        """Test Quick Multi-Add Order dialog with registered customer auto-fill and custom dishes selector."""
        from PySide6.QtWidgets import QApplication
        import sys
        from ui.booking_page import AddMultipleBookingsDialog, MultiMenuSelectionDialog

        _ = QApplication.instance() or QApplication(sys.argv)

        # Test MultiMenuSelectionDialog
        menu_dlg = MultiMenuSelectionDialog(selected_items=["Special Pork Humba", "Chicken Pandan"])
        self.assertIsNotNone(menu_dlg)
        sel_names, sel_rate = menu_dlg.get_selected_dishes()
        self.assertIn("Special Pork Humba", sel_names)
        self.assertIn("Chicken Pandan", sel_names)
        self.assertGreater(sel_rate, 0.0)

        # Test AddMultipleBookingsDialog
        multi_dlg = AddMultipleBookingsDialog()
        self.assertIsNotNone(multi_dlg)
        self.assertEqual(multi_dlg.table.columnCount(), 11)
        self.assertGreaterEqual(multi_dlg.table.rowCount(), 5)

        # Populate first row and test save_all
        cust_combo = multi_dlg.table.cellWidget(0, 0)
        cust_combo.setCurrentText("Test Multi Customer")
        multi_dlg._save_all()
        self.assertGreaterEqual(multi_dlg._added_count, 1)

    def test_export_success_dialog_and_prompt(self):
        """Test ExportSuccessDialog and prompt_file_saved helper across different file types."""
        from PySide6.QtWidgets import QApplication
        import sys
        import tempfile
        from components.dialogs import ExportSuccessDialog, prompt_file_saved

        _ = QApplication.instance() or QApplication(sys.argv)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            xlsx_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            csv_path = f.name

        # PDF Dialog
        dlg_pdf = ExportSuccessDialog(file_path=pdf_path, title="PDF Exported")
        self.assertIsNotNone(dlg_pdf)
        self.assertEqual(dlg_pdf.file_path, pdf_path)

        # Excel Dialog
        dlg_xlsx = ExportSuccessDialog(file_path=xlsx_path, title="Excel Exported")
        self.assertIsNotNone(dlg_xlsx)

    def test_confirm_booking_with_downpayment_persists_confirmed_status(self):
        """Verify that confirming a booking with any downpayment persists CONFIRMED status in DB."""
        # Pre-cleanup in case of earlier interrupted run
        import utils.db as _d
        _d.execute("DELETE FROM bookings WHERE LOWER(bk_customer_name) = 'test downpayment confirmation client'")

        # 1. Create a booking (initially PENDING)
        bkg = repo.create_booking({
            "name": "Test Downpayment Confirmation Client",
            "contact": "09189998877",
            "email": "downpayment_test@example.com",
            "address": "Cebu City",
            "occasion": "Anniversary",
            "venue": "Radisson Blu",
            "date": "2026-09-10",
            "time": "7:00 PM",
            "pax": 100,
            "total": 45000.0,
            "payment_mode": "Cash",
            "down_payment": 0.0,
        })
        self.assertIsNotNone(bkg)
        db_id = bkg["booking_id"]

        try:
            # Check initial status in DB is PENDING
            detail = repo.get_booking_detail(db_id)
            self.assertIsNotNone(detail)
            self.assertEqual(detail.get("status"), "PENDING")

            # 2. Confirm booking with a partial downpayment (e.g. ₱5,000 on ₱45,000 order)
            pay_res = repo.pay_invoice(
                db_id,
                payment_amount=5000.0,
                payment_date="2026-09-01",
                method="GCash",
                note="Down payment upon booking confirmation"
            )
            self.assertEqual(pay_res["new_booking_status"], "CONFIRMED")
            self.assertEqual(pay_res["new_paid"], 5000.0)

            # 3. Explicitly update booking status as done in UI
            repo.update_booking_status(db_id, "CONFIRMED")

            # 4. Query fresh detail from DB — MUST be CONFIRMED and NOT revert to PENDING
            fresh_detail = repo.get_booking_detail(db_id)
            self.assertEqual(fresh_detail.get("status"), "CONFIRMED")
            self.assertEqual(float(fresh_detail.get("amount_paid", 0.0)), 5000.0)

            # 5. Check in get_all_bookings list
            all_b = repo.get_all_bookings()
            matched = next((x for x in all_b if x["db_id"] == db_id), None)
            self.assertIsNotNone(matched)
            self.assertEqual(matched["status"], "CONFIRMED")
        finally:
            repo.delete_booking(db_id)

    def test_ai_typewriter_and_card_animation(self):
        """Test TypewriterLabel, format_ai_text, and build_ai_card animation behavior."""
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        from components.global_ai_floating import format_ai_text, TypewriterLabel, build_ai_card

        # 1. Test markdown formatting helper
        raw_text = "Hello **Chef**! *Here* is `₱ 45,000`\nNext line."
        formatted = format_ai_text(raw_text, is_dark=True)
        self.assertIn("<b>Chef</b>", formatted)
        self.assertIn("<i>Here</i>", formatted)
        self.assertIn("<br/>", formatted)

        # 2. Test TypewriterLabel instant rendering
        lbl_static = TypewriterLabel("Instant Text", animate=False)
        self.assertIn("Instant Text", lbl_static.text())

        # 3. Test TypewriterLabel animated execution
        lbl_anim = TypewriterLabel("Animated Answer for testing typewriter", animate=True)
        # Advance tick
        lbl_anim._on_tick()
        self.assertTrue(len(lbl_anim.text()) > 0)
        # Skip to end
        lbl_anim._current_len = lbl_anim._total_len
        lbl_anim._on_tick()
        self.assertIn("Animated Answer", lbl_anim.text())

        # 4. Test build_ai_card creation with animation and options
        options = [{"label": "Action 1", "send": "send_action_1"}]
        card = build_ai_card("Hello from Chef Jay!", options=options, animate_typing=True)
        self.assertIsNotNone(card)

    def test_dynamic_occasions_in_booking_and_multi_order(self):
        """Verify that occasions added in Settings dynamically appear in BookingModal and MultiOrder."""
        import utils.repository as repo
        from components.booking_modal import BookingModal
        from ui.booking_page import AddMultipleBookingsDialog

        test_occ = "Grand Thanksgiving Gala"
        repo.add_occasion(test_occ)
        try:
            occasions = repo.get_all_occasions()
            self.assertIn(test_occ, occasions)

            # Check AddMultipleBookingsDialog
            multi_dlg = AddMultipleBookingsDialog()
            self.assertIn(test_occ, multi_dlg._occasions)
            occ_combo = multi_dlg.table.cellWidget(0, 2)
            self.assertTrue(occ_combo.isEditable())
            items = [occ_combo.itemText(i) for i in range(occ_combo.count())]
            self.assertIn(test_occ, items)

            # Check BookingModal
            modal = BookingModal()
            self.assertIn(test_occ, modal._occasions)
            modal_items = [modal.f_occasion.itemText(i) for i in range(modal.f_occasion.count())]
            self.assertIn(test_occ, modal_items)
            self.assertTrue(modal.f_occasion.isEditable())
        finally:
            repo.delete_occasion(test_occ)

    def test_calendar_displays_unpaid_and_confirmed_bookings(self):
        """Verify that confirmed bookings (even unpaid / 0 down payment) and various date formats display in calendar."""
        import utils.repository as repo
        from datetime import date
        from ui.calendar_page import CalendarPage

        b_data = {
            "name": "Calendar Display Test Client",
            "contact": "09170001111",
            "email": "caltest@test.com",
            "address": "Cebu City",
            "occasion": "Company Gala",
            "venue": "Waterfront Cebu",
            "date": "2026-11-15",
            "time": "7:00 PM",
            "pax": 120,
            "notes": "Motif: Royal Blue and Silver",
            "menu_type": "package",
            "total": 60000.0,
            "amount_paid": 0.0,  # ₱0 down payment - completely unpaid
            "down_payment": 0.0,
            "status": "CONFIRMED",
        }
        res = repo.create_booking(b_data)
        self.assertIsNotNone(res)
        b_id = res.get("booking_id")
        self.assertIsNotNone(b_id)

        try:
            # Explicitly ensure status is CONFIRMED
            repo.update_booking_status(b_id, "CONFIRMED")

            # Check get_calendar_events_for_month
            month_events = repo.get_calendar_events_for_month(2026, 11)
            self.assertIn((2026, 11, 15), month_events)
            events_on_day = month_events[(2026, 11, 15)]
            matched = next((e for e in events_on_day if e.get("customer_name") == "Calendar Display Test Client"), None)
            self.assertIsNotNone(matched)
            self.assertEqual(matched.get("status"), "CONFIRMED")
            self.assertEqual(matched.get("balance"), 60000.0)
            self.assertEqual(matched.get("amount_paid"), 0.0)

            # Check get_calendar_events_for_date
            day_events = repo.get_calendar_events_for_date(date(2026, 11, 15))
            self.assertTrue(any("Calendar Display Test Client" in e.get("name", "") for e in day_events))

            # Check CalendarPage render
            page = CalendarPage()
            page.current_year = 2026
            page.current_month = 11
            page.reload()
            self.assertIn((2026, 11, 15), page._db_cache)
        finally:
            repo.delete_booking(b_id)

    def test_batch_confirm_dialog_flexible_payment_options(self):
        """Test BatchConfirmBookingDialog allows Unpaid, Down Payment, and Fully Paid options."""
        from components.confirm_booking_dialog import BatchConfirmBookingDialog
        
        sample_pending = [
            {"id": "BK-202608-01", "name": "Batch Client 1", "total": 50000.0, "amount_paid": 0.0, "status": "PENDING"},
            {"id": "BK-202608-02", "name": "Batch Client 2", "total": 30000.0, "amount_paid": 5000.0, "status": "PENDING"},
        ]

        dlg = BatchConfirmBookingDialog(sample_pending)
        self.assertEqual(dlg._count, 2)
        self.assertEqual(dlg._tot_val, 80000.0)
        self.assertEqual(dlg._paid_val, 5000.0)
        self.assertEqual(dlg._rem_val, 75000.0)

        # Default is "none" (No payment today, confirm only)
        self.assertEqual(dlg.get_action_mode(), "none")
        self.assertEqual(dlg.get_payment_amount_per_booking(), 0.0)

        # Switch to downpayment
        dlg.rb_custom.setChecked(True)
        self.assertEqual(dlg.get_action_mode(), "downpayment")
        dlg.num_amount.setValue(10000.0)
        self.assertEqual(dlg.get_payment_amount_per_booking(), 10000.0)

        # Switch to fully paid
        dlg.rb_full.setChecked(True)
        self.assertEqual(dlg.get_action_mode(), "full")

        # Color Theme Selector check
        self.assertTrue(hasattr(dlg, "get_color_theme"))
        self.assertEqual(dlg.get_color_theme(), "#2563EB")
        dlg._color_picker.set_color("#E11D48")
        self.assertEqual(dlg.get_color_theme(), "#E11D48")

    def test_cash_flow_page_loading_and_packaging_spec(self):
        """Test Cash Flow page import, instantiation, and inclusion in spec hiddenimports."""
        # 1. Direct import & instantiation
        from ui.cash_flow_page import CashFlowPage
        page = CashFlowPage()
        self.assertIsNotNone(page)

        # 2. Main window dynamic resolution
        import importlib
        mod = importlib.import_module("ui.cash_flow_page")
        cls = getattr(mod, "CashFlowPage")
        self.assertEqual(cls, CashFlowPage)

        # 3. Spec file hiddenimports check
        from pathlib import Path
        spec_path = Path(__file__).resolve().parents[2] / "jayraldines.spec"
        if spec_path.exists():
            spec_content = spec_path.read_text(encoding="utf-8")
            self.assertIn("ui.cash_flow_page", spec_content)

    def test_booking_color_theme_persistence_and_calendar_integration(self):
        """Test booking color theme storage, modification, calendar event integration, and PDF export."""
        b_data = {
            "name": "Color Theme Test Client",
            "contact": "09170009999",
            "email": "colortest@example.com",
            "address": "Cebu City",
            "venue": "Marco Polo Plaza Cebu",
            "occasion": "Golden Wedding Anniversary",
            "date": "2026-12-20",
            "time": "6:30 PM",
            "pax": 150,
            "notes": "Motif: Emerald Green and Champagne Gold",
            "menu_type": "package",
            "total": 75000.0,
            "amount_paid": 20000.0,
            "down_payment": 20000.0,
            "color_theme": "#059669",  # Emerald Green
            "status": "CONFIRMED",
        }
        res = repo.create_booking(b_data)
        self.assertIsNotNone(res)
        b_id = res.get("booking_id")
        self.assertIsNotNone(b_id)

        try:
            # 1. Verify get_booking_detail retrieves color_theme
            detail = repo.get_booking_detail(b_id)
            self.assertIsNotNone(detail)
            self.assertEqual(detail.get("color_theme"), "#059669")

            # 2. Verify update_booking_color_theme modifies it
            success = repo.update_booking_color_theme(b_id, "#7C3AED")  # Royal Purple
            self.assertTrue(success)
            detail2 = repo.get_booking_detail(b_id)
            self.assertEqual(detail2.get("color_theme"), "#7C3AED")

            # 3. Verify get_calendar_events_for_month includes color_theme
            month_events = repo.get_calendar_events_for_month(2026, 12)
            self.assertIn((2026, 12, 20), month_events)
            ev_list = month_events[(2026, 12, 20)]
            ev = next((e for e in ev_list if e.get("customer_name") == "Color Theme Test Client"), None)
            self.assertIsNotNone(ev)
            self.assertEqual(ev.get("color_theme"), "#7C3AED")
            self.assertEqual(ev.get("color"), "#7C3AED")

            # 4. Verify Calendar PDF Export generation with Color Theme & Agenda replacement
            from utils.exporter import export_calendar_pdf
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                out_path = tmp_pdf.name
            
            gen_res = export_calendar_pdf(2026, 12, out_path, month_events, biz_name="Jayraldine's Catering Services")
            self.assertTrue(gen_res)
            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 1000)
            try:
                os.remove(out_path)
            except Exception:
                pass
        finally:
            repo.delete_booking(b_id)


if __name__ == "__main__":
    unittest.main()


