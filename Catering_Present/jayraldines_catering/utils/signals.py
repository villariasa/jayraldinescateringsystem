from PySide6.QtCore import QObject, Signal, QCoreApplication


class _AppEvents(QObject):
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


_instance: _AppEvents | None = None


def app_events() -> _AppEvents:
    global _instance
    if _instance is None:
        _instance = _AppEvents()
        app = QCoreApplication.instance()
        if app is not None and hasattr(app, "thread"):
            try:
                _instance.moveToThread(app.thread())
            except Exception:
                pass
    return _instance
