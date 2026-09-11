"""
utils/notif_scheduler.py
------------------------
Periodic checker that fires toast notifications for upcoming events.
All DB calls run in a background QThread so the main UI thread is never blocked.
"""
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, QTimer, Signal
from utils.data_loader import DataLoader


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
        self._loader = None
        self._busy = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_async)
        self._timer.start(60_000)
        # Delay initial check by 15 s so the app finishes loading first
        QTimer.singleShot(15_000, self._check_async)

    def _check_async(self):
        """Start a background fetch \u2014 never call repo directly from the main thread."""
        if self._busy:
            return
        if self._loader is not None and self._loader.isRunning():
            return
        self._busy = True

        def _bg():
            import utils.repository as repo
            try:
                return repo.get_upcoming_bookings_for_alerts()
            except Exception:
                return []

        loader = DataLoader(_bg)
        loader.data_ready.connect(self._on_data)
        loader.load_error.connect(lambda _: self._done())
        self._loader = loader
        loader.start()

    def _on_data(self, bookings):
        """Process results on the main thread \u2014 no DB calls here."""
        try:
            import utils.repository as repo

            if not bookings:
                return

            now = datetime.now()

            to_push = []
            for b in bookings:
                event_dt = b.get("event_dt")
                if not event_dt:
                    continue
                ref  = b.get("booking_ref", "")
                name = b.get("customer_name", "")
                delta = event_dt - now
                total_secs = delta.total_seconds()

                for win_key, win_from, win_tol, ntype, title_tpl, msg_tpl, color in _WINDOWS:
                    fire_key = f"{ref}:{win_key}"
                    if fire_key in _fired:
                        continue
                    low  = (win_from - win_tol).total_seconds()
                    high = (win_from + win_tol).total_seconds()
                    if low <= total_secs <= high:
                        title = title_tpl.format(ref=ref, name=name)
                        msg   = msg_tpl.format(ref=ref, name=name)
                        _fired.add(fire_key)
                        to_push.append((ntype, title, msg, color))

            # Push DB writes in a background thread too
            if to_push:
                def _push_all():
                    import utils.repository as repo
                    for ntype, title, msg, color in to_push:
                        try:
                            repo.push_notification(ntype, title, msg, color)
                        except Exception:
                            pass
                    return to_push

                push_loader = DataLoader(_push_all)
                push_loader.data_ready.connect(
                    lambda items: [self.new_notification.emit(t, m, c) for _, t, m, c in items]
                )
                push_loader.start()
        finally:
            self._done()

    def _done(self):
        self._busy = False
