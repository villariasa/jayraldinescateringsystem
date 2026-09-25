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
from utils.animations import animate_dialog_open, create_soft_shadow


_DEFAULT_PARTICULARS = [
    "Cash on Hand",
    "GCash",
    "Maya",
    "UnionBank",
    "BDO Personal Savings (DOWN PAYMENT)",
    "BDO Personal Checking (CAFE)",
    "BDO Jayraldine's Catering (CATERING)",
    "BPI Personal Savings",
]


class TransactionModal(QDialog):
    def __init__(self, parent=None, tx_data: dict = None, default_classification: str = None):
        super().__init__(parent)
        self._tx = tx_data or {}
        self._default_classification = default_classification
        self.setWindowTitle("Edit Transaction" if self._tx else "Add Cash Flow Transaction")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(620)
        self.setModal(True)

        dep = float(self._tx.get("deposit") or 0.0)
        withd = float(self._tx.get("withdrawal") or 0.0)
        if withd > 0 and dep == 0:
            self._tx_type = "withdrawal"
            self._initial_amount = withd
        else:
            self._tx_type = "deposit"
            self._initial_amount = dep if dep > 0 else 0.0

        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240, auto_center=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("modalCard")
        create_soft_shadow(container, radius=32, y_offset=8, opacity=50)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(26, 22, 26, 22)
        lay.setSpacing(14)

        # ── 1. Header ─────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        is_edit = bool(self._tx)
        icon_badge = QFrame()
        icon_badge.setFixedSize(40, 40)
        if is_edit:
            icon_badge.setStyleSheet(
                "background: rgba(56, 189, 248, 0.15); border: 1.5px solid rgba(56, 189, 248, 0.4); border-radius: 20px;"
            )
        else:
            icon_badge.setStyleSheet(
                "background: rgba(34, 197, 94, 0.15); border: 1.5px solid rgba(34, 197, 94, 0.4); border-radius: 20px;"
            )
        ib_lay = QVBoxLayout(icon_badge)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        ib_lay.setAlignment(Qt.AlignCenter)
        ib_lbl = QLabel("✎" if is_edit else "+")
        ib_lbl.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {'#38BDF8' if is_edit else '#22C55E'};")
        ib_lay.addWidget(ib_lbl)
        header.addWidget(icon_badge)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        title_text = "Edit Cash Flow Transaction" if is_edit else "Add Cash Flow Transaction"
        title = QLabel(title_text)
        title.setObjectName("h3")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F9FAFB;")
        sub_text = (
            f"Update reference #{self._tx.get('check_no') or self._tx.get('id')}"
            if is_edit
            else "Record money movement, deposits, withdrawals, and bank reconciliations."
        )
        sub = QLabel(sub_text)
        sub.setObjectName("subtitle")
        sub.setStyleSheet("font-size: 12px; color: #9CA3AF;")
        v_head.addWidget(title)
        v_head.addWidget(sub)
        header.addLayout(v_head, 1)

        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#9CA3AF", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 14px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.1); }"
        )
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn, alignment=Qt.AlignTop)
        lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        lay.addWidget(div)

        # ── 2. Segmented Transaction Type Pill ────────────────────
        type_box = QHBoxLayout()
        type_box.setSpacing(10)

        self._btn_type_dep = QPushButton("  📥 Deposit (Money In)")
        self._btn_type_dep.setCursor(Qt.PointingHandCursor)
        self._btn_type_dep.setFixedHeight(38)
        self._btn_type_dep.clicked.connect(lambda: self._set_tx_type("deposit"))

        self._btn_type_withd = QPushButton("  📤 Withdrawal (Money Out)")
        self._btn_type_withd.setCursor(Qt.PointingHandCursor)
        self._btn_type_withd.setFixedHeight(38)
        self._btn_type_withd.clicked.connect(lambda: self._set_tx_type("withdrawal"))

        type_box.addWidget(self._btn_type_dep, 1)
        type_box.addWidget(self._btn_type_withd, 1)
        lay.addLayout(type_box)

        self._lbl_type_hint = QLabel()
        self._lbl_type_hint.setStyleSheet("font-size: 11px; font-weight: 600; margin-left: 2px;")
        lay.addWidget(self._lbl_type_hint)

        # ── 3. Amount Input & Quick Presets ───────────────────────
        amt_card = QFrame()
        amt_card.setStyleSheet(
            "QFrame { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; }"
        )
        amt_lay = QVBoxLayout(amt_card)
        amt_lay.setContentsMargins(14, 12, 14, 12)
        amt_lay.setSpacing(8)

        self._lbl_amount_title = QLabel("Transaction Amount *")
        self._lbl_amount_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF; text-transform: uppercase;")
        amt_lay.addWidget(self._lbl_amount_title)

        self._amount_f = QDoubleSpinBox()
        self._amount_f.setRange(0, 999999999)
        self._amount_f.setDecimals(2)
        self._amount_f.setPrefix("₱ ")
        self._amount_f.setValue(self._initial_amount)
        self._amount_f.setFixedHeight(46)
        amt_lay.addWidget(self._amount_f)

        # Quick preset buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        for label, val in [("+₱500", 500), ("+₱1k", 1000), ("+₱5k", 5000), ("+₱10k", 10000), ("+₱50k", 50000)]:
            p_btn = QPushButton(label)
            p_btn.setCursor(Qt.PointingHandCursor)
            p_btn.setFixedHeight(26)
            p_btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.12); color: #E5E7EB; border-radius: 6px; font-size: 11px; font-weight: 600; padding: 0 8px; }"
                "QPushButton:hover { background: rgba(255, 255, 255, 0.12); border-color: rgba(255, 255, 255, 0.25); color: #FFFFFF; }"
            )
            p_btn.clicked.connect(lambda _, add_val=val: self._add_preset(add_val))
            preset_row.addWidget(p_btn)

        clear_btn = QPushButton("↺ Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedHeight(26)
        clear_btn.setStyleSheet(
            "QPushButton { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25); color: #FCA5A5; border-radius: 6px; font-size: 11px; font-weight: 600; padding: 0 8px; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.2); border-color: #EF4444; color: #FFFFFF; }"
        )
        clear_btn.clicked.connect(lambda: self._amount_f.setValue(0.0))
        preset_row.addWidget(clear_btn)
        preset_row.addStretch()
        amt_lay.addLayout(preset_row)

        lay.addWidget(amt_card)

        # ── 4. Particulars / Account Classification ───────────────
        v_part = QVBoxLayout()
        v_part.setSpacing(8)
        lbl_part = QLabel("Account / Classification *")
        lbl_part.setStyleSheet("font-size: 12px; font-weight: 700; color: #D1D5DB; padding-top: 4px; padding-bottom: 2px;")
        v_part.addWidget(lbl_part)

        self._part_f = QComboBox()
        self._part_f.setEditable(True)
        self._part_f.setFixedHeight(40)
        self._part_f.setStyleSheet(
            "QComboBox { font-size: 13px; font-weight: 600; padding: 6px 12px; border-radius: 8px; }"
            "QComboBox::drop-down { width: 28px; border: none; background: transparent; }"
            "QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #9CA3AF; width: 0; height: 0; margin-right: 8px; }"
        )
        self._part_f.addItems(_DEFAULT_PARTICULARS)

        target_account = self._tx.get("particulars") or self._default_classification
        if target_account:
            idx = self._part_f.findText(target_account)
            if idx >= 0:
                self._part_f.setCurrentIndex(idx)
            else:
                self._part_f.setEditText(target_account)
        v_part.addWidget(self._part_f)

        # Quick account chips
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        chips_row.setContentsMargins(0, 2, 0, 2)
        for chip_name in ["Cash on Hand", "GCash", "Maya", "UnionBank", "BDO Jayraldine's Catering (CATERING)"]:
            short_lbl = chip_name.replace("BDO Jayraldine's Catering (CATERING)", "BDO Catering")
            c_btn = QPushButton(short_lbl)
            c_btn.setCursor(Qt.PointingHandCursor)
            c_btn.setFixedHeight(28)
            c_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            c_btn.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12); color: #D1D5DB; border-radius: 14px; font-size: 11px; font-weight: 600; padding: 2px 14px; }"
                "QPushButton:hover { background: rgba(56, 189, 248, 0.15); border-color: #38BDF8; color: #38BDF8; }"
            )
            c_btn.clicked.connect(lambda _, name=chip_name: self._set_account_chip(name))
            chips_row.addWidget(c_btn)
        chips_row.addStretch()
        v_part.addLayout(chips_row)
        lay.addLayout(v_part)

        # ── 5. Two-column Row: Date & Check # ─────────────────────
        date_ref_row = QHBoxLayout()
        date_ref_row.setSpacing(12)

        v_date = QVBoxLayout()
        v_date.setSpacing(6)
        lbl_date = QLabel("Transaction Date *")
        lbl_date.setStyleSheet("font-size: 12px; font-weight: 700; color: #D1D5DB;")
        v_date.addWidget(lbl_date)

        self._date_f = QDateEdit()
        self._date_f.setCalendarPopup(True)
        self._date_f.setDisplayFormat("MMM dd, yyyy")
        self._date_f.setFixedHeight(38)
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
        v_date.addWidget(self._date_f)
        date_ref_row.addLayout(v_date, 1)

        v_check = QVBoxLayout()
        v_check.setSpacing(6)
        lbl_check = QLabel("Check # / Ref #")
        lbl_check.setStyleSheet("font-size: 12px; font-weight: 700; color: #D1D5DB;")
        v_check.addWidget(lbl_check)

        self._check_f = QLineEdit(self._tx.get("check_no", "") or "")
        self._check_f.setPlaceholderText("e.g. GCASH-101, REF-882, CHK-001")
        self._check_f.setFixedHeight(38)
        v_check.addWidget(self._check_f)
        date_ref_row.addLayout(v_check, 1)

        lay.addLayout(date_ref_row)

        # ── 6. Notes & Optional Actual Sales ──────────────────────
        opt_row = QHBoxLayout()
        opt_row.setSpacing(12)

        v_notes = QVBoxLayout()
        v_notes.setSpacing(6)
        lbl_notes = QLabel("Notes / Description")
        lbl_notes.setStyleSheet("font-size: 12px; font-weight: 700; color: #D1D5DB;")
        v_notes.addWidget(lbl_notes)
        self._notes_f = QLineEdit(self._tx.get("notes", "") or "")
        self._notes_f.setPlaceholderText("Optional description or purpose...")
        self._notes_f.setFixedHeight(38)
        self._notes_f.returnPressed.connect(self._save)
        v_notes.addWidget(self._notes_f)
        opt_row.addLayout(v_notes, 2)

        v_sales = QVBoxLayout()
        v_sales.setSpacing(6)
        lbl_sales = QLabel("Actual Sales (Optional)")
        lbl_sales.setStyleSheet("font-size: 12px; font-weight: 700; color: #9CA3AF;")
        v_sales.addWidget(lbl_sales)
        self._actual_sales_f = QDoubleSpinBox()
        self._actual_sales_f.setRange(0, 999999999)
        self._actual_sales_f.setDecimals(2)
        self._actual_sales_f.setPrefix("₱ ")
        self._actual_sales_f.setValue(float(self._tx.get("actual_sales") or 0.0))
        self._actual_sales_f.setFixedHeight(38)
        v_sales.addWidget(self._actual_sales_f)
        opt_row.addLayout(v_sales, 1)

        lay.addLayout(opt_row)

        # ── 7. Footer Action Row ──────────────────────────────────
        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 8, 0, 0)
        lbl_lock = QLabel("🔒 Balances recalculate automatically")
        lbl_lock.setStyleSheet("font-size: 11px; color: #6B7280;")
        foot_row.addWidget(lbl_lock)
        foot_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(38)
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("  Save Transaction" if not is_edit else "  Update Transaction")
        save_btn.setObjectName("primaryButton")
        save_btn.setIcon(btn_icon_primary("check"))
        save_btn.setIconSize(QSize(14, 14))
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(38)
        save_btn.setMinimumWidth(155)
        save_btn.clicked.connect(self._save)

        foot_row.addWidget(cancel_btn)
        foot_row.addWidget(save_btn)
        lay.addLayout(foot_row)

        outer.addWidget(container)
        self._update_type_ui()

    def _set_tx_type(self, tx_type: str):
        self._tx_type = tx_type
        self._update_type_ui()

    def _update_type_ui(self):
        if self._tx_type == "deposit":
            self._btn_type_dep.setStyleSheet(
                "QPushButton { background: rgba(34, 197, 94, 0.2); border: 2px solid #22C55E; color: #22C55E; font-weight: 700; border-radius: 9px; padding: 8px 14px; font-size: 13px; }"
            )
            self._btn_type_withd.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); color: #9CA3AF; font-weight: 600; border-radius: 9px; padding: 8px 14px; font-size: 13px; }"
                "QPushButton:hover { background: rgba(239, 68, 68, 0.1); color: #FCA5A5; }"
            )
            self._lbl_amount_title.setText("Deposit Amount (Money In) *")
            self._lbl_type_hint.setText("🟢 Money In: Increases balance in the selected account.")
            self._lbl_type_hint.setStyleSheet("font-size: 11px; font-weight: 600; color: #22C55E; margin-left: 2px;")
            self._amount_f.setStyleSheet(
                "QDoubleSpinBox { font-size: 22px; font-weight: 800; color: #22C55E; padding: 4px 12px; border: 1.5px solid rgba(34, 197, 94, 0.4); border-radius: 8px; background: rgba(34, 197, 94, 0.05); }"
                "QDoubleSpinBox:focus { border: 2px solid #22C55E; }"
            )
        else:
            self._btn_type_withd.setStyleSheet(
                "QPushButton { background: rgba(239, 68, 68, 0.2); border: 2px solid #EF4444; color: #EF4444; font-weight: 700; border-radius: 9px; padding: 8px 14px; font-size: 13px; }"
            )
            self._btn_type_dep.setStyleSheet(
                "QPushButton { background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); color: #9CA3AF; font-weight: 600; border-radius: 9px; padding: 8px 14px; font-size: 13px; }"
                "QPushButton:hover { background: rgba(34, 197, 94, 0.1); color: #86EFAC; }"
            )
            self._lbl_amount_title.setText("Withdrawal Amount (Money Out) *")
            self._lbl_type_hint.setText("🔴 Money Out: Deducts funds from the selected account.")
            self._lbl_type_hint.setStyleSheet("font-size: 11px; font-weight: 600; color: #EF4444; margin-left: 2px;")
            self._amount_f.setStyleSheet(
                "QDoubleSpinBox { font-size: 22px; font-weight: 800; color: #EF4444; padding: 4px 12px; border: 1.5px solid rgba(239, 68, 68, 0.4); border-radius: 8px; background: rgba(239, 68, 68, 0.05); }"
                "QDoubleSpinBox:focus { border: 2px solid #EF4444; }"
            )

    def _add_preset(self, val: float):
        curr = self._amount_f.value()
        self._amount_f.setValue(curr + val)

    def _set_account_chip(self, name: str):
        idx = self._part_f.findText(name)
        if idx >= 0:
            self._part_f.setCurrentIndex(idx)
        else:
            self._part_f.setEditText(name)

    def _save(self):
        part = self._part_f.currentText().strip()
        if not part:
            QMessageBox.warning(self, "Validation Error", "Please provide a valid account or particulars description.")
            return

        amt = self._amount_f.value()
        actual_sales = self._actual_sales_f.value()

        if amt <= 0 and actual_sales <= 0:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid Transaction Amount greater than ₱ 0.00.")
            return

        if self._tx_type == "deposit":
            dep = amt
            withd = 0.0
        else:
            dep = 0.0
            withd = amt

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
        self._filter_classification = None
        self._classification_balances = {}
        self._search_text = ""
        self._reload_deferred = False
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

    def _has_active_search(self) -> bool:
        try:
            return bool(self._search_input.text().strip())
        except Exception:
            return bool(getattr(self, "_search_text", "").strip())

    def _mark_dirty_and_reload(self):
        self._dirty = True
        # Don't rebuild the table while the user is actively searching.
        if self._has_active_search():
            self._reload_deferred = True
            return
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

        # Per-row Edit/Delete controls are baked in at render time, so a role
        # change (e.g. logging back in as Admin after a Staff session) would
        # otherwise leave already-rendered rows showing the PREVIOUS user's
        # permissions. Rebuild the table when the permission set changes.
        sig = (can_create, can_edit, can_delete)
        if sig != getattr(self, "_last_perm_sig", None):
            self._last_perm_sig = sig
            if getattr(self, "_transactions", None) and not getattr(self, "_rendering", False):
                self._populate_table()

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

        lbl_cls = QLabel("Classification:")
        lbl_cls.setStyleSheet("font-weight: 600; font-size: 12px; color: #9CA3AF;")
        f_lay.addWidget(lbl_cls)

        self._combo_classification = QComboBox()
        self._combo_classification.setFixedHeight(36)
        self._combo_classification.setMinimumWidth(240)
        self._combo_classification.addItem("📁 All Accounts / Classifications", None)
        for p in _DEFAULT_PARTICULARS:
            self._combo_classification.addItem(p, p)
        self._combo_classification.currentIndexChanged.connect(self._on_classification_changed)
        f_lay.addWidget(self._combo_classification)

        self._lbl_account_badge = QLabel("📁 Total Balance: ₱ 0.00")
        self._lbl_account_badge.setFixedHeight(36)
        self._lbl_account_badge.setStyleSheet(
            "background: rgba(56, 189, 248, 0.12); color: #38BDF8; font-weight: 700; font-size: 12px; padding: 4px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.28);"
        )
        f_lay.addWidget(self._lbl_account_badge)

        f_lay.addSpacing(6)
        lbl_search = QLabel("Search:")
        lbl_search.setStyleSheet("font-weight: 600; font-size: 12px; color: #9CA3AF;")
        f_lay.addWidget(lbl_search)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter check #, notes, or details...")
        self._search_input.setFixedHeight(36)
        self._search_input.textChanged.connect(self._on_search_changed)
        f_lay.addWidget(self._search_input, 2)

        f_lay.addSpacing(6)
        lbl_date = QLabel("Date:")
        lbl_date.setStyleSheet("font-weight: 600; font-size: 12px; color: #9CA3AF;")
        f_lay.addWidget(lbl_date)

        self._btn_all_dates = QPushButton("All Dates")
        self._btn_all_dates.setObjectName("primaryButton")
        self._btn_all_dates.setFixedHeight(36)
        self._btn_all_dates.clicked.connect(lambda: self._set_date_filter(None))
        f_lay.addWidget(self._btn_all_dates)

        self._btn_today = QPushButton("Today")
        self._btn_today.setObjectName("secondaryButton")
        self._btn_today.setFixedHeight(36)
        self._btn_today.clicked.connect(lambda: self._set_date_filter(datetime.now().strftime("%Y-%m-%d")))
        f_lay.addWidget(self._btn_today)

        self._spec_date = QDateEdit(QDate.currentDate())
        self._spec_date.setCalendarPopup(True)
        self._spec_date.setDisplayFormat("MMM dd, yyyy")
        self._spec_date.setFixedHeight(36)
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
        card._title_lbl = t_lbl
        card._val_lbl = v_lbl

        lay.addWidget(t_lbl)
        lay.addWidget(v_lbl)
        return card

    def _on_classification_changed(self, idx: int):
        val = self._combo_classification.currentData()
        self._filter_classification = val
        self._load_data()

    def _update_combo_item_balances(self, balances: dict, total_balance: float):
        self._combo_classification.blockSignals(True)
        try:
            all_str = f"₱ {total_balance:,.2f}" if total_balance >= 0 else f"(₱ {abs(total_balance):,.2f})"
            self._combo_classification.setItemText(0, f"📁 All Accounts ({all_str})")

            for i in range(1, self._combo_classification.count()):
                acc_name = self._combo_classification.itemData(i)
                if acc_name:
                    acc_bal = balances.get(acc_name, 0.0)
                    bal_str = f"₱ {acc_bal:,.2f}" if acc_bal >= 0 else f"(₱ {abs(acc_bal):,.2f})"
                    self._combo_classification.setItemText(i, f"{acc_name} ({bal_str})")

            # Add any extra distinct accounts from DB that aren't already in combo
            existing = {self._combo_classification.itemData(i) for i in range(self._combo_classification.count())}
            for acc_name, acc_bal in balances.items():
                if acc_name and acc_name not in existing and acc_name.lower() != "bdo personal savings (savings)".lower():
                    bal_str = f"₱ {acc_bal:,.2f}" if acc_bal >= 0 else f"(₱ {abs(acc_bal):,.2f})"
                    self._combo_classification.addItem(f"{acc_name} ({bal_str})", acc_name)
        finally:
            self._combo_classification.blockSignals(False)

    def _on_search_changed(self, text: str):
        self._search_text = text.strip()
        # Debounced - _load_data() re-fetches from the DB, so firing it on
        # every single keystroke was the actual cause of laggy search here.
        self._search_timer.start(500)

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
        self._reload_deferred = False

        # Pagination resets on every full reload - we always re-fetch page 0.
        self._has_more = True
        self._loading_more = False
        self._cached_remainder = None

        from utils.data_cache import DataCache
        if not self._filter_date and not self._search_text and not self._filter_classification:
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
        # Page 0 only + aggregate summary filtered by classification if active
        txs = repo.get_cash_flow_transactions_page(
            0, self._page_size, filter_date=self._filter_date, search=self._search_text,
            classification=self._filter_classification
        )
        summary = repo.get_cash_flow_summary(
            filter_date=self._filter_date, search=self._search_text,
            classification=self._filter_classification
        )
        balances = repo.get_cash_flow_classification_balances()
        return {"transactions": txs, "summary": summary, "balances": balances}

    def _on_data_ready(self, data):
        try:
            page = data.get("transactions", [])
            self._transactions = page
            if len(page) < self._page_size:
                self._has_more = False
            summary = data.get("summary", {})
            self._summary = summary
            balances = data.get("balances", {})
            self._classification_balances = balances

            dep = summary.get("total_deposits", 0.0)
            withd = summary.get("total_withdrawals", 0.0)
            bal = summary.get("current_balance", 0.0)
            sales = summary.get("total_actual_sales", 0.0)
            diff = summary.get("total_difference", bal - sales)

            # Update Stat Cards dynamically
            cls_name = self._filter_classification
            if cls_name and cls_name not in ("All Accounts", "All Accounts / Classifications", "All"):
                self._card_deposit._title_lbl.setText(f"{cls_name} Deposits (In)")
                self._card_withd._title_lbl.setText(f"{cls_name} Withdrawals (Out)")
                self._card_balance._title_lbl.setText(f"{cls_name} Balance")
            else:
                self._card_deposit._title_lbl.setText("Total Deposits (In)")
                self._card_withd._title_lbl.setText("Total Withdrawals (Out)")
                self._card_balance._title_lbl.setText("Running Balance")

            self._card_deposit._val_lbl.setText(f"₱ {dep:,.2f}")
            self._card_withd._val_lbl.setText(f"₱ {withd:,.2f}")
            bal_color = "#22C55E" if bal >= 0 else "#EF4444"
            self._card_balance._val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {bal_color};")
            bal_str = f"₱ {bal:,.2f}" if bal >= 0 else f"(₱ {abs(bal):,.2f})"
            self._card_balance._val_lbl.setText(bal_str)

            self._card_sales._val_lbl.setText(f"₱ {sales:,.2f}")
            diff_color = "#22C55E" if diff >= 0 else "#EF4444"
            diff_str = f"₱ {diff:,.2f}" if diff >= 0 else f"(₱ {abs(diff):,.2f})"
            self._card_diff._val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {diff_color};")
            self._card_diff._val_lbl.setText(diff_str)

            # Update Live Account Badge
            if cls_name and cls_name not in ("All Accounts", "All Accounts / Classifications", "All"):
                self._lbl_account_badge.setText(f"● {cls_name} Balance: {bal_str}")
                badge_bg = "rgba(34, 197, 94, 0.12)" if bal >= 0 else "rgba(239, 68, 68, 0.12)"
                badge_border = "rgba(34, 197, 94, 0.3)" if bal >= 0 else "rgba(239, 68, 68, 0.3)"
                self._lbl_account_badge.setStyleSheet(
                    f"background: {badge_bg}; color: {bal_color}; font-weight: 700; font-size: 12px; "
                    f"padding: 4px 12px; border-radius: 8px; border: 1px solid {badge_border};"
                )
            else:
                self._lbl_account_badge.setText(f"📁 Total Balance: {bal_str}")
                self._lbl_account_badge.setStyleSheet(
                    "background: rgba(56, 189, 248, 0.12); color: #38BDF8; font-weight: 700; font-size: 12px; "
                    "padding: 4px 12px; border-radius: 8px; border: 1px solid rgba(56, 189, 248, 0.28);"
                )

            # Update dropdown item texts with live balances
            all_current_bal = bal if not cls_name else repo.get_cash_flow_summary().get("current_balance", 0.0)
            self._update_combo_item_balances(balances, all_current_bal)

            # _populate_table() kicks off async batch rendering; the loader is
            # hidden by _render_next_batch once the LAST batch finishes (which
            # also covers the empty/zero-row case), not here.
            self._populate_table()
        except Exception:
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            self._reload_finished()
            raise

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
            # Auto-continue: keep loading the remaining pages in the background
            # without waiting for a manual scroll. Guards above have already been
            # reset, so this self-perpetuates until _has_more becomes False.
            if self._has_more and not self._loading_more:
                QTimer.singleShot(150, self._load_more)

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
                  self._filter_date, self._search_text, self._filter_classification)

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
        default_cls = self._filter_classification
        if default_cls in ("All Accounts", "All Accounts / Classifications", "All"):
            default_cls = None
        dlg = TransactionModal(self, default_classification=default_cls)
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
