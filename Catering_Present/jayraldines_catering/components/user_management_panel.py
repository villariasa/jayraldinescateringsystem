"""
Jayraldine's Catering - User Management & RBAC Administration Panel.
Allows Admins to manage staff accounts, permissions matrix, and password resets.
Also provides self-service password changing for logged-in users.
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QLineEdit, QComboBox, QCheckBox, QFrame, QMessageBox,
    QGraphicsDropShadowEffect, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from utils.auth import (
    list_users, create_user, update_user_password,
    update_user_permissions, set_user_active,
    validate_password, get_user_permissions,
    ALL_MODULES, MODULE_DISPLAY_NAMES, SessionManager
)
from utils.db_config import get_db_config, get_config_path


class ResetPasswordDialog(QDialog):
    """Admin password reset dialog for any user account."""
    def __init__(self, user_id: int, username: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.setWindowTitle(f"Reset Password — {username}")
        self.resize(450, 270)
        self.setMinimumSize(420, 250)
        self.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        t_lbl = QLabel(f"Set New Password for '{username}':")
        t_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        lay.addWidget(t_lbl)

        input_style = "background: #1E293B; border: 1px solid #334155; color: #F8FAFC; padding: 8px 12px; border-radius: 6px; font-size: 13px; min-height: 22px;"

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("Minimum 8 chars, 1 letter, 1 number")
        self.pwd_edit.setStyleSheet(input_style)
        lay.addWidget(self.pwd_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit.setPlaceholderText("Confirm new password")
        self.confirm_edit.setStyleSheet(input_style)
        lay.addWidget(self.confirm_edit)

        lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("background: #334155; color: #CBD5E1; padding: 8px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; min-height: 34px;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Reset Password")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("background: #E11D48; color: #FFFFFF; font-weight: 700; padding: 8px 22px; border-radius: 6px; font-size: 13px; min-height: 34px;")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _on_save(self):
        pwd = self.pwd_edit.text()
        conf = self.confirm_edit.text()
        if pwd != conf:
            QMessageBox.warning(self, "Mismatch", "Passwords do not match.")
            return

        ok, err = update_user_password(self.user_id, pwd)
        if ok:
            QMessageBox.information(self, "Success", f"Password for '{self.username}' has been reset successfully.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", err)


class ChangeOwnPasswordDialog(QDialog):
    """Dialog allowing the currently logged-in user to change their own password."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = SessionManager.current_user() or {}
        self.setWindowTitle("Change Password")
        self.resize(460, 320)
        self.setMinimumSize(430, 300)
        self.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        t_lbl = QLabel(f"Change Password — {self.user.get('display_name', 'User')}")
        t_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        lay.addWidget(t_lbl)

        input_style = "background: #1E293B; border: 1px solid #334155; color: #F8FAFC; padding: 8px 12px; border-radius: 6px; font-size: 13px; min-height: 22px;"

        self.new_pwd_edit = QLineEdit()
        self.new_pwd_edit.setEchoMode(QLineEdit.Password)
        self.new_pwd_edit.setPlaceholderText("New password (8+ chars, 1 letter, 1 number)")
        self.new_pwd_edit.setStyleSheet(input_style)
        lbl_new = QLabel("New Password:")
        lbl_new.setStyleSheet("font-size: 12px; font-weight: 600; color: #94A3B8;")
        lay.addWidget(lbl_new)
        lay.addWidget(self.new_pwd_edit)

        self.conf_pwd_edit = QLineEdit()
        self.conf_pwd_edit.setEchoMode(QLineEdit.Password)
        self.conf_pwd_edit.setPlaceholderText("Confirm new password")
        self.conf_pwd_edit.setStyleSheet(input_style)
        lbl_conf = QLabel("Confirm New Password:")
        lbl_conf.setStyleSheet("font-size: 12px; font-weight: 600; color: #94A3B8;")
        lay.addWidget(lbl_conf)
        lay.addWidget(self.conf_pwd_edit)

        lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("background: #334155; color: #CBD5E1; padding: 8px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; min-height: 34px;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Update Password")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("background: #E11D48; color: #FFFFFF; font-weight: 700; padding: 8px 22px; border-radius: 6px; font-size: 13px; min-height: 34px;")
        save_btn.clicked.connect(self._on_update)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _on_update(self):
        new_pwd = self.new_pwd_edit.text()
        conf = self.conf_pwd_edit.text()
        if new_pwd != conf:
            QMessageBox.warning(self, "Mismatch", "Passwords do not match.")
            return

        user_id = self.user.get("id")
        if not user_id:
            QMessageBox.warning(self, "Error", "No active user session.")
            return

        ok, err = update_user_password(user_id, new_pwd)
        if ok:
            QMessageBox.information(self, "Success", "Your password has been changed successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", err)


