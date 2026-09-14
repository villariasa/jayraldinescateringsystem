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
    QFileDialog, QScrollArea, QSizePolicy, QMenu, QCheckBox
)
from PySide6.QtCore import Qt, QSize, QDate, QTimer
from PySide6.QtGui import QColor, QFont

import utils.repository as repo
from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_red, get_icon
from components.dialogs import confirm, success, prompt_file_saved, error
from components.loading_overlay import LoadingOverlay
from utils.session import SessionManager
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

        # Check #
        self._check_f = QLineEdit(self._tx.get("check_no", "") or "")
        self._check_f.setPlaceholderText("e.g. CHK-001, GCASH-101, or —")

        # Particulars
        self._part_f = QComboBox()
        self._part_f.setEditable(True)
        self._part_f.addItems(_DEFAULT_PARTICULARS)
        if self._tx.get("particulars"):
            idx = self._part_f.findText(self._tx["particulars"])
            if idx >= 0:
                self._part_f.setCurrentIndex(idx)
            else:
                self._part_f.setEditText(self._tx["particulars"])

        # Deposit
        self._dep_f = QDoubleSpinBox()
        self._dep_f.setRange(0, 99999999)
        self._dep_f.setDecimals(2)
        self._dep_f.setPrefix("₱ ")
        self._dep_f.setValue(float(self._tx.get("deposit") or 0.0))

        # Withdrawal
        self._withd_f = QDoubleSpinBox()
        self._withd_f.setRange(0, 99999999)
        self._withd_f.setDecimals(2)
        self._withd_f.setPrefix("₱ ")
        self._withd_f.setValue(float(self._tx.get("withdrawal") or 0.0))

        # Actual Sales (Optional)
        self._actual_sales_f = QDoubleSpinBox()
        self._actual_sales_f.setRange(0, 99999999)
        self._actual_sales_f.setDecimals(2)
        self._actual_sales_f.setPrefix("₱ ")
        self._actual_sales_f.setValue(float(self._tx.get("actual_sales") or 0.0))

        # Notes / Remarks
        self._notes_f = QLineEdit(self._tx.get("notes", "") or "")
        self._notes_f.setPlaceholderText("Optional description or reference...")

        form.addRow(QLabel("Transaction Date:"), self._date_f)
        form.addRow(QLabel("Check / Ref #:"), self._check_f)
        form.addRow(QLabel("Particulars / Account:"), self._part_f)
        form.addRow(QLabel("Deposit (Money In):"), self._dep_f)
        form.addRow(QLabel("Withdrawal (Money Out):"), self._withd_f)
        form.addRow(QLabel("Actual Sales (Optional):"), self._actual_sales_f)
        form.addRow(QLabel("Notes / Purpose:"), self._notes_f)

        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Transaction")
        save_btn.setObjectName("primaryButton")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        outer.addWidget(container)

    def _save(self):
        part = self._part_f.currentText().strip()
        if not part:
            QMessageBox.warning(self, "Validation Error", "Please provide a valid account or particulars description.")
            return

        dep = self._dep_f.value()
        withd = self._withd_f.value()
        actual_sales = self._actual_sales_f.value()

        if dep == 0 and withd == 0 and actual_sales == 0:
            QMessageBox.warning(self, "Validation Error", "Please enter at least a Deposit, Withdrawal, or Actual Sales amount.")
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dirty = True  # Load on first show
        self._filter_date = None
        self._search_text = ""
        self._transactions = []
        self._selected_ids = set()
        self._row_checkboxes = {}
        self._render_token = 0
        self._render_queue = []
        self._reload_in_flight = False
        self._reload_pending = False
        # Busy-flag guarding the batched render pipeline against a scroll-triggered
        # append firing while the initial page's batch chain is still running.
        self._rendering = False
        # Lazy-loading / infinite-scroll pagination state.
        self._page_size = 50
        self._has_more = True
        self._loading_more = False
        self._cached_remainder = None
        self._summary = {}
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._load_data)
        self._build_ui()

        try:
            from utils.signals import app_events
            app_events().cash_flow_saved.connect(self._mark_dirty_and_reload)
            app_events().data_changed.connect(self._mark_dirty)
        except Exception:
            pass

    def _mark_dirty(self):
        self._dirty = True

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self.reload()

    def refresh_permissions(self):
        can_create = SessionManager.has_permission("cashflow", "create")
        can_edit = SessionManager.has_permission("cashflow", "edit")
        can_delete = SessionManager.has_permission("cashflow", "delete")
        can_export = SessionManager.has_permission("reports", "view") or SessionManager.has_permission("cashflow", "view")

        if hasattr(self, "btn_add"):
            self.btn_add.setEnabled(can_create)
            self.btn_add.setVisible(can_create)
        if hasattr(self, "btn_import"):
            self.btn_import.setEnabled(can_create)
            self.btn_import.setVisible(can_create)
        if hasattr(self, "_btn_delete_selected"):
            self._btn_delete_selected.setVisible(can_delete)
            if not can_delete:
                self._btn_delete_selected.setEnabled(False)
        if hasattr(self, "_cb_select_all"):
            self._cb_select_all.setVisible(can_delete)
        if hasattr(self, "_lbl_selected_count"):
            self._lbl_selected_count.setVisible(can_delete)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_permissions()
        if getattr(self, "_dirty", True):
            self._load_data()
            self._dirty = False

    def reload(self):
        self._dirty = False
        self.refresh_permissions()
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

        self.btn_add = QPushButton("  + Add Transaction")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.setIcon(btn_icon_primary("plus"))
        self.btn_add.setIconSize(QSize(15, 15))
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._open_add_dialog)

        self.btn_import = QPushButton("  Import")
        self.btn_import.setObjectName("secondaryButton")
        self.btn_import.setIcon(btn_icon_secondary("export"))
        self.btn_import.setIconSize(QSize(15, 15))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self._open_import_dialog)

        self.btn_export = QPushButton("  Export")
        self.btn_export.setObjectName("secondaryButton")
        self.btn_export.setIcon(btn_icon_secondary("export"))
        self.btn_export.setIconSize(QSize(15, 15))
        self.btn_export.setCursor(Qt.PointingHandCursor)

        export_menu = QMenu(self)
        act_csv = export_menu.addAction("Export as CSV (.csv)")
        act_csv.triggered.connect(self._export_csv)
        act_excel = export_menu.addAction("Export as Excel (.xlsx)")
        act_excel.triggered.connect(self._export_excel)
        act_pdf = export_menu.addAction("Export as PDF (.pdf)")
        act_pdf.triggered.connect(self._export_pdf)
        self.btn_export.setMenu(export_menu)

        header.addWidget(self.btn_add)
        header.addWidget(self.btn_import)
        header.addWidget(self.btn_export)
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

        # Cash Flow Ledger Table Card
        table_card = QFrame()
        table_card.setObjectName("card")
        t_lay = QVBoxLayout(table_card)
        t_lay.setContentsMargins(16, 16, 16, 16)
        t_lay.setSpacing(12)

        # Multi-Select Batch Action Toolbar
        batch_toolbar = QHBoxLayout()
        batch_toolbar.setContentsMargins(4, 0, 4, 4)
        batch_toolbar.setSpacing(12)

        self._cb_select_all = QCheckBox("Select All")
        self._cb_select_all.setStyleSheet("QCheckBox { font-weight: 600; font-size: 13px; color: #9CA3AF; }")
        self._cb_select_all.stateChanged.connect(self._toggle_select_all)
        batch_toolbar.addWidget(self._cb_select_all)

        self._lbl_selected_count = QLabel("0 selected")
        self._lbl_selected_count.setStyleSheet("font-size: 12px; color: #6B7280; font-weight: 600;")
        batch_toolbar.addWidget(self._lbl_selected_count)

        batch_toolbar.addStretch()

        self._btn_delete_selected = QPushButton("  Delete Selected")
        self._btn_delete_selected.setIcon(btn_icon_red("trash"))
        self._btn_delete_selected.setIconSize(QSize(13, 13))
        self._btn_delete_selected.setCursor(Qt.PointingHandCursor)
        self._btn_delete_selected.setEnabled(False)
        self._btn_delete_selected.setStyleSheet(
            "QPushButton { background: rgba(225,29,72,0.15); border: 1px solid rgba(225,29,72,0.3); color: #E11D48; border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(225,29,72,0.25); border-color: #E11D48; }"
            "QPushButton:disabled { opacity: 0.35; background: rgba(255,255,255,0.04); border-color: transparent; color: #6B7280; }"
        )
        self._btn_delete_selected.clicked.connect(self._delete_selected_transactions)
        batch_toolbar.addWidget(self._btn_delete_selected)

        t_lay.addLayout(batch_toolbar)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "", "Date", "Check #", "Particulars (Account / Detail)",
            "Deposit (₱)", "Withdrawal (₱)", "Running Balance (₱)",
            "Actual Sales (₱)", "Variance / Diff (₱)", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 44)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.horizontalHeader().setMinimumSectionSize(40)

        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setMinimumHeight(450)
        t_lay.addWidget(self.table, 1)
        # Infinite scroll: append the next page when the user nears the bottom.
        self.table.verticalScrollBar().valueChanged.connect(self._on_scroll_near_bottom)
        root.addWidget(table_card, 1)
        self._loader = LoadingOverlay(self, "Loading cash flow transactions...")

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
        # Debounced - _load_data() re-fetches from the DB, so firing it on
        # every single keystroke was the actual cause of laggy search here.
        self._search_timer.start(150)

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
        # Coalesce overlapping reloads: if a reload (fetch + batch-render) is
        # already running, don't start a second one in parallel - just remember
        # to run exactly one more pass once the current one fully finishes.
        if getattr(self, "_reload_in_flight", False):
            self._reload_pending = True
            return
        self._reload_in_flight = True
        self._reload_pending = False

        # Pagination resets on every full reload - we always re-fetch page 0.
        self._has_more = True
        self._loading_more = False
        self._cached_remainder = None

        from utils.data_cache import DataCache
        if not self._filter_date and not self._search_text:
            cached = DataCache.get("cash_flow_data")
            if cached is not None and not getattr(self, "_has_loaded_once", False):
                self._has_loaded_once = True
                # The login welcome sequence caches the FULL transaction list plus
                # a lightweight summary. Slice off page 1 for instant render and
                # keep the remainder in memory to serve scroll-pages with no DB hit.
                all_txs = list(cached.get("transactions", []))
                self._summary = cached.get("summary", {})
                page = all_txs[:self._page_size]
                self._cached_remainder = all_txs[self._page_size:]
                if not self._cached_remainder:
                    self._has_more = False
                payload = {"transactions": page, "summary": self._summary}
                if hasattr(self, "_loader"):
                    self._loader.show_overlay("Loading cash flow transactions...")
                    QTimer.singleShot(60, lambda: self._on_data_ready(payload))
                else:
                    self._on_data_ready(payload)
                return

        if hasattr(self, "_loader"):
            self._loader.show_overlay("Loading cash flow transactions...")
        run_async(self, self._fetch_data, self._on_data_ready)

    def _reload_finished(self):
        self._reload_in_flight = False
        self._loading_more = False
        if self._reload_pending:
            self._reload_pending = False
            QTimer.singleShot(0, self._load_data)

    def _fetch_data(self):
        # Page 0 only + a lightweight aggregate summary that stays accurate
        # regardless of how many pages get loaded into the table.
        txs = repo.get_cash_flow_transactions_page(
            0, self._page_size, filter_date=self._filter_date, search=self._search_text
        )
        summary = repo.get_cash_flow_summary()
        return {"transactions": txs, "summary": summary}

    def _on_data_ready(self, data):
        try:
            page = data.get("transactions", [])
            self._transactions = page
            if len(page) < self._page_size:
                self._has_more = False
            summary = data.get("summary", {})
            self._summary = summary

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

            # _populate_table() kicks off async batch rendering; the loader is
            # hidden by _render_next_batch once the LAST batch finishes (which
            # also covers the empty/zero-row case), not here.
            self._populate_table()
        except Exception:
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            self._reload_finished()
            raise

    def _populate_table(self):
        # Cancel any in-flight batched render from a previous populate call.
        self._render_token += 1
        token = self._render_token

        self._row_checkboxes.clear()
        # Keep only selected IDs that still exist in current transactions
        visible_ids = {int(tx["id"]) for tx in self._transactions if tx.get("id")}
        self._selected_ids.intersection_update(visible_ids)

        # Hoist per-row-invariant permission checks out of the loop.
        self._render_can_edit = SessionManager.has_permission("cashflow", "edit")
        self._render_can_del = SessionManager.has_permission("cashflow", "delete")

        # Set row count once upfront; disable sorting during bulk fill.
        self._rendering = True
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._transactions))

        # Build a queue of (row_index, tx) and render in yielding batches so the
        # UI event loop stays responsive during heavy cell-widget construction.
        self._render_queue = list(enumerate(self._transactions))
        self._render_next_batch(token)

    def _render_next_batch(self, token, batch_size=15, is_append=False):
        # Cancel stale batches if a newer populate has started.
        if token != self._render_token:
            return

        self.table.setUpdatesEnabled(False)
        try:
            batch = self._render_queue[:batch_size]
            del self._render_queue[:batch_size]
            for r_idx, tx in batch:
                self._build_table_row(r_idx, tx, self._render_can_edit, self._render_can_del)
        finally:
            self.table.setUpdatesEnabled(True)

        if self._render_queue:
            QTimer.singleShot(0, lambda: self._render_next_batch(token, batch_size, is_append))
        else:
            self.table.setSortingEnabled(False)
            self._update_selection_ui()
            # Pipeline truly finished (queue drained) for both reload and append.
            self._rendering = False
            if is_append:
                # Appending a scroll-page - the loader was never shown and this
                # is not a full reload, so just release the load-more guard.
                self._loading_more = False
            else:
                # Full render pipeline complete - safe to hide the loader now and
                # let a coalesced reload (if any was requested mid-render) run.
                if hasattr(self, "_loader"):
                    self._loader.hide_overlay()
                self._reload_finished()

    def _on_scroll_near_bottom(self, value):
        sb = self.table.verticalScrollBar()
        if sb.maximum() - value < 200:
            self._load_more()

    def _load_more(self):
        if self._loading_more or not self._has_more:
            return
        # Don't append pages while the batched render pipeline (initial page or a
        # previous append) is still in flight - both would mutate the table.
        if self._rendering:
            return
        # Don't append pages while a full reload/render is still running.
        if getattr(self, "_reload_in_flight", False):
            return
        self._loading_more = True
        if self._cached_remainder is not None:
            # Serve the next slice straight from the pre-loaded list - no DB hit.
            more = self._cached_remainder[:self._page_size]
            self._cached_remainder = self._cached_remainder[self._page_size:]
            if not self._cached_remainder:
                self._has_more = False
            QTimer.singleShot(0, lambda: self._on_more_loaded(more))
            return
        run_async(self, repo.get_cash_flow_transactions_page, self._on_more_loaded,
                  None, len(self._transactions), self._page_size,
                  self._filter_date, self._search_text)

    def _on_more_loaded(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        new_rows = data or []
        if self._cached_remainder is None and len(new_rows) < self._page_size:
            self._has_more = False
        if not new_rows:
            self._loading_more = False
            return
        self._append_rows(new_rows)

    def _append_rows(self, new_rows):
        # Grow the table and fill ONLY the new row indices, reusing the same
        # batch-chunking renderer so appending a page doesn't cause a stutter.
        start = len(self._transactions)
        self._transactions.extend(new_rows)

        self._render_token += 1
        token = self._render_token

        self._render_can_edit = SessionManager.has_permission("cashflow", "edit")
        self._render_can_del = SessionManager.has_permission("cashflow", "delete")

        self._rendering = True
        self.table.setSortingEnabled(False)
        self.table.setRowCount(start + len(new_rows))
        self._render_queue = list(enumerate(new_rows, start=start))
        self._render_next_batch(token, is_append=True)

    def _build_table_row(self, r_idx, tx, can_edit, can_del):
        tx_id = int(tx.get("id") or 0)

        # Column 0: Checkbox
        cb_widget = QWidget()
        cb_lay = QHBoxLayout(cb_widget)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setAlignment(Qt.AlignCenter)
        cb = QCheckBox()
        cb.setCursor(Qt.PointingHandCursor)
        cb.setChecked(tx_id in self._selected_ids)
        cb.toggled.connect(lambda checked, tid=tx_id: self._on_row_checked(tid, checked))
        cb_lay.addWidget(cb)
        self._row_checkboxes[tx_id] = cb
        self.table.setCellWidget(r_idx, 0, cb_widget)

        # Column 1: Date
        d_val = str(tx.get("date", ""))
        try:
            qd = QDate.fromString(d_val, "yyyy-MM-dd")
            date_str = qd.toString("MMM dd, yyyy") if qd.isValid() else d_val
        except Exception:
            date_str = d_val
        item_d = QTableWidgetItem(date_str)
        item_d.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Column 2: Check #
        item_c = QTableWidgetItem(str(tx.get("check_no", "") or "—"))
        item_c.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Column 3: Particulars
        part_text = str(tx.get("particulars", ""))
        if tx.get("notes"):
            part_text += f" ({tx['notes']})"
        item_p = QTableWidgetItem(part_text)
        item_p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        item_p.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Column 4: Deposit
        dep_val = float(tx.get("deposit") or 0.0)
        item_dep = QTableWidgetItem(f"₱ {dep_val:,.2f}" if dep_val > 0 else "—")
        item_dep.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if dep_val > 0:
            item_dep.setForeground(QColor("#22C55E"))

        # Column 5: Withdrawal
        withd_val = float(tx.get("withdrawal") or 0.0)
        item_w = QTableWidgetItem(f"₱ {withd_val:,.2f}" if withd_val > 0 else "—")
        item_w.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if withd_val > 0:
            item_w.setForeground(QColor("#EF4444"))

        # Column 6: Balance
        bal_val = float(tx.get("balance") or 0.0)
        bal_str = f"₱ {bal_val:,.2f}" if bal_val >= 0 else f"(₱ {abs(bal_val):,.2f})"
        item_bal = QTableWidgetItem(bal_str)
        item_bal.setFont(QFont("Segoe UI", 10, QFont.Bold))
        item_bal.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item_bal.setForeground(QColor("#22C55E" if bal_val >= 0 else "#EF4444"))

        # Column 7: Actual Sales
        sales_val = float(tx.get("actual_sales") or 0.0)
        sales_str = f"₱ {sales_val:,.2f}" if sales_val > 0 else "—"
        item_sales = QTableWidgetItem(sales_str)
        item_sales.setFont(QFont("Segoe UI", 10, QFont.Bold))
        item_sales.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if sales_val > 0:
            item_sales.setForeground(QColor("#C084FC"))

        # Column 8: Variance / Difference (Balance - Actual Sales)
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

        self.table.setItem(r_idx, 1, item_d)
        self.table.setItem(r_idx, 2, item_c)
        self.table.setItem(r_idx, 3, item_p)
        self.table.setItem(r_idx, 4, item_dep)
        self.table.setItem(r_idx, 5, item_w)
        self.table.setItem(r_idx, 6, item_bal)
        self.table.setItem(r_idx, 7, item_sales)
        self.table.setItem(r_idx, 8, item_diff)

        # Column 9: Actions (Edit / Delete)
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

        if can_edit:
            act_lay.addWidget(edit_btn)
        if can_del:
            act_lay.addWidget(del_btn)
        self.table.setCellWidget(r_idx, 9, act_widget)

    def _on_row_checked(self, tx_id: int, checked: bool):
        if checked:
            self._selected_ids.add(tx_id)
        else:
            self._selected_ids.discard(tx_id)
        self._update_selection_ui()

    def _toggle_select_all(self, state):
        visible_tx_ids = [int(tx["id"]) for tx in self._transactions if tx.get("id")]
        if state:
            self._selected_ids.update(visible_tx_ids)
        else:
            self._selected_ids.difference_update(visible_tx_ids)

        for tx_id, cb in self._row_checkboxes.items():
            if tx_id in visible_tx_ids:
                cb.blockSignals(True)
                cb.setChecked(bool(state))
                cb.blockSignals(False)

        self._update_selection_ui()

    def _update_selection_ui(self):
        count = len(self._selected_ids)
        self._lbl_selected_count.setText(f"{count} selected")
        can_delete = SessionManager.has_permission("cashflow", "delete")
        self._btn_delete_selected.setEnabled(count > 0 and can_delete)
        self._btn_delete_selected.setVisible(can_delete)
        self._btn_delete_selected.setText(f"  Delete Selected ({count})" if count > 0 else "  Delete Selected")

        visible_tx_ids = [int(tx["id"]) for tx in self._transactions if tx.get("id")]
        all_checked = len(visible_tx_ids) > 0 and all(tid in self._selected_ids for tid in visible_tx_ids)
        self._cb_select_all.blockSignals(True)
        self._cb_select_all.setChecked(all_checked)
        self._cb_select_all.blockSignals(False)

    def _delete_selected_transactions(self):
        if not SessionManager.has_permission("cashflow", "delete"):
            error(self, title="Access Denied", message="You do not have permission to delete transactions.")
            return
        if not self._selected_ids:
            return
        count = len(self._selected_ids)
        if not confirm(self, title="Delete Multiple Transactions",
                       message=f"Are you sure you want to permanently delete {count} selected cash flow transaction(s)?\nRunning balances will be recalculated automatically.",
                       confirm_label=f"Delete {count} Transactions", danger=True):
            return

        deleted = repo.delete_cash_flow_transactions(list(self._selected_ids))
        self._selected_ids.clear()
        self._load_data()
        try:
            from utils.signals import app_events
            app_events().cash_flow_saved.emit()
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message=f"Successfully deleted {deleted} transaction(s).")

    def _open_add_dialog(self):
        if not SessionManager.has_permission("cashflow", "create"):
            error(self, title="Access Denied", message="You do not have permission to add transactions.")
            return
        dlg = TransactionModal(self)
        if dlg.exec():
            self._load_data()
            try:
                from utils.signals import app_events
                app_events().cash_flow_saved.emit()
                app_events().data_changed.emit()
            except Exception:
                pass
            success(self, message="Cash flow transaction recorded.")

    def _edit_transaction(self, tx: dict):
        if not SessionManager.has_permission("cashflow", "edit"):
            error(self, title="Access Denied", message="You do not have permission to edit transactions.")
            return
        dlg = TransactionModal(self, tx_data=tx)
        if dlg.exec():
            self._load_data()
            try:
                from utils.signals import app_events
                app_events().cash_flow_saved.emit()
                app_events().data_changed.emit()
            except Exception:
                pass
            success(self, message="Transaction updated.")

    def _delete_transaction(self, tx: dict):
        if not SessionManager.has_permission("cashflow", "delete"):
            error(self, title="Access Denied", message="You do not have permission to delete transactions.")
            return
        if not confirm(self, title="Delete Transaction",
                       message=f"Are you sure you want to delete transaction for '{tx.get('particulars')}'?",
                       confirm_label="Delete", danger=True):
            return
        tx_id = int(tx.get("id") or 0)
        repo.delete_cash_flow_transaction(tx_id)
        self._selected_ids.discard(tx_id)
        self._load_data()
        try:
            from utils.signals import app_events
            app_events().cash_flow_saved.emit()
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message="Transaction deleted.")

    def _open_import_dialog(self):
        if not SessionManager.has_permission("cashflow", "create"):
            error(self, title="Access Denied", message="You do not have permission to import transactions.")
            return
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
