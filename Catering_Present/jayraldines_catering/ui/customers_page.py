from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QSizePolicy, QTextEdit, QScrollArea,
    QCheckBox, QMessageBox, QCompleter
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor
from components.address_search import AddressSearchWidget
from utils.data_loader import run_async


def _format_phone_input(text: str) -> str:
    digits = "".join(c for c in text if c.isdigit())[:10]
    if len(digits) <= 3:
        return digits
    elif len(digits) <= 6:
        return f"{digits[:3]} {digits[3:]}"
    elif len(digits) <= 10:
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return f"{digits[:3]} {digits[3:6]} {digits[6:10]}"


def _format_contact_preserving_cursor(line_edit: QLineEdit):
    text = line_edit.text()
    cursor_pos = line_edit.cursorPosition()
    digits_before = sum(1 for c in text[:cursor_pos] if c.isdigit())
    
    formatted = _format_phone_input(text)
    if formatted != text:
        line_edit.blockSignals(True)
        line_edit.setText(formatted)
        new_pos = 0
        counted_digits = 0
        for i, ch in enumerate(formatted):
            if ch.isdigit():
                counted_digits += 1
            if counted_digits == digits_before:
                new_pos = i + 1
                break
        else:
            new_pos = len(formatted)
        line_edit.setCursorPosition(new_pos)
        line_edit.blockSignals(False)


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
from components.dialogs import confirm, success
import utils.repository as repo



class AddCustomerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Customer")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 580)
        self.setModal(True)
        self._result = None
        self._build_ui()

    def _build_ui(self):
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
        for code, label in _COUNTRY_CODES:
            self.country_code_combo.addItem(label, code)
        self.country_code_combo.setCurrentIndex(0)
        self.contact_field = QLineEdit()
        self.contact_field.setPlaceholderText("9XX XXX XXXX")
        self.contact_field.setFixedHeight(38)
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
            addr_str = street
        self._result = {
            "name":         name,
            "contact":      contact,
            "email":        self.email_field.text().strip(),
            "address":      addr_str,
            "address_data": sel,
            "street":       street,
            "events":       0,
            "status":       self.status_field.currentText(),
        }
        self.accept()

    def _auto_format_contact(self, _text):
        _format_contact_preserving_cursor(self.contact_field)

    def get_result(self):
        return self._result


class EditCustomerDialog(QDialog):
    def __init__(self, parent=None, customer=None):
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
            if code == matched_code:
                self.country_code_combo.setCurrentIndex(self.country_code_combo.count() - 1)
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

        self._existing_addr = self._customer.get("address", "")
        self.address_widget = AddressSearchWidget()

        self.status_field = QComboBox()
        self.status_field.setFixedHeight(38)
        self.status_field.addItems(["Active", "Pending", "Inactive"])
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
        _format_contact_preserving_cursor(self.contact_field)

    def _save(self):
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
        return self._result


_TIER_COLORS = {
    "Bronze": ("#CD7F32", "rgba(205,127,50,.15)"),
    "Silver": ("#C0C0C0", "rgba(192,192,192,.15)"),
    "Gold":   ("#F59E0B", "rgba(245,158,11,.15)"),
    "VIP":    ("#A855F7", "rgba(168,85,247,.15)"),
}


def _tier_badge(tier: str) -> QLabel:
    color, bg = _TIER_COLORS.get(tier, ("#9CA3AF", "rgba(156,163,175,.15)"))
    lbl = QLabel(tier)
    lbl.setStyleSheet(
        f"font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;"
        f"background:{bg};color:{color};border:1px solid {color};"
    )
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


