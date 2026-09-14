"""
Turns a plain editable QComboBox into a search-as-you-type combobox: typing
filters the dropdown to items that CONTAIN the typed text (not just items
that start with it), case-insensitively, via a QCompleter with popup
completion. Drop-in for any existing editable QComboBox - one call, no
layout/behavior changes needed at the call site beyond that.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter


def make_searchable(combo: QComboBox) -> QCompleter:
    """Call on an already-editable QComboBox to enable contains-match,
    case-insensitive, popup-filtered search as the user types."""
    combo.setEditable(True)
    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    return completer
