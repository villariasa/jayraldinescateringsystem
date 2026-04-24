"""
Shared modal dialogs used system-wide.

ConfirmDialog  — "Are you sure?" before destructive actions
SuccessDialog  — "Action completed successfully." after CRUD
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, QSize, QTimer
from utils.icons import get_icon


def _base_modal(parent, width=380):
    dlg = QDialog(parent)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dlg.setAttribute(Qt.WA_TranslucentBackground)
    dlg.setFixedWidth(width)
    dlg.setModal(True)

    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(16, 16, 16, 16)

    container = QFrame()
    container.setObjectName("card")
    container.setStyleSheet("")

    inner = QVBoxLayout(container)
    inner.setContentsMargins(28, 28, 28, 28)
    inner.setSpacing(16)

    outer.addWidget(container)
    return dlg, inner


class ConfirmDialog(QDialog):
    """
    Usage:
        dlg = ConfirmDialog(parent, title="Delete Booking",
                            message="Are you sure you want to delete this booking?",
                            confirm_label="Delete", danger=True)
        if dlg.exec() == QDialog.Accepted:
            # proceed
    """
    def __init__(self, parent=None, title="Confirm Action",
                 message="Are you sure you want to proceed?",
                 confirm_label="Confirm", danger=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(400)
        self.setModal(True)
        self._build(title, message, confirm_label, danger)

    def _build(self, title, message, confirm_label, danger):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        inner = QVBoxLayout(container)
        inner.setContentsMargins(28, 28, 28, 28)
        inner.setSpacing(16)

        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setObjectName("h3")
        header.addWidget(title_lbl)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        inner.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        inner.addWidget(div)

        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("subtitle")
        msg_lbl.setWordWrap(True)
        inner.addWidget(msg_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        ok_btn = QPushButton(f"  {confirm_label}")
        ok_btn.setObjectName("dangerButton" if danger else "primaryButton")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        inner.addLayout(btn_row)
        outer.addWidget(container)


class SuccessDialog(QDialog):
    """
    Auto-closes after `auto_close_ms` milliseconds (default 1800).
    Usage:
        SuccessDialog(parent, message="Booking saved successfully.").exec()
    """
    def __init__(self, parent=None, title="Success",
                 message="Action completed successfully.",
                 auto_close_ms=1800):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(360)
        self.setModal(True)
        self._build(title, message)
        QTimer.singleShot(auto_close_ms, self.accept)

    def _build(self, title, message):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        inner = QVBoxLayout(container)
        inner.setContentsMargins(28, 24, 28, 24)
        inner.setSpacing(12)

        icon_row = QHBoxLayout()
        icon_row.addStretch()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            get_icon("check", color="#22C55E", size=QSize(28, 28)).pixmap(QSize(28, 28))
        )
        icon_row.addWidget(icon_lbl)
        icon_row.addStretch()
        inner.addLayout(icon_row)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("h3")
        title_lbl.setAlignment(Qt.AlignCenter)
        inner.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("subtitle")
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignCenter)
        inner.addWidget(msg_lbl)

        outer.addWidget(container)


def confirm(parent, title="Confirm", message="Are you sure?",
            confirm_label="Confirm", danger=False) -> bool:
    """Convenience one-liner — returns True if user confirmed."""
    dlg = ConfirmDialog(parent, title=title, message=message,
                        confirm_label=confirm_label, danger=danger)
    return dlg.exec() == QDialog.Accepted


def success(parent, message="Action completed successfully.", title="Success"):
    """Convenience one-liner — shows auto-closing success modal."""
    SuccessDialog(parent, title=title, message=message).exec()
