import csv
import os
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox,
    QFileDialog, QMessageBox, QDateEdit, QScrollArea
)
from PySide6.QtCore import Qt, QSize, QDate
from datetime import date as _date_type
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success, prompt_file_saved
import utils.repository as repo
import utils.exporter as exporter
from utils.session import get_actor
from utils.signals import app_events
from utils.data_loader import run_async


_STATUS_COLORS = {"Paid": "#22C55E", "Partial": "#F59E0B", "Unpaid": "#EF4444"}
_STATUSES = ["Unpaid", "Partial", "Paid"]
_METHODS = ["Cash", "GCash", "Maya", "Bank Transfer", "Credit Card", "Cheque", "Other"]


def _fmt_date(val) -> str:
    if isinstance(val, _date_type):
        return val.strftime("%b %d, %Y")
    s = str(val)
    q = QDate.fromString(s, "yyyy-MM-dd")
    if q.isValid():
        return q.toString("MMM dd, yyyy")
    q2 = QDate.fromString(s, "MMM dd, yyyy")
    if q2.isValid():
        return q2.toString("MMM dd, yyyy")
    return s


class RecordPaymentDialog(QDialog):
    def __init__(self, parent=None, inv: dict = None):
        super().__init__(parent)
        self._inv = inv or {}
        self._pay_info = None
        self.setWindowTitle("Record Payment")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)
        self.setModal(True)
        self._result = None

        if self._inv.get("booking_id"):
            try:
                self._pay_info = repo.get_invoice_payment_info(self._inv["booking_id"])
            except Exception:
                self._pay_info = None

        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Record Payment")
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

        pi = self._pay_info
        if pi:
            total     = pi["total"]
            paid      = pi["paid"]
            remaining = pi["remaining"]
            req       = pi["required_payment"]
            min_pct   = pi["min_pct"]
            is_first  = paid == 0
            req_label = (
                f"Required downpayment ({min_pct:.0f}%): <b style='color:#F59E0B;'>₱ {req:,.2f}</b>"
                if is_first and not pi["allow_zero"]
                else f"Amount due: <b style='color:#E11D48;'>₱ {remaining:,.2f}</b>"
            )
            summary_html = (
                f"<b>{self._inv.get('invoice', '')}</b> — {self._inv.get('customer', '')}<br>"
                f"Total: <b>₱ {total:,.2f}</b> &nbsp;|&nbsp; "
                f"Paid: <b>₱ {paid:,.2f}</b> &nbsp;|&nbsp; "
                f"Balance: <b style='color:#E11D48;'>₱ {remaining:,.2f}</b><br>"
                f"{req_label}"
            )
            max_amount = remaining
            default_amount = req if req > 0 else remaining
        else:
            balance = float(self._inv.get("amount", 0)) - float(self._inv.get("paid", 0))
            summary_html = (
                f"<b>{self._inv.get('invoice', '')}</b> — {self._inv.get('customer', '')}<br>"
                f"Balance due: <span style='color:#E11D48;font-weight:700;'>₱ {balance:,.2f}</span>"
            )
            max_amount = balance
            default_amount = balance

        info = QLabel(summary_html)
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        info.setStyleSheet("font-size:13px; padding:8px 0;")
        lay.addWidget(info)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self._amount_f = QDoubleSpinBox()
        self._amount_f.setPrefix("₱ ")
        self._amount_f.setRange(0.01, max(max_amount, 0.01))
        self._amount_f.setValue(max(default_amount, 0.01))
        self._amount_f.setDecimals(2)
        self._amount_f.setSingleStep(1000)
        self._amount_f.setFixedHeight(38)

        self._date_f = QDateEdit()
        self._date_f.setCalendarPopup(True)
        self._date_f.setDisplayFormat("MMM dd, yyyy")
        self._date_f.setDate(QDate.currentDate())
        self._date_f.setFixedHeight(38)

        self._method_f = QComboBox()
        self._method_f.addItems(_METHODS)
        self._method_f.setFixedHeight(38)

        self._note_f = QLineEdit()
        self._note_f.setPlaceholderText("Optional note...")
        self._note_f.setFixedHeight(38)

        for lbl, widget in [
            ("Amount *",       self._amount_f),
            ("Payment Date *", self._date_f),
            ("Method",         self._method_f),
            ("Note",           self._note_f),
        ]:
            form.addRow(QLabel(lbl), widget)

        lay.addLayout(form)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #E11D48; font-size: 12px;")
        self._err.setWordWrap(True)
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        save = QPushButton("  Record Payment")
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
        amount = self._amount_f.value()
        if amount <= 0:
            self._err.setText("Amount must be greater than 0.")
            self._err.show()
            return
        self._result = {
            "amount":       amount,
            "payment_date": self._date_f.date().toString("yyyy-MM-dd"),
            "method":       self._method_f.currentText(),
            "note":         self._note_f.text().strip(),
        }
        self.accept()

    def get_result(self):
        return self._result


