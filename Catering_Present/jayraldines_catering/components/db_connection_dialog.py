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
    get_db_config, save_db_config, test_postgres_connection, get_local_lan_ip
)
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
        self._engine_combo.addItems(["PostgreSQL", "SQLite (Embedded Local)"])
        cur_engine = self._cfg.get("engine", "postgres").lower()
        self._engine_combo.setCurrentIndex(0 if cur_engine == "postgres" else 1)
        self._engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        lay.addWidget(self._engine_combo)

        # Host + Helper buttons
        self._pg_fields_container = QWidget()
        pg_lay = QVBoxLayout(self._pg_fields_container)
        pg_lay.setContentsMargins(0, 0, 0, 0)
        pg_lay.setSpacing(10)

        host_hdr = QHBoxLayout()
        host_hdr.addWidget(QLabel("Server Host / IP:"))
        host_hdr.addStretch()

        lan_ip = get_local_lan_ip()
        btn_local = QPushButton("localhost")
        btn_local.setCursor(Qt.PointingHandCursor)
        btn_local.setStyleSheet("background: #1E293B; color: #38BDF8; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid #0284C7;")
        btn_local.clicked.connect(lambda: self._host_f.setText("localhost"))
        host_hdr.addWidget(btn_local)

        if lan_ip and lan_ip != "127.0.0.1":
            btn_lan = QPushButton(f"LAN ({lan_ip})")
            btn_lan.setCursor(Qt.PointingHandCursor)
            btn_lan.setStyleSheet("background: #1E293B; color: #10B981; font-size: 11px; padding: 2px 8px; border-radius: 4px; border: 1px solid #059669;")
            btn_lan.clicked.connect(lambda: self._host_f.setText(lan_ip))
            host_hdr.addWidget(btn_lan)

        pg_lay.addLayout(host_hdr)

        self._host_f = QLineEdit(str(self._cfg.get("host", "localhost")))
        self._host_f.setPlaceholderText("e.g. localhost, 192.168.1.10, or server domain")
        pg_lay.addWidget(self._host_f)

        # Port & DB Name
        row2 = QHBoxLayout()
        port_box = QVBoxLayout()
        port_box.setSpacing(4)
        port_box.addWidget(QLabel("Port:"))
        self._port_f = QSpinBox()
        self._port_f.setRange(1, 65535)
        self._port_f.setValue(int(self._cfg.get("port", 5432)))
        port_box.addWidget(self._port_f)
        row2.addLayout(port_box, 1)

        db_box = QVBoxLayout()
        db_box.setSpacing(4)
        db_box.addWidget(QLabel("Database Name:"))
        self._dbname_f = QLineEdit(str(self._cfg.get("dbname", "jayraldines_catering")))
        db_box.addWidget(self._dbname_f)
        row2.addLayout(db_box, 2)
        pg_lay.addLayout(row2)

        # Username & Password
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
        pg_lay.addLayout(row3)

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
        is_pg = (idx == 0)
        self._pg_fields_container.setVisible(is_pg)

    def _test_connection(self):
        engine = "postgres" if self._engine_combo.currentIndex() == 0 else "sqlite"
        if engine == "sqlite":
            self._status_lbl.setText("✅ SQLite is embedded and ready.")
            self._status_lbl.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
            self._status_lbl.setVisible(True)
            return

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
        engine = "postgres" if self._engine_combo.currentIndex() == 0 else "sqlite"
        host = self._host_f.text().strip() or "localhost"
        port = self._port_f.value()
        dbname = self._dbname_f.text().strip() or "jayraldines_catering"
        user = self._user_f.text().strip() or "jayraldines_app"
        pwd = self._pass_f.text()

        # Save to db_config.json & update process environment
        save_db_config(
            engine=engine,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=pwd,
        )

        # Reconnect live active connection
        try:
            if engine == "postgres":
                db.connect_postgres(force=True)
            else:
                db.connect_sqlite()
        except Exception as exc:
            pass

        if self._on_saved:
            try:
                self._on_saved()
            except Exception:
                pass

        QMessageBox.information(
            self, "Configuration Saved",
            f"Database connection settings have been updated and applied!\n\n"
            f"Engine: {engine.upper()}\nHost: {host}:{port}\nDatabase: {dbname}\nUser: {user}"
        )
        self.accept()
