from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon


_SAMPLE_INVOICES = [
    {"invoice": "INV-001", "customer": "Maria Santos",  "event_date": "Apr 30, 2026", "amount": 45000.0,  "paid": 22500.0,  "status": "Partial"},
    {"invoice": "INV-002", "customer": "TechCorp Inc.", "event_date": "Oct 24, 2025", "amount": 120000.0, "paid": 120000.0, "status": "Paid"},
    {"invoice": "INV-003", "customer": "Cruz Family",   "event_date": "Dec 15, 2025", "amount": 85000.0,  "paid": 0.0,      "status": "Unpaid"},
    {"invoice": "INV-004", "customer": "Smith Wedding", "event_date": "Jun 12, 2026", "amount": 200000.0, "paid": 60000.0,  "status": "Partial"},
]

_STATUS_COLORS = {"Paid": "#22C55E", "Partial": "#F59E0B", "Unpaid": "#EF4444"}
_STATUSES = ["Unpaid", "Partial", "Paid"]


class NewInvoiceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Invoice")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(440)
        self.setModal(True)
        self._result = None
        self._inv_count = len(_SAMPLE_INVOICES) + 1
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("modalContainer")
        container.setStyleSheet(
            "QFrame#modalContainer { background-color: #111827; border-radius: 14px; border: 1px solid #243244; }"
        )

        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("New Invoice")
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

        self.customer_field = QLineEdit()
        self.customer_field.setPlaceholderText("Customer name")

        self.date_field = QLineEdit()
        self.date_field.setPlaceholderText("e.g. Jan 01, 2026")

        self.amount_field = QDoubleSpinBox()
        self.amount_field.setPrefix("₱ ")
        self.amount_field.setRange(0, 9999999)
        self.amount_field.setDecimals(2)
        self.amount_field.setSingleStep(1000)

        self.paid_field = QDoubleSpinBox()
        self.paid_field.setPrefix("₱ ")
        self.paid_field.setRange(0, 9999999)
        self.paid_field.setDecimals(2)
        self.paid_field.setSingleStep(1000)

        self.status_field = QComboBox()
        self.status_field.addItems(_STATUSES)

        for lbl, widget in [
            ("Customer *",  self.customer_field),
            ("Event Date *", self.date_field),
            ("Total Amount", self.amount_field),
            ("Amount Paid",  self.paid_field),
            ("Status",       self.status_field),
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
        save = QPushButton("  Create Invoice")
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
        customer = self.customer_field.text().strip()
        date     = self.date_field.text().strip()
        if not customer or not date:
            self._err.setText("Customer and Event Date are required.")
            self._err.show()
            if not customer:
                self.customer_field.setStyleSheet("border: 1px solid #E11D48;")
            if not date:
                self.date_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        self._result = {
            "invoice":    f"INV-{self._inv_count:03d}",
            "customer":   customer,
            "event_date": date,
            "amount":     self.amount_field.value(),
            "paid":       self.paid_field.value(),
            "status":     self.status_field.currentText(),
        }
        self.accept()

    def get_result(self):
        return self._result


class BillingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._invoices = list(_SAMPLE_INVOICES)
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

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(["Invoice #", "Customer", "Event Date", "Amount", "Paid", "Status", ""])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self._table.setColumnWidth(6, 60)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(self._table)

        root.addWidget(card)

    def _populate_table(self):
        self._table.setRowCount(0)
        for row, inv in enumerate(self._invoices):
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(inv["invoice"]))
            self._table.setItem(row, 1, QTableWidgetItem(inv["customer"]))
            self._table.setItem(row, 2, QTableWidgetItem(inv["event_date"]))
            self._table.setItem(row, 3, QTableWidgetItem(f"₱{inv['amount']:,.2f}"))
            self._table.setItem(row, 4, QTableWidgetItem(f"₱{inv['paid']:,.2f}"))

            status_item = QTableWidgetItem(inv["status"])
            status_item.setForeground(QColor(_STATUS_COLORS.get(inv["status"], "#9CA3AF")))
            self._table.setItem(row, 5, status_item)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(self._delete_invoice)
            self._table.setCellWidget(row, 6, del_btn)

    def _delete_invoice(self):
        btn = self.sender()
        for r in range(self._table.rowCount()):
            if self._table.cellWidget(r, 6) is btn:
                self._invoices.pop(r)
                self._populate_table()
                return

    def _open_new_invoice(self):
        dlg = NewInvoiceDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                self._invoices.append(result)
                self._populate_table()

    def filter_search(self, text):
        q = text.lower()
        orig = self._invoices
        self._invoices = [i for i in orig if q in i["customer"].lower() or q in i["invoice"].lower()]
        self._populate_table()
        self._invoices = orig

    def export_csv(self):
        import csv
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "Export Invoices", "invoices.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Invoice", "Customer", "Event Date", "Amount", "Paid", "Status"])
            for inv in self._invoices:
                writer.writerow([inv["invoice"], inv["customer"], inv["event_date"],
                                 inv["amount"], inv["paid"], inv["status"]])
        QMessageBox.information(self, "Export", f"Exported to:\n{path}")
