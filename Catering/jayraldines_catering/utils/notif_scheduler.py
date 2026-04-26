from datetime import datetime, timedelta
from PySide6.QtCore import QObject, QTimer, Signal
import utils.repository as repo


_WINDOWS = [
    ("1_day",  timedelta(hours=24),  timedelta(hours=1),   "warning", "Reminder: {ref} Tomorrow",
     "{name}'s event is happening tomorrow. Ensure all preparations are ready.", "#F59E0B"),
    ("30_min", timedelta(minutes=30), timedelta(minutes=2), "warning", "Event in 30 Minutes: {ref}",
     "{name}'s event starts in 30 minutes. Last-minute preparations needed.", "#F97316"),
    ("1_min",  timedelta(minutes=0),  timedelta(minutes=5), "error",   "Event Starting Now: {ref}",
     "{name}'s event is starting now. All hands on deck!", "#EF4444"),
]

_fired: set = set()


class NotifScheduler(QObject):
    new_notification = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)
        self._timer.start(30_000)
        QTimer.singleShot(2_000, self._check)

    def _check(self):
        try:
            bookings = repo.get_upcoming_bookings_for_alerts()
        except Exception as exc:
            print(f"[Scheduler] fetch failed: {exc}")
            return

        now = datetime.now()

        for b in bookings:
            event_dt = b.get("event_dt")
            if not event_dt:
                continue
            ref  = b.get("booking_ref", "")
            name = b.get("customer_name", "")
            delta = event_dt - now

            for win_key, win_from, win_tol, ntype, title_tpl, msg_tpl, color in _WINDOWS:
                fire_key = f"{ref}:{win_key}"
                if fire_key in _fired:
                    continue
                if win_from - win_tol <= delta <= win_from + win_tol:
                    title = title_tpl.format(ref=ref, name=name)
                    msg   = msg_tpl.format(ref=ref, name=name)
                    _fired.add(fire_key)
                    try:
                        repo.push_notification(ntype, title, msg, color)
                    except Exception:
                        pass
                    self.new_notification.emit(title, msg, color)
