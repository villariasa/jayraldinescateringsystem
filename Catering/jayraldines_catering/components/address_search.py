from __future__ import annotations
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QAbstractItemView,
)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QRect
from PySide6.QtGui import QColor, QMouseEvent

import utils.repository as repo


class _DropdownPopup(QListWidget):
    """Floating frameless popup positioned via global screen coords."""

    def __init__(self, on_pick: Callable[[QListWidgetItem], None]):
        super().__init__(None)
        self._on_pick = on_pick
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName("addressDropdown")
        self.setStyleSheet(_DROPDOWN_STYLE)
        self.hide()

    def show_below(self, anchor: QWidget, max_h: int):
        count = self.count()
        h = min(count * 36 + 8, max_h)
        gp = anchor.mapToGlobal(QPoint(0, anchor.height() + 2))
        self.setGeometry(QRect(gp.x(), gp.y(), anchor.width(), h))
        self.show()
        self.raise_()

    def mousePressEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if item and (item.flags() & Qt.ItemIsEnabled):
            self._on_pick(item)
        else:
            super().mousePressEvent(event)


class AddressSearchWidget(QWidget):
    address_selected = Signal(dict)
    address_cleared  = Signal()

    _DROPDOWN_MAX_H = 260

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected: Optional[dict] = None
        self._closing = False
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_selection(self) -> Optional[dict]:
        return self._selected

    def get_street(self) -> str:
        return self._street.text().strip()

    def set_value(self, display_text: str, street: str = "",
                  data: Optional[dict] = None) -> None:
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
        self._search.clear()
        self._street.clear()
        self._selected = None
        self._hide_widget(self._street_row)
        self._clear_btn.setVisible(False)
        self._close_dropdown()
        self.address_cleared.emit()

    def is_valid(self) -> bool:
        return self._selected is not None and bool(self.get_street())

    def highlight_street_error(self) -> None:
        self._street.setStyleSheet(
            "border: 1px solid #E11D48; border-radius: 6px; background: rgba(225,29,72,0.05);"
        )
        self._street.setFocus()

    def _clear_street_error(self) -> None:
        self._street.setStyleSheet("")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # --- search row ---
        self._search_container = QWidget()
        search_row = QHBoxLayout(self._search_container)
        search_row.setContentsMargins(0, 0, 0, 0)
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
        self._clear_btn.mousePressEvent = lambda _e: self.clear()

        search_row.addWidget(self._search)
        search_row.addWidget(self._clear_btn)
        root.addWidget(self._search_container)

        # --- floating dropdown ---
        self._dropdown = _DropdownPopup(on_pick=self._on_item_picked)

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
        self._street.textChanged.connect(self._clear_street_error)

        street_lay.addWidget(lbl)
        street_lay.addWidget(self._street)
        self._street_row.setMaximumHeight(0)
        self._street_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self._street_row)

        self._hint = QLabel("Start typing to search (min 2 characters)")
        self._hint.setStyleSheet("color:#6B7280; font-size:11px;")
        self._hint.setMaximumHeight(0)
        self._hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self._hint)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _show_widget(self, w, max_h: int):
        w.setMaximumHeight(max_h)

    def _hide_widget(self, w):
        w.setMaximumHeight(0)

    def _open_dropdown(self):
        self._dropdown.show_below(self._search_container, self._DROPDOWN_MAX_H)

    def _close_dropdown(self):
        self._dropdown.hide()
        self._dropdown.clear()

    def _on_text_changed(self, text: str):
        if self._selected:
            self._selected = None
            self._hide_widget(self._street_row)
            self._clear_btn.setVisible(False)
            self.address_cleared.emit()

        if len(text.strip()) < 2:
            self._close_dropdown()
            if len(text.strip()) == 1:
                self._show_widget(self._hint, 20)
            else:
                self._hide_widget(self._hint)
            return

        self._hide_widget(self._hint)
        self._debounce.start(300)

    def _run_search(self):
        query = self._search.text().strip()
        if len(query) < 2:
            self._close_dropdown()
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
                item = QListWidgetItem(display)
                item.setData(Qt.UserRole, row)
                self._dropdown.addItem(item)

        self._open_dropdown()

    def _on_item_picked(self, item: QListWidgetItem):
        """Called directly from popup mousePressEvent — no timing issues."""
        data = item.data(Qt.UserRole)
        if not data:
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
    # Event filter — close dropdown on focus-out (only if not clicking popup)
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._search and event.type() == QEvent.FocusOut:
            # Only close if focus did NOT go to our popup
            QTimer.singleShot(50, self._maybe_close)
        return super().eventFilter(obj, event)

    def _maybe_close(self):
        from PySide6.QtWidgets import QApplication
        focused = QApplication.focusWidget()
        if focused is not self._dropdown and focused is not self._search:
            self._close_dropdown()

    def hideEvent(self, event):
        self._close_dropdown()
        super().hideEvent(event)


_DROPDOWN_STYLE = """
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
