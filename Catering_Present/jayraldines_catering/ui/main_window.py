"""
Main application window for the Jayraldine's Catering desktop app.

This module defines :class:`MainWindow`, the top-level QMainWindow that hosts
the entire UI shell. Responsibilities include:

* A two-layer root stack: (0) the unified auth / welcome screen and
  (1) the main application shell (sidebar + topbar + page stack).
* Lazy construction of feature pages (see ``_PAGE_MODULES``) so that a single
  failing/optional page (e.g. a missing Qt DLL) never crashes the whole app.
* Permission-gated navigation between pages via the sidebar and topbar.
* Idle-based auto-lock, background notification polling, periodic dashboard
  refresh, theme switching, toasts, and the floating AI mascot.
* Reacting to cross-app data-change signals (bookings, payments, expenses,
  etc.) by marking pages "dirty" and reloading the visible one.

Side effects: installs a global application event filter (for idle tracking),
starts several QTimers, and connects to many app-wide signal buses.
"""
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
    """Top-level window and controller for the whole application.

    Owns the sidebar, topbar, the stacked feature pages, and the global
    services (notifications, toasts, idle auto-lock, theme overlay, floating
    AI). Pages are created lazily on first navigation; on construction it
    decides whether to show the auth/welcome screen or jump straight into the
    app shell based on the existing login session.
    """
    def __init__(self):
        """Build the full UI shell, wire up signals/timers, and show the
        correct initial screen (app shell if already logged in, otherwise the
        auth/welcome screen)."""
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.setMinimumSize(1024, 600)
        self.resize(1280, 768)

        # Global fullscreen toggles: F11 enters/exits, Esc leaves fullscreen.
        self.shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        self.shortcut_f11.activated.connect(self._toggle_fullscreen)
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self._exit_fullscreen)
        # root_stack swaps between the auth/welcome screen (layer 0) and the
        # main app shell (layer 1); it is the window's central widget.
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
        # Parallel slot list to _PAGE_MODULES: each entry is None until that
        # page is lazily instantiated by _get_page(); index == page id.
        self._pages = [None] * len(_PAGE_MODULES)

        from components.loading_overlay import LoadingOverlay
        self._nav_loader = LoadingOverlay(self.stack, "Loading workspace...")

        self.right_layout.addWidget(self.stack)
        self.main_layout.addWidget(self.right_widget)
        self.root_stack.addWidget(self.app_shell)

        # Navigation requests can come from either the sidebar or the topbar.
        self.sidebar.page_changed.connect(self._navigate)
        self.sidebar.logout_requested.connect(self._handle_logout)
        self.topbar.tab_selected.connect(self._navigate)

        # Idle auto-lock: the timer fires after the configured inactivity
        # window; an app-wide event filter resets it on user input.
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

        # Notification state: track the highest-seen id so only genuinely new
        # notifications raise toasts; the loader/busy fields guard concurrency.
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

        # Subscribe to the app-wide event bus so any part of the app that
        # mutates data can trigger targeted page reloads here.
        from utils.signals import app_events
        _ev = app_events()
        _ev.booking_saved.connect(self._on_booking_saved)
        _ev.booking_updated.connect(self._on_booking_saved)
        _ev.booking_created.connect(self._on_booking_saved)
        _ev.payment_recorded.connect(self._on_payment_recorded)
        _ev.kitchen_updated.connect(self._on_kitchen_updated)
        _ev.expense_saved.connect(self._on_expense_saved)
        _ev.customer_saved.connect(self._on_customer_saved)
        _ev.invoice_saved.connect(self._on_sync_completed)
        _ev.data_changed.connect(self._on_sync_completed)
        _ev.sync_started.connect(self._on_sync_started)
        _ev.sync_completed.connect(self._on_sync_completed)

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

        # If a session is already active (e.g. app relaunch), skip the auth
        # screen and go straight into the dashboard; otherwise show login.
        if SessionManager.is_logged_in():
            self.root_stack.setCurrentWidget(self.app_shell)
            can_view_ai = SessionManager.has_permission("ai_chef_jay", "view")
            self._floating_ai.setVisible(can_view_ai)
            self._floating_ai.show()
            self._floating_ai.raise_()
            self._navigate(0)
            QTimer.singleShot(400, self._show_welcome_greeting)
            if can_view_ai:
                QTimer.singleShot(1500, self._floating_ai.check_and_show_morning_briefing)
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
        """Swap from the auth/welcome layer to the app shell once login and the
        welcome animation complete, then reload the session and open the
        dashboard (index 0)."""
        self.root_stack.setCurrentWidget(self.app_shell)
        self._reload_user_session()
        self._navigate(0)

    def _show_welcome_greeting(self):
        """Show a transient 'Welcome, <name>!' toast identifying the signed-in
        user and their role label."""
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
        """Return the page widget for ``index``, importing and instantiating it
        lazily on first request.

        The target module/class comes from ``_PAGE_MODULES``. If import or
        construction fails (commonly a missing Qt DLL on a target machine), a
        self-contained error placeholder widget with the full traceback is
        substituted so the rest of the app keeps working. The created widget is
        cached in ``self._pages`` and added to the page stack.

        Side effects: caches the page, adds it to ``self.stack``, logs failures,
        and wires dashboard-specific signals when ``index == 0``.
        """
        # Return the cached instance if this page was already built.
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

        # Cache the (real or placeholder) page and register it with the stack.
        self._pages[index] = page
        self.stack.addWidget(page)

        # Dashboard (index 0) emits cross-page navigation requests; forward
        # them to the matching page indices.
        if index == 0:
            if hasattr(page, "new_booking_requested"):
                page.new_booking_requested.connect(lambda: self._navigate(1))
            if hasattr(page, "view_all_activity_requested"):
                page.view_all_activity_requested.connect(lambda: self._navigate(1))
            if hasattr(page, "ai_requested"):
                page.ai_requested.connect(lambda: self._navigate(9))

        return page

    # Maps a page index to the permission module key checked before allowing
    # navigation to that page (see _navigate / _start_page_prewarming).
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
        """Switch the visible page to ``index`` after a permission check.

        Dashboard (0) is always allowed; any other page requires the logged-in
        user to hold "view" on its permission key, otherwise an "Access Denied"
        toast is shown and navigation is aborted. On first-ever open of a page
        a loading overlay is displayed and the heavy construction is deferred a
        few ms so the spinner animates smoothly; subsequent visits switch
        instantly via :meth:`_do_navigate`.
        """
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
        """Perform the actual page switch: build/fetch the page, make it current,
        sync sidebar/topbar highlight, refresh its permissions, reload it if it
        was flagged dirty, toggle the floating AI, reset scroll to top, and
        report the active module for telemetry.

        ``first_time`` indicates this is the page's first open (drives the
        loading overlay lifecycle and skips the dirty-reload)."""
        PAGE_TITLES = {
            0: "Dashboard", 1: "Bookings", 2: "Customers", 3: "Menu Items",
            4: "Calendar", 5: "Kitchen Orders", 6: "Billing & Invoices",
            7: "Reports & Analytics", 8: "Expenses", 9: "AI Chef Jay", 10: "Settings"
        }
        page = self._get_page(index)

        # Freeze repaints while we reconfigure the stack to avoid flicker.
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
        """Application-wide event filter that treats user input as activity and
        resets the idle auto-lock timer. Discrete input (clicks, keys, wheel)
        forces a reset; continuous mouse movement uses the throttled path.
        Always defers to the base implementation afterwards."""
        if event.type() in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel):
            self._reset_idle_timer(force=True)
        elif event.type() == QEvent.MouseMove:
            self._reset_idle_timer(force=False)
        return super().eventFilter(obj, event)

    def _reset_idle_timer(self, force: bool = False):
        """(Re)start the idle auto-lock timer based on the configured lock
        minutes. When ``force`` is False, resets are throttled to at most once
        per 10s so mouse-move spam doesn't thrash the timer. A lock setting of
        0 (or less) disables auto-lock and stops the timer."""
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
        """Fired when the idle timer elapses: if a user is logged in, present a
        modal lock screen requiring re-authentication, then restart idle
        tracking once it is dismissed. No-op when nobody is logged in."""
        from utils.auth import SessionManager
        if not SessionManager.is_logged_in():
            return
        self._idle_timer.stop()
        from components.login_dialog import LockScreenDialog
        dlg = LockScreenDialog(self)
        dlg.exec()
        self._reset_idle_timer()

    def _handle_logout(self):
        """Confirm intent, then log the user out: clear the session, hide the
        floating AI, and return to the login screen."""
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
        """Re-apply the current user's context after login/session change:
        refresh sidebar/topbar permissions, restart idle tracking, update the
        floating AI visibility (and schedule its morning briefing), reload the
        settings page if built, then open the dashboard and greet the user."""
        self.sidebar.refresh_permissions()
        self.topbar.refresh_permissions()
        self._reset_idle_timer()
        if hasattr(self, "_floating_ai") and self._floating_ai:
            from utils.auth import SessionManager
            can_view_ai = SessionManager.has_permission("ai_chef_jay", "view")
            self._floating_ai.setVisible(can_view_ai)
            if can_view_ai:
                QTimer.singleShot(1500, self._floating_ai.check_and_show_morning_briefing)
        if len(self._pages) > 10 and self._pages[10] is not None:
            p = self._pages[10]
            if hasattr(p, "reload"):
                p.reload()
        self._navigate(0)
        self._show_welcome_greeting()

    def _on_search(self, text):
        """Handle topbar search text changes with a 500ms debounce so the
        current page's ``filter_search`` runs once the user pauses typing,
        rather than on every keystroke."""
        # Debounce: without this, every page whose filter_search() does a
        # full clear-and-rebuild (e.g. Billing, Menu) reruns that on every
        # single keystroke - typing a short word could trigger it 5+ times
        # in a row, which is what made search feel laggy.
        self._pending_search_text = text
        if not hasattr(self, "_search_debounce_timer"):
            self._search_debounce_timer = QTimer(self)
            self._search_debounce_timer.setSingleShot(True)
            self._search_debounce_timer.timeout.connect(self._dispatch_search)
        self._search_debounce_timer.start(500)

    def _dispatch_search(self):
        """Debounce callback: forward the pending search text to the currently
        visible page if it supports ``filter_search``."""
        page = self.stack.currentWidget()
        if hasattr(page, "filter_search"):
            page.filter_search(self._pending_search_text)

    def _toggle_fullscreen(self):
        """F11 handler: leave fullscreen (back to maximized) if in it, else
        enter fullscreen."""
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _exit_fullscreen(self):
        """Esc handler: drop out of fullscreen to maximized (no-op otherwise)."""
        if self.isFullScreen():
            self.showMaximized()

    def _open_notif_popover(self):
        """Toggle the notifications popover anchored to the topbar bell, showing
        cached items instantly while a fresh fetch runs in the background."""
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

        self.topbar.notif_badge.setText(str(count) if count <= 99 else "99+")
        self.topbar.notif_badge.setVisible(count > 0)
        if self._notif_popover.isVisible():
            self._notif_popover._refresh_list()

        if _notifications:
            # db_id can arrive as a string when proxied from a client-mode
            # server (JSON round-trip), so coerce before comparing.
            max_id = max(int(n.get("db_id", 0) or 0) for n in _notifications)
            if self._last_notif_id is None:
                self._last_notif_id = max_id
            else:
                new_ones = [n for n in _notifications if int(n.get("db_id", 0) or 0) > self._last_notif_id]
                if new_ones:
                    for n in new_ones:
                        self._toast_manager.show(n["title"], n["message"], n.get("color", "#3B82F6"), duration_ms=7000)
                    self._last_notif_id = max_id
        elif self._last_notif_id is None:
            self._last_notif_id = 0

        self._finish_notif_poll()

    def _finish_notif_poll(self):
        """Release the notification poll busy-guard so the next poll can run."""
        self._notif_poll_busy = False

    def _on_new_notification(self, title: str, message: str, color: str):
        """Handle a live notification pushed by the scheduler: pop a toast now
        and schedule a background poll to refresh the badge/list."""
        # Schedule an async poll ΓÇö don't call synchronously
        QTimer.singleShot(500, self._poll_notifications)
        self._toast_manager.show(title, message, color, duration_ms=7000)

    def _on_all_read(self):
        """Clear the topbar unread badge after the user marks all
        notifications read."""
        self.topbar.notif_badge.setText("0")
        self.topbar.notif_badge.setVisible(False)

    def _smart_reload(self, index: int):
        """Mark page[index] dirty. If it is the currently visible page, also
        call reload() immediately. Otherwise the page will self-reload when
        the user navigates to it (via its showEvent / _dirty check)."""
        p = self._pages[index] if index < len(self._pages) else None
        if p is None:
            return  # page not yet created — nothing to do
        # Mark dirty regardless
        if hasattr(p, "_mark_dirty"):
            p._mark_dirty()
        elif hasattr(p, "_dirty"):
            p._dirty = True
        # Immediately reload only if currently shown
        if self.stack.currentWidget() is p and hasattr(p, "reload"):
            try:
                p.reload()
            except Exception as exc:
                print(f"[MainWindow] _smart_reload({index}) error: {exc}")

    def _reload_dashboard(self):
        """Periodic-timer callback that refreshes the dashboard (page 0) via the
        dirty/smart-reload mechanism."""
        self._smart_reload(0)

    def _on_booking_saved(self):
        """React to booking create/update: mark all booking-affected pages
        (bookings, calendar, kitchen, billing, dashboard, reports) dirty,
        immediately reload whichever is visible, and refresh notifications."""
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
        cur_w = self.stack.currentWidget()
        if cur_w is not None and hasattr(cur_w, "reload"):
            try:
                cur_w.reload()
            except Exception as exc:
                print(f"[MainWindow] _on_booking_saved reload error: {exc}")
        self._poll_notifications()

    def _on_payment_recorded(self):
        """React to a recorded payment by refreshing billing, dashboard, and
        reports pages, then polling notifications."""
        self._smart_reload(6)   # BillingPage
        self._smart_reload(0)   # DashboardPage
        self._smart_reload(7)   # ReportsPage
        self._poll_notifications()

    def _on_kitchen_updated(self):
        """React to a kitchen/order change by refreshing the dashboard (which
        surfaces kitchen status) and polling notifications."""
        self._smart_reload(0)   # DashboardPage reflects kitchen changes
        self._poll_notifications()

    def _on_expense_saved(self):
        """React to an expense save by refreshing expenses, dashboard, and
        reports pages, then polling notifications."""
        self._smart_reload(8)   # ExpensesPage
        self._smart_reload(0)   # DashboardPage
        self._smart_reload(7)   # ReportsPage
        self._poll_notifications()

    def _on_customer_saved(self):
        """React to a customer save: mark customers, bookings, and dashboard
        pages dirty, reload the visible one, and poll notifications."""
        for idx in [2, 1, 0]:
            p = self._pages[idx] if idx < len(self._pages) else None
            if p is None:
                continue
            if hasattr(p, "_mark_dirty"):
                p._mark_dirty()
            elif hasattr(p, "_dirty"):
                p._dirty = True
        cur_w = self.stack.currentWidget()
        if cur_w is not None and hasattr(cur_w, "reload"):
            try:
                cur_w.reload()
            except Exception:
                pass
        self._poll_notifications()

    def _on_sync_started(self, msg: str = ""):
        """Sync-start hook. Intentionally silent to avoid toast spam during
        frequent background syncs."""
        # Silent background sync - no intrusive toast spam
        pass

    def _on_sync_completed(self):
        """Sync-complete hook: invalidate the shared data cache and schedule a
        debounced (400ms) reload of all pages to avoid stutter during rapid
        successive syncs."""
        from utils.data_cache import DataCache
        DataCache.clear()
        # Debounce reloading to prevent screen stutter during rapid syncs
        if not hasattr(self, "_sync_reload_timer"):
            self._sync_reload_timer = QTimer(self)
            self._sync_reload_timer.setSingleShot(True)
            self._sync_reload_timer.setInterval(400)
            self._sync_reload_timer.timeout.connect(self._reload_all_pages)
        self._sync_reload_timer.start(400)

    def _reload_all_pages(self):
        """Only reload the current visible page; mark all others dirty so they
        refresh lazily when the user navigates to them."""
        cur_widget = self.stack.currentWidget()
        for p in self._pages:
            if p is None:
                continue
            if hasattr(p, "_mark_dirty"):
                p._mark_dirty()
            elif hasattr(p, "_dirty"):
                p._dirty = True
            if p is cur_widget and hasattr(p, "reload"):
                try:
                    p.reload()
                except Exception as exc:
                    print(f"[MainWindow] Error reloading active page: {exc}")
        self._poll_notifications()

    def _on_theme_changing(self, palette_id: str):
        """Theme-change start hook: show the full-window theme loading overlay
        naming the palette being switched to."""
        if hasattr(self, "_theme_overlay") and self._theme_overlay:
            from utils.palette import THEME_PALETTES
            pal = THEME_PALETTES.get(palette_id, {})
            name = pal.get("name", "Theme")
            self._theme_overlay.show_loading(f"Switching to {name}...", "Updating color palette & UI styles...")

    def _on_theme_changed(self, _theme: str):
        """Theme-change complete hook: restyle the sidebar/topbar and notify
        every already-built page via its theme hook (``_apply_theme_styles`` or
        ``_on_theme_changed``) in place, keeping all page instances and their
        data in memory, then dismiss the theme overlay with an animation."""
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
        """Handle a fired reminder/alarm: show a long-lived toast with the
        message and time, and make the floating AI mascot react with a
        'surprised' state and a speech bubble."""
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
        """Keep overlays and the floating AI positioned correctly on window
        resize: stretch the theme overlay to fill the window and re-anchor the
        mascot to the bottom-right corner unless the user has dragged it."""
        super().resizeEvent(event)
        if hasattr(self, "_theme_overlay") and self._theme_overlay and self._theme_overlay.isVisible():
            self._theme_overlay.resize(self.size())
        if hasattr(self, "_floating_ai") and self._floating_ai:
            # Respect a user-dragged position; only auto-reposition otherwise.
            if not getattr(self._floating_ai, "_user_moved", False):
                x = self.width() - self._floating_ai.width() - 24
                y = self.height() - self._floating_ai.height() - 24
                self._floating_ai.move(max(0, x), max(0, y))
                self._floating_ai.raise_()

    @property
    def dashboard_page(self):
        """The Dashboard page instance (index 0), or None if not yet built."""
        return self._pages[0]

    @property
    def billing_page(self):
        """The Billing page instance (index 6), or None if not yet built."""
        return self._pages[6]

    @property
    def kitchen_page(self):
        """The Kitchen Orders page instance (index 5), or None if not yet
        built."""
        return self._pages[5]

    def closeEvent(self, event):
        """Clean up on window close: hide/stop the floating AI's background
        thread and quit any per-page background data loaders so no threads are
        left running, then defer to the base handler."""
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
