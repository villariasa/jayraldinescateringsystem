from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success
import utils.repository as repo


_SAMPLE_CUSTOMERS = [
    {"name": "Maria Santos",    "contact": "+63 912 345 6789", "email": "maria@email.com",    "events": 3, "status": "Active"},
    {"name": "TechCorp Inc.",   "contact": "+63 917 000 1234", "email": "events@techcorp.ph", "events": 1, "status": "Active"},
    {"name": "Cruz Family",     "contact": "+63 920 111 2222", "email": "cruz@gmail.com",     "events": 2, "status": "Active"},
    {"name": "Smith Wedding",   "contact": "+63 932 555 6666", "email": "smith@yahoo.com",    "events": 1, "status": "Pending"},
]


class AddCustomerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Customer")
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

        self.name_field    = QLineEdit(); self.name_field.setPlaceholderText("Full name / Company name")
        self.contact_field = QLineEdit(); self.contact_field.setPlaceholderText("+63 9XX XXX XXXX")
        self.email_field   = QLineEdit(); self.email_field.setPlaceholderText("email@example.com")
        self.status_field  = QComboBox(); self.status_field.addItems(["Active", "Pending", "Inactive"])

        for lbl, widget in [
            ("Name *",    self.name_field),
            ("Contact *", self.contact_field),
            ("Email",     self.email_field),
            ("Status",    self.status_field),
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
        name    = self.name_field.text().strip()
        contact = self.contact_field.text().strip()
        if not name or not contact:
            self._err.setText("Name and Contact are required.")
            self._err.show()
            if not name:
                self.name_field.setStyleSheet("border: 1px solid #E11D48;")
            if not contact:
                self.contact_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        self._result = {
            "name":    name,
            "contact": contact,
            "email":   self.email_field.text().strip(),
            "events":  0,
            "status":  self.status_field.currentText(),
        }
        self.accept()

    def get_result(self):
        return self._result


class CustomersPage(QWidget):
    def __init__(self):
        super().__init__()
        db_rows = repo.get_all_customers()
        self._customers = db_rows if db_rows else list(_SAMPLE_CUSTOMERS)
        self._build_ui()
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

        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        header.addWidget(export_btn)

        root.addLayout(header)

        self._search = QLineEdit()
        self._search.setObjectName("searchBox")
        self._search.setPlaceholderText("Search customers...")
        self._search.setFixedHeight(38)
        self._search.setMaximumWidth(320)
        self._search.textChanged.connect(self._filter_table)
        root.addWidget(self._search)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["Name", "Contact", "Email", "Total Events", "Status", ""])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self._table.setColumnWidth(5, 60)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(self._table)

        root.addWidget(card)

    def _populate_table(self, customers=None):
        data = customers if customers is not None else self._customers
        self._table.setRowCount(0)
        for row, c in enumerate(data):
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(c["name"]))
            self._table.setItem(row, 1, QTableWidgetItem(c["contact"]))
            self._table.setItem(row, 2, QTableWidgetItem(c["email"]))
            self._table.setItem(row, 3, QTableWidgetItem(str(c["events"])))

            status_item = QTableWidgetItem(c["status"])
            color_map = {"Active": "#22C55E", "Pending": "#F59E0B", "Inactive": "#6B7280"}
            status_item.setForeground(QColor(color_map.get(c["status"], "#9CA3AF")))
            self._table.setItem(row, 4, status_item)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setProperty("row_index", row)
            del_btn.clicked.connect(self._delete_customer)
            self._table.setCellWidget(row, 5, del_btn)

    def _delete_customer(self):
        btn = self.sender()
        row = self._table.indexAt(btn.pos()).row()
        if row < 0:
            for r in range(self._table.rowCount()):
                w = self._table.cellWidget(r, 5)
                if w is btn:
                    row = r
                    break
        if 0 <= row < len(self._customers):
            c = self._customers[row]
            if not confirm(self, title="Delete Customer",
                           message=f"Are you sure you want to delete '{c['name']}'? This cannot be undone.",
                           confirm_label="Delete", danger=True):
                return
            if c.get("id"):
                repo.delete_customer(c["id"])
            self._customers.pop(row)
            self._populate_table()
            success(self, message="Customer deleted successfully.")

    def _open_add_dialog(self):
        dlg = AddCustomerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                new_id = repo.add_customer(result)
                if new_id:
                    result["id"] = new_id
                self._customers.append(result)
                self._populate_table()
                success(self, message="Customer added successfully.")

    def _filter_table(self, text):
        q = text.lower()
        filtered = [c for c in self._customers if q in c["name"].lower() or q in c["email"].lower() or q in c["contact"].lower()]
        self._populate_table(filtered)

    def filter_search(self, text):
        self._search.setText(text)
