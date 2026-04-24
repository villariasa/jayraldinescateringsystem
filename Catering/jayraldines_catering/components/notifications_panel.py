from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import get_icon


_DEFAULT_NOTIFICATIONS = [
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

_notifications = list(_DEFAULT_NOTIFICATIONS)


class NotificationsPanel(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notifications")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(400)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        self._container = QFrame()
        self._container.setObjectName("card")
        self._container.setStyleSheet("")

        self._c_lay = QVBoxLayout(self._container)
        self._c_lay.setContentsMargins(20, 20, 20, 20)
        self._c_lay.setSpacing(0)

        self._build_header()
        self._build_list()

        outer.addWidget(self._container)

    def _build_header(self):
        header = QHBoxLayout()
        title = QLabel("Notifications")
        title.setObjectName("h3")
        header.addWidget(title)

        self._badge = QLabel(str(len(_notifications)))
        self._badge.setObjectName("notifBadge")
        self._badge.setFixedSize(20, 20)
        self._badge.setAlignment(Qt.AlignCenter)
        header.addWidget(self._badge)
        header.addStretch()

        mark_btn = QPushButton("Mark all read")
        mark_btn.setObjectName("ghostButton")
        mark_btn.setCursor(Qt.PointingHandCursor)
        mark_btn.clicked.connect(self._mark_all_read)
        header.addWidget(mark_btn)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        self._c_lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        self._c_lay.addSpacing(12)
        self._c_lay.addWidget(div)
        self._c_lay.addSpacing(8)

    def _build_list(self):
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setMaximumHeight(420)

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setSpacing(0)
        self._inner_lay.setContentsMargins(0, 0, 0, 0)

        self._refresh_list()

        self._scroll.setWidget(self._inner)
        self._c_lay.addWidget(self._scroll)

    def _refresh_list(self):
        while self._inner_lay.count():
            item = self._inner_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not _notifications:
            empty = QLabel("No new notifications.")
            empty.setStyleSheet("color: #6B7280; font-size: 13px; padding: 20px;")
            empty.setAlignment(Qt.AlignCenter)
            self._inner_lay.addWidget(empty)
        else:
            for notif in list(_notifications):
                item = self._build_item(notif)
                self._inner_lay.addWidget(item)
                sep = QFrame()
                sep.setObjectName("divider")
                self._inner_lay.addWidget(sep)

        self._inner_lay.addStretch()
        self._badge.setText(str(len(_notifications)))

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
        lay.addWidget(dot, alignment=Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        title_lbl = QLabel(notif["title"])
        title_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        msg_lbl = QLabel(notif["message"])
        msg_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        msg_lbl.setWordWrap(True)
        time_lbl = QLabel(notif["time"])
        time_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")
        text_col.addWidget(title_lbl)
        text_col.addWidget(msg_lbl)
        text_col.addWidget(time_lbl)
        lay.addLayout(text_col, 1)

        dismiss_btn = QPushButton()
        dismiss_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(12, 12)))
        dismiss_btn.setIconSize(QSize(12, 12))
        dismiss_btn.setFixedSize(22, 22)
        dismiss_btn.setStyleSheet("background: transparent; border: none;")
        dismiss_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn.setToolTip("Dismiss")
        dismiss_btn.clicked.connect(lambda _, n=notif: self._dismiss(n))
        lay.addWidget(dismiss_btn, alignment=Qt.AlignVCenter)

        return w

    def _dismiss(self, notif):
        if notif in _notifications:
            _notifications.remove(notif)
        self._refresh_list()

    def _mark_all_read(self):
        _notifications.clear()
        self._refresh_list()
