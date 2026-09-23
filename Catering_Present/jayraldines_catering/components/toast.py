"""Transient toast notifications and a manager that stacks them.

``Toast`` is a single frameless, translucent notification card that auto-dismisses
after a timeout. ``ToastManager`` owns the on-screen stack (max 3), positioning
new toasts in the top-right of the host window and repositioning the rest as they
appear or disappear.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QMouseEvent

from utils.theme import ThemeManager


# Accent colours keyed by hex; used to validate/normalize the requested colour.
_COLOR_MAP = {
    "#F59E0B": "#F59E0B",
    "#F97316": "#F97316",
    "#EF4444": "#EF4444",
    "#22C55E": "#22C55E",
    "#3B82F6": "#3B82F6",
}


class Toast(QWidget):
    """A single auto-dismissing notification card (title, message, accent, close)."""

    def __init__(self, title: str, message: str, color: str = "#3B82F6", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Show without stealing focus so the toast never interrupts the user's typing.
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedWidth(360)
        self.setMinimumHeight(76)

        # Fall back to the raw colour string if it isn't a known mapped accent.
        accent = _COLOR_MAP.get(color, color)

        # Theme-dependent palette for the card background and text tones.
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

        # Single-shot timer that auto-dismisses the toast after its duration.
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._dismiss)
        # Guard flag so _dismiss() can't run twice (timer + manual click).
        self._dismissing = False

        self.setCursor(Qt.PointingHandCursor)

    def show_toast(self, x: int, y: int, duration_ms: int = 6000):
        """Position the toast at (x, y), show it, and start the auto-dismiss timer."""
        self.adjustSize()
        self.move(x, y)
        self.show()
        self.raise_()
        self._auto_timer.start(duration_ms)

    def _dismiss(self):
        """Hide and schedule deletion of the toast (idempotent)."""
        # Ignore repeat calls (e.g. close click after the timer already fired).
        if self._dismissing:
            return
        self._dismissing = True
        self._auto_timer.stop()
        self.hide()
        self.deleteLater()


class ToastManager:
    """Owns the stack of visible toasts and positions them in the window corner."""

    _MARGIN_RIGHT = 24   # px gap from the window's right edge
    _MARGIN_TOP   = 76   # px gap from the window's top edge (clears the header)
    _GAP          = 10   # px vertical gap between stacked toasts

    def __init__(self):
        self._stack: list[Toast] = []
        self._window = None

    def show(self, title: str, message: str, color: str = "#3B82F6", duration_ms: int = 6000):
        """Create and display a toast, evicting the oldest if the stack is full."""
        # Only stack max 3 toasts at once to prevent clutter
        if len(self._stack) >= 3:
            oldest = self._stack.pop(0)
            oldest._dismiss()

        toast = Toast(title, message, color, parent=self._window)
        self._stack.append(toast)
        self._reposition()
        x, y = self._pos_for(len(self._stack) - 1)
        toast.show_toast(x, y, duration_ms)
        # Re-flow the stack once this toast is destroyed so gaps close up.
        toast.destroyed.connect(lambda: self._remove(toast))

    def _remove(self, toast: Toast):
        """Drop a destroyed toast from the stack and re-layout the survivors."""
        try:
            self._stack.remove(toast)
        except ValueError:
            # Already removed elsewhere; ignore.
            pass
        try:
            # If the host window itself was destroyed, reset state and bail so we
            # don't touch a dangling C++ object.
            from shiboken6 import isValid
            if self._window and not isValid(self._window):
                self._window = None
                self._stack.clear()
                return
        except Exception:
            pass
        self._reposition()

    def set_window(self, window) -> None:
        """Set the host window that toasts are positioned relative to."""
        self._window = window

    def _pos_for(self, idx: int):
        """Compute the (x, y) top-left for the toast at stack index ``idx``."""
        if not self._window:
            # No window bound yet; use a harmless default corner.
            return 100, 100
        win_w = self._window.width()
        # Right-align: window width minus toast width minus margin.
        base_x = win_w - 360 - self._MARGIN_RIGHT
        base_y = self._MARGIN_TOP
        # Sum the heights (+gap) of toasts stacked above this one to get its Y.
        offset = 0
        for i, t in enumerate(self._stack):
            if i == idx:
                break
            offset += t.height() + self._GAP
        return max(20, base_x), base_y + offset

    def _reposition(self):
        """Re-stack all live toasts top-down against the window's top-right."""
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
                # Toast's C++ side was already deleted; skip it.
                pass
