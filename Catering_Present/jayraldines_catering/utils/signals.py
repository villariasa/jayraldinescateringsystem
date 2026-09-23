"""Application-wide event bus built on Qt signals.

_AppEvents is a single shared QObject whose signals let decoupled parts of the
app broadcast domain events (bookings, invoices, payments, sync, etc.) without
holding direct references to each other. Access the shared instance through
app_events(); emit a signal to notify, connect a slot to react.
"""
from PySide6.QtCore import QObject, Signal, QCoreApplication


class _AppEvents(QObject):
    """Container of app-wide Qt signals used as a global publish/subscribe bus."""
    booking_saved     = Signal()
    booking_created   = Signal()
    booking_updated   = Signal()
    invoice_saved     = Signal()
    invoice_created   = Signal()
    payment_recorded  = Signal()
    kitchen_updated   = Signal()
    customer_saved    = Signal()
    menu_saved        = Signal()
    expense_saved     = Signal()
    cash_flow_saved   = Signal()
    data_changed      = Signal()
    notification_push = Signal()
    alarm_fired       = Signal(dict)
    sync_started      = Signal(str)
    sync_completed    = Signal()


# Lazily-created singleton holding the shared event bus.
_instance: _AppEvents | None = None


def app_events() -> _AppEvents:
    """Return the shared _AppEvents bus, creating it on first use."""
    global _instance
    if _instance is None:
        _instance = _AppEvents()
        # Pin the bus to the main (GUI) thread so its queued signal deliveries
        # run there, regardless of which thread first called this.
        app = QCoreApplication.instance()
        if app is not None and hasattr(app, "thread"):
            try:
                _instance.moveToThread(app.thread())
            except Exception:
                pass  # thread affinity is best-effort; ignore if it fails
    return _instance
