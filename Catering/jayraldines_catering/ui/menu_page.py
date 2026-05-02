from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QComboBox, QLineEdit, QDoubleSpinBox,
    QTabWidget, QTextEdit, QMessageBox, QScrollArea, QSpinBox,
    QCheckBox, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success
from utils.theme import ThemeManager
import utils.menu_store as menu_store
import utils.repository as repo

_CATEGORIES = ["Main Course", "Noodles", "Soup", "Vegetables", "Dessert", "Drinks", "Bread", "Other"]
_PACKAGES   = ["Budget", "Standard", "Premium", "Custom"]
_STATUSES   = ["Available", "Unavailable", "Out of Stock", "Seasonal"]


class MenuItemDialog(QDialog):
    def __init__(self, parent=None, item_data=None):
        super().__init__(parent)
        self._edit_mode = item_data is not None
        self._item_data = item_data or {}
        self.setWindowTitle("Edit Menu Item" if self._edit_mode else "Add Menu Item")
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
        title = QLabel("Edit Menu Item" if self._edit_mode else "Add Menu Item")
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
        if self._edit_mode:
            self.item_field.setText(self._item_data.get("item", ""))

        self.desc_field = QLineEdit()
        self.desc_field.setPlaceholderText("Short description")
        if self._edit_mode:
            self.desc_field.setText(self._item_data.get("description", ""))

        self.cat_field = QComboBox()
        self.cat_field.addItems(_CATEGORIES)
        if self._edit_mode:
            idx = self.cat_field.findText(self._item_data.get("category", ""))
            if idx >= 0:
                self.cat_field.setCurrentIndex(idx)

        self.pkg_field = QComboBox()
        self.pkg_field.addItems(_PACKAGES)
        if self._edit_mode:
            idx = self.pkg_field.findText(self._item_data.get("package", ""))
            if idx >= 0:
                self.pkg_field.setCurrentIndex(idx)

        self.price_field = QDoubleSpinBox()
        self.price_field.setPrefix("₱ ")
        self.price_field.setRange(0, 999999)
        self.price_field.setDecimals(2)
        self.price_field.setSingleStep(100)
        if self._edit_mode:
            self.price_field.setValue(float(self._item_data.get("price", 0)))

        self.status_field = QComboBox()
        self.status_field.addItems(_STATUSES)
        if self._edit_mode:
            idx = self.status_field.findText(self._item_data.get("status", "Available"))
            if idx >= 0:
                self.status_field.setCurrentIndex(idx)

        for lbl, widget in [
            ("Item Name *",  self.item_field),
            ("Description",  self.desc_field),
            ("Category",     self.cat_field),
            ("Package",      self.pkg_field),
            ("Price",        self.price_field),
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
        label = "Save Changes" if self._edit_mode else "  Save Item"
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
        name = self.item_field.text().strip()
        if not name:
            self._err.setText("Item name is required.")
            self._err.show()
            self.item_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        self._result = {
            "item":        name,
            "description": self.desc_field.text().strip(),
            "category":    self.cat_field.currentText(),
            "package":     self.pkg_field.currentText(),
            "price":       self.price_field.value(),
            "status":      self.status_field.currentText(),
        }
        self.accept()

    def get_result(self):
        return self._result


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


class PackageDialog(QDialog):
    def __init__(self, parent=None, pkg_data=None):
        super().__init__(parent)
        self._edit_mode = pkg_data is not None
        self._pkg_data = pkg_data or {}
        self._pkg_id = self._pkg_data.get("id")
        self.setWindowTitle("Edit Package" if self._edit_mode else "Add Package")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumWidth(720)
        self.setModal(True)
        self._result = None
        self._item_rows = []
        self._build_ui()
        self._load_menu_items()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Edit Package" if self._edit_mode else "Add Package")
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
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("e.g. Standard Package")
        if self._edit_mode:
            self.name_field.setText(self._pkg_data.get("name", ""))

        price_min_row = QHBoxLayout()
        self.price_field = QDoubleSpinBox()
        self.price_field.setPrefix("₱ ")
        self.price_field.setRange(0.01, 9999999)
        self.price_field.setDecimals(2)
        self.price_field.setSingleStep(100)
        if self._edit_mode:
            self.price_field.setValue(float(self._pkg_data.get("price_per_pax", 0)))

        min_pax_lbl = QLabel("  Min Pax:")
        min_pax_lbl.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        self.min_pax_field = QSpinBox()
        self.min_pax_field.setRange(1, 9999)
        self.min_pax_field.setSuffix(" pax")
        self.min_pax_field.setValue(int(self._pkg_data.get("min_pax", 1)) if self._edit_mode else 1)
        price_min_row.addWidget(self.price_field)
        price_min_row.addWidget(min_pax_lbl)
        price_min_row.addWidget(self.min_pax_field)
        price_min_row.addStretch()

        self.desc_field = QTextEdit()
        self.desc_field.setPlaceholderText("Describe what's included in this package...")
        self.desc_field.setFixedHeight(72)
        if self._edit_mode:
            self.desc_field.setPlainText(self._pkg_data.get("description", ""))

        form.addRow(QLabel("Package Name *"), self.name_field)
        form.addRow(QLabel("Price / Pax *"), price_min_row)
        form.addRow(QLabel("Description"), self.desc_field)
        lay.addLayout(form)

        items_lbl = QLabel("Included Menu Items")
        items_lbl.setStyleSheet("font-weight: 600; font-size: 13px; margin-top: 4px;")
        lay.addWidget(items_lbl)

        hint = QLabel("Check items to include in this package and set a custom price per item.")
        hint.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        lay.addWidget(hint)

        _is_light = not ThemeManager().is_dark()
        _sf_border = "#E2E8F0" if _is_light else "#374151"
        self._row_hover = "#F1F5F9" if _is_light else "#1F2937"
        _row_hover = self._row_hover
        scroll_frame = QFrame()
        scroll_frame.setObjectName("card")
        scroll_frame.setStyleSheet(f"#card {{ border: 1px solid {_sf_border}; border-radius: 8px; }}")
        scroll_frame.setFixedHeight(260)
        scroll_frame_lay = QVBoxLayout(scroll_frame)
        scroll_frame_lay.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._items_container = QWidget()
        self._items_layout = QVBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(12, 8, 12, 8)
        self._items_layout.setSpacing(2)
        self._items_layout.addStretch()

        scroll.setWidget(self._items_container)
        scroll_frame_lay.addWidget(scroll)
        lay.addWidget(scroll_frame)

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
        label = "Save Changes" if self._edit_mode else "  Add Package"
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

    def _load_menu_items(self):
        all_items = repo.get_all_menu_items()
        existing = {}
        if self._edit_mode and self._pkg_id:
            for row in repo.get_package_items(self._pkg_id):
                existing[row["menu_item_id"]] = float(row["custom_price"])

        categories = {}
        for item in all_items:
            cat = item.get("category", "Other")
            categories.setdefault(cat, []).append(item)

        stretch = self._items_layout.takeAt(self._items_layout.count() - 1)

        for cat, items in sorted(categories.items()):
            cat_lbl = QLabel(cat)
            cat_lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 600; padding: 6px 0 2px 0;")
            self._items_layout.addWidget(cat_lbl)

            for item in items:
                item_id = item.get("id")
                row_widget = QWidget()
                row_widget.setStyleSheet(f"QWidget {{ border-radius: 4px; }} QWidget:hover {{ background: {self._row_hover}; }}")
                row_lay = QHBoxLayout(row_widget)
                row_lay.setContentsMargins(4, 4, 4, 4)
                row_lay.setSpacing(10)

                chk = QCheckBox()
                chk.setChecked(item_id in existing)
                row_lay.addWidget(chk)

                name_lbl = QLabel(item.get("item", ""))
                name_lbl.setMinimumWidth(180)
                name_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                row_lay.addWidget(name_lbl)

                orig_price_lbl = QLabel(f"(Base: ₱{float(item.get('price', 0)):,.2f})")
                orig_price_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")
                row_lay.addWidget(orig_price_lbl)

                custom_price = QDoubleSpinBox()
                custom_price.setPrefix("₱ ")
                custom_price.setRange(0, 9999999)
                custom_price.setDecimals(2)
                custom_price.setSingleStep(50)
                custom_price.setFixedWidth(130)
                custom_price.setToolTip("Custom price for this item in the package")
                if item_id in existing:
                    custom_price.setValue(existing[item_id])
                else:
                    custom_price.setValue(float(item.get("price", 0)))

                def _toggle_price(state, sp=custom_price):
                    sp.setEnabled(bool(state))

                chk.stateChanged.connect(_toggle_price)
                custom_price.setEnabled(item_id in existing)
                row_lay.addWidget(custom_price)

                self._items_layout.addWidget(row_widget)
                self._item_rows.append({
                    "item_id": item_id,
                    "chk": chk,
                    "price_spin": custom_price,
                })

        if stretch:
            self._items_layout.addItem(stretch)
        else:
            self._items_layout.addStretch()

    def _save(self):
        name = self.name_field.text().strip()
        if not name:
            self._err.setText("Package name is required.")
            self._err.show()
            self.name_field.setStyleSheet("border: 1px solid #E11D48;")
            return
        selected_items = [
            {"menu_item_id": r["item_id"], "custom_price": r["price_spin"].value()}
            for r in self._item_rows
            if r["chk"].isChecked()
        ]
        self._result = {
            "name":          name,
            "price_per_pax": self.price_field.value(),
            "min_pax":       self.min_pax_field.value(),
            "description":   self.desc_field.toPlainText().strip(),
            "items":         selected_items,
        }
        self.accept()

    def get_result(self):
        return self._result


class MenuPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._populate_table()
        self._populate_packages_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Menu")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

        self._build_menu_items_tab()
        self._build_packages_tab()

    def _build_menu_items_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        add_btn = QPushButton("  Add Item")
        add_btn.setObjectName("primaryButton")
        add_btn.setIcon(btn_icon_primary("plus"))
        add_btn.setIconSize(QSize(15, 15))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._open_add_dialog)
        toolbar.addWidget(add_btn)
        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        toolbar.addWidget(export_btn)
        lay.addLayout(toolbar)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 7)
        self._table.setObjectName("menuTable")
        self._table.setHorizontalHeaderLabels(["Item", "Category", "Package", "Price", "Status", "", ""])
        _mn_hdr = self._table.horizontalHeader()
        _mn_hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        _mn_hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        _mn_hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        _mn_hdr.setSectionResizeMode(6, QHeaderView.Fixed)
        self._table.setColumnWidth(5, 40)
        self._table.setColumnWidth(6, 40)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setMouseTracking(False)
        self._table.setStyleSheet("QTableWidget::item:hover { background: transparent; } QTableWidget::item:selected { background: transparent; }")
        card_layout.addWidget(self._table)
        lay.addWidget(card)

        self._tabs.addTab(tab, "Menu Items")

    def _build_packages_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        add_pkg_btn = QPushButton("  Add Package")
        add_pkg_btn.setObjectName("primaryButton")
        add_pkg_btn.setIcon(btn_icon_primary("plus"))
        add_pkg_btn.setIconSize(QSize(15, 15))
        add_pkg_btn.setCursor(Qt.PointingHandCursor)
        add_pkg_btn.clicked.connect(self._open_add_package_dialog)
        toolbar.addWidget(add_pkg_btn)
        lay.addLayout(toolbar)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._pkg_table = QTableWidget(0, 7)
        self._pkg_table.setObjectName("menuTable")
        self._pkg_table.setHorizontalHeaderLabels(["Package Name", "Price / Pax", "Min Pax", "Items", "Description", "", ""])
        _hdr = self._pkg_table.horizontalHeader()
        _hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        _hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        _hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        _hdr.setSectionResizeMode(4, QHeaderView.Stretch)
        _hdr.setSectionResizeMode(5, QHeaderView.Fixed)
        _hdr.setSectionResizeMode(6, QHeaderView.Fixed)
        self._pkg_table.setColumnWidth(5, 40)
        self._pkg_table.setColumnWidth(6, 40)
        self._pkg_table.setAlternatingRowColors(True)
        self._pkg_table.setSelectionMode(QTableWidget.NoSelection)
        self._pkg_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._pkg_table.verticalHeader().setVisible(False)
        self._pkg_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._pkg_table.setMouseTracking(False)
        self._pkg_table.setStyleSheet("QTableWidget::item:hover { background: transparent; } QTableWidget::item:selected { background: transparent; }")
        card_layout.addWidget(self._pkg_table)
        lay.addWidget(card)

        self._tabs.addTab(tab, "Packages")

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

            edit_btn = QPushButton()
            edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(14, 14)))
            edit_btn.setIconSize(QSize(14, 14))
            edit_btn.setFixedSize(32, 32)
            edit_btn.setStyleSheet("background: transparent; border: none;")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setToolTip("Edit item")
            edit_btn.clicked.connect(self._edit_item)
            self._table.setCellWidget(row, 5, edit_btn)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(self._delete_item)
            self._table.setCellWidget(row, 6, del_btn)

    def _edit_item(self):
        btn = self.sender()
        for r in range(self._table.rowCount()):
            if self._table.cellWidget(r, 5) is btn:
                items = repo.get_all_menu_items() or menu_store.all_items()
                item = items[r] if r < len(items) else {}
                dlg = MenuItemDialog(self, item_data=item)
                if dlg.exec() == QDialog.Accepted:
                    result = dlg.get_result()
                    if result and item.get("id"):
                        repo.update_menu_item(item["id"], result)
                        self._populate_table()
                        success(self, message="Menu item updated successfully.")
                return

    def _delete_item(self):
        btn = self.sender()
        for r in range(self._table.rowCount()):
            if self._table.cellWidget(r, 6) is btn:
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
        dlg = MenuItemDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                repo.add_menu_item(result)
                self._populate_table()
                success(self, message="Menu item added successfully.")

    def _populate_packages_table(self):
        packages = repo.get_all_packages()
        self._pkg_table.setRowCount(0)
        self._packages_data = packages
        for row, pkg in enumerate(packages):
            self._pkg_table.insertRow(row)
            self._pkg_table.setItem(row, 0, QTableWidgetItem(pkg["name"]))

            price_item = QTableWidgetItem(f"₱{float(pkg['price_per_pax']):,.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._pkg_table.setItem(row, 1, price_item)

            min_pax_item = QTableWidgetItem(f"{pkg.get('min_pax', 1)} pax")
            min_pax_item.setTextAlignment(Qt.AlignCenter)
            self._pkg_table.setItem(row, 2, min_pax_item)

            pkg_items = repo.get_package_items(pkg["id"]) if pkg.get("id") else []
            item_count = len(pkg_items)
            if item_count > 0:
                names = ", ".join(i["item_name"] for i in pkg_items[:3])
                if item_count > 3:
                    names += f" +{item_count - 3} more"
                items_cell = QTableWidgetItem(f"{item_count} ({names})")
            else:
                items_cell = QTableWidgetItem("No items")
                items_cell.setForeground(QColor("#6B7280"))
            self._pkg_table.setItem(row, 3, items_cell)

            self._pkg_table.setItem(row, 4, QTableWidgetItem(pkg.get("description", "")))

            edit_btn = QPushButton()
            edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(14, 14)))
            edit_btn.setIconSize(QSize(14, 14))
            edit_btn.setFixedSize(32, 32)
            edit_btn.setStyleSheet("background: transparent; border: none;")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setToolTip("Edit package")
            edit_btn.clicked.connect(self._edit_package)
            self._pkg_table.setCellWidget(row, 5, edit_btn)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete package")
            del_btn.clicked.connect(self._delete_package)
            self._pkg_table.setCellWidget(row, 6, del_btn)

    def _open_add_package_dialog(self):
        dlg = PackageDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                pkg_id = repo.add_package(result)
                if pkg_id:
                    repo.set_package_items(pkg_id, result.get("items", []))
                    self._populate_packages_table()
                    success(self, message="Package added successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to add package. Name may already exist.")

    def _edit_package(self):
        btn = self.sender()
        for r in range(self._pkg_table.rowCount()):
            if self._pkg_table.cellWidget(r, 5) is btn:
                pkg = self._packages_data[r] if r < len(self._packages_data) else {}
                dlg = PackageDialog(self, pkg_data=pkg)
                if dlg.exec() == QDialog.Accepted:
                    result = dlg.get_result()
                    if result and pkg.get("id"):
                        ok = repo.update_package(pkg["id"], result)
                        if ok:
                            repo.set_package_items(pkg["id"], result.get("items", []))
                            self._populate_packages_table()
                            success(self, message="Package updated successfully.")
                        else:
                            QMessageBox.warning(self, "Error", "Failed to update package.")
                return

    def _delete_package(self):
        btn = self.sender()
        for r in range(self._pkg_table.rowCount()):
            if self._pkg_table.cellWidget(r, 6) is btn:
                pkg = self._packages_data[r] if r < len(self._packages_data) else {}
                pkg_name = pkg.get("name", "")
                if not confirm(self, title="Delete Package",
                               message=f"Delete package '{pkg_name}'? Packages linked to existing bookings cannot be deleted.",
                               confirm_label="Delete", danger=True):
                    return
                ok = repo.delete_package(pkg.get("id"))
                if ok:
                    self._populate_packages_table()
                    success(self, message="Package deleted successfully.")
                else:
                    QMessageBox.warning(self, "Cannot Delete",
                                        "This package is linked to existing bookings and cannot be deleted.")
                return

    def filter_search(self, text):
        q = text.lower()
        self._filter_q = q
        self._populate_table()

