import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QBrush
from utils.paths import resource_path


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 300)

        self._build_ui()
        self._center()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QWidget(self)
        self._card.setObjectName("splashCard")
        self._card.setStyleSheet("""
            QWidget#splashCard {
                background-color: #111827;
                border-radius: 18px;
                border: 1px solid #1F2937;
            }
        """)
        self._card.setFixedSize(480, 300)

        layout = QVBoxLayout(self._card)
        layout.setContentsMargins(40, 40, 40, 32)
        layout.setSpacing(0)

        logo_row = QWidget()
        logo_row.setStyleSheet("background: transparent;")
        logo_row_lay = QVBoxLayout(logo_row)
        logo_row_lay.setContentsMargins(0, 0, 0, 0)
        logo_row_lay.setSpacing(6)
        logo_row_lay.setAlignment(Qt.AlignCenter)

        logo_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_path):
            logo_lbl = QLabel()
            logo_lbl.setStyleSheet("background: transparent;")
            px = QPixmap(logo_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(px)
            logo_lbl.setAlignment(Qt.AlignCenter)
            logo_row_lay.addWidget(logo_lbl)

        name_lbl = QLabel("Jayraldine's Catering")
        name_lbl.setStyleSheet("background: transparent; color: #F9FAFB; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;")
        name_lbl.setAlignment(Qt.AlignCenter)
        logo_row_lay.addWidget(name_lbl)

        sub_lbl = QLabel("Management System")
        sub_lbl.setStyleSheet("background: transparent; color: #9CA3AF; font-size: 13px; font-weight: 500;")
        sub_lbl.setAlignment(Qt.AlignCenter)
        logo_row_lay.addWidget(sub_lbl)

        layout.addWidget(logo_row)
        layout.addStretch()

        self._status_lbl = QLabel("Starting up...")
        self._status_lbl.setStyleSheet("background: transparent; color: #6B7280; font-size: 12px;")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status_lbl)

        layout.addSpacing(10)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("""
            QProgressBar {
                background-color: #1F2937;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #E11D48;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self._bar)

        layout.addSpacing(12)

        ver_lbl = QLabel("v1.0")
        ver_lbl.setStyleSheet("background: transparent; color: #374151; font-size: 11px;")
        ver_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver_lbl)

        outer.addWidget(self._card)

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    def set_status(self, text: str, progress: int):
        self._status_lbl.setText(text)
        self._bar.setValue(progress)
        QApplication.processEvents()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 18, 18)
        super().paintEvent(event)