class CustomerLedgerDialog(QDialog):
    def __init__(self, parent=None, customer=None):
        super().__init__(parent)
        self._customer = customer or {}
        self._drag_pos = None
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
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def _build_ui(self):
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

        entries = []
        cid = cust.get("id") or cust.get("cus_id")
        if cid:
            try:
                import utils.repository as _repo
                entries = _repo.get_customer_ledger(cid) or []
            except Exception as e:
                print(f"[CustomerLedgerDialog] Error loading ledger for customer {cid}: {e}")
                entries = []

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

        balance = total_debit - total_credit

        summary_row = QHBoxLayout()
        summary_row.setSpacing(16)
        for lbl, val, color in [
            ("Total Charged", f"₱ {total_debit:,.2f}",  "#E11D48"),
            ("Total Paid",    f"₱ {total_credit:,.2f}", "#22C55E"),
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Multiple Customers")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(860, 540)
        self.setModal(True)
        self._added_count = 0
        self._build_ui()

    def _build_ui(self):
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
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0F172A;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                gridline-color: rgba(255,255,255,0.06);
                font-size: 13px;
                color: #F9FAFB;
            }
            QTableWidget::item {
                padding: 4px 6px;
                color: #F9FAFB;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            QTableWidget::item:selected {
                background-color: rgba(225,29,72,0.25);
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #111827;
                color: #9CA3AF;
                font-weight: 700;
                font-size: 11px;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
        """)

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
        r = self.table.rowCount()
        self.table.insertRow(r)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Customer / Company Name *")
        name_edit.setFixedHeight(34)
        name_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 0, name_edit)

        contact_edit = QLineEdit()
        contact_edit.setPlaceholderText("09171234567")
        contact_edit.setFixedHeight(34)
        contact_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 1, contact_edit)

        email_edit = QLineEdit()
        email_edit.setPlaceholderText("client@example.com")
        email_edit.setFixedHeight(34)
        email_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 2, email_edit)

        addr_combo = QComboBox()
        addr_combo.setEditable(True)
        addr_combo.addItems(_CEBU_ADDRESS_OPTIONS)
        addr_combo.setFixedHeight(34)
        completer = QCompleter(_CEBU_ADDRESS_OPTIONS[1:], addr_combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        addr_combo.setCompleter(completer)
        addr_combo.setStyleSheet("""
            QComboBox {
                background: #1E293B;
                color: #FFFFFF;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QComboBox:focus { border-color: #E11D48; }
            QComboBox QAbstractItemView {
                background: #1E293B;
                color: #FFFFFF;
                selection-background-color: #E11D48;
                selection-color: #FFFFFF;
                border: 1px solid #334155;
            }
        """)
        self.table.setCellWidget(r, 3, addr_combo)

    def _delete_selected_row(self):
        curr = self.table.currentRow()
        if curr >= 0:
            self.table.removeRow(curr)

    def _save_all(self):
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
                continue
            if not name:
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
        for data in rows_to_save:
            res = repo.add_customer(data)
            if res:
                saved += 1

        self._added_count = saved
        self.accept()


class CustomersPage(QWidget):
    def __init__(self):
        super().__init__()
        self._dirty = True
        self._customers = []
        self._selected_ids: set[int] = set()
        self._card_checkboxes: dict[int, QCheckBox] = {}
        self._build_ui()
        self._do_reload()

        try:
            from utils.signals import app_events
            app_events().customer_saved.connect(self._mark_dirty_and_reload)
            app_events().booking_saved.connect(self._mark_dirty_and_reload)
            app_events().data_changed.connect(self._mark_dirty)
        except Exception:
            pass

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self._do_reload()

    def _mark_dirty(self):
        self._dirty = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._dirty:
            self._do_reload()

    def reload(self):
        self._mark_dirty()
        if self.isVisible():
            self._do_reload()

    def _do_reload(self):
        self._dirty = False
        run_async(self, repo.get_all_customers_with_loyalty, self._on_customers_loaded)

    def _on_customers_loaded(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        rows = data or []
        if not rows:
            rows = repo.get_all_customers() or []
        self._customers = rows
        self._selected_ids.clear()
        self._populate_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Customers")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("  Add Customer")
        add_btn.setObjectName("primaryButton")
        add_btn.setIcon(btn_icon_primary("plus"))
        add_btn.setIconSize(QSize(15, 15))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._open_add_dialog)
        header.addWidget(add_btn)

        multi_add_btn = QPushButton("  + Quick Multi-Add")
        multi_add_btn.setObjectName("secondaryButton")
        multi_add_btn.setCursor(Qt.PointingHandCursor)
        multi_add_btn.clicked.connect(self._open_multi_add_dialog)
        header.addWidget(multi_add_btn)

        import_btn = QPushButton("  Import")
        import_btn.setObjectName("secondaryButton")
        import_btn.setIcon(btn_icon_secondary("export"))
        import_btn.setIconSize(QSize(15, 15))
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._open_import_dialog)
        header.addWidget(import_btn)

        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.clicked.connect(self._export_csv)
        header.addWidget(export_btn)

        root.addLayout(header)

        # Search Bar
        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setPlaceholderText("Search customers...")
        self._search.setFixedHeight(38)
        self._search.setMaximumWidth(320)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._filter_table_now)
        self._search.textChanged.connect(lambda: self._search_timer.start(120))
        root.addWidget(self._search)

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
        card_layout.addWidget(self.scroll_area)
        root.addWidget(card)

    def _populate_table(self, customers=None):
        if hasattr(self, "cards_container"):
            self.cards_container.setUpdatesEnabled(False)
        try:
            self._card_checkboxes.clear()
            for _, card_w in self._customer_cards:
                self.cards_layout.removeWidget(card_w)
                card_w.hide()
                card_w.deleteLater()
            self._customer_cards.clear()

            while self.cards_layout.count() > 1:
                item = self.cards_layout.takeAt(1)
                if item.widget() and item.widget() != self._empty_lbl:
                    item.widget().deleteLater()

            data = customers if customers is not None else self._customers

            if not data:
                self._empty_lbl.show()
            else:
                self._empty_lbl.hide()
                for c in data:
                    c_card = self._create_customer_card(c)
                    self.cards_layout.addWidget(c_card)
                    self._customer_cards.append((c, c_card))

            self.cards_layout.addStretch()
            self._update_selection_ui()
            self._filter_table_now()
        finally:
            if hasattr(self, "cards_container"):
                self.cards_container.setUpdatesEnabled(True)

    def _create_customer_card(self, c: dict) -> QFrame:
        cid = int(c.get("id") or c.get("cus_id") or 0)
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 14, 18, 14)
        lay.setSpacing(14)

        # Col 0: Checkbox
        cb = QCheckBox()
        cb.setChecked(cid in self._selected_ids)
        cb.stateChanged.connect(lambda state, cust_id=cid: self._on_card_checked(cust_id, state))
        self._card_checkboxes[cid] = cb
        lay.addWidget(cb, alignment=Qt.AlignVCenter)

        # Col 1: Customer Name, Contact, Email
        c1 = QVBoxLayout()
        c1.setSpacing(2)
        name_lbl = QLabel(c["name"])
        name_lbl.setStyleSheet("font-weight: 700; font-size: 15px;")
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
        actions_w = QFrame()
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(13, 13)))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setFixedSize(30, 30)
        edit_btn.setToolTip("Edit customer")
        edit_btn.setStyleSheet("background: transparent; border: none;")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.clicked.connect(lambda _, cust=c: self._open_edit_dialog(cust))

        ledger_btn = QPushButton()
        ledger_btn.setIcon(get_icon("reports", color="#3B82F6", size=QSize(13, 13)))
        ledger_btn.setIconSize(QSize(13, 13))
        ledger_btn.setFixedSize(30, 30)
        ledger_btn.setToolTip("View ledger")
        ledger_btn.setStyleSheet("background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.3);border-radius:6px;")
        ledger_btn.setCursor(Qt.PointingHandCursor)
        ledger_btn.clicked.connect(lambda _, cust=c: self._open_ledger(cust))

        fu_btn = QPushButton()
        fu_btn.setIcon(get_icon("bell", color="#F59E0B", size=QSize(13, 13)))
        fu_btn.setIconSize(QSize(13, 13))
        fu_btn.setFixedSize(30, 30)
        fu_btn.setToolTip("Follow-up reminders")
        fu_btn.setStyleSheet("background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:6px;")
        fu_btn.setCursor(Qt.PointingHandCursor)
        fu_btn.clicked.connect(lambda _, cust=c: self._open_follow_ups(cust))

        del_btn = QPushButton()
        del_btn.setIcon(btn_icon_red("trash"))
        del_btn.setIconSize(QSize(13, 13))
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("background: transparent; border: none;")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(lambda _, cust=c: self._delete_customer_by_ref(cust))

        actions_l.addWidget(edit_btn)
        actions_l.addWidget(ledger_btn)
        actions_l.addWidget(fu_btn)
        actions_l.addWidget(del_btn)

        lay.addWidget(actions_w)

        return card

    def _on_card_checked(self, cid: int, state):
        if not cid:
            return
        if state:
            self._selected_ids.add(cid)
        else:
            self._selected_ids.discard(cid)
        self._update_selection_ui()

    def _toggle_select_all(self, state):
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

        for cid, cb in self._card_checkboxes.items():
            if cid in visible_cids:
                cb.blockSignals(True)
                cb.setChecked(bool(state))
                cb.blockSignals(False)

        self._update_selection_ui()

    def _update_selection_ui(self):
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
        success(self, message=f"Successfully deleted {deleted} customer(s).")

    def _open_multi_add_dialog(self):
        dlg = AddMultipleCustomersDialog(self)
        if dlg.exec():
            self.reload()
            try:
                from utils.signals import app_events
                app_events().customer_saved.emit()
                app_events().data_changed.emit()
            except Exception:
                pass
            success(self, message=f"Added {dlg._added_count} customer(s) successfully.")


    def _open_ledger(self, c):
        try:
            dlg = CustomerLedgerDialog(self, customer=c)
            dlg.exec()
        except Exception as e:
            print(f"[CustomersPage] Error opening ledger dialog: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ledger Error", f"Unable to open customer ledger:\n{e}")

    def _delete_customer_by_ref(self, c):
        if not confirm(self, title="Delete Customer",
                       message=f"Are you sure you want to delete '{c['name']}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if c.get("id"):
            repo.delete_customer(c["id"])
        self._customers = [x for x in self._customers if x is not c]
        self._populate_table()
        try:
            from utils.signals import app_events
            app_events().customer_saved.emit()
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message="Customer deleted successfully.")

    def _open_follow_ups(self, c):
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
            while inner_lay.count():
                item = inner_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            fups = repo.get_follow_ups(c["id"]) if c.get("id") else []
            for fu in fups:
                fu_row = QHBoxLayout()
                done_cb_lbl = QLabel(("✓ " if fu["is_done"] else "○ ") + fu["date"] + " — " + fu["note"])
                _done_color = "#94A3B8" if fu["is_done"] else ("#475569" if not ThemeManager().is_dark() else "#F9FAFB")
                done_cb_lbl.setStyleSheet(f"color:{_done_color};")
                done_cb_lbl.setWordWrap(True)
                fu_row.addWidget(done_cb_lbl, 1)
                if not fu["is_done"]:
                    done_btn = QPushButton("Done")
                    done_btn.setFixedHeight(26)
                    done_btn.setStyleSheet("background:#16A34A;color:white;border:none;border-radius:5px;font-size:11px;padding:0 8px;")
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
        dlg = EditCustomerDialog(self, customer=c)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result and c.get("id"):
                repo.update_customer(c["id"], result)
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
                c["name"]    = result["name"]
                c["contact"] = result["contact"]
                c["email"]   = result["email"]
                c["address"] = result["address"]
                c["status"]  = result["status"]
                self._populate_table()
                try:
                    from utils.signals import app_events
                    app_events().customer_saved.emit()
                    app_events().data_changed.emit()
                except Exception:
                    pass
                success(self, message="Customer updated successfully.")

    def _open_add_dialog(self):
        dlg = AddCustomerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                new_id = repo.add_customer(result)
                if new_id:
                    result["id"] = new_id
                    result["loyalty_tier"] = "Bronze"
                    try:
                        repo.recalculate_loyalty(new_id)
                    except Exception:
                        pass
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
                    self._populate_table()
                    try:
                        from utils.signals import app_events
                        app_events().customer_saved.emit()
                        app_events().data_changed.emit()
                    except Exception:
                        pass
                    success(self, message="Customer added successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to save customer to database.")

    def _filter_table(self, _text=""):
        if hasattr(self, "_search_timer"):
            self._search_timer.start(120)
        else:
            self._filter_table_now()

    def _filter_table_now(self):
        q = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        visible_count = 0
        for c, card_w in getattr(self, "_customer_cards", []):
            if not q:
                card_w.show()
                visible_count += 1
            else:
                match = (
                    q in c.get("name", "").lower() or
                    q in c.get("email", "").lower() or
                    q in c.get("contact", "").lower() or
                    q in c.get("address", "").lower()
                )
                card_w.setVisible(match)
                if match:
                    visible_count += 1
        if hasattr(self, "_empty_lbl") and self._empty_lbl:
            self._empty_lbl.setVisible(visible_count == 0 and len(getattr(self, "_customers", [])) > 0)

    def filter_search(self, text):
        self._search.setText(text)

    def _export_csv(self):
        import csv
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "Export Customers", "customers.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Contact", "Email", "Total Events", "Status"])
            for c in self._customers:
                writer.writerow([
                    c.get("name", ""), c.get("contact", ""),
                    c.get("email", ""), c.get("events", 0), c.get("status", ""),
                ])
        QMessageBox.information(self, "Export", f"Exported to:\n{path}")

    def _open_import_dialog(self):
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="customers", parent=self)
        if dlg.exec():
            self.reload()