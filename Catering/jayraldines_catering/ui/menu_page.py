from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success
import utils.menu_store as menu_store
import utils.repository as repo

_CATEGORIES = ["Main Course", "Noodles", "Soup", "Vegetables", "Dessert", "Drinks", "Bread", "Other"]
_PACKAGES   = ["Budget", "Standard", "Premium", "Custom"]
_STATUSES   = ["Available", "Unavailable", "Out of Stock", "Seasonal"]


class AddMenuItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Menu Item")
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
        title = QLabel("Add Menu Item")
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

        self.item_field = QLineEdit()
        self.item_field.setPlaceholderText("e.g. Lechon de Leche")

        self.cat_field = QComboBox()
        self.cat_field.addItems(_CATEGORIES)

        self.pkg_field = QComboBox()
        self.pkg_field.addItems(_PACKAGES)

        self.price_field = QDoubleSpinBox()
        self.price_field.setPrefix("₱ ")
        self.price_field.setRange(0, 999999)
        self.price_field.setDecimals(2)
        self.price_field.setSingleStep(100)

        self.status_field = QComboBox()
        self.status_field.addItems(_STATUSES)

        for lbl, widget in [
            ("Item Name *", self.item_field),
            ("Category",    self.cat_field),
            ("Package",     self.pkg_field),
            ("Price",       self.price_field),
            ("Status",      self.status_field),
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
        save = QPushButton("  Save Item")
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
        name = self.item_field.text().strip()
        if not name:
            self._err.setText("Item name is required.")
            self._err.show()
            self.item_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        self._result = {
            "item":     name,
            "category": self.cat_field.currentText(),
            "package":  self.pkg_field.currentText(),
            "price":    self.price_field.value(),
            "status":   self.status_field.currentText(),
        }
        self.accept()

    def get_result(self):
        return self._result


class MenuPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._populate_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Menu")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("  Add Item")
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

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["Item", "Category", "Package", "Price", "Status", ""])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self._table.setColumnWidth(5, 60)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(self._table)

        root.addWidget(card)

    def _populate_table(self):
        q = getattr(self, "_filter_q", "")
        db_items = repo.get_all_menu_items()
        items = db_items if db_items else menu_store.all_items()
        if q:
            items = [i for i in items if q in i["item"].lower() or q in i["category"].lower() or q in i["package"].lower()]
        self._table.setRowCount(0)
        status_colors = {"Available": "#22C55E", "Unavailable": "#EF4444", "Out of Stock": "#F97316", "Seasonal": "#F59E0B"}
        for row, item in enumerate(items):
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(item["item"]))
            self._table.setItem(row, 1, QTableWidgetItem(item["category"]))
            self._table.setItem(row, 2, QTableWidgetItem(item["package"]))
            self._table.setItem(row, 3, QTableWidgetItem(f"₱{item['price']:,.2f}"))

            status_item = QTableWidgetItem(item["status"])
            status_item.setForeground(QColor(status_colors.get(item["status"], "#9CA3AF")))
            self._table.setItem(row, 4, status_item)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(self._delete_item)
            self._table.setCellWidget(row, 5, del_btn)

    def _delete_item(self):
        btn = self.sender()
        for r in range(self._table.rowCount()):
            if self._table.cellWidget(r, 5) is btn:
                items = repo.get_all_menu_items() or menu_store.all_items()
                item = items[r] if r < len(items) else {}
                item_name = item.get("item", "")
                item_id = item.get("id")
                if not confirm(self, title="Delete Menu Item",
                               message=f"Are you sure you want to delete '{item_name}'? This cannot be undone.",
                               confirm_label="Delete", danger=True):
                    return
                repo.delete_menu_item(r, item_id)
                self._populate_table()
                success(self, message="Menu item deleted successfully.")
                return

    def _open_add_dialog(self):
        dlg = AddMenuItemDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                repo.add_menu_item(result)
                self._populate_table()
                success(self, message="Menu item added successfully.")

    def filter_search(self, text):
        q = text.lower()
        self._filter_q = q
        self._populate_table()
