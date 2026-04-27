from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QComboBox, QSizePolicy, QTextEdit
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor


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


_SAMPLE_CUSTOMERS = [
    {"name": "Maria Santosasds  ",    "contact": "+63 912 345 6789", "email": "maria@email.com",    "events": 3, "status": "Active"},
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
        self.setFixedWidth(480)
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
        contact_row.addWidget(self.country_code_combo)
        contact_row.addWidget(self.contact_field)
        contact_widget = QWidget()
        contact_widget.setLayout(contact_row)

        self.email_field = QLineEdit()
        self.email_field.setPlaceholderText("email@example.com")
        self.email_field.setFixedHeight(38)

        self.address_field = QTextEdit()
        self.address_field.setPlaceholderText("Street, Barangay, City, Province")
        self.address_field.setFixedHeight(72)

        self.status_field = QComboBox()
        self.status_field.setFixedHeight(38)
        self.status_field.addItems(["Active", "Pending", "Inactive"])

        for lbl, widget in [
            ("Name *",    self.name_field),
            ("Contact *", contact_widget),
            ("Email",     self.email_field),
            ("Address",   self.address_field),
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
        number  = self.contact_field.text().strip()
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
        self._result = {
            "name":    name,
            "contact": contact,
            "email":   self.email_field.text().strip(),
            "address": self.address_field.toPlainText().strip(),
            "events":  0,
            "status":  self.status_field.currentText(),
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


class CustomersPage(QWidget):
    def __init__(self):
        super().__init__()
        db_rows = repo.get_all_customers_with_loyalty()
        if not db_rows:
            db_rows = repo.get_all_customers() or list(_SAMPLE_CUSTOMERS)
        self._customers = db_rows
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
        export_btn.clicked.connect(self._export_csv)
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

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(["Name", "Contact", "Email", "Events", "Tier", "Status", ""])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self._table.setColumnWidth(4, 72)
        self._table.setColumnWidth(6, 100)
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
            self._table.setRowHeight(row, 48)
            self._table.setItem(row, 0, QTableWidgetItem(c["name"]))
            self._table.setItem(row, 1, QTableWidgetItem(c["contact"]))
            self._table.setItem(row, 2, QTableWidgetItem(c["email"]))
            self._table.setItem(row, 3, QTableWidgetItem(str(c.get("events", 0))))

            tier = c.get("loyalty_tier", "Bronze")
            tier_w = QWidget()
            tier_l = QHBoxLayout(tier_w)
            tier_l.setContentsMargins(4, 0, 4, 0)
            tier_l.addWidget(_tier_badge(tier))
            tier_l.addStretch()
            self._table.setCellWidget(row, 4, tier_w)

            status_item = QTableWidgetItem(c["status"])
            color_map = {"Active": "#22C55E", "Pending": "#F59E0B", "Inactive": "#6B7280"}
            status_item.setForeground(QColor(color_map.get(c["status"], "#9CA3AF")))
            self._table.setItem(row, 5, status_item)

            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(2, 0, 2, 0)
            action_l.setSpacing(4)

            fu_btn = QPushButton()
            fu_btn.setIcon(get_icon("bell", color="#F59E0B", size=QSize(13, 13)))
            fu_btn.setIconSize(QSize(13, 13))
            fu_btn.setFixedSize(28, 28)
            fu_btn.setToolTip("Follow-up reminders")
            fu_btn.setStyleSheet("background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:6px;")
            fu_btn.setCursor(Qt.PointingHandCursor)
            fu_btn.clicked.connect(lambda _, cust=c: self._open_follow_ups(cust))
            action_l.addWidget(fu_btn)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(13, 13))
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda _, cust=c: self._delete_customer_by_ref(cust))
            action_l.addWidget(del_btn)
            action_l.addStretch()
            self._table.setCellWidget(row, 6, action_w)

    def _delete_customer_by_ref(self, c):
        if not confirm(self, title="Delete Customer",
                       message=f"Are you sure you want to delete '{c['name']}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if c.get("id"):
            repo.delete_customer(c["id"])
        self._customers = [x for x in self._customers if x is not c]
        self._populate_table()
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
                    # FIX 1: Added closing parenthesis
                    done_btn.setStyleSheet("background:#16A34A;color:white;border:none;border-radius:5px;font-size:11px;padding:0 8px;")
                    done_btn.clicked.connect(lambda _, fid=fu["id"]: (repo.complete_follow_up(fid), _reload()))
                    fu_row.addWidget(done_btn)
                del_btn2 = QPushButton("✕")
                del_btn2.setFixedSize(24, 24)
                # FIX 2: Added closing parenthesis
                del_btn2.setStyleSheet("background:transparent;border:none;font-weight:700;")
                del_btn2.clicked.connect(lambda _, fid=fu["id"]: (repo.delete_follow_up(fid), _reload()))
                fu_row.addWidget(del_btn2)
                row_w = QWidget()
                row_w.setLayout(fu_row)
                inner_lay.addWidget(row_w)
            if not fups:
                empty = QLabel("No follow-ups yet.")
                # FIX 3: Added closing parenthesis
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

    def _open_add_dialog(self):
        dlg = AddCustomerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                new_id = repo.add_customer(result)
                if new_id:
                    result["id"] = new_id
                    result["loyalty_tier"] = "Bronze"
                    repo.recalculate_loyalty(new_id)
                self._customers.append(result)
                self._populate_table()
                success(self, message="Customer added successfully.")

    def _filter_table(self, text):
        q = text.lower()
        filtered = [c for c in self._customers if q in c["name"].lower() or q in c["email"].lower() or q in c["contact"].lower()]
        self._populate_table(filtered)

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