class EditBillingDialog(QDialog):
    """Allows editing payment-related values on an invoice (Amount Paid and Balance)
    to correct manual encoding mistakes as requested.
    """
    def __init__(self, parent=None, inv: dict = None):
        super().__init__(parent)
        self._inv = inv or {}
        self.setWindowTitle("Edit Billing Payment")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel(f"Edit Payment — {self._inv.get('invoice', 'Invoice')}")
        title.setObjectName("h3")
        sub = QLabel(f"Customer: {self._inv.get('customer', 'Valued Client')}")
        sub.setObjectName("subtitle")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        header.addLayout(title_col)
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
        form.setLabelAlignment(Qt.AlignLeft)

        self._total_val = float(self._inv.get("amount") or 0.0)
        curr_paid = float(self._inv.get("paid") or 0.0)
        curr_bal = float(self._inv.get("balance") if self._inv.get("balance") is not None else max(0.0, self._total_val - curr_paid))

        # Total Amount (Read-only reference)
        lbl_tot = QLabel(f"₱ {self._total_val:,.2f}")
        lbl_tot.setStyleSheet("font-weight: 800; font-size: 15px; color: #D97706;")
        form.addRow(QLabel("Total Amount"), lbl_tot)

        # 1. Paid Amount (Editable)
        self._paid_spin = QDoubleSpinBox()
        self._paid_spin.setRange(0, 9999999)
        self._paid_spin.setPrefix("₱ ")
        self._paid_spin.setDecimals(2)
        self._paid_spin.setSingleStep(500)
        self._paid_spin.setValue(curr_paid)
        self._paid_spin.setFixedHeight(38)

        # 2. Balance Due (Editable)
        self._bal_spin = QDoubleSpinBox()
        self._bal_spin.setRange(0, 9999999)
        self._bal_spin.setPrefix("₱ ")
        self._bal_spin.setDecimals(2)
        self._bal_spin.setSingleStep(500)
        self._bal_spin.setValue(curr_bal)
        self._bal_spin.setFixedHeight(38)

        self._updating = False

        def _on_paid_changed(val):
            if self._updating:
                return
            self._updating = True
            new_bal = max(0.0, self._total_val - val)
            self._bal_spin.setValue(new_bal)
            self._updating = False

        def _on_bal_changed(val):
            if self._updating:
                return
            self._updating = True
            new_paid = max(0.0, self._total_val - val)
            self._paid_spin.setValue(new_paid)
            self._updating = False

        self._paid_spin.valueChanged.connect(_on_paid_changed)
        self._bal_spin.valueChanged.connect(_on_bal_changed)

        form.addRow(QLabel("Amount Paid (₱) *"), self._paid_spin)
        form.addRow(QLabel("Remaining Balance (₱) *"), self._bal_spin)

        lay.addLayout(form)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #E11D48; font-size: 12px;")
        self._err.setWordWrap(True)
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

    def _save(self):
        new_paid = self._paid_spin.value()
        new_bal = self._bal_spin.value()

        if new_paid < 0 or new_bal < 0:
            self._err.setText("Values cannot be negative.")
            self._err.show()
            return

        db_id = self._inv.get("db_id")
        if not db_id:
            self._err.setText("Invoice database ID not found.")
            self._err.show()
            return

        ok = repo.update_invoice_payment(db_id, new_paid, new_bal)
        if ok:
            self.accept()
        else:
            self._err.setText("Failed to save changes to database.")
            self._err.show()


