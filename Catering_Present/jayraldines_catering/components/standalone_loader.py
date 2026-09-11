"""
Standalone Theme Loading Overlay Process.
Runs in an independent OS process with its own dedicated GUI thread and Qt event loop.
Immune to main application GUI thread freezes during stylesheet compilation.
"""

import sys
import argparse
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QConicalGradient


class IndependentSpinner(QWidget):
    def __init__(self, size=52, line_width=4, color_start="#E11D48", color_end="#38BDF8", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._line_width = line_width
        self._color_start = QColor(color_start)
        self._color_end = QColor(color_end)
        self._angle = 0
        self._arc_length = 100

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # 60 FPS
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def _on_tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin = self._line_width / 2.0 + 2.0
        rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)

        # Subtle track ring
        track_pen = QPen(QColor(255, 255, 255, 25), self._line_width)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Rotating gradient active arc
        painter.save()
        painter.translate(w / 2.0, h / 2.0)
        painter.rotate(self._angle)
        painter.translate(-w / 2.0, -h / 2.0)

        conical_grad = QConicalGradient(w / 2.0, h / 2.0, 0)
        conical_grad.setColorAt(0.0, self._color_end)
        conical_grad.setColorAt(0.25, self._color_start)
        conical_grad.setColorAt(0.4, QColor(self._color_start.red(), self._color_start.green(), self._color_start.blue(), 20))
        conical_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

        arc_pen = QPen(conical_grad, self._line_width)
        arc_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arc_pen)

        span_angle = int(self._arc_length * 16)
        painter.drawArc(rect, 0, span_angle)
        painter.restore()


class StandaloneOverlayWindow(QWidget):
    def __init__(self, x: int, y: int, w: int, h: int, title: str, accent: str):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setGeometry(x, y, w, h)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

        # Main backdrop layout
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setAlignment(Qt.AlignCenter)

        # Dim backdrop frame
        backdrop = QFrame(self)
        backdrop.setStyleSheet("background: rgba(10, 15, 29, 0.72);")
        back_lay = QVBoxLayout(backdrop)
        back_lay.setAlignment(Qt.AlignCenter)

        # Center Card
        card = QFrame(backdrop)
        card.setObjectName("loaderCard")
        card.setStyleSheet(f"""
            QFrame#loaderCard {{
                background: #1E293B;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 16px;
                padding: 24px 32px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setAlignment(Qt.AlignCenter)
        card_lay.setSpacing(12)

        self.spinner = IndependentSpinner(size=48, line_width=4, color_start=accent, color_end="#38BDF8", parent=card)
        card_lay.addWidget(self.spinner, alignment=Qt.AlignCenter)

        title_lbl = QLabel(title, card)
        title_lbl.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 700; background: transparent;")
        title_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(title_lbl)

        sub_lbl = QLabel("Applying theme palette & styles", card)
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; background: transparent;")
        sub_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(sub_lbl)

        back_lay.addWidget(card)
        root_lay.addWidget(backdrop)

        self._anim = None

        # Safety auto-close after 6 seconds max
        self._safety_timer = QTimer(self)
        self._safety_timer.setSingleShot(True)
        self._safety_timer.timeout.connect(self.close_smoothly)
        self._safety_timer.start(6000)

        # Listen on stdin for close signal
        self._stdin_timer = QTimer(self)
        self._stdin_timer.setInterval(20)
        self._stdin_timer.timeout.connect(self._check_stdin)
        self._stdin_timer.start()

    def _check_stdin(self):
        try:
            import msvcrt
            if msvcrt.kbhit():
                pass
            # Check if stdin is closed by parent
            import os
            if sys.stdin.closed:
                self.close_smoothly()
        except Exception:
            pass

    def close_smoothly(self):
        self._safety_timer.stop()
        self._stdin_timer.stop()
        if self._anim and self._anim.state() == QPropertyAnimation.Running:
            return
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(120)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)
        self._anim.finished.connect(QApplication.instance().quit)
        self._anim.start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=int, default=100)
    parser.add_argument("--y", type=int, default=100)
    parser.add_argument("--w", type=int, default=1280)
    parser.add_argument("--h", type=int, default=768)
    parser.add_argument("--title", type=str, default="Applying Theme...")
    parser.add_argument("--accent", type=str, default="#E11D48")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    overlay = StandaloneOverlayWindow(args.x, args.y, args.w, args.h, args.title, args.accent)
    overlay.show()

    # Read stdin in non-blocking way for CLOSE command
    import threading
    def _read_input():
        try:
            for line in sys.stdin:
                if "CLOSE" in line or "DONE" in line:
                    break
        except Exception:
            pass
        # Signal main thread to close
        QTimer.singleShot(0, overlay.close_smoothly)

    t = threading.Thread(target=_read_input, daemon=True)
    t.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
