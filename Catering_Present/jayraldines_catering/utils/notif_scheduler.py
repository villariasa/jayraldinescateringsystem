from datetime import datetime, timedelta
from PySide6.QtCore import QObject, QTimer, Signal
import utils.repository as repo


_WINDOWS = [
    ("1_day",  timedelta(hours=24),   timedelta(hours=1),    "warning",
     "Reminder: {ref} Tomorrow",
     "{name}'s event is happening tomorrow. Ensure all preparations are ready.",
     "#F59E0B"),
    ("30_min", timedelta(minutes=30), timedelta(minutes=4),  "warning",
     "Event in 30 Minutes: {ref}",
     "{name}'s event starts in 30 minutes. Last-minute preparations needed.",
     "#F97316"),
    ("now",    timedelta(minutes=0),  timedelta(minutes=10), "error",
     "Event Starting Now: {ref}",
     "{name}'s event is starting now. All hands on deck!",
     "#EF4444"),
]

_fired: set = set()


class NotifScheduler(QObject):
    new_notification = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)
        self._timer.start(60_000)
        QTimer.singleShot(5_000, self._check)

    def _check(self):
        try:
            bookings = repo.get_upcoming_bookings_for_alerts()
        except Exception as exc:
            print(f"[Scheduler] fetch error: {exc}")
            return

        if not bookings:
            return

        now = datetime.now()
        print(f"[Scheduler] checking {len(bookings)} booking(s) at {now.strftime('%H:%M:%S')}")

        for b in bookings:
            event_dt = b.get("event_dt")
            if not event_dt:
                continue
            ref    = b.get("booking_ref", "")
            name   = b.get("customer_name", "")
            delta  = event_dt - now
            total_secs = delta.total_seconds()
            print(f"[Scheduler]   {ref} ({name}) — event in {total_secs/60:.1f} min")

            for win_key, win_from, win_tol, ntype, title_tpl, msg_tpl, color in _WINDOWS:
                fire_key = f"{ref}:{win_key}"
                if fire_key in _fired:
                    continue
                low  = (win_from - win_tol).total_seconds()
                high = (win_from + win_tol).total_seconds()
                if low <= total_secs <= high:
                    title = title_tpl.format(ref=ref, name=name)
                    msg   = msg_tpl.format(ref=ref, name=name)
                    print(f"[Scheduler] >>> FIRING {win_key} for {ref}")
                    _fired.add(fire_key)
                    try:
                        repo.push_notification(ntype, title, msg, color)
                    except Exception as exc:
                        print(f"[Scheduler] push_notification failed: {exc}")
                    self.new_notification.emit(title, msg, color)
