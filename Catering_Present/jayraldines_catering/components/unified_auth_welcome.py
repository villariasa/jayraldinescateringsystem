"""
Unified Full-Window Authentication & Professional Welcome View.
Eliminates standalone cutout windows and provides a seamless in-app transition
from login credentials to a circular loading spinner and directly into the dashboard.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QApplication, QMessageBox, QStackedLayout,
    QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QThread, QSize
from PySide6.QtGui import QPixmap, QColor, QIcon
from utils.icons import get_icon

import utils.db as db
from utils.auth import authenticate, SessionManager
from utils.db_config import get_db_config, save_db_config, test_postgres_connection
from utils.paths import resource_path
from components.circular_spinner import CircularSpinner
from components.login_dialog import ServerConfigDialog
from utils.data_cache import DataCache


class DataWarmupWorker(QThread):
    """
    Background worker that actively pre-loads core database datasets into
    DataCache while the user views the welcome screen animation.
    Eliminates cold-load query latency across all tabs.
    """
    step_progress = Signal(str, int)  # (status_message, percentage)
    warmup_finished = Signal()

    def run(self):
        try:
            import utils.repository as repo
            from datetime import datetime

            # Step 1: Bookings & Calendar
            try:
                self.step_progress.emit("📊  Loading catering bookings & reservations...", 15)
                bookings = repo.get_all_bookings()
                DataCache.set("bookings", bookings, ttl_seconds=600.0)
            except Exception as e:
                print(f"[DataWarmupWorker] Bookings pre-load note: {e}")

            # Step 2: Customers & Loyalty Tiers
            try:
                self.step_progress.emit("👥  Loading client directory & loyalty tiers...", 30)
                customers = repo.get_all_customers_with_loyalty()
                DataCache.set("customers_loyalty", customers, ttl_seconds=600.0)
                DataCache.set("customers", customers, ttl_seconds=600.0)
            except Exception as e:
                print(f"[DataWarmupWorker] Customers pre-load note: {e}")

            # Step 3: Billing & Invoices
            try:
                self.step_progress.emit("💳  Loading billing records & invoices...", 45)
                invoices = repo.get_all_invoices()
                DataCache.set("invoices", invoices, ttl_seconds=600.0)
            except Exception as e:
                print(f"[DataWarmupWorker] Invoices pre-load note: {e}")

            # Step 4: Menu Items & Packages
            try:
                self.step_progress.emit("🍽️  Pre-warming catering menus & packages...", 60)
                menu_items = repo.get_all_menu_items()
                packages = repo.get_all_packages()
                DataCache.set("menu_items", menu_items, ttl_seconds=600.0)
                DataCache.set("packages", packages, ttl_seconds=600.0)
            except Exception as e:
                print(f"[DataWarmupWorker] Menu/packages pre-load note: {e}")

            # Step 5: Dashboard Analytics & Charts
            try:
                self.step_progress.emit("📈  Computing dashboard KPIs & analytics...", 72)
                now = datetime.now()
                rows = repo.get_monthly_revenue_chart_data(now.year)
                chart_data = [(r["month"], r["revenue"], r["expense"]) for r in rows] if rows else []
                dash_data = {
                    "kpis":       repo.get_dashboard_kpis(),
                    "profit":     repo.get_profit_summary(),
                    "events":     repo.get_upcoming_events(limit=20),
                    "activity":   repo.get_recent_activity(limit=10),
                    "chart_data": chart_data,
                    "followups":  repo.get_todays_follow_ups(),
                }
                DataCache.set("dashboard_data", dash_data, ttl_seconds=600.0)
            except Exception as e:
                print(f"[DataWarmupWorker] Dashboard pre-load note: {e}")

            # Step 6: Expenses & Cash Flow
            try:
                self.step_progress.emit("💰  Loading expenses & cash flow transactions...", 80)
                expenses = repo.get_all_expenses()
                DataCache.set("expenses", expenses, ttl_seconds=600.0)
                summary = repo.get_cash_flow_summary()
                txs = repo.get_cash_flow_transactions()
                DataCache.set("cash_flow_data", {"transactions": txs, "summary": summary}, ttl_seconds=600.0)
            except Exception as e:
                print(f"[DataWarmupWorker] Cashflow/expenses pre-load note: {e}")

            self.step_progress.emit("⚙️  Database records cached! Preparing workspaces...", 82)
            self.msleep(150)
        except Exception as exc:
            print(f"[DataWarmupWorker] General note: {exc}")
        finally:
            self.warmup_finished.emit()


class UnifiedAuthWelcome(QWidget):
    """
    Full-window authentication and smooth welcome setup view.
    Operates inside the main application window without any window cutouts.
    """
    auth_and_welcome_finished = Signal()
    request_prebuild_pages = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("unifiedAuthWelcome")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            #unifiedAuthWelcome {
                background-color: #070B14;
            }
        """)

        self._stacked = QStackedLayout(self)
        self._stacked.setContentsMargins(0, 0, 0, 0)
        self._stacked.setStackingMode(QStackedLayout.StackOne)

        # 1. Login View
        self._login_view = self._create_login_view()
        self._stacked.addWidget(self._login_view)

        # 2. Welcome Loading View
        self._welcome_view = self._create_welcome_view()
        self._stacked.addWidget(self._welcome_view)

        # Warmup worker reference
        self._warmup_worker = None

    # -----------------------------------------------------------------------
    # Login View Construction
    # -----------------------------------------------------------------------
    def _create_login_view(self) -> QWidget:
        container = QWidget(self)
        root_lay = QVBoxLayout(container)
        root_lay.setContentsMargins(20, 20, 20, 20)

        # Top Bar (Gear config + Close)
        top_bar = QHBoxLayout()
        gear_btn = QPushButton()
        gear_btn.setIcon(get_icon("settings", color="#CBD5E1", size=QSize(17, 17)))
        gear_btn.setIconSize(QSize(17, 17))
        gear_btn.setFixedSize(30, 30)
        gear_btn.setCursor(Qt.PointingHandCursor)
        gear_btn.setToolTip("Configure Database Server Connection")
        gear_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)
        gear_btn.clicked.connect(self._open_server_settings)
        top_bar.addWidget(gear_btn)

        top_bar.addStretch()

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#94A3B8", size=QSize(17, 17)))
        close_btn.setIconSize(QSize(17, 17))
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("Close Application")
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 6px; }
            QPushButton:hover { background: rgba(239, 68, 68, 0.25); }
        """)
        close_btn.clicked.connect(self._on_close_app)
        top_bar.addWidget(close_btn)

        root_lay.addLayout(top_bar)
        root_lay.addStretch(1)

        # Centered Login Card
        center_row = QHBoxLayout()
        center_row.addStretch(1)

        self.login_card = QFrame()
        self.login_card.setFixedWidth(440)
        self.login_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1A1F36, stop:0.4 #0F172A, stop:1 #030712);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 18px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self.login_card)
        shadow.setBlurRadius(40)
        shadow.setYOffset(16)
        shadow.setColor(QColor(0, 0, 0, 220))
        self.login_card.setGraphicsEffect(shadow)

        card_lay = QVBoxLayout(self.login_card)
        card_lay.setContentsMargins(32, 32, 32, 32)
        card_lay.setSpacing(14)

        # Brand Header
        header_lay = QVBoxLayout()
        header_lay.setSpacing(6)
        header_lay.setAlignment(Qt.AlignCenter)

        logo_lbl = QLabel()
        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            pm = QPixmap(logo_path).scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pm)
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        header_lay.addWidget(logo_lbl)

        title_lbl = QLabel("Jayraldine's Catering")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #F8FAFC; font-size: 21px; font-weight: 800; border: none; background: transparent; letter-spacing: 0.5px;")
        header_lay.addWidget(title_lbl)

        sub_lbl = QLabel("Sign in to access catering management")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none; background: transparent;")
        header_lay.addWidget(sub_lbl)

        card_lay.addLayout(header_lay)

        # Server Status Pill
        self.server_status_lbl = QLabel()
        self.server_status_lbl.setAlignment(Qt.AlignCenter)
        self.server_status_lbl.setFixedHeight(24)
        self._update_server_status_badge()
        card_lay.addWidget(self.server_status_lbl)

        # Form Inputs
        input_style = """
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.14);
                color: #F8FAFC;
                padding: 10px 14px;
                font-size: 13.5px;
                border-radius: 8px;
            }
            QLineEdit:focus {
                border: 1.5px solid #E11D48;
                background-color: #0F172A;
            }
        """

        card_lay.addWidget(QLabel("Username", styleSheet="color: #94A3B8; font-size: 12px; font-weight: 600; border: none; background: transparent;"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter username")
        self.username_edit.setStyleSheet(input_style)
        self.username_edit.returnPressed.connect(self._do_login)
        card_lay.addWidget(self.username_edit)

        card_lay.addWidget(QLabel("Password", styleSheet="color: #94A3B8; font-size: 12px; font-weight: 600; border: none; background: transparent;"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.setStyleSheet(input_style)
        self.password_edit.returnPressed.connect(self._do_login)
        from utils.password_field import add_show_password_toggle
        add_show_password_toggle(self.password_edit)
        card_lay.addWidget(self.password_edit)

        # Options Row
        opt_row = QHBoxLayout()
        self.remember_cb = QCheckBox("Remember me")
        self.remember_cb.setStyleSheet("""
            QCheckBox { color: #94A3B8; font-size: 12px; border: none; background: transparent; }
            QCheckBox::indicator { width: 15px; height: 15px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.25); background: #1E293B; }
            QCheckBox::indicator:checked { background: #E11D48; border-color: #E11D48; }
        """)
        opt_row.addWidget(self.remember_cb)
        opt_row.addStretch()
        card_lay.addLayout(opt_row)

        # Error Notice
        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600; border: none; background: transparent;")
        self.err_lbl.setAlignment(Qt.AlignCenter)
        self.err_lbl.hide()
        card_lay.addWidget(self.err_lbl)

        # Login Button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setFixedHeight(42)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #BE123C);
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F43F5E, stop:1 #E11D48);
            }
            QPushButton:pressed {
                background: #9F1239;
            }
        """)
        self.login_btn.clicked.connect(self._do_login)
        card_lay.addWidget(self.login_btn)

        center_row.addWidget(self.login_card)
        center_row.addStretch(1)

        root_lay.addLayout(center_row)
        root_lay.addStretch(2)

        # Load saved username if present
        self._load_saved_credentials()

        return container

    # -----------------------------------------------------------------------
    # Welcome & Loading View Construction (With Circular Spinner)
    # -----------------------------------------------------------------------
    def _create_welcome_view(self) -> QWidget:
        container = QWidget(self)
        lay = QVBoxLayout(container)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(20)

        # Welcome Content Box
        self.welcome_card = QFrame()
        self.welcome_card.setFixedWidth(520)
        self.welcome_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(30, 27, 75, 0.7), stop:1 rgba(15, 23, 42, 0.85));
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 20px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self.welcome_card)
        shadow.setBlurRadius(48)
        shadow.setColor(QColor(0, 0, 0, 220))
        self.welcome_card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(self.welcome_card)
        c_lay.setContentsMargins(40, 44, 40, 44)
        c_lay.setSpacing(16)
        c_lay.setAlignment(Qt.AlignCenter)

        # Logo
        w_logo = QLabel()
        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            pm = QPixmap(logo_path).scaled(68, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            w_logo.setPixmap(pm)
        w_logo.setAlignment(Qt.AlignCenter)
        w_logo.setStyleSheet("background: transparent; border: none;")
        c_lay.addWidget(w_logo)

        # Welcome Greeting Text
        self.welcome_title = QLabel("Welcome back!")
        self.welcome_title.setAlignment(Qt.AlignCenter)
        self.welcome_title.setWordWrap(True)   # long names wrap instead of being clipped
        self.welcome_title.setStyleSheet("color: #F8FAFC; font-size: 24px; font-weight: 800; border: none; background: transparent;")
        c_lay.addWidget(self.welcome_title)

        # Role Badge
        self.role_badge = QLabel("Administrator")
        self.role_badge.setAlignment(Qt.AlignCenter)
        self.role_badge.setFixedHeight(26)
        self.role_badge.setStyleSheet("""
            color: #38BDF8;
            font-size: 12px;
            font-weight: 700;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 13px;
            padding: 2px 14px;
        """)
        c_lay.addWidget(self.role_badge, alignment=Qt.AlignCenter)

        c_lay.addSpacing(10)

        # Sleek Circular Spinner
        self.spinner = CircularSpinner(size=56, line_width=4, color_start="#E11D48", color_end="#FB7185")
        c_lay.addWidget(self.spinner, alignment=Qt.AlignCenter)

        # Dynamic Status Label
        self.loading_status_lbl = QLabel("Authenticating credentials...")
        self.loading_status_lbl.setAlignment(Qt.AlignCenter)
        self.loading_status_lbl.setStyleSheet("color: #F8FAFC; font-size: 13.5px; font-weight: 700; border: none; background: transparent;")
        c_lay.addWidget(self.loading_status_lbl)

        # Visual Animated Progress Bar
        self.loading_progress = QProgressBar()
        self.loading_progress.setFixedHeight(8)
        self.loading_progress.setRange(0, 100)
        self.loading_progress.setValue(0)
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.08);
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:0.6 #FB7185, stop:1 #38BDF8);
                border-radius: 4px;
            }
        """)
        c_lay.addWidget(self.loading_progress)

        # Percentage Subtitle
        self.loading_pct_lbl = QLabel("0% Complete")
        self.loading_pct_lbl.setAlignment(Qt.AlignCenter)
        self.loading_pct_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        c_lay.addWidget(self.loading_pct_lbl)

        lay.addWidget(self.welcome_card)
        return container

    def update_progress(self, text: str, pct: int):
        """Updates the status text, animated progress bar, and percentage counter."""
        try:
            self.loading_status_lbl.setText(text)
            self.loading_progress.setValue(min(100, max(0, pct)))
            self.loading_pct_lbl.setText(f"{pct}% Complete")
            QApplication.processEvents()
        except Exception:
            pass

    def finish_and_fade_out(self):
        """Transitions out of the welcome view once all data and workspaces are loaded."""
        if not getattr(self, "_finishing", False):
            self._finishing = True
            self._fade_out_and_finish()

    # -----------------------------------------------------------------------
    # Authentication & Transition Logic
    # -----------------------------------------------------------------------
    def _do_login(self):
        self.err_lbl.hide()
        user = self.username_edit.text().strip()
        pwd = self.password_edit.text()

        if not user or not pwd:
            self.err_lbl.setText("Please enter both username and password.")
            self.err_lbl.show()
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing In...")
        QApplication.processEvents()

        authenticated_user = authenticate(user, pwd)
        if authenticated_user:
            SessionManager.login(authenticated_user)
            self._save_credentials(user, self.remember_cb.isChecked())
            self._start_welcome_sequence(authenticated_user)
        else:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")
            self.err_lbl.setText("Invalid username or password.")
            self.err_lbl.show()

    def _start_welcome_sequence(self, user_info: dict):
        disp_name = user_info.get("display_name") or user_info.get("username") or "User"
        role = user_info.get("role") or "staff"
        role_label = "🛡️  Administrator" if role.lower() == "admin" else "👤  Catering Staff"

        self.welcome_title.setText(f"Welcome back, {disp_name}!")
        self.role_badge.setText(role_label)
        self._finishing = False

        # Transition to Welcome View
        self._stacked.setCurrentIndex(1)
        self.spinner.start()
        self.update_progress("🔐  Verifying permissions & security tokens...", 5)

        # Start active background data pre-loader
        self._warmup_worker = DataWarmupWorker(self)
        self._warmup_worker.step_progress.connect(self._on_warmup_progress)
        self._warmup_worker.warmup_finished.connect(self._on_warmup_finished)
        self._warmup_worker.start()

        # Safety fallback timeout: max 15 seconds in case of severe network latency
        self._fallback_timer = QTimer(self)
        self._fallback_timer.setSingleShot(True)
        self._fallback_timer.timeout.connect(self.finish_and_fade_out)
        self._fallback_timer.start(15000)

    def _on_warmup_progress(self, text: str, pct: int):
        self.update_progress(text, pct)

    def _on_warmup_finished(self):
        if hasattr(self, "_fallback_timer") and self._fallback_timer.isActive():
            self._fallback_timer.stop()
        self.request_prebuild_pages.emit()

    def _fade_out_and_finish(self):
        """Smoothly fades out the overlay to reveal MainWindow."""
        self._anim_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._anim_effect)

        self._fade_anim = QPropertyAnimation(self._anim_effect, b"opacity")
        self._fade_anim.setDuration(350)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

        def _on_anim_finished():
            self.spinner.stop()
            try:
                self.setGraphicsEffect(None)
            except Exception:
                pass
            self._anim_effect = None
            self.hide()
            self.auth_and_welcome_finished.emit()

        self._fade_anim.finished.connect(_on_anim_finished)
        self._fade_anim.start()

    def reset_to_login(self):
        """Resets view back to login mode (e.g. after logout)."""
        self._finishing = False
        try:
            self.setGraphicsEffect(None)
        except Exception:
            pass
        self._anim_effect = None
        self.password_edit.clear()
        self.err_lbl.hide()
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")
        self._stacked.setCurrentIndex(0)
        self._update_server_status_badge()
        self.show()
        self.raise_()
        self.update()
        if hasattr(self, "username_edit"):
            if self.username_edit.text().strip():
                self.password_edit.setFocus()
            else:
                self.username_edit.setFocus()

    # -----------------------------------------------------------------------
    # Server Status & Config
    # -----------------------------------------------------------------------
    def _update_server_status_badge(self):
        cfg = get_db_config()
        host = cfg.get("host", "localhost")
        if host in ("localhost", "127.0.0.1"):
            txt = "🟢 Local Server Active"
            color = "#22C55E"
            bg = "rgba(34, 197, 94, 0.1)"
        else:
            txt = f"🌐 Connected to Server ({host})"
            color = "#38BDF8"
            bg = "rgba(56, 189, 248, 0.1)"

        self.server_status_lbl.setText(txt)
        self.server_status_lbl.setStyleSheet(f"""
            color: {color};
            font-size: 11.5px;
            font-weight: 700;
            background: {bg};
            border: 1px solid {color}33;
            border-radius: 12px;
            padding: 2px 10px;
        """)

    def _open_server_settings(self):
        dlg = ServerConfigDialog(self)
        if dlg.exec():
            self._update_server_status_badge()

    def _on_close_app(self):
        app = QApplication.instance()
        if app:
            app.quit()

    def _load_saved_credentials(self):
        saved_file = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JayraldinesCatering" / "last_username.txt"
        if saved_file.exists():
            try:
                name = saved_file.read_text(encoding="utf-8").strip()
                if name:
                    self.username_edit.setText(name)
                    self.remember_cb.setChecked(True)
                    self.password_edit.setFocus()
                    return
            except Exception:
                pass
        self.username_edit.setFocus()

    def _save_credentials(self, username: str, remember: bool):
        saved_file = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JayraldinesCatering" / "last_username.txt"
        try:
            saved_file.parent.mkdir(parents=True, exist_ok=True)
            if remember:
                saved_file.write_text(username.strip(), encoding="utf-8")
            elif saved_file.exists():
                saved_file.unlink()
        except Exception:
            pass
