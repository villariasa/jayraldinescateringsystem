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
from components.dialogs import confirm, success, prompt_file_saved
from utils.theme import ThemeManager
import utils.menu_store as menu_store
import utils.repository as repo
from utils.data_loader import run_async

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


class AddMultipleMenuItemsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Multiple Menu Items")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(940, 540)
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
        title = QLabel("Add Multiple Menu Items")
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

        sub = QLabel("Quickly add multiple dishes and culinary offerings to the menu:")
        sub.setObjectName("subtitle")
        lay.addWidget(sub)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Item Name *", "Category *", "Package Tier", "Price (₱) *", "Status", "Description"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
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
            QTableWidget::item { padding: 4px 6px; color: #F9FAFB; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QTableWidget::item:selected { background-color: rgba(225,29,72,0.25); color: #FFFFFF; }
            QHeaderView::section { background-color: #111827; color: #9CA3AF; font-weight: 700; font-size: 11px; padding: 10px 8px; border: none; border-bottom: 1px solid rgba(255,255,255,0.1); }
        """)

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
        save = QPushButton("  Save All Items")
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
        name_edit.setPlaceholderText("e.g. Special Pork Humba")
        name_edit.setFixedHeight(34)
        name_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 0, name_edit)

        cat_combo = QComboBox()
        cat_combo.addItems(_CATEGORIES)
        cat_combo.setFixedHeight(34)
        cat_combo.setStyleSheet("QComboBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QComboBox:focus { border-color: #E11D48; } QComboBox QAbstractItemView { background: #1E293B; color: #FFFFFF; selection-background-color: #E11D48; selection-color: #FFFFFF; border: 1px solid #334155; }")
        self.table.setCellWidget(r, 1, cat_combo)

        pkg_combo = QComboBox()
        pkg_combo.addItems(_PACKAGES)
        pkg_combo.setCurrentText("Standard")
        pkg_combo.setFixedHeight(34)
        pkg_combo.setStyleSheet("QComboBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QComboBox:focus { border-color: #E11D48; } QComboBox QAbstractItemView { background: #1E293B; color: #FFFFFF; selection-background-color: #E11D48; selection-color: #FFFFFF; border: 1px solid #334155; }")
        self.table.setCellWidget(r, 2, pkg_combo)

        price_spin = QDoubleSpinBox()
        price_spin.setRange(0, 999999)
        price_spin.setPrefix("₱ ")
        price_spin.setDecimals(2)
        price_spin.setSingleStep(50)
        price_spin.setValue(350.0)
        price_spin.setFixedHeight(34)
        price_spin.setStyleSheet("QDoubleSpinBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QDoubleSpinBox:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 3, price_spin)

        status_combo = QComboBox()
        status_combo.addItems(_STATUSES)
        status_combo.setCurrentText("Available")
        status_combo.setFixedHeight(34)
        status_combo.setStyleSheet("QComboBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QComboBox:focus { border-color: #E11D48; } QComboBox QAbstractItemView { background: #1E293B; color: #FFFFFF; selection-background-color: #E11D48; selection-color: #FFFFFF; border: 1px solid #334155; }")
        self.table.setCellWidget(r, 4, status_combo)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("Short description / serving size")
        desc_edit.setFixedHeight(34)
        desc_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 5, desc_edit)

    def _delete_selected_row(self):
        curr = self.table.currentRow()
        if curr >= 0:
            self.table.removeRow(curr)

    def _save_all(self):
        rows_to_save = []
        for r in range(self.table.rowCount()):
            name_w = self.table.cellWidget(r, 0)
            cat_w = self.table.cellWidget(r, 1)
            pkg_w = self.table.cellWidget(r, 2)
            price_w = self.table.cellWidget(r, 3)
            status_w = self.table.cellWidget(r, 4)
            desc_w = self.table.cellWidget(r, 5)

            name = name_w.text().strip() if isinstance(name_w, QLineEdit) else ""
            cat = cat_w.currentText().strip() if isinstance(cat_w, QComboBox) else "Main Course"
            pkg = pkg_w.currentText().strip() if isinstance(pkg_w, QComboBox) else "Standard"
            price = price_w.value() if isinstance(price_w, QDoubleSpinBox) else 0.0
            status = status_w.currentText().strip() if isinstance(status_w, QComboBox) else "Available"
            desc = desc_w.text().strip() if isinstance(desc_w, QLineEdit) else ""

            if not name:
                continue

            rows_to_save.append({
                "item": name,
                "category": cat,
                "package": pkg,
                "price": price,
                "status": status,
                "description": desc,
            })

        if not rows_to_save:
            self._err.setText("Please enter at least one menu item.")
            self._err.show()
            return

        saved = 0
        for item_data in rows_to_save:
            res = repo.add_menu_item(item_data)
            if res:
                saved += 1

        self._added_count = saved
        self.accept()


class AddMultiplePackagesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Multiple Packages")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(880, 520)
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
        title = QLabel("Add Multiple Packages")
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

        sub = QLabel("Quickly add multiple catering packages:")
        sub.setObjectName("subtitle")
        lay.addWidget(sub)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Package Name *", "Price per Pax (₱) *", "Min Pax *", "Description"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
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
            QTableWidget::item { padding: 4px 6px; color: #F9FAFB; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QTableWidget::item:selected { background-color: rgba(225,29,72,0.25); color: #FFFFFF; }
            QHeaderView::section { background-color: #111827; color: #9CA3AF; font-weight: 700; font-size: 11px; padding: 10px 8px; border: none; border-bottom: 1px solid rgba(255,255,255,0.1); }
        """)

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
        save = QPushButton("  Save All Packages")
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
        name_edit.setPlaceholderText("e.g. Platinum Buffet Feast")
        name_edit.setFixedHeight(34)
        name_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 0, name_edit)

        price_spin = QDoubleSpinBox()
        price_spin.setRange(0, 999999)
        price_spin.setPrefix("₱ ")
        price_spin.setDecimals(2)
        price_spin.setSingleStep(50)
        price_spin.setValue(450.0)
        price_spin.setFixedHeight(34)
        price_spin.setStyleSheet("QDoubleSpinBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QDoubleSpinBox:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 1, price_spin)

        pax_spin = QSpinBox()
        pax_spin.setRange(1, 5000)
        pax_spin.setValue(50)
        pax_spin.setFixedHeight(34)
        pax_spin.setStyleSheet("QSpinBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QSpinBox:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 2, pax_spin)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("Package inclusions and description")
        desc_edit.setFixedHeight(34)
        desc_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 3, desc_edit)

    def _delete_selected_row(self):
        curr = self.table.currentRow()
        if curr >= 0:
            self.table.removeRow(curr)

    def _save_all(self):
        rows_to_save = []
        for r in range(self.table.rowCount()):
            name_w = self.table.cellWidget(r, 0)
            price_w = self.table.cellWidget(r, 1)
            pax_w = self.table.cellWidget(r, 2)
            desc_w = self.table.cellWidget(r, 3)

            name = name_w.text().strip() if isinstance(name_w, QLineEdit) else ""
            price = price_w.value() if isinstance(price_w, QDoubleSpinBox) else 0.0
            min_pax = pax_w.value() if isinstance(pax_w, QSpinBox) else 50
            desc = desc_w.text().strip() if isinstance(desc_w, QLineEdit) else ""

            if not name:
                continue

            rows_to_save.append({
                "name": name,
                "price_per_pax": price,
                "min_pax": min_pax,
                "description": desc,
                "items": []
            })

        if not rows_to_save:
            self._err.setText("Please enter at least one package.")
            self._err.show()
            return

        saved = 0
        for pkg_data in rows_to_save:
            res = repo.add_package(pkg_data)
            if res:
                saved += 1

        self._added_count = saved
        self.accept()


class MenuPage(QWidget):
    def __init__(self):
        super().__init__()
        self._dirty = True
        self._selected_item_ids = set()
        self._selected_pkg_ids = set()
        self._item_checkboxes = {}
        self._pkg_checkboxes = {}
        self._build_ui()
        self._do_reload()

        try:
            from utils.signals import app_events
            app_events().data_changed.connect(self._mark_dirty)
        except Exception:
            pass

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
        run_async(self, repo.get_all_menu_items, self._on_menu_items_loaded)
        run_async(self, repo.get_all_packages, self._on_packages_loaded)

    def _on_menu_items_loaded(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        self._menu_items_data = data if data else (menu_store.all_items() if hasattr(menu_store, "all_items") else [])
        self._populate_table()

    def _on_packages_loaded(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        self._packages_cache = data or []
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

        multi_add_btn = QPushButton("  + Quick Multi-Add")
        multi_add_btn.setObjectName("secondaryButton")
        multi_add_btn.setCursor(Qt.PointingHandCursor)
        multi_add_btn.clicked.connect(self._open_multi_add_items_dialog)
        toolbar.addWidget(multi_add_btn)

        import_btn = QPushButton("  Import")
        import_btn.setObjectName("secondaryButton")
        import_btn.setIcon(btn_icon_secondary("export"))
        import_btn.setIconSize(QSize(15, 15))
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._open_import_items_dialog)
        toolbar.addWidget(import_btn)

        export_btn = QPushButton("  Export")
        export_btn.setObjectName("secondaryButton")
        export_btn.setIcon(btn_icon_secondary("export"))
        export_btn.setIconSize(QSize(15, 15))
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_menu_items)
        toolbar.addWidget(export_btn)

        lay.addLayout(toolbar)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        # Batch Selection Toolbar for Menu Items
        batch_toolbar = QHBoxLayout()
        batch_toolbar.setContentsMargins(4, 0, 4, 4)
        batch_toolbar.setSpacing(12)

        self._cb_select_all_items = QCheckBox("Select All")
        self._cb_select_all_items.setStyleSheet("QCheckBox { font-weight: 600; font-size: 13px; color: #9CA3AF; }")
        self._cb_select_all_items.stateChanged.connect(self._toggle_select_all_items)
        batch_toolbar.addWidget(self._cb_select_all_items)

        self._lbl_items_selected_count = QLabel("0 selected")
        self._lbl_items_selected_count.setStyleSheet("font-size: 12px; color: #6B7280; font-weight: 600;")
        batch_toolbar.addWidget(self._lbl_items_selected_count)

        batch_toolbar.addStretch()

        self._btn_delete_selected_items = QPushButton("  Delete Selected")
        self._btn_delete_selected_items.setIcon(btn_icon_red("trash"))
        self._btn_delete_selected_items.setIconSize(QSize(13, 13))
        self._btn_delete_selected_items.setCursor(Qt.PointingHandCursor)
        self._btn_delete_selected_items.setEnabled(False)
        self._btn_delete_selected_items.setStyleSheet(
            "QPushButton { background: rgba(225,29,72,0.15); border: 1px solid rgba(225,29,72,0.3); color: #E11D48; border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(225,29,72,0.25); border-color: #E11D48; }"
            "QPushButton:disabled { opacity: 0.35; background: rgba(255,255,255,0.04); border-color: transparent; color: #6B7280; }"
        )
        self._btn_delete_selected_items.clicked.connect(self._delete_selected_menu_items)
        batch_toolbar.addWidget(self._btn_delete_selected_items)

        card_layout.addLayout(batch_toolbar)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        card_layout.addWidget(div)

        self.menu_scroll = QScrollArea()
        self.menu_scroll.setWidgetResizable(True)
        self.menu_scroll.setFrameShape(QFrame.NoFrame)
        self.menu_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.menu_scroll.setStyleSheet("background: transparent;")

        self.menu_container = QWidget()
        self.menu_container.setStyleSheet("background: transparent;")
        self.menu_cards_layout = QVBoxLayout(self.menu_container)
        self.menu_cards_layout.setContentsMargins(0, 0, 10, 0)
        self.menu_cards_layout.setSpacing(12)

        self.menu_scroll.setWidget(self.menu_container)
        card_layout.addWidget(self.menu_scroll)
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

        multi_pkg_btn = QPushButton("  + Quick Multi-Add")
        multi_pkg_btn.setObjectName("secondaryButton")
        multi_pkg_btn.setCursor(Qt.PointingHandCursor)
        multi_pkg_btn.clicked.connect(self._open_multi_add_packages_dialog)
        toolbar.addWidget(multi_pkg_btn)

        export_pkg_btn = QPushButton("  Export")
        export_pkg_btn.setObjectName("secondaryButton")
        export_pkg_btn.setIcon(btn_icon_secondary("export"))
        export_pkg_btn.setIconSize(QSize(15, 15))
        export_pkg_btn.setCursor(Qt.PointingHandCursor)
        export_pkg_btn.clicked.connect(self._export_packages)
        toolbar.addWidget(export_pkg_btn)

        lay.addLayout(toolbar)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        # Batch Selection Toolbar for Packages
        batch_toolbar = QHBoxLayout()
        batch_toolbar.setContentsMargins(4, 0, 4, 4)
        batch_toolbar.setSpacing(12)

        self._cb_select_all_pkgs = QCheckBox("Select All")
        self._cb_select_all_pkgs.setStyleSheet("QCheckBox { font-weight: 600; font-size: 13px; color: #9CA3AF; }")
        self._cb_select_all_pkgs.stateChanged.connect(self._toggle_select_all_packages)
        batch_toolbar.addWidget(self._cb_select_all_pkgs)

        self._lbl_pkgs_selected_count = QLabel("0 selected")
        self._lbl_pkgs_selected_count.setStyleSheet("font-size: 12px; color: #6B7280; font-weight: 600;")
        batch_toolbar.addWidget(self._lbl_pkgs_selected_count)

        batch_toolbar.addStretch()

        self._btn_delete_selected_pkgs = QPushButton("  Delete Selected")
        self._btn_delete_selected_pkgs.setIcon(btn_icon_red("trash"))
        self._btn_delete_selected_pkgs.setIconSize(QSize(13, 13))
        self._btn_delete_selected_pkgs.setCursor(Qt.PointingHandCursor)
        self._btn_delete_selected_pkgs.setEnabled(False)
        self._btn_delete_selected_pkgs.setStyleSheet(
            "QPushButton { background: rgba(225,29,72,0.15); border: 1px solid rgba(225,29,72,0.3); color: #E11D48; border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(225,29,72,0.25); border-color: #E11D48; }"
            "QPushButton:disabled { opacity: 0.35; background: rgba(255,255,255,0.04); border-color: transparent; color: #6B7280; }"
        )
        self._btn_delete_selected_pkgs.clicked.connect(self._delete_selected_packages)
        batch_toolbar.addWidget(self._btn_delete_selected_pkgs)

        card_layout.addLayout(batch_toolbar)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        card_layout.addWidget(div)

        self.pkg_scroll = QScrollArea()
        self.pkg_scroll.setWidgetResizable(True)
        self.pkg_scroll.setFrameShape(QFrame.NoFrame)
        self.pkg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.pkg_scroll.setStyleSheet("background: transparent;")

        self.pkg_container = QWidget()
        self.pkg_container.setStyleSheet("background: transparent;")
        self.pkg_cards_layout = QVBoxLayout(self.pkg_container)
        self.pkg_cards_layout.setContentsMargins(0, 0, 10, 0)
        self.pkg_cards_layout.setSpacing(12)

        self.pkg_scroll.setWidget(self.pkg_container)
        card_layout.addWidget(self.pkg_scroll)
        lay.addWidget(card)

        self._tabs.addTab(tab, "Packages")

    def _toggle_select_all_items(self, state):
        items = getattr(self, "_menu_items_data", []) or []
        if state == 2:  # Checked
            for item in items:
                if item.get("id"):
                    self._selected_item_ids.add(item["id"])
        else:
            self._selected_item_ids.clear()

        for cid, cb in self._item_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(cid in self._selected_item_ids)
            cb.blockSignals(False)

        self._update_items_selection_ui()

    def _toggle_select_all_packages(self, state):
        pkgs = getattr(self, "_packages_data", []) or []
        if state == 2:
            for p in pkgs:
                if p.get("id"):
                    self._selected_pkg_ids.add(p["id"])
        else:
            self._selected_pkg_ids.clear()

        for pid, cb in self._pkg_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(pid in self._selected_pkg_ids)
            cb.blockSignals(False)

        self._update_pkgs_selection_ui()

    def _update_items_selection_ui(self):
        count = len(self._selected_item_ids)
        self._lbl_items_selected_count.setText(f"{count} selected")
        self._btn_delete_selected_items.setEnabled(count > 0)
        if count > 0:
            self._btn_delete_selected_items.setText(f"  Delete Selected ({count})")
        else:
            self._btn_delete_selected_items.setText("  Delete Selected")

    def _update_pkgs_selection_ui(self):
        count = len(self._selected_pkg_ids)
        self._lbl_pkgs_selected_count.setText(f"{count} selected")
        self._btn_delete_selected_pkgs.setEnabled(count > 0)
        if count > 0:
            self._btn_delete_selected_pkgs.setText(f"  Delete Selected ({count})")
        else:
            self._btn_delete_selected_pkgs.setText("  Delete Selected")

    def _populate_table(self):
        self.menu_container.setUpdatesEnabled(False)
        self._item_checkboxes.clear()
        try:
            while self.menu_cards_layout.count():
                item = self.menu_cards_layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().deleteLater()

            q = getattr(self, "_filter_q", "")
            items = getattr(self, "_menu_items_data", None)
            if items is None:
                items = repo.get_all_menu_items() or menu_store.all_items()
            if q:
                items = [i for i in items if q in i["item"].lower() or q in i["category"].lower() or q in i["package"].lower()]

            if not items:
                empty_lbl = QLabel("No menu items found.")
                empty_lbl.setObjectName("subtitle")
                empty_lbl.setAlignment(Qt.AlignCenter)
                self.menu_cards_layout.addWidget(empty_lbl)
            else:
                for item in items:
                    m_card = self._create_menu_item_card(item)
                    self.menu_cards_layout.addWidget(m_card)

            self.menu_cards_layout.addStretch()
            self._update_items_selection_ui()
        finally:
            self.menu_container.setUpdatesEnabled(True)

    def _create_menu_item_card(self, item: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(14)

        item_id = item.get("id")

        # Multi-select Checkbox
        chk = QCheckBox()
        chk.setChecked(item_id in self._selected_item_ids if item_id else False)
        chk.stateChanged.connect(lambda state, iid=item_id: self._on_item_checked(iid, state))
        if item_id:
            self._item_checkboxes[item_id] = chk
        lay.addWidget(chk)

        c1 = QVBoxLayout()
        c1.setSpacing(2)
        name_lbl = QLabel(item["item"])
        name_lbl.setStyleSheet("font-weight: 700; font-size: 15px;")
        cat_lbl = QLabel(f"Category: {item['category']}  |  Package: {item['package']}")
        cat_lbl.setObjectName("subtitle")
        c1.addWidget(name_lbl)
        c1.addWidget(cat_lbl)
        lay.addLayout(c1, 3)

        price_lbl = QLabel(f"₱{item['price']:,.2f}")
        price_lbl.setStyleSheet("font-weight: 800; font-size: 15px; color: #F59E0B;")
        lay.addWidget(price_lbl, alignment=Qt.AlignVCenter)

        status_colors = {"Available": "#22C55E", "Unavailable": "#EF4444", "Out of Stock": "#F97316", "Seasonal": "#F59E0B"}
        s_color = status_colors.get(item["status"], "#9CA3AF")
        status_lbl = QLabel(item["status"])
        status_lbl.setStyleSheet(f"font-weight: 700; font-size: 11px; color: {s_color}; padding: 4px 10px; background: rgba(255,255,255,0.05); border-radius: 8px;")
        lay.addWidget(status_lbl, alignment=Qt.AlignVCenter)

        actions_w = QFrame()
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(13, 13)))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("background: transparent; border: none;")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setToolTip("Edit item")
        edit_btn.clicked.connect(lambda _, it=item: self._edit_item_dict(it))

        del_btn = QPushButton()
        del_btn.setIcon(btn_icon_red("trash"))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("background: transparent; border: none;")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("Delete item")
        del_btn.clicked.connect(lambda _, it=item: self._delete_item_dict(it))

        actions_l.addWidget(edit_btn)
        actions_l.addWidget(del_btn)
        lay.addWidget(actions_w)

        return card

    def _on_item_checked(self, item_id: int, state: int):
        if not item_id:
            return
        if state == 2:
            self._selected_item_ids.add(item_id)
        else:
            self._selected_item_ids.discard(item_id)
        self._update_items_selection_ui()

    def _edit_item_dict(self, item: dict):
        dlg = MenuItemDialog(self, item_data=item)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result and item.get("id"):
                repo.update_menu_item(item["id"], result)
                self._menu_items_data = repo.get_all_menu_items() or menu_store.all_items()
                self._populate_table()
                try:
                    from utils.signals import app_events
                    app_events().data_changed.emit()
                except Exception:
                    pass
                success(self, message="Menu item updated successfully.")

    def _delete_item_dict(self, item: dict):
        item_name = item.get("item", "")
        item_id = item.get("id")
        if not confirm(self, title="Delete Menu Item",
                       message=f"Are you sure you want to delete '{item_name}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        repo.delete_menu_item(item_id)
        self._menu_items_data = repo.get_all_menu_items() or menu_store.all_items()
        self._populate_table()
        try:
            from utils.signals import app_events
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message="Menu item deleted successfully.")

    def _delete_selected_menu_items(self):
        if not self._selected_item_ids:
            return
        count = len(self._selected_item_ids)
        if not confirm(self, title="Delete Multiple Menu Items",
                       message=f"Are you sure you want to permanently delete {count} selected menu item(s)?\nThis cannot be undone.",
                       confirm_label=f"Delete {count} Items", danger=True):
            return

        deleted = repo.delete_multiple_menu_items(list(self._selected_item_ids))
        self._selected_item_ids.clear()
        self.reload()
        try:
            from utils.signals import app_events
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message=f"Successfully deleted {deleted} menu item(s).")

    def _open_add_dialog(self):
        dlg = MenuItemDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                repo.add_menu_item(result)
                self._menu_items_data = repo.get_all_menu_items() or menu_store.all_items()
                self._populate_table()
                try:
                    from utils.signals import app_events
                    app_events().data_changed.emit()
                except Exception:
                    pass
                success(self, message="Menu item added successfully.")

    def _open_multi_add_items_dialog(self):
        dlg = AddMultipleMenuItemsDialog(self)
        if dlg.exec():
            self.reload()
            try:
                from utils.signals import app_events
                app_events().data_changed.emit()
            except Exception:
                pass
            success(self, message=f"Added {dlg._added_count} menu item(s) successfully.")

    def _open_import_items_dialog(self):
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="menu_items", parent=self)
        if dlg.exec():
            self.reload()
            try:
                from utils.signals import app_events
                app_events().data_changed.emit()
            except Exception:
                pass

    def _export_menu_items(self):
        import csv
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Menu Items", "menu_items.csv", "CSV Files (*.csv)")
        if not path:
            return
        items = getattr(self, "_menu_items_data", []) or []
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Item Name", "Category", "Package", "Price", "Status", "Description"])
            for it in items:
                writer.writerow([it.get("item", ""), it.get("category", ""), it.get("package", ""), it.get("price", 0), it.get("status", ""), it.get("description", "")])
        prompt_file_saved(self, path, title="Menu Items Exported", message="Menu items list exported successfully.")

    def _populate_packages_table(self):
        if hasattr(self, "pkg_container"):
            self.pkg_container.setUpdatesEnabled(False)
        self._pkg_checkboxes.clear()
        try:
            while self.pkg_cards_layout.count():
                item = self.pkg_cards_layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().deleteLater()

            packages = getattr(self, "_packages_cache", None)
            if packages is None:
                packages = repo.get_all_packages()
            self._packages_data = packages

            if not packages:
                empty_lbl = QLabel("No packages found.")
                empty_lbl.setStyleSheet("color: #9CA3AF; font-size: 13px; padding: 24px;")
                empty_lbl.setAlignment(Qt.AlignCenter)
                self.pkg_cards_layout.addWidget(empty_lbl)
            else:
                for pkg in packages:
                    p_card = self._create_package_card(pkg)
                    self.pkg_cards_layout.addWidget(p_card)

            self.pkg_cards_layout.addStretch()
            self._update_pkgs_selection_ui()
        finally:
            if hasattr(self, "pkg_container"):
                self.pkg_container.setUpdatesEnabled(True)

    def _create_package_card(self, pkg: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(14)

        pkg_id = pkg.get("id")

        # Multi-select Checkbox
        chk = QCheckBox()
        chk.setChecked(pkg_id in self._selected_pkg_ids if pkg_id else False)
        chk.stateChanged.connect(lambda state, pid=pkg_id: self._on_pkg_checked(pid, state))
        if pkg_id:
            self._pkg_checkboxes[pkg_id] = chk
        lay.addWidget(chk)

        c1 = QVBoxLayout()
        c1.setSpacing(2)
        name_lbl = QLabel(pkg["name"])
        name_lbl.setStyleSheet("font-weight: 700; font-size: 15px;")
        desc_lbl = QLabel(pkg.get("description", "No description"))
        desc_lbl.setObjectName("subtitle")
        desc_lbl.setWordWrap(True)
        c1.addWidget(name_lbl)
        c1.addWidget(desc_lbl)
        lay.addLayout(c1, 3)

        pkg_items = pkg.get("items")
        if pkg_items is None and pkg.get("id"):
            pkg_items = repo.get_package_items(pkg["id"])
        pkg_items = pkg_items or []
        item_count = len(pkg_items)
        if item_count > 0:
            names = ", ".join(i.get("item_name", "") for i in pkg_items[:3] if i.get("item_name"))
            if item_count > 3:
                names += f" +{item_count - 3} more"
            items_str = f"📦 {item_count} items ({names})"
        else:
            items_str = "📦 No items"
        items_lbl = QLabel(items_str)
        items_lbl.setObjectName("subtitle")
        items_lbl.setWordWrap(True)
        lay.addWidget(items_lbl, 2)

        p_info = QVBoxLayout()
        p_info.setSpacing(2)
        p_val = QLabel(f"₱{float(pkg['price_per_pax']):,.2f} / pax")
        p_val.setStyleSheet("font-weight: 800; font-size: 14px; color: #F59E0B;")
        min_p = QLabel(f"Min: {pkg.get('min_pax', 1)} pax")
        min_p.setStyleSheet("font-size: 11px; color: #6B7280;")
        p_info.addWidget(p_val)
        p_info.addWidget(min_p)
        lay.addLayout(p_info, 2)

        actions_w = QFrame()
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(13, 13)))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("background: transparent; border: none;")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setToolTip("Edit package")
        edit_btn.clicked.connect(lambda _, p=pkg: self._edit_package_dict(p))

        del_btn = QPushButton()
        del_btn.setIcon(btn_icon_red("trash"))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("background: transparent; border: none;")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("Delete package")
        del_btn.clicked.connect(lambda _, p=pkg: self._delete_package_dict(p))

        actions_l.addWidget(edit_btn)
        actions_l.addWidget(del_btn)
        lay.addWidget(actions_w)

        return card

    def _on_pkg_checked(self, pkg_id: int, state: int):
        if not pkg_id:
            return
        if state == 2:
            self._selected_pkg_ids.add(pkg_id)
        else:
            self._selected_pkg_ids.discard(pkg_id)
        self._update_pkgs_selection_ui()

    def _open_add_package_dialog(self):
        dlg = PackageDialog(self)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result:
                pkg_id = repo.add_package(result)
                if pkg_id:
                    repo.set_package_items(pkg_id, result.get("items", []))
                    self._packages_cache = repo.get_all_packages()
                    self._populate_packages_table()
                    try:
                        from utils.signals import app_events
                        app_events().data_changed.emit()
                    except Exception:
                        pass
                    success(self, message="Package added successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to add package. Name may already exist.")

    def _open_multi_add_packages_dialog(self):
        dlg = AddMultiplePackagesDialog(self)
        if dlg.exec():
            self.reload()
            try:
                from utils.signals import app_events
                app_events().data_changed.emit()
            except Exception:
                pass
            success(self, message=f"Added {dlg._added_count} package(s) successfully.")

    def _export_packages(self):
        import csv
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Packages", "packages.csv", "CSV Files (*.csv)")
        if not path:
            return
        pkgs = getattr(self, "_packages_data", []) or []
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Package Name", "Price per Pax", "Min Pax", "Description"])
            for p in pkgs:
                writer.writerow([p.get("name", ""), p.get("price_per_pax", 0), p.get("min_pax", 1), p.get("description", "")])
        prompt_file_saved(self, path, title="Packages Exported", message="Packages list exported successfully.")

    def _edit_package_dict(self, pkg: dict):
        dlg = PackageDialog(self, pkg_data=pkg)
        if dlg.exec() == QDialog.Accepted:
            result = dlg.get_result()
            if result and pkg.get("id"):
                ok = repo.update_package(pkg["id"], result)
                if ok:
                    repo.set_package_items(pkg["id"], result.get("items", []))
                    self._packages_cache = repo.get_all_packages()
                    self._populate_packages_table()
                    try:
                        from utils.signals import app_events
                        app_events().data_changed.emit()
                    except Exception:
                        pass
                    success(self, message="Package updated successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to update package.")

    def _delete_package_dict(self, pkg: dict):
        pkg_name = pkg.get("name", "")
        if not confirm(self, title="Delete Package",
                       message=f"Delete package '{pkg_name}'? Packages linked to existing bookings cannot be deleted.",
                       confirm_label="Delete", danger=True):
            return
        ok = repo.delete_package(pkg.get("id"))
        if ok:
            self._packages_cache = repo.get_all_packages()
            self._populate_packages_table()
            try:
                from utils.signals import app_events
                app_events().data_changed.emit()
            except Exception:
                pass
            success(self, message="Package deleted successfully.")
        else:
            QMessageBox.warning(self, "Cannot Delete",
                                "This package is linked to existing bookings and cannot be deleted.")

    def _delete_selected_packages(self):
        if not self._selected_pkg_ids:
            return
        count = len(self._selected_pkg_ids)
        if not confirm(self, title="Delete Multiple Packages",
                       message=f"Are you sure you want to delete {count} selected package(s)?\nPackages linked to existing bookings cannot be deleted.",
                       confirm_label=f"Delete {count} Packages", danger=True):
            return

        deleted = repo.delete_multiple_packages(list(self._selected_pkg_ids))
        self._selected_pkg_ids.clear()
        self.reload()
        try:
            from utils.signals import app_events
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message=f"Successfully deleted {deleted} package(s).")

    def filter_search(self, text):
        q = text.lower()
        self._filter_q = q
        self._populate_table()

