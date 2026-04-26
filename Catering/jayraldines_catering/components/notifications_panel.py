from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QApplication
)
from PySide6.QtCore import Qt, QSize, QPoint, QEvent, QTimer, Signal
from PySide6.QtGui import QColor

from utils.icons import get_icon
import utils.repository as repo


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

_TYPE_GROUPS = {
    "warning": "Payments",
    "success": "Orders",
    "info":    "System",
    "danger":  "System",
}


def _load_notifications():
    db_rows = repo.get_unread_notifications()
    if db_rows:
        return [{
            "type":    r["type"],
            "title":   r["title"],
            "message": r["message"],
            "time":    "just now",
            "color":   r.get("color", "#9CA3AF"),
            "db_id":   r["id"],
        } for r in db_rows]
    return []


_notifications = _load_notifications()


def reload_notifications() -> int:
    global _notifications
    fresh = _load_notifications()
    _notifications.clear()
    _notifications.extend(fresh)
    return len(_notifications)


class NotificationPopover(QFrame):
    all_read = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setObjectName("card")
        self.setFixedWidth(380)

        self._build_ui()
        self.hide()

        # ===== FIX 1: safe event filter install =====
        if parent is not None:
            QTimer.singleShot(0, lambda: parent.installEventFilter(self))

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        inner = QFrame()
        inner.setObjectName("card")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(20, 18, 20, 18)
        inner_lay.setSpacing(0)

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
        mark_btn.setFixedHeight(28)
        mark_btn.setCursor(Qt.PointingHandCursor)
        mark_btn.clicked.connect(self._mark_all_read)
        header.addWidget(mark_btn)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(13, 13)))
        close_btn.setIconSize(QSize(13, 13))
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)

        # ===== FIX 2: safe hide call =====
        close_btn.clicked.connect(lambda: QTimer.singleShot(0, self.hide))

        header.addWidget(close_btn)
        inner_lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        inner_lay.addSpacing(10)
        inner_lay.addWidget(div)
        inner_lay.addSpacing(4)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setMaximumHeight(400)

        self._inner_w = QWidget()
        self._inner_w.setStyleSheet("background: transparent;")
        self._list_lay = QVBoxLayout(self._inner_w)
        self._list_lay.setSpacing(0)
        self._list_lay.setContentsMargins(0, 0, 0, 0)

        self._scroll.setWidget(self._inner_w)
        inner_lay.addWidget(self._scroll)

        lay.addWidget(inner)
        self._refresh_list()

    def _refresh_list(self):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not _notifications:
            empty = QLabel("You're all caught up!")
            empty.setObjectName("subtitle")
            empty.setAlignment(Qt.AlignCenter)
            empty.setContentsMargins(0, 20, 0, 20)
            self._list_lay.addWidget(empty)
        else:
            grouped = {}
            for n in _notifications:
                g = _TYPE_GROUPS.get(n["type"], "System")
                grouped.setdefault(g, []).append(n)

            for group_name, items in grouped.items():
                grp_lbl = QLabel(group_name.upper())
                grp_lbl.setStyleSheet(
                    "color: #6B7280; font-size: 10px; font-weight: 700;"
                    " letter-spacing: 1px; padding: 10px 0 4px 0;"
                )
                self._list_lay.addWidget(grp_lbl)

                for notif in items:
                    self._list_lay.addWidget(self._build_item(notif))
                    sep = QFrame()
                    sep.setObjectName("divider")
                    self._list_lay.addWidget(sep)

        self._list_lay.addStretch()
        self._badge.setText(str(len(_notifications)))
        self._badge.setVisible(len(_notifications) > 0)
        self.adjustSize()

    def _build_item(self, notif):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(12)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {notif['color']}; border-radius: 4px;")
        lay.addWidget(dot, alignment=Qt.AlignTop | Qt.AlignHCenter)

        text_col = QVBoxLayout()
        title_lbl = QLabel(notif["title"])
        title_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        msg_lbl = QLabel(notif["message"])
        msg_lbl.setObjectName("subtitle")
        msg_lbl.setWordWrap(True)
        time_lbl = QLabel(notif["time"])
        time_lbl.setObjectName("muted")

        text_col.addWidget(title_lbl)
        text_col.addWidget(msg_lbl)
        text_col.addWidget(time_lbl)
        lay.addLayout(text_col, 1)

        dismiss_btn = QPushButton()
        dismiss_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(11, 11)))
        dismiss_btn.setIconSize(QSize(11, 11))
        dismiss_btn.setFixedSize(20, 20)
        dismiss_btn.setStyleSheet("background: transparent; border: none;")
        dismiss_btn.setCursor(Qt.PointingHandCursor)
        dismiss_btn.clicked.connect(lambda _, n=notif: self._dismiss(n))
        lay.addWidget(dismiss_btn)

        return w

    def _dismiss(self, notif):
        if notif in _notifications:
            _notifications.remove(notif)
        if notif.get("db_id"):
            repo.dismiss_notification(notif["db_id"])
        self._refresh_list()

    def _mark_all_read(self):
        _notifications.clear()
        repo.mark_all_notifications_read()
        self._refresh_list()
        self.all_read.emit()

    def show_anchored(self, anchor_btn):
        global_pos = anchor_btn.mapToGlobal(QPoint(0, anchor_btn.height() + 6))
        parent = self.parent()

        if parent:
            local = parent.mapFromGlobal(global_pos)
            x = min(local.x(), parent.width() - self.width() - 8)
            self.move(x, local.y())
        else:
            self.move(global_pos)

        self.raise_()
        self.show()

    def toggle_anchored(self, anchor_btn):
        if self.isVisible():
            self.hide()
        else:
            self.show_anchored(anchor_btn)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and self.isVisible():
            pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            local = self.mapFromGlobal(pos)
            if not self.rect().contains(local):
                self.hide()
        return False