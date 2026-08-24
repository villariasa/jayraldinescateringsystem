"""
ui/cash_flow_page.py
-------------------
Cash Flow Management Module for Jayraldine's Catering System (Ref Image 2).
Tracks actual movement of money: Date, Check #, Particulars (Accounts),
Deposit, Withdrawal, and Running Balance.
"""

import csv
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QComboBox, QLineEdit, QDoubleSpinBox, QDateEdit, QMessageBox,
    QFileDialog, QScrollArea, QSizePolicy, QMenu
)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QColor, QFont

import utils.repository as repo
from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success, prompt_file_saved
from utils.signals import app_events
from utils.data_loader import run_async


_DEFAULT_PARTICULARS = [
    "Cash on Hand",
    "GCash",
    "Maya",
    "UnionBank",
    "BDO Personal Savings (SAVINGS)",
    "BDO Personal Savings (DOWN PAYMENT)",
    "BDO Personal Checking (CAFE)",
    "BDO Jayraldine's Catering (CATERING)",
    "BPI Personal Savings",
]


class TransactionModal(QDialog):
    def __init__(self, parent=None, tx_data: dict = None):
        super().__init__(parent)
        self._tx = tx_data or {}
        self.setWindowTitle("Edit Transaction" if self._tx else "Add Cash Flow Transaction")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(480)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title_text = "Edit Transaction" if self._tx else "Add Transaction"
        title = QLabel(title_text)
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
        lay.addWidget(div)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight)

        # Date
        self._date_f = QDateEdit()
        self._date_f.setCalendarPopup(True)
        self._date_f.setDisplayFormat("MMM dd, yyyy")
        if self._tx.get("date"):
            try:
                qd = QDate.fromString(str(self._tx["date"]), "yyyy-MM-dd")
                if not qd.isValid():
                    qd = QDate.fromString(str(self._tx["date"]), "MMM dd, yyyy")
                self._date_f.setDate(qd if qd.isValid() else QDate.currentDate())
            except Exception:
                self._date_f.setDate(QDate.currentDate())
        else:
            self._date_f.setDate(QDate.currentDate())
        self._date_f.setFixedHeight(36)
        form.addRow(QLabel("Date *"), self._date_f)

        # Check #
        self._check_f = QLineEdit(str(self._tx.get("check_no", "")))
        self._check_f.setPlaceholderText("Check # / Ref (optional)")
        self._check_f.setFixedHeight(36)
        form.addRow(QLabel("Check #"), self._check_f)

        # Particulars (Account)
        self._particulars_f = QComboBox()
        self._particulars_f.setEditable(True)
        self._particulars_f.addItems(_DEFAULT_PARTICULARS)
        cur_part = str(self._tx.get("particulars", "Cash on Hand"))
        idx = self._particulars_f.findText(cur_part)
        if idx >= 0:
            self._particulars_f.setCurrentIndex(idx)
        else:
            self._particulars_f.setEditText(cur_part)
        self._particulars_f.setFixedHeight(36)
        form.addRow(QLabel("Particulars *"), self._particulars_f)

        # Deposit
        self._deposit_f = QDoubleSpinBox()
        self._deposit_f.setRange(0, 99999999)
        self._deposit_f.setPrefix("₱ ")
        self._deposit_f.setDecimals(2)
        self._deposit_f.setSingleStep(1000)
        self._deposit_f.setValue(float(self._tx.get("deposit") or 0.0))
        self._deposit_f.setFixedHeight(36)
        form.addRow(QLabel("Deposit (In)"), self._deposit_f)

        # Withdrawal
        self._withdrawal_f = QDoubleSpinBox()
        self._withdrawal_f.setRange(0, 99999999)
        self._withdrawal_f.setPrefix("₱ ")
        self._withdrawal_f.setDecimals(2)
        self._withdrawal_f.setSingleStep(1000)
        self._withdrawal_f.setValue(float(self._tx.get("withdrawal") or 0.0))
        self._withdrawal_f.setFixedHeight(36)
        form.addRow(QLabel("Withdrawal (Out)"), self._withdrawal_f)

        # Actual Sales
        self._actual_sales_f = QDoubleSpinBox()
        self._actual_sales_f.setRange(0, 99999999)
        self._actual_sales_f.setPrefix("₱ ")
        self._actual_sales_f.setDecimals(2)
        self._actual_sales_f.setSingleStep(1000)
        self._actual_sales_f.setValue(float(self._tx.get("actual_sales") or 0.0))
        self._actual_sales_f.setFixedHeight(36)
        form.addRow(QLabel("Actual Sales (₱)"), self._actual_sales_f)

        # Notes
        self._notes_f = QLineEdit(str(self._tx.get("notes", "")))
        self._notes_f.setPlaceholderText("Optional transaction notes / remarks...")
        self._notes_f.setFixedHeight(36)
        form.addRow(QLabel("Remarks"), self._notes_f)

        lay.addLayout(form)

        self._err_lbl = QLabel("")
        self._err_lbl.setStyleSheet("color: #EF4444; font-size: 12px;")
        self._err_lbl.hide()
        lay.addWidget(self._err_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        save = QPushButton("  Save Transaction")
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
        part = self._particulars_f.currentText().strip()
        dep = self._deposit_f.value()
        withd = self._withdrawal_f.value()
        actual_sales = self._actual_sales_f.value()

        if not part:
            self._err_lbl.setText("Please specify particulars / account.")
            self._err_lbl.show()
            return

        if dep <= 0 and withd <= 0 and actual_sales <= 0:
            self._err_lbl.setText("Please enter a deposit, withdrawal, or actual sales amount.")
            self._err_lbl.show()
            return

        payload = {
            "date": self._date_f.date().toString("yyyy-MM-dd"),
            "check_no": self._check_f.text().strip(),
            "particulars": part,
            "deposit": dep,
            "withdrawal": withd,
            "actual_sales": actual_sales,
            "notes": self._notes_f.text().strip(),
        }

        if self._tx.get("id"):
            repo.update_cash_flow_transaction(self._tx["id"], payload)
        else:
            repo.add_cash_flow_transaction(payload)

        self.accept()


class CashFlowPage(QWidget):
    def __init__(self):
        super().__init__()
        self._filter_date = None
        self._search_text = ""
        self._transactions = []
        self._build_ui()
        self._load_data()

        try:
            from utils.signals import app_events
            app_events().cash_flow_saved.connect(self.reload)
            app_events().data_changed.connect(self.reload)
        except Exception:
            pass

    def reload(self):
        self._load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(16)

        # Header Row
        header = QHBoxLayout()
        v_title = QVBoxLayout()
        title = QLabel("Cash Flow")
        title.setObjectName("pageTitle")
        sub = QLabel("Track and reconcile actual money movement across bank accounts and cash on hand (Ref Image 2).")
        sub.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        header.addLayout(v_title)
        header.addStretch()

        btn_add = QPushButton("  + Add Transaction")
        btn_add.setObjectName("primaryButton")
        btn_add.setIcon(btn_icon_primary("plus"))
        btn_add.setIconSize(QSize(15, 15))
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._open_add_dialog)

        btn_import = QPushButton("  Import")
        btn_import.setObjectName("secondaryButton")
        btn_import.setIcon(btn_icon_secondary("export"))
        btn_import.setIconSize(QSize(15, 15))
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self._open_import_dialog)

        btn_export = QPushButton("  Export")
        btn_export.setObjectName("secondaryButton")
        btn_export.setIcon(btn_icon_secondary("export"))
        btn_export.setIconSize(QSize(15, 15))
        btn_export.setCursor(Qt.PointingHandCursor)

        export_menu = QMenu(self)
        export_menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 8px 24px 8px 16px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #E11D48;
                color: #FFFFFF;
            }
        """)
        act_csv = export_menu.addAction("Export as CSV (.csv)")
        act_csv.triggered.connect(self._export_csv)
        act_excel = export_menu.addAction("Export as Excel (.xlsx)")
        act_excel.triggered.connect(self._export_excel)
        act_pdf = export_menu.addAction("Export as PDF (.pdf)")
        act_pdf.triggered.connect(self._export_pdf)
        btn_export.setMenu(export_menu)

        header.addWidget(btn_add)
        header.addWidget(btn_import)
        header.addWidget(btn_export)
        root.addLayout(header)

        # Summary Stat Cards (Deposits, Withdrawals, Balance, Actual Sales, Net Difference)
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)

        self._card_deposit = self._make_stat_card("Total Deposits (In)", "₱ 0.00", "#22C55E", "trending-up")
        self._card_withd = self._make_stat_card("Total Withdrawals (Out)", "₱ 0.00", "#EF4444", "trending-down")
        self._card_balance = self._make_stat_card("Running Balance", "₱ 0.00", "#38BDF8", "billing")
        self._card_sales = self._make_stat_card("Total Actual Sales", "₱ 0.00", "#C084FC", "calendar")
        self._card_diff = self._make_stat_card("Net Variance / Diff", "₱ 0.00", "#F59E0B", "trending-up")

        summary_row.addWidget(self._card_deposit)
        summary_row.addWidget(self._card_withd)
        summary_row.addWidget(self._card_balance)
        summary_row.addWidget(self._card_sales)
        summary_row.addWidget(self._card_diff)
        root.addLayout(summary_row)

        # Filter & Search Toolbar
        filter_card = QFrame()
        filter_card.setObjectName("card")
        f_lay = QHBoxLayout(filter_card)
        f_lay.setContentsMargins(16, 12, 16, 12)
        f_lay.setSpacing(12)

        f_lay.addWidget(QLabel("Search / Account:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter particulars (e.g. GCash, Maya, BDO)...")
        self._search_input.setFixedHeight(34)
        self._search_input.textChanged.connect(self._on_search_changed)
        f_lay.addWidget(self._search_input, 2)

        f_lay.addSpacing(10)
        f_lay.addWidget(QLabel("Date Filter:"))
        self._btn_all_dates = QPushButton("All Dates")
        self._btn_all_dates.setObjectName("primaryButton")
        self._btn_all_dates.setFixedHeight(34)
        self._btn_all_dates.clicked.connect(lambda: self._set_date_filter(None))
        f_lay.addWidget(self._btn_all_dates)

        self._btn_today = QPushButton("Today")
        self._btn_today.setObjectName("secondaryButton")
        self._btn_today.setFixedHeight(34)
        self._btn_today.clicked.connect(lambda: self._set_date_filter(datetime.now().strftime("%Y-%m-%d")))
        f_lay.addWidget(self._btn_today)

        self._spec_date = QDateEdit(QDate.currentDate())
        self._spec_date.setCalendarPopup(True)
        self._spec_date.setDisplayFormat("MMM dd, yyyy")
        self._spec_date.setFixedHeight(34)
        self._spec_date.dateChanged.connect(lambda qd: self._set_date_filter(qd.toString("yyyy-MM-dd")))
        f_lay.addWidget(self._spec_date)

        f_lay.addStretch()
        root.addWidget(filter_card)

        # Cash Flow Ledger Table
        table_card = QFrame()
        table_card.setObjectName("card")
        t_lay = QVBoxLayout(table_card)
        t_lay.setContentsMargins(16, 16, 16, 16)
        t_lay.setSpacing(12)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Date", "Check #", "Particulars (Account / Detail)",
            "Deposit (₱)", "Withdrawal (₱)", "Running Balance (₱)",
            "Actual Sales (₱)", "Variance / Diff (₱)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.horizontalHeader().setMinimumSectionSize(80)

        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setMinimumHeight(450)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0F172A;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                gridline-color: rgba(255,255,255,0.06);
                font-size: 13px;
                color: #F9FAFB;
            }
            QTableWidget::item {
                padding: 6px 10px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            QHeaderView::section {
                background-color: #111827;
                color: #9CA3AF;
                font-weight: 700;
                font-size: 11px;
                padding: 10px 10px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            QScrollBar:horizontal {
                height: 10px;
                background: #0F172A;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #334155;
                min-width: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #E11D48;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
            QScrollBar:vertical {
                width: 10px;
                background: #0F172A;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #E11D48;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
        """)
        t_lay.addWidget(self.table, 1)
        root.addWidget(table_card, 1)

    def _make_stat_card(self, title: str, val: str, color: str, icon_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(6)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF; text-transform: uppercase;")
        v_lbl = QLabel(val)
        v_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {color};")
        card._val_lbl = v_lbl

        lay.addWidget(t_lbl)
        lay.addWidget(v_lbl)
        return card

    def _on_search_changed(self, text: str):
        self._search_text = text.strip()
        self._load_data()

    def _set_date_filter(self, date_str: str = None):
        self._filter_date = date_str
        if not date_str:
            self._btn_all_dates.setObjectName("primaryButton")
            self._btn_today.setObjectName("secondaryButton")
        else:
            self._btn_all_dates.setObjectName("secondaryButton")
            self._btn_today.setObjectName("primaryButton" if date_str == datetime.now().strftime("%Y-%m-%d") else "secondaryButton")

        for btn in [self._btn_all_dates, self._btn_today]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._load_data()

    def _load_data(self):
        run_async(self, self._fetch_data, self._on_data_ready)

    def _fetch_data(self):
        txs = repo.get_cash_flow_transactions(filter_date=self._filter_date, search=self._search_text)
        summary = repo.get_cash_flow_summary()
        return {"transactions": txs, "summary": summary}

    def _on_data_ready(self, data):
        self._transactions = data.get("transactions", [])
        summary = data.get("summary", {})

        dep = summary.get("total_deposits", 0.0)
        withd = summary.get("total_withdrawals", 0.0)
        bal = summary.get("current_balance", 0.0)
        sales = summary.get("total_actual_sales", 0.0)
        diff = summary.get("total_difference", bal - sales)

        self._card_deposit._val_lbl.setText(f"₱ {dep:,.2f}")
        self._card_withd._val_lbl.setText(f"₱ {withd:,.2f}")
        bal_color = "#22C55E" if bal >= 0 else "#EF4444"
        self._card_balance._val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {bal_color};")
        self._card_balance._val_lbl.setText(f"₱ {bal:,.2f}")

        self._card_sales._val_lbl.setText(f"₱ {sales:,.2f}")
        diff_color = "#22C55E" if diff >= 0 else "#EF4444"
        diff_str = f"₱ {diff:,.2f}" if diff >= 0 else f"(₱ {abs(diff):,.2f})"
        self._card_diff._val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {diff_color};")
        self._card_diff._val_lbl.setText(diff_str)

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(len(self._transactions))
        for r_idx, tx in enumerate(self._transactions):
            # Date
            d_val = str(tx.get("date", ""))
            try:
                qd = QDate.fromString(d_val, "yyyy-MM-dd")
                date_str = qd.toString("MMM dd, yyyy") if qd.isValid() else d_val
            except Exception:
                date_str = d_val
            item_d = QTableWidgetItem(date_str)
            item_d.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Check #
            item_c = QTableWidgetItem(str(tx.get("check_no", "") or "—"))
            item_c.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Particulars
            part_text = str(tx.get("particulars", ""))
            if tx.get("notes"):
                part_text += f" ({tx['notes']})"
            item_p = QTableWidgetItem(part_text)
            item_p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            item_p.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Deposit
            dep_val = float(tx.get("deposit") or 0.0)
            item_dep = QTableWidgetItem(f"₱ {dep_val:,.2f}" if dep_val > 0 else "—")
            item_dep.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if dep_val > 0:
                item_dep.setForeground(QColor("#22C55E"))

            # Withdrawal
            withd_val = float(tx.get("withdrawal") or 0.0)
            item_w = QTableWidgetItem(f"₱ {withd_val:,.2f}" if withd_val > 0 else "—")
            item_w.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if withd_val > 0:
                item_w.setForeground(QColor("#EF4444"))

            # Balance
            bal_val = float(tx.get("balance") or 0.0)
            bal_str = f"₱ {bal_val:,.2f}" if bal_val >= 0 else f"(₱ {abs(bal_val):,.2f})"
            item_bal = QTableWidgetItem(bal_str)
            item_bal.setFont(QFont("Segoe UI", 10, QFont.Bold))
            item_bal.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_bal.setForeground(QColor("#22C55E" if bal_val >= 0 else "#EF4444"))

            # Actual Sales
            sales_val = float(tx.get("actual_sales") or 0.0)
            sales_str = f"₱ {sales_val:,.2f}" if sales_val > 0 else "—"
            item_sales = QTableWidgetItem(sales_str)
            item_sales.setFont(QFont("Segoe UI", 10, QFont.Bold))
            item_sales.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if sales_val > 0:
                item_sales.setForeground(QColor("#C084FC"))

            # Variance / Difference (Balance - Actual Sales)
            if sales_val > 0:
                diff_val = bal_val - sales_val
                diff_str = f"₱ {diff_val:,.2f}" if diff_val >= 0 else f"(₱ {abs(diff_val):,.2f})"
                diff_color = QColor("#22C55E" if diff_val >= 0 else "#EF4444")
            else:
                diff_str = "—"
                diff_color = QColor("#9CA3AF")
            item_diff = QTableWidgetItem(diff_str)
            item_diff.setFont(QFont("Segoe UI", 10, QFont.Bold))
            item_diff.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_diff.setForeground(diff_color)

            self.table.setItem(r_idx, 0, item_d)
            self.table.setItem(r_idx, 1, item_c)
            self.table.setItem(r_idx, 2, item_p)
            self.table.setItem(r_idx, 3, item_dep)
            self.table.setItem(r_idx, 4, item_w)
            self.table.setItem(r_idx, 5, item_bal)
            self.table.setItem(r_idx, 6, item_sales)
            self.table.setItem(r_idx, 7, item_diff)

            # Actions (Edit / Delete)
            act_widget = QWidget()
            act_lay = QHBoxLayout(act_widget)
            act_lay.setContentsMargins(4, 2, 4, 2)
            act_lay.setSpacing(6)

            edit_btn = QPushButton()
            edit_btn.setIcon(get_icon("edit", color="#38BDF8", size=QSize(13, 13)))
            edit_btn.setFixedSize(28, 28)
            edit_btn.setStyleSheet("background: transparent; border: none;")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setToolTip("Edit Transaction")
            edit_btn.clicked.connect(lambda _, item_tx=tx: self._edit_transaction(item_tx))

            del_btn = QPushButton()
            del_btn.setIcon(get_icon("trash", color="#EF4444", size=QSize(13, 13)))
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete Transaction")
            del_btn.clicked.connect(lambda _, item_tx=tx: self._delete_transaction(item_tx))

            act_lay.addWidget(edit_btn)
            act_lay.addWidget(del_btn)
            self.table.setCellWidget(r_idx, 8, act_widget)

    def _open_add_dialog(self):
        dlg = TransactionModal(self)
        if dlg.exec():
            self._load_data()
            success(self, message="Cash flow transaction recorded.")

    def _edit_transaction(self, tx: dict):
        dlg = TransactionModal(self, tx_data=tx)
        if dlg.exec():
            self._load_data()
            success(self, message="Transaction updated.")

    def _delete_transaction(self, tx: dict):
        if not confirm(self, title="Delete Transaction",
                       message=f"Are you sure you want to delete transaction for '{tx.get('particulars')}'?",
                       confirm_label="Delete", danger=True):
            return
        repo.delete_cash_flow_transaction(tx["id"])
        self._load_data()
        success(self, message="Transaction deleted.")

    def _open_import_dialog(self):
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="cash_flow", parent=self)
        if dlg.exec():
            self._load_data()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Cash Flow (CSV)", "Jayraldines_Cash_Flow.csv", "CSV Files (*.csv)")
        if not path:
            return
        from utils.exporter import export_custom_entity_data
        ok = export_custom_entity_data("Cash Flow", is_excel=False, save_path=path)
        if ok:
            prompt_file_saved(self, path, title="Cash Flow Exported", message="Cash flow CSV exported successfully.")
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to export Cash Flow CSV.")

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Cash Flow (Excel)", "Jayraldines_Cash_Flow.xlsx", "Excel Files (*.xlsx)")
        if not path:
            return
        from utils.exporter import export_custom_entity_data
        ok = export_custom_entity_data("Cash Flow", is_excel=True, save_path=path)
        if ok:
            prompt_file_saved(self, path, title="Cash Flow Workbook Exported", message="Cash flow Excel workbook exported successfully.")
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to export Cash Flow Excel workbook.")

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Cash Flow (PDF)", "Jayraldines_Cash_Flow_Report.pdf", "PDF Documents (*.pdf)")
        if not path:
            return
        from utils.exporter import export_cash_flow_pdf
        smry = repo.get_cash_flow_summary()
        ok = export_cash_flow_pdf(path, transactions=self._transactions, summary=smry)
        if ok:
            prompt_file_saved(self, path, title="Cash Flow PDF Generated", message="Cash flow PDF report generated successfully.")
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to generate Cash Flow PDF.")
