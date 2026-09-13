"""
Modal Dialog for Configuring and Updating Database Connection Settings
(PostgreSQL / SQLite) for Jayraldine's Catering.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QComboBox, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from utils.db_config import (
    get_db_config, save_db_config, test_postgres_connection, test_sqlite_sync_connection, get_local_lan_ip
)
import re
import utils.db as db
from utils.animations import animate_dialog_open, create_soft_shadow


class EditDbConnectionDialog(QDialog):
    """Allows administrators to update PostgreSQL host, port, dbname, user, and password."""

    def __init__(self, parent=None, on_saved=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(520)
        self.setModal(True)
        self._on_saved = on_saved
        self._cfg = get_db_config()
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=220)

    @staticmethod
    def _clean_host(raw: str) -> str:
        """Strip http://, https://, trailing slashes and port suffixes from a host string."""
        raw = str(raw).strip()
        # Remove scheme
        raw = re.sub(r'^https?://', '', raw)
        # Remove trailing port (e.g. :8000 or :5432)
        raw = re.sub(r':\d+$', '', raw)
        # Remove trailing slashes
        raw = raw.rstrip('/')
        return raw.strip()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("modalCard")
        card.setStyleSheet("""
            QFrame#modalCard {
                background-color: #0F172A;
                border: 1.5px solid #334155;
                border-radius: 14px;
            }
            QLabel {
                color: #F8FAFC;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #F8FAFC;
                padding: 7px 12px;
                font-size: 13px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #38BDF8;
            }
        """)
        create_soft_shadow(card, radius=24, y_offset=6, opacity=60)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Database Connection Settings")
        title.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")
        sub = QLabel("Configure PostgreSQL centralized server connection parameters.")
        sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                border-radius: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: #FFFFFF;
                border-color: #EF4444;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        # Engine Selection
        lay.addWidget(QLabel("Database Engine:"))
        self._engine_combo = QComboBox()
        self._engine_combo.addItems(["SQLite (Embedded Local / LAN Sync)", "PostgreSQL"])
        cur_engine = self._cfg.get("engine", "sqlite").lower()
        self._engine_combo.setCurrentIndex(0 if cur_engine == "sqlite" else 1)
        self._engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        lay.addWidget(self._engine_combo)

        # Station Role (for SQLite)
        self._station_mode_container = QWidget()
        sm_lay = QVBoxLayout(self._station_mode_container)
        sm_lay.setContentsMargins(0, 0, 0, 0)
        sm_lay.setSpacing(4)
        sm_lay.addWidget(QLabel("Station Role:"))
        self._station_mode_combo = QComboBox()
        self._station_mode_combo.addItems([
            "🖥️ Central Database Server Host (Primary PC with catering.db)",
            "💻 Client Workstation (Connects to Server PC e.g. 192.168.1.32)"
        ])
        is_client_mode = (self._cfg.get("sync_role") == "client") or (str(self._cfg.get("host", "")).strip() in ("192.168.1.32", "192.168.1.10"))
        self._station_mode_combo.setCurrentIndex(1 if is_client_mode else 0)
        self._station_mode_combo.currentIndexChanged.connect(self._on_station_mode_changed)
        sm_lay.addWidget(self._station_mode_combo)
        lay.addWidget(self._station_mode_container)

        # Host + Helper buttons
        self._pg_fields_container = QWidget()
        pg_lay = QVBoxLayout(self._pg_fields_container)
        pg_lay.setContentsMargins(0, 0, 0, 0)
        pg_lay.setSpacing(10)

        host_hdr = QHBoxLayout()
        self._host_lbl = QLabel("Server Host / IP:")
        host_hdr.addWidget(self._host_lbl)
        host_hdr.addStretch()

        lan_ip = get_local_lan_ip()
        btn_32 = QPushButton("192.168.1.32 (PC Server)")
        btn_32.setCursor(Qt.PointingHandCursor)
        btn_32.setStyleSheet("background: #1E293B; color: #38BDF8; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid #0284C7; font-weight: bold;")
        btn_32.clicked.connect(lambda: self._host_f.setText("192.168.1.32"))
        host_hdr.addWidget(btn_32)

        btn_local = QPushButton("localhost")
        btn_local.setCursor(Qt.PointingHandCursor)
        btn_local.setStyleSheet("background: #1E293B; color: #94A3B8; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid #334155;")
        btn_local.clicked.connect(lambda: self._host_f.setText("localhost"))
        host_hdr.addWidget(btn_local)

        if lan_ip and lan_ip != "127.0.0.1":
            btn_lan = QPushButton(f"LAN ({lan_ip})")
            btn_lan.setCursor(Qt.PointingHandCursor)
            btn_lan.setStyleSheet("background: #1E293B; color: #10B981; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid #059669;")
            btn_lan.clicked.connect(lambda: self._host_f.setText(lan_ip))
            host_hdr.addWidget(btn_lan)

        pg_lay.addLayout(host_hdr)

        initial_host = self._clean_host(str(self._cfg.get("host", "192.168.1.32" if is_client_mode else "localhost")))
        self._host_f = QLineEdit(initial_host)
        self._host_f.setPlaceholderText("e.g. 192.168.1.32 or localhost")
        pg_lay.addWidget(self._host_f)

        # Port & DB Name
        row2 = QHBoxLayout()
        port_box = QVBoxLayout()
        port_box.setSpacing(4)
        port_box.addWidget(QLabel("Port (8000 for Sync / 5432 for PG):"))
        self._port_f = QSpinBox()
        self._port_f.setRange(1, 65535)
        self._port_f.setValue(int(self._cfg.get("port", 8000 if cur_engine == "sqlite" else 5432)))
        port_box.addWidget(self._port_f)
        row2.addLayout(port_box, 1)

        self._db_name_box = QWidget()
        db_lay = QVBoxLayout(self._db_name_box)
        db_lay.setContentsMargins(0, 0, 0, 0)
        db_lay.setSpacing(4)
        db_lay.addWidget(QLabel("Database Name:"))
        self._dbname_f = QLineEdit(str(self._cfg.get("dbname", "catering.db" if cur_engine == "sqlite" else "jayraldines_catering")))
        db_lay.addWidget(self._dbname_f)
        row2.addWidget(self._db_name_box, 2)
        pg_lay.addLayout(row2)

        # Username & Password container (for PG only)
        self._creds_container = QWidget()
        creds_lay = QVBoxLayout(self._creds_container)
        creds_lay.setContentsMargins(0, 0, 0, 0)
        creds_lay.setSpacing(10)

        row3 = QHBoxLayout()
        user_box = QVBoxLayout()
        user_box.setSpacing(4)
        user_box.addWidget(QLabel("Username:"))
        self._user_f = QLineEdit(str(self._cfg.get("user", "jayraldines_app")))
        user_box.addWidget(self._user_f)
        row3.addLayout(user_box, 1)

        pass_box = QVBoxLayout()
        pass_box.setSpacing(4)
        pass_box.addWidget(QLabel("Password:"))
        pass_row = QHBoxLayout()
        self._pass_f = QLineEdit(str(self._cfg.get("password", "12345678")))
        self._pass_f.setEchoMode(QLineEdit.Password)
        pass_row.addWidget(self._pass_f, 1)

        self._show_pass_btn = QPushButton("👁")
        self._show_pass_btn.setFixedSize(34, 34)
        self._show_pass_btn.setCursor(Qt.PointingHandCursor)
        self._show_pass_btn.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 6px; color: #94A3B8;")
        self._show_pass_btn.clicked.connect(self._toggle_password_vis)
        pass_row.addWidget(self._show_pass_btn)
        pass_box.addLayout(pass_row)
        row3.addLayout(pass_box, 1)
        creds_lay.addLayout(row3)
        pg_lay.addWidget(self._creds_container)

        # Server Info Box (for SQLite Central Server)
        self._server_info_box = QFrame()
        self._server_info_box.setStyleSheet("background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px;")
        s_inf_lay = QVBoxLayout(self._server_info_box)
        s_inf_lay.setSpacing(4)
        s_title = QLabel("🖥️ Central Server Mode (Primary Host)")
        s_title.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
        s_inf_lay.addWidget(s_title)
        s_desc = QLabel("This computer hosts the master <b>catering.db</b> database and automatically runs the LAN Sync Server on port <b>8000</b>. Tablets and Client Workstations connect to this computer's IP address.")
        s_desc.setWordWrap(True)
        s_desc.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        s_inf_lay.addWidget(s_desc)
        lay.addWidget(self._server_info_box)

        lay.addWidget(self._pg_fields_container)

        # Status result label
        self._status_lbl = QLabel("")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet("font-size: 12px; font-weight: 600; padding: 4px;")
        self._status_lbl.setVisible(False)
        lay.addWidget(self._status_lbl)

        # Action Buttons
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(10)

        test_btn = QPushButton("⚡ Test Connection")
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: 700;
                padding: 9px 16px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        test_btn.clicked.connect(self._test_connection)
        btn_lay.addWidget(test_btn)

        btn_lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #CBD5E1;
                font-weight: 600;
                padding: 9px 16px;
                border-radius: 8px;
                border: 1px solid #334155;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save & Apply")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 700;
                padding: 9px 18px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        save_btn.clicked.connect(self._save_and_apply)
        btn_lay.addWidget(save_btn)

        lay.addLayout(btn_lay)
        root.addWidget(card)

        self._on_engine_changed(self._engine_combo.currentIndex())

    def _toggle_password_vis(self):
        if self._pass_f.echoMode() == QLineEdit.Password:
            self._pass_f.setEchoMode(QLineEdit.Normal)
            self._show_pass_btn.setStyleSheet("background: #0284C7; border: 1px solid #38BDF8; border-radius: 6px; color: #FFFFFF;")
        else:
            self._pass_f.setEchoMode(QLineEdit.Password)
            self._show_pass_btn.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 6px; color: #94A3B8;")

    def _on_engine_changed(self, idx: int):
        is_sqlite = (idx == 0)
        self._station_mode_container.setVisible(is_sqlite)
        if is_sqlite:
            self._on_station_mode_changed(self._station_mode_combo.currentIndex())
        else:
            self._station_mode_container.setVisible(False)
            self._server_info_box.setVisible(False)
            self._pg_fields_container.setVisible(True)
            self._creds_container.setVisible(True)
            self._db_name_box.setVisible(True)
            self._host_lbl.setText("PostgreSQL Server Host / IP:")
            self._port_f.setValue(5432)

    def _on_station_mode_changed(self, idx: int):
        is_client = (idx == 1)
        if is_client:
            self._server_info_box.setVisible(False)
            self._pg_fields_container.setVisible(True)
            self._creds_container.setVisible(False)
            self._db_name_box.setVisible(False)
            self._host_lbl.setText("Central Server PC LAN IP:")
            if not self._host_f.text().strip() or self._host_f.text().strip() == "localhost":
                self._host_f.setText("192.168.1.32")
            self._port_f.setValue(8000)
        else:
            self._server_info_box.setVisible(True)
            self._pg_fields_container.setVisible(False)

    def _test_connection(self):
        engine = "sqlite" if self._engine_combo.currentIndex() == 0 else "postgres"
        if engine == "sqlite":
            is_client = (self._station_mode_combo.currentIndex() == 1)
            if not is_client:
                # Central server local probe
                try:
                    db.connect_sqlite()
                    row = db.fetchone("SELECT 1 as alive")
                    if row and row.get("alive") == 1:
                        self._status_lbl.setText("✅ Central SQLite database is online, active, and accessible.")
                        self._status_lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
                    else:
                        self._status_lbl.setText("⚠️ Local SQLite opened, but query returned no result.")
                        self._status_lbl.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 600;")
                except Exception as e:
                    self._status_lbl.setText(f"❌ Local SQLite error: {e}")
                    self._status_lbl.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
                self._status_lbl.setVisible(True)
                return

            # Client Workstation HTTP Sync Hub test
            host = self._clean_host(self._host_f.text().strip() or "192.168.1.32")
            port = self._port_f.value()
            self._status_lbl.setText(f"⏳ Testing LAN Sync link to http://{host}:{port}...")
            self._status_lbl.setStyleSheet("color: #38BDF8; font-size: 12px;")
            self._status_lbl.setVisible(True)
            self.repaint()

            ok, msg = test_sqlite_sync_connection(host=host, port=port, timeout=4)
            if ok:
                self._status_lbl.setText(f"✅ Connection successful! Reached Central Server Hub at http://{host}:{port}")
                self._status_lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
            else:
                self._status_lbl.setText(f"❌ Cannot connect to Central Server at http://{host}:{port}:\n{msg}\n(Ensure Central Server is running on the other PC)")
                self._status_lbl.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
            return

        # PostgreSQL test
        host = self._host_f.text().strip() or "localhost"
        port = self._port_f.value()
        dbname = self._dbname_f.text().strip() or "jayraldines_catering"
        user = self._user_f.text().strip() or "jayraldines_app"
        pwd = self._pass_f.text()

        self._status_lbl.setText("⏳ Testing connection to PostgreSQL...")
        self._status_lbl.setStyleSheet("color: #38BDF8; font-size: 12px;")
        self._status_lbl.setVisible(True)
        self.repaint()

        ok, msg = test_postgres_connection(host, port, dbname, user, pwd, timeout=4)
        if ok:
            self._status_lbl.setText(f"✅ Connection successful to {dbname}@{host}:{port}!")
            self._status_lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
        else:
            self._status_lbl.setText(f"❌ Connection failed:\n{msg}")
            self._status_lbl.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")

    def _save_and_apply(self):
        engine = "sqlite" if self._engine_combo.currentIndex() == 0 else "postgres"
        if engine == "sqlite":
            is_client = (self._station_mode_combo.currentIndex() == 1)
            host = self._clean_host(self._host_f.text().strip()) if is_client else "localhost"
            port = self._port_f.value() if is_client else 8000
            sync_role = "client" if is_client else "host"

            save_db_config(
                engine="sqlite",
                host=host,
                port=port,
                dbname="catering.db",
                user="client" if is_client else "admin",
                password="",
                sync_role=sync_role,
                sync_server_url=f"http://{host}:{port}"
            )
            try:
                db.connect_sqlite()
            except Exception:
                pass

            if self._on_saved:
                try:
                    self._on_saved()
                except Exception:
                    pass

            role_title = f"Client Workstation (Connected to {host}:{port})" if is_client else "Central Server Host (Local DB)"
            QMessageBox.information(
                self, "Configuration Saved",
                f"Database connection settings have been updated!\n\n"
                f"Engine: SQLITE\n"
                f"Station Role: {role_title}\n"
                f"Host: {host}:{port}"
            )
            self.accept()
            return

        # PostgreSQL save
        host = self._host_f.text().strip() or "localhost"
        port = self._port_f.value()
        dbname = self._dbname_f.text().strip() or "jayraldines_catering"
        user = self._user_f.text().strip() or "jayraldines_app"
        pwd = self._pass_f.text()

        is_local = host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "", "::1") or host == get_local_lan_ip()
        sync_role = "host" if is_local else "client"

        save_db_config(
            engine="postgres",
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=pwd,
            sync_role=sync_role
        )
        try:
            db.connect_postgres(force=True)
        except Exception:
            pass

        if self._on_saved:
            try:
                self._on_saved()
            except Exception:
                pass

        QMessageBox.information(
            self, "Configuration Saved",
            f"Database connection settings have been updated and applied!\n\n"
            f"Engine: POSTGRESQL\nHost: {host}:{port}\nDatabase: {dbname}\nUser: {user}"
        )
        self.accept()
