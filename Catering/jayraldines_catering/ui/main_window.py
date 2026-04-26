from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Signal, QTimer

from components.sidebar import Sidebar
from components.topbar import TopBar
from components.notifications_panel import NotificationPopover, reload_notifications
from components.toast import ToastManager
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

        print("[MW] Initializing MainWindow...")

        self.setWindowTitle("Jayraldine's Catering")
        self.resize(1400, 900)

        print("[MW] Scheduling fullscreen...")
        self.fullscreen_timer = QTimer(self)
        self.fullscreen_timer.setSingleShot(True)
        self.fullscreen_timer.timeout.connect(self.showFullScreen)
        self.fullscreen_timer.start(300)

        self.shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        self.shortcut_f11.activated.connect(self._toggle_fullscreen)
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self._exit_fullscreen)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.main_layout.addWidget(self.sidebar)

        self.right_widget = QWidget(self.central_widget)
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        self.topbar = TopBar()
        self.right_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()

        print("[MW] Creating pages...")

        self.dashboard_page  = DashboardPage()
        self.booking_page    = BookingPage()
        self.customers_page  = CustomersPage()
        self.menu_page       = MenuPage()
        self.calendar_page   = CalendarPage()
        self.kitchen_page    = KitchenPage()
        self.billing_page    = BillingPage()
        
        # ✅ NEXT TEST: ReportsPage is now active!
        self.reports_page    = ReportsPage()
        
        self.settings_page   = SettingsPage()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.booking_page)
        self.stack.addWidget(self.customers_page)
        self.stack.addWidget(self.menu_page)
        self.stack.addWidget(self.calendar_page)
        self.stack.addWidget(self.kitchen_page)
        self.stack.addWidget(self.billing_page)
        
        # ✅ Added ReportsPage to the stack!
        self.stack.addWidget(self.reports_page)
        
        self.stack.addWidget(self.settings_page)

        self.right_layout.addWidget(self.stack)
        self.main_layout.addWidget(self.right_widget)

        self.sidebar.page_changed.connect(self._navigate)
        self.dashboard_page.new_booking_requested.connect(lambda: self._navigate(1))

        self._notif_popover = NotificationPopover(parent=self)
        self.topbar.notif_btn.clicked.connect(
            lambda: self._notif_popover.toggle_anchored(self.topbar.notif_btn)
        )

        self._notif_popover.all_read.connect(self._on_all_read)

        self._toast_manager = ToastManager(self)

        from utils.notif_scheduler import NotifScheduler
        self._scheduler = NotifScheduler(self)
        self._scheduler.new_notification.connect(self._on_new_notification)

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_notifications)
        self._poll_timer.start(60_000)
        QTimer.singleShot(0, self._poll_notifications)

        self.topbar.search_changed.connect(self._on_search)

        print("[MW] Navigating to dashboard...")
        self._navigate(0)

        print("[MW] MainWindow init complete")

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

    def _poll_notifications(self):
        count = reload_notifications()
        self.topbar.notif_badge.setText(str(count))
        self.topbar.notif_badge.setVisible(count > 0)
        if self._notif_popover.isVisible():
            self._notif_popover._refresh_list()

    def _on_new_notification(self, title: str, message: str, color: str):
        self._poll_notifications()
        self._toast_manager.show(title, message, color, duration_ms=7000)

    def _on_all_read(self):
        self.topbar.notif_badge.setText("0")
        self.topbar.notif_badge.setVisible(False)

    def _exit_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()