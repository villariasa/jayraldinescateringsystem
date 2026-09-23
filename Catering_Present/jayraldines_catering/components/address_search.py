"""Cebu address search widget with an inline autocomplete dropdown.

Provides a debounced type-ahead search over cached Cebu barangay/city addresses
(via ``utils.repository``), an inline results dropdown, and a follow-up
street/house-number field that appears only once an address is picked. Emits
``address_selected``/``address_cleared`` so parent forms can react.
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QAbstractItemView,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor

import utils.repository as repo


class AddressSearchWidget(QWidget):
    """Type-ahead Cebu address picker with an inline dropdown and street field.

    Signals:
        address_selected(dict): emitted with the chosen address row.
        address_cleared(): emitted when the selection is reset.
    """

    address_selected = Signal(dict)
    address_cleared  = Signal()

    # Hard cap on dropdown height so long result lists scroll instead of growing.
    _DROPDOWN_MAX_H = 260

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected: Optional[dict] = None
        # Single-shot timer used to debounce keystrokes before hitting search.
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)
        self._build_ui()
        # Warm up the in-memory address cache in background
        # (first search then hits a primed cache instead of loading synchronously).
        QTimer.singleShot(50, lambda: repo.get_all_cebu_addresses())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_selection(self) -> Optional[dict]:
        """Return the currently selected address dict, or None."""
        return self._selected

    def get_street(self) -> str:
        """Return the trimmed street/house-number text."""
        return self._street.text().strip()

    def set_value(self, display_text: str, street: str = "",
                  data: Optional[dict] = None) -> None:
        """Populate the widget programmatically (e.g. when editing a record)."""
        # Block signals so setting the text doesn't trigger the search/clear logic.
        self._search.blockSignals(True)
        self._search.setText(display_text)
        self._search.blockSignals(False)
        self._street.setText(street)
        self._selected = data
        if display_text:
            self._show_widget(self._street_row, 80)
        else:
            self._hide_widget(self._street_row)
        self._clear_btn.setVisible(bool(display_text))
        self._close_dropdown()

    def clear(self) -> None:
        """Reset all inputs and selection back to the empty state."""
        self._search.clear()
        self._street.clear()
        self._selected = None
        self._hide_widget(self._street_row)
        self._clear_btn.setVisible(False)
        self._close_dropdown()
        self.address_cleared.emit()

    def is_valid(self) -> bool:
        """True only when an address is selected AND a street was entered."""
        return self._selected is not None and bool(self.get_street())

    def highlight_street_error(self) -> None:
        """Outline the street field in red and focus it (validation feedback)."""
        self._street.setStyleSheet(
            "border: 1px solid #E11D48; border-radius: 6px; background: rgba(225,29,72,0.05);"
        )
        self._street.setFocus()

    def _clear_street_error(self) -> None:
        """Remove the error outline once the user edits the street field."""
        self._street.setStyleSheet("")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Lay out the search row, inline dropdown, street field and hint label."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- search row (fixed height so it NEVER moves) ---
        search_wrap = QWidget()
        search_wrap.setFixedHeight(44)
        search_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_row = QHBoxLayout(search_wrap)
        search_row.setContentsMargins(0, 3, 0, 3)
        search_row.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Type barangay or city in Cebu…")
        self._search.setFixedHeight(38)
        self._search.textChanged.connect(self._on_text_changed)
        self._search.installEventFilter(self)

        self._clear_btn = QLabel("✕")
        self._clear_btn.setFixedSize(22, 22)
        self._clear_btn.setAlignment(Qt.AlignCenter)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet("color:#6B7280; font-size:12px; background:transparent;")
        self._clear_btn.setVisible(False)
        # QLabel has no clicked signal, so override its mousePressEvent to clear.
        self._clear_btn.mousePressEvent = lambda _e: self.clear()

        search_row.addWidget(self._search)
        search_row.addWidget(self._clear_btn)
        root.addWidget(search_wrap)

        # --- inline dropdown (hidden by default via maxHeight=0) ---
        self._dropdown = QListWidget()
        self._dropdown.setObjectName("addressDropdown")
        self._dropdown.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._dropdown.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._dropdown.setStyleSheet(self._dropdown_style())
        self._dropdown.setSelectionMode(QAbstractItemView.SingleSelection)
        self._dropdown.setFocusPolicy(Qt.NoFocus)
        self._dropdown.setMaximumHeight(0)
        self._dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._dropdown.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self._dropdown)

        # --- street input (hidden until selection) ---
        self._street_row = QWidget()
        street_lay = QVBoxLayout(self._street_row)
        street_lay.setContentsMargins(0, 4, 0, 0)
        street_lay.setSpacing(4)

        lbl = QLabel("Street / House No. *")
        lbl.setObjectName("fieldLabel")
        self._street = QLineEdit()
        self._street.setPlaceholderText("e.g. Block 5 Lot 3, Rizal St.")
        self._street.setFixedHeight(38)
        self._street.textChanged.connect(self._clear_street_error)

        street_lay.addWidget(lbl)
        street_lay.addWidget(self._street)
        self._street_row.setMaximumHeight(0)
        self._street_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self._street_row)

        self._hint = QLabel("Start typing to search (min 2 characters)")
        self._hint.setObjectName("muted")
        self._hint.setStyleSheet("font-size:11px; padding-top:2px;")
        self._hint.setMaximumHeight(0)
        self._hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self._hint)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _show_widget(self, w, max_h: int):
        """Reveal a collapsed widget by lifting its max-height cap."""
        # Rows are hidden by pinning maxHeight to 0; restoring it "expands" them.
        w.setMaximumHeight(max_h)

    def _hide_widget(self, w):
        """Collapse a widget by pinning its max-height to 0."""
        w.setMaximumHeight(0)

    def _open_dropdown(self, count: int):
        """Size and show the results dropdown for ``count`` rows."""
        self._dropdown.setStyleSheet(self._dropdown_style())
        # ~38px per row + a little padding, capped so it scrolls past the max.
        h = min(count * 38 + 10, self._DROPDOWN_MAX_H)
        self._dropdown.setFixedHeight(h)

    def _close_dropdown(self):
        """Collapse and empty the results dropdown."""
        self._dropdown.setFixedHeight(0)
        self._dropdown.clear()

    def _on_text_changed(self, text: str):
        """React to typing: invalidate stale selection and (de)schedule search."""
        # Any edit invalidates a previously chosen address, hiding the street row.
        if self._selected:
            self._selected = None
            self._hide_widget(self._street_row)
            self._clear_btn.setVisible(False)
            self.address_cleared.emit()

        # Require at least 2 chars before searching; show the hint at exactly 1.
        if len(text.strip()) < 2:
            self._close_dropdown()
            if len(text.strip()) == 1:
                self._show_widget(self._hint, 20)
            else:
                self._hide_widget(self._hint)
            return

        self._hide_widget(self._hint)
        # Debounce: restart the 120ms timer on each keystroke so we only query
        # once the user pauses typing.
        self._debounce.start(120)

    def _run_search(self):
        """Query the address cache and populate the dropdown with results."""
        query = self._search.text().strip()
        # Guard again in case the text shrank below the threshold before the timer fired.
        if len(query) < 2:
            self._close_dropdown()
            return

        results = repo.search_cebu_address(query, limit=10)
        self._dropdown.clear()

        if not results:
            # Non-selectable placeholder row when nothing matches.
            item = QListWidgetItem("  No results found")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            item.setForeground(QColor("#6B7280"))
            self._dropdown.addItem(item)
            self._open_dropdown(1)
        else:
            for row in results:
                # Prefer a precomputed display string; otherwise build "barangay, city, province".
                display = row.get("display_text") or (
                    f"{row.get('barangay','')}, "
                    f"{row.get('city','')}, "
                    f"{row.get('province','')}"
                )
                item = QListWidgetItem(display)
                # Stash the full row on the item so selection can recover it.
                item.setData(Qt.UserRole, row)
                self._dropdown.addItem(item)
            self._open_dropdown(len(results))

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle a dropdown pick: store selection and reveal the street field."""
        data = item.data(Qt.UserRole)
        if not data:
            # The "No results" placeholder carries no data — ignore clicks on it.
            return
        self._selected = data
        self._search.blockSignals(True)
        self._search.setText(item.text())
        self._search.blockSignals(False)
        self._clear_btn.setVisible(True)
        self._close_dropdown()
        self._show_widget(self._street_row, 80)
        self._street.setFocus()
        self.address_selected.emit(data)

    # ------------------------------------------------------------------
    # Event filter
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        """Close the dropdown when the search box loses focus (deferred)."""
        from PySide6.QtCore import QEvent
        if obj is self._search and event.type() == QEvent.FocusOut:
            # Delay close so itemClicked can fire first
            # (clicking a result steals focus before the click is processed).
            QTimer.singleShot(200, self._on_search_focus_lost)
        return super().eventFilter(obj, event)

    def _on_search_focus_lost(self):
        """Close the dropdown unless focus is still within the widget."""
        # Don't close if the dropdown itself has focus or is being interacted with
        fw = QApplication.focusWidget()
        if fw is self._search or fw is self._dropdown:
            return
        self._close_dropdown()

    def hideEvent(self, event):
        """Ensure the floating dropdown is dismissed when the widget hides."""
        self._close_dropdown()
        super().hideEvent(event)

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    @staticmethod
    def _dropdown_style() -> str:
        """Return the dropdown QSS, choosing colours for the active theme."""
        from utils.theme import ThemeManager
        if ThemeManager().is_dark():
            bg, border, text, hover = "#1F2937", "#374151", "#F9FAFB", "#374151"
        else:
            bg, border, text, hover = "#FFFFFF", "#D8DFEA", "#101828", "#F3F5F9"
        return f"""
            QListWidget#addressDropdown {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px 0;
                color: {text};
                font-size: 13px;
            }}
            QListWidget#addressDropdown::item {{
                padding: 8px 14px;
                border-radius: 6px;
                color: {text};
            }}
            QListWidget#addressDropdown::item:hover {{
                background-color: {hover};
                color: {text};
            }}
            QListWidget#addressDropdown::item:selected {{
                background-color: #E11D48;
                color: #FFFFFF;
            }}
        """
