from PySide6.QtCore import QObject, Signal


class _AppEvents(QObject):
    booking_saved     = Signal()
    payment_recorded  = Signal()
    kitchen_updated   = Signal()
    customer_saved    = Signal()
    menu_saved        = Signal()
    notification_push = Signal()


_instance: _AppEvents | None = None


def app_events() -> _AppEvents:
    global _instance
    if _instance is None:
        _instance = _AppEvents()
    return _instance
