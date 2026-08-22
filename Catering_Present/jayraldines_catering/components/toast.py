from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QMouseEvent

from utils.theme import ThemeManager


_COLOR_MAP = {
    "#F59E0B": "#F59E0B",
    "#F97316": "#F97316",
    "#EF4444": "#EF4444",
    "#22C55E": "#22C55E",
    "#3B82F6": "#3B82F6",
}


class Toast(QWidget):
    def __init__(self, title: str, message: str, color: str = "#3B82F6", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(360)
        self.setMinimumHeight(76)

        accent = _COLOR_MAP.get(color, color)

        if ThemeManager().is_dark():
            bg, title_color, msg_color, close_color = "#1E293B", "#F8FAFC", "#94A3B8", "#64748B"
        else:
            bg, title_color, msg_color, close_color = "#FFFFFF", "#0F172A", "#475569", "#94A3B8"

        container = QWidget(self)
        container.setObjectName("toastContainer")
        container.setStyleSheet(f"""
            QWidget#toastContainer {{
                background-color: {bg};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {accent}; font-size: 10px;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {title_color}; font-weight: 700; font-size: 13px;")
        title_lbl.setWordWrap(True)
        top_row.addWidget(dot)
        top_row.addWidget(title_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(f"background: transparent; border: none; color: {close_color}; font-size: 11px; font-weight: 700;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self._dismiss)
        top_row.addWidget(close_btn)
        lay.addLayout(top_row)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"color: {msg_color}; font-size: 12px; line-height: 130%;")
        msg_lbl.setWordWrap(True)
        lay.addWidget(msg_lbl)

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._dismiss)
        self._dismissing = False

        self.setCursor(Qt.PointingHandCursor)

    def show_toast(self, x: int, y: int, duration_ms: int = 6000):
        self.adjustSize()
        self.move(x, y)
        self.show()
        self.raise_()
        self._auto_timer.start(duration_ms)

    def _dismiss(self):
        if self._dismissing:
            return
        self._dismissing = True
        self._auto_timer.stop()
        self.hide()
        self.deleteLater()


class ToastManager:
    _MARGIN_RIGHT = 24
    _MARGIN_TOP   = 76
    _GAP          = 10

    def __init__(self):
        self._stack: list[Toast] = []
        self._window = None

    def show(self, title: str, message: str, color: str = "#3B82F6", duration_ms: int = 6000):
        # Only stack max 3 toasts at once to prevent clutter
        if len(self._stack) >= 3:
            oldest = self._stack.pop(0)
            oldest._dismiss()

        toast = Toast(title, message, color, parent=self._window)
        self._stack.append(toast)
        self._reposition()
        x, y = self._pos_for(len(self._stack) - 1)
        toast.show_toast(x, y, duration_ms)
        toast.destroyed.connect(lambda: self._remove(toast))

    def _remove(self, toast: Toast):
        try:
            self._stack.remove(toast)
        except ValueError:
            pass
        try:
            from shiboken6 import isValid
            if self._window and not isValid(self._window):
                self._window = None
                self._stack.clear()
                return
        except Exception:
            pass
        self._reposition()

    def set_window(self, window) -> None:
        self._window = window

    def _pos_for(self, idx: int):
        if not self._window:
            return 100, 100
        win_w = self._window.width()
        base_x = win_w - 360 - self._MARGIN_RIGHT
        base_y = self._MARGIN_TOP
        offset = 0
        for i, t in enumerate(self._stack):
            if i == idx:
                break
            offset += t.height() + self._GAP
        return max(20, base_x), base_y + offset

    def _reposition(self):
        if not self._window:
            return
        win_w = self._window.width()
        base_x = win_w - 360 - self._MARGIN_RIGHT
        base_y = self._MARGIN_TOP
        offset = 0
        for t in self._stack:
            try:
                t.move(max(20, base_x), base_y + offset)
                t.raise_()
                offset += t.height() + self._GAP
            except RuntimeError:
                pass
