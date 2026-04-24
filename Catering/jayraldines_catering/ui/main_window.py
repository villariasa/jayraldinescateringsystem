from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Signal

from components.sidebar import Sidebar
from components.topbar import TopBar
from components.notifications_panel import NotificationPopover, _notifications
from ui.dashboard_page import DashboardPage
from ui.booking_page import BookingPage
from ui.customers_page import CustomersPage
from ui.menu_page import MenuPage
from ui.calendar_page import CalendarPage
from ui.kitchen_page import KitchenPage
from ui.billing_page import BillingPage
from ui.reports_page import ReportsPage
from ui.settings_page import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jayraldine's Catering")
        self.resize(1400, 900)
        self.showFullScreen()

        self.shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        self.shortcut_f11.activated.connect(self._toggle_fullscreen)
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self._exit_fullscreen)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.topbar = TopBar()
        right_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()

        self.dashboard_page  = DashboardPage()
        self.booking_page    = BookingPage()
        self.customers_page  = CustomersPage()
        self.menu_page       = MenuPage()
        self.calendar_page   = CalendarPage()
        self.kitchen_page    = KitchenPage()
        self.billing_page    = BillingPage()
        self.reports_page    = ReportsPage()
        self.settings_page   = SettingsPage()

        self.stack.addWidget(self.dashboard_page)   # 0
        self.stack.addWidget(self.booking_page)     # 1
        self.stack.addWidget(self.customers_page)   # 2
        self.stack.addWidget(self.menu_page)        # 3
        self.stack.addWidget(self.calendar_page)    # 4
        self.stack.addWidget(self.kitchen_page)     # 5
        self.stack.addWidget(self.billing_page)     # 6
        self.stack.addWidget(self.reports_page)     # 7
        self.stack.addWidget(self.settings_page)    # 8

        right_layout.addWidget(self.stack)
        main_layout.addWidget(right)

        self.sidebar.page_changed.connect(self._navigate)
        self.dashboard_page.new_booking_requested.connect(lambda: self._navigate(1))
        self._notif_popover = NotificationPopover(parent=self)
        self.topbar.notif_btn.clicked.connect(
            lambda: self._notif_popover.toggle_anchored(self.topbar.notif_btn)
        )
        self.topbar.search_changed.connect(self._on_search)

        self._navigate(0)

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        self.topbar.set_page(index)
        self.sidebar.handle_click(index)

    def _on_search(self, text):
        page = self.stack.currentWidget()
        if hasattr(page, "filter_search"):
            page.filter_search(text)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _exit_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
