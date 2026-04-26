from PySide6.QtCore import QObject, QTimer, Signal
import utils.repository as repo


class NotifScheduler(QObject):
    new_notification = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)
        self._timer.start(30_000)

    def _check(self):
        try:
            candidates = repo.get_event_alert_candidates()
        except Exception:
            return
        fired = False
        for c in candidates:
            ref = c.get("booking_ref", "")
            name = c.get("customer_name", "")
            window = c.get("window_label", "")
            if window == "1_day":
                repo.push_notification(
                    "warning",
                    f"Reminder: {ref} Tomorrow",
                    f"{name}'s event is happening tomorrow. Ensure all preparations are ready.",
                    "#F59E0B",
                )
                fired = True
            elif window == "30_min":
                repo.push_notification(
                    "warning",
                    f"Event in 30 Minutes: {ref}",
                    f"{name}'s event starts in 30 minutes. Last-minute preparations needed.",
                    "#F97316",
                )
                fired = True
            elif window == "1_min":
                repo.push_notification(
                    "danger",
                    f"Event Starting Now: {ref}",
                    f"{name}'s event is starting now. All hands on deck!",
                    "#EF4444",
                )
                fired = True
        if fired:
            self.new_notification.emit()
