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
    ("ui.expenses_page",   "ExpensesPage"),
    ("ui.ai_page",         "AIPage"),
    ("ui.settings_page",   "SettingsPage"),
]


class _PlaceholderPage(QWidget):
    """Lightweight stand-in kept in the stack until the real page is needed."""
    pass


from version import __version__, APP_NAME


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.setMinimumSize(1024, 600)
        self.resize(1280, 768)

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
        self.topbar.tab_selected.connect(self._navigate)

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
        self._poll_timer.start(30_000)
        QTimer.singleShot(2_000, self._poll_notifications)

        self._dash_timer = QTimer(self)
        self._dash_timer.timeout.connect(self._reload_dashboard)
        self._dash_timer.start(120_000)  # every 2 min instead of 1 min

        from utils.signals import app_events
        _ev = app_events()
        _ev.booking_saved.connect(self._on_booking_saved)
        _ev.payment_recorded.connect(self._on_payment_recorded)
        _ev.kitchen_updated.connect(self._on_kitchen_updated)
        _ev.expense_saved.connect(self._on_expense_saved)
        _ev.customer_saved.connect(self._on_customer_saved)
        _ev.data_changed.connect(self._reload_all_pages)

        from utils.reminder_manager import reminder_manager
        reminder_manager().alarm_fired.connect(self._on_alarm_fired)

        self.topbar.search_changed.connect(self._on_search)

        from utils.theme import ThemeManager
        ThemeManager().theme_changed.connect(self._on_theme_changed)

        from components.global_ai_floating import DraggableMascotWidget
        self._floating_ai = DraggableMascotWidget(parent=self)
        self._floating_ai.show()
        self._floating_ai.raise_()

        self._navigate(0)

        # Pre-construct remaining pages in the background during idle time (0ms tab switches)
        QTimer.singleShot(250, self._warmup_pages)

    def _warmup_pages(self):
        """Pre-construct pages sequentially so clicks on any module never wait for cold-start UI building."""
        for idx in range(len(_PAGE_MODULES)):
            if self._pages[idx] is None:
                self._get_page(idx)

    def _get_page(self, index: int):
        if self._pages[index] is not None:
            return self._pages[index]

        mod_name, cls_name = _PAGE_MODULES[index]
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            page = cls()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"[MainWindow] Error loading page {mod_name}.{cls_name}: {exc}")
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
            page = QWidget()
            err_lay = QVBoxLayout(page)
            err_lbl = QLabel(f"Unable to load page '{cls_name}':\n{exc}")
            err_lbl.setStyleSheet("color: #EF4444; font-size: 14px; padding: 24px;")
            err_lay.addWidget(err_lbl)

        self._pages[index] = page

        self.stack.removeWidget(self.stack.widget(index))
        self.stack.insertWidget(index, page)

        if index == 0:
            if hasattr(page, "new_booking_requested"):
                page.new_booking_requested.connect(lambda: self._navigate(1))
            if hasattr(page, "view_all_activity_requested"):
                page.view_all_activity_requested.connect(lambda: self._navigate(1))
            if hasattr(page, "ai_requested"):
                page.ai_requested.connect(lambda: self._navigate(9))

        return page

    def _navigate(self, index: int):
        first_time = self._pages[index] is None
        page = self._get_page(index)
        self.stack.setCurrentIndex(index)
        self.topbar.set_page(index)
        self.sidebar.handle_click(index)
        if not first_time and hasattr(page, "reload"):
            try:
                page.reload()
            except Exception as exc:
                print(f"[MainWindow] Error reloading page {index}: {exc}")
        if hasattr(self, "_floating_ai") and self._floating_ai:
            self._floating_ai.setVisible(index != 9)

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
        # Reload booking page if visible; mark others dirty for lazy reload
        for idx in [1, 4, 5, 6, 0, 7]:
            p = self._pages[idx] if idx < len(self._pages) else None
            if p is None:
                continue
            if hasattr(p, "_mark_dirty"):
                p._mark_dirty()
            elif hasattr(p, "_dirty"):
                p._dirty = True
        # Immediately reload only the currently visible page
        cur = self.stack.currentIndex()
        p = self._pages[cur] if cur < len(self._pages) else None
        if p is not None and hasattr(p, "reload"):
            try:
                p.reload()
            except Exception:
                pass
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

    def _on_expense_saved(self):
        if self._pages[8] is not None:  # ExpensesPage
            self._pages[8].reload()
        if self._pages[0] is not None:  # DashboardPage
            self._pages[0].reload()
        if self._pages[7] is not None:  # ReportsPage
            self._pages[7].reload()
        self._poll_notifications()

    def _on_customer_saved(self):
        for idx in [2, 1, 0]:
            p = self._pages[idx] if idx < len(self._pages) else None
            if p is None:
                continue
            if hasattr(p, "_mark_dirty"):
                p._mark_dirty()
            elif hasattr(p, "_dirty"):
                p._dirty = True
        cur = self.stack.currentIndex()
        p = self._pages[cur] if cur < len(self._pages) else None
        if p is not None and hasattr(p, "reload"):
            try:
                p.reload()
            except Exception:
                pass
        self._poll_notifications()

    def _reload_all_pages(self):
        """Only reload the current visible page; mark all others dirty so they
        refresh lazily when the user navigates to them."""
        current_idx = self.stack.currentIndex()
        for i, p in enumerate(self._pages):
            if p is None:
                continue
            if hasattr(p, "_mark_dirty"):
                p._mark_dirty()
            elif hasattr(p, "_dirty"):
                p._dirty = True
            if i == current_idx and hasattr(p, "reload"):
                try:
                    p.reload()
                except Exception as exc:
                    print(f"[MainWindow] Error reloading page {i}: {exc}")
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

    def _on_alarm_fired(self, entry: dict):
        msg = entry.get("message", "Alarm")
        target_dt = entry.get("target_dt")
        time_str = target_dt.strftime("%I:%M %p").lstrip("0") if target_dt else datetime.now().strftime("%I:%M %p")
        self._toast_manager.show("⏰ Alarm / Reminder", f"{msg} ({time_str})", color="#F59E0B", duration_ms=12000)

        # Animate mascot and display speech bubble
        if hasattr(self, "_floating_ai") and self._floating_ai and hasattr(self._floating_ai, "mascot"):
            m = self._floating_ai.mascot
            m.set_state("surprised")
            if hasattr(m, "speak"):
                m.speak(f"⏰ Alarm: {msg}!\n(Say 'snooze 5m' or 'dismiss')", 12000)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_floating_ai") and self._floating_ai:
            if not getattr(self._floating_ai, "_user_moved", False):
                x = self.width() - self._floating_ai.width() - 24
                y = self.height() - self._floating_ai.height() - 24
                self._floating_ai.move(max(0, x), max(0, y))
                self._floating_ai.raise_()

    @property
    def dashboard_page(self):
        return self._pages[0]

    @property
    def billing_page(self):
        return self._pages[6]

    @property
    def kitchen_page(self):
        return self._pages[5]
