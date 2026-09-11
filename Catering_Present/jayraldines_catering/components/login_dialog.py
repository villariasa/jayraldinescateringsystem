"""
Jayraldine's Catering - Modern Frameless Glassmorphic Login Dialog.
Handles user authentication, server status indication, and credential validation.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QFrame,
    QGraphicsDropShadowEffect, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QIcon

import utils.db as db
from utils.auth import authenticate, SessionManager
from utils.db_config import get_db_config, save_db_config, test_postgres_connection
from utils.paths import resource_path


class ServerConfigDialog(QDialog):
    """Small dialog allowing staff to update Server IP without reinstalling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 320)

        cfg = get_db_config()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)

        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        frame.setGraphicsEffect(shadow)

        f_lay = QVBoxLayout(frame)
        f_lay.setContentsMargins(18, 16, 18, 16)
        f_lay.setSpacing(10)

        t_row = QHBoxLayout()
        title = QLabel("⚙️ Server Connection Settings")
        title.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 700;")
        t_row.addWidget(title)
        t_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("color: #94A3B8; background: transparent; border: none; font-weight: bold;")
        close_btn.clicked.connect(self.reject)
        t_row.addWidget(close_btn)
        f_lay.addLayout(t_row)

        input_style = """
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                padding: 6px 10px;
                font-size: 12px;
                border-radius: 6px;
            }
        """

        f_lay.addWidget(QLabel("Server Host / IP:"))
        self.host_edit = QLineEdit(str(cfg.get("host", "localhost")))
        self.host_edit.setStyleSheet(input_style)
        f_lay.addWidget(self.host_edit)

        f_lay.addWidget(QLabel("Port:"))
        self.port_edit = QLineEdit(str(cfg.get("port", 5432)))
        self.port_edit.setStyleSheet(input_style)
        f_lay.addWidget(self.port_edit)

        f_lay.addWidget(QLabel("Database Password:"))
        self.pwd_edit = QLineEdit(str(cfg.get("password", "")))
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setStyleSheet(input_style)
        f_lay.addWidget(self.pwd_edit)

        f_lay.addStretch()

        btn_row = QHBoxLayout()
        test_btn = QPushButton("Test & Save")
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #E11D48;
                color: #FFFFFF;
                border: none;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 700;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #BE123C; }
        """)
        test_btn.clicked.connect(self._save_and_test)
        btn_row.addStretch()
        btn_row.addWidget(test_btn)
        f_lay.addLayout(btn_row)

        lay.addWidget(frame)

    def _save_and_test(self):
        host = self.host_edit.text().strip()
        port = int(self.port_edit.text().strip() or 5432)
        pwd = self.pwd_edit.text()

        ok, msg = test_postgres_connection(
            host=host, port=port, dbname="jayraldines_catering",
            user="jayraldines_app", password=pwd, timeout=4
        )
        if ok:
            save_db_config(
                engine="postgres", host=host, port=port,
                dbname="jayraldines_catering", user="jayraldines_app", password=pwd
            )
            QMessageBox.information(self, "Success", "Server connection settings updated successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Connection Failed", f"Could not connect to server:\n{msg}")


class LoginDialog(QDialog):
    """
    Sleek, dark-mode glassmorphic login dialog.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 480)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)

        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E1B4B, stop:0.35 #0F172A, stop:1 #020617);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setYOffset(12)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.frame.setGraphicsEffect(shadow)

        f_lay = QVBoxLayout(self.frame)
        f_lay.setContentsMargins(28, 22, 28, 24)
        f_lay.setSpacing(12)

        # Top Control Bar (Gear settings + Close)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        gear_btn = QPushButton("⚙️")
        gear_btn.setFixedSize(26, 26)
        gear_btn.setCursor(Qt.PointingHandCursor)
        gear_btn.setToolTip("Configure Database Server Connection")
        gear_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; font-size: 13px; }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)
        gear_btn.clicked.connect(self._open_server_settings)
        top_bar.addWidget(gear_btn)

        top_bar.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #94A3B8; font-size: 13px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background: rgba(239, 68, 68, 0.2); color: #EF4444; }
        """)
        close_btn.clicked.connect(self._on_close_clicked)
        top_bar.addWidget(close_btn)

        f_lay.addLayout(top_bar)

        # Brand Header
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        header_lay.setAlignment(Qt.AlignCenter)

        logo_lbl = QLabel()
        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            pm = QPixmap(logo_path).scaled(46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pm)
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        header_lay.addWidget(logo_lbl)

        title_lbl = QLabel("Jayraldine's Catering")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #F8FAFC; font-size: 19px; font-weight: 800; border: none; background: transparent;")
        header_lay.addWidget(title_lbl)

        sub_lbl = QLabel("Sign in to access catering management")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; border: none; background: transparent;")
        header_lay.addWidget(sub_lbl)

        f_lay.addLayout(header_lay)

        # Server Status Pill
        self.server_status_lbl = QLabel()
        self.server_status_lbl.setAlignment(Qt.AlignCenter)
        self.server_status_lbl.setFixedHeight(24)
        self._update_server_status_badge()
        f_lay.addWidget(self.server_status_lbl)

        # Form Inputs
        input_style = """
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: #F8FAFC;
                padding: 9px 12px;
                font-size: 13px;
                border-radius: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #E11D48;
                background-color: #0F172A;
            }
        """

        u_lay = QVBoxLayout()
        u_lay.setSpacing(3)
        u_lbl = QLabel("Username:")
        u_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setStyleSheet(input_style)
        u_lay.addWidget(u_lbl)
        u_lay.addWidget(self.username_edit)
        f_lay.addLayout(u_lay)

        p_lay = QVBoxLayout()
        p_lay.setSpacing(3)
        p_lbl = QLabel("Password:")
        p_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600; border: none; background: transparent;")

        p_input_row = QHBoxLayout()
        p_input_row.setSpacing(4)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setStyleSheet(input_style)
        self.password_edit.returnPressed.connect(self._do_login)

        eye_btn = QPushButton("👁")
        eye_btn.setFixedSize(36, 36)
        eye_btn.setCursor(Qt.PointingHandCursor)
        eye_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        eye_btn.clicked.connect(self._toggle_password_visibility)

        p_input_row.addWidget(self.password_edit, 1)
        p_input_row.addWidget(eye_btn)

        p_lay.addWidget(p_lbl)
        p_lay.addLayout(p_input_row)
        f_lay.addLayout(p_lay)

        # Remember Username checkbox
        self.cb_remember = QCheckBox("Remember username")
        self.cb_remember.setChecked(True)
        self.cb_remember.setStyleSheet("""
            QCheckBox { color: #94A3B8; font-size: 11px; font-weight: 600; spacing: 6px; border: none; background: transparent; }
            QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #475569; background-color: #1E293B; }
            QCheckBox::indicator:checked { background-color: #E11D48; border-color: #E11D48; }
        """)
        f_lay.addWidget(self.cb_remember)

        # Error Banner
        self.error_lbl = QLabel()
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        self.error_lbl.hide()
        f_lay.addWidget(self.error_lbl)

        # Sign In Button
        self.sign_in_btn = QPushButton("Sign In")
        self.sign_in_btn.setFixedHeight(40)
        self.sign_in_btn.setCursor(Qt.PointingHandCursor)
        self.sign_in_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                border: none;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                border-radius: 8px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BE123C, stop:1 #E11D48); }
        """)
        self.sign_in_btn.clicked.connect(self._do_login)
        f_lay.addWidget(self.sign_in_btn)

        lay.addWidget(self.frame)

        self._load_saved_username()

    def _update_server_status_badge(self):
        engine = db.get_engine_type()
        cfg = get_db_config()
        host = cfg.get("host", "localhost")
        port = cfg.get("port", 5432)

        if engine == "postgres" and db.is_available():
            self.server_status_lbl.setText(f"🟢 Connected to Central Server: {host}:{port}")
            self.server_status_lbl.setStyleSheet("""
                QLabel {
                    color: #10B981;
                    font-size: 10px;
                    font-weight: 700;
                    background-color: rgba(16, 185, 129, 0.12);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)
        elif engine == "sqlite":
            self.server_status_lbl.setText("🟡 Running in Standalone / Offline Mode")
            self.server_status_lbl.setStyleSheet("""
                QLabel {
                    color: #F59E0B;
                    font-size: 10px;
                    font-weight: 700;
                    background-color: rgba(245, 158, 11, 0.12);
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)
        else:
            self.server_status_lbl.setText(f"🔴 Central Server Offline ({host}:{port})")
            self.server_status_lbl.setStyleSheet("""
                QLabel {
                    color: #EF4444;
                    font-size: 10px;
                    font-weight: 700;
                    background-color: rgba(239, 68, 68, 0.12);
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    border-radius: 12px;
                    padding: 2px 10px;
                }
            """)

    def _open_server_settings(self):
        dlg = ServerConfigDialog(self)
        if dlg.exec() == QDialog.Accepted:
            db.connect()
            self._update_server_status_badge()

    def _toggle_password_visibility(self):
        if self.password_edit.echoMode() == QLineEdit.Password:
            self.password_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)

    def _load_saved_username(self):
        saved_file = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JayraldinesCatering" / "last_username.txt"
        if saved_file.exists():
            try:
                name = saved_file.read_text(encoding="utf-8").strip()
                if name:
                    self.username_edit.setText(name)
                    self.password_edit.setFocus()
                    return
            except Exception:
                pass
        self.username_edit.setFocus()

    def _save_username_if_checked(self, username: str):
        saved_file = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JayraldinesCatering" / "last_username.txt"
        try:
            saved_file.parent.mkdir(parents=True, exist_ok=True)
            if self.cb_remember.isChecked():
                saved_file.write_text(username, encoding="utf-8")
            elif saved_file.exists():
                saved_file.unlink()
        except Exception:
            pass

    def _do_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self._show_error("Please enter both username and password.")
            return

        self.sign_in_btn.setEnabled(False)
        self.sign_in_btn.setText("Signing in...")
        QApplication.processEvents()

        user_data = authenticate(username, password)
        self.sign_in_btn.setEnabled(True)
        self.sign_in_btn.setText("Sign In")

        if user_data:
            SessionManager.set_user(user_data)
            self._save_username_if_checked(username)
            self.accept()
        else:
            self._show_error("Invalid username or password, or account is deactivated.")
            self._shake_animation()

    def _show_error(self, message: str):
        self.error_lbl.setText(message)
        self.error_lbl.show()

    def _shake_animation(self):
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(300)
        orig = self.pos()
        curve = QEasingCurve.OutBounce
        anim.setEasingCurve(curve)
        anim.setKeyValueAt(0.0, orig)
        anim.setKeyValueAt(0.2, orig + QPoint(-10, 0))
        anim.setKeyValueAt(0.4, orig + QPoint(10, 0))
        anim.setKeyValueAt(0.6, orig + QPoint(-8, 0))
        anim.setKeyValueAt(0.8, orig + QPoint(8, 0))
        anim.setKeyValueAt(1.0, orig)
        anim.start()

    def _on_close_clicked(self):
        self.reject()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class LockScreenDialog(QDialog):
    """
    Non-destructive lock overlay that appears after idle session timeout.
    Requires re-entering the current user's password or allows switching users.
    """
    switch_user_requested = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 360)

        self._drag_pos = None
        user = SessionManager.current_user() or {}
        self.username = user.get("username", "admin")
        self.display_name = user.get("display_name", self.username)
        self.role = user.get("role", "staff").upper()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)

        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E1B4B, stop:0.4 #0F172A, stop:1 #020617);
                border: 2px solid #E11D48;
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 220))
        frame.setGraphicsEffect(shadow)

        f_lay = QVBoxLayout(frame)
        f_lay.setContentsMargins(28, 24, 28, 24)
        f_lay.setSpacing(12)

        # Lock Icon
        lock_lbl = QLabel("🔒")
        lock_lbl.setAlignment(Qt.AlignCenter)
        lock_lbl.setStyleSheet("font-size: 36px; border: none; background: transparent;")
        f_lay.addWidget(lock_lbl)

        title = QLabel("Session Locked")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: 800; border: none; background: transparent;")
        f_lay.addWidget(title)

        u_info = QLabel(f"👤 {self.display_name}  •  [{self.role}]")
        u_info.setAlignment(Qt.AlignCenter)
        u_info.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600; border: none; background: transparent;")
        f_lay.addWidget(u_info)

        msg = QLabel("Enter your password to unlock and resume your session.")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #94A3B8; font-size: 11px; border: none; background: transparent;")
        f_lay.addWidget(msg)

        # Password Input
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("Password")
        self.pwd_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #F8FAFC;
                padding: 8px 12px;
                font-size: 13px;
                border-radius: 8px;
            }
            QLineEdit:focus { border-color: #E11D48; }
        """)
        self.pwd_edit.returnPressed.connect(self._do_unlock)
        f_lay.addWidget(self.pwd_edit)

        self.err_lbl = QLabel()
        self.err_lbl.setAlignment(Qt.AlignCenter)
        self.err_lbl.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        self.err_lbl.hide()
        f_lay.addWidget(self.err_lbl)

        # Unlock button
        unlock_btn = QPushButton("Unlock Session")
        unlock_btn.setFixedHeight(36)
        unlock_btn.setCursor(Qt.PointingHandCursor)
        unlock_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                border-radius: 7px;
                border: none;
            }
            QPushButton:hover { background: #BE123C; }
        """)
        unlock_btn.clicked.connect(self._do_unlock)
        f_lay.addWidget(unlock_btn)

        # Switch user link button
        switch_btn = QPushButton("Switch User / Log Out")
        switch_btn.setCursor(Qt.PointingHandCursor)
        switch_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94A3B8;
                font-size: 11px;
                text-decoration: underline;
            }
            QPushButton:hover { color: #FFFFFF; }
        """)
        switch_btn.clicked.connect(self._on_switch_user)
        f_lay.addWidget(switch_btn)

        lay.addWidget(frame)

    def _do_unlock(self):
        pwd = self.pwd_edit.text()
        user_data = authenticate(self.username, pwd)
        if user_data:
            self.accept()
        else:
            self.err_lbl.setText("Incorrect password.")
            self.err_lbl.show()
            self.pwd_edit.clear()

    def _on_switch_user(self):
        self.switch_user_requested = True
        SessionManager.logout()
        self.reject()

