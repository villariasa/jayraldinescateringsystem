"""
tests/unit/test_ui_pages_instantiation.py
-----------------------------------------
Instantiates every single UI page in a QApplication instance to guarantee
zero NameErrors, missing imports, or layout bugs during runtime page loading.
"""

import unittest
import sys
from PySide6.QtWidgets import QApplication

# Ensure single QApplication exists
app = QApplication.instance() or QApplication(sys.argv)


class TestUIPagesInstantiation(unittest.TestCase):

    def test_all_pages_instantiation(self):
        from ui.dashboard_page import DashboardPage
        from ui.booking_page import BookingPage
        from ui.customers_page import CustomersPage
        from ui.menu_page import MenuPage
        from ui.calendar_page import CalendarPage
        from ui.cash_flow_page import CashFlowPage
        from ui.billing_page import BillingPage
        from ui.reports_page import ReportsPage
        from ui.expenses_page import ExpensesPage
        from ui.ai_page import AIPage
        from ui.settings_page import SettingsPage
        from ui.main_window import MainWindow

        # Test instantiate each page
        p_dashboard = DashboardPage()
        self.assertIsNotNone(p_dashboard)

        p_booking = BookingPage()
        self.assertIsNotNone(p_booking)

        p_customers = CustomersPage()
        self.assertIsNotNone(p_customers)

        p_menu = MenuPage()
        self.assertIsNotNone(p_menu)

        p_calendar = CalendarPage()
        self.assertIsNotNone(p_calendar)

        p_cashflow = CashFlowPage()
        self.assertIsNotNone(p_cashflow)

        p_billing = BillingPage()
        self.assertIsNotNone(p_billing)

        p_reports = ReportsPage()
        self.assertIsNotNone(p_reports)

        p_expenses = ExpensesPage()
        self.assertIsNotNone(p_expenses)

        p_ai = AIPage()
        self.assertIsNotNone(p_ai)

        p_settings = SettingsPage()
        self.assertIsNotNone(p_settings)

        # Test MainWindow instantiation and page switching
        win = MainWindow()
        self.assertIsNotNone(win)
        for idx in range(11):
            win._navigate(idx)
            page = win._get_page(idx)
            self.assertIsNotNone(page)


if __name__ == "__main__":
    unittest.main()
