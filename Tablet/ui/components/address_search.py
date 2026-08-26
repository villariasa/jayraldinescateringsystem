"""
Built-in Touch-Optimized Address Dropdown & Search Widget for Tablet App.
Allows searching and selecting from standard Cebu & Philippine address hierarchy
with automatic street number input.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer, Signal

import utils.repository as repo
from ui import theme


class AddressSearchWidget(QWidget):
    address_selected = Signal(dict)
    address_cleared  = Signal()

    _DROPDOWN_MAX_H = 240

    def __init__(self, placeholder: str = "Search Barangay, City, or Province...", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._placeholder = placeholder
        self._selected: Optional[dict] = None
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)
        self._build_ui()
        QTimer.singleShot(100, lambda: repo.get_all_cebu_addresses())

    def get_selection(self) -> Optional[dict]:
        return self._selected

    def get_street(self) -> str:
        return self._street.text().strip()

    def get_full_address(self) -> str:
        street = self.get_street()
        if self._selected and self._selected.get("display_text"):
            return f"{street}, {self._selected['display_text']}" if street else self._selected["display_text"]
        return self._search.text().strip()

    def set_value(self, display_text: str, street: str = "") -> None:
        self._search.blockSignals(True)
        self._search.setText(display_text)
        self._search.blockSignals(False)
        self._street.setText(street)
        if display_text:
            self._street_row.setMaximumHeight(80)
            self._clear_btn.setVisible(True)
        else:
            self._street_row.setMaximumHeight(0)
            self._clear_btn.setVisible(False)
        self._close_dropdown()

    def clear(self) -> None:
        self._search.clear()
        self._street.clear()
        self._selected = None
        self._street_row.setMaximumHeight(0)
        self._clear_btn.setVisible(False)
        self._close_dropdown()
        self.address_cleared.emit()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        search_wrap = QWidget()
        search_wrap.setFixedHeight(46)
        search_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_row = QHBoxLayout(search_wrap)
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText(self._placeholder)
        self._search.setMinimumHeight(46)
        self._search.textChanged.connect(self._on_text_changed)

        self._clear_btn = QLabel("X")
        self._clear_btn.setFixedSize(30, 46)
        self._clear_btn.setAlignment(Qt.AlignCenter)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet("color: #94A3B8; font-weight: bold; font-size: 14px;")
        self._clear_btn.setVisible(False)
        self._clear_btn.mousePressEvent = lambda _e: self.clear()

        search_row.addWidget(self._search, 1)
        search_row.addWidget(self._clear_btn)
        root.addWidget(search_wrap)

        # Dropdown list
        self._dropdown = QListWidget()
        self._dropdown.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._dropdown.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._dropdown.setStyleSheet("""
            QListWidget {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #334155;
            }
            QListWidget::item:selected {
                background: #D97706;
                color: #FFFFFF;
            }
        """)
        self._dropdown.setSelectionMode(QAbstractItemView.SingleSelection)
        self._dropdown.setFocusPolicy(Qt.NoFocus)
        self._dropdown.setMaximumHeight(0)
        self._dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._dropdown.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self._dropdown)

        # Optional Street row
        self._street_row = QWidget()
        street_lay = QVBoxLayout(self._street_row)
        street_lay.setContentsMargins(0, 4, 0, 0)
        street_lay.setSpacing(2)

        lbl = QLabel("Street / House No. / Building (Optional)")
        lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8;")
        self._street = QLineEdit()
        self._street.setPlaceholderText("e.g. Unit 402, Acacia St.")
        self._street.setMinimumHeight(44)

        street_lay.addWidget(lbl)
        street_lay.addWidget(self._street)
        self._street_row.setMaximumHeight(0)
        root.addWidget(self._street_row)

    def _on_text_changed(self, text: str):
        self._clear_btn.setVisible(bool(text))
        if self._selected and self._selected.get("display_text") != text:
            self._selected = None
            self._street_row.setMaximumHeight(0)
        self._debounce.start(120)

    def _run_search(self):
        query = self._search.text().strip()
        if len(query) < 1:
            self._close_dropdown()
            return

        results = repo.search_cebu_address(query, limit=8)
        if not results:
            self._close_dropdown()
            return

        self._dropdown.clear()
        for r in results:
            item = QListWidgetItem(r["display_text"])
            item.setData(Qt.UserRole, r)
            self._dropdown.addItem(item)

        h = min(len(results) * 44 + 8, self._DROPDOWN_MAX_H)
        self._dropdown.setMaximumHeight(h)

    def _on_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if not data:
            return
        self._selected = data
        self._search.blockSignals(True)
        self._search.setText(data["display_text"])
        self._search.blockSignals(False)
        self._close_dropdown()
        self._street_row.setMaximumHeight(80)
        self._clear_btn.setVisible(True)
        self.address_selected.emit(data)

    def _close_dropdown(self):
        self._dropdown.setMaximumHeight(0)
        self._dropdown.clear()
