from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QListWidget, QListWidgetItem, QSizePolicy, QAbstractItemView,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from utils.theme import ThemeManager


class CustomerSearchWidget(QWidget):
    customer_selected = Signal(dict)
    customer_cleared  = Signal()

    _DROPDOWN_MAX_H = 240

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected: Optional[dict] = None
        self._all_customers: list[dict] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_customers(self, customers: list[dict]) -> None:
        self._all_customers = customers or []

    def get_selection(self) -> Optional[dict]:
        return self._selected

    def set_customer(self, customer: dict) -> None:
        """Pre-select a customer (e.g. edit mode)."""
        self._selected = customer
        self._search.blockSignals(True)
        self._search.setText(customer.get("name", ""))
        self._search.blockSignals(False)
        self._clear_btn.setVisible(True)
        self._close_dropdown()

    def clear(self) -> None:
        self._search.clear()
        self._selected = None
        self._clear_btn.setVisible(False)
        self._close_dropdown()
        self.customer_cleared.emit()

    def set_error(self) -> None:
        self._search.setStyleSheet(
            "border: 1px solid #EF4444; border-radius: 8px;"
        )

    def clear_error(self) -> None:
        self._search.setStyleSheet("")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        search_wrap = QWidget()
        search_wrap.setFixedHeight(44)
        search_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row = QHBoxLayout(search_wrap)
        row.setContentsMargins(0, 3, 0, 3)
        row.setSpacing(6)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search customer name…")
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

        row.addWidget(self._search)
        row.addWidget(self._clear_btn)
        root.addWidget(search_wrap)

        self._dropdown = QListWidget()
        self._dropdown.setObjectName("customerDropdown")
        self._dropdown.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._dropdown.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._dropdown.setStyleSheet(self._style())
        self._dropdown.setSelectionMode(QAbstractItemView.SingleSelection)
        self._dropdown.setFocusPolicy(Qt.NoFocus)
        self._dropdown.setMaximumHeight(0)
        self._dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._dropdown.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self._dropdown)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _open_dropdown(self, count: int):
        self._dropdown.setStyleSheet(self._style())
        h = min(count * 44 + 8, self._DROPDOWN_MAX_H)
        self._dropdown.setMaximumHeight(h)

    def _close_dropdown(self):
        self._dropdown.setMaximumHeight(0)
        self._dropdown.clear()

    def _on_text_changed(self, text: str):
        if self._selected:
            self._selected = None
            self._clear_btn.setVisible(False)
            self.customer_cleared.emit()

        q = text.strip().lower()
        if not q:
            self._close_dropdown()
            return

        matches = [c for c in self._all_customers if q in c.get("name", "").lower()]

        self._dropdown.clear()
        if not matches:
            item = QListWidgetItem("  No customers found")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            item.setForeground(QColor("#6B7280"))
            self._dropdown.addItem(item)
            self._open_dropdown(1)
        else:
            for c in matches:
                name = c.get("name", "")
                contact = c.get("contact", "")
                item = QListWidgetItem()
                item.setData(Qt.UserRole, c)
                label = f"{name}"
                if contact:
                    label += f"  ·  {contact}"
                item.setText(label)
                self._dropdown.addItem(item)
            self._open_dropdown(len(matches))

    def _on_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if not data:
            return
        self._selected = data
        self._search.blockSignals(True)
        self._search.setText(data.get("name", ""))
        self._search.blockSignals(False)
        self._clear_btn.setVisible(True)
        self._close_dropdown()
        self.customer_selected.emit(data)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._search and event.type() == QEvent.FocusOut:
            QTimer.singleShot(200, self._on_focus_lost)
        return super().eventFilter(obj, event)

    def _on_focus_lost(self):
        fw = QApplication.focusWidget()
        if fw is self._search or fw is self._dropdown:
            return
        self._close_dropdown()

    def hideEvent(self, event):
        self._close_dropdown()
        super().hideEvent(event)

    @staticmethod
    def _style() -> str:
        is_light = not ThemeManager().is_dark()
        if is_light:
            bg      = "#FFFFFF"
            border  = "#E2E8F0"
            text    = "#0F172A"
            hover   = "#F1F5F9"
        else:
            bg      = "#1F2937"
            border  = "#374151"
            text    = "#F9FAFB"
            hover   = "#374151"
        return f"""
            QListWidget#customerDropdown {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px 0;
                color: {text};
                font-size: 13px;
            }}
            QListWidget#customerDropdown::item {{
                padding: 10px 14px;
                border-radius: 6px;
                color: {text};
            }}
            QListWidget#customerDropdown::item:hover {{
                background-color: {hover};
                color: {text};
            }}
            QListWidget#customerDropdown::item:selected {{
                background-color: #E11D48;
                color: #FFFFFF;
            }}
        """
