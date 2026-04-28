import csv
import os
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox,
    QFileDialog, QMessageBox, QDateEdit, QTextEdit, QSizePolicy,
    QStackedWidget
)
from PySide6.QtCore import Qt, QSize, QDate, QTimer
from PySide6.QtWidgets import QCompleter
from datetime import date as _date_type
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success
import utils.repository as repo
import utils.exporter as exporter
from utils.session import get_actor


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
        self.setWindowTitle("Record Payment")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
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

        balance = float(self._inv.get("amount", 0)) - float(self._inv.get("paid", 0))
        info = QLabel(
            f"<b>{self._inv.get('invoice', '')}</b> — {self._inv.get('customer', '')}<br>"
            f"Balance due: <span style='color:#E11D48;font-weight:700;'>₱ {balance:,.2f}</span>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size:13px; padding:8px 0;")
        lay.addWidget(info)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self._amount_f = QDoubleSpinBox()
        self._amount_f.setPrefix("₱ ")
        self._amount_f.setRange(0.01, max(balance, 0.01))
        self._amount_f.setValue(min(balance, balance))
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
        balance = float(self._inv.get("amount", 0)) - float(self._inv.get("paid", 0))
        if amount <= 0:
            self._err.setText("Amount must be greater than 0.")
            self._err.show()
            return
        if amount > balance + 0.005:
            self._err.setText(f"Amount exceeds remaining balance of ₱ {balance:,.2f}.")
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

        tbl = QTableWidget(len(records), 4)
        tbl.setHorizontalHeaderLabels(["Date", "Method", "Amount", "Note"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setShowGrid(False)
        tbl.setAlternatingRowColors(True)
        tbl.setMinimumHeight(200)

        if records:
            for i, r in enumerate(records):
                tbl.setRowHeight(i, 38)
                tbl.setItem(i, 0, QTableWidgetItem(r["payment_date"]))
                tbl.setItem(i, 1, QTableWidgetItem(r["method"]))
                amt = QTableWidgetItem(f"₱ {r['amount']:,.2f}")
                amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tbl.setItem(i, 2, amt)
                tbl.setItem(i, 3, QTableWidgetItem(r["note"]))
        else:
            tbl.insertRow(0)
            item = QTableWidgetItem("No payment records found.")
            item.setForeground(QColor("#9CA3AF"))
            tbl.setItem(0, 0, item)

        lay.addWidget(tbl)

        close = QPushButton("Close")
        close.setObjectName("secondaryButton")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        lay.addWidget(close, alignment=Qt.AlignRight)

        outer.addWidget(container)


class InvoiceDialog(QDialog):
    def __init__(self, parent=None, invoice_data=None):
        super().__init__(parent)
        self._edit_mode = invoice_data is not None
        self._invoice_data = invoice_data or {}
        self.setWindowTitle("Edit Invoice" if self._edit_mode else "New Invoice")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(460)
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
        title = QLabel("Edit Invoice" if self._edit_mode else "New Invoice")
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

        self._customers = repo.get_all_customers() or []
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setFixedHeight(38)
        self.customer_combo.setPlaceholderText("Search customer...")
        self.customer_combo.addItem("", None)
        for c in self._customers:
            self.customer_combo.addItem(c["name"], c)
        self.customer_combo.setCurrentIndex(0)
        self.customer_combo.setEditText("")
        completer = self.customer_combo.completer()
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setFilterMode(Qt.MatchContains)
        
        # NOTE: Signal connection removed from here to fix AttributeError

        self._date_stack = QStackedWidget()
        self._date_stack.setFixedHeight(38)

        self.date_field = QDateEdit()
        self.date_field.setCalendarPopup(True)
        self.date_field.setFixedHeight(38)
        self.date_field.setDisplayFormat("MMM dd, yyyy")
        if self._edit_mode:
            raw = self._invoice_data.get("event_date", "")
            q = QDate.fromString(str(raw), "yyyy-MM-dd")
            if not q.isValid():
                q = QDate.fromString(str(raw), "MMM dd, yyyy")
            self.date_field.setDate(q if q.isValid() else QDate.currentDate())
        else:
            self.date_field.setDate(QDate.currentDate())

        self.date_combo = QComboBox()
        self.date_combo.setFixedHeight(38)
        self.date_combo.setPlaceholderText("Select booking date...")

        self._date_stack.addWidget(self.date_field)
        self._date_stack.addWidget(self.date_combo)
        self._date_stack.setCurrentIndex(0)

        self._balance_lbl = QLabel()
        self._balance_lbl.setStyleSheet("font-size: 12px; color: #6B7280; padding: 4px 0;")
        self._balance_lbl.hide()

        # --- FIX 1: Move Signal down here so self.date_combo exists first ---
        self.customer_combo.currentIndexChanged.connect(self._on_customer_selected)
        self.date_combo.currentIndexChanged.connect(self._on_booking_date_selected)
        
        if self._edit_mode:
            idx = self.customer_combo.findText(self._invoice_data.get("customer", ""))
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
            else:
                self.customer_combo.setEditText(self._invoice_data.get("customer", ""))

        self.amount_field = QDoubleSpinBox()
        self.amount_field.setPrefix("₱ ")
        self.amount_field.setRange(0, 9999999)
        self.amount_field.setDecimals(2)
        self.amount_field.setSingleStep(1000)
        self.amount_field.setFixedHeight(38)
        if self._edit_mode:
            self.amount_field.setValue(float(self._invoice_data.get("amount", 0)))

        self.paid_field = QDoubleSpinBox()
        self.paid_field.setPrefix("₱ ")
        self.paid_field.setRange(0, 9999999)
        self.paid_field.setDecimals(2)
        self.paid_field.setSingleStep(1000)
        self.paid_field.setFixedHeight(38)
        if self._edit_mode:
            self.paid_field.setValue(float(self._invoice_data.get("paid", 0)))

        self.status_field = QComboBox()
        self.status_field.addItems(_STATUSES)
        self.status_field.setFixedHeight(38)
        if self._edit_mode:
            idx = self.status_field.findText(self._invoice_data.get("status", "Unpaid"))
            if idx >= 0:
                self.status_field.setCurrentIndex(idx)

        for lbl, widget in [
            ("Customer *",   self.customer_combo),
            ("Event Date *", self._date_stack),
            ("Total Amount", self.amount_field),
            ("Amount Paid",  self.paid_field),
            ("Status",       self.status_field),
        ]:
            form.addRow(QLabel(lbl), widget)

        lay.addLayout(form)
        lay.addWidget(self._balance_lbl)

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
        label = "Save Changes" if self._edit_mode else "  Create Invoice"
        self._save_btn = QPushButton(label)
        self._save_btn.setObjectName("primaryButton")
        self._save_btn.setIcon(btn_icon_primary("check"))
        self._save_btn.setIconSize(QSize(15, 15))
        self._save_btn.setCursor(Qt.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(self._save_btn)
        lay.addLayout(btn_row)

        outer.addWidget(container)

    def _save(self):
        customer = self.customer_combo.currentText().strip()
        if not customer or self.customer_combo.currentIndex() == 0:
            self._err.setText("Please search and select a customer.")
            self._err.show()
            return

        booking_id = None
        if self._date_stack.currentIndex() == 1:
            booking_id = self.date_combo.currentData()

        if not self._edit_mode and not booking_id:
            self._err.setText("Please select a booking event date. A booking is required to create an invoice.")
            self._err.show()
            return

        self._result = {
            "booking_id": booking_id,
            "customer":   customer,
            "event_date": self._get_event_date(),
            "amount":     self.amount_field.value(),
            "paid":       self.paid_field.value(),
            "status":     self.status_field.currentText(),
        }
        self.accept()

    def get_result(self):
        return self._result

    def _on_customer_selected(self, index):
        name = self.customer_combo.itemText(index).strip()
        if not name or index == 0:
            self._date_stack.setCurrentIndex(0)
            self._balance_lbl.hide()
            if hasattr(self, "_save_btn"):
                self._save_btn.setEnabled(True)
            return
        try:
            dates = repo.get_customer_event_dates(name)
        except Exception:
            dates = []
        if dates:
            self.date_combo.blockSignals(True)
            self.date_combo.clear()
            for d in dates:
                if isinstance(d, dict):
                    self.date_combo.addItem(d.get("date", ""), d.get("id"))
                else:
                    self.date_combo.addItem(d)
            self.date_combo.blockSignals(False)
            self._date_stack.setCurrentIndex(1)
            self._err.hide()
            if hasattr(self, "_save_btn"):
                self._save_btn.setEnabled(True)
            self._on_booking_date_selected(self.date_combo.currentIndex())
        else:
            self._date_stack.setCurrentIndex(0)
            self._balance_lbl.hide()
            self._err.setText("This customer has no bookings yet. Cannot create an invoice without a booking.")
            self._err.show()
            if hasattr(self, "_save_btn"):
                self._save_btn.setEnabled(False)

    def _on_booking_date_selected(self, index):
        booking_id = self.date_combo.itemData(index)
        if not booking_id:
            self._balance_lbl.hide()
            return
        try:
            bal = repo.get_booking_balance(booking_id)
        except Exception:
            bal = None
        if bal:
            color = "#22C55E" if bal["balance"] <= 0 else "#E11D48"
            self._balance_lbl.setText(
                f"Booking total: <b>₱ {bal['total']:,.2f}</b>  |  "
                f"Already paid: <b>₱ {bal['paid']:,.2f}</b>  |  "
                f"Balance: <b style='color:{color};'>₱ {bal['balance']:,.2f}</b>"
            )
            self._balance_lbl.show()
        else:
            self._balance_lbl.hide()

    def _get_event_date(self) -> str:
        if self._date_stack.currentIndex() == 1:
            return self.date_combo.currentText().strip()
        return self.date_field.date().toString("yyyy-MM-dd")


class BillingPage(QWidget):
    def __init__(self):
        super().__init__()
        db_rows = repo.get_all_invoices()
        self._invoices = db_rows if db_rows else []
        self._build_ui()
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

        new_btn = QPushButton("  New Invoice")
        new_btn.setObjectName("primaryButton")
        new_btn.setIcon(btn_icon_primary("plus"))
        new_btn.setIconSize(QSize(15, 15))
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self._open_new_invoice)
        header.addWidget(new_btn)

        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.clicked.connect(self.export_csv)
        header.addWidget(export_btn)

        root.addLayout(header)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 11)
        self._table.setHorizontalHeaderLabels(
            ["Invoice #", "Customer", "Event Date", "Total", "Paid", "Balance", "Status", "", "", "", ""]
        )
        
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        
        # --- FIX 3: Let the action columns resize automatically to fit without cutting off ---
        hdr.setSectionResizeMode(7,  QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(8,  QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(9,  QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(10, QHeaderView.ResizeToContents)
        # We removed the lines forcing the columns to 38px
        
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setShowGrid(False)
        card_layout.addWidget(self._table)

        root.addWidget(card)

    def _populate_table(self):
        self._table.setRowCount(0)
        for row, inv in enumerate(self._invoices):
            self._table.insertRow(row)
            self._table.setRowHeight(row, 44)

            inv_item = QTableWidgetItem(inv.get("invoice", ""))
            self._table.setItem(row, 0, inv_item)
            self._table.setItem(row, 1, QTableWidgetItem(inv.get("customer", "")))
            self._table.setItem(row, 2, QTableWidgetItem(_fmt_date(inv.get("event_date", ""))))

            total = float(inv.get("amount", 0))
            paid  = float(inv.get("paid", 0))
            bal   = total - paid

            self._table.setItem(row, 3, QTableWidgetItem(f"₱{total:,.2f}"))
            self._table.setItem(row, 4, QTableWidgetItem(f"₱{paid:,.2f}"))

            bal_item = QTableWidgetItem(f"₱{bal:,.2f}")
            if bal > 0:
                bal_item.setForeground(QColor("#EF4444"))
            else:
                bal_item.setForeground(QColor("#22C55E"))
            self._table.setItem(row, 5, bal_item)

            status = inv.get("status", "")
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(_STATUS_COLORS.get(status, "#9CA3AF")))
            self._table.setItem(row, 6, status_item)

            edit_btn = QPushButton()
            edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(14, 14)))
            edit_btn.setIconSize(QSize(14, 14))
            edit_btn.setFixedSize(34, 34)
            edit_btn.setStyleSheet("background: transparent; border: none;")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setToolTip("Edit invoice")
            edit_btn.clicked.connect(self._edit_invoice)
            self._table.setCellWidget(row, 7, edit_btn)

            pay_btn = QPushButton()
            pay_btn.setIcon(get_icon("check", color="#22C55E", size=QSize(14, 14)))
            pay_btn.setIconSize(QSize(14, 14))
            pay_btn.setFixedSize(34, 34)
            pay_btn.setStyleSheet("background: transparent; border: none;")
            pay_btn.setCursor(Qt.PointingHandCursor)
            pay_btn.setToolTip("Record Payment")
            pay_btn.setEnabled(bal > 0.005)
            pay_btn.clicked.connect(self._record_payment)
            self._table.setCellWidget(row, 8, pay_btn)

            hist_btn = QPushButton()
            hist_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(14, 14)))
            hist_btn.setIconSize(QSize(14, 14))
            hist_btn.setFixedSize(34, 34)
            hist_btn.setStyleSheet("background: transparent; border: none;")
            hist_btn.setCursor(Qt.PointingHandCursor)
            hist_btn.setToolTip("Payment History")
            hist_btn.clicked.connect(self._show_payment_history)
            self._table.setCellWidget(row, 9, hist_btn)

            actions_frame = QFrame()
            actions_frame.setStyleSheet("background: transparent;")
            actions_lay = QHBoxLayout(actions_frame)
            actions_lay.setContentsMargins(2, 2, 2, 2)
            actions_lay.setSpacing(2)

            print_btn = QPushButton()
            print_btn.setIcon(get_icon("export", color="#9CA3AF", size=QSize(14, 14)))
            print_btn.setIconSize(QSize(14, 14))
            print_btn.setFixedSize(28, 28)
            print_btn.setStyleSheet("background: transparent; border: none;")
            print_btn.setCursor(Qt.PointingHandCursor)
            print_btn.setToolTip("Print / Save Receipt PDF")
            print_btn.clicked.connect(self._print_receipt)

            email_btn = QPushButton()
            email_btn.setIcon(get_icon("bell", color="#3B82F6", size=QSize(14, 14)))
            email_btn.setIconSize(QSize(14, 14))
            email_btn.setFixedSize(28, 28)
            email_btn.setStyleSheet("background: transparent; border: none;")
            email_btn.setCursor(Qt.PointingHandCursor)
            email_btn.setToolTip("Email Receipt")
            email_btn.clicked.connect(self._email_receipt)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(14, 14))
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete invoice")
            del_btn.clicked.connect(self._delete_invoice)

            actions_lay.addWidget(print_btn)
            actions_lay.addWidget(email_btn)
            actions_lay.addWidget(del_btn)
            self._table.setCellWidget(row, 10, actions_frame)

    def _row_from_sender(self, col):
        btn = self.sender()
        for r in range(self._table.rowCount()):
            w = self._table.cellWidget(r, col)
            if w is btn:
                return r
            if w is not None and hasattr(w, "layout"):
                layout = w.layout()
                if layout:
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget() is btn:
                            return r
        return -1

    def _row_from_sender_any(self):
        btn = self.sender()
        for r in range(self._table.rowCount()):
            for col in range(self._table.columnCount()):
                w = self._table.cellWidget(r, col)
                if w is btn:
                    return r
                if w is not None:
                    layout = getattr(w, "layout", None)
                    if callable(layout):
                        lay = layout()
                        if lay:
                            for i in range(lay.count()):
                                item = lay.itemAt(i)
                                if item and item.widget() is btn:
                                    return r
        return -1

    def _edit_invoice(self):
        row = self._row_from_sender(7)
        if row < 0:
            return
        inv = self._invoices[row]
        dlg = InvoiceDialog(self, invoice_data=inv)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                if inv.get("db_id"):
                    repo.update_invoice(inv["db_id"], {
                        "customer":   result["customer"],
                        "event_date": result["event_date"],
                        "amount":     result["amount"],
                        "paid":       result["paid"],
                        "status":     result["status"],
                    })
                inv.update({
                    "customer":   result["customer"],
                    "event_date": _fmt_date(result["event_date"]),
                    "amount":     result["amount"],
                    "paid":       result["paid"],
                    "status":     result["status"],
                })
                self._populate_table()
                repo.write_audit_log(get_actor(), "UPDATE", "invoices", inv.get("db_id"),
                    {"status": inv.get("status"), "paid": inv.get("paid")},
                    {"status": result["status"], "paid": result["paid"]})
                success(self, message="Invoice updated successfully.")

    def _record_payment(self):
        row = self._row_from_sender(8)
        if row < 0:
            return
        inv = self._invoices[row]
        dlg = RecordPaymentDialog(self, inv=inv)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result and inv.get("db_id"):
                try:
                    pr = repo.add_payment_record(
                        inv["db_id"],
                        result["amount"],
                        result["payment_date"],
                        result["method"],
                        result["note"],
                    )
                    if pr:
                        inv["paid"]   = pr["new_paid"]
                        inv["status"] = pr["new_status"]
                        self._populate_table()
                        repo.write_audit_log(get_actor(), "PAYMENT", "invoices", inv["db_id"],
                            None, {"amount": result["amount"], "method": result["method"]})
                        try:
                            repo.push_notification(
                                "success",
                                "Payment Recorded",
                                f"₱{result['amount']:,.2f} payment via {result['method']} recorded for {inv.get('customer', '')} — {inv.get('invoice', '')}.",
                                "#22C55E",
                            )
                        except Exception:
                            pass
                        success(self, message=f"Payment of ₱{result['amount']:,.2f} recorded.")
                    else:
                        QMessageBox.warning(self, "Error", "Failed to record payment.")
                except Exception as exc:
                    QMessageBox.warning(self, "Payment Error", str(exc))

    def _show_payment_history(self):
        row = self._row_from_sender(9)
        if row < 0:
            return
        inv = self._invoices[row]
        PaymentHistoryDialog(self, inv=inv).exec()

    def _delete_invoice(self):
        row = self._row_from_sender_any()
        if row < 0:
            return
        inv = self._invoices[row]
        if not confirm(self, title="Delete Invoice",
                       message=f"Are you sure you want to delete invoice '{inv.get('invoice', '')}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if inv.get("db_id"):
            repo.delete_invoice(inv["db_id"])
        self._invoices.pop(row)
        self._populate_table()
        success(self, message="Invoice deleted successfully.")

    def _print_receipt(self):
        row = self._row_from_sender_any()
        if row < 0:
            return
        inv = self._invoices[row]
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
            success(self, message=f"Receipt saved to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed",
                "Could not generate PDF. Make sure reportlab is installed.")

    def _email_receipt(self):
        row = self._row_from_sender_any()
        if row < 0:
            return
        inv = self._invoices[row]
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

    def _open_new_invoice(self):
        dlg = InvoiceDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                result["event_date"] = _fmt_date(result["event_date"])
                db_result = repo.create_invoice(result)
                if db_result:
                    result["db_id"]   = db_result.get("invoice_id")
                    result["invoice"] = db_result.get("invoice_ref", f"INV-{len(self._invoices)+1:03d}")
                else:
                    result["invoice"] = f"INV-{len(self._invoices)+1:03d}"
                result["customer_email"] = repo.get_customer_email_by_name(result.get("customer", ""))
                if result.get("status") == "Paid" and result.get("db_id") and result.get("amount", 0) > 0:
                    try:
                        repo.add_payment_record(
                            result["db_id"],
                            result["amount"],
                            None,
                            "Cash",
                            "Auto-recorded on invoice creation (Paid status)",
                        )
                    except Exception:
                        pass
                self._invoices.append(result)
                self._populate_table()
                repo.write_audit_log(get_actor(), "CREATE", "invoices", result.get("db_id"),
                    None, {"invoice": result.get("invoice"), "customer": result.get("customer")})
                try:
                    repo.push_notification(
                        "info",
                        "Invoice Created",
                        f"Invoice {result.get('invoice', '')} created for {result.get('customer', '')} — ₱{float(result.get('amount', 0)):,.2f}.",
                        "#3B82F6",
                    )
                except Exception:
                    pass
                success(self, message="Invoice created successfully.")

    def filter_search(self, text):
        q = text.lower()
        orig = self._invoices
        filtered = [i for i in orig if q in i.get("customer", "").lower() or q in i.get("invoice", "").lower()]
        self._table.setRowCount(0)
        saved = self._invoices
        self._invoices = filtered
        self._populate_table()
        self._invoices = saved

    def highlight_row(self, item_id):
        for row, inv in enumerate(self._invoices):
            if inv.get("db_id") == item_id or str(inv.get("db_id", "")) == str(item_id):
                self._table.scrollTo(self._table.model().index(row, 0))
                self._set_row_highlight(row, True)
                QTimer.singleShot(2000, lambda r=row: self._set_row_highlight(r, False))
                break

    def _set_row_highlight(self, row: int, on: bool):
        hl = QColor("#F59E0B") if on else QColor("transparent")
        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item:
                item.setBackground(hl)
            w = self._table.cellWidget(row, col)
            if w:
                w.setStyleSheet(f"background: {'rgba(245,158,11,0.18)' if on else 'transparent'};")

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
        QMessageBox.information(self, "Export", f"Exported to:\n{path}")