class PaymentHistoryDialog(QDialog):
    def __init__(self, parent=None, inv: dict = None):
        super().__init__(parent)
        self._inv = inv or {}
        self.setWindowTitle("Payment History")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(560)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(f"Payment History — {self._inv.get('invoice', '')}")
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

        records = []
        if self._inv.get("db_id"):
            try:
                records = repo.get_payment_records(self._inv["db_id"])
            except Exception:
                records = []

        # Scrollable Cards List for Payment History
        p_scroll = QScrollArea()
        p_scroll.setWidgetResizable(True)
        p_scroll.setFrameShape(QFrame.NoFrame)
        p_scroll.setStyleSheet("background: transparent;")
        p_scroll.setMinimumHeight(200)

        p_container = QWidget()
        p_container.setStyleSheet("background: transparent;")
        p_lay = QVBoxLayout(p_container)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(8)

        if records:
            for r in records:
                p_card = QFrame()
                p_card.setObjectName("entryCard")
                pl = QHBoxLayout(p_card)
                pl.setContentsMargins(12, 10, 12, 10)
                pl.setSpacing(14)

                c1 = QVBoxLayout()
                c1.setSpacing(2)
                d_lbl = QLabel(r["payment_date"])
                d_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
                m_lbl = QLabel(f"Method: {r['method']}")
                m_lbl.setObjectName("subtitle")
                c1.addWidget(d_lbl)
                c1.addWidget(m_lbl)
                pl.addLayout(c1, 2)

                note_text = r.get("note", "") or "—"
                note_lbl = QLabel(f"Note: {note_text}")
                note_lbl.setObjectName("subtitle")
                pl.addWidget(note_lbl, 3)

                amt_lbl = QLabel(f"₱ {r['amount']:,.2f}")
                amt_lbl.setStyleSheet("font-weight: 800; font-size: 14px; color: #22C55E;")
                amt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                pl.addWidget(amt_lbl, 2)

                p_lay.addWidget(p_card)
        else:
            empty_card = QFrame()
            empty_card.setObjectName("entryCard")
            el = QVBoxLayout(empty_card)
            item = QLabel("No payment records found.")
            item.setObjectName("subtitle")
            item.setAlignment(Qt.AlignCenter)
            el.addWidget(item)
            p_lay.addWidget(empty_card)

        p_lay.addStretch()
        p_scroll.setWidget(p_container)
        lay.addWidget(p_scroll)

        close = QPushButton("Close")
        close.setObjectName("secondaryButton")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        lay.addWidget(close, alignment=Qt.AlignRight)

        outer.addWidget(container)


