import subprocess
from datetime import datetime, date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QFormLayout, QMessageBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QSpinBox, QCheckBox, QFileDialog, QListWidget, QListWidgetItem,
    QInputDialog, QColorDialog, QComboBox, QDateEdit, QDialog
)
from PySide6.QtCore import Qt, QSize, QDate, QTimer, QThread, Signal
from PySide6.QtGui import QColor

from components.circular_spinner import CircularSpinner

from utils.icons import btn_icon_primary, btn_icon_secondary, get_icon
from utils.theme import ThemeManager
from utils.accent import AccentManager, PRESET_THEMES
from utils.palette import THEME_CATEGORIES, THEME_PALETTES, get_palettes_by_category
from components.dialogs import success, prompt_file_saved, confirm
import utils.repository as repo
from utils.signals import app_events
from utils.auth import SessionManager
from components.user_management_panel import UserManagementPanel, ChangeOwnPasswordDialog
from utils.db_config import get_db_config, save_db_config, test_postgres_connection
from utils.db_server_service import (
    is_central_db_server_machine,
    get_local_db_server_status,
    restart_local_db_server,
    start_local_db_server,
    configure_server_remote_access,
    verify_owner_authorization,
)
from components.owner_auth_dialog import OwnerAuthDialog


_BUSINESS_INFO = {
    "name":    "Jayraldine's Catering",
    "contact": "+63 912 345 6789",
    "email":   "admin@jayraldines.com",
    "address": "123 Rizal St., Manila, Metro Manila",
}


