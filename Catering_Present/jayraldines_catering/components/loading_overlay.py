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
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._rotate)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _rotate(self):
        if not self.isVisible():
            self._timer.stop()
            return
        self._angle = (self._angle + 6) % 360
        self.update()

    def step(self, delta: int = 14):
        self._angle = (self._angle + delta) % 360
        if self.isVisible():
            self.repaint()
        else:
            self.update()

    def paintEvent(self, event):
        if not self.isVisible():
            return
        painter = QPainter(self)
        if not painter.isActive():
            return
        try:
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
        finally:
            painter.end()



class LoadingOverlay(QWidget):
    """Full overlay loading mask for dialogs and page cards."""
    def __init__(self, parent=None, text="Processing data, please wait..."):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        if parent:
            self.setGeometry(parent.rect())
            parent.installEventFilter(self)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "QWidget#loadingOverlay { background-color: %s; }"
            % ("rgba(241, 245, 249, 0.55)" if not ThemeManager().is_dark() else "rgba(10, 15, 29, 0.65)")
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Glassmorphism container card
        card = QFrame()
        card.setObjectName("cardElevated")
        card.setStyleSheet(
            "QFrame#cardElevated { background-color: %s; border-radius: 14px; border: 1px solid %s; }"
            % (
                "rgba(255, 255, 255, 0.98)" if not ThemeManager().is_dark() else "rgba(30, 41, 59, 0.98)",
                "#E2E8F0" if not ThemeManager().is_dark() else "#334155"
            )
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(28, 22, 28, 22)
        card_lay.setSpacing(14)
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

        layout.addWidget(card, alignment=Qt.AlignCenter)
        self.hide()

    def set_text(self, text: str):
        self._lbl_text.setText(text)

    def show_overlay(self, text: str = None):
        if text:
            self.set_text(text)
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
            p = self.parent()
            if p is not None and isValid(p):
                self.setGeometry(p.rect())
                self.raise_()
            self.show()
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception:
            pass

    def spin_step(self, delta: int = 15):
        """Advances spinner rotation immediately and flushes pending UI events."""
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
            if hasattr(self, "_spinner") and self._spinner and isValid(self._spinner):
                self._spinner.step(delta)
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception:
            pass

    def hide_overlay(self):
        try:
            from shiboken6 import isValid
            if isValid(self):
                self.hide()
        except Exception:
            pass

    def eventFilter(self, obj, event):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return False
            p = self.parent()
            if p is not None and isValid(p) and obj == p and event.type() in (QEvent.Resize, QEvent.Show):
                self.setGeometry(p.rect())
                self.raise_()
        except Exception:
            return False
        return super().eventFilter(obj, event)

