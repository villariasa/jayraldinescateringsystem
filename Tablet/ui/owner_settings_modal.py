"""
Owner Settings & Master Data Management Modal for Tablet Catering.
Allows the owner to manage Menu Items, Packages, and the Customer Directory.
"""
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QFrame,
    QMessageBox, QInputDialog, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor

import utils.repository as repo
from ui import theme


class OwnerSettingsModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Owner Settings — Master Data Management")
        self.resize(1000, 680)
        self.setMinimumSize(480, 450)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignVCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Owner Settings & Menu Management")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        sub = QLabel("Add, edit, or customize buffet packages, dishes, and customer profiles on this tablet.")
        sub.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(38)
        close_btn.setMinimumWidth(100)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #CBD5E1;
                font-size: 13px;
                font-weight: 700;
                border-radius: 8px;
                border: 1px solid #334155;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        root.addLayout(header)

        # Tab Widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1.5px solid {theme.BORDER};
                background: {theme.CARD};
                border-radius: 12px;
                padding: 12px;
            }}
            QTabBar::tab {{
                background: {theme.CARD_ELEVATED};
                color: {theme.TEXT_MUTED};
                font-weight: 700;
                font-size: 13px;
                padding: 10px 22px;
                margin-right: 6px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background: #D97706;
                color: #FFFFFF;
            }}
        """)

        self._pkg_tab = QWidget()
        self._menu_tab = QWidget()
        self._cust_tab = QWidget()

        self._build_packages_tab()
        self._build_menu_tab()
        self._build_customers_tab()

        self._tabs.addTab(self._pkg_tab, "Buffet Packages")
        self._tabs.addTab(self._menu_tab, "Menu Dishes & Add-ons")
        self._tabs.addTab(self._cust_tab, "Customer Directory")

        root.addWidget(self._tabs, 1)

    # ── TAB 1: PACKAGES ───────────────────────────────────────────────

    def _build_packages_tab(self):
        lay = QVBoxLayout(self._pkg_tab)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        top_row = QHBoxLayout()
        lbl = QLabel("Catering Buffet Packages")
        lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #E2E8F0;")
        top_row.addWidget(lbl)
        top_row.addStretch()

        add_btn = QPushButton("+ Add New Package")
        add_btn.setObjectName("Primary")
        add_btn.setFixedHeight(38)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; border-radius: 8px; padding: 6px 16px;")
        add_btn.clicked.connect(self._add_package_dialog)
        top_row.addWidget(add_btn)
        lay.addLayout(top_row)

        self._pkg_table = QTableWidget()
        self._pkg_table.setColumnCount(5)
        self._pkg_table.setHorizontalHeaderLabels(["ID", "Package Name", "Price / Pax (₱)", "Min Pax", "Actions"])
        self._pkg_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._pkg_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self._pkg_table.setColumnWidth(0, 50)
        self._pkg_table.setColumnWidth(2, 130)
        self._pkg_table.setColumnWidth(3, 80)
        self._pkg_table.setColumnWidth(4, 170)
        self._pkg_table.verticalHeader().setDefaultSectionSize(46)
        self._pkg_table.verticalHeader().setVisible(False)
        self._pkg_table.setStyleSheet(f"background: {theme.CARD_ELEVATED}; gridline-color: {theme.BORDER}; font-size: 13px;")
        lay.addWidget(self._pkg_table, 1)
        self._reload_packages()

    def _reload_packages(self):
        pkgs = repo.get_packages()
        self._pkg_table.setRowCount(len(pkgs))
        for r, p in enumerate(pkgs):
            self._pkg_table.setItem(r, 0, QTableWidgetItem(str(p["id"])))
            self._pkg_table.setItem(r, 1, QTableWidgetItem(p["name"]))
            self._pkg_table.setItem(r, 2, QTableWidgetItem(f"₱{p['price_per_pax']:,.2f}"))
            self._pkg_table.setItem(r, 3, QTableWidgetItem(str(p["min_pax"])))

            act_w = QWidget()
            al = QHBoxLayout(act_w)
            al.setContentsMargins(4, 4, 4, 4)
            al.setSpacing(8)

            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedHeight(30)
            edit_btn.setMinimumWidth(65)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #CBD5E1;
                    font-size: 12px;
                    font-weight: 700;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #334155; color: #FFFFFF; }
            """)
            edit_btn.clicked.connect(lambda _, pkg=p: self._edit_package_dialog(pkg))
            al.addWidget(edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedHeight(30)
            del_btn.setMinimumWidth(65)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.15);
                    color: #F87171;
                    font-size: 12px;
                    font-weight: 700;
                    border: 1px solid #EF4444;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: rgba(239, 68, 68, 0.25); }
            """)
            del_btn.clicked.connect(lambda _, pkg=p: self._delete_package(pkg))
            al.addWidget(del_btn)

            self._pkg_table.setCellWidget(r, 4, act_w)

    def _add_package_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Add New Buffet Package")
        d.resize(460, 360)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        name_in = QLineEdit()
        name_in.setPlaceholderText("e.g. Deluxe Wedding Package")
        desc_in = QTextEdit()
        desc_in.setPlaceholderText("Package description, inclusions...")
        desc_in.setFixedHeight(80)
        ppp_in = QDoubleSpinBox()
        ppp_in.setRange(0, 50000)
        ppp_in.setValue(350)
        min_in = QSpinBox()
        min_in.setRange(10, 1000)
        min_in.setValue(30)

        lay.addWidget(QLabel("Package Name:"))
        lay.addWidget(name_in)
        lay.addWidget(QLabel("Price Per Pax (₱):"))
        lay.addWidget(ppp_in)
        lay.addWidget(QLabel("Minimum Guests (Pax):"))
        lay.addWidget(min_in)
        lay.addWidget(QLabel("Description:"))
        lay.addWidget(desc_in)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Package")
        save_btn.setObjectName("Primary")
        save_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; padding: 8px 18px;")
        save_btn.clicked.connect(lambda: self._save_new_package(d, name_in.text(), desc_in.toPlainText(), ppp_in.value(), min_in.value()))
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)
        d.exec()

    def _save_new_package(self, dlg, name, desc, ppp, min_p):
        if not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Please enter a package name.")
            return
        repo.add_package(name, desc, ppp, min_p)
        dlg.accept()
        self._reload_packages()

    def _edit_package_dialog(self, pkg):
        d = QDialog(self)
        d.setWindowTitle(f"Edit Package: {pkg['name']}")
        d.resize(460, 360)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        name_in = QLineEdit(pkg["name"])
        desc_in = QTextEdit(pkg.get("description", ""))
        desc_in.setFixedHeight(80)
        ppp_in = QDoubleSpinBox()
        ppp_in.setRange(0, 50000)
        ppp_in.setValue(pkg["price_per_pax"])
        min_in = QSpinBox()
        min_in.setRange(10, 1000)
        min_in.setValue(pkg["min_pax"])

        lay.addWidget(QLabel("Package Name:"))
        lay.addWidget(name_in)
        lay.addWidget(QLabel("Price Per Pax (₱):"))
        lay.addWidget(ppp_in)
        lay.addWidget(QLabel("Minimum Guests (Pax):"))
        lay.addWidget(min_in)
        lay.addWidget(QLabel("Description:"))
        lay.addWidget(desc_in)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Update Package")
        save_btn.setObjectName("Primary")
        save_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; padding: 8px 18px;")
        save_btn.clicked.connect(lambda: self._update_package(d, pkg["id"], name_in.text(), desc_in.toPlainText(), ppp_in.value(), min_in.value()))
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)
        d.exec()

    def _update_package(self, dlg, pid, name, desc, ppp, min_p):
        if not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Please enter a package name.")
            return
        repo.update_package(pid, name, desc, ppp, min_p)
        dlg.accept()
        self._reload_packages()

    def _delete_package(self, pkg):
        if QMessageBox.question(self, "Delete Package", f"Are you sure you want to delete '{pkg['name']}'?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            repo.delete_package(pkg["id"])
            self._reload_packages()

    # ── TAB 2: MENU ITEMS ─────────────────────────────────────────────

    def _build_menu_tab(self):
        lay = QVBoxLayout(self._menu_tab)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl = QLabel("Filter Category:")
        lbl.setStyleSheet("font-size: 13px; color: #94A3B8; font-weight: 600;")
        top_row.addWidget(lbl)

        self._cat_combo = QComboBox()
        self._cat_combo.addItem("All Categories")
        for c in repo.get_menu_categories():
            self._cat_combo.addItem(c)
        self._cat_combo.currentIndexChanged.connect(self._reload_menu_items)
        top_row.addWidget(self._cat_combo)
        top_row.addStretch()

        add_btn = QPushButton("+ Add Menu Item")
        add_btn.setObjectName("Primary")
        add_btn.setFixedHeight(38)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; border-radius: 8px; padding: 6px 16px;")
        add_btn.clicked.connect(self._add_menu_dialog)
        top_row.addWidget(add_btn)
        lay.addLayout(top_row)

        self._menu_table = QTableWidget()
        self._menu_table.setColumnCount(5)
        self._menu_table.setHorizontalHeaderLabels(["ID", "Item / Dish Name", "Category", "Add-on Price (₱)", "Actions"])
        self._menu_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._menu_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self._menu_table.setColumnWidth(0, 50)
        self._menu_table.setColumnWidth(2, 140)
        self._menu_table.setColumnWidth(3, 140)
        self._menu_table.setColumnWidth(4, 170)
        self._menu_table.verticalHeader().setDefaultSectionSize(46)
        self._menu_table.verticalHeader().setVisible(False)
        self._menu_table.setStyleSheet(f"background: {theme.CARD_ELEVATED}; gridline-color: {theme.BORDER}; font-size: 13px;")
        lay.addWidget(self._menu_table, 1)
        self._reload_menu_items()

    def _reload_menu_items(self):
        items = repo.get_all_menu_items()
        selected_cat = self._cat_combo.currentText()
        if selected_cat and selected_cat != "All Categories":
            items = [i for i in items if i["category"] == selected_cat]

        self._menu_table.setRowCount(len(items))
        for r, it in enumerate(items):
            self._menu_table.setItem(r, 0, QTableWidgetItem(str(it["id"])))
            self._menu_table.setItem(r, 1, QTableWidgetItem(it["name"]))
            self._menu_table.setItem(r, 2, QTableWidgetItem(it["category"]))
            self._menu_table.setItem(r, 3, QTableWidgetItem(f"₱{it['price']:,.2f}"))

            act_w = QWidget()
            al = QHBoxLayout(act_w)
            al.setContentsMargins(4, 4, 4, 4)
            al.setSpacing(8)

            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedHeight(30)
            edit_btn.setMinimumWidth(65)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #CBD5E1;
                    font-size: 12px;
                    font-weight: 700;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #334155; color: #FFFFFF; }
            """)
            edit_btn.clicked.connect(lambda _, item=it: self._edit_menu_dialog(item))
            al.addWidget(edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedHeight(30)
            del_btn.setMinimumWidth(65)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.15);
                    color: #F87171;
                    font-size: 12px;
                    font-weight: 700;
                    border: 1px solid #EF4444;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: rgba(239, 68, 68, 0.25); }
            """)
            del_btn.clicked.connect(lambda _, item=it: self._delete_menu_item(item))
            al.addWidget(del_btn)

            self._menu_table.setCellWidget(r, 4, act_w)

    def _add_menu_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Add New Menu Item")
        d.resize(440, 320)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        name_in = QLineEdit()
        name_in.setPlaceholderText("e.g. Sweet & Sour Pork")
        cat_in = QComboBox()
        for c in repo.get_menu_categories():
            cat_in.addItem(c)
        price_in = QDoubleSpinBox()
        price_in.setRange(0, 50000)
        price_in.setValue(0.0)

        lay.addWidget(QLabel("Item Name:"))
        lay.addWidget(name_in)
        lay.addWidget(QLabel("Category:"))
        lay.addWidget(cat_in)
        lay.addWidget(QLabel("Extra Add-on Price (₱, 0 if included in package):"))
        lay.addWidget(price_in)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Item")
        save_btn.setObjectName("Primary")
        save_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; padding: 8px 18px;")
        save_btn.clicked.connect(lambda: self._save_new_menu(d, name_in.text(), cat_in.currentText(), price_in.value()))
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)
        d.exec()

    def _save_new_menu(self, dlg, name, cat, price):
        if not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Please enter a dish/item name.")
            return
        repo.add_menu_item(name, cat, price)
        dlg.accept()
        self._reload_menu_items()

    def _edit_menu_dialog(self, it):
        d = QDialog(self)
        d.setWindowTitle(f"Edit Menu Item: {it['name']}")
        d.resize(440, 320)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        name_in = QLineEdit(it["name"])
        cat_in = QComboBox()
        for c in repo.get_menu_categories():
            cat_in.addItem(c)
        cat_in.setCurrentText(it["category"])
        price_in = QDoubleSpinBox()
        price_in.setRange(0, 50000)
        price_in.setValue(it["price"])

        lay.addWidget(QLabel("Item Name:"))
        lay.addWidget(name_in)
        lay.addWidget(QLabel("Category:"))
        lay.addWidget(cat_in)
        lay.addWidget(QLabel("Extra Add-on Price (₱):"))
        lay.addWidget(price_in)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Update Item")
        save_btn.setObjectName("Primary")
        save_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; padding: 8px 18px;")
        save_btn.clicked.connect(lambda: self._update_menu(d, it["id"], name_in.text(), cat_in.currentText(), price_in.value()))
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)
        d.exec()

    def _update_menu(self, dlg, mid, name, cat, price):
        if not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Please enter a dish/item name.")
            return
        repo.update_menu_item(mid, name, cat, price)
        dlg.accept()
        self._reload_menu_items()

    def _delete_menu_item(self, it):
        if QMessageBox.question(self, "Delete Menu Item", f"Are you sure you want to delete '{it['name']}'?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            repo.delete_menu_item(it["id"])
            self._reload_menu_items()

    # ── TAB 3: CUSTOMERS DIRECTORY ────────────────────────────────────

    def _build_customers_tab(self):
        lay = QVBoxLayout(self._cust_tab)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._cust_search = QLineEdit()
        self._cust_search.setPlaceholderText("Search customer name, contact, or address...")
        self._cust_search.textChanged.connect(self._reload_customers)
        top_row.addWidget(self._cust_search, 1)

        add_btn = QPushButton("+ Add Customer")
        add_btn.setObjectName("Primary")
        add_btn.setFixedHeight(38)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; border-radius: 8px; padding: 6px 16px;")
        add_btn.clicked.connect(self._add_customer_dialog)
        top_row.addWidget(add_btn)
        lay.addLayout(top_row)

        self._cust_table = QTableWidget()
        self._cust_table.setColumnCount(5)
        self._cust_table.setHorizontalHeaderLabels(["ID", "Customer Name", "Contact", "Address", "Actions"])
        self._cust_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._cust_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._cust_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self._cust_table.setColumnWidth(0, 50)
        self._cust_table.setColumnWidth(2, 130)
        self._cust_table.setColumnWidth(4, 170)
        self._cust_table.verticalHeader().setDefaultSectionSize(46)
        self._cust_table.verticalHeader().setVisible(False)
        self._cust_table.setStyleSheet(f"background: {theme.CARD_ELEVATED}; gridline-color: {theme.BORDER}; font-size: 13px;")
        lay.addWidget(self._cust_table, 1)
        self._reload_customers()

    def _reload_customers(self):
        query = self._cust_search.text()
        custs = repo.search_customers(query)
        self._cust_table.setRowCount(len(custs))
        for r, c in enumerate(custs):
            self._cust_table.setItem(r, 0, QTableWidgetItem(str(c["id"])))
            self._cust_table.setItem(r, 1, QTableWidgetItem(c["name"]))
            self._cust_table.setItem(r, 2, QTableWidgetItem(c["contact"] or "—"))
            self._cust_table.setItem(r, 3, QTableWidgetItem(c["address"] or "—"))

            act_w = QWidget()
            al = QHBoxLayout(act_w)
            al.setContentsMargins(4, 4, 4, 4)
            al.setSpacing(8)

            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setFixedHeight(30)
            edit_btn.setMinimumWidth(65)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B;
                    color: #CBD5E1;
                    font-size: 12px;
                    font-weight: 700;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: #334155; color: #FFFFFF; }
            """)
            edit_btn.clicked.connect(lambda _, cust=c: self._edit_customer_dialog(cust))
            al.addWidget(edit_btn)

            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedHeight(30)
            del_btn.setMinimumWidth(65)
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.15);
                    color: #F87171;
                    font-size: 12px;
                    font-weight: 700;
                    border: 1px solid #EF4444;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QPushButton:hover { background-color: rgba(239, 68, 68, 0.25); }
            """)
            del_btn.clicked.connect(lambda _, cust=c: self._delete_customer(cust))
            al.addWidget(del_btn)

            self._cust_table.setCellWidget(r, 4, act_w)

    def _add_customer_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Add Customer Profile")
        d.resize(460, 320)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        name_in = QLineEdit()
        contact_in = QLineEdit()
        email_in = QLineEdit()
        addr_in = QLineEdit()

        lay.addWidget(QLabel("Full Name *:"))
        lay.addWidget(name_in)
        lay.addWidget(QLabel("Contact Number:"))
        lay.addWidget(contact_in)
        lay.addWidget(QLabel("Email Address:"))
        lay.addWidget(email_in)
        lay.addWidget(QLabel("Billing / Delivery Address:"))
        lay.addWidget(addr_in)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Customer")
        save_btn.setObjectName("Primary")
        save_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; padding: 8px 18px;")
        save_btn.clicked.connect(lambda: self._save_new_cust(d, name_in.text(), contact_in.text(), email_in.text(), addr_in.text()))
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)
        d.exec()

    def _save_new_cust(self, dlg, name, contact, email, addr):
        if not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Please enter customer name.")
            return
        repo.add_customer(name, contact, email, addr)
        dlg.accept()
        self._reload_customers()

    def _edit_customer_dialog(self, cust):
        d = QDialog(self)
        d.setWindowTitle(f"Edit Customer: {cust['name']}")
        d.resize(460, 320)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        name_in = QLineEdit(cust["name"])
        contact_in = QLineEdit(cust["contact"])
        email_in = QLineEdit(cust.get("email", ""))
        addr_in = QLineEdit(cust["address"])

        lay.addWidget(QLabel("Full Name *:"))
        lay.addWidget(name_in)
        lay.addWidget(QLabel("Contact Number:"))
        lay.addWidget(contact_in)
        lay.addWidget(QLabel("Email Address:"))
        lay.addWidget(email_in)
        lay.addWidget(QLabel("Billing / Delivery Address:"))
        lay.addWidget(addr_in)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Update Customer")
        save_btn.setObjectName("Primary")
        save_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: 700; padding: 8px 18px;")
        save_btn.clicked.connect(lambda: self._update_cust(d, cust["id"], name_in.text(), contact_in.text(), email_in.text(), addr_in.text()))
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)
        d.exec()

    def _update_cust(self, dlg, cid, name, contact, email, addr):
        if not name.strip():
            QMessageBox.warning(self, "Invalid Name", "Please enter customer name.")
            return
        repo.update_customer(cid, name, contact, email, addr)
        dlg.accept()
        self._reload_customers()

    def _delete_customer(self, cust):
        if QMessageBox.question(self, "Delete Customer", f"Are you sure you want to delete '{cust['name']}'?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            repo.delete_customer(cust["id"])
            self._reload_customers()
