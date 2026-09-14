"""
Every text field, spinbox, and date/time field starts read-only. A single
click removes read-only and lets the user actually type/change the value;
losing focus puts it back to read-only. This uses the real Qt `readOnly`
property directly (QLineEdit.setReadOnly / QTextEdit.setReadOnly /
QAbstractSpinBox.setReadOnly, which QDateTimeEdit/QDateEdit/QTimeEdit inherit)
- not an intercepted/simulated event - so it is guaranteed to take effect.

Some fields (e.g. settings_page.py's SMTP host/actor display fields,
confirm_booking_dialog.py's locked amount field) are set read-only by the
app itself, PERMANENTLY, for reasons unrelated to this guard (permissions,
display-only values). The first time we ever see a widget (its first Show
event), we check whether it's ALREADY read-only at that point - if so, the
app set it intentionally before the widget was ever shown, and we leave it
alone forever. Only widgets that started out editable get the click-to-unlock
treatment.

QComboBox has no equivalent read-only concept in Qt (a combobox IS its
dropdown - there is nothing to "read only" about clicking it open, and
disabling it outright would block that click entirely). The only real
complaint that applies to comboboxes is the mouse wheel silently changing the
selected option while merely hovering/scrolling past it - that is blocked
here too, gated on focus, without touching its normal click-to-open behavior.

Applied as a single QApplication-wide event filter so it covers every
instance of these widgets everywhere in the app - current and future, in
every module and every "multi add" modal - without touching per-module code.
"""
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox, QComboBox, QLineEdit, QTextEdit, QPlainTextEdit,
    QAbstractScrollArea, QApplication,
)

_READONLY_TYPES = (QAbstractSpinBox, QLineEdit, QTextEdit, QPlainTextEdit)
_ALL_GUARDED_TYPES = _READONLY_TYPES + (QComboBox,)

_MANAGED_ATTR = "_input_guard_managed"
_PERMANENT_ATTR = "_input_guard_permanent_readonly"


class InputActivationGuard(QObject):
    def eventFilter(self, obj, event):
        if not isinstance(obj, _ALL_GUARDED_TYPES):
            return False

        et = event.type()

        if isinstance(obj, _READONLY_TYPES):
            if et == QEvent.Show and not getattr(obj, _MANAGED_ATTR, False):
                # First time we've seen this widget - decide once whether the
                # app already made it permanently read-only before this.
                permanent = obj.isReadOnly()
                setattr(obj, _PERMANENT_ATTR, permanent)
                setattr(obj, _MANAGED_ATTR, True)
                if not permanent and not obj.hasFocus():
                    obj.setReadOnly(True)
            elif not getattr(obj, _PERMANENT_ATTR, False):
                if et == QEvent.FocusIn:
                    obj.setReadOnly(False)
                elif et == QEvent.FocusOut:
                    obj.setReadOnly(True)
                elif et == QEvent.MouseButtonPress and obj.isReadOnly():
                    obj.setReadOnly(False)

        elif isinstance(obj, QComboBox) and not obj.hasFocus():
            if et == QEvent.Wheel:
                parent = obj.parentWidget()
                while parent is not None:
                    if isinstance(parent, QAbstractScrollArea):
                        QApplication.sendEvent(parent.viewport(), event)
                        break
                    parent = parent.parentWidget()
                return True
            if et == QEvent.MouseButtonPress:
                obj.setFocus(Qt.MouseFocusReason)

        return False


_guard = None


def install_input_activation_guard(app):
    """Call once, right after creating the QApplication."""
    global _guard
    if _guard is None:
        _guard = InputActivationGuard(app)
        app.installEventFilter(_guard)
    return _guard
