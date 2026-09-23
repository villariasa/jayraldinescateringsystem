"""Notifications popover component.

Renders an anchored, frameless popover listing unread notifications pulled from
the database via ``utils.repository``. Notifications are held in a module-level
cache (``_notifications``) so the panel and the header badge can share a single
source of truth, grouped by type (Payments / Orders / System) for display.
Supports dismissing single items and marking everything as read.
"""

from datetime import datetime, timezone
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QApplication
)
from PySide6.QtCore import Qt, QSize, QPoint, QEvent, QTimer, Signal

from utils.icons import get_icon
from utils.theme import ThemeManager
from utils.animations import create_soft_shadow
import utils.repository as repo


def _is_light():
    """Return True when the app is currently in light theme."""
    return not ThemeManager().is_dark()


def _muted(size=11):
    """Inline stylesheet for muted/tertiary text, theme-aware."""
    # Pick a lighter grey for light theme so contrast stays subtle in both modes.
    return "font-size: %dpx; color: %s;" % (size, "#7A879E" if _is_light() else "#6B7280")


def _secondary(size=12):
    """Inline stylesheet for secondary body text, theme-aware."""
    return "font-size: %dpx; color: %s;" % (size, "#46536B" if _is_light() else "#9CA3AF")


# Maps a notification's raw ``type`` to the section header it renders under.
_TYPE_GROUPS = {
    "warning": "Payments",
    "success": "Orders",
    "info":    "System",
    "error":   "System",
}


def _relative_time(created_at) -> str:
    """Format a timestamp as a short relative string ("5m ago", "2h ago").

    Falls back to "just now" on any error or missing value so the UI never
    breaks over a bad/undefined timestamp.
    """
    try:
        if created_at is None:
            return "just now"
        now = datetime.now(timezone.utc)
        # Compare against an aware "now" only when the stamp is tz-aware;
        # otherwise use naive local time to avoid subtracting mixed types.
        if hasattr(created_at, 'tzinfo') and created_at.tzinfo is not None:
            diff = now - created_at
        else:
            diff = datetime.now() - created_at
        secs = int(diff.total_seconds())
        if secs < 60:
            return "just now"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return "just now"


def _load_notifications():
    """Fetch unread notifications from the DB and normalize them to UI dicts.

    Returns an empty list if the query fails or there are no rows, keeping the
    caller resilient to DB/connection errors.
    """
    try:
        db_rows = repo.get_unread_notifications()
    except Exception:
        return []
    if not db_rows:
        return []
    return [{
        "type":       r["type"],
        "title":      r["title"],
        "message":    r["message"],
        "time":       _relative_time(r.get("created_at")),
        "color":      r.get("color") or "#9CA3AF",
        "db_id":      r["id"],
    } for r in db_rows]


# Shared in-memory cache of unread notifications; the header badge and the
# popover both read from this so they stay in sync without re-querying.
_notifications: list = []


def reload_notifications() -> int:
    """Refresh the shared cache from the DB and return the unread count.

    Mutates the existing list in place (clear + extend) rather than rebinding
    so other references to ``_notifications`` keep pointing at live data.
    """
    global _notifications
    fresh = _load_notifications()
    _notifications.clear()
    _notifications.extend(fresh)
    return len(_notifications)


