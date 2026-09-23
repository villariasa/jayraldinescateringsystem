"""
Customers page for the Jayraldines catering desktop app.

This module renders the "Customers" screen plus the modal dialogs used to
create, edit, bulk-add, and inspect customers. It is built on PySide6 (Qt for
Python). Key pieces:

  - AddCustomerDialog / EditCustomerDialog: single-customer forms with a
        country-code + auto-formatted phone field and a Cebu address search.
  - AddMultipleCustomersDialog: a spreadsheet-style grid for bulk entry.
  - CustomerLedgerDialog: read-only accounting view (charges, payments, balance).
  - CustomersPage: the main list screen with search, an Active/Show-All filter,
        batch selection/delete, and an incremental (batched, lazily paginated)
        card renderer designed to keep the Qt UI thread responsive.

Persistence and business logic live in ``utils.repository`` (aliased ``repo``);
this module is the UI layer only. Several performance/correctness concerns are
handled here and documented inline: reload coalescing, render generation tokens,
lazy pagination with an optional in-memory cache, and permission-aware cards.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QSizePolicy, QTextEdit, QScrollArea,
    QCheckBox, QMessageBox, QCompleter
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor
from components.address_search import AddressSearchWidget
from components.loading_overlay import LoadingOverlay
from utils.data_loader import run_async


def _format_phone_input(text: str) -> str:
    """Normalize free-form phone input into a grouped 10-digit local number.

    Strips all non-digits, caps at 10 digits, and inserts spaces as
    ``XXX XXX XXXX`` (partial groupings for shorter input).

    Args:
        text: Raw phone text (may contain spaces, dashes, letters, etc.).

    Returns:
        The digits regrouped with spaces, e.g. ``"917 555 1234"``.
    """
    digits = "".join(c for c in text if c.isdigit())[:10]
    # Progressive grouping so the field reads sensibly while still being typed.
    if len(digits) <= 3:
        return digits
    elif len(digits) <= 6:
        return f"{digits[:3]} {digits[3:]}"
    elif len(digits) <= 10:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return f"{digits[:3]} {digits[3:6]} {digits[6:10]}"


def _format_contact_preserving_cursor(line_edit: QLineEdit):
    """Reformat a phone QLineEdit in place while keeping the caret sensible.

    Naively calling ``setText`` on every keystroke would jump the caret to the
    end. This reformats via :func:`_format_phone_input` and then repositions the
    caret so it sits after the same *digit* the user was on, not the same raw
    character index (which shifts as spaces are inserted/removed).

    Args:
        line_edit: The contact QLineEdit to reformat; edited in place.

    Side effects: mutates the widget's text and cursor position. Signals are
    blocked during the edit to avoid re-triggering the textChanged handler.
    """
    text = line_edit.text()
    cursor_pos = line_edit.cursorPosition()
    # Count how many digits precede the caret - this is the anchor we preserve.
    digits_before = sum(1 for c in text[:cursor_pos] if c.isdigit())

    formatted = _format_phone_input(text)
    if formatted != text:
        # Block signals so setText doesn't recursively fire textChanged.
        line_edit.blockSignals(True)
        line_edit.setText(formatted)
        # Walk the reformatted string to find the index just past the Nth digit,
        # so the caret lands after the same digit the user had just typed.
        new_pos = 0
        counted_digits = 0
        for i, ch in enumerate(formatted):
            if ch.isdigit():
                counted_digits += 1
            if counted_digits == digits_before:
                new_pos = i + 1
                break
        else:
            # Fewer digits than expected (shouldn't normally happen): go to end.
            new_pos = len(formatted)
        line_edit.setCursorPosition(new_pos)
        line_edit.blockSignals(False)


# Country dial codes offered in the contact combo box, as (dial_code, label)
# pairs. PH (+63) is first so it is the default selection. The label is what the
# user sees; the code is stored as the combo's item data.
_COUNTRY_CODES = [
    ("+63", "PH  +63"),
    ("+1",  "US  +1"),
    ("+44", "UK  +44"),
    ("+61", "AU  +61"),
    ("+81", "JP  +81"),
    ("+82", "KR  +82"),
    ("+86", "CN  +86"),
    ("+91", "IN  +91"),
    ("+65", "SG  +65"),
    ("+60", "MY  +60"),
    ("+62", "ID  +62"),
    ("+66", "TH  +66"),
    ("+84", "VN  +84"),
    ("+971","UAE +971"),
    ("+966","SA  +966"),
    ("+49", "DE  +49"),
    ("+33", "FR  +33"),
    ("+39", "IT  +39"),
    ("+34", "ES  +34"),
    ("+7",  "RU  +7"),
    ("+55", "BR  +55"),
    ("+52", "MX  +52"),
    ("+27", "ZA  +27"),
    ("+234","NG  +234"),
    ("+20", "EG  +20"),
]

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from utils.theme import ThemeManager
from utils.text_highlight import highlight_html
from components.dialogs import confirm, success
import utils.repository as repo



class AddCustomerDialog(QDialog):
    """Modal form for creating a single new customer.

    Captures name, contact (country code + auto-formatted number), email,
    status, and a Cebu address via :class:`AddressSearchWidget`. The validated
    payload is exposed through :meth:`get_result`; the caller performs the DB
    insert.
    """

    def __init__(self, parent=None):
        """Set up the frameless modal window and build the form.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Add Customer")
        # Frameless + translucent: the styled "card" QFrame supplies the chrome.
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 580)
        self.setModal(True)
        self._result = None  # Populated by _save() on a valid submit.
        self._build_ui()

    def _build_ui(self):
        """Build the header, form fields, address widget, and action buttons.

        Side effects: stores the input widgets (name/contact/email/status,
        country code combo, address widget, error label) as instance attributes.
        """
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")

        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Add Customer")
        title.setObjectName("h3")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        lay.addWidget(div)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Full name / Company name")
        self.name_field.setFixedHeight(38)

        contact_row = QHBoxLayout()
        contact_row.setSpacing(6)
        self.country_code_combo = QComboBox()
        self.country_code_combo.setFixedHeight(38)
        self.country_code_combo.setFixedWidth(110)
        # Store the dial code as item data (2nd arg) while showing the label.
        for code, label in _COUNTRY_CODES:
            self.country_code_combo.addItem(label, code)
        self.country_code_combo.setCurrentIndex(0)  # Default to PH (+63).
        self.contact_field = QLineEdit()
        self.contact_field.setPlaceholderText("9XX XXX XXXX")
        self.contact_field.setFixedHeight(38)
        # Live-format the number as the user types (see _auto_format_contact).
        self.contact_field.textChanged.connect(self._auto_format_contact)
        contact_row.addWidget(self.country_code_combo)
        contact_row.addWidget(self.contact_field)
        contact_widget = QWidget()
        contact_widget.setLayout(contact_row)

        self.email_field = QLineEdit()
        self.email_field.setPlaceholderText("email@example.com")
        self.email_field.setFixedHeight(38)

        self.address_widget = AddressSearchWidget()

        self.status_field = QComboBox()
        self.status_field.setFixedHeight(38)
        self.status_field.addItems(["Active", "Pending", "Inactive"])

        for lbl, widget in [
            ("Name *",    self.name_field),
            ("Contact *", contact_widget),
            ("Email",     self.email_field),
            ("Status",    self.status_field),
        ]:
            form.addRow(QLabel(lbl), widget)

        lay.addLayout(form)

        addr_lbl = QLabel("Address (Cebu)")
        addr_lbl.setStyleSheet("color:#9CA3AF; font-size:12px; font-weight:600;")
        lay.addWidget(addr_lbl)
        lay.addWidget(self.address_widget)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #E11D48; font-size: 12px;")
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        save = QPushButton("  Save Customer")
        save.setObjectName("primaryButton")
        save.setIcon(btn_icon_primary("check"))
        save.setIconSize(QSize(15, 15))
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

        outer.addWidget(container)

    def _save(self):
        """Validate the form, assemble ``self._result``, and accept on success.

        Name and contact number are required. If an address was picked from the
        search widget, a street/house number is also required. On any validation
        failure the error label is shown and the dialog stays open. The final
        contact string is the selected dial code prefixed to the local number.
        """
        name   = self.name_field.text().strip()
        number = self.contact_field.text().strip()
        if not name or not number:
            # Required-field guard for name/contact; red-border the offenders.
            self._err.setText("Name and Contact are required.")
            self._err.show()
            if not name:
                self.name_field.setStyleSheet("border: 1px solid #E11D48;")
            if not number:
                self.contact_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        code    = self.country_code_combo.currentData()
        contact = f"{code} {number}"  # e.g. "+63 917 555 1234"
        sel    = self.address_widget.get_selection()
        street = self.address_widget.get_street()
        if sel and not street:
            # A barangay/city was chosen but the specific street is missing.
            self._err.setText("Street / House No. is required after selecting an address.")
            self._err.show()
            self.address_widget.highlight_street_error()
            return
        if sel:
            # Compose a human-readable address; strip trailing separators in case
            # any component is blank.
            addr_str = f"{street}, {sel['barangay']}, {sel['city']}, Cebu".strip(", ")
        else:
            # No structured selection: store whatever free-text street was typed.
            addr_str = street
        self._result = {
            "name":         name,
            "contact":      contact,
            "email":        self.email_field.text().strip(),
            "address":      addr_str,
            "address_data": sel,      # Structured ids for save_address(); may be None.
            "street":       street,
            "events":       0,        # New customers start with zero events.
            "status":       self.status_field.currentText(),
        }
        self.accept()

    def _auto_format_contact(self, _text):
        """textChanged handler: reformat the contact field, preserving the caret."""
        _format_contact_preserving_cursor(self.contact_field)

    def get_result(self):
        """Return the collected customer dict, or None if cancelled/invalid."""
        return self._result