class PermissionsMatrixDialog(QDialog):
    """Admin dialog to view and configure granular module permissions."""
    def __init__(self, user_id: int, username: str, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.username = username
        self.setWindowTitle(f"Edit Permissions — {username}")
        self.resize(740, 620)
        self.setMinimumSize(680, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
            }
            QLabel {
                background: transparent;
                color: #F8FAFC;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        t_lbl = QLabel(f"Module Permissions Matrix for '{username}'")
        t_lbl.setStyleSheet("font-size: 17px; font-weight: 700; color: #F8FAFC; padding-bottom: 2px;")
        lay.addWidget(t_lbl)

        # Quick Presets Buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        p_title = QLabel("Presets:")
        p_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #94A3B8;")
        preset_row.addWidget(p_title)

        for name, preset_vals in [
            ("Full Access", (True, True, True, True)),
            ("Standard Staff", (True, True, True, False)),
            ("Read Only", (True, False, False, False)),
            ("Clear All", (False, False, False, False)),
        ]:
            b = QPushButton(name)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background: #1E293B;
                    border: 1px solid #475569;
                    color: #E2E8F0;
                    padding: 6px 14px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    min-height: 26px;
                }
                QPushButton:hover {
                    background: #334155;
                    border-color: #64748B;
                    color: #FFFFFF;
                }
            """)
            b.clicked.connect(lambda _, pv=preset_vals: self._apply_preset(pv))
            preset_row.addWidget(b)
        preset_row.addStretch()
        lay.addLayout(preset_row)

        # Permissions Grid Frame
        grid_frame = QFrame()
        grid_frame.setObjectName("permGridFrame")
        grid_frame.setStyleSheet("""
            QFrame#permGridFrame {
                background-color: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        g_lay = QGridLayout(grid_frame)
        g_lay.setContentsMargins(20, 16, 20, 16)
        g_lay.setHorizontalSpacing(24)
        g_lay.setVerticalSpacing(12)

        # Headers
        headers = ["Module", "View", "Create", "Edit", "Delete"]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            if col == 0:
                lbl.setStyleSheet("font-weight: 700; color: #94A3B8; font-size: 13px; padding: 2px 0px;")
            else:
                lbl.setStyleSheet("font-weight: 700; color: #94A3B8; font-size: 13px; padding: 2px 0px;")
                lbl.setAlignment(Qt.AlignCenter)
            lbl.setMinimumHeight(24)
            g_lay.addWidget(lbl, 0, col)

        self.checks: Dict[str, Dict[str, QCheckBox]] = {}
        current_perms = get_user_permissions(user_id)

        cb_style = """
            QCheckBox {
                spacing: 0px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 2px solid #475569;
                background-color: #0F172A;
            }
            QCheckBox::indicator:hover {
                border-color: #FB7185;
                background-color: #1E293B;
            }
            QCheckBox::indicator:checked {
                background-color: #E11D48;
                border-color: #FB7185;
            }
        """

        for row, mod in enumerate(ALL_MODULES, start=1):
            disp = MODULE_DISPLAY_NAMES.get(mod, mod)
            mod_lbl = QLabel(disp)
            mod_lbl.setStyleSheet("color: #F8FAFC; font-size: 13px; font-weight: 600; padding: 4px 0px;")
            mod_lbl.setMinimumHeight(28)
            g_lay.addWidget(mod_lbl, row, 0)

            self.checks[mod] = {}
            for col, action in enumerate(["view", "create", "edit", "delete"], start=1):
                cb = QCheckBox()
                cb.setCursor(Qt.PointingHandCursor)
                cb.setStyleSheet(cb_style)
                is_checked = current_perms.get(mod, {}).get(action, False)
                cb.setChecked(is_checked)
                g_lay.addWidget(cb, row, col, alignment=Qt.AlignCenter)
                self.checks[mod][action] = cb

        lay.addWidget(grid_frame)
        lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #CBD5E1;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 22px;
                border-radius: 6px;
                min-height: 34px;
            }
            QPushButton:hover {
                background: #475569;
                color: #FFFFFF;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save Permissions")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 26px;
                border-radius: 6px;
                min-height: 34px;
            }
            QPushButton:hover {
                background: #BE123C;
            }
        """)
        save_btn.clicked.connect(self._save_permissions)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _apply_preset(self, vals: tuple):
        v, c, e, d = vals
        for mod, acts in self.checks.items():
            acts["view"].setChecked(v)
            acts["create"].setChecked(c)
            acts["edit"].setChecked(e)
            acts["delete"].setChecked(d)

    def _save_permissions(self):
        new_perms: Dict[str, Dict[str, bool]] = {}
        for mod, acts in self.checks.items():
            new_perms[mod] = {
                "view": acts["view"].isChecked(),
                "create": acts["create"].isChecked(),
                "edit": acts["edit"].isChecked(),
                "delete": acts["delete"].isChecked(),
            }
        update_user_permissions(self.user_id, new_perms)
        QMessageBox.information(self, "Saved", f"Permissions updated for '{self.username}'.")
        self.accept()


class CreateUserDialog(QDialog):
    """Admin dialog to create a new user account."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New User Account")
        self.resize(480, 440)
        self.setMinimumSize(450, 400)
        self.setStyleSheet("background-color: #0F172A; color: #F8FAFC;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        t_lbl = QLabel("Create User Account")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC; padding-bottom: 2px;")
        lay.addWidget(t_lbl)

        input_style = "background: #1E293B; border: 1px solid #334155; color: #F8FAFC; padding: 8px 12px; border-radius: 6px; font-size: 13px; min-height: 22px;"
        lbl_style = "font-size: 12px; font-weight: 600; color: #94A3B8;"

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Username (e.g. maria_cashier)")
        self.username_edit.setStyleSheet(input_style)
        l_u = QLabel("Username:")
        l_u.setStyleSheet(lbl_style)
        lay.addWidget(l_u)
        lay.addWidget(self.username_edit)

        self.display_edit = QLineEdit()
        self.display_edit.setPlaceholderText("Full Name / Display Name")
        self.display_edit.setStyleSheet(input_style)
        l_d = QLabel("Display Name:")
        l_d.setStyleSheet(lbl_style)
        lay.addWidget(l_d)
        lay.addWidget(self.display_edit)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["staff", "admin"])
        self.role_combo.setStyleSheet(input_style)
        l_r = QLabel("Role:")
        l_r.setStyleSheet(lbl_style)
        lay.addWidget(l_r)
        lay.addWidget(self.role_combo)

        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.Password)
        self.pwd_edit.setPlaceholderText("Minimum 8 chars, 1 letter, 1 number")
        self.pwd_edit.setStyleSheet(input_style)
        l_p = QLabel("Initial Password:")
        l_p.setStyleSheet(lbl_style)
        lay.addWidget(l_p)
        lay.addWidget(self.pwd_edit)

        lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("background: #334155; color: #CBD5E1; padding: 8px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; min-height: 34px;")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        create_btn = QPushButton("Create Account")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                color: #FFFFFF;
                font-weight: 700;
                padding: 8px 22px;
                border-radius: 6px;
                font-size: 13px;
                min-height: 34px;
            }
            QPushButton:hover {
                background: #BE123C;
            }
        """)
        create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(create_btn)
        lay.addLayout(btn_row)

    def _on_create(self):
        username = self.username_edit.text().strip()
        display_name = self.display_edit.text().strip() or username
        role = self.role_combo.currentText()
        pwd = self.pwd_edit.text()

        cur_user = SessionManager.current_user() or {}
        creator_id = cur_user.get("id")

        ok, err, new_id = create_user(
            username=username,
            password=pwd,
            display_name=display_name,
            role=role,
            created_by=creator_id
        )

        if ok:
            QMessageBox.information(self, "Success", f"User '{username}' created successfully!")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", err)


class UserManagementPanel(QWidget):
    """
    Main user management view for system administrators.
    Integrated into Settings tab.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("userManagementPanel")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(12)

        # Header bar with Actions
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("User Accounts & Access Control")
        t.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        sub = QLabel("Manage system users, reset passwords, and configure per-module permissions.")
        sub.setStyleSheet("font-size: 11px; color: #94A3B8;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        header_row.addLayout(title_box)

        header_row.addStretch()

        new_user_btn = QPushButton("+ Create User")
        new_user_btn.setCursor(Qt.PointingHandCursor)
        new_user_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #F43F5E);
                color: #FFFFFF;
                font-weight: 700;
                padding: 7px 16px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background: #BE123C; }
        """)
        new_user_btn.clicked.connect(self._create_user_dialog)
        header_row.addWidget(new_user_btn)

        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("background: #1E293B; border: 1px solid #334155; color: #CBD5E1; padding: 7px 14px; border-radius: 6px; font-size: 12px;")
        refresh_btn.clicked.connect(self.reload_users)
        header_row.addWidget(refresh_btn)

        lay.addLayout(header_row)

        # Users Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Display Name", "Role", "Status", "Last Login", "Actions"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(5, 170)
        self.table.setColumnWidth(6, 340)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0F172A;
                gridline-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #F8FAFC;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 10px 12px;
                font-weight: 700;
                font-size: 13px;
                border: none;
            }
        """)
        lay.addWidget(self.table)

        self.reload_users()

    def reload_users(self):
        from utils.data_loader import run_async
        run_async(self, list_users, self._on_users_loaded)

    def _on_users_loaded(self, users):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        users = users or []
        self.table.setRowCount(len(users))

        for row, u in enumerate(users):
            u_id = u["id"]
            uname = u["username"]
            role = u.get("role", "staff")
            is_active = bool(u.get("is_active", True))

            item_id = QTableWidgetItem(str(u_id))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            item_uname = QTableWidgetItem(uname)
            item_uname.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, 1, item_uname)

            item_dname = QTableWidgetItem(u.get("display_name") or uname)
            item_dname.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, 2, item_dname)

            item_role = QTableWidgetItem(role.upper())
            item_role.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, item_role)

            status_item = QTableWidgetItem("Active" if is_active else "Deactivated")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor("#10B981" if is_active else "#EF4444"))
            self.table.setItem(row, 4, status_item)

            last_log = str(u.get("last_login") or "Never")
            item_log = QTableWidgetItem(last_log)
            item_log.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, 5, item_log)

            # Actions Cell
            actions_widget = QWidget()
            a_lay = QHBoxLayout(actions_widget)
            a_lay.setContentsMargins(6, 6, 6, 6)
            a_lay.setSpacing(8)
            a_lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Permissions button
            if role != "admin":
                perm_btn = QPushButton("Permissions")
                perm_btn.setCursor(Qt.PointingHandCursor)
                perm_btn.setStyleSheet("""
                    QPushButton {
                        background: #0284C7;
                        color: #FFFFFF;
                        padding: 6px 13px;
                        font-size: 12px;
                        font-weight: 600;
                        border-radius: 6px;
                        min-height: 28px;
                    }
                    QPushButton:hover {
                        background: #0369A1;
                    }
                """)
                perm_btn.clicked.connect(lambda _, uid=u_id, un=uname: self._open_permissions(uid, un))
                a_lay.addWidget(perm_btn)

            # Reset Password button
            reset_btn = QPushButton("Reset Pwd")
            reset_btn.setCursor(Qt.PointingHandCursor)
            reset_btn.setStyleSheet("""
                QPushButton {
                    background: #334155;
                    color: #F8FAFC;
                    padding: 6px 13px;
                    font-size: 12px;
                    font-weight: 600;
                    border-radius: 6px;
                    min-height: 28px;
                }
                QPushButton:hover {
                    background: #475569;
                }
            """)
            reset_btn.clicked.connect(lambda _, uid=u_id, un=uname: self._reset_password_dialog(uid, un))
            a_lay.addWidget(reset_btn)

            # Toggle status button
            if uname != "admin":
                toggle_btn = QPushButton("Deactivate" if is_active else "Activate")
                toggle_btn.setCursor(Qt.PointingHandCursor)
                btn_color = "#E11D48" if is_active else "#10B981"
                btn_hover = "#BE123C" if is_active else "#059669"
                toggle_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {btn_color};
                        color: #FFFFFF;
                        padding: 6px 13px;
                        font-size: 12px;
                        font-weight: 600;
                        border-radius: 6px;
                        min-height: 28px;
                    }}
                    QPushButton:hover {{
                        background: {btn_hover};
                    }}
                """)
                toggle_btn.clicked.connect(lambda _, uid=u_id, act=is_active: self._toggle_user_status(uid, act))
                a_lay.addWidget(toggle_btn)

            self.table.setCellWidget(row, 6, actions_widget)

    def _create_user_dialog(self):
        dlg = CreateUserDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.reload_users()

    def _open_permissions(self, user_id: int, username: str):
        dlg = PermissionsMatrixDialog(user_id, username, self)
        dlg.exec()

    def _reset_password_dialog(self, user_id: int, username: str):
        dlg = ResetPasswordDialog(user_id, username, self)
        dlg.exec()

    def _toggle_user_status(self, user_id: int, current_active: bool):
        new_active = not current_active
        action_name = "deactivate" if current_active else "activate"
        if QMessageBox.question(
            self, "Confirm Action",
            f"Are you sure you want to {action_name} this user account?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            ok, msg = set_user_active(user_id, new_active)
            if ok:
                self.reload_users()
            else:
                QMessageBox.warning(self, "Error", msg)
