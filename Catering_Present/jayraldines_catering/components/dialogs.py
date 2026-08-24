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
        msg_lbl = QLabel()
        msg_lbl.setText(f"<div style='line-height: 140%;'>{message}</div>")
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

        msg_lbl = QLabel()
        msg_lbl.setText(f"<div style='line-height: 140%;'>{message}</div>")
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


class ExportSuccessDialog(QDialog):
    """
    Sleek, modern prompt modal shown whenever any file (PDF, Excel, CSV, Backup, Report)
    is exported or downloaded. Allows user to Open File, Open Containing Folder, or Copy Path.
    """
    def __init__(self, parent=None, file_path: str = "", title: str = "Export Successful",
                 message: str = "File has been exported successfully."):
        super().__init__(parent)
        import os
        self.file_path = os.path.normpath(file_path) if file_path else ""
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)
        self.setModal(True)
        self._build(title, message)

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240)

    def _build(self, title: str, message: str):
        import os
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("modalCard")
        create_soft_shadow(container, radius=32, y_offset=8, opacity=45)
        inner = QVBoxLayout(container)
        inner.setContentsMargins(26, 24, 26, 22)
        inner.setSpacing(14)

        # Header row: Icon chip + Title + Close button
        header = QHBoxLayout()
        header.setSpacing(14)

        ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ""
        if ext == ".pdf":
            chip = _icon_chip("PDF", "#DC2626", "rgba(220,38,38,0.12)", size=44)
        elif ext in (".xlsx", ".xls"):
            chip = _icon_chip("XLS", "#16A34A", "rgba(22,163,74,0.12)", size=44)
        elif ext == ".csv":
            chip = _icon_chip("CSV", "#2563EB", "rgba(37,99,235,0.12)", size=44)
        elif ext in (".db", ".bak", ".sqlite"):
            chip = _icon_chip("DB", "#9333EA", "rgba(147,51,234,0.12)", size=44)
        else:
            chip = _icon_chip("DOC", "#0D9488", "rgba(13,148,136,0.12)", size=44)

        header.addWidget(chip, alignment=Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("h3")
        text_col.addWidget(title_lbl)

        msg_lbl = QLabel(message or "Your file is ready to view.")
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

        # File Card Info Box
        if self.file_path:
            file_box = QFrame()
            file_box.setObjectName("cardElevated")
            file_box.setStyleSheet(
                "border-radius: 8px; padding: 6px 10px;"
            )
            box_lay = QVBoxLayout(file_box)
            box_lay.setContentsMargins(10, 8, 10, 8)
            box_lay.setSpacing(4)

            fname = os.path.basename(self.file_path)
            f_label = QLabel(f"📄 <b>{fname}</b>")
            f_label.setTextFormat(Qt.RichText)
            box_lay.addWidget(f_label)

            path_row = QHBoxLayout()
            path_row.setSpacing(6)
            p_lbl = QLabel(self.file_path)
            p_lbl.setObjectName("subtitle")
            p_lbl.setStyleSheet("font-size: 11px;")
            p_lbl.setWordWrap(True)
            path_row.addWidget(p_lbl, 1)

            from PySide6.QtWidgets import QApplication
            copy_btn = QPushButton("Copy Path")
            copy_btn.setObjectName("secondaryButton")
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.setFixedHeight(24)
            copy_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
            def _copy_path():
                clipboard = QApplication.clipboard()
                if clipboard:
                    clipboard.setText(self.file_path)
                copy_btn.setText("✓ Copied")
                QTimer.singleShot(1500, lambda: copy_btn.setText("Copy Path"))
            copy_btn.clicked.connect(_copy_path)
            path_row.addWidget(copy_btn, 0, Qt.AlignRight)
            box_lay.addLayout(path_row)

            inner.addWidget(file_box)

        inner.addSpacing(6)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        open_folder_btn = QPushButton("📁 Open Folder")
        open_folder_btn.setObjectName("secondaryButton")
        open_folder_btn.setCursor(Qt.PointingHandCursor)
        open_folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(open_folder_btn)

        open_file_btn = QPushButton("📂 Open File")
        open_file_btn.setObjectName("primaryButton")
        open_file_btn.setCursor(Qt.PointingHandCursor)
        open_file_btn.setDefault(True)
        open_file_btn.clicked.connect(self._open_file)
        btn_row.addWidget(open_file_btn)

        inner.addLayout(btn_row)
        outer.addWidget(container)

    def _open_file(self):
        import os
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        try:
            if self.file_path and os.path.exists(self.file_path):
                if os.name == "nt":
                    os.startfile(self.file_path)
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        except Exception:
            pass
        self.accept()

    def _open_folder(self):
        import os
        import subprocess
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        try:
            if self.file_path and os.path.exists(self.file_path):
                if os.name == "nt":
                    subprocess.Popen(f'explorer /select,"{self.file_path}"')
                else:
                    folder = os.path.dirname(self.file_path)
                    QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        except Exception:
            try:
                folder = os.path.dirname(self.file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            except Exception:
                pass
        self.accept()


def prompt_file_saved(parent, file_path: str, title: str = "Export Successful", message: str = ""):
    """Convenience helper to show the Open File / Open Folder prompt modal."""
    if not file_path:
        return
    dlg = ExportSuccessDialog(parent=parent, file_path=file_path, title=title, message=message)
    dlg.exec()

