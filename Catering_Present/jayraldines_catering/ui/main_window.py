from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QApplication, QDialog
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Signal, QTimer, Qt, QEvent
import time

from components.sidebar import Sidebar
from components.topbar import TopBar
from components.notifications_panel import NotificationPopover, _notifications as _notif_cache
from components.toast import ToastManager
from utils.data_loader import DataLoader





# ---------------------------------------------------------------------------
# Lazy page-class registry: (module_name, class_name)
# Pages are NOT imported at module level so a DLL failure in one page
# (e.g., QtCharts missing on a target machine) does NOT prevent the rest
# of the application from launching.
# ---------------------------------------------------------------------------
_PAGE_MODULES = [
    ("ui.dashboard_page",  "DashboardPage"),
    ("ui.booking_page",    "BookingPage"),
    ("ui.customers_page",  "CustomersPage"),
    ("ui.menu_page",       "MenuPage"),
    ("ui.calendar_page",   "CalendarPage"),
    ("ui.cash_flow_page",  "CashFlowPage"),
    ("ui.billing_page",    "BillingPage"),
    ("ui.reports_page",    "ReportsPage"),
    ("ui.expenses_page",   "ExpensesPage"),
    ("ui.ai_page",         "AIPage"),
    ("ui.settings_page",   "SettingsPage"),
]

