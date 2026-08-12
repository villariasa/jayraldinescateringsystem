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
from utils.animations import animate_dialog_open, create_soft_shadow


def _icon_chip(text: str, fg: str, bg: str, size: int = 40) -> QLabel:
    """Round tinted circle holding a glyph — theme-neutral accent colors."""
    chip = QLabel(text)
    chip.setFixedSize(size, size)
    chip.setAlignment(Qt.AlignCenter)
    chip.setStyleSheet(
        f"background-color: {bg}; color: {fg}; border-radius: {size // 2}px;"
        f" font-size: {size // 2 - 2}px; font-weight: 800; border: none;"
    )
    return chip


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
        self.setFixedWidth(420)
        self.setModal(True)
        self._build(title, message, confirm_label, danger)

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240)

    def _build(self, title, message, confirm_label, danger):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("modalCard")
        create_soft_shadow(container, radius=32, y_offset=8, opacity=45)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(24, 24, 24, 20)
        inner.setSpacing(0)

        # --- header: icon chip + title/message + close ---
        header = QHBoxLayout()
        header.setSpacing(16)

        if danger:
            chip = _icon_chip("!", "#DC2626", "rgba(220,38,38,0.12)")
        else:
            chip = _icon_chip("?", "#D97706", "rgba(217,119,6,0.12)")
        header.addWidget(chip, alignment=Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("h3")
        text_col.addWidget(title_lbl)
        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("subtitle")
        msg_lbl.setWordWrap(True)
        text_col.addWidget(msg_lbl)
        header.addLayout(text_col, 1)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#98A2B3", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn, alignment=Qt.AlignTop)

        inner.addLayout(header)
        inner.addSpacing(22)

        # --- footer buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setMinimumWidth(96)
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        ok_btn = QPushButton(confirm_label)
        ok_btn.setObjectName("dangerFilledButton" if danger else "primaryButton")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setMinimumWidth(110)
        ok_btn.setDefault(True)
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
        self.setFixedWidth(380)
        self.setModal(True)
        self._build(title, message)
        QTimer.singleShot(auto_close_ms, self.accept)

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240)

    def _build(self, title, message):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("modalCard")
        create_soft_shadow(container, radius=32, y_offset=8, opacity=45)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(28, 30, 28, 28)
        inner.setSpacing(12)

        icon_row = QHBoxLayout()
        icon_row.addStretch()
        chip = QLabel()
        chip.setFixedSize(52, 52)
        chip.setAlignment(Qt.AlignCenter)
        chip.setStyleSheet(
            "background-color: rgba(34,197,94,0.12); border-radius: 26px; border: none;"
        )
        chip.setPixmap(
            get_icon("check", color="#16A34A", size=QSize(26, 26)).pixmap(QSize(26, 26))
        )
        icon_row.addWidget(chip)
        icon_row.addStretch()
        inner.addLayout(icon_row)
        inner.addSpacing(4)

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
