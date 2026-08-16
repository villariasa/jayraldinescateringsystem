"""
LoadingOverlay — Glassmorphism loading spinner overlay widget for Jayraldine's Catering System.
Displays a non-blocking semi-transparent loading card with animated spinner and status message
over any container during database operations, saving, updating, or deleting.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QProgressBar
from PySide6.QtCore import Qt, QTimer, QSize, QEvent
from PySide6.QtGui import QColor, QPainter, QConicalGradient, QPen

from utils.theme import ThemeManager
from utils.accent import AccentManager


class SpinnerWidget(QWidget):
    """Smooth rotating circular spinner widget."""
    def __init__(self, size=36, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16) # ~60 FPS
        self._timer.timeout.connect(self._rotate)
        self._timer.start()

    def _rotate(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(4, 4, -4, -4)
        
        color_current = QColor(AccentManager().current)

        # Draw track
        track_pen = QPen(QColor(148, 163, 184, 40), 3)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Draw arc
        arc_pen = QPen(color_current, 3)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(rect, int(-self._angle * 16), int(120 * 16))


class LoadingOverlay(QWidget):
    """Full overlay loading mask for dialogs and page cards."""
    def __init__(self, parent=None, text="Processing data, please wait..."):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        if parent:
            self.setGeometry(parent.rect())
            parent.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Glassmorphism container card
        card = QFrame()
        card.setObjectName("cardElevated")
        card.setStyleSheet(
            "QFrame#cardElevated { background-color: %s; border-radius: 14px; border: 1px solid %s; }"
            % (
                "rgba(255, 255, 255, 0.95)" if not ThemeManager().is_dark() else "rgba(30, 41, 59, 0.95)",
                "#E2E8F0" if not ThemeManager().is_dark() else "#334155"
            )
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(24, 20, 24, 20)
        card_lay.setSpacing(12)
        card_lay.setAlignment(Qt.AlignCenter)

        self._spinner = SpinnerWidget(size=40)
        card_lay.addWidget(self._spinner, alignment=Qt.AlignCenter)

        self._lbl_text = QLabel(text)
        self._lbl_text.setAlignment(Qt.AlignCenter)
        self._lbl_text.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: %s;"
            % ("#0F172A" if not ThemeManager().is_dark() else "#F8FAFC")
        )
        card_lay.addWidget(self._lbl_text)

        layout.addWidget(card)
        self.hide()

    def set_text(self, text: str):
        self._lbl_text.setText(text)

    def show_overlay(self, text: str = None):
        if text:
            self.set_text(text)
        if self.parent():
            self.setGeometry(self.parent().rect())
            self.raise_()
        self.show()

    def hide_overlay(self):
        self.hide()

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.setGeometry(self.parent().rect())
        return super().eventFilter(obj, event)
