from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QMouseEvent


_COLOR_MAP = {
    "#F59E0B": "#F59E0B",
    "#F97316": "#F97316",
    "#EF4444": "#EF4444",
    "#22C55E": "#22C55E",
    "#3B82F6": "#3B82F6",
}


class Toast(QWidget):
    def __init__(self, title: str, message: str, color: str = "#3B82F6"):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFixedWidth(360)
        self.setMinimumHeight(80)

        accent = _COLOR_MAP.get(color, color)

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

        container.setMinimumHeight(80)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

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
        msg_lbl.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        msg_lbl.setWordWrap(True)
        msg_lbl.setMinimumHeight(20)
        lay.addWidget(msg_lbl)

        self._anim_in   = None
        self._anim_out  = None
        self._anim_slide = None
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._dismiss)
        self._dismissing = False

        self._drag_start_pos = None
        self._drag_start_x   = None
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_start_x   = self.x()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_pos is None:
            return
        delta_x = event.globalPosition().toPoint().x() - self._drag_start_pos.x()
        if delta_x > 0:
            self.move(self._drag_start_x + delta_x, self.y())
            opacity = max(0.0, 1.0 - delta_x / self.width())
            self.setWindowOpacity(opacity)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_start_pos is None:
            return
        delta_x = event.globalPosition().toPoint().x() - self._drag_start_pos.x()
        self._drag_start_pos = None
        if delta_x > self.width() * 0.3:
            self._slide_out()
        elif delta_x < 5:
            self._dismiss()
        else:
            self.move(self._drag_start_x, self.y())
            self.setWindowOpacity(1.0)

    def show_toast(self, x: int, y: int, duration_ms: int = 7000):
        self.adjustSize()
        if self.height() < 80:
            self.setFixedHeight(80)
        self.move(x, y)
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

    def _slide_out(self):
        if self._dismissing:
            return
        self._dismissing = True
        self._auto_timer.stop()
        screen = QApplication.primaryScreen()
        target_x = screen.availableGeometry().right() + 20 if screen else self.x() + 400
        self._anim_slide = QPropertyAnimation(self, b"pos")
        self._anim_slide.setDuration(250)
        self._anim_slide.setStartValue(self.pos())
        self._anim_slide.setEndValue(QPoint(target_x, self.y()))
        self._anim_slide.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_slide.finished.connect(self.close)
        self._anim_slide.start()

    def _dismiss(self):
        if self._dismissing:
            return
        self._dismissing = True
        self._auto_timer.stop()
        self._anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(self.windowOpacity())
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.close)
        self._anim_out.start()


class ToastManager:
    _MARGIN_RIGHT = 20
    _MARGIN_TOP   = 72
    _GAP          = 10

    def __init__(self):
        self._stack: list[Toast] = []

    def show(self, title: str, message: str, color: str = "#3B82F6", duration_ms: int = 7000):
        toast = Toast(title, message, color)
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
        self._reposition()

    def _screen_rect(self):
        screen = QApplication.primaryScreen()
        if screen:
            return screen.availableGeometry()
        return None

    def _pos_for(self, idx: int):
        rect = self._screen_rect()
        if rect is None:
            return 100, 100
        base_x = rect.right() - 360 - self._MARGIN_RIGHT
        base_y = rect.top() + self._MARGIN_TOP
        offset = 0
        for i, t in enumerate(self._stack):
            if i == idx:
                break
            offset += t.height() + self._GAP
        return base_x, base_y + offset

    def _reposition(self):
        rect = self._screen_rect()
        if rect is None:
            return
        base_x = rect.right() - 360 - self._MARGIN_RIGHT
        base_y = rect.top() + self._MARGIN_TOP
        offset = 0
        for t in self._stack:
            try:
                t.move(base_x, base_y + offset)
                offset += t.height() + self._GAP
            except RuntimeError:
                pass
