from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, Property, QRect
from PySide6.QtGui import QColor


_COLOR_MAP = {
    "#F59E0B": ("#F59E0B", "rgba(245,158,11,0.12)"),
    "#F97316": ("#F97316", "rgba(249,115,22,0.12)"),
    "#EF4444": ("#EF4444", "rgba(239,68,68,0.12)"),
    "#22C55E": ("#22C55E", "rgba(34,197,94,0.12)"),
    "#3B82F6": ("#3B82F6", "rgba(59,130,246,0.12)"),
}


class Toast(QWidget):
    def __init__(self, title: str, message: str, color: str = "#3B82F6", parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(360)

        accent, bg = _COLOR_MAP.get(color, (color, "rgba(59,130,246,0.12)"))

        container = QWidget(self)
        container.setObjectName("toastContainer")
        container.setStyleSheet(f"""
            QWidget#toastContainer {{
                background: #1F2937;
                border: 1px solid {accent};
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)

        top_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {accent}; font-size: 10px;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #F9FAFB; font-weight: 700; font-size: 13px;")
        title_lbl.setWordWrap(True)
        top_row.addWidget(dot)
        top_row.addWidget(title_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("background: transparent; border: none; color: #6B7280; font-size: 11px;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self._dismiss)
        top_row.addWidget(close_btn)
        lay.addLayout(top_row)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        msg_lbl.setWordWrap(True)
        lay.addWidget(msg_lbl)

        self._anim_in  = None
        self._anim_out = None
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._dismiss)

    def show_toast(self, duration_ms: int = 6000):
        self.adjustSize()
        self._position()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._anim_in = QPropertyAnimation(self, b"windowOpacity")
        self._anim_in.setDuration(350)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_in.start()

        self._auto_timer.start(duration_ms)

    def _position(self):
        parent = self.parent()
        if parent and parent.isVisible():
            pr = parent.geometry()
            x = pr.right() - self.width() - 20
            y = pr.top() + 72
        else:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 72
        self.move(x, y)

    def _dismiss(self):
        self._auto_timer.stop()
        self._anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(self.windowOpacity())
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.close)
        self._anim_out.start()


class ToastManager:
    def __init__(self, parent=None):
        self._parent = parent
        self._stack: list[Toast] = []

    def show(self, title: str, message: str, color: str = "#3B82F6", duration_ms: int = 6000):
        toast = Toast(title, message, color, self._parent)
        toast.destroyed.connect(lambda: self._on_closed(toast))
        self._stack.append(toast)
        self._reposition()
        toast.show_toast(duration_ms)

    def _on_closed(self, toast):
        if toast in self._stack:
            self._stack.remove(toast)
        self._reposition()

    def _reposition(self):
        parent = self._parent
        if parent and parent.isVisible():
            pr = parent.geometry()
            base_x = pr.right() - 380
            base_y = pr.top() + 72
        else:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            base_x = screen.right() - 380
            base_y = screen.top() + 72

        offset = 0
        for t in self._stack:
            t.move(base_x, base_y + offset)
            offset += t.height() + 10