class BillingPage(QWidget):
    def __init__(self):
        super().__init__()
        db_rows = repo.get_all_invoices()
        self._invoices = db_rows if db_rows else []
        self._build_ui()
        self._populate_table()
        app_events().payment_recorded.connect(self.reload)
        app_events().booking_updated.connect(self.reload)
        app_events().booking_created.connect(self.reload)

    def reload(self):
        run_async(self, repo.get_all_invoices, self._on_invoices_loaded)

    def _on_invoices_loaded(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        new_rows = data or []
        old_sig = [(i.get("db_id"), i.get("paid"), i.get("status")) for i in self._invoices]
        new_sig = [(i.get("db_id"), i.get("paid"), i.get("status")) for i in new_rows]
        if old_sig == new_sig:
            return
        self._invoices = new_rows
        self._populate_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Billing")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.clicked.connect(self.export_csv)
        header.addWidget(export_btn)

        root.addLayout(header)

        # Down Payment Tracking Summary Cards
        self._dp_summary_box = QFrame()
        self._dp_summary_box.setObjectName("card")
        dp_lay = QHBoxLayout(self._dp_summary_box)
        dp_lay.setContentsMargins(20, 16, 20, 16)
        dp_lay.setSpacing(24)

        # Total Payments / DP Received
        dp1 = QVBoxLayout()
        dp1.setSpacing(4)
        dp1_lbl = QLabel("TOTAL PAYMENTS RECEIVED")
        dp1_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF;")
        self._dp1_val = QLabel("₱ 0.00")
        self._dp1_val.setStyleSheet("font-size: 20px; font-weight: 800; color: #22C55E;")
        dp1.addWidget(dp1_lbl)
        dp1.addWidget(self._dp1_val)
        dp_lay.addLayout(dp1)

        # Pending Balance
        dp2 = QVBoxLayout()
        dp2.setSpacing(4)
        dp2_lbl = QLabel("PENDING BALANCE / UNPAID")
        dp2_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF;")
        self._dp2_val = QLabel("₱ 0.00")
        self._dp2_val.setStyleSheet("font-size: 20px; font-weight: 800; color: #F59E0B;")
        dp2.addWidget(dp2_lbl)
        dp2.addWidget(self._dp2_val)
        dp_lay.addLayout(dp2)

        # Active Billing Events
        dp3 = QVBoxLayout()
        dp3.setSpacing(4)
        dp3_lbl = QLabel("ACTIVE / UPCOMING EVENTS")
        dp3_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF;")
        self._dp3_val = QLabel("0 Events")
        self._dp3_val.setStyleSheet("font-size: 20px; font-weight: 800; color: #38BDF8;")
        dp3.addWidget(dp3_lbl)
        dp3.addWidget(self._dp3_val)
        dp_lay.addLayout(dp3)

        root.addWidget(self._dp_summary_box)

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

        self.scroll_area.setWidget(self.cards_container)
        root.addWidget(self.scroll_area)

    def _populate_table(self):
        # Refresh Billing summary metrics directly from active invoice records
        try:
            if self._invoices:
                total_rcv = sum(float(i.get("paid", 0.0) or 0.0) for i in self._invoices)
                total_pending = sum(max(0.0, float(i.get("amount", 0.0) or 0.0) - float(i.get("paid", 0.0) or 0.0)) for i in self._invoices if i.get("status") != "Paid")
                events_cnt = len(self._invoices)
            else:
                total_rcv = 0.0
                total_pending = 0.0
                events_cnt = 0

            if hasattr(self, "_dp1_val"):
                self._dp1_val.setText(f"₱ {total_rcv:,.2f}")
            if hasattr(self, "_dp2_val"):
                self._dp2_val.setText(f"₱ {total_pending:,.2f}")
            if hasattr(self, "_dp3_val"):
                self._dp3_val.setText(f"{events_cnt} Event{'s' if events_cnt != 1 else ''}")
        except Exception:
            pass

        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._invoices:
            empty_lbl = QLabel("No invoices found.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_layout.addWidget(empty_lbl)
        else:
            for inv in self._invoices:
                i_card = self._create_invoice_card(inv)
                self.cards_layout.addWidget(i_card)

        self.cards_layout.addStretch()

    def _create_invoice_card(self, inv: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(16)

        # Col 1: Invoice #, Customer, Event Date
        c1 = QVBoxLayout()
        c1.setSpacing(2)
        inv_lbl = QLabel(inv.get("invoice", ""))
        inv_lbl.setStyleSheet("font-weight: 800; font-size: 13px; color: #E11D48;")
        cust_lbl = QLabel(inv.get("customer", ""))
        cust_lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
        date_lbl = QLabel(f"Event: {_fmt_date(inv.get('event_date', ''))}")
        date_lbl.setObjectName("subtitle")
        c1.addWidget(inv_lbl)
        c1.addWidget(cust_lbl)
        c1.addWidget(date_lbl)
        lay.addLayout(c1, 3)

        # Col 2: Total, Down Payment, Paid, Balance
        total = float(inv.get("amount", 0))
        paid  = float(inv.get("paid", 0))
        down  = float(inv.get("down_payment") or 0.0)
        bal   = max(0.0, total - paid)
        is_verified = bool(inv.get("is_verified", True))

        c2 = QHBoxLayout()
        c2.setSpacing(14)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        t_title = QLabel("TOTAL")
        t_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #6B7280;")
        t_val = QLabel(f"₱{total:,.2f}")
        t_val.setStyleSheet("font-weight: 700; font-size: 13px;")
        t_box.addWidget(t_title)
        t_box.addWidget(t_val)
        c2.addLayout(t_box)

        if down > 0:
            dp_box = QVBoxLayout()
            dp_box.setSpacing(2)
            dp_title = QLabel("DOWN PAYMENT")
            dp_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #38BDF8;")
            dp_val = QLabel(f"₱{down:,.2f}")
            dp_val.setStyleSheet("font-weight: 700; font-size: 13px; color: #38BDF8;")
            dp_box.addWidget(dp_title)
            dp_box.addWidget(dp_val)
            c2.addLayout(dp_box)

        p_box = QVBoxLayout()
        p_box.setSpacing(2)
        p_title = QLabel("PAID")
        p_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #6B7280;")
        p_val = QLabel(f"₱{paid:,.2f}")
        p_val.setStyleSheet("font-weight: 700; font-size: 13px; color: #22C55E;")
        p_box.addWidget(p_title)
        p_box.addWidget(p_val)
        c2.addLayout(p_box)

        b_box = QVBoxLayout()
        b_box.setSpacing(2)
        b_title = QLabel("BALANCE")
        b_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #6B7280;")
        b_val = QLabel(f"₱{bal:,.2f}")
        b_color = "#EF4444" if bal > 0 else "#22C55E"
        b_val.setStyleSheet(f"font-weight: 800; font-size: 14px; color: {b_color};")
        b_box.addWidget(b_title)
        b_box.addWidget(b_val)
        c2.addLayout(b_box)

        lay.addLayout(c2, 4)

        # Col 3: Status & Verification badge
        col_status = QVBoxLayout()
        col_status.setSpacing(4)
        status = inv.get("status", "")
        s_color = _STATUS_COLORS.get(status, "#9CA3AF")
        status_lbl = QLabel(status)
        status_lbl.setStyleSheet(f"font-weight: 700; font-size: 11px; color: {s_color}; padding: 3px 8px; background: rgba(255,255,255,0.05); border-radius: 6px;")
        col_status.addWidget(status_lbl)

        if not is_verified and paid > 0:
            unver_lbl = QLabel("Unverified")
            unver_lbl.setStyleSheet("font-weight: 700; font-size: 10px; color: #F59E0B; padding: 2px 6px; background: rgba(245,158,11,0.15); border-radius: 4px;")
            col_status.addWidget(unver_lbl)

        lay.addLayout(col_status)

        # Col 4: Action Buttons
        actions_w = QFrame()
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        # Manual Verify Payment Action Button
        if not is_verified and paid > 0:
            verify_btn = QPushButton("  Accept Payment")
            verify_btn.setObjectName("primaryButton")
            verify_btn.setIcon(btn_icon_primary("check"))
            verify_btn.setIconSize(QSize(12, 12))
            verify_btn.setFixedHeight(30)
            verify_btn.setCursor(Qt.PointingHandCursor)
            verify_btn.setToolTip("Manually verify and accept this payment")
            verify_btn.clicked.connect(lambda _, invoice=inv: self._verify_payment_dict(invoice))
            actions_l.addWidget(verify_btn)

        pay_btn = QPushButton()
        pay_btn.setIcon(get_icon("check", color="#22C55E", size=QSize(14, 14)))
        pay_btn.setIconSize(QSize(14, 14))
        pay_btn.setFixedSize(32, 32)
        pay_btn.setStyleSheet("background: transparent; border: none;")
        pay_btn.setCursor(Qt.PointingHandCursor)
        pay_btn.setToolTip("Record Payment")
        pay_btn.setEnabled(bal > 0.005 and bool(inv.get("booking_id")))
        pay_btn.clicked.connect(lambda _, invoice=inv: self._record_payment_dict(invoice))

        hist_btn = QPushButton()
        hist_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(14, 14)))
        hist_btn.setIconSize(QSize(14, 14))
        hist_btn.setFixedSize(32, 32)
        hist_btn.setStyleSheet("background: transparent; border: none;")
        hist_btn.setCursor(Qt.PointingHandCursor)
        hist_btn.setToolTip("Payment History")
        hist_btn.clicked.connect(lambda _, invoice=inv: PaymentHistoryDialog(self, inv=invoice).exec())

        print_btn = QPushButton()
        print_btn.setIcon(get_icon("export", color="#9CA3AF", size=QSize(14, 14)))
        print_btn.setIconSize(QSize(14, 14))
        print_btn.setFixedSize(32, 32)
        print_btn.setStyleSheet("background: transparent; border: none;")
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.setToolTip("Print / Save Receipt PDF")
        print_btn.clicked.connect(lambda _, invoice=inv: self._print_receipt_dict(invoice))

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(14, 14)))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(32, 32)
        edit_btn.setStyleSheet("background: transparent; border: none;")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setToolTip("Edit Payment / Balance")
        edit_btn.clicked.connect(lambda _, invoice=inv: self._edit_billing_dict(invoice))

        del_btn = QPushButton()
        del_btn.setIcon(btn_icon_red("trash"))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(32, 32)
        del_btn.setStyleSheet("background: transparent; border: none;")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("Delete invoice")
        del_btn.clicked.connect(lambda _, invoice=inv: self._delete_invoice_dict(invoice))

        actions_l.addWidget(pay_btn)
        actions_l.addWidget(hist_btn)
        actions_l.addWidget(print_btn)
        actions_l.addWidget(edit_btn)
        actions_l.addWidget(del_btn)

        lay.addWidget(actions_w)

        return card

    def _edit_billing_dict(self, inv: dict):
        dlg = EditBillingDialog(self, inv=inv)
        if dlg.exec() == QDialog.Accepted:
            success(self, message=f"Invoice {inv.get('invoice')} payment details updated successfully.")
            self.reload()

    def _verify_payment_dict(self, inv: dict):
        if not inv.get("db_id"):
            return
        try:
            repo.verify_invoice_payment(inv["db_id"])
            success(self, message=f"Payment for invoice {inv.get('invoice')} has been verified and accepted!")
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Verification Failed", str(e))

    def _record_payment_dict(self, inv: dict):
        if not inv.get("booking_id"):
            QMessageBox.warning(self, "Not Allowed",
                "This invoice is not linked to a booking and cannot accept payments through this flow.")
            return
        dlg = RecordPaymentDialog(self, inv=inv)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                try:
                    pr = repo.pay_invoice(
                        inv["booking_id"],
                        result["amount"],
                        result["payment_date"],
                        result["method"],
                        result["note"],
                    )
                    inv["paid"]   = pr["new_paid"]
                    inv["status"] = pr["new_invoice_status"]
                    self._populate_table()
                    repo.write_audit_log(get_actor(), "PAYMENT", "invoices", inv["db_id"],
                        None, {"amount": result["amount"], "method": result["method"]})
                    try:
                        repo.push_notification(
                            "success",
                            "Payment Recorded",
                            f"₱{result['amount']:,.2f} via {result['method']} recorded for {inv.get('customer', '')} — {inv.get('invoice', '')}.",
                            "#22C55E",
                        )
                    except Exception:
                        pass
                    app_events().payment_recorded.emit()
                    success(self, message=f"Payment of ₱{result['amount']:,.2f} recorded.")
                except Exception as exc:
                    QMessageBox.warning(self, "Payment Error", str(exc))

    def _delete_invoice_dict(self, inv: dict):
        if not confirm(self, title="Delete Invoice",
                       message=f"Are you sure you want to delete invoice '{inv.get('invoice', '')}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if inv.get("db_id"):
            repo.delete_invoice(inv["db_id"])
        if inv in self._invoices:
            self._invoices.remove(inv)
        self._populate_table()
        success(self, message="Invoice deleted successfully.")

    def _print_receipt_dict(self, inv: dict):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Receipt PDF",
            f"receipt_{inv.get('invoice', 'receipt')}.pdf",
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        business = repo.get_business_info()
        ok = exporter.export_receipt_pdf(path, inv, business)
        if ok:
            if inv.get("db_id"):
                repo.log_receipt_sent(inv["db_id"], "print")
            prompt_file_saved(self, path, title="Receipt PDF Saved", message="Receipt PDF generated successfully.")
        else:
            QMessageBox.warning(self, "Export Failed",
                "Could not generate PDF. Make sure reportlab is installed.")

    def _email_receipt_dict(self, inv: dict):
        to_email = inv.get("customer_email", "").strip()
        if not to_email:
            to_email = repo.get_customer_email_by_name(inv.get("customer", "")).strip()
        if not to_email or "@" not in to_email:
            QMessageBox.warning(self, "No Email",
                f"No email address found for {inv.get('customer', 'this customer')}.\n"
                "Please update the customer's email in the Customers page.")
            return
        business = repo.get_business_info()
        smtp = repo.get_smtp_config()
        if not smtp.get("smtp_host"):
            QMessageBox.warning(self, "SMTP Not Configured",
                "Please configure SMTP settings in the Settings page before sending emails.")
            return
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            pdf_ok = exporter.export_receipt_pdf(tmp_path, inv, business)
            if not pdf_ok:
                QMessageBox.warning(self, "PDF Error",
                    "Could not generate receipt PDF. Make sure reportlab is installed.")
                return
            from utils.mailer import send_receipt_email
            inv_for_email = {**inv, "business_name": business.get("name", "Jayraldine's Catering")}
            sent, err = send_receipt_email(smtp, to_email, inv_for_email, tmp_path)
            if sent:
                if inv.get("db_id"):
                    repo.log_receipt_sent(inv["db_id"], "email")
                success(self, message=f"Receipt emailed to {to_email}.")
            else:
                QMessageBox.warning(self, "Email Failed", err)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def filter_search(self, text):
        q = text.lower().strip()
        if not q:
            self._populate_table()
            return
        orig = self._invoices
        filtered = [
            i for i in orig
            if q in i.get("customer", "").lower()
            or q in i.get("invoice", "").lower()
            or q in i.get("status", "").lower()
            or q in _fmt_date(i.get("event_date", "")).lower()
        ]
        saved = self._invoices
        self._invoices = filtered
        self._populate_table()
        self._invoices = saved

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Invoices", "invoices.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Invoice", "Customer", "Event Date", "Total", "Paid", "Balance", "Status"])
            for inv in self._invoices:
                total = float(inv.get("amount", 0))
                paid  = float(inv.get("paid", 0))
                writer.writerow([
                    inv.get("invoice", ""), inv.get("customer", ""),
                    inv.get("event_date", ""),
                    f"{total:,.2f}", f"{paid:,.2f}", f"{total-paid:,.2f}",
                    inv.get("status", ""),
                ])
        prompt_file_saved(self, path, title="Invoices Exported", message="Invoices list exported successfully.")