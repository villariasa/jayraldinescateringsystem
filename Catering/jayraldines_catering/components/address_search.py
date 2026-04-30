from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QListWidget, QListWidgetItem, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtGui import QColor

import utils.repository as repo


class AddressSearchWidget(QWidget):
    """
    Google Maps-style single-input address search for Cebu.

    Signals
    -------
    address_selected(dict)
        Emitted when the user picks a suggestion.
        Dict keys: barangay_id, barangay, city_id, city, province_id,
                   province, display_text
    address_cleared()
        Emitted when the selection is cleared / the widget is reset.
    """

    address_selected = Signal(dict)
    address_cleared  = Signal()

    _DROPDOWN_MAX_H = 260

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected: Optional[dict] = None
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)

        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_selection(self) -> Optional[dict]:
        """Return the currently selected address dict or None."""
        return self._selected

    def get_street(self) -> str:
        return self._street.text().strip()

    def set_value(self, display_text: str, street: str = "",
                  data: Optional[dict] = None) -> None:
        """Pre-fill the widget (e.g. when editing an existing customer)."""
        self._search.blockSignals(True)
        self._search.setText(display_text)
        self._search.blockSignals(False)
        self._street.setText(street)
        self._selected = data
        self._street_row.setVisible(bool(display_text))
        self._clear_btn.setVisible(bool(display_text))
        self._hide_dropdown()

    def clear(self) -> None:
        self._search.clear()
        self._street.clear()
        self._selected = None
        self._street_row.setVisible(False)
        self._clear_btn.setVisible(False)
        self._hide_dropdown()
        self.address_cleared.emit()

    def is_valid(self) -> bool:
        """Return True if a suggestion has been selected and street is not empty."""
        return self._selected is not None and bool(self.get_street())

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # --- search row ---
        search_row = QHBoxLayout()
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
        self._clear_btn.setStyleSheet(
            "color:#6B7280; font-size:12px; background:transparent;"
        )
        self._clear_btn.setVisible(False)
        self._clear_btn.mousePressEvent = lambda _e: self.clear()

        search_row.addWidget(self._search)
        search_row.addWidget(self._clear_btn)
        root.addLayout(search_row)

        # --- dropdown (hidden by default) ---
        self._dropdown = QListWidget()
        self._dropdown.setObjectName("addressDropdown")
        self._dropdown.setFixedWidth(self._search.width())
        self._dropdown.setMaximumHeight(self._DROPDOWN_MAX_H)
        self._dropdown.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._dropdown.setStyleSheet(self._dropdown_style())
        self._dropdown.itemClicked.connect(self._on_item_clicked)
        self._dropdown.setVisible(False)
        root.addWidget(self._dropdown)

        # --- street input (hidden until selection) ---
        self._street_row = QWidget()
        street_lay = QVBoxLayout(self._street_row)
        street_lay.setContentsMargins(0, 0, 0, 0)
        street_lay.setSpacing(4)

        lbl = QLabel("Street / House No. *")
        lbl.setStyleSheet("color:#9CA3AF; font-size:12px;")
        self._street = QLineEdit()
        self._street.setPlaceholderText("e.g. Block 5 Lot 3, Rizal St.")
        self._street.setFixedHeight(38)

        street_lay.addWidget(lbl)
        street_lay.addWidget(self._street)
        self._street_row.setVisible(False)
        root.addWidget(self._street_row)

        # --- hint label ---
        self._hint = QLabel("Start typing to search (min 2 characters)")
        self._hint.setStyleSheet("color:#6B7280; font-size:11px;")
        self._hint.setVisible(False)
        root.addWidget(self._hint)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str):
        if self._selected:
            self._selected = None
            self._street_row.setVisible(False)
            self._clear_btn.setVisible(False)
            self.address_cleared.emit()

        if len(text.strip()) < 2:
            self._hide_dropdown()
            self._hint.setVisible(len(text.strip()) == 1)
            return

        self._hint.setVisible(False)
        self._debounce.start(300)

    def _run_search(self):
        query = self._search.text().strip()
        if len(query) < 2:
            self._hide_dropdown()
            return

        results = repo.search_cebu_address(query, limit=10)

        self._dropdown.clear()

        if not results:
            item = QListWidgetItem("  No results found")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            item.setForeground(QColor("#6B7280"))
            self._dropdown.addItem(item)
        else:
            for row in results:
                display = row.get("display_text") or (
                    f"{row.get('barangay','')}, "
                    f"{row.get('city','')}, "
                    f"{row.get('province','')}"
                )
                item = QListWidgetItem()
                item.setText(display)
                item.setData(Qt.UserRole, row)
                self._dropdown.addItem(item)

        row_h = 36
        count = self._dropdown.count()
        h = min(count * row_h + 8, self._DROPDOWN_MAX_H)
        self._dropdown.setFixedHeight(h)
        self._dropdown.setVisible(True)

    def _on_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if not data:
            return
        self._selected = data
        self._search.blockSignals(True)
        self._search.setText(item.text())
        self._search.blockSignals(False)
        self._clear_btn.setVisible(True)
        self._hide_dropdown()
        self._street_row.setVisible(True)
        self._street.setFocus()
        self.address_selected.emit(data)

    def _hide_dropdown(self):
        self._dropdown.setVisible(False)
        self._dropdown.clear()

    # ------------------------------------------------------------------
    # Event filter — close dropdown when focus leaves the search field
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._search and event.type() == QEvent.FocusOut:
            QTimer.singleShot(150, self._hide_dropdown)
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    @staticmethod
    def _dropdown_style() -> str:
        return """
            QListWidget#addressDropdown {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 4px 0;
                color: #F9FAFB;
                font-size: 13px;
            }
            QListWidget#addressDropdown::item {
                padding: 8px 14px;
                border-radius: 6px;
            }
            QListWidget#addressDropdown::item:hover {
                background-color: #374151;
                color: #F9FAFB;
            }
            QListWidget#addressDropdown::item:selected {
                background-color: #E11D48;
                color: #FFFFFF;
            }
        """