# NOTE: _PAGE_FACTORY removed — all pages are now loaded lazily via _PAGE_MODULES
# to prevent a single DLL failure from crashing the whole application.


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
        self.root_stack = QStackedWidget(self)
        self.setCentralWidget(self.root_stack)

        # Layer 0: Full-Window Unified Auth & Welcome Screen
        from components.unified_auth_welcome import UnifiedAuthWelcome
        self._auth_welcome = UnifiedAuthWelcome(parent=self.root_stack)
        self._auth_welcome.auth_and_welcome_finished.connect(self._on_auth_and_welcome_finished)
        self._auth_welcome.request_prebuild_pages.connect(self._prebuild_all_pages_before_entry)
        self.root_stack.addWidget(self._auth_welcome)

        # Layer 1: Main Application Shell (Sidebar + Topbar + Content Pages)
        self.app_shell = QWidget(self.root_stack)
        self.main_layout = QHBoxLayout(self.app_shell)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.main_layout.addWidget(self.sidebar)

        self.right_widget = QWidget(self.app_shell)
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        self.topbar = TopBar()
        self.right_layout.addWidget(self.topbar)

        self.stack = QStackedWidget(self.right_widget)
        self._pages = [None] * len(_PAGE_MODULES)

        from components.loading_overlay import LoadingOverlay
        self._nav_loader = LoadingOverlay(self.stack, "Loading workspace...")

        self.right_layout.addWidget(self.stack)
        self.main_layout.addWidget(self.right_widget)
        self.root_stack.addWidget(self.app_shell)

        self.sidebar.page_changed.connect(self._navigate)
        self.sidebar.logout_requested.connect(self._handle_logout)
        self.topbar.tab_selected.connect(self._navigate)

        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._trigger_auto_lock)
        self._reset_idle_timer()
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self)

        self._notif_popover = NotificationPopover(parent=self)
        self.topbar.notif_btn.clicked.connect(self._open_notif_popover)
        self._notif_popover.all_read.connect(self._on_all_read)

        self._toast_manager = ToastManager()
        self._toast_manager.set_window(self)

        from utils.notif_scheduler import NotifScheduler
        self._scheduler = NotifScheduler(self)
        self._scheduler.new_notification.connect(self._on_new_notification)

        self._last_notif_id = None
        self._notif_loader = None  # active background loader reference
        self._notif_poll_busy = False  # debounce guard

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_notifications)
        self._poll_timer.start(90_000)   # every 90 s — reduced frequency
        QTimer.singleShot(8_000, self._poll_notifications)  # first check after 8 s

        self._dash_timer = QTimer(self)
        self._dash_timer.timeout.connect(self._reload_dashboard)
        self._dash_timer.start(180_000)  # every 3 min

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
        from components.theme_loading_overlay import ThemeLoadingOverlay
        self._theme_overlay = ThemeLoadingOverlay(parent=self)
        ThemeManager().theme_changing.connect(self._on_theme_changing)
        ThemeManager().theme_changed.connect(self._on_theme_changed)

        from components.global_ai_floating import DraggableMascotWidget
        self._floating_ai = DraggableMascotWidget(parent=self)
        from utils.auth import SessionManager

        self.sidebar.refresh_permissions()
        self.topbar.refresh_permissions()

        if SessionManager.is_logged_in():
            self.root_stack.setCurrentWidget(self.app_shell)
            self._floating_ai.setVisible(SessionManager.has_permission("ai_chef_jay", "view"))
            self._floating_ai.show()
            self._floating_ai.raise_()
            self._navigate(0)
            QTimer.singleShot(400, self._show_welcome_greeting)
        else:
            self._floating_ai.hide()
            self.root_stack.setCurrentWidget(self._auth_welcome)

    def _prebuild_all_pages_before_entry(self):
        """
        Pre-builds Dashboard workspace and enters the system smoothly.
        Other modules load lazily on first tab click with smooth circular spinners.
        """
        try:
            if hasattr(self, "_auth_welcome") and self._auth_welcome:
                self._auth_welcome.update_progress("⚙️  Preparing Dashboard workspace...", 92)
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
            if self._pages[0] is None:
                self._get_page(0)
                if app:
                    app.processEvents()
        except Exception as exc:
            print(f"[MainWindow] Pre-building Dashboard error: {exc}")

        if hasattr(self, "_auth_welcome") and self._auth_welcome:
            self._auth_welcome.update_progress("🚀  All workspaces ready! Entering system...", 100)
            app = QApplication.instance()
            if app:
                app.processEvents()
            QTimer.singleShot(150, self._auth_welcome.finish_and_fade_out)
        else:
            self._on_auth_and_welcome_finished()


    def _on_auth_and_welcome_finished(self):
        self.root_stack.setCurrentWidget(self.app_shell)
        self._reload_user_session()
        self._navigate(0)

    def _show_welcome_greeting(self):
        from utils.auth import SessionManager
        user = SessionManager.current_user() or {}
        name = user.get("display_name") or user.get("username", "Admin")
        role = (user.get("role") or "staff")
        role_label = "Administrator" if role.lower() == "admin" else role.capitalize()
        self._toast_manager.show(
            f"Welcome, {name}!",
            f"Signed in as {role_label}. All authorized modules are loaded.",
            color="#10B981",
            duration_ms=4500
        )

    def _start_page_prewarming(self):
        """
        Background pre-warming that silently instantiates and pre-fetches all authorized pages
        so that subsequent tab clicks are 0ms instant with zero loading screens.
        """
        from utils.auth import SessionManager
        if not SessionManager.is_logged_in():
            return

        unloaded = [
            i for i in range(len(self._pages))
            if self._pages[i] is None and i != 9  # Skip AI assistant page unless clicked
        ]

        def _warm_step(idx_pos=0):
            if idx_pos >= len(unloaded):
                return
            target_idx = unloaded[idx_pos]
            perm_key = self.PAGE_MODULE_PERM.get(target_idx, "dashboard")
            if target_idx == 0 or SessionManager.has_permission(perm_key, "view"):
                try:
                    p = self._get_page(target_idx)
                    # Silently warm up data if page has a reload/do_reload method and is dirty
                    if p and getattr(p, "_dirty", False):
                        if hasattr(p, "reload"):
                            p.reload()
                        elif hasattr(p, "_do_reload"):
                            p._do_reload()
                except Exception as exc:
                    print(f"[MainWindow] Prewarming tab {target_idx} notice: {exc}")
            QTimer.singleShot(100, lambda: _warm_step(idx_pos + 1))

        QTimer.singleShot(150, lambda: _warm_step(0))

    def _get_page(self, index: int):
        if self._pages[index] is not None:
            return self._pages[index]

        mod_name, cls_name = _PAGE_MODULES[index] if index < len(_PAGE_MODULES) else ("unknown", "Page")
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            # Pass parent=self.stack so Qt never creates or exposes a top-level native OS window
            try:
                page = cls(parent=self.stack)
            except TypeError:
                page = cls()
                page.setParent(self.stack)
        except Exception as exc:
            import traceback
            import sys
            tb_str = traceback.format_exc()

            # Log full details to file — essential for diagnosing DLL failures on other machines
            try:
                from utils.logger import get_logger
                _log = get_logger()
                try:
                    from PySide6 import __version__ as _ps6_ver
                except Exception:
                    _ps6_ver = "unknown"
                try:
                    from PySide6.QtCore import qVersion
                    _qt_ver = qVersion()
                except Exception:
                    _qt_ver = "unknown"
                import platform
                _log.error(
                    f"PAGE LOAD FAILURE — {mod_name}.{cls_name}\n"
                    f"Error Type   : {type(exc).__name__}\n"
                    f"Error Message: {exc}\n"
                    f"Python       : {sys.version}\n"
                    f"PySide6      : {_ps6_ver}\n"
                    f"Qt           : {_qt_ver}\n"
                    f"Platform     : {platform.system()} {platform.release()} {platform.version()}\n"
                    f"Architecture : {platform.machine()}\n"
                    f"Executable   : {sys.executable}\n"
                    f"Full Traceback:\n{tb_str}"
                )
            except Exception as log_err:
                print(f"[MainWindow] Could not write to logger: {log_err}")

            print(f"[MainWindow] PAGE LOAD FAILURE — {mod_name}.{cls_name}: {exc}")
            print(tb_str)

            from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
            page = QWidget(parent=self.stack)
            err_lay = QVBoxLayout(page)
            err_lay.setContentsMargins(24, 24, 24, 24)
            err_lay.setSpacing(12)

            # Friendly error title
            title_lbl = QLabel(f"⚠️ Unable to load '{cls_name}'")
            title_lbl.setStyleSheet("color: #EF4444; font-size: 15px; font-weight: 700; padding: 0;")
            err_lay.addWidget(title_lbl)

            # Error message
            err_lbl = QLabel(f"{type(exc).__name__}: {exc}")
            err_lbl.setStyleSheet("color: #F87171; font-size: 13px; padding: 0;")
            err_lbl.setWordWrap(True)
            err_lay.addWidget(err_lbl)

            # Full traceback in scrollable area
            tb_lbl = QLabel(tb_str)
            tb_lbl.setStyleSheet(
                "color: #94A3B8; font-family: monospace; font-size: 11px; "
                "background: #0F172A; padding: 12px; border-radius: 6px;"
            )
            tb_lbl.setWordWrap(True)
            tb_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            scroll = QScrollArea()
            scroll.setWidget(tb_lbl)
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(300)
            scroll.setStyleSheet("background: #0F172A; border: 1px solid #334155; border-radius: 6px;")
            err_lay.addWidget(scroll)

            hint_lbl = QLabel(
                "💡 If you see 'DLL load failed': A required Qt library is missing on this computer.\n"
                "   Please run the Diagnostic Report (Settings → Diagnostic Report) and send it to support."
            )
            hint_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; padding: 4px 0;")
            hint_lbl.setWordWrap(True)
            err_lay.addWidget(hint_lbl)
            err_lay.addStretch()

        self._pages[index] = page
        self.stack.addWidget(page)

        if index == 0:
            if hasattr(page, "new_booking_requested"):
                page.new_booking_requested.connect(lambda: self._navigate(1))
            if hasattr(page, "view_all_activity_requested"):
                page.view_all_activity_requested.connect(lambda: self._navigate(1))
            if hasattr(page, "ai_requested"):
                page.ai_requested.connect(lambda: self._navigate(9))

        return page

    PAGE_MODULE_PERM = {
        0: "dashboard",
        1: "bookings",
        2: "customers",
        3: "menu",
        4: "bookings",
        5: "cashflow",
        6: "cashflow",
        7: "reports",
        8: "expenses",
        9: "ai_chef_jay",
        10: "settings",
    }

    def _navigate(self, index: int):
        from utils.auth import SessionManager
        perm_key = self.PAGE_MODULE_PERM.get(index, "dashboard")
        # Dashboard (index 0) is always allowed for all logged in users
        if index != 0 and SessionManager.is_logged_in():
            if not SessionManager.has_permission(perm_key, "view"):
                disp_name = perm_key.replace("_", " ").title()
                if perm_key == "ai_chef_jay":
                    disp_name = "AI Assistant"
                self._toast_manager.show(
                    "Access Denied",
                    f"Your account does not have permission to access the {disp_name} module.",
                    color="#EF4444"
                )
                return

        PAGE_TITLES = {
            0: "Dashboard", 1: "Bookings", 2: "Customers", 3: "Menu Items",
            4: "Calendar", 5: "Kitchen Orders", 6: "Billing & Invoices",
            7: "Reports & Analytics", 8: "Expenses", 9: "AI Chef Jay", 10: "Settings"
        }
        mod_name = PAGE_TITLES.get(index, "Workspace")
        first_time = self._pages[index] is None
        if first_time and hasattr(self, "_nav_loader"):
            self._nav_loader.show_overlay(f"Opening {mod_name}...")
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
            # Defer heavy construction by 25ms so Qt starts the circling animation smoothly and never freezes
            QTimer.singleShot(25, lambda: self._do_navigate(index, mod_name, first_time=True))
            return

        self._do_navigate(index, mod_name, first_time=False)

    def _do_navigate(self, index: int, mod_name: str, first_time: bool = False):
        PAGE_TITLES = {
            0: "Dashboard", 1: "Bookings", 2: "Customers", 3: "Menu Items",
            4: "Calendar", 5: "Kitchen Orders", 6: "Billing & Invoices",
            7: "Reports & Analytics", 8: "Expenses", 9: "AI Chef Jay", 10: "Settings"
        }
        page = self._get_page(index)
        
        self.stack.setUpdatesEnabled(False)
        try:
            self.stack.setCurrentWidget(page)
            self.topbar.set_page(index)
            self.sidebar.handle_click(index)
            if hasattr(page, "refresh_permissions"):
                try:
                    page.refresh_permissions()
                except Exception:
                    pass
            # Only reload if the page has been explicitly flagged dirty by data change signals
            if not first_time and getattr(page, "_dirty", False):
                try:
                    page.reload()
                except Exception as exc:
                    print(f"[MainWindow] Error reloading page {index}: {exc}")
            if hasattr(self, "_floating_ai") and self._floating_ai:
                from utils.auth import SessionManager
                self._floating_ai.setVisible(index != 9 and SessionManager.has_permission("ai_chef_jay", "view"))

            # Reset scroll position to top whenever navigating to any page
            self._reset_page_scroll(page)
            QTimer.singleShot(0, lambda p=page: self._reset_page_scroll(p))
            QTimer.singleShot(60, lambda p=page: self._reset_page_scroll(p))

            # Telemetry: Update active screen on server
            try:
                from utils.device_tracker import device_tracker
                device_tracker().set_active_module(PAGE_TITLES.get(index, "Dashboard"))
            except Exception:
                pass
        finally:
            self.stack.setUpdatesEnabled(True)
            if first_time and hasattr(self, "_nav_loader"):
                QTimer.singleShot(75, self._nav_loader.hide_overlay)


    def _reset_page_scroll(self, page):
        """Resets all scrollbars inside the page to top (0) so switching tabs always starts at the top."""
        if not page:
            return
        try:
            from PySide6.QtWidgets import QAbstractScrollArea
            if isinstance(page, QAbstractScrollArea):
                vbar = page.verticalScrollBar()
                if vbar:
                    vbar.setValue(0)
                hbar = page.horizontalScrollBar()
                if hbar:
                    hbar.setValue(0)

            for sa in page.findChildren(QAbstractScrollArea):
                try:
                    vbar = sa.verticalScrollBar()
                    if vbar:
                        vbar.setValue(0)
                    hbar = sa.horizontalScrollBar()
                    if hbar:
                        hbar.setValue(0)
                except Exception:
                    pass

            if hasattr(page, "reset_scroll") and callable(page.reset_scroll):
                try:
                    page.reset_scroll()
                except Exception:
                    pass
            elif hasattr(page, "scroll_to_top") and callable(page.scroll_to_top):
                try:
                    page.scroll_to_top()
                except Exception:
                    pass
        except Exception as exc:
            print(f"[MainWindow] _reset_page_scroll note: {exc}")

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel):
            self._reset_idle_timer(force=True)
        elif event.type() == QEvent.MouseMove:
            self._reset_idle_timer(force=False)
        return super().eventFilter(obj, event)

    def _reset_idle_timer(self, force: bool = False):
        now = time.monotonic()
        last = getattr(self, "_last_idle_reset_time", 0.0)
        # Avoid lock acquisition and timer restarts on every single mouse pixel movement
        if not force and (now - last) < 10.0:
            return
        self._last_idle_reset_time = now
        from utils.auth import SessionManager
        mins = SessionManager.get_auto_lock_minutes()
        if mins <= 0:
            self._idle_timer.stop()
        else:
            self._idle_timer.start(mins * 60 * 1000)

    def _trigger_auto_lock(self):
        from utils.auth import SessionManager
        if not SessionManager.is_logged_in():
            return
        self._idle_timer.stop()
        from components.login_dialog import LockScreenDialog
        dlg = LockScreenDialog(self)
        dlg.exec()
        self._reset_idle_timer()

    def _handle_logout(self):
        from components.dialogs import confirm
        from utils.auth import SessionManager
        if not confirm(self, "Sign Out", "Are you sure you want to sign out?"):
            return
        SessionManager.logout()
        if hasattr(self, "_floating_ai") and self._floating_ai:
            self._floating_ai.hide()
        if hasattr(self, "_auth_welcome") and self._auth_welcome:
            self._auth_welcome.reset_to_login()
            self.root_stack.setCurrentWidget(self._auth_welcome)

    def _reload_user_session(self):
        self.sidebar.refresh_permissions()
        self.topbar.refresh_permissions()
        self._reset_idle_timer()
        if hasattr(self, "_floating_ai") and self._floating_ai:
            from utils.auth import SessionManager
            self._floating_ai.setVisible(SessionManager.has_permission("ai_chef_jay", "view"))
        if len(self._pages) > 10 and self._pages[10] is not None:
            p = self._pages[10]
            if hasattr(p, "reload"):
                p.reload()
        self._navigate(0)
        self._show_welcome_greeting()

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
        # Open panel immediately with cached data; async refresh in background
        self._notif_popover.toggle_anchored(self.topbar.notif_btn)
        self._poll_notifications()

    def _poll_notifications(self):
        """Kick off async notification reload ΓÇö NEVER blocks the main thread."""
        if self._notif_poll_busy:
            return  # previous fetch still in progress
        if self._notif_loader is not None and self._notif_loader.isRunning():
            return
        self._notif_poll_busy = True

        from components.notifications_panel import _load_notifications

        def _bg_load():
            return _load_notifications()

        loader = DataLoader(_bg_load)
        loader.data_ready.connect(self._on_notif_data_ready)
        loader.load_error.connect(lambda _e: self._finish_notif_poll())
        self._notif_loader = loader
        loader.start()

    def _on_notif_data_ready(self, fresh):
        """Called on main thread after background notification fetch completes."""
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass

        from components.notifications_panel import _notifications
        _notifications.clear()
        _notifications.extend(fresh or [])
        count = len(_notifications)

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

        self._finish_notif_poll()

    def _finish_notif_poll(self):
        self._notif_poll_busy = False

    def _on_new_notification(self, title: str, message: str, color: str):
        # Schedule an async poll ΓÇö don't call synchronously
        QTimer.singleShot(500, self._poll_notifications)
        self._toast_manager.show(title, message, color, duration_ms=7000)

    def _on_all_read(self):
        self.topbar.notif_badge.setText("0")
        self.topbar.notif_badge.setVisible(False)

    def _smart_reload(self, index: int):
        """Mark page[index] dirty. If it is the currently visible page, also
        call reload() immediately. Otherwise the page will self-reload when
        the user navigates to it (via its showEvent / _dirty check)."""
        p = self._pages[index] if index < len(self._pages) else None
        if p is None:
            return  # page not yet created ΓÇö nothing to do
        # Mark dirty regardless
        if hasattr(p, "_mark_dirty"):
            p._mark_dirty()
        elif hasattr(p, "_dirty"):
            p._dirty = True
        # Immediately reload only if currently shown
        if self.stack.currentIndex() == index and hasattr(p, "reload"):
            try:
                p.reload()
            except Exception as exc:
                print(f"[MainWindow] _smart_reload({index}) error: {exc}")

    def _reload_dashboard(self):
        self._smart_reload(0)

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
        self._smart_reload(6)   # BillingPage
        self._smart_reload(0)   # DashboardPage
        self._smart_reload(7)   # ReportsPage
        self._poll_notifications()

    def _on_kitchen_updated(self):
        self._smart_reload(0)   # DashboardPage reflects kitchen changes
        self._poll_notifications()

    def _on_expense_saved(self):
        self._smart_reload(8)   # ExpensesPage
        self._smart_reload(0)   # DashboardPage
        self._smart_reload(7)   # ReportsPage
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

    def _on_theme_changing(self, palette_id: str):
        if hasattr(self, "_theme_overlay") and self._theme_overlay:
            from utils.palette import THEME_PALETTES
            pal = THEME_PALETTES.get(palette_id, {})
            name = pal.get("name", "Theme")
            self._theme_overlay.show_loading(f"Switching to {name}...", "Updating color palette & UI styles...")

    def _on_theme_changed(self, _theme: str):
        # In-place dynamic styling: keep all page instances and data in memory
        if hasattr(self, "sidebar"):
            self.sidebar.refresh_permissions()
        if hasattr(self, "topbar"):
            self.topbar.refresh_permissions()

        # Notify loaded pages if they have theme hook methods
        for p in self._pages:
            if p is not None:
                if hasattr(p, "_apply_theme_styles"):
                    try:
                        p._apply_theme_styles()
                    except Exception as e:
                        print(f"[MainWindow] Error applying theme styles on page: {e}")
                elif hasattr(p, "_on_theme_changed"):
                    try:
                        p._on_theme_changed(_theme)
                    except Exception as e:
                        print(f"[MainWindow] Error in _on_theme_changed on page: {e}")

        # Smooth animated dismissal of loading overlay after fluid rotation
        if hasattr(self, "_theme_overlay") and self._theme_overlay and self._theme_overlay.isVisible():
            QTimer.singleShot(80, lambda: self._theme_overlay.hide_loading(animated=True))

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
        if hasattr(self, "_theme_overlay") and self._theme_overlay and self._theme_overlay.isVisible():
            self._theme_overlay.resize(self.size())
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

    def closeEvent(self, event):
        # Stop floating AI threads/timers
        if hasattr(self, "_floating_ai") and self._floating_ai:
            try:
                self._floating_ai.hide()
                if hasattr(self._floating_ai, "_stop_thread"):
                    self._floating_ai._stop_thread()
            except Exception:
                pass

        # Stop any active background data loaders on pages
        for p in getattr(self, "_pages", []):
            if p is not None and hasattr(p, "_active_loaders"):
                try:
                    for loader in list(p._active_loaders):
                        if hasattr(loader, "quit"):
                            loader.quit()
                            loader.wait(300)
                    p._active_loaders.clear()
                except Exception:
                    pass

        super().closeEvent(event)
