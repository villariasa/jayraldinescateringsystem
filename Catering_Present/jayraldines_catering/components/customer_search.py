"""Customer search widget backed by a native QCompleter popup.

Lets the user type a customer's name or contact and pick from an autocompleting
list of previously loaded customers. If the typed text matches no one, the
widget still yields a "new customer" payload so callers can create records
inline. Emits ``customer_selected``/``customer_cleared`` for parent forms.
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QLabel,
    QCompleter, QSizePolicy, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QStringListModel, QModelIndex
from utils.theme import ThemeManager


class CustomerSearchWidget(QWidget):
    """Autocomplete search box for selecting (or inventing) a customer.

    Signals:
        customer_selected(dict): a known/typed customer was chosen.
        customer_cleared(): the field was emptied.
    """

    customer_selected = Signal(dict)
    customer_cleared  = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected: Optional[dict] = None
        self._all_customers: list[dict] = []
        # Lookup indexes built in load_customers() for O(1) exact matching:
        #   label -> customer ("Name  ·  Contact"), and lowercased name -> customer.
        self._customers_by_label: dict[str, dict] = {}
        self._customers_by_name: dict[str, dict] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_customers(self, customers: list[dict]) -> None:
        """Load the customer list and (re)build the completer + lookup indexes."""
        self._all_customers = customers or []
        self._customers_by_label = {}
        self._customers_by_name = {}
        labels = []
        for c in self._all_customers:
            name = c.get("name", "").strip()
            contact = c.get("contact", "").strip()
            # Label combines name and contact so duplicate names stay distinguishable.
            lbl = f"{name}  ·  {contact}" if contact else name
            labels.append(lbl)
            self._customers_by_label[lbl] = c
            self._customers_by_name[name.lower()] = c

        # Feed the assembled labels to the completer's model as its suggestion set.
        model = QStringListModel(labels, self._completer)
        self._completer.setModel(model)

    def get_selection(self) -> Optional[dict]:
        """Return the chosen customer, or a fresh payload for a typed-in name.

        Returns None only when the field is empty; a non-matching entry yields a
        new-customer dict so the caller can create the record.
        """
        if self._selected:
            return self._selected
        txt = self._search.text().strip()
        if txt:
            # 1. Check exact match
            c = self._find_matching_customer(txt)
            if c:
                self._selected = c
                return c
            # 2. Return new customer payload if custom name entered
            return {"name": txt, "contact": "", "email": "", "address": "", "status": "Active"}
        return None

    def set_customer(self, customer: dict) -> None:
        """Programmatically select a customer and reflect it in the field."""
        self._selected = customer
        # Block signals so setText doesn't re-trigger the change handler.
        self._search.blockSignals(True)
        self._search.setText(customer.get("name", ""))
        self._search.blockSignals(False)
        self._clear_btn.setVisible(True)

    def clear(self) -> None:
        """Empty the field, drop the selection and notify listeners."""
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)
        self._selected = None
        self._clear_btn.setVisible(False)
        self.customer_cleared.emit()

    def set_error(self) -> None:
        """Show a red validation outline on the search box."""
        self._search.setStyleSheet(
            "border: 1px solid #EF4444; border-radius: 8px; padding: 8px 12px;"
        )

    def clear_error(self) -> None:
        """Remove the validation error outline."""
        self._search.setStyleSheet("")

    # ------------------------------------------------------------------
    # UI & Event Handling
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build the search line edit, its QCompleter popup and the clear button."""
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 3, 0, 3)
        row.setSpacing(6)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search customer name or contact…")
        self._search.setFixedHeight(38)
        self._search.textChanged.connect(self._on_text_changed)
        self._search.returnPressed.connect(self._on_enter_or_finish)
        self._search.editingFinished.connect(self._on_enter_or_finish)

        # Native floating QCompleter popup
        self._completer = QCompleter(self._search)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        # MatchContains so typing any substring (e.g. part of a contact number) matches.
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setMaxVisibleItems(7)
        self._completer.activated.connect(self._on_activated)

        popup = self._completer.popup()
        popup.setObjectName("customerCompleterPopup")
        popup.setFocusPolicy(Qt.NoFocus)
        popup.setStyleSheet(self._style())
        self._search.setCompleter(self._completer)

        self._clear_btn = QLabel("✕")
        self._clear_btn.setFixedSize(22, 22)
        self._clear_btn.setAlignment(Qt.AlignCenter)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet("color:#6B7280; font-size:12px; background:transparent;")
        self._clear_btn.setVisible(False)
        # QLabel has no clicked signal, so override mousePressEvent to clear.
        self._clear_btn.mousePressEvent = lambda _e: self.clear()

        row.addWidget(self._search)
        row.addWidget(self._clear_btn)

    def _find_matching_customer(self, text: str) -> Optional[dict]:
        """Resolve free text to a customer via fastest-to-loosest matching.

        Tries an exact label hit, then an exact name hit, then a substring scan
        over name/contact. Returns None if nothing matches.
        """
        clean = text.strip().lower()
        if not clean:
            return None
        # 1. Exact label match (the "Name  ·  Contact" string shown in the popup)
        if text.strip() in self._customers_by_label:
            return self._customers_by_label[text.strip()]
        # 2. Exact name match
        if clean in self._customers_by_name:
            return self._customers_by_name[clean]
        # 3. Search in all customers list (substring fallback for partial input)
        for c in self._all_customers:
            c_name = c.get("name", "").strip().lower()
            c_contact = c.get("contact", "").strip().lower()
            if c_name == clean or clean in c_name or (c_contact and clean in c_contact):
                return c
        return None

    def _on_activated(self, text_or_index):
        """Handle a completer selection (fired when a popup item is chosen)."""
        # activated() may deliver either the QModelIndex or the string depending
        # on the overload Qt picks; normalize both to the display text.
        if isinstance(text_or_index, QModelIndex):
            text = text_or_index.data() or ""
        else:
            text = str(text_or_index)

        c = self._find_matching_customer(text)
        if c:
            self._selected = c
            # Collapse the label back to just the name in the field, without re-triggering handlers.
            self._search.blockSignals(True)
            self._search.setText(c.get("name", ""))
            self._search.blockSignals(False)
            self._clear_btn.setVisible(True)
            self.customer_selected.emit(c)

    def _on_text_changed(self, text: str):
        """Track typing: match against known customers or drop a stale selection."""
        clean = text.strip()
        if not clean:
            self._selected = None
            self._clear_btn.setVisible(False)
            self.customer_cleared.emit()
            return

        self._clear_btn.setVisible(True)
        # Check if typed text matches a known customer
        c = self._find_matching_customer(clean)
        if c:
            self._selected = c
            self.customer_selected.emit(c)
        # If the user edited away from the selected customer's name, drop the selection.
        elif self._selected and clean.lower() != self._selected.get("name", "").strip().lower():
            self._selected = None

    def _on_enter_or_finish(self):
        """On Enter/editing-finished, lock in a match if the text resolves to one."""
        clean = self._search.text().strip()
        if clean:
            c = self._find_matching_customer(clean)
            if c:
                self._selected = c
                self._search.blockSignals(True)
                self._search.setText(c.get("name", ""))
                self._search.blockSignals(False)
                self._clear_btn.setVisible(True)
                self.customer_selected.emit(c)

    @staticmethod
    def _style() -> str:
        """Return the completer popup QSS for the active theme."""
        is_light = not ThemeManager().is_dark()
        if is_light:
            bg      = "#FFFFFF"
            border  = "#D8DFEA"
            text    = "#101828"
            hover   = "#F3F5F9"
        else:
            bg      = "#1F2937"
            border  = "#374151"
            text    = "#F9FAFB"
            hover   = "#374151"
        return f"""
            QListView#customerCompleterPopup {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px;
                color: {text};
                font-size: 13px;
                outline: 0;
            }}
            QListView#customerCompleterPopup::item {{
                padding: 8px 12px;
                border-radius: 6px;
                min-height: 20px;
            }}
            QListView#customerCompleterPopup::item:hover,
            QListView#customerCompleterPopup::item:selected {{
                background-color: {hover};
                color: {text};
            }}
        """
