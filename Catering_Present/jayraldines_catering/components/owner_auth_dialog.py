"""
Master Owner Authorization Dialog for sensitive server maintenance operations.
Restricts database start, stop, and restart actions from standard administrator accounts.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from utils.db_server_service import verify_owner_authorization


class OwnerAuthDialog(QDialog):
    """
    Prompts for Master Owner Authorization passkey to permit
    central database server restart / maintenance operations.
    """

    def __init__(self, parent=None, operation_name: str = "Restart Central Database Server"):
        super().__init__(parent)
        self.operation_name = operation_name
        self.setWindowTitle("Owner Authorization Required")
        self.setFixedSize(480, 260)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
            }
            QLabel {
                color: #F8FAFC;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        # Header Title
        title = QLabel("🔒 Master Owner Authorization")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F59E0B;")
        lay.addWidget(title)

        # Prompt description
        desc = QLabel(
            f"Action: <b>{operation_name}</b><br>"
            "Administrator accounts can monitor status, but server restart/start operations "
            "are restricted to prevent disruption to active order kiosks. Enter the Master Owner "
            "passkey to authorize this operation:"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #CBD5E1; line-height: 1.4;")
        lay.addWidget(desc)

        # Passkey input
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Enter Master Owner Passkey or Password")
        from utils.password_field import add_show_password_toggle
        add_show_password_toggle(self.key_edit)
        self.key_edit.setStyleSheet("""
            QLineEdit {
                background: #1E293B;
                border: 1px solid #334155;
                color: #F8FAFC;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 13px;
                min-height: 24px;
            }
            QLineEdit:focus {
                border-color: #F59E0B;
            }
        """)
        self.key_edit.returnPressed.connect(self._verify_and_accept)
        lay.addWidget(self.key_edit)

        lay.addStretch()

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #CBD5E1;
                padding: 8px 18px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #475569;
                color: #FFFFFF;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        auth_btn = QPushButton("Authorize & Proceed")
        auth_btn.setCursor(Qt.PointingHandCursor)
        auth_btn.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: #FFFFFF;
                font-weight: 700;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #B45309;
            }
        """)
        auth_btn.clicked.connect(self._verify_and_accept)
        btn_row.addWidget(auth_btn)

        lay.addLayout(btn_row)

    def _verify_and_accept(self):
        entered = self.key_edit.text().strip()
        if not entered:
            QMessageBox.warning(self, "Required", "Please enter the Master Owner passkey.")
            return

        if verify_owner_authorization(entered):
            self.accept()
        else:
            QMessageBox.warning(self, "Access Denied", "Incorrect Master Owner Passkey. Authorization failed.")
            self.key_edit.selectAll()
            self.key_edit.setFocus()
