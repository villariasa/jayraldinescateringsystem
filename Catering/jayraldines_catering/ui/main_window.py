from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Signal, QTimer

from components.sidebar import Sidebar
from components.topbar import TopBar
from components.notifications_panel import NotificationPopover, reload_notifications
from components.toast import ToastManager


_PAGE_MODULES = [
    ("ui.dashboard_page",  "DashboardPage"),
    ("ui.booking_page",    "BookingPage"),
    ("ui.customers_page",  "CustomersPage"),
    ("ui.menu_page",       "MenuPage"),
    ("ui.calendar_page",   "CalendarPage"),
    ("ui.kitchen_page",    "KitchenPage"),
    ("ui.billing_page",    "BillingPage"),
    ("ui.reports_page",    "ReportsPage"),
    ("ui.settings_page",   "SettingsPage"),
]


class _PlaceholderPage(QWidget):
    """Lightweight stand-in kept in the stack until the real page is needed."""
    pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Jayraldine's Catering")
        self.resize(1400, 900)

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

        self._pages = [None] * len(_PAGE_MODULES)
        for i in range(len(_PAGE_MODULES)):
            ph = _PlaceholderPage()
            self.stack.addWidget(ph)

        self.right_layout.addWidget(self.stack)
        self.main_layout.addWidget(self.right_widget)

        self.sidebar.page_changed.connect(self._navigate)

        self._notif_popover = NotificationPopover(parent=self)
        self.topbar.notif_btn.clicked.connect(self._open_notif_popover)
        self._notif_popover.all_read.connect(self._on_all_read)

        self._toast_manager = ToastManager()
        self._toast_manager.set_window(self)

        from utils.notif_scheduler import NotifScheduler
        self._scheduler = NotifScheduler(self)
        self._scheduler.new_notification.connect(self._on_new_notification)

        self._last_notif_id = None

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_notifications)
        self._poll_timer.start(5_000)
        QTimer.singleShot(0, self._poll_notifications)

        self._dash_timer = QTimer(self)
        self._dash_timer.timeout.connect(self._reload_dashboard)
        self._dash_timer.start(5_000)

        from utils.signals import app_events
        _ev = app_events()
        _ev.booking_saved.connect(self._on_booking_saved)
        _ev.payment_recorded.connect(self._on_payment_recorded)
        _ev.kitchen_updated.connect(self._on_kitchen_updated)

        self.topbar.search_changed.connect(self._on_search)

        from utils.theme import ThemeManager
        ThemeManager().theme_changed.connect(self._on_theme_changed)

        self._navigate(0)

    def _get_page(self, index: int):
        if self._pages[index] is not None:
            return self._pages[index]

        mod_name, cls_name = _PAGE_MODULES[index]
        import importlib
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
        page = cls()
        self._pages[index] = page

        self.stack.removeWidget(self.stack.widget(index))
        self.stack.insertWidget(index, page)

        if index == 0:
            page.new_booking_requested.connect(lambda: self._navigate(1))
            page.view_all_activity_requested.connect(lambda: self._navigate(1))

        return page

    def _navigate(self, index: int):
        page = self._get_page(index)
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

    def _open_notif_popover(self):
        reload_notifications()
        self._notif_popover.toggle_anchored(self.topbar.notif_btn)

    def _poll_notifications(self):
        from components.notifications_panel import _notifications
        count = reload_notifications()
        self.topbar.notif_badge.setText(str(count))
        self.topbar.notif_badge.setVisible(count > 0)
        if self._notif_popover.isVisible():
            self._notif_popover._refresh_list()
        if _notifications:
            max_id = max(n.get("db_id", 0) for n in _notifications)
            if self._last_notif_id is None:
                self._last_notif_id = max_id
            else:
                new_ones = [n for n in _notifications if n.get("db_id", 0) > self._last_notif_id]
                if new_ones:
                    for n in new_ones:
                        self._toast_manager.show(n["title"], n["message"], n.get("color", "#3B82F6"), duration_ms=7000)
                    self._last_notif_id = max_id
        elif self._last_notif_id is None:
            self._last_notif_id = 0

    def _on_new_notification(self, title: str, message: str, color: str):
        self._poll_notifications()
        self._toast_manager.show(title, message, color, duration_ms=7000)

    def _on_all_read(self):
        self.topbar.notif_badge.setText("0")
        self.topbar.notif_badge.setVisible(False)

    def _reload_dashboard(self):
        if self._pages[0] is not None:
            self._pages[0].reload()

    def _on_booking_saved(self):
        if self._pages[6] is not None:
            self._pages[6].reload()
        if self._pages[5] is not None:
            self._pages[5].reload()
        if self._pages[0] is not None:
            self._pages[0].reload()
        if self._pages[7] is not None:
            self._pages[7].reload()
        self._poll_notifications()

    def _on_payment_recorded(self):
        if self._pages[6] is not None:
            self._pages[6].reload()
        if self._pages[0] is not None:
            self._pages[0].reload()
        self._poll_notifications()

    def _on_kitchen_updated(self):
        if self._pages[0] is not None:
            self._pages[0].reload()
        self._poll_notifications()

    def _on_theme_changed(self, _theme: str):
        current_index = self.stack.currentIndex()
        for i in range(len(self._pages)):
            page = self._pages[i]
            if page is not None:
                self._pages[i] = None
                ph = _PlaceholderPage()
                idx = self.stack.indexOf(page)
                self.stack.insertWidget(idx, ph)
                self.stack.removeWidget(page)
                page.deleteLater()
        self._navigate(current_index)

    @property
    def dashboard_page(self):
        return self._pages[0]

    @property
    def billing_page(self):
        return self._pages[6]

    @property
    def kitchen_page(self):
        return self._pages[5]