class EditCustomerDialog(QDialog):
    """Modal form for editing an existing customer.

    Pre-fills every field from the passed ``customer`` dict, including splitting
    the stored contact string back into a country code + local number and
    preselecting the matching status. Emits the updated payload via
    :meth:`get_result`.
    """

    def __init__(self, parent=None, customer=None):
        """Store the customer being edited and build the pre-filled form.

        Args:
            parent: Optional parent widget.
            customer: The existing customer dict to edit (defaults to empty).
        """
        super().__init__(parent)
        self._customer = customer or {}
        self.setWindowTitle("Edit Customer")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 640)
        self.setModal(True)
        self._result = None
        self._build_ui()

    def _build_ui(self):
        """Build the edit form, pre-populating every field from ``self._customer``.

        Notable logic: the stored contact string is parsed back into a country
        code and local number so the combo and field can be pre-selected; the
        existing address is shown as a read-only "Current:" hint above the
        address search widget.
        """
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Edit Customer")
        title.setObjectName("h3")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        lay.addWidget(div)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_field = QLineEdit(self._customer.get("name", ""))
        self.name_field.setPlaceholderText("Full name / Company name")
        self.name_field.setFixedHeight(38)

        # Split the stored "code number" contact back into its parts so the
        # combo and number field can be pre-filled. Default to +63 if no known
        # dial code prefix is found. The "code + space" case is checked first so
        # a code like "+6" can't greedily match ahead of "+63".
        existing_contact = self._customer.get("contact", "")
        matched_code = "+63"
        number_part = existing_contact
        for code, _label in _COUNTRY_CODES:
            if existing_contact.startswith(code + " "):
                matched_code = code
                number_part = existing_contact[len(code) + 1:]
                break
            elif existing_contact.startswith(code):
                matched_code = code
                number_part = existing_contact[len(code):].lstrip()
                break

        contact_row = QHBoxLayout()
        contact_row.setSpacing(6)
        self.country_code_combo = QComboBox()
        self.country_code_combo.setFixedHeight(38)
        self.country_code_combo.setFixedWidth(110)
        for code, label in _COUNTRY_CODES:
            self.country_code_combo.addItem(label, code)
            # Select the item that matches the parsed dial code as it is added.
            if code == matched_code:
                self.country_code_combo.setCurrentIndex(self.country_code_combo.count() - 1)
        # Re-group the parsed local number for display consistency.
        self.contact_field = QLineEdit(_format_phone_input(number_part))
        self.contact_field.setPlaceholderText("9XX XXX XXXX")
        self.contact_field.setFixedHeight(38)
        self.contact_field.textChanged.connect(self._auto_format_contact)
        contact_row.addWidget(self.country_code_combo)
        contact_row.addWidget(self.contact_field)
        contact_widget = QWidget()
        contact_widget.setLayout(contact_row)

        self.email_field = QLineEdit(self._customer.get("email", ""))
        self.email_field.setPlaceholderText("email@example.com")
        self.email_field.setFixedHeight(38)

        # Remember the current address so we can keep it if the user doesn't pick
        # a new one, and show it as a read-only hint below.
        self._existing_addr = self._customer.get("address", "")
        self.address_widget = AddressSearchWidget()

        self.status_field = QComboBox()
        self.status_field.setFixedHeight(38)
        self.status_field.addItems(["Active", "Pending", "Inactive"])
        # Preselect the customer's existing status if it's one of the options.
        idx = self.status_field.findText(self._customer.get("status", "Active"))
        if idx >= 0:
            self.status_field.setCurrentIndex(idx)

        for lbl, widget in [
            ("Name *",    self.name_field),
            ("Contact *", contact_widget),
            ("Email",     self.email_field),
            ("Status",    self.status_field),
        ]:
            form.addRow(QLabel(lbl), widget)

        lay.addLayout(form)

        addr_lbl = QLabel("Address (Cebu)")
        addr_lbl.setStyleSheet("color:#9CA3AF; font-size:12px; font-weight:600;")
        lay.addWidget(addr_lbl)
        if self._existing_addr:
            self._current_addr_lbl = QLabel(f"Current: {self._existing_addr}")
            self._current_addr_lbl.setStyleSheet("color:#9CA3AF; font-size:13px;")
            self._current_addr_lbl.setWordWrap(True)
            lay.addWidget(self._current_addr_lbl)
        lay.addWidget(self.address_widget)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #E11D48; font-size: 12px;")
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        save = QPushButton("  Save Changes")
        save.setObjectName("primaryButton")
        save.setIcon(btn_icon_primary("check"))
        save.setIconSize(QSize(15, 15))
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

        outer.addWidget(container)

    def _auto_format_contact(self, _text):
        """textChanged handler: reformat the contact field, preserving the caret."""
        _format_contact_preserving_cursor(self.contact_field)

    def _save(self):
        """Validate and assemble the edited payload into ``self._result``.

        Same validation rules as :meth:`AddCustomerDialog._save`. The key
        difference: when no new address is selected, the customer's *existing*
        address is preserved rather than being blanked out.
        """
        name   = self.name_field.text().strip()
        number = self.contact_field.text().strip()
        if not name or not number:
            self._err.setText("Name and Contact are required.")
            self._err.show()
            if not name:
                self.name_field.setStyleSheet("border: 1px solid #E11D48;")
            if not number:
                self.contact_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        code    = self.country_code_combo.currentData()
        contact = f"{code} {number}"
        sel    = self.address_widget.get_selection()
        street = self.address_widget.get_street()
        if sel and not street:
            self._err.setText("Street / House No. is required after selecting an address.")
            self._err.show()
            self.address_widget.highlight_street_error()
            return
        if sel:
            addr_str = f"{street}, {sel['barangay']}, {sel['city']}, Cebu".strip(", ")
        else:
            # No new address chosen: keep the address the customer already had.
            addr_str = self._existing_addr
        self._result = {
            "name":         name,
            "contact":      contact,
            "email":        self.email_field.text().strip(),
            "address":      addr_str,
            "address_data": sel,
            "street":       street,
            "status":       self.status_field.currentText(),
        }
        self.accept()

    def get_result(self):
        """Return the edited customer dict, or None if cancelled/invalid."""
        return self._result


# Per-loyalty-tier colors as (text_color, background_color) used by _tier_badge.
_TIER_COLORS = {
    "Bronze": ("#CD7F32", "rgba(205,127,50,.15)"),
    "Silver": ("#C0C0C0", "rgba(192,192,192,.15)"),
    "Gold":   ("#F59E0B", "rgba(245,158,11,.15)"),
    "VIP":    ("#A855F7", "rgba(168,85,247,.15)"),
}


def _tier_badge(tier: str) -> QLabel:
    """Build a small colored pill label for a loyalty tier.

    Args:
        tier: Tier name (e.g. "Bronze", "Silver", "Gold", "VIP"). Unknown tiers
            fall back to a neutral gray.

    Returns:
        QLabel: A styled, centered badge for the tier.
    """
    color, bg = _TIER_COLORS.get(tier, ("#9CA3AF", "rgba(156,163,175,.15)"))
    lbl = QLabel(tier)
    lbl.setStyleSheet(
        f"font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;"
        f"background:{bg};color:{color};border:1px solid {color};"
    )
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