class DatabaseRestoreWorker(QThread):
    progress_update = Signal(str)
    restore_finished = Signal(bool, str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            import utils.db as db
            import shutil
            import os
            import sqlite3
            from pathlib import Path

            path = self.file_path
            self.progress_update.emit("Inspecting database backup structure...")

            # Detect whether SQLite binary
            is_sqlite_binary = False
            with open(path, "rb") as f:
                header = f.read(16)
                if header.startswith(b"SQLite format 3"):
                    is_sqlite_binary = True

            engine = db.get_engine_type()

            if is_sqlite_binary:
                if engine == "sqlite":
                    self.progress_update.emit("Closing active connections & cleaning cache...")
                    db.close()
                    dst = db.get_sqlite_db_path()
                    for ext in ["-wal", "-shm", "-journal"]:
                        wal = Path(str(dst) + ext)
                        if wal.exists():
                            try:
                                wal.unlink()
                            except Exception:
                                pass

                    self.progress_update.emit("Copying backup database files...")
                    shutil.copy2(path, dst)

                    self.progress_update.emit("Applying schema upgrades & missing columns...")
                    conn = sqlite3.connect(str(dst))
                    cur = conn.cursor()

                    # 1. Bookings columns
                    cur.execute("PRAGMA table_info(bookings)")
                    bk_cols = [r[1] for r in cur.fetchall()]
                    for col, defn in [
                        ("bk_contact", "TEXT DEFAULT ''"),
                        ("bk_email", "TEXT DEFAULT ''"),
                        ("bk_special_notes", "TEXT DEFAULT ''"),
                        ("bk_down_payment", "REAL DEFAULT 0.0"),
                        ("bk_down_payment_status", "TEXT DEFAULT 'PENDING'"),
                        ("bk_base_total", "REAL DEFAULT 0.0"),
                        ("bk_color_theme", "TEXT DEFAULT '#2563EB'"),
                    ]:
                        if col not in bk_cols:
                            cur.execute(f"ALTER TABLE bookings ADD COLUMN {col} {defn}")

                    # Backfill contact and email from customer records if empty
                    cur.execute("""
                        UPDATE bookings
                        SET bk_contact = (SELECT cus_contact FROM customers WHERE customers.cus_id = bookings.bk_customer_id)
                        WHERE (bk_contact IS NULL OR bk_contact = '') AND bk_customer_id IS NOT NULL
                    """)
                    cur.execute("""
                        UPDATE bookings
                        SET bk_email = (SELECT cus_email FROM customers WHERE customers.cus_id = bookings.bk_customer_id)
                        WHERE (bk_email IS NULL OR bk_email = '') AND bk_customer_id IS NOT NULL
                    """)

                    # 2. Audit logs columns
                    cur.execute("PRAGMA table_info(audit_logs)")
                    al_cols = [r[1] for r in cur.fetchall()]
                    if "al_device" not in al_cols:
                        cur.execute("ALTER TABLE audit_logs ADD COLUMN al_device TEXT DEFAULT 'Desktop / Server'")

                    conn.commit()

                    self.progress_update.emit("Counting restored records...")
                    cur.execute("SELECT count(*) FROM bookings")
                    bk_cnt = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM customers")
                    cus_cnt = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM invoices")
                    inv_cnt = cur.fetchone()[0]
                    conn.close()

                    self.progress_update.emit("Reconnecting to restored database...")
                    db.connect()

                    self.restore_finished.emit(
                        True,
                        f"Database restored successfully!\n\n"
                        f"• Confirmed Bookings / Orders: {bk_cnt}\n"
                        f"• Customers: {cus_cnt}\n"
                        f"• Invoices / Billings: {inv_cnt}\n\n"
                        f"Please restart the application to refresh all views."
                    )
                else:
                    self.progress_update.emit("Migrating SQLite backup tables into PostgreSQL...")
                    from utils.sqlite_to_postgres import migrate_sqlite_to_postgres
                    from utils.db_config import get_db_config
                    cfg = get_db_config()
                    ok, stats, err = migrate_sqlite_to_postgres(
                        Path(path), cfg,
                        progress_callback=lambda pct, msg: self.progress_update.emit(f"PostgreSQL [{pct}%]: {msg}")
                    )
                    if ok:
                        total_rows = sum(stats.values())
                        bk_cnt = stats.get("bookings", 0)
                        cus_cnt = stats.get("customers", 0)
                        inv_cnt = stats.get("invoices", 0)
                        self.restore_finished.emit(
                            True,
                            f"Client backup successfully migrated into PostgreSQL!\n\n"
                            f"• Total records restored: {total_rows}\n"
                            f"• Bookings / Orders: {bk_cnt}\n"
                            f"• Customers: {cus_cnt}\n"
                            f"• Invoices / Billings: {inv_cnt}\n\n"
                            f"Please restart the application to refresh all views."
                        )
                    else:
                        self.restore_finished.emit(False, f"Migration failed:\n\n{err}")
            else:
                self.progress_update.emit("Executing SQL script...")
                if engine == "sqlite":
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        sql_script = f.read()
                    conn = db.get_connection()
                    conn.executescript(sql_script)
                    self.restore_finished.emit(True, "SQL script restored into SQLite successfully. Please restart the application.")
                else:
                    from utils.db_config import get_db_config
                    cfg = get_db_config()
                    try:
                        import psycopg2
                        pg = psycopg2.connect(
                            host=cfg.get("host", "localhost"),
                            port=int(cfg.get("port", 5432)),
                            dbname=cfg.get("dbname", "jayraldines_catering"),
                            user=cfg.get("user", "postgres"),
                            password=cfg.get("password", "12345678"),
                            connect_timeout=15
                        )
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            sql_script = f.read()
                        with pg.cursor() as cur:
                            cur.execute(sql_script)
                        pg.commit()
                        pg.close()
                        self.restore_finished.emit(True, "SQL script restored into PostgreSQL successfully. Please restart the application.")
                    except Exception as p_err:
                        result = subprocess.run(
                            ["psql", "-U", cfg.get("user", "postgres"), "-d", cfg.get("dbname", "jayraldines_catering"), "-f", path],
                            capture_output=True, text=True, timeout=120
                        )
                        if result.returncode == 0:
                            self.restore_finished.emit(True, "Database restored successfully via psql. Please restart the application.")
                        else:
                            self.restore_finished.emit(False, f"psql error:\n{result.stderr or p_err}")
        except Exception as exc:
            self.restore_finished.emit(False, f"An error occurred during restore:\n{exc}")


class DatabaseRestoreProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restoring Database")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 220)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setObjectName("loaderCard")
        card.setStyleSheet("""
            QFrame#loaderCard {
                background: #0F172A;
                border: 1.5px solid #334155;
                border-radius: 16px;
            }
            QLabel {
                color: #F8FAFC;
            }
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setAlignment(Qt.AlignCenter)
        c_lay.setSpacing(14)

        self.spinner = CircularSpinner(size=52, line_width=4, color_start="#E11D48", color_end="#38BDF8", parent=card)
        c_lay.addWidget(self.spinner, alignment=Qt.AlignCenter)

        title = QLabel("Restoring Database Backup...", card)
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        title.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(title)

        self.status_lbl = QLabel("Please wait while records are being imported...", card)
        self.status_lbl.setStyleSheet("font-size: 13px; color: #94A3B8;")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(self.status_lbl)

        layout.addWidget(card)

    def set_status(self, text: str):
        self.status_lbl.setText(text)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = ThemeManager()
        self._accent = AccentManager()
        self._dirty = True
        self._build_ui()

        try:
            from utils.signals import app_events
            ev = app_events()
            ev.data_changed.connect(self._mark_dirty_and_reload)
            ev.customer_saved.connect(self._mark_dirty_and_reload)
            ev.booking_saved.connect(self._mark_dirty_and_reload)
            # NOTE: was "payment_saved" - not a real signal (see utils/signals.py),
            # so this connection silently never fired; payments recorded on a
            # remote client never refreshed Settings' audit log until now.
            ev.payment_recorded.connect(self._mark_dirty_and_reload)
        except Exception:
            pass

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self._load_all_settings_async()
            self._load_audit_log()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_dirty", True):
            self._dirty = False
            self._load_all_settings_async()
            self._load_audit_log()

    def reload(self):
        self._dirty = False
        self._load_all_settings_async()
        self._load_audit_log()

    @staticmethod
    def _fetch_all_settings_data_worker():
        cur_year = datetime.now().year
        try:
            biz = repo.get_business_info() or {}
        except Exception:
            biz = {}
        try:
            policy = repo.get_business_policy() or {}
        except Exception:
            policy = {}
        try:
            smtp = repo.get_smtp_config() or {}
        except Exception:
            smtp = {}
        try:
            occasions = repo.get_all_occasions() or []
        except Exception:
            occasions = []
        try:
            sales_targets = repo.get_monthly_sales_targets(cur_year) or {}
        except Exception:
            sales_targets = {}
        return {
            "biz": biz,
            "policy": policy,
            "smtp": smtp,
            "occasions": occasions,
            "sales_targets": sales_targets,
        }

    def _load_all_settings_async(self):
        from utils.data_loader import run_async
        if hasattr(self, "_loader"):
            self._loader.show_overlay("Loading system configuration...")
        run_async(self, self._fetch_all_settings_data_worker, self._apply_settings_data)

    def _apply_settings_data(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
            if not data:
                return
            if data.get("biz"):
                b = data["biz"]
                _BUSINESS_INFO.update(b)
                if hasattr(self, "_name_f"):
                    self._name_f.setText(b.get("name", ""))
                if hasattr(self, "_contact_f"):
                    self._contact_f.setText(b.get("contact", ""))
                if hasattr(self, "_email_f"):
                    self._email_f.setText(b.get("email", ""))
                if hasattr(self, "_address_f"):
                    self._address_f.setText(b.get("address", ""))
            if data.get("policy"):
                p = data["policy"]
                if hasattr(self, "_min_dp_spin"):
                    self._min_dp_spin.setValue(float(p.get("min_downpayment_pct", 30.0)))
                if hasattr(self, "_allow_zero_cb"):
                    self._allow_zero_cb.setChecked(bool(p.get("allow_zero_downpayment", False)))
                if hasattr(self, "_max_pax_spin"):
                    self._max_pax_spin.setValue(int(p.get("max_daily_pax", 600)))
            if data.get("smtp"):
                s = data["smtp"]
                if hasattr(self, "_smtp_host_f"):
                    self._smtp_host_f.setText(str(s.get("smtp_host", "")))
                if hasattr(self, "_smtp_port_f"):
                    self._smtp_port_f.setValue(int(s.get("smtp_port", 587)))
                if hasattr(self, "_smtp_user_f"):
                    self._smtp_user_f.setText(str(s.get("smtp_user", "")))
                if hasattr(self, "_smtp_pass_f"):
                    self._smtp_pass_f.setText(str(s.get("smtp_pass", "")))
            if data.get("occasions") is not None and hasattr(self, "_occ_list"):
                self._occ_list.clear()
                for name in data["occasions"]:
                    self._occ_list.addItem(QListWidgetItem(name))
            if data.get("sales_targets") and hasattr(self, "_month_target_spins"):
                st = data["sales_targets"]
                for m, spin in self._month_target_spins.items():
                    spin.setValue(float(st.get(m, 85000.0)))
        finally:
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()

    def _build_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self._content_lay = lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        lay.addWidget(title)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")
        can_delete = SessionManager.is_admin() or SessionManager.has_permission("settings", "delete")
        is_admin = SessionManager.is_admin()

        # Permission-gated cards are tracked as self._card_<slot> (None when
        # not currently built) so refresh_permissions() can remove/rebuild/
        # reinsert them at the correct position when a different user logs in.
        self._card_view_only_banner = self._build_view_only_banner() if not can_edit else None
        if self._card_view_only_banner is not None:
            lay.addWidget(self._card_view_only_banner)

        self._card_current_user = self._build_current_user_card()
        lay.addWidget(self._card_current_user)

        self._card_user_mgmt = self._build_user_management_card() if is_admin else None
        if self._card_user_mgmt is not None:
            lay.addWidget(self._card_user_mgmt)

        self._card_server_db = self._build_server_database_card() if is_admin else None
        if self._card_server_db is not None:
            lay.addWidget(self._card_server_db)

        lay.addWidget(self._build_session_security_card())

        self._card_business = self._build_business_card()
        lay.addWidget(self._card_business)

        self._card_sales_targets = self._build_sales_targets_card()
        lay.addWidget(self._card_sales_targets)

        self._card_import = self._build_import_card()
        lay.addWidget(self._card_import)

        self._card_occasions = self._build_occasions_card()
        lay.addWidget(self._card_occasions)

        self._card_menu_categories = self._build_menu_categories_card()
        lay.addWidget(self._card_menu_categories)

        self._card_policy = self._build_policy_card()
        lay.addWidget(self._card_policy)

        self._card_smtp = self._build_smtp_card()
        lay.addWidget(self._card_smtp)

        lay.addWidget(self._build_theme_card())

        self._card_backup = self._build_backup_card()
        lay.addWidget(self._card_backup)

        lay.addWidget(self._build_tablet_sync_card())
        lay.addWidget(self._build_audit_card())
        lay.addWidget(self._build_daily_report_card())
        lay.addWidget(self._build_diagnostics_card())

        self._card_purge = self._build_purge_data_card() if (can_edit and can_delete) else None
        if self._card_purge is not None:
            lay.addWidget(self._card_purge)

        lay.addStretch()

        scroll.setWidget(content)
        root_lay.addWidget(scroll)

        from components.loading_overlay import LoadingOverlay
        self._loader = LoadingOverlay(self, "Loading system configuration...")

    # ── Permission-refresh support ──────────────────────────────────────────
    # Slot order mirrors the on-screen card order built in _build_ui(). Slots
    # not in _ALWAYS_PRESENT_SLOTS are permission-gated and tracked via a
    # self._card_<slot> attribute (None when not currently built).
    _SLOT_ORDER = [
        "view_only_banner", "current_user", "user_mgmt", "server_db",
        "session_security", "business", "sales_targets", "import",
        "occasions", "menu_categories", "policy", "smtp", "theme", "backup", "tablet_sync",
        "audit", "daily_report", "diagnostics", "purge",
    ]
    _ALWAYS_PRESENT_SLOTS = {
        "session_security", "theme", "tablet_sync", "audit",
        "daily_report", "diagnostics",
    }

    def _build_view_only_banner(self):
        view_banner = QFrame()
        view_banner.setObjectName("viewBanner")
        view_banner.setStyleSheet("""
            QFrame#viewBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(245, 158, 11, 0.16), stop:1 rgba(217, 119, 6, 0.08));
                border: 1.5px solid rgba(245, 158, 11, 0.45);
                border-radius: 10px;
            }
        """)
        vb_lay = QHBoxLayout(view_banner)
        vb_lay.setContentsMargins(16, 12, 16, 12)
        vb_lay.setSpacing(12)
        vb_icon = QLabel("🔒")
        vb_icon.setStyleSheet("font-size: 20px;")
        vb_lay.addWidget(vb_icon)
        vb_text = QLabel(
            "<b>VIEW-ONLY ACCESS:</b> You have view-only permission for Settings. "
            "Adding, modifying, saving settings, importing data, restoring backups, and purging records are strictly disabled."
        )
        vb_text.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: 500;")
        vb_text.setWordWrap(True)
        vb_lay.addWidget(vb_text, 1)
        return view_banner

    def _insert_index_for_slot(self, slot: str) -> int:
        """Layout index a slot's widget should occupy, based on which earlier
        slots currently have an active (built) widget. Index 0 is the title,
        which is never removed/rebuilt."""
        idx = 1
        for s in self._SLOT_ORDER:
            if s == slot:
                break
            if s in self._ALWAYS_PRESENT_SLOTS:
                idx += 1
            elif getattr(self, f"_card_{s}", None) is not None:
                idx += 1
        return idx

    def refresh_permissions(self):
        """Re-evaluate the logged-in user's permissions and rebuild any
        permission-gated cards/controls so switching users (e.g. a Staff
        view-only session followed by an Admin login) is reflected
        immediately. Called by main_window.py after a login/user switch, if
        this (singleton, reused) page instance exposes the method."""
        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")
        can_delete = SessionManager.is_admin() or SessionManager.has_permission("settings", "delete")
        can_create = SessionManager.is_admin() or SessionManager.has_permission("settings", "create")
        is_admin = SessionManager.is_admin()
        sig = (can_edit, can_delete, can_create, is_admin)
        if sig == getattr(self, "_last_perm_sig", None):
            return
        self._last_perm_sig = sig
        # Cheap field-level toggle - this combo isn't part of a rebuilt card.
        if hasattr(self, "timeout_combo"):
            self.timeout_combo.setEnabled(can_edit)
        self._rebuild_permission_gated_cards(can_edit, can_delete, can_create, is_admin)

    def _rebuild_permission_gated_cards(self, can_edit, can_delete, can_create, is_admin):
        # NOTE: _build_user_management_card() and _build_server_database_card()
        # only assign instance attributes / connect signals on the NEW widgets
        # they create (e.g. self.user_panel, self._connected_devices_panel),
        # with no module/global-level signal or QTimer registration. The old
        # card (and any QTimer/panel parented to it, e.g. ConnectedDevicesPanel's
        # self._refresh_timer) is destroyed via deleteLater() below, so
        # rebuilding these is safe and does not leak timers or duplicate
        # connections.
        builders = {
            "view_only_banner": (not can_edit, self._build_view_only_banner),
            "current_user":     (True, self._build_current_user_card),
            "user_mgmt":        (is_admin, self._build_user_management_card),
            "server_db":        (is_admin, self._build_server_database_card),
            "business":         (True, self._build_business_card),
            "sales_targets":    (True, self._build_sales_targets_card),
            "import":           (True, self._build_import_card),
            "occasions":        (True, self._build_occasions_card),
            "menu_categories":  (True, self._build_menu_categories_card),
            "policy":           (True, self._build_policy_card),
            "smtp":             (True, self._build_smtp_card),
            "backup":           (True, self._build_backup_card),
            "purge":            (can_edit and can_delete, self._build_purge_data_card),
        }

        for slot, (should_exist, builder) in builders.items():
            attr = f"_card_{slot}"
            old = getattr(self, attr, None)
            idx = self._insert_index_for_slot(slot)
            if old is not None:
                self._content_lay.removeWidget(old)
                old.setParent(None)
                old.deleteLater()
                setattr(self, attr, None)
            if should_exist:
                new_widget = builder()
                self._content_lay.insertWidget(idx, new_widget)
                setattr(self, attr, new_widget)

        # Rebuilt cards (business/policy/smtp/occasions/sales targets) start
        # out with cached/default field values; repopulate them with the
        # actual persisted settings right away instead of waiting for the
        # next dirty-reload/showEvent.
        self._load_all_settings_async()

    def _build_current_user_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        sec_title = QLabel("Current User")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        hint = QLabel("This name is attached to every action you perform (orders, payments, charges) so it appears correctly in the Audit Log and Daily Activity Report.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")

        row = QHBoxLayout()
        from utils.session import get_actor, set_actor
        self._actor_f = QLineEdit(get_actor())
        self._actor_f.setPlaceholderText("Your name (e.g. John)")
        if not can_edit:
            self._actor_f.setReadOnly(True)

        def _save_actor():
            if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "edit"):
                QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot edit user information.")
                return
            set_actor(self._actor_f.text().strip())
            success(self, message=f"You are now logged as: {get_actor()}")

        row.addWidget(self._actor_f, 3)
        if can_edit:
            save_btn = QPushButton("Save Name")
            save_btn.setObjectName("primaryButton")
            save_btn.setFixedHeight(34)
            save_btn.clicked.connect(_save_actor)
            row.addWidget(save_btn, 1)

        # Change Password Button
        chg_pwd_btn = QPushButton("Change Password")
        chg_pwd_btn.setFixedHeight(34)
        chg_pwd_btn.setCursor(Qt.PointingHandCursor)
        chg_pwd_btn.setStyleSheet("background-color: #334155; color: #F8FAFC; border-radius: 6px; padding: 0 14px; font-weight: 600;")
        def _open_chg_pwd():
            dlg = ChangeOwnPasswordDialog(self)
            dlg.exec()
        chg_pwd_btn.clicked.connect(_open_chg_pwd)
        row.addWidget(chg_pwd_btn)

        lay.addLayout(row)
        return card

    def _build_user_management_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        self.user_panel = UserManagementPanel(self)
        lay.addWidget(self.user_panel)
        return card

    def _build_server_database_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        sec_title = QLabel("Central Database Server & Backups")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        hint = QLabel("View live PostgreSQL server status, inspect connectivity, export backup connection credentials, or perform authorized server maintenance.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # ── Status Container Box ───────────────────────────────────────────
        details_box = QFrame()
        details_box.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 14px;")
        d_lay = QVBoxLayout(details_box)
        d_lay.setSpacing(8)

        top_status_row = QHBoxLayout()
        top_status_row.setSpacing(10)

        self._machine_role_lbl = QLabel()
        self._machine_role_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #F8FAFC;")
        top_status_row.addWidget(self._machine_role_lbl)

        top_status_row.addStretch()

        self._live_status_badge = QLabel("Checking...")
        self._live_status_badge.setStyleSheet("""
            background-color: #065F46;
            color: #34D399;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 10px;
            border: 1px solid #10B981;
        """)
        top_status_row.addWidget(self._live_status_badge)

        refresh_status_btn = QPushButton("🔄 Refresh Status")
        refresh_status_btn.setCursor(Qt.PointingHandCursor)
        refresh_status_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #E2E8F0;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 6px;
                border: 1px solid #475569;
            }
            QPushButton:hover {
                background: #475569;
                color: #FFFFFF;
            }
        """)
        top_status_row.addWidget(refresh_status_btn)
        d_lay.addLayout(top_status_row)

        self._db_info_lbl = QLabel()
        self._db_info_lbl.setStyleSheet("color: #94A3B8; font-family: monospace; font-size: 12px; line-height: 1.4;")
        d_lay.addWidget(self._db_info_lbl)

        lay.addWidget(details_box)

        def _refresh_server_and_db_info():
            stat = get_local_db_server_status()
            is_central = stat.get("is_central_server", False)
            is_running = stat.get("is_running", False)
            state = stat.get("service_state", "UNKNOWN")
            port = stat.get("port", 5432)
            svc = stat.get("service_name", "postgresql-x64-18")
            local_ip = stat.get("local_ip", "127.0.0.1")
            sync_up = stat.get("sync_running", False)

            if is_central:
                self._machine_role_lbl.setText("🖥️ Machine Role: Central Database Server Host (Primary Server)")
            else:
                srv_host = stat.get('host', '192.168.1.32')
                self._machine_role_lbl.setText(f"💻 Machine Role: Client Workstation (Connected to {srv_host})")

            if stat.get("engine") == "sqlite":
                if is_central:
                    if is_running:
                        self._live_status_badge.setText(f"🟢 SQLITE DB: ACTIVE (WAL Mode)")
                        self._live_status_badge.setStyleSheet("""
                            background-color: #064E3B;
                            color: #34D399;
                            font-size: 11px;
                            font-weight: 700;
                            padding: 4px 12px;
                            border-radius: 12px;
                            border: 1px solid #059669;
                        """)
                    else:
                        self._live_status_badge.setText(f"🔴 SQLITE DB: INACTIVE")
                        self._live_status_badge.setStyleSheet("""
                            background-color: #7F1D1D;
                            color: #F87171;
                            font-size: 11px;
                            font-weight: 700;
                            padding: 4px 12px;
                            border-radius: 12px;
                            border: 1px solid #DC2626;
                        """)
                else:
                    if is_running:
                        self._live_status_badge.setText(f"🟢 SERVER SYNC: CONNECTED ({stat.get('host')})")
                        self._live_status_badge.setStyleSheet("""
                            background-color: #064E3B;
                            color: #34D399;
                            font-size: 11px;
                            font-weight: 700;
                            padding: 4px 12px;
                            border-radius: 12px;
                            border: 1px solid #059669;
                        """)
                    else:
                        self._live_status_badge.setText(f"🔴 SERVER: OFFLINE / UNREACHABLE")
                        self._live_status_badge.setStyleSheet("""
                            background-color: #7F1D1D;
                            color: #F87171;
                            font-size: 11px;
                            font-weight: 700;
                            padding: 4px 12px;
                            border-radius: 12px;
                            border: 1px solid #DC2626;
                        """)
            else:
                if is_running:
                    self._live_status_badge.setText(f"🟢 DB SERVER: RUNNING (Port {port})")
                    self._live_status_badge.setStyleSheet("""
                        background-color: #064E3B;
                        color: #34D399;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 4px 12px;
                        border-radius: 12px;
                        border: 1px solid #059669;
                    """)
                else:
                    self._live_status_badge.setText(f"🔴 DB SERVER: {state}")
                    self._live_status_badge.setStyleSheet("""
                        background-color: #7F1D1D;
                        color: #F87171;
                        font-size: 11px;
                        font-weight: 700;
                        padding: 4px 12px;
                        border-radius: 12px;
                        border: 1px solid #DC2626;
                    """)

            sync_str = "🟢 ACTIVE (Port 8000)" if sync_up else "⚪ INACTIVE"
            port_str = "🟢 LISTENING" if stat.get("port_listening") else "🔴 CLOSED"

            if stat.get("engine") == "sqlite":
                if is_central:
                    self._db_info_lbl.setText(
                        f"• Database Engine      : SQLITE (Embedded WAL Mode)\n"
                        f"• Database File Path   : catering.db (Primary Storage)\n"
                        f"• LAN Sync Server (Hub): {sync_str}\n"
                        f"• Central Server LAN IP: {local_ip}\n"
                        f"• Kiosk Tablet Web URL : http://{local_ip}:8000\n"
                        f"• Last Status Probe    : {stat.get('timestamp', '--:--:--')}"
                    )
                else:
                    srv_host = stat.get('host', '192.168.1.32')
                    srv_port = stat.get('port', 8000)
                    conn_state = f"🟢 CONNECTED (Port {srv_port})" if sync_up else f"🔴 UNREACHABLE (Check Wi-Fi/Port {srv_port})"
                    self._db_info_lbl.setText(
                        f"• Station Mode         : Client Workstation\n"
                        f"• Central Server PC IP : {srv_host}:{srv_port}\n"
                        f"• Server Sync Link     : {conn_state}\n"
                        f"• Local Workstation IP : {local_ip}\n"
                        f"• Local Storage Cache  : catering.db\n"
                        f"• Kiosk Tablet Web URL : http://{srv_host}:8000\n"
                        f"• Last Status Probe    : {stat.get('timestamp', '--:--:--')}"
                    )
            else:
                self._db_info_lbl.setText(
                    f"• Database Engine      : {stat.get('engine', 'postgres').upper()}\n"
                    f"• PostgreSQL Service   : {svc} ({state})\n"
                    f"• Service Port (5432)  : {port_str}\n"
                    f"• LAN Sync Server (Hub): {sync_str}\n"
                    f"• Local Server LAN IP  : {local_ip}\n"
                    f"• Database Name        : {stat.get('dbname', 'jayraldines_catering')}\n"
                    f"• Last Status Probe    : {stat.get('timestamp', '--:--:--')}"
                )

        refresh_status_btn.clicked.connect(_refresh_server_and_db_info)
        _refresh_server_and_db_info()

        # ── Buttons Row ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        edit_conn_btn = QPushButton("⚙ Update Connection Settings")
        edit_conn_btn.setCursor(Qt.PointingHandCursor)
        edit_conn_btn.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: 700; padding: 8px 16px; border-radius: 6px;")
        def _open_edit_conn():
            from components.db_connection_dialog import EditDbConnectionDialog
            dlg = EditDbConnectionDialog(self, on_saved=_refresh_server_and_db_info)
            dlg.exec()
        edit_conn_btn.clicked.connect(_open_edit_conn)
        btn_row.addWidget(edit_conn_btn)

        test_btn = QPushButton("⚡ Test Server Connection")
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-weight: 700; padding: 8px 16px; border-radius: 6px;")
        def _test_conn():
            c = get_db_config()
            if c.get("engine") == "sqlite":
                import utils.db as db
                try:
                    if db.is_available():
                        row = db.fetchone("SELECT 1 as alive, COUNT(*) as b_cnt FROM bookings")
                        b_cnt = row.get("b_cnt", 0) if row else 0
                        QMessageBox.information(
                            self,
                            "Database Test",
                            f"✅ Successfully connected to SQLite Database!\n\n• Engine: SQLite (WAL Mode)\n• Bookings in DB: {b_cnt}\n• LAN Sync Hub: Port 8000"
                        )
                    else:
                        QMessageBox.warning(self, "Database Test", "❌ SQLite Database connection could not be opened.")
                except Exception as ex:
                    QMessageBox.warning(self, "Database Test", f"❌ SQLite Test Error: {ex}")
            else:
                ok, msg = test_postgres_connection(
                    host=c.get("host", "localhost"),
                    port=int(c.get("port", 5432)),
                    dbname=c.get("dbname", "jayraldines_catering"),
                    user=c.get("user", "jayraldines_app"),
                    password=c.get("password", ""),
                )
                if ok:
                    QMessageBox.information(self, "Connection Test", "✅ Successfully connected to Central PostgreSQL Server!")
                else:
                    QMessageBox.warning(self, "Connection Test", f"❌ Failed to connect:\n{msg}")
            _refresh_server_and_db_info()
        test_btn.clicked.connect(_test_conn)
        btn_row.addWidget(test_btn)

        export_creds_btn = QPushButton("Export Credentials Backup (.txt)")
        export_creds_btn.setCursor(Qt.PointingHandCursor)
        export_creds_btn.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-weight: 700; padding: 8px 16px; border-radius: 6px;")
        def _export_creds():
            from pathlib import Path
            c = get_db_config()
            content = (
                "=====================================================\n"
                "  JAYRALDINE'S CATERING - SERVER CREDENTIALS BACKUP\n"
                "=====================================================\n\n"
                f"Server Host IP : {c.get('host', 'localhost')}\n"
                f"Port           : {c.get('port', 5432)}\n"
                f"Database Name  : {c.get('dbname', 'jayraldines_catering')}\n"
                f"DB User        : {c.get('user', 'jayraldines_app')}\n"
                f"DB Password    : {c.get('password', '')}\n\n"
                f"Generated on   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Credentials Backup",
                str(Path.home() / "Desktop" / "jayraldines_credentials_backup.txt"),
                "Text Files (*.txt);;All Files (*)"
            )
            if file_path:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    QMessageBox.information(self, "Exported", f"Credentials backup saved to:\n{file_path}")
                except Exception as exc:
                    QMessageBox.warning(self, "Error", f"Could not write file: {exc}")
        export_creds_btn.clicked.connect(_export_creds)
        btn_row.addWidget(export_creds_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        # ── Central Server Host Controls (Restart / Start) ──────────────────
        if is_central_db_server_machine():
            server_ctrl_box = QFrame()
            server_ctrl_box.setStyleSheet("background: #0B1329; border: 1px dashed #334155; border-radius: 8px; padding: 14px;")
            sc_lay = QVBoxLayout(server_ctrl_box)
            sc_lay.setSpacing(10)

            sc_title = QLabel("🖥️ Central Server Maintenance Controls")
            sc_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #F8FAFC;")
            sc_lay.addWidget(sc_title)

            sc_row = QHBoxLayout()
            sc_row.setSpacing(10)

            is_owner = SessionManager.is_owner_or_superadmin()

            restart_btn = QPushButton("🔄 Restart DB Server")
            restart_btn.setCursor(Qt.PointingHandCursor)

            def _do_restart():
                confirm_reply = QMessageBox.question(
                    self, "Confirm Server Restart",
                    "Are you sure you want to restart the Central PostgreSQL Database Server?\n\n"
                    "Connected tablet kiosks and client computers will briefly reconnect.",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm_reply != QMessageBox.Yes:
                    return

                ok, msg = restart_local_db_server()
                if ok:
                    QMessageBox.information(self, "Server Restarted", f"✅ {msg}")
                else:
                    QMessageBox.warning(self, "Restart Failed", f"❌ {msg}")
                _refresh_server_and_db_info()

            if is_owner:
                # Full direct access for Owner / Super Admin
                restart_btn.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: 700; padding: 8px 16px; border-radius: 6px;")
                restart_btn.clicked.connect(_do_restart)
                sc_row.addWidget(restart_btn)
            else:
                # ADMIN ACCOUNT: Status is visible, but direct restart or start server is NOT permitted!
                # Restricted mode with Owner Authorization passkey required.
                restart_btn.setText("🔒 Restart DB Server (Owner Only)")
                restart_btn.setStyleSheet("background-color: #334155; color: #94A3B8; font-weight: 700; padding: 8px 16px; border-radius: 6px; border: 1px solid #475569;")

                def _handle_admin_restart():
                    dlg = OwnerAuthDialog(self, operation_name="Restart Central Database Server")
                    if dlg.exec():
                        _do_restart()

                restart_btn.clicked.connect(_handle_admin_restart)
                sc_row.addWidget(restart_btn)

                unlock_btn = QPushButton("🔑 Authorize as Owner")
                unlock_btn.setCursor(Qt.PointingHandCursor)
                unlock_btn.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: 600; padding: 8px 14px; border-radius: 6px;")
                def _unlock_owner():
                    dlg = OwnerAuthDialog(self, operation_name="Unlock Server Maintenance Controls")
                    if dlg.exec():
                        restart_btn.setText("🔄 Restart DB Server")
                        restart_btn.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: 700; padding: 8px 16px; border-radius: 6px;")
                        restart_btn.clicked.disconnect()
                        restart_btn.clicked.connect(_do_restart)
                        unlock_btn.setVisible(False)
                        security_notice.setText("✅ Master Owner authorized for this session. Restart DB Server is now unlocked.")
                        security_notice.setStyleSheet("font-size: 11px; color: #34D399; font-style: italic;")
                unlock_btn.clicked.connect(_unlock_owner)
            remote_access_btn = QPushButton("🌐 Allow Remote Workstations")
            remote_access_btn.setCursor(Qt.PointingHandCursor)
            remote_access_btn.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-weight: 700; padding: 8px 16px; border-radius: 6px;")
            def _do_config_remote():
                ok, msg = configure_server_remote_access()
                if ok:
                    QMessageBox.information(
                        self, "Remote Access Enabled",
                        "✅ PostgreSQL pg_hba.conf and Windows Firewall configured successfully!\n\n"
                        "Remote workstations (such as 192.168.1.34) and tablets can now connect directly to this PC Server."
                    )
                else:
                    QMessageBox.warning(self, "Setup Note", f"Result:\n{msg}")
            remote_access_btn.clicked.connect(_do_config_remote)
            sc_row.addWidget(remote_access_btn)

            sc_row.addStretch()
            sc_lay.addLayout(sc_row)

            security_notice = QLabel(
                "ℹ️ Server Control Policy: Administrator accounts can view live server status and test connectivity. "
                "Restarting or starting the central database requires Master Owner authorization."
            )
            security_notice.setStyleSheet("font-size: 11px; color: #94A3B8; font-style: italic;")
            security_notice.setWordWrap(True)
            sc_lay.addWidget(security_notice)

            lay.addWidget(server_ctrl_box)

        # ── Connected Devices & Server Activity Telemetry ──────────────────
        from components.connected_devices_panel import ConnectedDevicesPanel
        self._connected_devices_panel = ConnectedDevicesPanel(card)
        lay.addWidget(self._connected_devices_panel)

        return card

    def _build_session_security_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        sec_title = QLabel("Session Security & Auto-Lock")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        hint = QLabel("Configure how long the system waits during inactivity before locking the screen to protect catering records.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(QLabel("Idle Lock Timeout:"))

        self.timeout_combo = QComboBox()
        self.timeout_combo.addItems([
            "60 minutes (Default - Recommended)",
            "30 minutes",
            "120 minutes (2 Hours)",
            "Disabled (Never Auto-Lock)"
        ])
        timeout_map = [60, 30, 120, 0]
        cur_mins = SessionManager.get_auto_lock_minutes()
        if cur_mins in timeout_map:
            self.timeout_combo.setCurrentIndex(timeout_map.index(cur_mins))
        else:
            self.timeout_combo.setCurrentIndex(0)

        def _on_timeout_changed(idx: int):
            if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "edit"):
                return
            if 0 <= idx < len(timeout_map):
                SessionManager.set_auto_lock_minutes(timeout_map[idx])

        self.timeout_combo.currentIndexChanged.connect(_on_timeout_changed)
        self.timeout_combo.setStyleSheet("background: #1E293B; border: 1px solid #334155; color: #F8FAFC; padding: 6px 12px; border-radius: 6px;")
        if not can_edit:
            self.timeout_combo.setEnabled(False)
        row.addWidget(self.timeout_combo, 1)

        lock_now_btn = QPushButton("🔒 Lock Screen Now")
        lock_now_btn.setCursor(Qt.PointingHandCursor)
        lock_now_btn.setStyleSheet("background-color: #E11D48; color: #FFFFFF; font-weight: 700; padding: 7px 16px; border-radius: 6px;")
        def _lock_now():
            from components.login_dialog import LockScreenDialog
            dlg = LockScreenDialog(self.window())
            dlg.exec()
        lock_now_btn.clicked.connect(_lock_now)
        row.addWidget(lock_now_btn)

        lay.addLayout(row)
        return card

    def _build_business_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        sec_title = QLabel("Business Information")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")

        self._name_f    = QLineEdit(_BUSINESS_INFO["name"])
        self._contact_f = QLineEdit(_BUSINESS_INFO["contact"])
        self._email_f   = QLineEdit(_BUSINESS_INFO["email"])
        self._address_f = QLineEdit(_BUSINESS_INFO["address"])

        if not can_edit:
            self._name_f.setReadOnly(True)
            self._contact_f.setReadOnly(True)
            self._email_f.setReadOnly(True)
            self._address_f.setReadOnly(True)

        for label, field in [
            ("Business Name",  self._name_f),
            ("Contact Number", self._contact_f),
            ("Email",          self._email_f),
            ("Address",        self._address_f),
        ]:
            form.addRow(QLabel(label), field)

        lay.addLayout(form)

        self._save_notice = QLabel("")
        self._save_notice.setStyleSheet("color: #22C55E; font-size: 12px;")
        self._save_notice.hide()
        lay.addWidget(self._save_notice)

        if can_edit:
            save_btn = QPushButton("  Save Changes")
            save_btn.setObjectName("primaryButton")
            save_btn.setIcon(btn_icon_primary("check"))
            save_btn.setIconSize(QSize(15, 15))
            save_btn.setFixedWidth(160)
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.clicked.connect(self._save_business)
            lay.addWidget(save_btn, alignment=Qt.AlignRight)

        return card

    def _build_sales_targets_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        sec_title = QLabel("Monthly Sales Target Configuration")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        desc = QLabel(
            "Configure monthly revenue targets used in the Sales Report evaluation (e.g. ₱85,000.00/month). "
            "You can apply a default target to all 12 months or configure custom targets for each month."
        )
        desc.setObjectName("subtitle")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")

        top_ctrl = QHBoxLayout()
        top_ctrl.setSpacing(12)

        top_ctrl.addWidget(QLabel("Target Year:"))
        self._target_year_combo = QComboBox()
        cur_year = datetime.now().year
        for yr in [cur_year - 2, cur_year - 1, cur_year, cur_year + 1, cur_year + 2]:
            self._target_year_combo.addItem(str(yr), yr)
        self._target_year_combo.setCurrentText(str(cur_year))
        self._target_year_combo.setFixedHeight(34)
        top_ctrl.addWidget(self._target_year_combo)

        top_ctrl.addSpacing(16)
        top_ctrl.addWidget(QLabel("Quick Target:"))
        self._universal_target_spin = QDoubleSpinBox()
        self._universal_target_spin.setRange(0, 99999999)
        self._universal_target_spin.setPrefix("₱ ")
        self._universal_target_spin.setValue(85000.0)
        self._universal_target_spin.setSingleStep(5000)
        self._universal_target_spin.setFixedHeight(34)
        if not can_edit:
            self._universal_target_spin.setEnabled(False)
        top_ctrl.addWidget(self._universal_target_spin)

        if can_edit:
            apply_btn = QPushButton("  Apply to All 12 Months")
            apply_btn.setObjectName("secondaryButton")
            apply_btn.setFixedHeight(34)
            apply_btn.clicked.connect(self._apply_universal_target)
            top_ctrl.addWidget(apply_btn)
        top_ctrl.addStretch()

        lay.addLayout(top_ctrl)

        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(10)
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        self._month_target_spins = {}
        for m in range(1, 13):
            m_lbl = QLabel(f"<b>{month_names[m-1]}:</b>")
            m_spin = QDoubleSpinBox()
            m_spin.setRange(0, 99999999)
            m_spin.setPrefix("₱ ")
            m_spin.setValue(85000.0)
            m_spin.setSingleStep(5000)
            m_spin.setFixedHeight(32)
            if not can_edit:
                m_spin.setEnabled(False)
            self._month_target_spins[m] = m_spin
            row = (m - 1) // 3
            col = (m - 1) % 3
            grid.addWidget(m_lbl, row * 2, col)
            grid.addWidget(m_spin, row * 2 + 1, col)

        lay.addLayout(grid)

        if can_edit:
            save_btn = QPushButton("  Save Sales Targets")
            save_btn.setObjectName("primaryButton")
            save_btn.setIcon(btn_icon_primary("check"))
            save_btn.setIconSize(QSize(15, 15))
            save_btn.setFixedWidth(180)
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.clicked.connect(self._save_sales_targets)
            lay.addWidget(save_btn, alignment=Qt.AlignRight)

        self._target_year_combo.currentIndexChanged.connect(self._load_sales_targets)
        return card

    def _load_sales_targets(self):
        try:
            yr = int(self._target_year_combo.currentText())
            from utils.data_loader import run_async
            run_async(self, lambda y=yr: repo.get_monthly_sales_targets(y), self._on_sales_targets_loaded)
        except Exception as e:
            print(f"[SettingsPage] Error requesting sales targets: {e}")

    def _on_sales_targets_loaded(self, targets):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        targets = targets or {}
        for m, spin in getattr(self, "_month_target_spins", {}).items():
            spin.setValue(float(targets.get(m, 85000.0)))

    def _apply_universal_target(self):
        val = self._universal_target_spin.value()
        for spin in self._month_target_spins.values():
            spin.setValue(val)

    def _save_sales_targets(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "edit"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot modify sales targets.")
            return
        try:
            yr = int(self._target_year_combo.currentText())
            for m, spin in self._month_target_spins.items():
                repo.set_monthly_sales_target(yr, m, spin.value())
            success(self, message=f"Monthly sales targets for {yr} saved successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save targets: {e}")

    def _build_policy_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        sec_title = QLabel("Booking & Capacity Policy")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")
        policy = {"min_downpayment_pct": 30.0, "allow_zero_downpayment": False, "max_daily_pax": 600}

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        self._min_dp_spin = QDoubleSpinBox()
        self._min_dp_spin.setRange(0, 100)
        self._min_dp_spin.setSuffix(" %")
        self._min_dp_spin.setValue(policy["min_downpayment_pct"])
        if not can_edit:
            self._min_dp_spin.setEnabled(False)
        form.addRow(QLabel("Minimum Downpayment"), self._min_dp_spin)

        self._allow_zero_cb = QCheckBox("Allow confirming without downpayment")
        self._allow_zero_cb.setChecked(policy["allow_zero_downpayment"])
        if not can_edit:
            self._allow_zero_cb.setEnabled(False)
        form.addRow(QLabel("Override"), self._allow_zero_cb)

        self._max_pax_spin = QSpinBox()
        self._max_pax_spin.setRange(1, 10000)
        self._max_pax_spin.setSuffix(" pax")
        self._max_pax_spin.setValue(policy["max_daily_pax"])
        if not can_edit:
            self._max_pax_spin.setEnabled(False)
        form.addRow(QLabel("Max Daily Capacity"), self._max_pax_spin)

        lay.addLayout(form)

        if can_edit:
            save_btn = QPushButton("  Save Policy")
            save_btn.setObjectName("primaryButton")
            save_btn.setIcon(btn_icon_primary("check"))
            save_btn.setIconSize(QSize(15, 15))
            save_btn.setFixedWidth(140)
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.clicked.connect(self._save_policy)
            lay.addWidget(save_btn, alignment=Qt.AlignRight)

        return card

    def _build_smtp_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        sec_title = QLabel("Email (SMTP) Configuration")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        sub = QLabel("Used for sending receipts and booking confirmations. Gmail: use App Password with port 587.")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")
        smtp = {"smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_user": "", "smtp_pass": ""}

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        self._smtp_host_f = QLineEdit(smtp["smtp_host"])
        self._smtp_host_f.setPlaceholderText("smtp.gmail.com")
        self._smtp_port_f = QSpinBox()
        self._smtp_port_f.setRange(1, 65535)
        self._smtp_port_f.setValue(smtp["smtp_port"])
        self._smtp_user_f = QLineEdit(smtp["smtp_user"])
        self._smtp_user_f.setPlaceholderText("your@email.com")
        self._smtp_pass_f = QLineEdit(smtp["smtp_pass"])
        self._smtp_pass_f.setEchoMode(QLineEdit.Password)
        self._smtp_pass_f.setPlaceholderText("App password or SMTP password")
        from utils.password_field import add_show_password_toggle
        add_show_password_toggle(self._smtp_pass_f)

        if not can_edit:
            self._smtp_host_f.setReadOnly(True)
            self._smtp_port_f.setEnabled(False)
            self._smtp_user_f.setReadOnly(True)
            self._smtp_pass_f.setReadOnly(True)

        for label, field in [
            ("SMTP Host",     self._smtp_host_f),
            ("Port",          self._smtp_port_f),
            ("Username",      self._smtp_user_f),
            ("Password",      self._smtp_pass_f),
        ]:
            form.addRow(QLabel(label), field)

        lay.addLayout(form)

        if can_edit:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(12)

            test_btn = QPushButton("  Test Connection")
            test_btn.setObjectName("secondaryButton")
            test_btn.setIcon(get_icon("bell", color="#64748B", size=QSize(15, 15)))
            test_btn.setIconSize(QSize(15, 15))
            test_btn.setFixedWidth(160)
            test_btn.setCursor(Qt.PointingHandCursor)
            test_btn.clicked.connect(self._test_smtp)
            btn_row.addWidget(test_btn)

            save_btn = QPushButton("  Save SMTP Config")
            save_btn.setObjectName("primaryButton")
            save_btn.setIcon(btn_icon_primary("check"))
            save_btn.setIconSize(QSize(15, 15))
            save_btn.setFixedWidth(180)
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.clicked.connect(self._save_smtp)
            btn_row.addWidget(save_btn)

            lay.addLayout(btn_row)

        return card

    def _build_theme_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        header_row = QHBoxLayout()
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)

        sec_title = QLabel("Appearance & Themes")
        sec_title.setObjectName("h3")
        sec_sub = QLabel("Select from curated theme palettes across nature, mood, colors, vibes, and seasons.")
        sec_sub.setObjectName("subtitle")
        v_titles.addWidget(sec_title)
        v_titles.addWidget(sec_sub)
        header_row.addLayout(v_titles, 1)

        self._theme_lbl = QLabel(self._theme.palette.get("name", "Dark Mode"))
        self._theme_lbl.setStyleSheet(f"color: {AccentManager().current}; font-size: 13px; font-weight: 700;")
        header_row.addWidget(self._theme_lbl)

        toggle_btn = QPushButton("  Toggle Dark/Light")
        toggle_btn.setObjectName("secondaryButton")
        toggle_btn.setFixedWidth(160)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.clicked.connect(self._toggle_theme)
        header_row.addWidget(toggle_btn)
        lay.addLayout(header_row)

        # ── Category Filter Pills ──────────────────────────────────────────
        self._active_category = "All"
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(46)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        cat_w = QWidget()
        self._cat_row = QHBoxLayout(cat_w)
        self._cat_row.setContentsMargins(0, 4, 0, 4)
        self._cat_row.setSpacing(8)

        self._cat_buttons = []
        for cat in ["All"] + THEME_CATEGORIES:
            btn = QPushButton(cat)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda _, c=cat: self._on_select_category(c))
            self._cat_row.addWidget(btn)
            self._cat_buttons.append((cat, btn))

        self._cat_row.addStretch()
        cat_scroll.setWidget(cat_w)
        lay.addWidget(cat_scroll)
        self._update_cat_buttons_style()

        # ── Palette Cards Container (Compact & Space Conserving) ────────────
        self._palettes_scroll = QScrollArea()
        self._palettes_scroll.setFixedHeight(230)
        self._palettes_scroll.setWidgetResizable(True)
        self._palettes_scroll.setFrameShape(QFrame.NoFrame)
        self._palettes_scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self._palettes_widget = QWidget()
        self._palettes_container = QVBoxLayout(self._palettes_widget)
        self._palettes_container.setContentsMargins(0, 0, 8, 0)
        self._palettes_container.setSpacing(8)
        self._palettes_scroll.setWidget(self._palettes_widget)
        lay.addWidget(self._palettes_scroll)
        self._rebuild_palette_cards()

        # ── Accent Color Customizer ─────────────────────────────────────────
        accent_divider = QFrame()
        accent_divider.setFrameShape(QFrame.HLine)
        accent_divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        lay.addWidget(accent_divider)

        color_lbl = QLabel("Primary Accent Color")
        color_lbl.setStyleSheet("font-size: 14px; font-weight: 700; margin-top: 4px;")
        lay.addWidget(color_lbl)

        self._swatch_container = QVBoxLayout()
        self._swatch_container.setSpacing(8)
        lay.addLayout(self._swatch_container)
        self._rebuild_color_swatches()

        return card

    # ── Category & Palette Selection ────────────────────────────────────────

    def _on_select_category(self, cat: str):
        self._active_category = cat
        self._update_cat_buttons_style()
        self._rebuild_palette_cards()

    def _update_cat_buttons_style(self):
        for cat, btn in self._cat_buttons:
            if cat == self._active_category:
                btn.setStyleSheet(
                    f"background: {AccentManager().current}; color: #FFFFFF; font-weight: 700; "
                    f"border-radius: 16px; padding: 0 16px; border: none; font-size: 12px;"
                )
            else:
                dark = self._theme.is_dark()
                bg = "rgba(255, 255, 255, 0.05)" if dark else "rgba(0, 0, 0, 0.05)"
                fg = "#94A3B8" if dark else "#64748B"
                border = "#334155" if dark else "#CBD5E1"
                btn.setStyleSheet(
                    f"background: {bg}; color: {fg}; font-weight: 600; "
                    f"border-radius: 16px; padding: 0 16px; border: 1px solid {border}; font-size: 12px;"
                )

    def _rebuild_palette_cards(self):
        self._clear_layout(self._palettes_container)

        by_cat = get_palettes_by_category()
        categories_to_show = [self._active_category] if self._active_category != "All" else THEME_CATEGORIES

        for cat in categories_to_show:
            palettes = by_cat.get(cat, [])
            if not palettes:
                continue

            if self._active_category == "All":
                cat_head = QLabel(cat)
                cat_head.setStyleSheet("font-weight: 700; font-size: 12px; color: #94A3B8; margin-top: 4px; margin-bottom: 2px;")
                self._palettes_container.addWidget(cat_head)

            # Compact Grid in rows of 4
            current_row = QHBoxLayout()
            current_row.setSpacing(8)
            cards_in_row = 0

            for pal in palettes:
                card = self._create_palette_card(pal)
                current_row.addWidget(card)
                cards_in_row += 1
                if cards_in_row == 4:
                    self._palettes_container.addLayout(current_row)
                    current_row = QHBoxLayout()
                    current_row.setSpacing(8)
                    cards_in_row = 0

            if cards_in_row > 0:
                current_row.addStretch()
                self._palettes_container.addLayout(current_row)

    def _create_palette_card(self, pal: dict) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(54)
        card.setMinimumWidth(170)

        is_active = self._theme.palette_id == pal["id"]
        dark = self._theme.is_dark()
        active_border = f"2px solid {pal['primary']}" if is_active else ("1px solid #334155" if dark else "1px solid #E2E8F0")
        card_bg = pal["surface"]

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: {active_border};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 2px solid {pal['primary']};
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(4)

        top_row = QHBoxLayout()
        name_lbl = QLabel(pal["name"])
        name_lbl.setStyleSheet(f"color: {pal['text_primary']}; font-weight: 700; font-size: 11px;")
        top_row.addWidget(name_lbl, 1)

        mode_badge = QLabel(f"{pal['mode'][:1].upper()}")
        mode_color = "#38BDF8" if pal["mode"] == "dark" else "#F59E0B"
        mode_badge.setStyleSheet(f"background: rgba(255,255,255,0.08); color: {mode_color}; font-size: 9px; font-weight: 800; border-radius: 4px; padding: 1px 4px;")
        top_row.addWidget(mode_badge)

        if is_active:
            check_lbl = QLabel("✓")
            check_lbl.setStyleSheet(f"color: {pal['primary']}; font-weight: 900; font-size: 12px;")
            top_row.addWidget(check_lbl)

        lay.addLayout(top_row)

        # 4-bar mini swatch preview dots
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(3)
        colors = [pal["background"], pal["surface"], pal["primary"], pal["text_primary"]]
        for c in colors:
            sw = QFrame()
            sw.setFixedHeight(6)
            sw.setStyleSheet(f"background-color: {c}; border-radius: 3px; border: 1px solid rgba(0,0,0,0.12);")
            swatch_row.addWidget(sw, 1)
        lay.addLayout(swatch_row)

        card.mousePressEvent = lambda _, pid=pal["id"]: self._on_select_palette(pid)
        return card

    def _on_select_palette(self, palette_id: str):
        self._theme.apply_palette(palette_id)
        self._theme_lbl.setText(self._theme.palette.get("name", "Dark Mode"))
        self._theme_lbl.setStyleSheet(f"color: {AccentManager().current}; font-size: 13px; font-weight: 700;")
        self._update_cat_buttons_style()
        QTimer.singleShot(120, self._rebuild_palette_cards)
        QTimer.singleShot(120, self._rebuild_color_swatches)
        success(self, message=f"Theme set to '{self._theme.palette.get('name')}'")

    # ── Color theme picker ──────────────────────────────────────────────

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _make_swatch(self, hex_color: str, removable: bool = False) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        selected = hex_color.upper() == self._accent.current.upper()
        ring = "#F9FAFB" if self._theme.is_dark() else "#0F172A"
        border = f"3px solid {ring}" if selected else "3px solid transparent"
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {hex_color}; border-radius: 14px; border: {border}; }}"
        )
        btn.setToolTip(hex_color.upper() + (" (right-click to remove)" if removable else ""))
        btn.clicked.connect(lambda _checked=False, h=hex_color: self._select_accent(h))
        if removable:
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda _pos, h=hex_color: self._remove_custom_color(h))
        return btn

    def _rebuild_color_swatches(self):
        self._clear_layout(self._swatch_container)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for _name, hex_color in PRESET_THEMES:
            preset_row.addWidget(self._make_swatch(hex_color))
        preset_row.addStretch()
        self._swatch_container.addLayout(preset_row)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        for hex_color in self._accent.custom_colors:
            custom_row.addWidget(self._make_swatch(hex_color, removable=True))

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setCursor(Qt.PointingHandCursor)
        dark = self._theme.is_dark()
        muted_border = "#4B5563" if dark else "#CBD5E1"
        muted_text = "#9CA3AF" if dark else "#64748B"
        add_btn.setStyleSheet(
            f"QPushButton {{ border-radius: 14px; border: 2px dashed {muted_border}; "
            f"color: {muted_text}; font-weight: 700; background: transparent; }}"
            f"QPushButton:hover {{ border-color: {self._accent.current}; color: {self._accent.current}; }}"
        )
        add_btn.setToolTip("Add a custom color")
        add_btn.clicked.connect(self._pick_custom_color)
        custom_row.addWidget(add_btn)
        custom_row.addStretch()
        self._swatch_container.addLayout(custom_row)

    def _select_accent(self, hex_color: str):
        self._accent.set_accent(hex_color)
        self._rebuild_color_swatches()
        self._rebuild_palette_cards()

    def _pick_custom_color(self):
        color = QColorDialog.getColor(QColor(self._accent.current), self, "Choose a Custom Color")
        if not color.isValid():
            return
        hex_color = color.name().upper()
        self._accent.add_custom_color(hex_color)
        self._accent.set_accent(hex_color)
        self._rebuild_color_swatches()
        self._rebuild_palette_cards()

    def _remove_custom_color(self, hex_color: str):
        self._accent.remove_custom_color(hex_color)
        self._rebuild_color_swatches()

    def _build_backup_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        sec_title = QLabel("Database Backup & Restore")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        sub = QLabel("Backup exports the full database to a .sql file. Restore will overwrite current data.")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        backup_btn = QPushButton("  Backup Database")
        backup_btn.setObjectName("primaryButton")
        backup_btn.setIcon(btn_icon_primary("export"))
        backup_btn.setIconSize(QSize(15, 15))
        backup_btn.setCursor(Qt.PointingHandCursor)
        backup_btn.clicked.connect(self._backup_db)
        btn_row.addWidget(backup_btn)

        if can_edit:
            restore_btn = QPushButton("  Restore Database")
            restore_btn.setObjectName("secondaryButton")
            restore_btn.setCursor(Qt.PointingHandCursor)
            restore_btn.setToolTip("DESTRUCTIVE: completely replaces all current data with the backup file.\nUse 'Merge Data from Another Device' instead if you just want to bring in another device's records.")
            restore_btn.clicked.connect(self._restore_db)
            btn_row.addWidget(restore_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        if can_edit:
            div = QFrame()
            div.setObjectName("divider")
            lay.addWidget(div)

            merge_title = QLabel("Merge Data from Another Device (Safe)")
            merge_title.setStyleSheet("font-weight: 700; font-size: 13px;")
            lay.addWidget(merge_title)

            merge_sub = QLabel(
                "For multiple devices (e.g. a PC and a laptop) that each have their own bookings and "
                "payments. This safely combines the other device's backup into this database — it never "
                "deletes or downgrades a payment/status that already exists here (Paid stays Paid, Partial "
                "stays at least Partial), only adds genuinely new bookings and payments."
            )
            merge_sub.setObjectName("subtitle")
            merge_sub.setWordWrap(True)
            lay.addWidget(merge_sub)

            merge_btn = QPushButton("  Merge Backup File Into This Database...")
            merge_btn.setObjectName("secondaryButton")
            merge_btn.setCursor(Qt.PointingHandCursor)
            merge_btn.clicked.connect(self._merge_db)
            lay.addWidget(merge_btn, alignment=Qt.AlignLeft)

        return card

    def _merge_db(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "edit"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot merge external database files.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup Database File to Merge", "",
            "All Supported Files (*.db *.bak *.sql);;SQLite Database (*.db *.bak);;SQL Dump (*.sql);;All Files (*.*)"
        )
        if not path:
            return
        if not confirm(
            self, title="Merge Database",
            message=(
                "This will merge bookings, customers, payments, and additional charges from:\n\n"
                f"{path}\n\n"
                "into this device's database. Existing payments and Paid/Partial statuses here will "
                "never be removed or downgraded — only new records are added. Continue?"
            ),
            confirm_label="Merge",
        ):
            return

        dlg = DatabaseRestoreProgressDialog(self)
        dlg.set_status("Analyzing and merging database records...")

        class MergeWorker(QThread):
            merge_finished = Signal(dict)
            def run(self):
                import utils.importer as importer
                from utils.session import get_actor
                stats = importer.merge_database_file(path, actor=get_actor())
                self.merge_finished.emit(stats)

        worker = MergeWorker(self)

        def _on_merge_done(stats):
            dlg.accept()
            if stats.get("errors"):
                QMessageBox.warning(self, "Merge Completed With Warnings",
                    "Merge finished, but some issues occurred:\n\n" + "\n".join(stats["errors"][:10]))
            summary = (
                f"New customers added: {stats.get('new_customers', 0)}\n"
                f"Existing customers matched: {stats.get('matched_customers', 0)}\n"
                f"New bookings added: {stats.get('new_bookings', 0)}\n"
                f"Existing bookings matched: {stats.get('matched_bookings', 0)}\n"
                f"New payments merged: {stats.get('new_payments', 0)}\n"
                f"New additional charges merged: {stats.get('new_charges', 0)}\n"
                f"Terms acknowledgements merged: {stats.get('terms_merged', 0)}\n"
                f"Invoices recalculated: {stats.get('invoices_recalculated', 0)}"
            )
            success(self, message=f"Database merge complete.\n\n{summary}")
            try:
                from utils.signals import app_events
                app_events().data_changed.emit()
                app_events().booking_saved.emit()
                app_events().booking_updated.emit()
            except Exception:
                pass

        worker.merge_finished.connect(_on_merge_done)
        worker.start()
        dlg.exec()

    def _build_tablet_sync_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        sec_title = QLabel("Tablet App Sync")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        sub = QLabel(
            "Export the current packages, menu items, and prices for use in the Tablet App "
            "(Settings → Import Master Data on the tablet). Tablet orders are transferred back "
            "into this PC using the 'Merge Backup File Into This Database' option above."
        )
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        export_btn = QPushButton("  Export Tablet Master Data...")
        export_btn.setObjectName("primaryButton")
        export_btn.setIcon(btn_icon_primary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_tablet_master_data)
        lay.addWidget(export_btn, alignment=Qt.AlignLeft)

        return card

    def _export_tablet_master_data(self):
        from datetime import datetime as _dt
        default_name = f"tablet_master_data_{_dt.now().strftime('%Y%m%d')}.db"
        path, _ = QFileDialog.getSaveFileName(self, "Export Tablet Master Data", default_name, "SQLite Database (*.db)")
        if not path:
            return
        import utils.exporter as exporter
        stats = exporter.export_tablet_master_data(path)
        if stats.get("errors"):
            QMessageBox.warning(self, "Export Failed", "\n".join(stats["errors"]))
            return
        prompt_file_saved(
            self, path, title="Tablet Master Data Exported",
            message=f"{stats['packages']} Packages, {stats['menu_items']} Menu Items, {stats['package_items']} Package Items exported.\n\nImport this file on the tablet via Settings → Import Master Data.",
        )

    def _build_import_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        sec_title = QLabel("Data Import & Export Migration")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        sub = QLabel("Import or export Bookings, Customers, Expenses, Menu Items, or Billings using pre-formatted Excel or CSV templates.")
        sub.setObjectName("subtitle")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        can_create = SessionManager.is_admin() or SessionManager.has_permission("settings", "create") or SessionManager.has_permission("settings", "edit")

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        if can_create:
            import_btn = QPushButton("  Open Data Import Wizard")
            import_btn.setObjectName("primaryButton")
            import_btn.setIcon(btn_icon_primary("export"))
            import_btn.setIconSize(QSize(15, 15))
            import_btn.setCursor(Qt.PointingHandCursor)
            import_btn.clicked.connect(self._open_import_wizard)
            btn_row.addWidget(import_btn)

        export_btn = QPushButton("  Open Data Export Wizard")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._open_export_wizard)
        btn_row.addWidget(export_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)
        return card

    def _open_import_wizard(self):
        if not SessionManager.is_admin() and not (SessionManager.has_permission("settings", "create") or SessionManager.has_permission("settings", "edit")):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot import data.")
            return
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="customers", parent=self)
        dlg.exec()

    def _open_export_wizard(self):
        from components.export_dialog import ExportWizardDialog
        dlg = ExportWizardDialog(parent=self)
        dlg.exec()

    def _build_occasions_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")
        can_create = SessionManager.is_admin() or SessionManager.has_permission("settings", "create")
        can_delete = SessionManager.is_admin() or SessionManager.has_permission("settings", "delete")

        head = QHBoxLayout()
        sec_title = QLabel("Occasion Types")
        sec_title.setObjectName("h3")
        head.addWidget(sec_title)
        head.addStretch()
        if can_create:
            add_btn = QPushButton("  Add")
            add_btn.setObjectName("primaryButton")
            add_btn.setFixedHeight(30)
            add_btn.setIcon(btn_icon_primary("plus"))
            add_btn.clicked.connect(self._add_occasion)
            head.addWidget(add_btn)
        lay.addLayout(head)

        self._occ_list = QListWidget()
        self._occ_list.setFixedHeight(200)
        self._occ_list.setFocusPolicy(Qt.NoFocus)
        lay.addWidget(self._occ_list)

        if can_edit or can_delete:
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            if can_edit:
                edit_btn = QPushButton("  Rename")
                edit_btn.setObjectName("secondaryButton")
                edit_btn.setFixedHeight(30)
                edit_btn.clicked.connect(self._edit_occasion)
                btn_row.addWidget(edit_btn)
            if can_delete:
                del_btn = QPushButton("  Delete")
                del_btn.setObjectName("secondaryButton")
                del_btn.setFixedHeight(30)
                del_btn.clicked.connect(self._delete_occasion)
                btn_row.addWidget(del_btn)
            lay.addLayout(btn_row)

        return card

    def _load_occasions(self):
        from utils.data_loader import run_async
        run_async(self, repo.get_all_occasions, self._on_occasions_loaded)

    def _on_occasions_loaded(self, occasions):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        if hasattr(self, "_occ_list"):
            self._occ_list.clear()
            for name in (occasions or []):
                self._occ_list.addItem(QListWidgetItem(name))

    def _add_occasion(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "create"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot add occasion types.")
            return
        text, ok = QInputDialog.getText(self, "Add Occasion", "Occasion name:")
        if ok and text.strip():
            try:
                repo.add_occasion(text.strip())
                self._load_occasions()
                app_events().data_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _edit_occasion(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "edit"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot edit occasion types.")
            return
        item = self._occ_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select an occasion to rename.")
            return
        old_name = item.text()
        text, ok = QInputDialog.getText(self, "Rename Occasion", "New name:", text=old_name)
        if ok and text.strip() and text.strip() != old_name:
            try:
                repo.update_occasion(old_name, text.strip())
                self._load_occasions()
                app_events().data_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_occasion(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "delete"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot delete occasion types.")
            return
        item = self._occ_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select an occasion to delete.")
            return
        name = item.text()
        reply = QMessageBox.question(
            self, "Delete Occasion",
            f"Delete '{name}'? Existing bookings using this occasion will not be affected.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                repo.delete_occasion(name)
                self._load_occasions()
                app_events().data_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _build_menu_categories_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        can_edit = SessionManager.is_admin() or SessionManager.has_permission("settings", "edit")
        can_create = SessionManager.is_admin() or SessionManager.has_permission("settings", "create")
        can_delete = SessionManager.is_admin() or SessionManager.has_permission("settings", "delete")

        head = QHBoxLayout()
        sec_title = QLabel("Menu Categories")
        sec_title.setObjectName("h3")
        head.addWidget(sec_title)
        head.addStretch()
        if can_create:
            add_btn = QPushButton("  Add")
            add_btn.setObjectName("primaryButton")
            add_btn.setFixedHeight(30)
            add_btn.setIcon(btn_icon_primary("plus"))
            add_btn.clicked.connect(self._add_menu_category)
            head.addWidget(add_btn)
        lay.addLayout(head)

        hint = QLabel("Categories available when adding/editing a menu item (e.g. Main Course, Dessert).")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self._mc_list = QListWidget()
        self._mc_list.setFixedHeight(200)
        self._mc_list.setFocusPolicy(Qt.NoFocus)
        lay.addWidget(self._mc_list)
        self._load_menu_categories()

        if can_edit or can_delete:
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            if can_edit:
                edit_btn = QPushButton("  Rename")
                edit_btn.setObjectName("secondaryButton")
                edit_btn.setFixedHeight(30)
                edit_btn.clicked.connect(self._edit_menu_category)
                btn_row.addWidget(edit_btn)
            if can_delete:
                del_btn = QPushButton("  Delete")
                del_btn.setObjectName("secondaryButton")
                del_btn.setFixedHeight(30)
                del_btn.clicked.connect(self._delete_menu_category)
                btn_row.addWidget(del_btn)
            lay.addLayout(btn_row)

        return card

    def _load_menu_categories(self):
        from utils.data_loader import run_async
        run_async(self, repo.get_all_menu_categories, self._on_menu_categories_loaded)

    def _on_menu_categories_loaded(self, categories):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        if hasattr(self, "_mc_list"):
            self._mc_list.clear()
            for name in (categories or []):
                self._mc_list.addItem(QListWidgetItem(name))

    def _add_menu_category(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "create"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot add menu categories.")
            return
        text, ok = QInputDialog.getText(self, "Add Menu Category", "Category name:")
        if ok and text.strip():
            try:
                repo.add_menu_category(text.strip())
                self._load_menu_categories()
                app_events().menu_saved.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _edit_menu_category(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "edit"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot edit menu categories.")
            return
        item = self._mc_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select a category to rename.")
            return
        old_name = item.text()
        text, ok = QInputDialog.getText(self, "Rename Menu Category", "New name:", text=old_name)
        if ok and text.strip() and text.strip() != old_name:
            try:
                repo.update_menu_category(old_name, text.strip())
                self._load_menu_categories()
                app_events().menu_saved.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _delete_menu_category(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "delete"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot delete menu categories.")
            return
        item = self._mc_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select a category to delete.")
            return
        name = item.text()
        reply = QMessageBox.question(
            self, "Delete Menu Category",
            f"Delete '{name}'? Existing menu items using this category will keep it as free text until re-edited.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                repo.delete_menu_category(name)
                self._load_menu_categories()
                app_events().menu_saved.emit()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _build_audit_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        head = QHBoxLayout()
        sec_title = QLabel("Audit Log")
        sec_title.setObjectName("h3")
        head.addWidget(sec_title)
        head.addStretch()

        filter_lbl = QLabel("Filter:")
        filter_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 600;")
        head.addWidget(filter_lbl)

        self.audit_device_filter = QComboBox()
        self.audit_device_filter.addItems(["All Logs & Devices", "Tablet Kiosks", "Desktop / Server"])
        self.audit_device_filter.setFixedHeight(30)
        self.audit_device_filter.setCursor(Qt.PointingHandCursor)
        self.audit_device_filter.currentIndexChanged.connect(self._load_audit_log)
        head.addWidget(self.audit_device_filter)

        refresh_btn = QPushButton("  Refresh")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.setFixedHeight(30)
        refresh_btn.clicked.connect(self._load_audit_log)
        head.addWidget(refresh_btn)
        lay.addLayout(head)

        self.audit_scroll = QScrollArea()
        self.audit_scroll.setWidgetResizable(True)
        self.audit_scroll.setFrameShape(QFrame.NoFrame)
        self.audit_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.audit_scroll.setStyleSheet("background: transparent;")
        self.audit_scroll.setMinimumHeight(260)

        self.audit_cards_container = QWidget()
        self.audit_cards_container.setStyleSheet("background: transparent;")
        self.audit_cards_layout = QVBoxLayout(self.audit_cards_container)
        self.audit_cards_layout.setContentsMargins(0, 0, 10, 0)
        self.audit_cards_layout.setSpacing(8)

        self.audit_scroll.setWidget(self.audit_cards_container)
        lay.addWidget(self.audit_scroll)

        self._load_audit_log()
        return card

    def _load_audit_log(self):
        # Coalesce overlapping reloads: multiple data-changed signals (data_changed,
        # customer_saved, booking_saved, payment_saved), showEvent, reload(), the
        # filter and the refresh button can all fire in quick succession. If a
        # fetch + batch-render is already running, don't start a second one in
        # parallel - just remember to run exactly one more pass once it finishes.
        if getattr(self, "_audit_reload_in_flight", False):
            self._audit_reload_pending = True
            return
        self._audit_reload_in_flight = True
        self._audit_reload_pending = False

        from utils.data_loader import run_async
        dev_choice = self.audit_device_filter.currentText() if hasattr(self, "audit_device_filter") else "All Logs & Devices"
        dev_filter = None
        if "Tablet" in dev_choice:
            dev_filter = "Tablet"
        elif "Desktop" in dev_choice:
            dev_filter = "Desktop"
        run_async(self, lambda: repo.get_audit_log(50, device_filter=dev_filter), self._on_audit_logs_loaded)

    def _audit_reload_finished(self):
        self._audit_reload_in_flight = False
        if getattr(self, "_audit_reload_pending", False):
            self._audit_reload_pending = False
            QTimer.singleShot(0, self._load_audit_log)

    def _on_audit_logs_loaded(self, logs):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        # Invalidate any batch render still in flight from a previous call.
        self._audit_render_token = getattr(self, "_audit_render_token", 0) + 1
        token = self._audit_render_token

        while self.audit_cards_layout.count():
            item = self.audit_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not logs:
            empty_card = QFrame()
            empty_card.setObjectName("entryCard")
            el = QVBoxLayout(empty_card)
            item = QLabel("No audit entries found for this filter.")
            item.setObjectName("subtitle")
            item.setAlignment(Qt.AlignCenter)
            el.addWidget(item)
            self.audit_cards_layout.addWidget(empty_card)
            self.audit_cards_layout.addStretch()
            # No batches run on the empty path - finish the reload cycle now.
            self._audit_reload_finished()
            return

        # Render incrementally so a large audit log never blocks the UI thread.
        self._audit_render_queue = list(logs)
        self._render_next_audit_batch(token)

    def _render_next_audit_batch(self, token, batch_size=15):
        # Bail out if a newer render started or the page was destroyed.
        if token != getattr(self, "_audit_render_token", 0):
            return
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass

        # Per-item-invariant lookup table, built once per batch (not per row).
        action_colors = {
            "APPROVE": "#22C55E", "CREATE": "#3B82F6", "ADD": "#3B82F6", "CANCEL": "#EF4444",
            "DELETE": "#EF4444", "REMOVE": "#EF4444", "PAYMENT": "#10B981", "DOWN_PAYMENT": "#10B981",
            "UPDATE": "#8B5CF6", "EDIT": "#8B5CF6", "STATUS_CHANGE": "#6366F1",
            "ADD_CHARGE": "#38BDF8", "DELETE_CHARGE": "#F43F5E",
            "FOLLOW_UP": "#EC4899", "COMPLETE_FOLLOW_UP": "#14B8A6", "DELETE_FOLLOW_UP": "#64748B",
            "ADJUST_STOCK": "#06B6D4", "MERGE_IMPORT": "#F59E0B", "REPLACE_IMPORT": "#EA580C",
        }

        batch = self._audit_render_queue[:batch_size]
        self._audit_render_queue = self._audit_render_queue[batch_size:]

        self.audit_cards_container.setUpdatesEnabled(False)
        try:
            for log in batch:
                card = QFrame()
                card.setObjectName("entryCard")
                cl = QHBoxLayout(card)
                cl.setContentsMargins(12, 10, 12, 10)
                cl.setSpacing(14)

                c1 = QVBoxLayout()
                c1.setSpacing(3)
                act_str = log.get("action", "LOG")
                act_color = action_colors.get(act_str, "#9CA3AF")
                act_lbl = QLabel(act_str)
                act_lbl.setStyleSheet(f"font-weight: 800; font-size: 11px; color: {act_color}; padding: 2px 6px; background: rgba(255,255,255,0.05); border-radius: 4px;")
                actor_lbl = QLabel(f"By: {log.get('actor', 'User')}")
                actor_lbl.setObjectName("subtitle")

                dev_val = str(log.get("device") or "Desktop / Server")
                is_tablet = "tablet" in dev_val.lower() or "kiosk" in dev_val.lower()
                dev_icon = "📱" if is_tablet else "💻"
                dev_color = "#38BDF8" if is_tablet else "#10B981"
                dev_badge = QLabel(f"{dev_icon} {dev_val}")
                dev_badge.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {dev_color};")

                c1.addWidget(act_lbl, alignment=Qt.AlignLeft)
                c1.addWidget(actor_lbl)
                c1.addWidget(dev_badge)
                cl.addLayout(c1, 1)

                desc_lbl = QLabel(log.get("description", ""))
                desc_lbl.setStyleSheet("font-size: 12px;")
                desc_lbl.setWordWrap(True)
                cl.addWidget(desc_lbl, 4)

                time_lbl = QLabel(log.get("created_at", ""))
                time_lbl.setStyleSheet("font-size: 11px; color: #6B7280;")
                cl.addWidget(time_lbl, 2)

                self.audit_cards_layout.addWidget(card)
        finally:
            self.audit_cards_container.setUpdatesEnabled(True)

        if self._audit_render_queue:
            # Yield to the event loop before rendering the next batch.
            QTimer.singleShot(0, lambda: self._render_next_audit_batch(token, batch_size))
        else:
            self.audit_cards_layout.addStretch()
            # Full pipeline (fetch + all batches) done - finish the reload cycle.
            self._audit_reload_finished()

    def _build_daily_report_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        sec_title = QLabel("Daily Activity Report")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        hint = QLabel("Export a report of who did what — orders added, payments recorded, charges added, cancellations — for a specific date or date range.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(10)

        row.addWidget(QLabel("From:"))
        self._report_from = QDateEdit(QDate.currentDate())
        self._report_from.setCalendarPopup(True)
        self._report_from.setDisplayFormat("MMM d, yyyy")
        row.addWidget(self._report_from)

        row.addWidget(QLabel("To:"))
        self._report_to = QDateEdit(QDate.currentDate())
        self._report_to.setCalendarPopup(True)
        self._report_to.setDisplayFormat("MMM d, yyyy")
        row.addWidget(self._report_to)

        row.addStretch()

        export_pdf_btn = QPushButton("  Export PDF")
        export_pdf_btn.setObjectName("primaryButton")
        export_pdf_btn.setIcon(btn_icon_primary("export"))
        export_pdf_btn.setFixedHeight(34)
        export_pdf_btn.clicked.connect(self._export_daily_report_pdf)
        row.addWidget(export_pdf_btn)

        export_csv_btn = QPushButton("  Export CSV")
        export_csv_btn.setObjectName("secondaryButton")
        export_csv_btn.setFixedHeight(34)
        export_csv_btn.clicked.connect(self._export_daily_report_csv)
        row.addWidget(export_csv_btn)

        lay.addLayout(row)
        return card

    def _gather_daily_report_entries(self):
        start = self._report_from.date().toString("yyyy-MM-dd")
        end = self._report_to.date().toString("yyyy-MM-dd")
        entries = repo.get_audit_log(start_date=start, end_date=end)
        if self._report_from.date() == self._report_to.date():
            period_label = self._report_from.date().toString("MMMM d, yyyy")
        else:
            period_label = f"{self._report_from.date().toString('MMM d, yyyy')} — {self._report_to.date().toString('MMM d, yyyy')}"
        return entries, period_label

    def _export_daily_report_pdf(self):
        entries, period_label = self._gather_daily_report_entries()
        default_name = f"daily_activity_report_{self._report_from.date().toString('yyyyMMdd')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save Daily Activity Report", default_name, "PDF Files (*.pdf)")
        if not path:
            return
        import utils.exporter as exporter
        business = repo.get_business_info()
        ok = exporter.export_daily_activity_report_pdf(path, entries, business, period_label)
        if ok:
            prompt_file_saved(self, path, title="Report Exported", message="Daily Activity Report exported successfully.")
        else:
            QMessageBox.warning(self, "Export Failed", "Could not generate PDF. Make sure reportlab is installed.")

    def _export_daily_report_csv(self):
        entries, _ = self._gather_daily_report_entries()
        default_name = f"daily_activity_report_{self._report_from.date().toString('yyyyMMdd')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Save Daily Activity Report", default_name, "CSV Files (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Time", "User", "Action", "Details"])
            for e in entries:
                writer.writerow([e.get("date", ""), e.get("time", ""), e.get("actor", ""), e.get("action", ""), e.get("description", "")])
        prompt_file_saved(self, path, title="Report Exported", message="Daily Activity Report exported successfully.")

    def _save_business(self):
        _BUSINESS_INFO["name"]    = self._name_f.text().strip()
        _BUSINESS_INFO["contact"] = self._contact_f.text().strip()
        _BUSINESS_INFO["email"]   = self._email_f.text().strip()
        _BUSINESS_INFO["address"] = self._address_f.text().strip()
        repo.save_business_info(_BUSINESS_INFO)
        self._save_notice.setText("Changes saved successfully.")
        self._save_notice.show()
        success(self, message="Business information saved successfully.")

    def _save_policy(self):
        try:
            repo.save_booking_policy(self._min_dp_spin.value(), self._allow_zero_cb.isChecked())
            repo.save_capacity_policy(self._max_pax_spin.value())
            success(self, message="Policy saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _test_smtp(self):
        host = self._smtp_host_f.text().strip()
        port = self._smtp_port_f.value()
        user = self._smtp_user_f.text().strip()
        pwd  = self._smtp_pass_f.text()

        if not host or not user or not pwd:
            QMessageBox.warning(self, "Incomplete Configuration", "Please enter SMTP Host, Username/Email, and Password before testing.")
            return

        import smtplib
        import ssl
        try:
            context = ssl.create_default_context()
            if port == 465:
                with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                    server.login(user, pwd)
            else:
                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(user, pwd)
            success(self, message=f"SMTP Connection Successful!\nConnected and authenticated with {host}:{port} as {user}.")
        except Exception as exc:
            err_msg = str(exc)
            if "Application-specific password required" in err_msg or "BadCredentials" in err_msg or "Username and Password not accepted" in err_msg:
                err_msg += "\n\nTip for Gmail: Google requires a 16-character 'App Password'.\nGo to Google Account -> Security -> 2-Step Verification -> App Passwords."
            QMessageBox.critical(self, "SMTP Connection Failed", f"Could not connect to SMTP server:\n\n{err_msg}")

    def _save_smtp(self):
        try:
            repo.save_smtp_config(
                self._smtp_host_f.text().strip(),
                self._smtp_port_f.value(),
                self._smtp_user_f.text().strip(),
                self._smtp_pass_f.text(),
            )
            success(self, message="SMTP configuration saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _toggle_theme(self):
        new_theme = self._theme.toggle()
        self._theme_lbl.setText("Dark Mode" if new_theme == "dark" else "Light Mode")

    def _build_diagnostics_card(self):
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        sec_title = QLabel("System Diagnostics & Error Logs")
        sec_title.setObjectName("h3")
        lay.addWidget(sec_title)

        desc = QLabel(
            "If you experience any issues, click 'Export Diagnostic Report' to automatically "
            "generate a troubleshooting text file on your Desktop to send to support."
        )
        desc.setObjectName("subtitle")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        import utils.db as db
        from utils.logger import get_log_file_path
        engine = db.get_engine_type().upper()

        info_box = QFrame()
        info_box.setStyleSheet("background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px;")
        info_lay = QVBoxLayout(info_box)
        info_lay.setSpacing(6)

        lbl_engine = QLabel(f"<b>Database Engine:</b> {engine} (High Performance Embedded)")
        lbl_log = QLabel(f"<b>Active Log File:</b> {get_log_file_path()}")
        lbl_log.setWordWrap(True)
        info_lay.addWidget(lbl_engine)
        info_lay.addWidget(lbl_log)
        lay.addWidget(info_box)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        export_btn = QPushButton("  Export Diagnostic Report")
        export_btn.setObjectName("primaryButton")
        export_btn.setIcon(btn_icon_primary("download"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.setFixedHeight(36)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_diagnostics)

        open_log_btn = QPushButton("  Open Log Folder")
        open_log_btn.setObjectName("secondaryButton")
        open_log_btn.setIcon(btn_icon_secondary("search"))
        open_log_btn.setIconSize(QSize(15, 15))
        open_log_btn.setFixedHeight(36)
        open_log_btn.setCursor(Qt.PointingHandCursor)
        open_log_btn.clicked.connect(self._open_log_folder)

        btn_row.addWidget(export_btn)
        btn_row.addWidget(open_log_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        return card

    def _export_diagnostics(self):
        try:
            from utils.logger import export_diagnostic_report
            report_path = export_diagnostic_report()
            success(self, message=f"Diagnostic report exported to Desktop:\n\n{report_path.name}\n\nYou can send this file to support.")
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", f"Could not generate report: {exc}")

    def _open_log_folder(self):
        import os
        from utils.logger import get_log_dir
        log_dir = get_log_dir()
        try:
            if os.name == "nt":
                os.startfile(str(log_dir))
            else:
                subprocess.Popen(["xdg-open", str(log_dir)])
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not open folder: {exc}")

    def _backup_db(self):
        import utils.db as db
        import shutil
        engine = db.get_engine_type()
        if engine == "sqlite":
            src = db.get_sqlite_db_path()
            if not src.exists():
                QMessageBox.warning(self, "Error", "Database file does not exist yet.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self, "Backup Database", "jayraldines_backup.db", "SQLite Database (*.db *.bak)"
            )
            if not path:
                return
            try:
                shutil.copy2(src, path)
                prompt_file_saved(self, path, title="Database Backup Created", message="SQLite database backup created successfully.")
            except Exception as exc:
                QMessageBox.warning(self, "Backup Error", str(exc))
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Backup Database", "jayraldines_backup.sql", "SQL Files (*.sql)"
            )
            if not path:
                return
            try:
                result = subprocess.run(
                    ["pg_dump", "-U", "postgres", "-d", "jayraldines_catering", "-f", path],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    prompt_file_saved(self, path, title="Database Backup Created", message="PostgreSQL database backup created successfully.")
                else:
                    QMessageBox.warning(self, "Backup Failed", result.stderr or "pg_dump returned an error.")
            except FileNotFoundError:
                QMessageBox.warning(self, "Not Found",
                    "pg_dump not found. Make sure PostgreSQL is installed and in your PATH.")
            except Exception as exc:
                QMessageBox.warning(self, "Backup Error", str(exc))

    def _restore_db(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "edit"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot restore database backups.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Restore Database Backup", "",
            "All Supported Backups (*.db *.bak *.sql);;SQLite Database (*.db *.bak);;SQL Dump (*.sql);;All Files (*.*)"
        )
        if not path:
            return

        confirm = QMessageBox.warning(
            self, "Confirm Restore",
            "This will OVERWRITE or MERGE data from the selected backup.\n\nAre you sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if confirm != QMessageBox.Yes:
            return

        worker = DatabaseRestoreWorker(path, self)
        dlg = DatabaseRestoreProgressDialog(self)

        def _on_finished(ok, msg):
            dlg.accept()
            if ok:
                success(self, message=msg)
                try:
                    from utils.signals import app_events
                    app_events().data_changed.emit()
                    app_events().booking_saved.emit()
                except Exception:
                    pass
            else:
                QMessageBox.warning(self, "Restore Error", msg)

        worker.progress_update.connect(dlg.set_status)
        worker.restore_finished.connect(_on_finished)
        worker.start()
        dlg.exec()

    def _build_purge_data_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("QFrame#card { border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 12px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Title Row
        head_lay = QHBoxLayout()
        sec_title = QLabel("Data Reset & Purge Management")
        sec_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #EF4444;")
        head_lay.addWidget(sec_title)
        head_lay.addStretch()

        badge = QLabel("Danger Zone")
        badge.setStyleSheet(
            "background: rgba(239, 68, 68, 0.15); color: #EF4444; font-weight: 700; "
            "font-size: 11px; padding: 3px 10px; border-radius: 6px; border: 1px solid rgba(239, 68, 68, 0.3);"
        )
        head_lay.addWidget(badge)
        lay.addLayout(head_lay)

        desc = QLabel(
            "Select specific operational data categories to delete, or perform a complete factory wipe. "
            "Deleted data cannot be recovered. Please create a database backup before proceeding."
        )
        desc.setObjectName("subtitle")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # Checkbox selection box
        chk_box = QFrame()
        chk_box.setStyleSheet(
            "background: rgba(0,0,0,0.12); border: 1px solid rgba(255,255,255,0.06); "
            "border-radius: 8px; padding: 14px;"
        )
        chk_lay = QVBoxLayout(chk_box)
        chk_lay.setSpacing(10)

        self._purge_cbs = {}
        items = [
            ("bookings",        "Bookings & Invoices",           "Deletes bookings, invoices, payments, and kitchen orders"),
            ("customers",       "Customers & Contacts",          "Deletes customer profiles, addresses, and follow-ups"),
            ("expenses",        "Expenses & Costs",              "Deletes all operational expense entries"),
            ("menu_items",      "Menu Items & Catalog",          "Deletes all menu catalog items and dishes"),
            ("packages",        "Catering Packages",             "Deletes all catering packages and set menus"),
            ("calendar_events", "Manual Calendar Events",        "Deletes custom calendar reminders and events"),
            ("logs",            "Notifications & Audit Logs",    "Deletes notifications and system audit logs"),
        ]

        for key, title, sub in items:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(10)

            cb = QCheckBox(title)
            cb.setStyleSheet("font-weight: 600; font-size: 13px;")
            cnt_lbl = QLabel("(0 records)")
            cnt_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
            sub_lbl = QLabel(f"— {sub}")
            sub_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")

            row_l.addWidget(cb)
            row_l.addWidget(cnt_lbl)
            row_l.addWidget(sub_lbl)
            row_l.addStretch()

            self._purge_cbs[key] = (cb, cnt_lbl)
            chk_lay.addWidget(row_w)

        lay.addWidget(chk_box)

        # Quick Actions Row
        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        btn_select_all = QPushButton("Select All")
        btn_select_all.setObjectName("secondaryButton")
        btn_select_all.setFixedHeight(28)
        btn_select_all.setCursor(Qt.PointingHandCursor)
        btn_select_all.clicked.connect(self._select_all_purge)
        quick_row.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.setObjectName("secondaryButton")
        btn_deselect_all.setFixedHeight(28)
        btn_deselect_all.setCursor(Qt.PointingHandCursor)
        btn_deselect_all.clicked.connect(self._deselect_all_purge)
        quick_row.addWidget(btn_deselect_all)

        btn_refresh_counts = QPushButton("Refresh Counts")
        btn_refresh_counts.setObjectName("secondaryButton")
        btn_refresh_counts.setFixedHeight(28)
        btn_refresh_counts.setCursor(Qt.PointingHandCursor)
        btn_refresh_counts.clicked.connect(self._refresh_purge_counts)
        quick_row.addWidget(btn_refresh_counts)

        quick_row.addStretch()
        lay.addLayout(quick_row)

        # Execution Buttons Row
        exec_row = QHBoxLayout()
        exec_row.setSpacing(14)

        btn_delete_selected = QPushButton("  Delete Selected Data")
        btn_delete_selected.setFixedHeight(36)
        btn_delete_selected.setCursor(Qt.PointingHandCursor)
        btn_delete_selected.setStyleSheet(
            "QPushButton { background: transparent; color: #EF4444; border: 1.5px solid #EF4444; "
            "font-weight: 700; border-radius: 8px; padding: 6px 18px; } "
            "QPushButton:hover { background: rgba(239, 68, 68, 0.12); }"
        )
        btn_delete_selected.clicked.connect(self._on_purge_selected)
        exec_row.addWidget(btn_delete_selected)

        btn_delete_all = QPushButton("  Delete All Data (Complete Reset)")
        btn_delete_all.setFixedHeight(36)
        btn_delete_all.setCursor(Qt.PointingHandCursor)
        btn_delete_all.setStyleSheet(
            "QPushButton { background: #DC2626; color: #FFFFFF; border: none; "
            "font-weight: 700; border-radius: 8px; padding: 6px 20px; } "
            "QPushButton:hover { background: #B91C1C; }"
        )
        btn_delete_all.clicked.connect(self._on_purge_all)
        exec_row.addWidget(btn_delete_all)

        exec_row.addStretch()
        lay.addLayout(exec_row)

        self._refresh_purge_counts()
        return card

    def _select_all_purge(self):
        for cb, _ in self._purge_cbs.values():
            cb.setChecked(True)

    def _deselect_all_purge(self):
        for cb, _ in self._purge_cbs.values():
            cb.setChecked(False)

    def _refresh_purge_counts(self):
        counts = repo.get_data_counts()
        label_map = {
            "bookings": f"({counts.get('bookings', 0)} bookings, {counts.get('invoices', 0)} invoices)",
            "customers": f"({counts.get('customers', 0)} records)",
            "expenses": f"({counts.get('expenses', 0)} records)",
            "menu_items": f"({counts.get('menu_items', 0)} items)",
            "packages": f"({counts.get('packages', 0)} packages)",
            "calendar_events": f"({counts.get('calendar_events', 0)} events)",
            "logs": f"({counts.get('notifications', 0)} notifs, {counts.get('audit_logs', 0)} logs)",
        }
        for key, (_, lbl) in self._purge_cbs.items():
            if key in label_map:
                lbl.setText(label_map[key])

    def _on_purge_selected(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "delete"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot purge data.")
            return
        selected = [k for k, (cb, _) in self._purge_cbs.items() if cb.isChecked()]
        if not selected:
            QMessageBox.information(self, "No Selection", "Please check at least one category to delete.")
            return

        names = [cb.text() for k, (cb, _) in self._purge_cbs.items() if cb.isChecked()]
        list_str = "\n".join(f"  • {n}" for n in names)

        confirm = QMessageBox.warning(
            self,
            "Confirm Data Deletion",
            f"Are you sure you want to PERMANENTLY delete the following categories?\n\n"
            f"{list_str}\n\n"
            f"This action CANNOT be undone.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            repo.purge_selected_data(selected)
            self._deselect_all_purge()
            self._refresh_purge_counts()
            success(self, message="Selected data has been deleted successfully.\nAll views have been refreshed.")
        except Exception as exc:
            QMessageBox.critical(self, "Deletion Error", f"An error occurred during deletion:\n{exc}")

    def _on_purge_all(self):
        if not SessionManager.is_admin() and not SessionManager.has_permission("settings", "delete"):
            QMessageBox.warning(self, "Access Denied", "View-only permission: You cannot purge data.")
            return
        confirm = QMessageBox.critical(
            self,
            "FACTORY RESET CONFIRMATION",
            "WARNING: You are about to DELETE ALL DATA in the system:\n\n"
            "  • All Bookings, Invoices & Payments\n"
            "  • All Customers & Addresses\n"
            "  • All Expenses\n"
            "  • All Menu Items & Packages\n"
            "  • All Calendar Events & Logs\n\n"
            "The system will be completely wiped clean.\n\n"
            "Are you absolutely certain?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            repo.purge_all_data()
            self._deselect_all_purge()
            self._refresh_purge_counts()
            success(self, message="All data has been permanently deleted.\nSystem has been reset to clean state.")
        except Exception as exc:
            QMessageBox.critical(self, "Reset Error", f"An error occurred during reset:\n{exc}")

