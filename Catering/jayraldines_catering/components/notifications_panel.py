from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import get_icon


_NOTIFICATIONS = [
    {
        "type":    "warning",
        "title":   "Payment Pending",
        "message": "Invoice #BKG-002 (Smith Wedding) requires a 50% downpayment of ₱60,000.",
        "time":    "1 hour ago",
        "color":   "#F59E0B",
    },
    {
        "type":    "success",
        "title":   "Booking Confirmed",
        "message": "TechCorp Inc. booking for Oct 24 has been confirmed. 150 pax.",
        "time":    "3 hours ago",
        "color":   "#22C55E",
    },
    {
        "type":    "info",
        "title":   "New Booking Request",
        "message": "Cruz Corporate submitted an event inquiry for Apr 30, 2026.",
        "time":    "5 hours ago",
        "color":   "#3B82F6",
    },
]


class NotificationsPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notifications")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(400)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        container.setStyleSheet("")

        shadow = QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        container.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(20, 20, 20, 20)
        c_lay.setSpacing(0)

        header = QHBoxLayout()
        title = QLabel("Notifications")
        title.setObjectName("h3")
        header.addWidget(title)

        badge = QLabel(str(len(_NOTIFICATIONS)))
        badge.setObjectName("notifBadge")
        badge.setFixedSize(20, 20)
        badge.setAlignment(Qt.AlignCenter)
        header.addWidget(badge)
        header.addStretch()

        mark_btn = QPushButton("Mark all read")
        mark_btn.setObjectName("ghostButton")
        mark_btn.setCursor(Qt.PointingHandCursor)
        mark_btn.clicked.connect(self.accept)
        header.addWidget(mark_btn)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        c_lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        c_lay.addSpacing(12)
        c_lay.addWidget(div)
        c_lay.addSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setMaximumHeight(420)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")  # keep transparent so card bg shows through
        inner_lay = QVBoxLayout(inner)
        inner_lay.setSpacing(0)
        inner_lay.setContentsMargins(0, 0, 0, 0)

        for notif in _NOTIFICATIONS:
            item = self._build_item(notif)
            inner_lay.addWidget(item)
            sep = QFrame()
            sep.setObjectName("divider")
            inner_lay.addWidget(sep)

        inner_lay.addStretch()
        scroll.setWidget(inner)
        c_lay.addWidget(scroll)

        outer.addWidget(container)

    def _build_item(self, notif):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 12, 0, 12)
        lay.setSpacing(14)

        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(
            f"background: {notif['color']}; border-radius: 5px; min-width: 10px; max-width: 10px;"
        )
        lay.addWidget(dot, alignment=Qt.AlignTop)
        lay.setAlignment(dot, Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        title_lbl = QLabel(notif["title"])
        title_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #F9FAFB;")

        msg_lbl = QLabel(notif["message"])
        msg_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        msg_lbl.setWordWrap(True)

        time_lbl = QLabel(notif["time"])
        time_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")

        text_col.addWidget(title_lbl)
        text_col.addWidget(msg_lbl)
        text_col.addWidget(time_lbl)

        lay.addLayout(text_col)
        return w