class CustomerLedgerDialog(QDialog):
    """Read-only accounting/ledger view for a single customer.

    Loads the customer's ledger entries via ``repo.get_customer_ledger`` and
    renders per-entry cards (bookings, invoices, payments) plus summary totals
    (total charged, total paid, balance due). Because the window is frameless,
    it implements manual drag-to-move and Esc-to-close.
    """

    def __init__(self, parent=None, customer=None):
        """Set up the frameless ledger window for ``customer`` and build the UI.

        Args:
            parent: Optional parent widget.
            customer: The customer dict whose ledger is shown (defaults to empty).
        """
        super().__init__(parent)
        self._customer = customer or {}
        self._drag_pos = None  # Offset captured on press for frameless dragging.
        name = str(self._customer.get("name") or "Customer")
        self.setWindowTitle(f"Ledger — {name}")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(780)
        self.setMinimumHeight(480)
        self.setMaximumHeight(720)
        self.setModal(True)
        self._build_ui()

    def mousePressEvent(self, event):
        """Record the cursor-to-window offset so the frameless dialog can be dragged."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Move the frameless window to follow the drag started in mousePressEvent."""
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """End the drag by clearing the stored offset."""
        self._drag_pos = None

    def keyPressEvent(self, event):
        """Close on Escape; defer all other keys to the default handler."""
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def _build_ui(self):
        """Fetch the ledger, compute totals, and render the info/summary/entries.

        Side effects: queries ``repo.get_customer_ledger`` (failures are caught
        and treated as an empty ledger), then builds the header, customer info
        row, summary cards, and a scrollable list of entry cards.
        """
        from utils.icons import get_icon
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("modalCard")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Customer Ledger")
        title.setObjectName("h3")
        sub_title = QLabel("Complete accounting balance, billing invoices, and payment trail")
        sub_title.setObjectName("subtitle")
        title_col.addWidget(title)
        title_col.addWidget(sub_title)
        header.addLayout(title_col)
        header.addStretch()

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#9CA3AF", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(30, 30)
        close_btn.setObjectName("modalCloseBtn")
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn, alignment=Qt.AlignTop)
        lay.addLayout(header)

        cust = self._customer or {}
        info_row = QHBoxLayout()
        info_row.setSpacing(20)
        for lbl, val in [
            ("Customer", str(cust.get("name") or "—")),
            ("Contact",  str(cust.get("contact") or "—")),
            ("Email",    str(cust.get("email") or "—")),
            ("Events",   str(cust.get("events") or cust.get("total_events") or 0)),
            ("Tier",     str(cust.get("loyalty_tier") or cust.get("tier") or "Bronze")),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            l = QLabel(lbl.upper())
            l.setStyleSheet("font-size: 10px; color: #6B7280; font-weight: 700; letter-spacing: 1px;")
            v = QLabel(val)
            v.setStyleSheet("font-size: 13px; font-weight: 600;")
            col.addWidget(l)
            col.addWidget(v)
            info_row.addLayout(col)
        info_row.addStretch()
        lay.addLayout(info_row)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        lay.addWidget(div)

        # Load ledger rows; support either id key. Any failure degrades to an
        # empty ledger rather than crashing the dialog.
        entries = []
        cid = cust.get("id") or cust.get("cus_id")
        if cid:
            try:
                import utils.repository as _repo
                entries = _repo.get_customer_ledger(cid) or []
            except Exception as e:
                print(f"[CustomerLedgerDialog] Error loading ledger for customer {cid}: {e}")
                entries = []

        # Sum debits (charges) and credits (payments) defensively - a single
        # malformed row must not abort the whole total.
        total_debit = 0.0
        total_credit = 0.0
        for e in entries:
            try:
                total_debit += float(e.get("debit") or 0.0)
            except Exception:
                pass
            try:
                total_credit += float(e.get("credit") or 0.0)
            except Exception:
                pass

        balance = total_debit - total_credit  # Positive = customer still owes.

        summary_row = QHBoxLayout()
        summary_row.setSpacing(16)
        for lbl, val, color in [
            ("Total Charged", f"₱ {total_debit:,.2f}",  "#E11D48"),
            ("Total Paid",    f"₱ {total_credit:,.2f}", "#22C55E"),
            # Balance shows amber when money is still owed, green when settled.
            ("Balance Due",   f"₱ {balance:,.2f}",      "#F59E0B" if balance > 0 else "#22C55E"),
        ]:
            card = QFrame()
            card.setObjectName("card")
            card.setStyleSheet("QFrame#card { padding: 6px 14px; }")
            cl = QVBoxLayout(card)
            cl.setSpacing(2)
            cl.setContentsMargins(12, 8, 12, 8)
            l = QLabel(lbl)
            l.setStyleSheet("font-size: 11px; color: #6B7280;")
            v = QLabel(val)
            v.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {color};")
            cl.addWidget(l)
            cl.addWidget(v)
            summary_row.addWidget(card)
        summary_row.addStretch()
        lay.addLayout(summary_row)

        # Ledger Cards List
        ledger_scroll = QScrollArea()
        ledger_scroll.setWidgetResizable(True)
        ledger_scroll.setFrameShape(QFrame.NoFrame)
        ledger_scroll.setStyleSheet("background: transparent;")

        ledger_container = QWidget()
        ledger_container.setStyleSheet("background: transparent;")
        ledger_lay = QVBoxLayout(ledger_container)
        ledger_lay.setContentsMargins(0, 0, 4, 0)
        ledger_lay.setSpacing(8)

        # Accent color per entry type and per entry status, used on the cards below.
        _TYPE_COLORS = {
            "Booking": "#3B82F6",
            "Invoice": "#F59E0B",
            "Payment": "#22C55E",
        }
        _STATUS_COLORS = {
            "CONFIRMED": "#22C55E", "COMPLETED": "#16A34A",
            "PENDING":   "#F59E0B", "CANCELLED": "#EF4444",
            "Paid":      "#22C55E", "Partial":   "#F59E0B",
            "Unpaid":    "#EF4444",
        }

        if not entries:
            empty_card = QFrame()
            empty_card.setObjectName("entryCard")
            empty_lay = QVBoxLayout(empty_card)
            empty_lbl = QLabel("No ledger entries found for this customer.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lay.addWidget(empty_lbl)
            ledger_lay.addWidget(empty_card)
        else:
            for e in entries:
                entry_card = QFrame()
                entry_card.setObjectName("entryCard")
                el = QHBoxLayout(entry_card)
                el.setContentsMargins(12, 10, 12, 10)
                el.setSpacing(14)

                ref_str = str(e.get("reference") or "—")
                rec_str = str(e.get("recorded_date") or "—")
                ev_str = str(e.get("event_date") or "—")
                e_type = str(e.get("entry_type") or "Entry")
                desc_str = str(e.get("description") or "—")
                st_str = str(e.get("status") or "CONFIRMED")
                debit_val = float(e.get("debit") or 0.0)
                credit_val = float(e.get("credit") or 0.0)

                col1 = QVBoxLayout()
                col1.setSpacing(2)
                ref_l = QLabel(ref_str)
                ref_l.setStyleSheet("font-weight: 700; font-size: 13px;")
                date_l = QLabel(f"Rec: {rec_str} | Event: {ev_str}")
                date_l.setObjectName("subtitle")
                col1.addWidget(ref_l)
                col1.addWidget(date_l)
                el.addLayout(col1, 2)

                t_color = _TYPE_COLORS.get(e_type, "#9CA3AF")
                type_lbl = QLabel(e_type)
                type_lbl.setStyleSheet(f"font-weight: 700; font-size: 11px; color: {t_color}; padding: 3px 8px; background: rgba(255,255,255,0.05); border-radius: 6px;")
                el.addWidget(type_lbl)

                desc_l = QLabel(f"{desc_str}  <span style='color:{_STATUS_COLORS.get(st_str, '#9CA3AF')}; font-weight:700;'>[{st_str}]</span>")
                desc_l.setStyleSheet("font-size: 12px;")
                desc_l.setTextFormat(Qt.RichText)
                el.addWidget(desc_l, 3)

                # Amount rendering depends on entry type: payments are credits
                # (green, "+"), bookings are charges (red), everything else
                # (invoices) is shown as an amber debit.
                if e_type == "Payment":
                    amt_text = f"+ ₱ {credit_val:,.2f}"
                    amt_color = "#22C55E"
                elif e_type == "Booking":
                    amt_text = f"₱ {debit_val:,.2f}"
                    amt_color = "#E11D48"
                else:
                    amt_text = f"₱ {debit_val:,.2f}"
                    amt_color = "#F59E0B"

                amt_lbl = QLabel(amt_text)
                amt_lbl.setStyleSheet(f"font-weight: 800; font-size: 14px; color: {amt_color};")
                amt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                el.addWidget(amt_lbl, 1)

                ledger_lay.addWidget(entry_card)

        ledger_lay.addStretch()
        ledger_scroll.setWidget(ledger_container)
        lay.addWidget(ledger_scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close = QPushButton("Close")
        close.setObjectName("secondaryButton")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        btn_row.addWidget(close)
        lay.addLayout(btn_row)

        outer.addWidget(container)

# Preset barangay/city options for the bulk-add address dropdown + completer.
# The leading "" is a blank default; the completer uses the list from index 1 on.
_CEBU_ADDRESS_OPTIONS = [
    "",
    "Lahug, Cebu City", "Guadalupe, Cebu City", "Mabolo, Cebu City", "Talamban, Cebu City",
    "Banilad, Cebu City", "Capitol Site, Cebu City", "Apas, Cebu City", "Tisa, Cebu City",
    "Pardo, Cebu City", "Basak San Nicolas, Cebu City", "Punta Princesa, Cebu City",
    "Sambag I, Cebu City", "Sambag II, Cebu City", "Kasambagan, Cebu City", "Camputhaw, Cebu City",
    "Tipolo, Mandaue City", "Subangdaku, Mandaue City", "Banilad, Mandaue City",
    "Bakilid, Mandaue City", "Cabancalan, Mandaue City", "Maguikay, Mandaue City", "Centro, Mandaue City",
    "Mactan, Lapu-Lapu City", "Maribago, Lapu-Lapu City", "Basak, Lapu-Lapu City",
    "Poblacion, Lapu-Lapu City", "Gun-ob, Lapu-Lapu City", "Pajac, Lapu-Lapu City",
    "Tabunok, Talisay City", "Bulacao, Talisay City", "Lawaan I, Talisay City", "Lawaan II, Talisay City",
    "Poblacion, Talisay City", "Dumlog, Talisay City", "San Roque, Talisay City",
    "Cebu City", "Mandaue City", "Lapu-Lapu City", "Talisay City"
]


class AddMultipleCustomersDialog(QDialog):
    """Spreadsheet-style modal for entering many customers in one pass.

    Presents an editable table (name / contact / email / address) that saves all
    non-empty rows at once, skipping duplicates by name. The count of newly
    inserted customers is exposed as ``self._added_count`` for the caller's toast.
    """

    def __init__(self, parent=None):
        """Set up the bulk-add window and build the grid UI.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Add Multiple Customers")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(860, 540)
        self.setModal(True)
        self._added_count = 0  # How many rows were actually inserted (post-dedupe).
        self._build_ui()

    def _build_ui(self):
        """Build the header, the 4-column entry table, row controls, and buttons.

        Side effects: creates ``self.table`` seeded with 5 empty rows and
        ``self._err`` for validation messages.
        """
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Add Multiple Customers")
        title.setObjectName("h3")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        sub = QLabel("Quickly enter multiple client records at once (searchable Cebu address dropdown included):")
        sub.setObjectName("subtitle")
        lay.addWidget(sub)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Customer / Company Name *", "Contact Number *", "Email Address", "Address (Cebu Dropdown / Search)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(46)
        # Add 5 initial rows
        for _ in range(5):
            self._add_row()

        lay.addWidget(self.table)

        row_actions = QHBoxLayout()
        add_row_btn = QPushButton("  + Add Row")
        add_row_btn.setObjectName("secondaryButton")
        add_row_btn.clicked.connect(self._add_row)
        del_row_btn = QPushButton("  - Remove Selected Row")
        del_row_btn.setObjectName("secondaryButton")
        del_row_btn.clicked.connect(self._delete_selected_row)
        row_actions.addWidget(add_row_btn)
        row_actions.addWidget(del_row_btn)
        row_actions.addStretch()
        lay.addLayout(row_actions)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #E11D48; font-size: 12px;")
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        save = QPushButton("  Save All Customers")
        save.setObjectName("primaryButton")
        save.setIcon(btn_icon_primary("check"))
        save.setIconSize(QSize(15, 15))
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save_all)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

        outer.addWidget(container)

    def _add_row(self):
        """Append one empty entry row with name/contact/email inputs and an
        editable, auto-completing Cebu-address combo box."""
        r = self.table.rowCount()
        self.table.insertRow(r)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Customer / Company Name *")
        name_edit.setFixedHeight(34)
        self.table.setCellWidget(r, 0, name_edit)

        contact_edit = QLineEdit()
        contact_edit.setPlaceholderText("09171234567")
        contact_edit.setFixedHeight(34)
        self.table.setCellWidget(r, 1, contact_edit)

        email_edit = QLineEdit()
        email_edit.setPlaceholderText("client@example.com")
        email_edit.setFixedHeight(34)
        self.table.setCellWidget(r, 2, email_edit)

        addr_combo = QComboBox()
        addr_combo.setEditable(True)  # Allow free-text addresses beyond the presets.
        addr_combo.addItems(_CEBU_ADDRESS_OPTIONS)
        addr_combo.setFixedHeight(34)
        # Case-insensitive completer over the presets (skipping the blank at [0]).
        completer = QCompleter(_CEBU_ADDRESS_OPTIONS[1:], addr_combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        addr_combo.setCompleter(completer)
        self.table.setCellWidget(r, 3, addr_combo)

    def _delete_selected_row(self):
        """Remove the currently selected table row, if any."""
        curr = self.table.currentRow()
        if curr >= 0:
            self.table.removeRow(curr)

    def _save_all(self):
        """Collect, validate, dedupe, and insert every non-empty row.

        Rows with neither a name nor a contact are skipped silently. A row with a
        contact but no name is a hard validation error. Duplicates - either within
        this batch or already in the DB (``repo.customer_exists``) - are skipped
        and reported. Sets ``self._added_count`` and accepts the dialog.
        """
        rows_to_save = []
        for r in range(self.table.rowCount()):
            name_w = self.table.cellWidget(r, 0)
            contact_w = self.table.cellWidget(r, 1)
            email_w = self.table.cellWidget(r, 2)
            addr_w = self.table.cellWidget(r, 3)

            name = name_w.text().strip() if isinstance(name_w, QLineEdit) else ""
            contact = contact_w.text().strip() if isinstance(contact_w, QLineEdit) else ""
            email = email_w.text().strip() if isinstance(email_w, QLineEdit) else ""
            addr = addr_w.currentText().strip() if isinstance(addr_w, QComboBox) else ""

            if not name and not contact:
                continue  # Entirely blank row - ignore it.
            if not name:
                # A contact without a name is invalid; point at the offending row.
                self._err.setText(f"Row {r+1}: Customer Name cannot be empty.")
                self._err.show()
                return
            rows_to_save.append({
                "name": name,
                "contact": contact,
                "email": email,
                "address": addr,
                "status": "Active"
            })

        if not rows_to_save:
            self._err.setText("Please enter at least one customer.")
            self._err.show()
            return

        saved = 0
        skipped_names = []
        seen_names = set()  # Case-insensitive names already handled this batch.
        for data in rows_to_save:
            name_key = data["name"].strip().lower()
            # Skip if it's a duplicate within this batch OR already in the DB.
            if name_key in seen_names or repo.customer_exists(data["name"]):
                skipped_names.append(data["name"])
                continue
            seen_names.add(name_key)
            res = repo.add_customer(data)
            if res:
                saved += 1

        self._added_count = saved
        if skipped_names:
            # Tell the user which names were skipped, with singular/plural grammar.
            from components.dialogs import success as _success
            names_str = ", ".join(skipped_names)
            _success(
                self,
                f"{names_str} already exist{'s' if len(skipped_names) == 1 else ''} — skipping "
                f"{'this customer' if len(skipped_names) == 1 else 'these customers'}. "
                f"{saved} new customer(s) added.",
                "Some Customers Skipped",
            )
        self.accept()


class CustomersPage(QWidget):
    """Main customers screen: searchable, paginated, batch-selectable card list.

    Design notes / invariants worth knowing when editing this class:

    - Reloads are *coalesced*: a debounce timer plus in-flight/pending flags
      (``_reload_in_flight`` / ``_reload_pending``) ensure only one fetch+render
      pass runs at a time, with at most one more queued behind it.
    - Rendering is *generation-tokened*: ``_reload_generation`` and
      ``_render_token`` let stale async callbacks/batches detect they've been
      superseded and abort, preventing races that mutate the same layout.
    - The list is *lazily paginated* (``_page_size`` rows at a time) and rendered
      in small yielded batches so the Qt UI thread is never blocked for long.
    - An optional pre-warmed in-memory cache serves the "Show All" view instantly;
      the default "Active only" view always hits the DB for the recency window.
    - Cards bake in per-user permissions at render time, so a permission change
      forces a rebuild (see :meth:`refresh_permissions`).
    """

    def __init__(self, parent=None):
        """Initialize all reload/pagination/selection state, build the UI, and
        subscribe to app-wide data-change signals that trigger a reload.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._dirty = True  # Needs a (re)load before it can show fresh data.
        self._customers = []  # Currently loaded customer rows (grows via pagination).
        self._selected_ids: set[int] = set()  # Ids checked for batch delete.
        self._card_checkboxes: dict[int, QCheckBox] = {}  # id -> its card checkbox.
        self._reload_generation = 0  # Bumped each reload; stale callbacks compare against it.
        self._reload_in_flight = False  # True while a fetch+render pass is running.
        self._reload_pending = False  # A reload was requested while one was in flight.
        # Lazy pagination: only fetch/render the rows the user actually scrolls to.
        self._page_size = 50
        self._has_more = True
        self._loading_more = False
        # Busy-flag guarding the card list's batch render pipeline. Prevents a
        # scroll-triggered load-more from starting while an initial/previous
        # batch chain is still mutating the same layout (see race fix).
        self._rendering = False
        self._cached_remainder = None  # Un-rendered tail of a cached full list, if any.
        # Default view: only customers with a booking in the last 6 months.
        # Toggle to "Show All" reveals dormant/never-booked customers too.
        self._active_only = True
        # Debounce timer: collapse a burst of reload requests into one fetch.
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(80)
        self._reload_timer.timeout.connect(self._do_reload_direct)
        self._build_ui()

        # Refresh whenever anything elsewhere in the app changes customer-relevant
        # data. Wrapped in try/except so a missing signals module never breaks the page.
        try:
            from utils.signals import app_events
            app_events().customer_saved.connect(self._mark_dirty_and_reload)
            app_events().booking_saved.connect(self._mark_dirty_and_reload)
            app_events().sync_completed.connect(self._mark_dirty_and_reload)
            app_events().data_changed.connect(self._mark_dirty_and_reload)
        except Exception:
            pass

    def _show_toast(self, title: str, message: str, color: str = "#22C55E"):
        """Show a transient toast via the main window's toast manager.

        Falls back to a modal success dialog if the window has no toast manager.

        Args:
            title: Toast heading.
            message: Toast body text.
            color: Accent color (defaults to green/success).
        """
        win = self.window()
        if hasattr(win, "_toast_manager") and win._toast_manager:
            win._toast_manager.show(title, message, color=color)
        else:
            from components.dialogs import success
            success(self, title=title, message=message)

    def _mark_dirty_and_reload(self):
        """Signal handler: mark data stale and reload, unless a search is active.

        If the user is mid-search, an immediate rebuild would wipe their filtered
        view, so the refresh is deferred (``_reload_deferred``) until the search
        clears. Only reloads when the page is actually visible.
        """
        self._dirty = True
        # Don't rebuild the list while the user is actively searching - it would
        # wipe their filtered view. Defer; refresh once the search is cleared.
        if self._has_active_search():
            self._reload_deferred = True
            return
        if self.isVisible():
            self._do_reload()

    def _mark_dirty(self):
        """Flag that the loaded data is stale and should be refetched next reload."""
        self._dirty = True

    def showEvent(self, event):
        """On becoming visible, refresh permissions and reload if data is stale.

        This is why navigating back to the page picks up external changes.
        """
        super().showEvent(event)
        self.refresh_permissions()
        if getattr(self, "_dirty", True):
            self._do_reload()

    def reload(self):
        """Force a full refresh: mark dirty, re-check permissions, and reload."""
        self._mark_dirty()
        self.refresh_permissions()
        self._do_reload()

    def _on_status_filter_changed(self, _idx):
        """Handle the Active/Show-All dropdown change and force a fresh fetch.

        ``_has_populated_once`` is reset so the reload can't reuse a population
        from the other filter mode (the cache only applies to "Show All").
        """
        self._active_only = bool(self._status_filter.currentData())
        # Force the next reload to re-fetch (cache only applies to Show All,
        # and a prior Show All population must not leak into Active or vice versa).
        self._has_populated_once = False
        self._do_reload()

    def refresh_permissions(self):
        """Re-read the current user's customer permissions and update the UI.

        Toggles visibility/enablement of the create/import/delete controls and,
        crucially, rebuilds the card list if the permission set changed - because
        per-card Edit/Delete buttons are baked in at render time and would
        otherwise reflect a previous user's rights after a re-login.
        """
        from utils.auth import SessionManager
        can_create = SessionManager.has_permission("customers", "create")
        can_delete = SessionManager.has_permission("customers", "delete")
        can_edit = SessionManager.has_permission("customers", "edit")

        # Per-card Edit/Delete buttons are baked in at render time, so a role
        # change (e.g. logging back in as Admin after a Staff session) would
        # otherwise leave already-rendered cards showing the PREVIOUS user's
        # permissions. Rebuild the card list when the permission set changes.
        sig = (can_create, can_edit, can_delete)
        if sig != getattr(self, "_last_perm_sig", None):
            self._last_perm_sig = sig
            if self._customers and not getattr(self, "_rendering", False):
                self._populate_table()

        if hasattr(self, "add_btn"):
            self.add_btn.setEnabled(can_create)
            self.add_btn.setVisible(can_create)
        if hasattr(self, "multi_add_btn"):
            self.multi_add_btn.setEnabled(can_create)
            self.multi_add_btn.setVisible(can_create)
        if hasattr(self, "import_btn"):
            self.import_btn.setEnabled(can_create)
            self.import_btn.setVisible(can_create)
        if hasattr(self, "_btn_delete_selected"):
            self._btn_delete_selected.setEnabled(can_delete and len(self._selected_ids) > 0)
            self._btn_delete_selected.setVisible(can_delete)
        if hasattr(self, "_cb_select_all"):
            self._cb_select_all.setVisible(can_delete)
        if hasattr(self, "_lbl_selected_count"):
            self._lbl_selected_count.setVisible(can_delete)

    def _do_reload(self):
        """Schedule a reload through the debounce timer (or run it immediately).

        Clears any deferred-reload flag and starts the 80ms timer so bursty
        triggers collapse into a single fetch.
        """
        self._reload_deferred = False
        if hasattr(self, "_reload_timer"):
            self._reload_timer.start(80)
        else:
            self._do_reload_direct()

    def _do_reload_direct(self):
        """Perform (or queue) the actual reload: fetch page 0 and re-render.

        Coalesces overlapping reloads via ``_reload_in_flight``/``_reload_pending``,
        resets pagination, and serves from the pre-warmed cache when eligible
        (Show-All view, first population) otherwise fetches page 0 from the DB.
        """
        # Coalesce overlapping reloads: if a reload (fetch + batch-render) is
        # already running, don't start a second one in parallel - just remember
        # to run exactly one more pass once the current one fully finishes.
        if getattr(self, "_reload_in_flight", False):
            self._reload_pending = True
            return
        self._reload_in_flight = True
        self._reload_pending = False

        self._dirty = False
        self._reload_generation += 1
        gen = self._reload_generation

        # Pagination resets on every full reload - we always re-fetch page 0.
        self._has_more = True
        self._loading_more = False

        # Instant render from the pre-loaded memory cache if available. The login
        # welcome sequence may have cached the FULL, unfiltered customer list, so
        # it's only valid for the "Show All" view - the default "Active Customers"
        # filter always goes through the DB so the 12-month window is honored.
        from utils.data_cache import DataCache
        cached = DataCache.get("customers_loyalty") if not self._active_only else None
        if cached is not None and not getattr(self, "_has_populated_once", False):
            self._has_populated_once = True
            # Render only the first page now; stash the rest to serve on scroll
            # without touching the DB again.
            self._cached_remainder = list(cached[self._page_size:])
            page = list(cached[:self._page_size])
            if len(cached) <= self._page_size:
                self._has_more = False
            if hasattr(self, "_loader"):
                self._loader.show_overlay("Loading customer records...")
                # Slight delay lets the overlay paint before the render work starts.
                QTimer.singleShot(60, lambda: self._on_customers_loaded(page, gen))
            else:
                self._on_customers_loaded(page, gen)
            return

        # No cache - fetch just page 0 from the DB (never the whole table).
        self._cached_remainder = None
        if hasattr(self, "_loader"):
            self._loader.show_overlay("Loading customer records...")
        run_async(self, repo.get_customers_page,
                  lambda data, gen=gen: self._on_first_page_loaded(data, gen),
                  None, 0, self._page_size, self._active_only)

    def _on_first_page_loaded(self, data, gen=None):
        """Async callback for the page-0 DB fetch; hands off to the renderer.

        Args:
            data: The fetched first-page rows (or None).
            gen: Reload generation this fetch belongs to, for staleness checks.
        """
        page = data or []
        if len(page) < self._page_size:
            # A short first page means there is no further page to load.
            self._has_more = False
        self._on_customers_loaded(page, gen)

    def _reload_finished(self):
        """Mark the current reload pass complete and run one queued reload if any.

        This is the single exit point that clears the in-flight flag, so a
        coalesced ``_reload_pending`` request is honored exactly once here.
        """
        self._reload_in_flight = False
        self._loading_more = False
        if self._reload_pending:
            self._reload_pending = False
            QTimer.singleShot(0, self._do_reload)

    def _on_customers_loaded(self, data, gen=None):
        """Receive page-0 rows and (re)populate the card list if they changed.

        Guards: aborts if the widget was destroyed (shiboken ``isValid``) or if a
        newer reload generation has superseded this one. Short-circuits the render
        pipeline when the data signature is unchanged from what's already shown.

        Args:
            data: The customer rows to display.
            gen: The reload generation this data belongs to.
        """
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        if gen is not None and gen != self._reload_generation:
            return  # A newer reload has started; this callback is stale.
        rows = data if data is not None else []
        # Cheap change-detection signature: if the visible fields are identical,
        # skip the expensive re-render entirely.
        old_sig = [(c.get("id"), c.get("name"), c.get("events"), c.get("status")) for c in self._customers]
        new_sig = [(c.get("id"), c.get("name"), c.get("events"), c.get("status")) for c in rows]
        if old_sig == new_sig and getattr(self, "_has_populated_once", False):
            # Nothing changed - the render pipeline won't run, so finish now.
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            self._reload_finished()
            return
        self._has_populated_once = True
        self._customers = rows
        self._selected_ids.clear()
        # _populate_table() kicks off async batch rendering; the loader is
        # hidden by _render_next_batch once the LAST batch finishes, not here.
        self._populate_table()

    def _on_scroll_near_bottom(self, value):
        """Scrollbar handler: trigger loading the next page when near the bottom.

        Args:
            value: Current vertical scrollbar position.
        """
        sb = self.scroll_area.verticalScrollBar()
        if sb.maximum() - value < 200:  # Within 200px of the end -> prefetch more.
            self._load_more_customers()

    def _load_more_customers(self):
        """Load and append the next page of customers (from cache or the DB).

        No-ops if a page load is already running, there are no more rows, or the
        batch renderer is still busy (guards against concurrent layout mutation).
        """
        if getattr(self, "_loading_more", False) or not getattr(self, "_has_more", False):
            return
        # Don't start a new page while this list's batch chain is still active.
        if self._rendering:
            return
        self._loading_more = True
        if self._cached_remainder is not None:
            # Serve the next slice straight from the cached full list - no DB hit.
            more = self._cached_remainder[:self._page_size]
            self._cached_remainder = self._cached_remainder[self._page_size:]
            if not self._cached_remainder:
                self._has_more = False
            QTimer.singleShot(0, lambda: self._on_more_customers_loaded(more))
            return
        # Offset by the current row count so we fetch the next contiguous page.
        run_async(self, repo.get_customers_page, self._on_more_customers_loaded,
                  None, len(self._customers), self._page_size, self._active_only)

    def _on_more_customers_loaded(self, data):
        """Async callback for a subsequent page: append the new rows' cards.

        Args:
            data: The newly fetched rows (or None). A short page clears
                ``_has_more``; an empty page just releases the loading flag.
        """
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return  # Widget was destroyed before the fetch returned.
        except Exception:
            pass
        new_rows = data or []
        if self._cached_remainder is None and len(new_rows) < self._page_size:
            self._has_more = False
        if not new_rows:
            self._loading_more = False
            return
        self._customers.extend(new_rows)
        self._append_customer_cards(new_rows)

    def _append_customer_cards(self, new_rows):
        """Kick off incremental rendering of appended rows onto the existing list.

        Args:
            new_rows: The newly loaded customer rows to render as cards.

        Side effects: snapshots current edit/delete permissions, bumps the render
        token, and starts the batched renderer with ``_rendering`` set.
        """
        # New cards are inserted just before the trailing stretch by the batch
        # renderer (see _insert_card_before_stretch), so we no longer take the
        # stretch out of the layout here - repeatedly take()-ing and discarding
        # a QLayoutItem was the suspected trigger for a native Qt memory-reuse
        # crash under heavy infinite-scroll append churn.
        from utils.auth import SessionManager
        self._render_can_edit = SessionManager.has_permission("customers", "edit")
        self._render_can_delete = SessionManager.has_permission("customers", "delete")
        self._render_token = getattr(self, "_render_token", 0) + 1
        self._render_queue = list(new_rows)
        self._rendering = True
        self._render_next_batch(self._render_token)

    def _build_ui(self):
        """Construct the full page: action header, search+filter row, and the
        scrollable card area with its batch-selection toolbar.

        Side effects: creates the many widgets/attributes the rest of the class
        relies on (``add_btn``, ``_search``, ``_status_filter``, ``scroll_area``,
        ``cards_layout``, ``_empty_lbl``, ``_loader`` and the batch controls).
        """
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Customers")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        self.add_btn = QPushButton("  Add Customer")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setIcon(btn_icon_primary("plus"))
        self.add_btn.setIconSize(QSize(15, 15))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._open_add_dialog)
        header.addWidget(self.add_btn)

        self.multi_add_btn = QPushButton("  + Quick Multi-Add")
        self.multi_add_btn.setObjectName("secondaryButton")
        self.multi_add_btn.setCursor(Qt.PointingHandCursor)
        self.multi_add_btn.clicked.connect(self._open_multi_add_dialog)
        header.addWidget(self.multi_add_btn)

        self.import_btn = QPushButton("  Import")
        self.import_btn.setObjectName("secondaryButton")
        self.import_btn.setIcon(btn_icon_secondary("export"))
        self.import_btn.setIconSize(QSize(15, 15))
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self._open_import_dialog)
        header.addWidget(self.import_btn)

        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.clicked.connect(self._export_csv)
        header.addWidget(export_btn)

        root.addLayout(header)

        # Search Bar + Active/Show-All filter
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setPlaceholderText("Search customers...")
        self._search.setFixedHeight(38)
        self._search.setMaximumWidth(320)
        # Debounce search input by 500ms so filtering runs once the user pauses,
        # not on every keystroke.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._filter_table_now)
        self._search.textChanged.connect(lambda: self._search_timer.start(500))
        search_row.addWidget(self._search)

        self._status_filter = QComboBox()
        self._status_filter.setFixedHeight(38)
        self._status_filter.setMinimumWidth(200)
        # Item data is the _active_only flag: True = recent-only, False = all.
        self._status_filter.addItem("Active Customers (Default)", True)
        self._status_filter.addItem("Show All", False)
        self._status_filter.currentIndexChanged.connect(self._on_status_filter_changed)
        search_row.addWidget(self._status_filter)

        search_row.addStretch()
        root.addLayout(search_row)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        # Batch Selection Toolbar
        batch_toolbar = QHBoxLayout()
        batch_toolbar.setContentsMargins(4, 0, 4, 4)
        batch_toolbar.setSpacing(12)

        self._cb_select_all = QCheckBox("Select All")
        self._cb_select_all.setStyleSheet("QCheckBox { font-weight: 600; font-size: 13px; color: #9CA3AF; }")
        self._cb_select_all.stateChanged.connect(self._toggle_select_all)
        batch_toolbar.addWidget(self._cb_select_all)

        self._lbl_selected_count = QLabel("0 selected")
        self._lbl_selected_count.setStyleSheet("font-size: 12px; color: #6B7280; font-weight: 600;")
        batch_toolbar.addWidget(self._lbl_selected_count)

        batch_toolbar.addStretch()

        self._btn_delete_selected = QPushButton("  Delete Selected")
        self._btn_delete_selected.setIcon(btn_icon_red("trash"))
        self._btn_delete_selected.setIconSize(QSize(13, 13))
        self._btn_delete_selected.setCursor(Qt.PointingHandCursor)
        self._btn_delete_selected.setEnabled(False)
        self._btn_delete_selected.setStyleSheet(
            "QPushButton { background: rgba(225,29,72,0.15); border: 1px solid rgba(225,29,72,0.3); color: #E11D48; border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(225,29,72,0.25); border-color: #E11D48; }"
            "QPushButton:disabled { opacity: 0.35; background: rgba(255,255,255,0.04); border-color: transparent; color: #6B7280; }"
        )
        self._btn_delete_selected.clicked.connect(self._delete_selected_customers)
        batch_toolbar.addWidget(self._btn_delete_selected)

        card_layout.addLayout(batch_toolbar)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        card_layout.addWidget(div)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.setSpacing(12)

        self._customer_cards: list[tuple[dict, QFrame]] = []
        self._empty_lbl = QLabel("No customers found.")
        self._empty_lbl.setObjectName("subtitle")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.hide()
        self.cards_layout.addWidget(self._empty_lbl)

        self.scroll_area.setWidget(self.cards_container)
        # Lazy "load more" as the user nears the bottom of the list.
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_near_bottom)
        card_layout.addWidget(self.scroll_area)
        root.addWidget(card)

        self._loader = LoadingOverlay(self, "Loading customer records...")

    def _populate_table(self, customers=None):
        """Tear down existing cards and (re)build the list via the batch renderer.

        Args:
            customers: Optional explicit row list to render; defaults to
                ``self._customers``.

        Side effects: destroys current card widgets, resets selection checkboxes,
        snapshots edit/delete permissions, and starts incremental rendering. When
        there's no data it shows the empty label and finishes the pipeline early.
        """
        # Invalidate any in-flight incremental render so stale batches abort.
        self._render_token = getattr(self, "_render_token", 0) + 1
        token = self._render_token

        # Freeze repaints while we mutate the layout to avoid flicker/partial paints.
        if hasattr(self, "cards_container"):
            self.cards_container.setUpdatesEnabled(False)
        try:
            self._card_checkboxes.clear()
            # Remove and schedule deletion of every previously rendered card.
            for _, card_w in self._customer_cards:
                self.cards_layout.removeWidget(card_w)
                card_w.hide()
                card_w.deleteLater()
            self._customer_cards.clear()

            # Sweep any leftover layout items except the empty label at index 0.
            while self.cards_layout.count() > 1:
                item = self.cards_layout.takeAt(1)
                if item.widget() and item.widget() != self._empty_lbl:
                    item.widget().deleteLater()

            data = customers if customers is not None else self._customers

            if not data:
                self._empty_lbl.show()
                self._update_selection_ui()
                self._filter_table_now()
                # No batches will run - finish the pipeline immediately.
                if hasattr(self, "_loader"):
                    self._loader.hide_overlay()
                self._rendering = False
                self._reload_finished()
                return

            self._empty_lbl.hide()
            # Hoist per-render-invariant permission checks out of the per-row loop.
            from utils.auth import SessionManager
            self._render_can_edit = SessionManager.has_permission("customers", "edit")
            self._render_can_delete = SessionManager.has_permission("customers", "delete")
            self._render_queue = list(data)  # Drained batch-by-batch by the renderer.
        finally:
            if hasattr(self, "cards_container"):
                self.cards_container.setUpdatesEnabled(True)

        # Build the cards incrementally so the main thread is never blocked
        # for more than one batch at a time.
        self._rendering = True
        self._render_next_batch(token)

    @staticmethod
    def _insert_card_before_stretch(layout, card):
        """Insert ``card`` just before a trailing stretch spacer, if present.

        Args:
            layout: The QVBoxLayout to insert into.
            card: The widget to add.

        Rationale: repeatedly ``take()``-ing and discarding the stretch spacer was
        the suspected trigger for a native Qt memory-reuse crash under heavy
        append churn, so the spacer is left in place and cards go before it.
        """
        # Insert just before a trailing stretch spacer if one exists, rather
        # than ever taking the spacer out of the layout - repeatedly
        # take()-ing and discarding a QLayoutItem was the suspected trigger
        # for a native Qt memory-reuse crash under heavy append churn.
        count = layout.count()
        if count > 0 and layout.itemAt(count - 1).widget() is None:
            layout.insertWidget(count - 1, card)
        else:
            layout.addWidget(card)

    def _render_next_batch(self, token, batch_size=15):
        """Render one batch of queued cards, then reschedule itself for the rest.

        Renders ``batch_size`` cards, yields to the Qt event loop, and continues
        on the next tick so the UI stays responsive. When the queue drains it adds
        the trailing stretch, updates selection/filter UI, hides the loader (only
        once nothing more is pending), and optionally auto-loads the next page.

        Args:
            token: The render token this chain was started with; if it no longer
                matches ``self._render_token`` the batch aborts (superseded).
            batch_size: Number of cards to build per event-loop slice.
        """
        # Abort if a newer populate call has superseded this render.
        if token != getattr(self, "_render_token", 0):
            return
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass

        # Pop the next slice off the front of the render queue.
        queue = getattr(self, "_render_queue", [])
        batch = queue[:batch_size]
        del queue[:batch_size]

        can_edit = getattr(self, "_render_can_edit", False)
        can_delete = getattr(self, "_render_can_delete", False)

        if hasattr(self, "cards_container"):
            self.cards_container.setUpdatesEnabled(False)
        try:
            for c in batch:
                c_card = self._create_customer_card(c, can_edit, can_delete)
                self._insert_card_before_stretch(self.cards_layout, c_card)
                self._customer_cards.append((c, c_card))
        finally:
            if hasattr(self, "cards_container"):
                self.cards_container.setUpdatesEnabled(True)

        # Advance the loading spinner one frame per batch as visible progress.
        if hasattr(self, "_loader") and self._loader and self._loader.isVisible():
            self._loader.spin_step()

        if queue:
            # Yield to the Qt event loop so paint/input events are processed
            # between batches, then continue rendering.
            QTimer.singleShot(0, lambda: self._render_next_batch(token, batch_size))
        else:
            # Add the trailing stretch only if one isn't already there (a
            # previous append cycle may have left one in place - we never
            # remove it, see _insert_card_before_stretch).
            count = self.cards_layout.count()
            if count == 0 or self.cards_layout.itemAt(count - 1).widget() is not None:
                self.cards_layout.addStretch()
            self._update_selection_ui()
            self._filter_table_now()
            # Only hide the loader once there's truly nothing left to load in
            # the background - otherwise the overlay disappears after page 0
            # while auto-continue is still silently fetching later pages.
            if hasattr(self, "_loader") and not self._has_more:
                self._loader.hide_overlay()
            self._rendering = False
            self._reload_finished()
            # Keep quietly loading the next page in the background instead of
            # waiting for the user to scroll - each page still fetches on a
            # background thread and renders in small yielded batches, so this
            # never blocks the UI; the short delay just avoids competing with
            # whatever the user is doing right after a page finishes.
            if self._has_more and not self._loading_more:
                QTimer.singleShot(150, self._load_more_customers)

    def _create_customer_card(self, c: dict, can_edit: bool = None, can_delete: bool = None) -> QFrame:
        """Build one customer row card with checkbox, details, actions, and status.

        Args:
            c: The customer dict (supports ``id`` or ``cus_id``).
            can_edit: Whether to render/enable the edit action. If None it is
                looked up from the session (used when called outside a batch).
            can_delete: Whether to render/enable the delete action; same None
                fallback as ``can_edit``.

        Returns:
            QFrame: The assembled, fully wired card. Edit/delete buttons are only
            added when the respective permission is granted, and double-click-to-
            edit is enabled only when editing is allowed.
        """
        cid = int(c.get("id") or c.get("cus_id") or 0)
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 14, 18, 14)
        lay.setSpacing(14)

        # Col 0: Checkbox
        cb = QCheckBox()
        cb.setChecked(cid in self._selected_ids)  # Restore selection across re-renders.
        # Default-arg captures this card's id so the handler targets the right row.
        cb.stateChanged.connect(lambda state, cust_id=cid: self._on_card_checked(cust_id, state))
        self._card_checkboxes[cid] = cb
        lay.addWidget(cb, alignment=Qt.AlignVCenter)

        # Col 1: Customer Name, Contact, Email
        c1 = QVBoxLayout()
        c1.setSpacing(2)
        _q = self._search.text() if hasattr(self, "_search") else ""
        name_lbl = QLabel(highlight_html(c.get("name", ""), _q))
        name_lbl.setTextFormat(Qt.RichText)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 15px;")
        # Keep a handle so the search filter can re-highlight the name live
        # (the list is filtered client-side without re-rendering the cards).
        card._name_lbl = name_lbl        # Label to re-apply highlight markup to.
        card._cust_name = c.get("name", "")  # Unhighlighted source name for filtering.
        info_lbl = QLabel(f"📞 {c['contact']}  |  ✉ {c['email']}")
        info_lbl.setObjectName("subtitle")
        c1.addWidget(name_lbl)
        c1.addWidget(info_lbl)
        if c.get("address"):
            addr_l = QLabel(f"📍 {c['address']}")
            addr_l.setStyleSheet("font-size: 11px; color: #6B7280;")
            c1.addWidget(addr_l)
        lay.addLayout(c1, 3)

        # Col 2: Events Count & Tier
        c2 = QHBoxLayout()
        c2.setSpacing(12)
        events_box = QVBoxLayout()
        events_box.setSpacing(2)
        ev_title = QLabel("EVENTS")
        ev_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #6B7280; letter-spacing: 0.5px;")
        ev_val = QLabel(str(c.get("events", 0)))
        ev_val.setStyleSheet("font-weight: 800; font-size: 14px; color: #F9FAFB;")
        events_box.addWidget(ev_title)
        events_box.addWidget(ev_val)
        c2.addLayout(events_box)

        tier = c.get("loyalty_tier", "Bronze")
        c2.addWidget(_tier_badge(tier), alignment=Qt.AlignVCenter)
        lay.addLayout(c2, 2)

        # Col 3: Status
        status_lbl = QLabel(c["status"])
        color_map = {"Active": "#22C55E", "Pending": "#F59E0B", "Inactive": "#6B7280"}
        s_color = color_map.get(c["status"], "#9CA3AF")
        status_lbl.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {s_color}; padding: 4px 10px; background: rgba(255,255,255,0.05); border-radius: 8px;")
        lay.addWidget(status_lbl, alignment=Qt.AlignVCenter)

        # Col 4: Action Buttons
        actions_w = QFrame(card)
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        # When permissions weren't passed in (card built outside a batch render),
        # look them up from the current session now.
        if can_edit is None or can_delete is None:
            from utils.auth import SessionManager
            if can_edit is None:
                can_edit = SessionManager.has_permission("customers", "edit")
            if can_delete is None:
                can_delete = SessionManager.has_permission("customers", "delete")

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", color="#38BDF8" if can_edit else "#4B5563", size=QSize(14, 14)))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(32, 32)
        edit_btn.setToolTip("Edit customer" if can_edit else "Permission required to edit")
        edit_btn.setStyleSheet(
            "QPushButton { background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; } "
            "QPushButton:hover { background: rgba(56, 189, 248, 0.25); border-color: #38BDF8; }"
        )
        edit_btn.setCursor(Qt.PointingHandCursor if can_edit else Qt.ForbiddenCursor)
        edit_btn.setEnabled(can_edit)
        edit_btn.clicked.connect(lambda _, cust=c: self._open_edit_dialog(cust))

        ledger_btn = QPushButton()
        ledger_btn.setIcon(get_icon("reports", color="#3B82F6", size=QSize(14, 14)))
        ledger_btn.setIconSize(QSize(14, 14))
        ledger_btn.setFixedSize(32, 32)
        ledger_btn.setToolTip("View statement & ledger")
        ledger_btn.setStyleSheet(
            "QPushButton { background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 6px; } "
            "QPushButton:hover { background: rgba(59, 130, 246, 0.25); border-color: #3B82F6; }"
        )
        ledger_btn.setCursor(Qt.PointingHandCursor)
        ledger_btn.clicked.connect(lambda _, cust=c: self._open_ledger(cust))

        fu_btn = QPushButton()
        fu_btn.setIcon(get_icon("bell", color="#F59E0B", size=QSize(14, 14)))
        fu_btn.setIconSize(QSize(14, 14))
        fu_btn.setFixedSize(32, 32)
        fu_btn.setToolTip("Follow-up reminders")
        fu_btn.setStyleSheet(
            "QPushButton { background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; } "
            "QPushButton:hover { background: rgba(245, 158, 11, 0.25); border-color: #F59E0B; }"
        )
        fu_btn.setCursor(Qt.PointingHandCursor)
        fu_btn.clicked.connect(lambda _, cust=c: self._open_follow_ups(cust))

        del_btn = QPushButton()
        del_btn.setIcon(btn_icon_red("trash") if can_delete else get_icon("trash", color="#4B5563", size=QSize(14, 14)))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(32, 32)
        del_btn.setStyleSheet(
            "QPushButton { background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; } "
            "QPushButton:hover { background: rgba(239, 68, 68, 0.25); border-color: #EF4444; }"
        )
        del_btn.setCursor(Qt.PointingHandCursor if can_delete else Qt.ForbiddenCursor)
        del_btn.setEnabled(can_delete)
        del_btn.setToolTip("Delete customer" if can_delete else "Permission required to delete")
        del_btn.clicked.connect(lambda _, cust=c: self._delete_customer_by_ref(cust))

        # Edit/delete buttons only appear when permitted; ledger and follow-up
        # are always available.
        if can_edit:
            actions_l.addWidget(edit_btn)
        actions_l.addWidget(ledger_btn)
        actions_l.addWidget(fu_btn)
        if can_delete:
            actions_l.addWidget(del_btn)

        lay.addWidget(actions_w)

        # Convenience: double-clicking the card opens edit (only if allowed).
        if can_edit:
            card.mouseDoubleClickEvent = lambda _, cust=c: self._open_edit_dialog(cust)

        return card

    def _on_card_checked(self, cid: int, state):
        """Add/remove a customer id from the batch selection on checkbox toggle.

        Args:
            cid: The customer id for the toggled card (0/falsy ids are ignored).
            state: Qt check state; truthy means checked.
        """
        if not cid:
            return
        if state:
            self._selected_ids.add(cid)
        else:
            self._selected_ids.discard(cid)
        self._update_selection_ui()

    def _toggle_select_all(self, state):
        """Select or deselect every currently *visible* card's checkbox.

        Only visible (search-matching) cards are affected so a filtered "Select
        All" doesn't silently select hidden rows.

        Args:
            state: Qt check state of the master checkbox; truthy = select all.
        """
        visible_cids = []
        for c, card_w in self._customer_cards:
            if card_w.isVisible():
                cid = int(c.get("id") or c.get("cus_id") or 0)
                if cid:
                    visible_cids.append(cid)

        if state:
            self._selected_ids.update(visible_cids)
        else:
            self._selected_ids.difference_update(visible_cids)

        # Sync each visible checkbox's UI state without re-firing its handler.
        for cid, cb in self._card_checkboxes.items():
            if cid in visible_cids:
                cb.blockSignals(True)
                cb.setChecked(bool(state))
                cb.blockSignals(False)

        self._update_selection_ui()

    def _update_selection_ui(self):
        """Refresh the selection count label, delete button, and select-all state.

        Recomputes whether all visible cards are selected to keep the master
        "Select All" checkbox in sync (signals blocked to avoid a feedback loop).
        """
        count = len(self._selected_ids)
        self._lbl_selected_count.setText(f"{count} selected")
        self._btn_delete_selected.setEnabled(count > 0)
        self._btn_delete_selected.setText(f"  Delete Selected ({count})" if count > 0 else "  Delete Selected")

        all_visible_cids = [int(c.get("id") or c.get("cus_id") or 0) for c, card_w in self._customer_cards if card_w.isVisible()]
        all_checked = len(all_visible_cids) > 0 and all(cid in self._selected_ids for cid in all_visible_cids)
        self._cb_select_all.blockSignals(True)
        self._cb_select_all.setChecked(all_checked)
        self._cb_select_all.blockSignals(False)

    def _delete_selected_customers(self):
        """Permission-check, confirm, and batch-delete all selected customers.

        Guards on the delete permission and a non-empty selection, asks for
        confirmation, performs the bulk delete via ``repo``, clears selection,
        reloads, emits change signals, and toasts the result.
        """
        from utils.auth import SessionManager
        if not SessionManager.has_permission("customers", "delete"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to delete customers.")
            return
        if not self._selected_ids:
            return
        count = len(self._selected_ids)
        if not confirm(self, title="Delete Multiple Customers",
                       message=f"Are you sure you want to permanently delete {count} selected customer(s)?\nThis will remove their contact history and cannot be undone.",
                       confirm_label=f"Delete {count} Customers", danger=True):
            return

        deleted = repo.delete_multiple_customers(list(self._selected_ids))
        self._selected_ids.clear()
        self.reload()
        try:
            from utils.signals import app_events
            app_events().customer_saved.emit()
            app_events().data_changed.emit()
        except Exception:
            pass
        self._show_toast("Customers Deleted", f"Successfully deleted {deleted} customer(s).")

    def _open_multi_add_dialog(self):
        """Open the bulk-add dialog (create permission required) and reload on save."""
        from utils.auth import SessionManager
        if not SessionManager.has_permission("customers", "create"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to add customers.")
            return
        dlg = AddMultipleCustomersDialog(self)
        if dlg.exec():
            self.reload()
            try:
                from utils.signals import app_events
                app_events().customer_saved.emit()
                app_events().data_changed.emit()
            except Exception:
                pass
            self._show_toast("Customers Added", f"Added {dlg._added_count} customer(s) successfully.")


    def _open_ledger(self, c):
        """Open the ledger dialog for customer ``c``; show a warning on failure."""
        try:
            dlg = CustomerLedgerDialog(self, customer=c)
            dlg.exec()
        except Exception as e:
            print(f"[CustomersPage] Error opening ledger dialog: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ledger Error", f"Unable to open customer ledger:\n{e}")

    def _delete_customer_by_ref(self, c):
        """Confirm and delete a single customer by object reference.

        Warns the user when the customer has bookings, since deleting them
        cascades to those bookings/invoices/payments (see ``sp_delete_customer``).
        Removes the row from the local mirror by identity, re-renders, emits the
        relevant change signals (including booking/invoice ones when events were
        deleted), and toasts.

        Args:
            c: The customer dict to delete.
        """
        from utils.auth import SessionManager
        if not SessionManager.has_permission("customers", "delete"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to delete customers.")
            return
        event_count = int(c.get("events") or 0)
        warning = (
            f" This will ALSO permanently delete all {event_count} of their booking(s), "
            f"including linked invoices and payment records."
            if event_count > 0 else ""
        )
        if not confirm(self, title="Delete Customer",
                       message=f"Are you sure you want to delete '{c['name']}'?{warning} This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if c.get("id"):
            repo.delete_customer(c["id"])
        # Drop by identity (is not) so a same-valued duplicate isn't also removed.
        self._customers = [x for x in self._customers if x is not c]
        if hasattr(self, "_loader"):
            self._loader.show_overlay("Updating customer records...")
        self._populate_table()
        try:
            from utils.signals import app_events
            app_events().customer_saved.emit()
            app_events().data_changed.emit()
            if event_count > 0:
                # Their bookings/invoices were also just deleted (see
                # sp_delete_customer) - refresh Orders/Billing/Calendar too.
                app_events().booking_updated.emit()
                app_events().invoice_saved.emit()
        except Exception:
            pass
        self._show_toast("Customer Deleted", "Customer deleted successfully.")

    def _open_follow_ups(self, c):
        """Open an inline follow-up/reminder manager dialog for customer ``c``.

        Builds a small self-contained dialog (locally imported widgets) that lists
        existing follow-ups with complete/delete actions and an add row. The inner
        ``_reload`` closure rebuilds the list after each mutation via ``repo``.

        Args:
            c: The customer dict whose follow-ups are managed (needs ``id``).
        """
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                       QPushButton, QLineEdit, QDateEdit, QScrollArea, QFrame)
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Follow-ups — {c['name']}")
        dlg.setMinimumWidth(460)
        dlg.setMinimumHeight(400)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(14)
        lay.setContentsMargins(20, 20, 20, 20)

        tier = c.get("loyalty_tier", "Bronze")
        head = QHBoxLayout()
        head.addWidget(QLabel(f"<b>{c['name']}</b> — {c.get('events', 0)} events"))
        head.addStretch()
        head.addWidget(_tier_badge(tier))
        lay.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setSpacing(8)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(inner)
        lay.addWidget(scroll)

        def _reload():
            # Rebuild the follow-up list from scratch after any add/complete/delete.
            while inner_lay.count():
                item = inner_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            fups = repo.get_follow_ups(c["id"]) if c.get("id") else []
            for fu in fups:
                fu_row = QHBoxLayout()
                # Checkmark for done, open circle for pending, plus date and note.
                done_cb_lbl = QLabel(("✓ " if fu["is_done"] else "○ ") + fu["date"] + " — " + fu["note"])
                # Muted color when done; otherwise pick a readable color per theme.
                _done_color = "#94A3B8" if fu["is_done"] else ("#475569" if not ThemeManager().is_dark() else "#F9FAFB")
                done_cb_lbl.setStyleSheet(f"color:{_done_color};")
                done_cb_lbl.setWordWrap(True)
                fu_row.addWidget(done_cb_lbl, 1)
                if not fu["is_done"]:
                    done_btn = QPushButton("Done")
                    done_btn.setFixedHeight(26)
                    done_btn.setStyleSheet("background:#16A34A;color:white;border:none;border-radius:5px;font-size:11px;padding:0 8px;")
                    # Mark done then rebuild the list (tuple runs both in the lambda).
                    done_btn.clicked.connect(lambda _, fid=fu["id"]: (repo.complete_follow_up(fid), _reload()))
                    fu_row.addWidget(done_btn)
                del_btn2 = QPushButton("✕")
                del_btn2.setFixedSize(24, 24)
                del_btn2.setStyleSheet("background:transparent;border:none;font-weight:700;")
                del_btn2.clicked.connect(lambda _, fid=fu["id"]: (repo.delete_follow_up(fid), _reload()))
                fu_row.addWidget(del_btn2)
                row_w = QWidget()
                row_w.setLayout(fu_row)
                inner_lay.addWidget(row_w)
            if not fups:
                empty = QLabel("No follow-ups yet.")
                empty.setStyleSheet("color:#64748B;")
                inner_lay.addWidget(empty)
            inner_lay.addStretch()

        _reload()

        add_row = QHBoxLayout()
        date_edit = QDateEdit(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("MMM dd, yyyy")
        date_edit.setFixedWidth(140)
        note_edit = QLineEdit()
        note_edit.setPlaceholderText("Note / reminder...")
        add_fu_btn = QPushButton("Add")
        add_fu_btn.setFixedHeight(30)
        add_fu_btn.setObjectName("primaryButton")

        def _add_fu():
            # Add a new follow-up; ignore empty notes or customers without an id.
            note = note_edit.text().strip()
            if not note or not c.get("id"):
                return
            date_str = date_edit.date().toString("MMM dd, yyyy")
            repo.add_follow_up(c["id"], date_str, note)
            note_edit.clear()
            _reload()

        add_fu_btn.clicked.connect(_add_fu)
        note_edit.returnPressed.connect(_add_fu)
        add_row.addWidget(date_edit)
        add_row.addWidget(note_edit)
        add_row.addWidget(add_fu_btn)
        lay.addLayout(add_row)

        dlg.exec()

    def _open_edit_dialog(self, c):
        """Open the edit dialog for ``c`` and persist changes on accept.

        Requires edit permission. On save it updates the customer row, optionally
        saves and links a new structured address, mirrors the changes back onto
        the local dict ``c`` (so the card reflects them without a full refetch),
        re-renders, emits change signals, and toasts.

        Args:
            c: The customer dict to edit (mutated in place on success).
        """
        from utils.auth import SessionManager
        if not SessionManager.has_permission("customers", "edit"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to edit customers.")
            return
        dlg = EditCustomerDialog(self, customer=c)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result and c.get("id"):
                repo.update_customer(c["id"], result)
                # If a structured address was picked, persist it and link it.
                addr_data = result.get("address_data")
                if addr_data:
                    addr_id = repo.save_address(
                        result.get("street", ""),
                        addr_data["barangay_id"],
                        addr_data["city_id"],
                        addr_data["province_id"],
                    )
                    if addr_id:
                        repo.link_customer_address(c["id"], addr_id)
                # Mirror the saved values back onto the in-memory row.
                c["name"]    = result["name"]
                c["contact"] = result["contact"]
                c["email"]   = result["email"]
                c["address"] = result["address"]
                c["status"]  = result["status"]
                if hasattr(self, "_loader"):
                    self._loader.show_overlay("Updating customer records...")
                self._populate_table()
                try:
                    from utils.signals import app_events
                    app_events().customer_saved.emit()
                    app_events().data_changed.emit()
                except Exception:
                    pass
                self._show_toast("Customer Updated", "Customer updated successfully.")

    def _open_add_dialog(self):
        """Open the single-customer add dialog and persist on accept.

        Requires create permission. Rejects a duplicate name up front, inserts
        the customer, seeds loyalty ("Bronze") and recalculates it, optionally
        saves/links a structured address, appends to the local mirror, re-renders,
        emits change signals, and toasts. Errors in loyalty/address steps are
        swallowed so they don't block the successful core insert.
        """
        from utils.auth import SessionManager
        if not SessionManager.has_permission("customers", "create"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to add customers.")
            return
        dlg = AddCustomerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                # Reject duplicate names before touching the DB.
                if repo.customer_exists(result.get("name", "")):
                    QMessageBox.warning(
                        self, "Customer Already Exists",
                        f"\"{result.get('name', '')}\" already exists — skipping this customer.",
                    )
                    return
                new_id = repo.add_customer(result)
                if new_id:
                    result["id"] = new_id
                    result["loyalty_tier"] = "Bronze"  # Everyone starts at Bronze.
                    try:
                        # Recompute tier in case rules give a higher starting tier.
                        repo.recalculate_loyalty(new_id)
                    except Exception:
                        pass
                    # Persist/link the structured address if one was selected.
                    addr_data = result.get("address_data")
                    if addr_data:
                        try:
                            addr_id = repo.save_address(
                                result.get("street", ""),
                                addr_data["barangay_id"],
                                addr_data["city_id"],
                                addr_data["province_id"],
                            )
                            if addr_id:
                                repo.link_customer_address(new_id, addr_id)
                        except Exception:
                            pass
                    self._customers.append(result)
                    if hasattr(self, "_loader"):
                        self._loader.show_overlay("Updating customer records...")
                    self._populate_table()
                    try:
                        from utils.signals import app_events
                        app_events().customer_saved.emit()
                        app_events().data_changed.emit()
                    except Exception:
                        pass
                    self._show_toast("Customer Added", "Customer added successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to save customer to database.")

    def _filter_table(self, _text=""):
        """Debounced entry point for filtering (restart the 500ms search timer)."""
        if hasattr(self, "_search_timer"):
            self._search_timer.start(500)
        else:
            self._filter_table_now()

    def _has_active_search(self) -> bool:
        """Return True if the search box currently holds a non-blank query."""
        try:
            return bool(self._search.text().strip())
        except Exception:
            return False

    def _filter_table_now(self):
        """Apply the current search query by showing/hiding already-rendered cards.

        Filtering is client-side (no re-render): each card's name label is
        re-highlighted and its visibility is set based on a substring match across
        name/email/contact/address. If the search just cleared while a background
        refresh was deferred, that deferred reload runs now instead.
        """
        raw_q = self._search.text() if hasattr(self, "_search") else ""
        q = raw_q.strip().lower()
        # Search just cleared while a background refresh was deferred -> reload once.
        if not q and getattr(self, "_reload_deferred", False):
            self._reload_deferred = False
            if self.isVisible():
                self._do_reload()
                return
        visible_count = 0
        for c, card_w in getattr(self, "_customer_cards", []):
            # Live-highlight the name to match what's typed.
            lbl = getattr(card_w, "_name_lbl", None)
            if lbl is not None:
                lbl.setText(highlight_html(getattr(card_w, "_cust_name", c.get("name", "")), raw_q))
            if not q:
                card_w.show()
                visible_count += 1
            else:
                match = (
                    q in str(c.get("name") or "").lower() or
                    q in str(c.get("email") or "").lower() or
                    q in str(c.get("contact") or "").lower() or
                    q in str(c.get("address") or "").lower()
                )
                card_w.setVisible(match)
                if match:
                    visible_count += 1
        # Show the empty label only when a non-empty dataset filtered down to zero
        # visible matches (not when there simply are no customers at all).
        if hasattr(self, "_empty_lbl") and self._empty_lbl:
            self._empty_lbl.setVisible(visible_count == 0 and len(getattr(self, "_customers", [])) > 0)

    def filter_search(self, text):
        """Public hook (e.g. from a global search) to set the page's search text."""
        self._search.setText(text)

    def _export_csv(self):
        """Open the export wizard dialog for exporting customer data."""
        from components.export_dialog import ExportWizardDialog
        dlg = ExportWizardDialog(parent=self)
        dlg.exec()

    def _open_import_dialog(self):
        """Open the import wizard (create permission required); reload on success."""
        from utils.auth import SessionManager
        if not SessionManager.has_permission("customers", "create"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to import customers.")
            return
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="customers", parent=self)
        if dlg.exec():
            self.reload()