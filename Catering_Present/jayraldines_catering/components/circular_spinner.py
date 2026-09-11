"""
Custom Circular Spinner Widget for Jayraldine's Catering.
Renders a smooth, modern 60-FPS circular loading arc with gradient accents.
"""

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QConicalGradient
from PySide6.QtWidgets import QWidget


class CircularSpinner(QWidget):
    """
    Sleek anti-aliased rotating circular loader.
    """
    def __init__(self, size: int = 56, line_width: int = 4, color_start: str = "#E11D48", color_end: str = "#FB7185", parent=None):
        super().__init__(parent)
        self._size = size
        self._line_width = line_width
        self._color_start = QColor(color_start) if not isinstance(color_start, QColor) else color_start
        self._color_end = QColor(color_end) if not isinstance(color_end, QColor) else color_end
        self._angle = 0
        self._arc_length = 100  # in degrees
        
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 60 FPS animation timer (16 ms)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def set_colors(self, color_start, color_end=None):
        """Safely updates spinner start and optional end colors."""
        if color_start:
            self._color_start = QColor(color_start) if not isinstance(color_start, QColor) else color_start
        if color_end:
            self._color_end = QColor(color_end) if not isinstance(color_end, QColor) else color_end
        self.update()

    def step(self, delta_degrees: int = 10):
        """Immediately advances rotation and forces a synchronous repaint."""
        self._angle = (self._angle + delta_degrees) % 360
        if self.isVisible():
            self.repaint()
        else:
            self.update()

    def _on_tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin = self._line_width / 2.0 + 2.0
        rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)

        # Ensure safe QColor objects
        c_start = self._color_start if isinstance(self._color_start, QColor) else QColor(str(self._color_start))
        c_end = self._color_end if isinstance(self._color_end, QColor) else QColor(str(self._color_end))

        # Draw subtle track ring
        track_pen = QPen(QColor(255, 255, 255, 22), self._line_width)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Draw rotating gradient active arc
        painter.save()
        painter.translate(w / 2.0, h / 2.0)
        painter.rotate(self._angle)
        painter.translate(-w / 2.0, -h / 2.0)

        conical_grad = QConicalGradient(w / 2.0, h / 2.0, 0)
        conical_grad.setColorAt(0.0, c_end)
        conical_grad.setColorAt(0.25, c_start)
        conical_grad.setColorAt(0.4, QColor(c_start.red(), c_start.green(), c_start.blue(), 20))
        conical_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

        arc_pen = QPen(conical_grad, self._line_width)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)

        # Qt angles are in 1/16th of a degree
        start_angle = 0 * 16
        span_angle = int(self._arc_length * 16)
        painter.drawArc(rect, start_angle, span_angle)

        painter.restore()
