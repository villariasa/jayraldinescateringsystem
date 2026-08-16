"""
Jayraldine's Catering - Futuristic Crystal Glass Splash Screen.
Fast, streamlined, and modern startup loader.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QApplication, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QFont, QPainter, QBrush, QLinearGradient, QPen
from utils.paths import resource_path

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "1.3.1"
    APP_NAME = "Jayraldine's Catering"


class CrystalPulseBadge(QWidget):
    """Prismatic glowing emblem badge with smooth breathing animation."""
    def __init__(self, logo_path: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(84, 84)
        self._glow_intensity = 0.6
        self._logo_pixmap = None
        if os.path.exists(logo_path):
            self._logo_pixmap = QPixmap(logo_path).scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_pulse)
        self._step = 0
        self._timer.start(30)

    def _animate_pulse(self):
        import math
        self._step += 0.08
        self._glow_intensity = 0.5 + 0.5 * math.sin(self._step)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        alpha = int(120 + 100 * self._glow_intensity)
        gradient.setColorAt(0.0, QColor(225, 29, 72, alpha))
        gradient.setColorAt(0.5, QColor(56, 189, 248, alpha // 2))
        gradient.setColorAt(1.0, QColor(251, 113, 133, alpha))

        pen = QPen(QBrush(gradient), 2.5)
        painter.setPen(pen)
        painter.setBrush(QColor(15, 23, 42, 220))
        painter.drawRoundedRect(5, 5, self.width() - 10, self.height() - 10, 20, 20)

        inner_pen = QPen(QColor(255, 255, 255, int(30 + 40 * self._glow_intensity)), 1.0)
        painter.setPen(inner_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(8, 8, self.width() - 16, self.height() - 16, 16, 16)

        if self._logo_pixmap:
            x = int(center_x - self._logo_pixmap.width() / 2)
            y = int(center_y - self._logo_pixmap.height() / 2)
            painter.drawPixmap(x, y, self._logo_pixmap)
        else:
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Segoe UI", 24, QFont.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "J")


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(540, 340)

        self._build_ui()
        self._center()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._card = QFrame(self)
        self._card.setObjectName("crystalCard")
        self._card.setStyleSheet("""
            QFrame#crystalCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #020617,
                    stop:0.35 #0F172A,
                    stop:0.75 #1E1B4B,
                    stop:1 #0F172A
                );
                border-radius: 24px;
                border: 1px solid rgba(244, 63, 94, 0.4);
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(42)
        shadow.setYOffset(10)
        shadow.setColor(QColor(225, 29, 72, 110))
        self._card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(36, 28, 36, 26)
        layout.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        sys_tag = QLabel("JAYRALDINE CORE ENGINE")
        sys_tag.setStyleSheet("""
            color: #38BDF8;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            background: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.2);
            padding: 4px 10px;
            border-radius: 12px;
        """)
        top_bar.addWidget(sys_tag)
        top_bar.addStretch()

        ver_tag = QLabel(f"v{__version__}")
        ver_tag.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        top_bar.addWidget(ver_tag)
        layout.addLayout(top_bar)

        layout.addSpacing(14)

        center_box = QVBoxLayout()
        center_box.setSpacing(8)
        center_box.setAlignment(Qt.AlignCenter)

        logo_path = resource_path("assets", "logo.png")
        self._badge = CrystalPulseBadge(logo_path, self)
        center_box.addWidget(self._badge, alignment=Qt.AlignCenter)

        name_lbl = QLabel("Jayraldine's")
        name_lbl.setStyleSheet("""
            color: #FFFFFF;
            font-size: 25px;
            font-weight: 900;
            letter-spacing: -0.5px;
            background: transparent;
        """)
        name_lbl.setAlignment(Qt.AlignCenter)
        center_box.addWidget(name_lbl)

        sub_lbl = QLabel("CATERING & EVENT MANAGEMENT SYSTEM")
        sub_lbl.setStyleSheet("""
            color: #FB7185;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 2px;
            text-transform: uppercase;
            background: transparent;
        """)
        sub_lbl.setAlignment(Qt.AlignCenter)
        center_box.addWidget(sub_lbl)

        layout.addLayout(center_box)
        layout.addStretch()

        # Telemetry Status
        status_row = QHBoxLayout()
        self._status_lbl = QLabel("[SYSTEM CORE] Initializing crystallization engine...")
        self._status_lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: 600; background: transparent;")
        status_row.addWidget(self._status_lbl)
        status_row.addStretch()

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 800; background: transparent;")
        status_row.addWidget(self._pct_lbl)
        layout.addLayout(status_row)

        layout.addSpacing(8)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setStyleSheet("""
            QProgressBar {
                background-color: #0F172A;
                border-radius: 3px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #06B6D4,
                    stop:0.5 #E11D48,
                    stop:1 #FB7185
                );
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._bar)

        outer.addWidget(self._card)

    def _center(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2 + geo.x()
            y = (geo.height() - self.height()) // 2 + geo.y()
            self.move(x, y)

    def set_status(self, text: str, progress: int = -1):
        prefix_map = {
            "Initializing": "[SYSTEM CORE]",
            "Connecting":   "[DATABASE]",
            "Loading":      "[INTERFACE]",
            "Waiting":      "[SYNC]",
            "Building":     "[COMPONENTS]",
            "Ready":        "[ONLINE]"
        }
        matched_prefix = "[KERNEL]"
        for key, prefix in prefix_map.items():
            if key.lower() in text.lower():
                matched_prefix = prefix
                break

        formatted_text = f"{matched_prefix} {text}"
        self._status_lbl.setText(formatted_text)

        if progress >= 0:
            self._bar.setValue(progress)
            self._pct_lbl.setText(f"{progress}%")
        QApplication.processEvents()

    def finish(self, main_window):
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutQuad)

        def _on_finish():
            self.close()
            main_window.showFullScreen()
            main_window.raise_()
            main_window.activateWindow()

        anim.finished.connect(_on_finish)
        anim.start()
