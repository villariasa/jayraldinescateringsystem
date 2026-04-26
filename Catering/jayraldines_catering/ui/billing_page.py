import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox,
    QFileDialog, QMessageBox, QDateEdit
)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success
import utils.repository as repo


_STATUS_COLORS = {"Paid": "#22C55E", "Partial": "#F59E0B", "Unpaid": "#EF4444"}
_STATUSES = ["Unpaid", "Partial", "Paid"]


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

        customers = repo.get_all_customers() or []
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setFixedHeight(38)
        for c in customers:
            self.customer_combo.addItem(c["name"])
        if self._edit_mode:
            idx = self.customer_combo.findText(self._invoice_data.get("customer", ""))
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
            else:
                self.customer_combo.setEditText(self._invoice_data.get("customer", ""))

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
        label = "Save Changes" if self._edit_mode else "  Create Invoice"
        save = QPushButton(label)
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
        customer = self.customer_combo.currentText().strip()
        if not customer:
            self._err.setText("Customer is required.")
            self._err.show()
            return
        self._result = {
            "customer":   customer,
            "event_date": self.date_field.date().toString("yyyy-MM-dd"),
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

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["Invoice #", "Customer", "Event Date", "Amount", "Paid", "Status", "", ""]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self._table.setColumnWidth(6, 36)
        self._table.setColumnWidth(7, 36)
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
            self._table.setItem(row, 0, QTableWidgetItem(inv.get("invoice", "")))
            self._table.setItem(row, 1, QTableWidgetItem(inv.get("customer", "")))
            self._table.setItem(row, 2, QTableWidgetItem(str(inv.get("event_date", ""))))
            self._table.setItem(row, 3, QTableWidgetItem(f"₱{float(inv.get('amount', 0)):,.2f}"))
            self._table.setItem(row, 4, QTableWidgetItem(f"₱{float(inv.get('paid', 0)):,.2f}"))

            status_item = QTableWidgetItem(inv.get("status", ""))
            status_item.setForeground(QColor(_STATUS_COLORS.get(inv.get("status", ""), "#9CA3AF")))
            self._table.setItem(row, 5, status_item)

            edit_btn = QPushButton()
            edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(14, 14)))
            edit_btn.setIconSize(QSize(14, 14))
            edit_btn.setFixedSize(32, 32)
            edit_btn.setStyleSheet("background: transparent; border: none;")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setToolTip("Edit invoice")
            edit_btn.clicked.connect(self._edit_invoice)
            self._table.setCellWidget(row, 6, edit_btn)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(14, 14))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete invoice")
            del_btn.clicked.connect(self._delete_invoice)
            self._table.setCellWidget(row, 7, del_btn)

    def _row_from_sender(self, col):
        btn = self.sender()
        for r in range(self._table.rowCount()):
            if self._table.cellWidget(r, col) is btn:
                return r
        return -1

    def _edit_invoice(self):
        row = self._row_from_sender(6)
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
                inv.update(result)
                self._populate_table()
                success(self, message="Invoice updated successfully.")

    def _delete_invoice(self):
        row = self._row_from_sender(7)
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

    def _open_new_invoice(self):
        dlg = InvoiceDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                db_result = repo.create_invoice(result)
                if db_result:
                    result["db_id"]   = db_result.get("invoice_id")
                    result["invoice"] = db_result.get("invoice_ref", f"INV-{len(self._invoices)+1:03d}")
                self._invoices.append(result)
                self._populate_table()
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

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Invoices", "invoices.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Invoice", "Customer", "Event Date", "Amount", "Paid", "Status"])
            for inv in self._invoices:
                writer.writerow([
                    inv.get("invoice", ""), inv.get("customer", ""),
                    inv.get("event_date", ""), inv.get("amount", ""),
                    inv.get("paid", ""), inv.get("status", ""),
                ])
        QMessageBox.information(self, "Export", f"Exported to:\n{path}")