class NotificationPopover(QFrame):
    """Frameless popover that lists unread notifications, anchored to a button.

    Emits ``all_read`` when the user marks everything read so the header badge
    can update. Installs an event filter on its parent to dismiss itself on an
    outside click.
    """

    all_read = Signal()

    def __init__(self, parent=None):
        # SubWindow + FramelessWindowHint gives a borderless floating panel that
        # stays tied to the parent window rather than a separate OS window.
        super().__init__(parent, Qt.SubWindow | Qt.FramelessWindowHint)

        # Transparent background so the inner rounded "card" (with shadow) shows
        # through instead of a hard rectangular frame.
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setObjectName("card")
        self.setFixedWidth(380)

        self._build_ui()
        self.hide()

        # ===== FIX 1: safe event filter install =====
        # Defer installing the outside-click filter to the next event loop tick
        # so the parent is fully constructed/valid before we attach to it.
        if parent is not None:
            QTimer.singleShot(0, lambda: parent.installEventFilter(self))

    def _build_ui(self):
        """Construct the popover: header (title, badge, actions) + scroll list."""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Inner card carries the visible background + drop shadow; the outer
        # frame is transparent (see __init__), so margins here create the shadow gap.
        inner = QFrame()
        inner.setObjectName("card")
        create_soft_shadow(inner, radius=28, y_offset=8, opacity=45)
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
        # Hide on the next tick rather than synchronously inside the click
        # handler, avoiding re-entrancy issues while the click is still dispatching.
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
        self._scroll.setMinimumHeight(200)
        self._scroll.setMaximumHeight(480)

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
        """Rebuild the notification list from the shared cache and update badge."""
        # Tear down existing rows first so repeated refreshes don't stack widgets.
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
            # Bucket notifications by their display section (Payments/Orders/System).
            grouped = {}
            for n in _notifications:
                g = _TYPE_GROUPS.get(n["type"], "System")
                grouped.setdefault(g, []).append(n)

            for group_name, items in grouped.items():
                grp_lbl = QLabel(group_name.upper())
                grp_lbl.setStyleSheet(
                    _muted(10) + " font-weight: 700; letter-spacing: 1px; padding: 10px 0 4px 0;"
                )
                self._list_lay.addWidget(grp_lbl)

                for notif in items:
                    self._list_lay.addWidget(self._build_item(notif))
                    sep = QFrame()
                    sep.setObjectName("divider")
                    self._list_lay.addWidget(sep)

        self._list_lay.addStretch()
        # Keep the count badge in sync and hide it entirely when at zero.
        self._badge.setText(str(len(_notifications)))
        self._badge.setVisible(len(_notifications) > 0)
        self.adjustSize()

    def _build_item(self, notif):
        """Build a single notification row: colour dot, text column, dismiss X."""
        w = QWidget()
        w.setMinimumHeight(72)
        w.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 12, 0, 12)
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
        msg_lbl.setMinimumHeight(18)
        msg_lbl.setStyleSheet(_secondary(12))
        time_lbl = QLabel(notif["time"])
        time_lbl.setObjectName("muted")
        time_lbl.setStyleSheet(_muted(11))

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
        # Bind the current notif into the lambda default so each button dismisses its own row.
        dismiss_btn.clicked.connect(lambda _, n=notif: self._dismiss(n))
        lay.addWidget(dismiss_btn)

        return w

    def _dismiss(self, notif):
        """Remove a single notification from the cache and DB, then refresh."""
        if notif in _notifications:
            _notifications.remove(notif)
        # Only persist to the DB when the row originated there (has a db_id).
        if notif.get("db_id"):
            repo.dismiss_notification(notif["db_id"])
        self._refresh_list()

    def _mark_all_read(self):
        """Clear all notifications locally + in the DB and notify listeners."""
        _notifications.clear()
        repo.mark_all_notifications_read()
        self._refresh_list()
        self.all_read.emit()

    def show_anchored(self, anchor_btn):
        """Position the popover under/left of ``anchor_btn`` and show it."""
        self._refresh_list()
        # Anchor to the button's bottom-right, then shift left by our own width so
        # the popover's right edge aligns with the button (right-aligned dropdown).
        btn_br = anchor_btn.mapToGlobal(QPoint(anchor_btn.width(), anchor_btn.height() + 6))
        x = btn_br.x() - self.width()
        # Clamp within the screen's available area so it never renders off-screen.
        screen = QApplication.screenAt(btn_br) or QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            x = max(sg.left() + 4, min(x, sg.right() - self.width() - 4))
        self.move(x, btn_br.y())
        self.raise_()
        self.show()

    def toggle_anchored(self, anchor_btn):
        """Show the popover if hidden, hide it if already visible."""
        if self.isVisible():
            self.hide()
        else:
            self.show_anchored(anchor_btn)

    def keyPressEvent(self, event):
        """Close the popover on Escape."""
        if event.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Dismiss the popover when the user clicks anywhere outside it."""
        # Guard against non-widget events whose type() isn't callable as expected.
        if not hasattr(event, 'type') or not callable(event.type):
            return False
        if event.type() == QEvent.MouseButtonPress and self.isVisible():
            # globalPosition() is the Qt6 API; fall back to globalPos() defensively.
            pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            local = self.mapFromGlobal(pos)
            if not self.rect().contains(local):
                self.hide()
        # Return False so the click still reaches its original target (don't consume it).
        return False