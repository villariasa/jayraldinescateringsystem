from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success
import utils.repository as repo

_UNITS = ['kg', 'g', 'L', 'mL', 'pcs', 'packs', 'trays', 'boxes']


class AddInventoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Inventory Item")
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
        title = QLabel("Add Inventory Item")
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

        self.ingredient_field = QLineEdit()
        self.ingredient_field.setPlaceholderText("e.g. Chicken")

        self.unit_field = QComboBox()
        self.unit_field.addItems(_UNITS)

        self.stock_field = QDoubleSpinBox()
        self.stock_field.setRange(0, 99999)
        self.stock_field.setDecimals(2)

        self.min_stock_field = QDoubleSpinBox()
        self.min_stock_field.setRange(0, 99999)
        self.min_stock_field.setDecimals(2)

        for lbl, widget in [
            ("Ingredient *", self.ingredient_field),
            ("Unit",         self.unit_field),
            ("Stock",        self.stock_field),
            ("Min. Stock",   self.min_stock_field),
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
        ingredient = self.ingredient_field.text().strip()
        if not ingredient:
            self._err.setText("Ingredient name is required.")
            self._err.show()
            self.ingredient_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        self._result = {
            "ingredient": ingredient,
            "unit":       self.unit_field.currentText(),
            "stock":      self.stock_field.value(),
            "min_stock":  self.min_stock_field.value(),
        }
        self.accept()

    def get_result(self):
        return self._result


class AdjustStockDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self._item = item
        self.setWindowTitle("Adjust Stock")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(380)
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
        title = QLabel(f"Adjust Stock — {self._item['ingredient']}")
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

        current_lbl = QLabel(f"Current stock: {self._item['stock']} {self._item['unit']}")
        current_lbl.setStyleSheet("font-size: 12px;"
        lay.addWidget(current_lbl)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.delta_field = QDoubleSpinBox()
        self.delta_field.setRange(-99999, 99999)
        self.delta_field.setDecimals(2)
        self.delta_field.setPrefix("Δ ")
        self.delta_field.setToolTip("Positive = restock, Negative = usage")

        form.addRow(QLabel("Delta *"), self.delta_field)
        lay.addLayout(form)

        hint = QLabel("Positive = restock   |   Negative = usage")
        hint.setStyleSheet("font-size: 11px;"
        lay.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        apply_btn = QPushButton("  Apply")
        apply_btn.setObjectName("primaryButton")
        apply_btn.setIcon(btn_icon_primary("check"))
        apply_btn.setIconSize(QSize(15, 15))
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(cancel)
        btn_row.addWidget(apply_btn)
        lay.addLayout(btn_row)

        outer.addWidget(container)

    def _apply(self):
        self._result = self.delta_field.value()
        self.accept()

    def get_result(self):
        return self._result


class InventoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._items = repo.get_all_inventory()
        self._build_ui()
        self._populate_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Inventory")
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
        self._table.setHorizontalHeaderLabels(["Ingredient", "Unit", "Stock", "Min. Stock", "Status", ""])
        _inv_hdr = self._table.horizontalHeader()
        _inv_hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        _inv_hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        _inv_hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        self._table.setColumnWidth(5, 110)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        card_layout.addWidget(self._table)

        root.addWidget(card)

    def _populate_table(self, items=None):
        data = items if items is not None else self._items
        self._table.setRowCount(0)
        for row, item in enumerate(data):
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(item["ingredient"]))
            self._table.setItem(row, 1, QTableWidgetItem(item["unit"]))
            self._table.setItem(row, 2, QTableWidgetItem(str(item["stock"])))
            self._table.setItem(row, 3, QTableWidgetItem(str(item["min_stock"])))

            status = item.get("status", "OK")
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("#EF4444" if status == "Low Stock" else "#22C55E"))
            self._table.setItem(row, 4, status_item)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            adj_btn = QPushButton("Adjust")
            adj_btn.setObjectName("secondaryButton")
            adj_btn.setFixedHeight(26)
            adj_btn.setCursor(Qt.PointingHandCursor)
            adj_btn.clicked.connect(lambda checked=False, i=item: self._adjust_stock(i))
            btn_layout.addWidget(adj_btn)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda checked=False, i=item: self._delete_item(i))
            btn_layout.addWidget(del_btn)

            self._table.setCellWidget(row, 5, btn_widget)

    def _open_add_dialog(self):
        dlg = AddInventoryDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                new_id = repo.add_inventory_item(result)
                if new_id:
                    result["id"] = new_id
                result["status"] = "Low Stock" if result["stock"] < result["min_stock"] else "OK"
                self._items.append(result)
                self._populate_table()
                success(self, message="Inventory item added successfully.")

    def _adjust_stock(self, item: dict):
        dlg = AdjustStockDialog(item, self)
        if dlg.exec() == QDialog.Accepted:
            delta = dlg.get_result()
            if delta is not None and item.get("id"):
                new_stock = repo.adjust_inventory_stock(item["id"], delta)
                if new_stock is not None:
                    item["stock"] = new_stock
                else:
                    item["stock"] = max(0.0, item["stock"] + delta)
                item["status"] = "Low Stock" if item["stock"] < item["min_stock"] else "OK"
                self._populate_table()
                success(self, message=f"Stock adjusted. New stock: {item['stock']} {item['unit']}")

    def _delete_item(self, item: dict):
        if not confirm(self, title="Delete Inventory Item",
                       message=f"Are you sure you want to delete '{item['ingredient']}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if item.get("id"):
            repo.delete_inventory_item(item["id"])
        if item in self._items:
            self._items.remove(item)
        self._populate_table()
        success(self, message="Inventory item deleted successfully.")

    def filter_search(self, text):
        q = text.lower()
        filtered = [i for i in self._items if q in i["ingredient"].lower() or q in i["unit"].lower()]
        self._populate_table(filtered)
