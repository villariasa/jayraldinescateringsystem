"""
Adds a clickable "show/hide password" eye icon inside a QLineEdit, using
Qt's built-in inline line-edit action slot (QLineEdit.addAction) rather than
a separate button widget - so it drops into any existing password field with
one line, no layout changes needed at the call site.
"""
from PySide6.QtCore import QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLineEdit

from utils.icons import get_icon


def add_show_password_toggle(line_edit: QLineEdit) -> QAction:
    """Call on any QLineEdit already set to EchoMode.Password. Adds a
    trailing eye icon the user can click to reveal/hide the typed text."""
    line_edit.setEchoMode(QLineEdit.Password)
    action = QAction(get_icon("eye", color="#94A3B8", size=QSize(16, 16)), "Show password", line_edit)
    action.setCheckable(True)

    def _toggle(checked: bool):
        line_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        action.setToolTip("Hide password" if checked else "Show password")

    action.toggled.connect(_toggle)
    line_edit.addAction(action, QLineEdit.TrailingPosition)
    return action
