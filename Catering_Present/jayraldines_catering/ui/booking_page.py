from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFileDialog, QMessageBox, QInputDialog, QScrollArea,
    QCheckBox, QComboBox, QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox,
    QTabWidget
)
from PySide6.QtCore import Qt, QSize, QDate, QTime, QTimer
from PySide6.QtGui import QColor
import os
import csv

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, btn_icon_red, get_icon
from utils.animations import animate_dialog_open
from utils.theme import ThemeManager
from components.booking_modal import BookingModal
from components.dialogs import confirm, success, prompt_file_saved
from components.filter_popover import FilterPopover
from components.loading_overlay import LoadingOverlay
import utils.repository as repo
import utils.db as _db
from utils.session import get_actor
from utils.signals import app_events
from utils.data_loader import run_async


_STATUS_COLORS = {
    "CONFIRMED": ("#22C55E", "rgba(34,197,94,.15)", "rgba(34,197,94,.3)"),
    "PENDING":   ("#F59E0B", "rgba(245,158,11,.15)", "rgba(245,158,11,.3)"),
    "CANCELLED": ("#EF4444", "rgba(239,68,68,.15)",  "rgba(239,68,68,.3)"),
}


class AnimatedCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


def _status_badge(text):
    color, bg, border = _STATUS_COLORS.get(text, ("#9CA3AF", "rgba(156,163,175,.15)", "rgba(156,163,175,.3)"))
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-weight:700;font-size:11px;padding:4px 10px;border-radius:12px;"
        f"background:{bg};color:{color};border:1px solid {border};"
    )
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


def _action_buttons(status, on_approve, on_decline, can_edit=True):
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(4, 0, 4, 0)
    row.setSpacing(6)
    if status == "PENDING" and can_edit:
        approve_btn = QPushButton()
        approve_btn.setIcon(get_icon("check", color="#22C55E", size=QSize(16, 16)))
        approve_btn.setIconSize(QSize(16, 16))
        approve_btn.setFixedSize(28, 28)
        approve_btn.setStyleSheet(
            "border-radius:14px;"
            "background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.3);"
        )
        approve_btn.setCursor(Qt.PointingHandCursor)
        approve_btn.setToolTip("Approve Booking")
        approve_btn.clicked.connect(on_approve)
        row.addWidget(approve_btn)

        decline_btn = QPushButton()
        decline_btn.setIcon(get_icon("x-circle", color="#EF4444", size=QSize(16, 16)))
        decline_btn.setIconSize(QSize(16, 16))
        decline_btn.setFixedSize(28, 28)
        decline_btn.setStyleSheet(
            "border-radius:14px;"
            "background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3);"
        )
        decline_btn.setCursor(Qt.PointingHandCursor)
        decline_btn.setToolTip("Decline Booking")
        decline_btn.clicked.connect(on_decline)
        row.addWidget(decline_btn)
    else:
        locked_lbl = QLabel("")
        row.addWidget(locked_lbl)
    row.addStretch()
    return widget


class AdditionalChargesDialog(QDialog):
    """View / add / remove Additional Charges & Items for a single order.

    Every charge is a separate, visible line item that adds on top of the
    order's base total - it must never silently merge into a flat total.
    """

    def __init__(self, parent=None, booking: dict = None):
        super().__init__(parent)
        self._booking = booking or {}
        self._booking_id = self._booking.get("db_id")
        self.setWindowTitle("Additional Charges / Additional Items")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(560)
        self.setModal(True)
        self.changed = False
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel(f"Additional Charges — {self._booking.get('name', '')}")
        title.setObjectName("h3")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        lay.addWidget(div)

        # Add-charge form
        form = QHBoxLayout()
        self._desc_input = QLineEdit()
        self._desc_input.setPlaceholderText("Description / Reason (e.g. Menu Change, Additional Lechon, or Discount - Loyalty)")
        self._amount_input = QDoubleSpinBox()
        self._amount_input.setRange(-10_000_000, 10_000_000)
        self._amount_input.setToolTip("Positive = additional charge. Negative = discount.")
        self._amount_input.setDecimals(2)
        self._amount_input.setPrefix("₱ ")
        self._amount_input.setFixedWidth(140)
        add_btn = QPushButton("Add Charge")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_charge)
        form.addWidget(self._desc_input, 3)
        form.addWidget(self._amount_input, 1)
        form.addWidget(add_btn)
        lay.addLayout(form)

        # Scrollable list of existing charges
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setMinimumHeight(220)
        lay.addWidget(self._scroll)

        self._total_lbl = QLabel()
        self._total_lbl.setStyleSheet("font-weight: 800; font-size: 14px; color: #F59E0B;")
        self._total_lbl.setAlignment(Qt.AlignRight)
        lay.addWidget(self._total_lbl)

        close = QPushButton("Close")
        close.setObjectName("secondaryButton")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        lay.addWidget(close, alignment=Qt.AlignRight)

        outer.addWidget(container)
        self._reload()

    def _reload(self):
        charges = repo.get_additional_charges(self._booking_id) if self._booking_id else []

        p_container = QWidget()
        p_container.setStyleSheet("background: transparent;")
        p_lay = QVBoxLayout(p_container)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(8)

        if charges:
            for ch in charges:
                card = QFrame()
                card.setObjectName("entryCard")
                pl = QHBoxLayout(card)
                pl.setContentsMargins(12, 10, 12, 10)
                pl.setSpacing(14)

                c1 = QVBoxLayout()
                c1.setSpacing(2)
                desc_lbl = QLabel(ch["description"])
                desc_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
                sub = f"Added {ch['date_added']}" + (f" by {ch['added_by']}" if ch.get("added_by") else "")
                sub_lbl = QLabel(sub)
                sub_lbl.setObjectName("subtitle")
                c1.addWidget(desc_lbl)
                c1.addWidget(sub_lbl)
                pl.addLayout(c1, 3)

                is_discount = ch["amount"] < 0
                amt_text = f"− ₱ {abs(ch['amount']):,.2f}" if is_discount else f"₱ {ch['amount']:,.2f}"
                amt_lbl = QLabel(amt_text)
                amt_lbl.setStyleSheet(f"font-weight: 800; font-size: 14px; color: {'#F59E0B' if is_discount else '#22C55E'};")
                amt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                pl.addWidget(amt_lbl, 1)

                del_btn = QPushButton()
                del_btn.setIcon(get_icon("trash", color="#EF4444", size=QSize(13, 13)))
                del_btn.setIconSize(QSize(13, 13))
                del_btn.setFixedSize(28, 28)
                del_btn.setStyleSheet("background:transparent;border:none;")
                del_btn.setCursor(Qt.PointingHandCursor)
                del_btn.setToolTip("Remove this charge")
                del_btn.clicked.connect(lambda _, cid=ch["id"]: self._delete_charge(cid))
                pl.addWidget(del_btn)

                p_lay.addWidget(card)
        else:
            empty_card = QFrame()
            empty_card.setObjectName("entryCard")
            el = QVBoxLayout(empty_card)
            item = QLabel("No additional charges recorded for this order.")
            item.setObjectName("subtitle")
            item.setAlignment(Qt.AlignCenter)
            el.addWidget(item)
            p_lay.addWidget(empty_card)

        p_lay.addStretch()
        self._scroll.setWidget(p_container)

        charges_sum = sum(c["amount"] for c in charges)
        detail = repo.get_booking_detail(self._booking_id) if self._booking_id else None
        new_total = float(detail["total"]) if detail else charges_sum
        self._total_lbl.setText(f"Additional Charges: ₱ {charges_sum:,.2f}   |   Updated Order Total: ₱ {new_total:,.2f}")

    def _add_charge(self):
        desc = self._desc_input.text().strip()
        amount = self._amount_input.value()
        if not desc:
            QMessageBox.warning(self, "Missing Description", "Please enter a description/reason for this charge.")
            return
        if amount == 0:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a non-zero amount (negative for a discount).")
            return
        if not self._booking_id:
            return
        repo.add_additional_charge(self._booking_id, desc, amount, get_actor())
        repo.write_audit_log(
            get_actor(), "ADD_CHARGE", "bookings", self._booking_id,
            None, {"description": desc, "amount": amount, "customer": self._booking.get("name")},
        )
        repo.push_notification(
            "info", "Additional Charge Added",
            f"{get_actor()} added a charge: {desc} — ₱{amount:,.2f} for {self._booking.get('name', '')}",
        )
        self._desc_input.clear()
        self._amount_input.setValue(0)
        self.changed = True
        self._reload()
        app_events().data_changed.emit()

    def _delete_charge(self, charge_id):
        if not confirm(self, title="Remove Charge", message="Remove this additional charge? This will update the order total.",
                       confirm_label="Remove", danger=True):
            return
        repo.delete_additional_charge(charge_id)
        self.changed = True
        self._reload()
        app_events().data_changed.emit()


_OCCASIONS_LIST = [
    "Wedding", "Birthday", "Debut", "Corporate Event", "Anniversary", "Christening", "Graduation", "Holiday Party", "Party"
]


class MultiMenuSelectionDialog(QDialog):
    """Interactive modal to select multiple custom dishes / menu offerings for an order."""
    def __init__(self, selected_items=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Custom Menu Dishes")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(780, 580)
        self.setModal(True)
        self._initial_selected = set(selected_items or [])
        self._checkboxes = []
        self._all_items = repo.get_available_menu_items() or []
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240, auto_center=True)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # Header
        head = QHBoxLayout()
        title = QLabel("Select Custom Menu Dishes")
        title.setObjectName("h3")
        head.addWidget(title)
        head.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        head.addWidget(close_btn)
        lay.addLayout(head)

        sub = QLabel("Pick multiple culinary dishes to create a custom catering menu for this order:")
        sub.setObjectName("subtitle")
        lay.addWidget(sub)

        # Search Bar + Quick Actions
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search dishes (e.g. Pork, Chicken, Seafood, Dessert)...")
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(self._filter_items)
        ctrl_row.addWidget(self._search, 2)

        btn_all = QPushButton("Select All")
        btn_all.setObjectName("secondaryButton")
        btn_all.setFixedHeight(36)
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.clicked.connect(self._select_all)

        btn_none = QPushButton("Clear All")
        btn_none.setObjectName("secondaryButton")
        btn_none.setFixedHeight(36)
        btn_none.setCursor(Qt.PointingHandCursor)
        btn_none.clicked.connect(self._clear_all)

        ctrl_row.addWidget(btn_all)
        ctrl_row.addWidget(btn_none)
        lay.addLayout(ctrl_row)

        # Scrollable Categorized Dish Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        self._dishes_lay = QVBoxLayout(content)
        self._dishes_lay.setContentsMargins(0, 0, 0, 0)
        self._dishes_lay.setSpacing(12)

        # Group items by category
        grouped = {}
        for item in self._all_items:
            cat = item.get("category") or "Main Course"
            grouped.setdefault(cat, []).append(item)

        if not grouped:
            empty_lbl = QLabel("No menu items found in the menu database.\nAdd dishes in the Menu module first.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self._dishes_lay.addWidget(empty_lbl)
        else:
            for cat, items in grouped.items():
                cat_group = QFrame()
                cat_group.setObjectName("entryCard")
                cg_lay = QVBoxLayout(cat_group)
                cg_lay.setContentsMargins(14, 12, 14, 12)
                cg_lay.setSpacing(6)

                cat_hdr = QLabel(f"● {cat.upper()}")
                cat_hdr.setStyleSheet("font-size: 11px; font-weight: 800; color: #E11D48; letter-spacing: 1px;")
                cg_lay.addWidget(cat_hdr)

                for it in items:
                    i_name = it.get("name") or it.get("item", "Dish")
                    i_price = float(it.get("price") or 0.0)
                    i_desc = it.get("description") or ""

                    row_frame = QFrame()
                    row_frame._dish_name = i_name
                    row_frame._dish_cat = cat
                    r_lay = QHBoxLayout(row_frame)
                    r_lay.setContentsMargins(6, 4, 6, 4)
                    r_lay.setSpacing(10)

                    cb = QCheckBox(i_name)
                    cb.setStyleSheet("QCheckBox { font-size: 13px; font-weight: 600; color: #F9FAFB; } QCheckBox::indicator { width: 18px; height: 18px; }")
                    if i_name in self._initial_selected:
                        cb.setChecked(True)
                    cb.stateChanged.connect(self._update_counter)

                    if i_desc:
                        desc_lbl = QLabel(f"— {i_desc}")
                        desc_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
                        r_lay.addWidget(cb)
                        r_lay.addWidget(desc_lbl, 1)
                    else:
                        r_lay.addWidget(cb, 1)

                    price_lbl = QLabel(f"₱ {i_price:,.2f} / pax")
                    price_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #F59E0B;")
                    r_lay.addWidget(price_lbl)

                    cg_lay.addWidget(row_frame)
                    self._checkboxes.append((cb, it, row_frame))

                self._dishes_lay.addWidget(cat_group)

        self._dishes_lay.addStretch()
        scroll.setWidget(content)
        lay.addWidget(scroll, 1)

        # Bottom Summary & Action Buttons
        bot_bar = QHBoxLayout()
        self._summary_lbl = QLabel("Selected: 0 dishes | Total Unit Rate: ₱ 0.00 / pax")
        self._summary_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #38BDF8;")
        bot_bar.addWidget(self._summary_lbl)
        bot_bar.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        bot_bar.addWidget(cancel)

        apply_btn = QPushButton("  Apply Dishes to Order")
        apply_btn.setObjectName("primaryButton")
        apply_btn.setIcon(btn_icon_primary("check"))
        apply_btn.setIconSize(QSize(15, 15))
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.clicked.connect(self.accept)
        bot_bar.addWidget(apply_btn)
        lay.addLayout(bot_bar)

        outer.addWidget(container)
        self._update_counter()

    def _filter_items(self, text: str):
        query = text.strip().lower()
        for cb, it, rf in self._checkboxes:
            dish_name = str(it.get("name") or it.get("item") or "")
            match = (
                query in dish_name.lower()
                or query in str(it.get("category") or "").lower()
                or query in str(it.get("description") or "").lower()
            )
            rf.setVisible(match)

    def _select_all(self):
        for cb, it, rf in self._checkboxes:
            if rf.isVisible():
                cb.setChecked(True)
        self._update_counter()

    def _clear_all(self):
        for cb, it, rf in self._checkboxes:
            cb.setChecked(False)
        self._update_counter()

    def _update_counter(self):
        cnt = sum(1 for cb, it, _ in self._checkboxes if cb.isChecked())
        tot = sum(float(it.get("price") or 0.0) for cb, it, _ in self._checkboxes if cb.isChecked())
        self._summary_lbl.setText(f"Selected: {cnt} dishes | Total Rate: ₱ {tot:,.2f} / pax")

    def get_selected_dishes(self) -> tuple[list[str], float]:
        selected_names = []
        sum_rate = 0.0
        for cb, it, _ in self._checkboxes:
            if cb.isChecked():
                dish_name = it.get("name") or it.get("item", "")
                selected_names.append(dish_name)
                sum_rate += float(it.get("price") or 0.0)
        return selected_names, sum_rate


class AddMultipleBookingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Multiple Orders & Bookings")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1420, 720)
        self.setMinimumSize(1020, 580)
        self.setModal(True)
        self._added_count = 0
        self._customers = repo.get_all_customers() or []
        self._packages = repo.get_all_packages() or []
        self._menu_items = repo.get_available_menu_items() or []
        self._occasions = repo.get_all_occasions() or []
        self._kpi_summary_lbl = QLabel("")
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        animate_dialog_open(self, duration=240, auto_center=True)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Add Multiple Orders & Bookings")
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

        sub = QLabel("Easily select registered customers, choose packages or multiple custom dishes, and set event dates & down payments:")
        sub.setObjectName("subtitle")
        lay.addWidget(sub)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Customer (Select or Type) *", "Contact / Phone", "Occasion", "Package / Custom Menu *",
            "Event Date *", "Event Time", "Pax *", "Theme / Motif / Notes", "Total Amount (₱) *", "Down Payment (₱)", "Action"
        ])
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setMinimumSectionSize(50)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # Generous column widths for maximum visibility of all values and dropdowns
        self.table.setColumnWidth(0, 280)  # Customer
        self.table.setColumnWidth(1, 130)  # Contact / Phone
        self.table.setColumnWidth(2, 160)  # Occasion
        self.table.setColumnWidth(3, 320)  # Package / Custom Menu
        self.table.setColumnWidth(4, 130)  # Event Date
        self.table.setColumnWidth(5, 135)  # Event Time
        self.table.setColumnWidth(6, 100)  # Pax
        self.table.setColumnWidth(7, 200)  # Theme / Motif / Notes
        self.table.setColumnWidth(8, 145)  # Total Amount
        self.table.setColumnWidth(9, 145)  # Down Payment
        self.table.setColumnWidth(10, 55)  # Action

        self.table.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.table)

        # Add 5 initial rows
        for _ in range(5):
            self._add_row()

        row_actions = QHBoxLayout()
        add_row_btn = QPushButton("  + Add Row")
        add_row_btn.setObjectName("secondaryButton")
        add_row_btn.clicked.connect(self._add_row)
        add_5_btn = QPushButton("  + Add 5 Rows")
        add_5_btn.setObjectName("secondaryButton")
        add_5_btn.clicked.connect(lambda: [self._add_row() for _ in range(5)])
        clear_btn = QPushButton("  Clear Empty Rows")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._clear_empty_rows)

        row_actions.addWidget(add_row_btn)
        row_actions.addWidget(add_5_btn)
        row_actions.addWidget(clear_btn)
        row_actions.addStretch()

        self._kpi_summary_lbl = QLabel("")
        self._kpi_summary_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #9CA3AF;")
        row_actions.addWidget(self._kpi_summary_lbl)
        lay.addLayout(row_actions)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #E11D48; font-size: 12px; font-weight: 600;")
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        save = QPushButton("  Save All Orders")
        save.setObjectName("primaryButton")
        save.setIcon(btn_icon_primary("check"))
        save.setIconSize(QSize(15, 15))
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save_all)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        lay.addLayout(btn_row)

        outer.addWidget(container)
        self._update_grand_totals()

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)

        # 0. Customer Selector (Editable QComboBox with auto-complete & auto-fill)
        cust_combo = QComboBox()
        cust_combo.setEditable(True)
        cust_combo.setFixedHeight(34)
        if cust_combo.view():
            cust_combo.view().setMinimumWidth(320)
        cust_combo.lineEdit().setPlaceholderText("Select or Type Customer Name *")
        cust_combo.addItem("+ Type New Customer Name...", None)
        for c in self._customers:
            c_name = c.get("name", "Client")
            c_phone = c.get("contact") or "No phone"
            cust_combo.addItem(f"{c_name} ({c_phone})", c)
        cust_combo.setCurrentIndex(0)
        self.table.setCellWidget(r, 0, cust_combo)

        # 1. Contact / Phone
        contact_edit = QLineEdit()
        contact_edit.setPlaceholderText("09171234567")
        contact_edit.setFixedHeight(34)
        self.table.setCellWidget(r, 1, contact_edit)

        # Auto-fill contact on customer selection
        def _on_cust_selected(idx):
            data = cust_combo.currentData()
            if isinstance(data, dict):
                phone = data.get("contact", "")
                if phone:
                    contact_edit.setText(phone)
        cust_combo.currentIndexChanged.connect(_on_cust_selected)

        # 2. Occasion (Dynamically loaded from Settings + Editable)
        occ_combo = QComboBox()
        occ_combo.setEditable(True)
        if occ_combo.view():
            occ_combo.view().setMinimumWidth(180)
        if occ_combo.lineEdit():
            occ_combo.lineEdit().setPlaceholderText("Select or Type Occasion...")
        occ_combo.addItems(self._occasions if self._occasions else ["Wedding", "Birthday", "Debut", "Party"])
        if "Party" in self._occasions:
            occ_combo.setCurrentText("Party")
        elif self._occasions:
            occ_combo.setCurrentIndex(0)
        occ_combo.setFixedHeight(34)
        self.table.setCellWidget(r, 2, occ_combo)

        # 3. Package / Custom Menu Smart Cell (Dropdown + 'Dishes' multi-select button)
        menu_widget = QWidget()
        m_lay = QHBoxLayout(menu_widget)
        m_lay.setContentsMargins(0, 0, 0, 0)
        m_lay.setSpacing(4)

        menu_combo = QComboBox()
        menu_combo.setFixedHeight(34)
        if menu_combo.view():
            menu_combo.view().setMinimumWidth(340)

        # Add Packages
        if self._packages:
            for pkg in self._packages:
                p_name = pkg.get("name", "Package")
                p_price = float(pkg.get("price_per_pax") or 0.0)
                menu_combo.addItem(f"📦 {p_name} (₱{p_price:,.0f}/pax)", {
                    "type": "package", "name": p_name, "rate": p_price, "id": pkg.get("id")
                })
        else:
            menu_combo.addItem("📦 Standard Package (₱350/pax)", {
                "type": "package", "name": "Standard Package", "rate": 350.0, "id": None
            })

        # Add Custom Multiple Dishes Entry
        menu_combo.addItem("🍽️ Custom Menu (Select Dishes...)", {
            "type": "custom", "items": [], "rate": 450.0, "name": "Custom Menu"
        })

        # Add Single Dishes
        for it in self._menu_items:
            i_name = it.get("name", "Dish")
            i_price = float(it.get("price") or 0.0)
            menu_combo.addItem(f"🍲 {i_name} (₱{i_price:,.0f}/pax)", {
                "type": "custom", "items": [i_name], "rate": i_price, "name": i_name
            })

        btn_dishes = QPushButton("🍽️ Dishes")
        btn_dishes.setObjectName("secondaryButton")
        btn_dishes.setFixedHeight(34)
        btn_dishes.setToolTip("Open multi-dish selector to pick custom menu dishes")

        m_lay.addWidget(menu_combo, 1)
        m_lay.addWidget(btn_dishes)
        self.table.setCellWidget(r, 3, menu_widget)

        # 4. Event Date
        date_edit = QDateEdit(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        date_edit.setFixedHeight(34)
        self.table.setCellWidget(r, 4, date_edit)

        # 5. Event Time (Editable QComboBox)
        time_combo = QComboBox()
        time_combo.setEditable(True)
        if time_combo.view():
            time_combo.view().setMinimumWidth(140)
        time_combo.addItems(["6:00 PM", "12:00 PM", "10:00 AM", "11:00 AM", "1:00 PM", "2:00 PM", "5:00 PM", "7:00 PM", "8:00 PM"])
        time_combo.setCurrentText("6:00 PM")
        time_combo.setFixedHeight(34)
        self.table.setCellWidget(r, 5, time_combo)

        # 6. Pax
        pax_spin = QSpinBox()
        pax_spin.setRange(1, 10000)
        pax_spin.setValue(50)
        pax_spin.setAlignment(Qt.AlignCenter)
        pax_spin.setFixedHeight(34)
        pax_spin.setStyleSheet("QSpinBox { font-size: 13px; font-weight: 700; padding: 2px 6px; }")
        self.table.setCellWidget(r, 6, pax_spin)

        # 7. Theme / Motif / Notes
        theme_edit = QLineEdit()
        theme_edit.setPlaceholderText("e.g. Purple & Gold theme, Twin Babies...")
        theme_edit.setFixedHeight(34)
        self.table.setCellWidget(r, 7, theme_edit)

        # 8. Total Amount
        total_spin = QDoubleSpinBox()
        total_spin.setRange(0, 9999999)
        total_spin.setPrefix("₱ ")
        total_spin.setDecimals(2)
        total_spin.setSingleStep(500)
        total_spin.setFixedHeight(34)
        self.table.setCellWidget(r, 8, total_spin)

        # 9. Down Payment (Defaults to ₱0.00 — user manually inputs actual payment)
        down_spin = QDoubleSpinBox()
        down_spin.setRange(0, 9999999)
        down_spin.setPrefix("₱ ")
        down_spin.setDecimals(2)
        down_spin.setSingleStep(500)
        down_spin.setValue(0.0)
        down_spin.setFixedHeight(34)
        self.table.setCellWidget(r, 9, down_spin)

        # 10. Action: Delete Row
        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", color="#EF4444", size=QSize(14, 14)))
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet("background: transparent; border: none;")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("Remove row")
        del_btn.clicked.connect(lambda _, w=menu_widget: self._delete_row_by_widget(w))
        self.table.setCellWidget(r, 10, del_btn)

        # Multi-dish selector handler
        def _open_dish_picker():
            curr_data = menu_combo.currentData() or {}
            initial_dishes = curr_data.get("items", [])
            dlg = MultiMenuSelectionDialog(selected_items=initial_dishes, parent=self)
            if dlg.exec():
                sel_names, sel_rate = dlg.get_selected_dishes()
                if sel_names:
                    label_desc = f"🍽️ Custom ({len(sel_names)} Dishes) - ₱{sel_rate:,.0f}/pax"
                    custom_payload = {
                        "type": "custom", "items": sel_names, "rate": sel_rate, "name": ", ".join(sel_names)
                    }
                    menu_combo.insertItem(0, label_desc, custom_payload)
                    menu_combo.setCurrentIndex(0)
                    _recompute_price()

        btn_dishes.clicked.connect(_open_dish_picker)

        # Auto-recompute total only (do NOT auto-assign 30% down payment)
        def _recompute_price():
            m_data = menu_combo.currentData() or {}
            rate = float(m_data.get("rate", 350.0))
            pax_val = pax_spin.value()
            computed_tot = rate * pax_val
            total_spin.setValue(computed_tot)
            self._update_grand_totals()

        menu_combo.currentIndexChanged.connect(_recompute_price)
        pax_spin.valueChanged.connect(_recompute_price)
        total_spin.valueChanged.connect(self._update_grand_totals)
        down_spin.valueChanged.connect(self._update_grand_totals)
        _recompute_price()

    def _delete_row_by_widget(self, cell_w: QWidget):
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 3) == cell_w:
                self.table.removeRow(r)
                break
        self._update_grand_totals()

    def _delete_selected_row(self):
        curr = self.table.currentRow()
        if curr >= 0:
            self.table.removeRow(curr)
        self._update_grand_totals()

    def _clear_empty_rows(self):
        r = 0
        while r < self.table.rowCount():
            name_w = self.table.cellWidget(r, 0)
            name_text = ""
            if isinstance(name_w, QComboBox):
                data = name_w.currentData()
                name_text = data.get("name", "") if isinstance(data, dict) else name_w.currentText().strip()
                if "+ Type" in name_text:
                    name_text = ""
            elif isinstance(name_w, QLineEdit):
                name_text = name_w.text().strip()

            if not name_text:
                self.table.removeRow(r)
            else:
                r += 1
        self._update_grand_totals()

    def _update_grand_totals(self):
        count = self.table.rowCount()
        tot_sales = 0.0
        tot_dp = 0.0
        for r in range(count):
            tot_w = self.table.cellWidget(r, 7)
            dp_w = self.table.cellWidget(r, 8)
            if isinstance(tot_w, QDoubleSpinBox):
                tot_sales += tot_w.value()
            if isinstance(dp_w, QDoubleSpinBox):
                tot_dp += dp_w.value()
        self._kpi_summary_lbl.setText(f"Rows: {count}  |  Total Estimated: ₱ {tot_sales:,.2f}  |  Total Down Payment: ₱ {tot_dp:,.2f}")

    def _save_all(self):
        rows_to_save = []
        for r in range(self.table.rowCount()):
            cust_w = self.table.cellWidget(r, 0)
            contact_w = self.table.cellWidget(r, 1)
            occ_w = self.table.cellWidget(r, 2)
            menu_cell = self.table.cellWidget(r, 3)
            date_w = self.table.cellWidget(r, 4)
            time_w = self.table.cellWidget(r, 5)
            pax_w = self.table.cellWidget(r, 6)
            theme_w = self.table.cellWidget(r, 7)
            total_w = self.table.cellWidget(r, 8)
            down_w = self.table.cellWidget(r, 9)

            # Customer Name extraction
            cust_name = ""
            existing_cid = None
            if isinstance(cust_w, QComboBox):
                c_data = cust_w.currentData()
                if isinstance(c_data, dict):
                    cust_name = c_data.get("name", "").strip()
                    existing_cid = c_data.get("id")
                else:
                    cust_name = cust_w.currentText().strip()
                    if "+ Type" in cust_name:
                        cust_name = ""
            elif isinstance(cust_w, QLineEdit):
                cust_name = cust_w.text().strip()

            if not cust_name:
                continue

            contact = contact_w.text().strip() if isinstance(contact_w, QLineEdit) else ""
            occ = occ_w.currentText().strip() if isinstance(occ_w, QComboBox) else "Party"

            # Menu & Package extraction
            menu_combo = menu_cell.findChild(QComboBox) if menu_cell else None
            m_data = menu_combo.currentData() if menu_combo else {}
            menu_type = m_data.get("type", "package") if isinstance(m_data, dict) else "package"
            pkg_id = m_data.get("id") if (isinstance(m_data, dict) and menu_type == "package") else None
            menu_val = ""
            if isinstance(m_data, dict):
                if menu_type == "custom":
                    items_list = m_data.get("items", [])
                    menu_val = ", ".join(items_list) if items_list else (m_data.get("name") or "Custom Menu")
                else:
                    menu_val = m_data.get("name", "Standard Package")
            else:
                menu_val = menu_combo.currentText() if menu_combo else "Standard Package"

            date_val = date_w.date().toString("yyyy-MM-dd") if isinstance(date_w, QDateEdit) else ""
            
            # Event Time extraction
            time_val = "6:00 PM"
            if isinstance(time_w, QComboBox):
                time_val = repo.format_time_ampm(time_w.currentText().strip() or "6:00 PM")
            elif isinstance(time_w, QLineEdit):
                time_val = repo.format_time_ampm(time_w.text().strip() or "6:00 PM")

            pax = pax_w.value() if isinstance(pax_w, QSpinBox) else 50
            theme_txt = theme_w.text().strip() if isinstance(theme_w, QLineEdit) else ""
            tot = total_w.value() if isinstance(total_w, QDoubleSpinBox) else 0.0
            down = down_w.value() if isinstance(down_w, QDoubleSpinBox) else 0.0

            rows_to_save.append({
                "name": cust_name,
                "customer_id": existing_cid,
                "contact": contact,
                "occasion": occ,
                "date": date_val,
                "event_time": time_val,
                "time": time_val,
                "venue": "Client Venue",
                "pax": pax,
                "total": tot,
                "amount_paid": down,
                "down_payment": down,
                "payment_mode": "Cash",
                "menu_type": menu_type,
                "menu_value": menu_val,
                "package_id": pkg_id,
                "status": "PENDING",
                "notes": theme_txt if theme_txt else f"Multi-Order entry with {menu_val}",
            })

        if not rows_to_save:
            self._err.setText("Please enter or select at least one customer.")
            self._err.show()
            return

        saved = 0
        for b_data in rows_to_save:
            cid = b_data.get("customer_id")
            if not cid:
                cust = repo.get_customer_by_name(b_data["name"])
                if not cust:
                    cid = repo.add_customer({
                        "name": b_data["name"],
                        "contact": b_data.get("contact", ""),
                        "email": "",
                        "address": b_data.get("venue", "Cebu"),
                        "status": "Active"
                    })
                else:
                    cid = cust["id"]

            b_data["customer_id"] = cid
            if "address" not in b_data:
                b_data["address"] = b_data.get("venue", "Cebu")
            ref = repo.create_booking(b_data)
            if ref:
                saved += 1

        self._added_count = saved
        self.accept()


class BookingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dirty = True
        self._bookings = []
        self._reload_in_flight = False
        self._reload_pending = False
        self._selected_refs: set[str] = set()
        self._card_checkboxes: dict[str, QCheckBox] = {}
        self._active_filter = "All"
        self._filter_popover = None
        self._search_query = ""

        # Server-side filter state (DB-level, ADDITIONAL to whatever tab
        # status_filter is active and independent of the client-side search box).
        # Defaults to "1 month back / 2 months ahead" so we never load the whole
        # booking history on open.
        self._filter_date_start, self._filter_date_end = repo.get_default_orders_window()
        self._filter_customer = None
        self._filter_event = None
        # Time-of-day filter (24h "HH:MM" strings) - None means no time
        # restriction (the default, full-day range).
        self._filter_time_start = None
        self._filter_time_end = None

        # Per-tab lazy pagination state (tab index -> value). Tabs page through
        # bookings independently by status so we never fetch/render rows nobody
        # is scrolled to. Tab 0 = Pending, 1 = Confirmed/Completed, 2 = All.
        self._page_size = 50
        self._tab_status = {0: ["PENDING"], 1: ["CONFIRMED", "COMPLETED"], 2: None}
        self._tab_rows = {0: [], 1: [], 2: []}
        self._tab_has_more = {0: True, 1: True, 2: True}
        self._tab_loading_more = {0: False, 1: False, 2: False}
        self._tab_cached_remainder = {0: None, 1: None, 2: None}
        # True while a batch-render chain (initial page OR scroll-appended page)
        # is actively mutating this tab's layout - blocks a new load-more from
        # starting mid-chain, which was corrupting the layout and crashing.
        self._tab_rendering = {0: False, 1: False, 2: False}
        self._tab_cached_full = {0: None, 1: None, 2: None}
        self._tab_layouts = {}
        self._scroll_areas = {}
        self._tab_loading_label = {0: None, 1: None, 2: None}
        self._counts = {"pending": 0, "confirmed": 0, "all": 0}
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_timer_fired)
        # Debounce server-side filter changes (editable customer combo fires
        # currentTextChanged per keystroke) so we coalesce into one DB reload.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(self._apply_server_filter_reload)
        self._build_ui()
        self._bookings = []
        self._dirty = True
        _ev = app_events()
        _ev.booking_saved.connect(self._mark_dirty_and_reload)
        _ev.booking_created.connect(self._mark_dirty_and_reload)
        _ev.booking_updated.connect(self._mark_dirty_and_reload)
        _ev.sync_completed.connect(self._mark_dirty_and_reload)
        _ev.data_changed.connect(self._mark_dirty_and_reload)

    def _mark_dirty(self):
        self._dirty = True

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self._refresh_bookings(silent=True)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_permissions()
        if getattr(self, "_dirty", True):
            self._refresh_bookings(silent=getattr(self, "_has_loaded_once", False))

    def reload(self, silent: bool = False):
        self._mark_dirty()
        self.refresh_permissions()
        if self.isVisible():
            self._refresh_bookings(silent=silent)

    def refresh_permissions(self):
        from utils.auth import SessionManager
        can_create = SessionManager.has_permission("bookings", "create")
        can_delete = SessionManager.has_permission("bookings", "delete")
        can_edit = SessionManager.has_permission("bookings", "edit")

        # Per-card Edit/Delete buttons are baked in at render time (not toggled
        # here), so a role change (e.g. logging back in as Admin after a Staff
        # session) would otherwise leave already-rendered cards showing the
        # PREVIOUS user's permissions. Force a full card rebuild when the
        # effective permission set actually changes.
        sig = (can_create, can_edit, can_delete)
        if sig != getattr(self, "_last_perm_sig", None):
            self._last_perm_sig = sig
            if getattr(self, "_bookings", None) is not None:
                self._dirty = True
                if self.isVisible():
                    self._refresh_bookings()

        if hasattr(self, "btn_new"):
            self.btn_new.setEnabled(can_create)
            self.btn_new.setVisible(can_create)
        if hasattr(self, "btn_multi_add"):
            self.btn_multi_add.setEnabled(can_create)
            self.btn_multi_add.setVisible(can_create)
        if hasattr(self, "btn_import"):
            self.btn_import.setEnabled(can_create)
            self.btn_import.setVisible(can_create)

        for tb in [getattr(self, "_pending_tb", None), getattr(self, "_confirmed_tb", None), getattr(self, "_all_tb", None)]:
            if tb:
                if tb.get("batch_approve"):
                    tb["batch_approve"].setVisible(can_edit)
                if tb.get("batch_cancel"):
                    tb["batch_cancel"].setVisible(can_edit)
                if tb.get("delete_selected"):
                    tb["delete_selected"].setVisible(can_delete)
                if tb.get("select_all"):
                    tb["select_all"].setVisible(can_edit or can_delete)
                if tb.get("selected_lbl"):
                    tb["selected_lbl"].setVisible(can_edit or can_delete)

    def _reset_pagination(self):
        # Every full reload starts each tab from page 0. Non-active tabs stay
        # empty until the user switches to them (lazy) or a memory cache is
        # available to slice their first page from with zero DB round-trips.
        for i in (0, 1, 2):
            self._tab_rows[i] = []
            self._tab_has_more[i] = True
            self._tab_loading_more[i] = False
            self._tab_cached_remainder[i] = None
            self._tab_cached_full[i] = None
        self._populated_tabs = set()

    def _refresh_bookings(self, silent: bool = False):
        # Coalesce overlapping reloads: if a reload (fetch + batch-render of the
        # active tab) is already running, don't start a second one in parallel -
        # just remember to run exactly one more pass once this one fully finishes.
        if getattr(self, "_reload_in_flight", False):
            self._reload_pending = True
            return
        if getattr(self, "_refreshing", False):
            return
        self._reload_in_flight = True
        self._reload_pending = False
        self._dirty = False

        # Pagination resets on every full reload - we always re-fetch page 0 for
        # the active tab (and lazily for the others).
        self._reset_pagination()
        self._selected_refs.clear()
        self._card_checkboxes.clear()

        # Instant render from pre-loaded memory cache if available. The login
        # welcome sequence may have cached the FULL booking list; partition it
        # per tab and slice off only page 1 for the active tab - the rest stays
        # in memory and serves subsequent scroll pages with zero DB round-trip.
        from utils.data_cache import DataCache
        cached = DataCache.get("bookings")
        if cached is not None and not getattr(self, "_has_loaded_once", False):
            self._has_loaded_once = True
            if hasattr(self, "_loader") and not silent:
                self._loader.show_overlay("Loading bookings & reservations...")
                QTimer.singleShot(60, lambda: self._load_from_cache(cached))
            else:
                self._load_from_cache(cached)
            return

        self._refreshing = True
        if hasattr(self, "_loader") and not silent and not getattr(self, "_has_loaded_once", False):
            self._loader.show_overlay("Loading bookings & reservations...")
        active_idx = self._tabs.currentIndex() if hasattr(self, "_tabs") else 0
        status = self._tab_status.get(active_idx)
        run_async(
            self, self._fetch_reload_data,
            lambda result, i=active_idx: self._on_reload_loaded(i, result),
            self._on_bookings_error,
            status, self._page_size, *self._current_filter_args(),
        )

    @staticmethod
    def _fetch_reload_data(status, page_size, date_start, date_end, customer, event, time_start=None, time_end=None):
        # Combined round trip: DB-side counts (accurate under pagination) plus
        # the active tab's first page. Both scoped by the active server-side
        # filter (date window / customer / occasion / time-of-day).
        return (
            repo.get_booking_counts(date_start, date_end, customer, event, time_start, time_end),
            repo.get_bookings_page(status, 0, page_size, date_start, date_end, customer, event, time_start, time_end),
        )

    def _on_reload_loaded(self, idx, result):
        self._refreshing = False
        from shiboken6 import isValid
        if not isValid(self):
            self._reload_in_flight = False
            return
        counts, rows = result if result else ({}, [])
        self._apply_counts(counts)
        self._has_loaded_once = True
        rows = rows or []
        self._tab_rows[idx] = list(rows)
        self._tab_has_more[idx] = len(rows) >= self._page_size
        self._rebuild_bookings()
        self._populated_tabs = set()
        self._render_tab_initial(idx)

    def _load_from_cache(self, cached):
        from shiboken6 import isValid
        if not isValid(self):
            self._reload_in_flight = False
            return
        # Scope the pre-loaded full list by the active server-side filter (the
        # default window on first open) so counts + rows match the DB path.
        cached = self._server_filter_rows(cached or [])
        pending = [b for b in cached if b.get("status") == "PENDING"]
        confirmed = [b for b in cached if b.get("status") in ("CONFIRMED", "COMPLETED")]
        self._tab_cached_full = {0: pending, 1: confirmed, 2: list(cached)}
        self._apply_counts({
            "pending": len(pending),
            "confirmed": len(confirmed),
            "all": len(cached),
        })
        idx = self._tabs.currentIndex() if hasattr(self, "_tabs") else 0
        self._serve_tab_from_cache(idx)
        self._populated_tabs = set()
        self._render_tab_initial(idx)

    def _serve_tab_from_cache(self, idx):
        full = self._tab_cached_full.get(idx) or []
        self._tab_rows[idx] = list(full[:self._page_size])
        self._tab_cached_remainder[idx] = list(full[self._page_size:])
        self._tab_has_more[idx] = len(full) > self._page_size
        self._rebuild_bookings()

    def _apply_counts(self, counts):
        counts = counts or {}
        self._counts = {
            "pending": int(counts.get("pending", 0) or 0),
            "confirmed": int(counts.get("confirmed", 0) or 0),
            "all": int(counts.get("all", 0) or 0),
        }
        if hasattr(self, "_tabs"):
            self._tabs.setTabText(0, f"⏳ Pending Bookings ({self._counts['pending']})")
            self._tabs.setTabText(1, f"✅ Confirmed Bookings ({self._counts['confirmed']})")
            self._tabs.setTabText(2, f"📋 All Bookings ({self._counts['all']})")

    def _rebuild_bookings(self):
        # self._bookings is the union of rows loaded across all tabs so far;
        # single-row lookups and selection helpers still resolve any card that is
        # currently rendered. It is NOT the full dataset under pagination.
        seen = set()
        merged = []
        for i in (0, 1, 2):
            for b in self._tab_rows.get(i, []):
                rid = b.get("id")
                if rid in seen:
                    continue
                seen.add(rid)
                merged.append(b)
        self._bookings = merged

    def _reload_finished(self):
        # Called only when the full pipeline (fetch + render of the active tab)
        # has truly completed. Reset the in-flight guard and, if a reload was
        # requested mid-render, schedule exactly one more pass.
        self._reload_in_flight = False
        if getattr(self, "_reload_pending", False):
            self._reload_pending = False
            QTimer.singleShot(0, self.reload)

    def _on_bookings_error(self, err):
        self._refreshing = False
        if hasattr(self, "_loader"):
            self._loader.hide_overlay()
        self._reload_finished()
        print(f"[BookingPage] Background refresh error: {err}")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header Row
        header_row = QHBoxLayout()
        v = QVBoxLayout()
        v.setSpacing(4)
        title = QLabel("Orders & Bookings")
        title.setObjectName("pageTitle")
        sub = QLabel("Manage all catering reservations, pending approvals, and confirmed events.")
        sub.setObjectName("subtitle")
        v.addWidget(title)
        v.addWidget(sub)
        header_row.addLayout(v)
        header_row.addStretch()

        self.btn_new = QPushButton("  New Booking")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.setIcon(btn_icon_primary("plus"))
        self.btn_new.setIconSize(QSize(15, 15))
        self.btn_new.clicked.connect(self._open_modal)
        header_row.addWidget(self.btn_new)

        self.btn_multi_add = QPushButton("  + Quick Multi-Order")
        self.btn_multi_add.setObjectName("secondaryButton")
        self.btn_multi_add.setCursor(Qt.PointingHandCursor)
        self.btn_multi_add.clicked.connect(self._open_multi_add_dialog)
        header_row.addWidget(self.btn_multi_add)

        self.btn_import = QPushButton("  Import")
        self.btn_import.setObjectName("secondaryButton")
        self.btn_import.setIcon(btn_icon_secondary("export"))
        self.btn_import.setIconSize(QSize(15, 15))
        self.btn_import.clicked.connect(self._open_import_dialog)
        header_row.addWidget(self.btn_import)
        layout.addLayout(header_row)

        # Search and Global Filter Bar
        search_filter_row = QHBoxLayout()
        search_filter_row.setSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search bookings by client name, reference ID, date, or pax...")
        self._search_input.setFixedHeight(38)
        self._search_input.textChanged.connect(self.filter_search)
        search_filter_row.addWidget(self._search_input, 1)

        self._btn_filter = QPushButton("  Filter")
        self._btn_filter.setObjectName("secondaryButton")
        self._btn_filter.setIcon(btn_icon_secondary("filter"))
        self._btn_filter.setIconSize(QSize(14, 14))
        self._btn_filter.setFixedHeight(38)
        self._btn_filter.setCursor(Qt.PointingHandCursor)
        self._btn_filter.clicked.connect(self._open_filter)
        search_filter_row.addWidget(self._btn_filter)

        self._btn_export = QPushButton("  Export")
        self._btn_export.setObjectName("secondaryButton")
        self._btn_export.setIcon(btn_icon_secondary("export"))
        self._btn_export.setIconSize(QSize(14, 14))
        self._btn_export.setFixedHeight(38)
        self._btn_export.setCursor(Qt.PointingHandCursor)
        self._btn_export.clicked.connect(self._export_csv)
        search_filter_row.addWidget(self._btn_export)

        layout.addLayout(search_filter_row)

        # Server-side filter bar (date range / customer / occasion). These narrow
        # the ACTIVE tab's own status_filter further at the DB level; they are
        # ADDITIONAL to the client-side search box above and apply within
        # whichever tab is currently selected.
        server_filter_row = QHBoxLayout()
        server_filter_row.setSpacing(10)

        server_filter_row.addWidget(QLabel("From"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("MMM d, yyyy")
        self._date_from.setFixedHeight(38)
        self._date_from.setDate(QDate.fromString(self._filter_date_start, "yyyy-MM-dd"))
        self._date_from.dateChanged.connect(lambda _=None: self._on_server_filter_changed())
        server_filter_row.addWidget(self._date_from)

        server_filter_row.addWidget(QLabel("To"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("MMM d, yyyy")
        self._date_to.setFixedHeight(38)
        self._date_to.setDate(QDate.fromString(self._filter_date_end, "yyyy-MM-dd"))
        self._date_to.dateChanged.connect(lambda _=None: self._on_server_filter_changed())
        server_filter_row.addWidget(self._date_to)

        # Time-of-day filter, on top of the existing date range - lets the
        # user narrow bookings down to a specific event time slot (e.g. to
        # check what else is already scheduled around a given time), which
        # the date range filter alone couldn't do.
        server_filter_row.addWidget(QLabel("Time"))
        self._time_from = QTimeEdit()
        self._time_from.setDisplayFormat("h:mm AP")
        self._time_from.setFixedHeight(38)
        self._time_from.setTime(QTime(0, 0))
        self._time_from.timeChanged.connect(lambda _=None: self._on_server_filter_changed())
        server_filter_row.addWidget(self._time_from)

        server_filter_row.addWidget(QLabel("to"))
        self._time_to = QTimeEdit()
        self._time_to.setDisplayFormat("h:mm AP")
        self._time_to.setFixedHeight(38)
        self._time_to.setTime(QTime(23, 59))
        self._time_to.timeChanged.connect(lambda _=None: self._on_server_filter_changed())
        server_filter_row.addWidget(self._time_to)

        server_filter_row.addWidget(QLabel("Customer"))
        self._customer_filter = QComboBox()
        self._customer_filter.setEditable(True)
        self._customer_filter.setFixedHeight(38)
        self._customer_filter.setMinimumWidth(180)
        self._customer_filter.addItem("All Customers")
        try:
            for _name in repo.get_customer_names():
                self._customer_filter.addItem(_name)
        except Exception as _exc:
            print(f"[BookingPage] customer names load failed: {_exc}")
        self._customer_filter.setCurrentIndex(0)
        from utils.searchable_combo import make_searchable
        make_searchable(self._customer_filter)
        self._customer_filter.currentTextChanged.connect(lambda _=None: self._on_server_filter_changed())
        server_filter_row.addWidget(self._customer_filter)

        server_filter_row.addWidget(QLabel("Occasion"))
        self._event_filter = QComboBox()
        self._event_filter.setFixedHeight(38)
        self._event_filter.setMinimumWidth(150)
        self._event_filter.addItem("All Occasions")
        try:
            for _occ in repo.get_all_occasions():
                self._event_filter.addItem(_occ)
        except Exception as _exc:
            print(f"[BookingPage] occasions load failed: {_exc}")
        self._event_filter.setCurrentIndex(0)
        self._event_filter.currentTextChanged.connect(lambda _=None: self._on_server_filter_changed())
        server_filter_row.addWidget(self._event_filter)

        self._btn_reset_filters = QPushButton("Reset")
        self._btn_reset_filters.setObjectName("secondaryButton")
        self._btn_reset_filters.setFixedHeight(38)
        self._btn_reset_filters.setCursor(Qt.PointingHandCursor)
        self._btn_reset_filters.clicked.connect(self._reset_server_filters)
        server_filter_row.addWidget(self._btn_reset_filters)

        server_filter_row.addStretch()
        layout.addLayout(server_filter_row)

        # 3-Tab Booking Matrix
        self._tabs = QTabWidget()
        self._tabs.setObjectName("bookingTabs")

        # Tab 1: Pending Bookings
        p_page, self._pending_cards_layout, self._pending_tb = self._create_booking_tab("PENDING")
        self._tabs.addTab(p_page, "⏳ Pending Bookings (0)")

        # Tab 2: Confirmed Bookings
        c_page, self._confirmed_cards_layout, self._confirmed_tb = self._create_booking_tab("CONFIRMED")
        self._tabs.addTab(c_page, "✅ Confirmed Bookings (0)")

        # Tab 3: All Bookings
        a_page, self._all_cards_layout, self._all_tb = self._create_booking_tab("ALL")
        self._tabs.addTab(a_page, "📋 All Bookings (0)")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs, 1)
        self._loader = LoadingOverlay(self, "Loading bookings & reservations...")
        self._populate_table()

    def _create_booking_tab(self, tab_type: str):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(12)

        # Tab Toolbar
        tb_lay = QHBoxLayout()
        tb_lay.setContentsMargins(4, 0, 4, 0)
        tb_lay.setSpacing(12)

        cb_select_all = QCheckBox("Select All")
        cb_select_all.setStyleSheet("QCheckBox { font-weight: 600; font-size: 13px; color: #9CA3AF; }")
        tb_lay.addWidget(cb_select_all)

        lbl_selected_count = QLabel("0 selected")
        lbl_selected_count.setStyleSheet("font-size: 12px; color: #6B7280; font-weight: 600;")
        tb_lay.addWidget(lbl_selected_count)

        tb_lay.addStretch()

        btn_batch_approve = None
        btn_batch_cancel = None

        if tab_type == "PENDING":
            btn_batch_approve = QPushButton("  Batch Confirm")
            btn_batch_approve.setObjectName("secondaryButton")
            btn_batch_approve.setIcon(get_icon("check", color="#22C55E", size=QSize(13, 13)))
            btn_batch_approve.setIconSize(QSize(13, 13))
            btn_batch_approve.setCursor(Qt.PointingHandCursor)
            btn_batch_approve.setEnabled(False)
            btn_batch_approve.setStyleSheet("QPushButton { color: #22C55E; font-weight: 700; }")
            btn_batch_approve.clicked.connect(self._batch_approve_bookings)
            tb_lay.addWidget(btn_batch_approve)

            btn_batch_cancel = QPushButton("  ✕ Batch Cancel")
            btn_batch_cancel.setObjectName("secondaryButton")
            btn_batch_cancel.setCursor(Qt.PointingHandCursor)
            btn_batch_cancel.setEnabled(False)
            btn_batch_cancel.setStyleSheet("QPushButton { color: #EF4444; font-weight: 700; }")
            btn_batch_cancel.clicked.connect(self._batch_cancel_bookings)
            tb_lay.addWidget(btn_batch_cancel)

        btn_delete_selected = QPushButton("  Delete Selected")
        btn_delete_selected.setIcon(btn_icon_red("trash"))
        btn_delete_selected.setIconSize(QSize(13, 13))
        btn_delete_selected.setCursor(Qt.PointingHandCursor)
        btn_delete_selected.setEnabled(False)
        btn_delete_selected.setStyleSheet(
            "QPushButton { background: rgba(225,29,72,0.15); border: 1px solid rgba(225,29,72,0.3); color: #E11D48; border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(225,29,72,0.25); border-color: #E11D48; }"
            "QPushButton:disabled { opacity: 0.35; background: rgba(255,255,255,0.04); border-color: transparent; color: #6B7280; }"
        )
        btn_delete_selected.clicked.connect(self._delete_selected_bookings)
        tb_lay.addWidget(btn_delete_selected)

        btn_print_selected = QPushButton("  Print Selected")
        btn_print_selected.setIcon(get_icon("export", color="#38BDF8", size=QSize(13, 13)))
        btn_print_selected.setIconSize(QSize(13, 13))
        btn_print_selected.setCursor(Qt.PointingHandCursor)
        btn_print_selected.setEnabled(False)
        btn_print_selected.setStyleSheet(
            "QPushButton { background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.3); color: #38BDF8; border-radius: 8px; padding: 6px 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background: rgba(56,189,248,0.25); border-color: #38BDF8; }"
            "QPushButton:disabled { opacity: 0.35; background: rgba(255,255,255,0.04); border-color: transparent; color: #6B7280; }"
        )
        btn_print_selected.clicked.connect(self._print_selected_orders)
        tb_lay.addWidget(btn_print_selected)

        lay.addLayout(tb_lay)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        lay.addWidget(div)

        # Scroll Area for Cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background: transparent;")

        cards_container = QWidget()
        cards_container.setStyleSheet("background: transparent;")
        cards_layout = QVBoxLayout(cards_container)
        cards_layout.setContentsMargins(0, 0, 10, 0)
        cards_layout.setSpacing(12)

        scroll_area.setWidget(cards_container)
        lay.addWidget(scroll_area, 1)

        # Wire up per-tab infinite scroll: loading the next page for THIS tab
        # specifically when the user nears the bottom of its scroll area.
        tab_idx = {"PENDING": 0, "CONFIRMED": 1, "ALL": 2}.get(tab_type, 2)
        self._tab_layouts[tab_idx] = cards_layout
        self._scroll_areas[tab_idx] = scroll_area
        scroll_area.verticalScrollBar().valueChanged.connect(
            lambda v, i=tab_idx: self._on_tab_scroll(i, v)
        )

        tb_bundle = {
            "select_all": cb_select_all,
            "selected_lbl": lbl_selected_count,
            "batch_approve": btn_batch_approve,
            "batch_cancel": btn_batch_cancel,
            "delete_selected": btn_delete_selected,
            "print_selected": btn_print_selected,
            "container": cards_container,
            "tab_type": tab_type
        }

        cb_select_all.stateChanged.connect(lambda state, t=tab_type: self._toggle_select_tab(t, state))

        return page, cards_layout, tb_bundle

    def _on_tab_changed(self, index: int):
        # Lazily load a tab's first page the first time it becomes active.
        if index not in getattr(self, "_populated_tabs", set()) and not self._tab_rows.get(index):
            self._ensure_tab_loaded(index)
        else:
            self._populate_active_tab()
        self._update_selection_ui()

    def _ensure_tab_loaded(self, idx: int):
        # Serve the tab's first page from the pre-loaded memory cache if we have
        # it (zero DB round-trip); otherwise fetch page 0 from the DB. Either way,
        # show the loader while this tab's cards batch-render - even the cached
        # path can take a visible moment to build widgets for a big tab, and with
        # no indicator it looked like tab switching just did nothing.
        if self._tab_cached_full.get(idx) is not None:
            if hasattr(self, "_loader"):
                self._loader.show_overlay("Loading bookings & reservations...")
            self._serve_tab_from_cache(idx)
            self._render_tab_initial(idx)
            return
        if self._tab_loading_more.get(idx):
            return
        self._tab_loading_more[idx] = True
        if hasattr(self, "_loader"):
            self._loader.show_overlay("Loading bookings & reservations...")
        run_async(
            self, repo.get_bookings_page,
            lambda rows, i=idx: self._on_tab_first_page(i, rows),
            self._on_bookings_error,
            self._tab_status.get(idx), 0, self._page_size, *self._current_filter_args(),
        )

    def _on_tab_first_page(self, idx: int, rows):
        from shiboken6 import isValid
        if not isValid(self):
            return
        rows = rows or []
        self._tab_loading_more[idx] = False
        self._tab_rows[idx] = list(rows)
        self._tab_has_more[idx] = len(rows) >= self._page_size
        self._rebuild_bookings()
        self._render_tab_initial(idx)

    def _render_tab_initial(self, idx: int):
        from utils.auth import SessionManager
        can_edit = SessionManager.has_permission("bookings", "edit")
        can_delete = SessionManager.has_permission("bookings", "delete")
        layout = self._tab_layouts.get(idx)
        rows = self._rows_for_tab(idx)
        empty_msg = self._tab_empty_msg(idx)
        if not hasattr(self, "_tab_data"):
            self._tab_data = {}
        self._tab_data[idx] = (layout, rows, empty_msg)
        if not hasattr(self, "_populated_tabs"):
            self._populated_tabs = set()
        self._populate_card_layout(layout, rows, empty_msg, can_edit, can_delete)
        self._populated_tabs.add(idx)
        self._update_selection_ui()

    def _tab_empty_msg(self, idx: int) -> str:
        return {
            0: "No pending bookings found.",
            1: "No confirmed bookings found.",
            2: "No bookings found.",
        }.get(idx, "No bookings found.")

    def _rows_for_tab(self, idx: int):
        # Enforce the tab's status bucket (so a row whose status changed via a
        # mutation - e.g. Pending -> Confirmed - drops out of the wrong tab on
        # re-render) then apply the client-side search/filter.
        rows = self._tab_rows.get(idx, [])
        statuses = self._tab_status.get(idx)
        if statuses:
            rows = [b for b in rows if b.get("status") in statuses]
        return self._filter_rows(rows)

    def _filter_rows(self, rows):
        # Client-side status + search filtering over the rows already loaded for a
        # tab. KNOWN LIMITATION: search/filter only sees loaded (scrolled-to)
        # rows, not the full DB set - full DB-side search is a later follow-up.
        f = self._active_filter
        if f and f != "All":
            if isinstance(f, list):
                rows = [b for b in rows if b.get("status") in f]
            else:
                rows = [b for b in rows if b.get("status") == f]

        q = (getattr(self, "_search_query", "") or "").strip().lower()
        if q:
            def _match(b):
                terms = [
                    str(b.get("name", "")),
                    str(b.get("id", "")),
                    str(b.get("date", "")),
                    str(b.get("pax", "")),
                    str(b.get("total", "")),
                    str(b.get("occasion", "")),
                    str(b.get("venue", "")),
                    str(b.get("notes", "")),
                    str(b.get("status", "")),
                    str(b.get("payment_mode", "")),
                    str(b.get("contact", "")),
                ]
                return q in " ".join(terms).lower()
            rows = [b for b in rows if _match(b)]
        return rows

    def _on_tab_scroll(self, idx: int, value: int):
        sa = self._scroll_areas.get(idx)
        if not sa:
            return
        sb = sa.verticalScrollBar()
        if sb.maximum() - value < 200:
            self._load_more_tab(idx)

    def _load_more_tab(self, idx: int):
        if self._tab_loading_more.get(idx) or not self._tab_has_more.get(idx):
            return
        # Don't start appending to this tab's layout while its own initial
        # batch-render chain is still actively mutating it - scrolling right
        # after switching tabs used to hit this and crash (two render chains
        # touching the same layout at once). Wait for it to finish first.
        if self._tab_rendering.get(idx):
            return
        # While a client-side search/filter is active we page through the loaded
        # set only; don't fetch further DB pages that the filter would hide.
        if (getattr(self, "_search_query", "") or "").strip():
            return
        self._tab_loading_more[idx] = True
        self._show_tab_loading_indicator(idx)
        remainder = self._tab_cached_remainder.get(idx)
        if remainder is not None:
            more = remainder[:self._page_size]
            self._tab_cached_remainder[idx] = remainder[self._page_size:]
            if not self._tab_cached_remainder[idx]:
                self._tab_has_more[idx] = False
            QTimer.singleShot(0, lambda i=idx, m=more: self._on_tab_more_loaded(i, m))
            return
        offset = len(self._tab_rows.get(idx, []))
        run_async(
            self, repo.get_bookings_page,
            lambda rows, i=idx: self._on_tab_more_loaded(i, rows),
            lambda err, i=idx: (self._hide_tab_loading_indicator(i), self._tab_loading_more.__setitem__(i, False), self._on_bookings_error(err)),
            self._tab_status.get(idx), offset, self._page_size, *self._current_filter_args(),
        )

    def _show_tab_loading_indicator(self, idx: int):
        layout = self._tab_layouts.get(idx)
        if not layout or self._tab_loading_label.get(idx) is not None:
            return
        lbl = QLabel("Loading more bookings...")
        lbl.setObjectName("subtitle")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 12px; color: #64748B; padding: 10px;")
        # Insert just before the trailing stretch (never remove/re-add it -
        # see _insert_card_before_stretch).
        self._insert_card_before_stretch(layout, lbl)
        self._tab_loading_label[idx] = lbl

    def _hide_tab_loading_indicator(self, idx: int):
        lbl = self._tab_loading_label.get(idx)
        if lbl is None:
            return
        layout = self._tab_layouts.get(idx)
        if layout is not None:
            layout.removeWidget(lbl)
        lbl.deleteLater()
        self._tab_loading_label[idx] = None

    def _on_tab_more_loaded(self, idx: int, rows):
        self._hide_tab_loading_indicator(idx)
        from shiboken6 import isValid
        if not isValid(self):
            return
        new_rows = rows or []
        if self._tab_cached_remainder.get(idx) is None and len(new_rows) < self._page_size:
            self._tab_has_more[idx] = False
        if not new_rows:
            self._tab_loading_more[idx] = False
            return
        self._tab_rows[idx].extend(new_rows)
        self._rebuild_bookings()
        self._append_tab_cards(idx, new_rows)
        self._tab_loading_more[idx] = False

    def _append_tab_cards(self, idx: int, new_rows):
        layout = self._tab_layouts.get(idx)
        if not layout:
            return
        # NOTE: we deliberately never remove/re-add the trailing stretch spacer
        # (previously done via layout.takeAt() on every append) - repeatedly
        # taking a QLayoutItem out of a layout and discarding it was the
        # suspected cause of a native Qt memory-reuse crash. _render_next_batch
        # inserts new cards just BEFORE the permanent stretch instead.
        from utils.auth import SessionManager
        can_edit = SessionManager.has_permission("bookings", "edit")
        can_delete = SessionManager.has_permission("bookings", "delete")
        self._render_token = getattr(self, "_render_token", 0) + 1
        token = self._render_token
        # Keep _tab_data row list in sync so re-renders (mutations) include these.
        entry = self._tab_data.get(idx) if hasattr(self, "_tab_data") else None
        if entry:
            self._tab_data[idx] = (entry[0], self._rows_for_tab(idx), entry[2])
        self._tab_rendering[idx] = True
        self._render_next_batch(layout, list(new_rows), token, can_edit, can_delete, tab_idx=idx)

    def _visible_bookings(self):
        rows = self._bookings
        f = self._active_filter
        if f and f != "All":
            if isinstance(f, list):
                rows = [b for b in rows if b.get("status") in f]
            else:
                rows = [b for b in rows if b.get("status") == f]

        q = (getattr(self, "_search_query", "") or "").strip().lower()
        if q:
            def _match(b):
                terms = [
                    str(b.get("name", "")),
                    str(b.get("id", "")),
                    str(b.get("date", "")),
                    str(b.get("pax", "")),
                    str(b.get("total", "")),
                    str(b.get("occasion", "")),
                    str(b.get("venue", "")),
                    str(b.get("notes", "")),
                    str(b.get("status", "")),
                    str(b.get("payment_mode", "")),
                    str(b.get("contact", "")),
                ]
                combined = " ".join(terms).lower()
                return q in combined

            rows = [b for b in rows if _match(b)]
        return rows

    def _populate_table(self, data=None):
        # Re-render the currently-loaded rows for each tab (used after mutations
        # like approve/cancel/delete/save and for client-side search/filter). The
        # per-tab paginated self._tab_rows are the source of truth for what's
        # loaded; tab title counts come from the DB aggregate (self._counts),
        # never from len() of the loaded slice.
        self.setUpdatesEnabled(False)
        try:
            self._card_checkboxes.clear()

            from utils.auth import SessionManager
            can_edit = SessionManager.has_permission("bookings", "edit")
            can_delete = SessionManager.has_permission("bookings", "delete")

            self._tab_data = {
                0: (self._pending_cards_layout, self._rows_for_tab(0), "No pending bookings found."),
                1: (self._confirmed_cards_layout, self._rows_for_tab(1), "No confirmed bookings found."),
                2: (self._all_cards_layout, self._rows_for_tab(2), "No bookings found."),
            }

            if hasattr(self, "_tabs"):
                self._tabs.setTabText(0, f"⏳ Pending Bookings ({self._counts.get('pending', 0)})")
                self._tabs.setTabText(1, f"✅ Confirmed Bookings ({self._counts.get('confirmed', 0)})")
                self._tabs.setTabText(2, f"📋 All Bookings ({self._counts.get('all', 0)})")

            # Reset populated state tracking and populate the active tab
            self._populated_tabs = set()
            self._populate_active_tab(can_edit, can_delete)
            self._update_selection_ui()
        finally:
            self.setUpdatesEnabled(True)

    def _populate_active_tab(self, can_edit=None, can_delete=None):
        if not hasattr(self, "_tabs") or not hasattr(self, "_tab_data"):
            return
        cur_idx = self._tabs.currentIndex()
        if not hasattr(self, "_populated_tabs"):
            self._populated_tabs = set()
        if cur_idx in self._populated_tabs:
            return
        if can_edit is None or can_delete is None:
            from utils.auth import SessionManager
            can_edit = SessionManager.has_permission("bookings", "edit")
            can_delete = SessionManager.has_permission("bookings", "delete")

        entry = self._tab_data.get(cur_idx)
        if entry:
            lay, rows, empty_msg = entry
            self._populate_card_layout(lay, rows, empty_msg, can_edit, can_delete, tab_idx=cur_idx)
            self._populated_tabs.add(cur_idx)

    def _populate_card_layout(self, layout: QVBoxLayout, rows: list[dict], empty_msg: str, can_edit: bool = True, can_delete: bool = True, tab_idx: int = None):
        if not layout:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item:
                w = item.widget()
                if w:
                    w.hide()
                    w.deleteLater()

        # Bump the render token so any in-flight batches from a previous
        # populate (rapid tab switches / refreshes) cancel themselves.
        self._render_token = getattr(self, "_render_token", 0) + 1
        token = self._render_token

        if not rows:
            msg = "Loading reservations..." if getattr(self, "_refreshing", False) and not getattr(self, "_has_loaded_once", False) else empty_msg
            empty_lbl = QLabel(msg)
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("font-size: 13px; color: #64748B; padding: 24px;")
            layout.addWidget(empty_lbl)
            layout.addStretch()
            if tab_idx is not None:
                self._tab_rendering[tab_idx] = False
            # No batches will run for this (active) tab - the render pipeline is
            # already complete, so hide the loader and settle any pending reload.
            if getattr(self, "_loader", None):
                self._loader.hide_overlay()
            self._reload_finished()
        else:
            if tab_idx is not None:
                # Mark this tab's list as "actively being built" so a scroll-
                # triggered load-more can't start appending to the SAME layout
                # while this initial batch chain is still mutating it - doing so
                # corrupted the shared render token/layout state and crashed
                # with a PySide QWidgetItem error when the user scrolled right
                # after switching tabs, before the tab finished rendering.
                self._tab_rendering[tab_idx] = True
            # Render incrementally in batches so widget construction/layout
            # never blocks the main thread as one giant loop (UI freeze fix).
            self._render_next_batch(layout, list(rows), token, can_edit, can_delete, tab_idx=tab_idx)

    @staticmethod
    def _insert_card_before_stretch(layout, card):
        # Insert just before a trailing stretch spacer if one exists, rather
        # than ever taking the spacer out of the layout - repeatedly
        # take()-ing and discarding a QLayoutItem was the suspected trigger
        # for a native Qt memory-reuse crash under heavy append/indicator churn.
        count = layout.count()
        if count > 0 and layout.itemAt(count - 1).widget() is None:
            layout.insertWidget(count - 1, card)
        else:
            layout.addWidget(card)

    def _render_next_batch(self, layout, queue, token, can_edit, can_delete, batch_size=15, tab_idx=None):
        # Abandon if a newer populate started (stale in-flight batch). The
        # newer chain owns _tab_rendering[tab_idx] now, so don't touch it here.
        if token != getattr(self, "_render_token", 0):
            return
        if not layout or queue is None:
            return
        container = layout.parentWidget()
        if container is not None:
            container.setUpdatesEnabled(False)
        try:
            count = 0
            while queue and count < batch_size:
                b = queue.pop(0)
                card = self._create_booking_card(b, can_edit, can_delete)
                self._insert_card_before_stretch(layout, card)
                count += 1
        finally:
            if container is not None:
                container.setUpdatesEnabled(True)

        if getattr(self, "_loader", None) and self._loader.isVisible():
            self._loader.spin_step()

        if queue:
            # Yield to the Qt event loop so paint/input events process
            # between batches, then continue with the rest.
            QTimer.singleShot(0, lambda: self._render_next_batch(layout, queue, token, can_edit, can_delete, batch_size, tab_idx))
        else:
            # Add the trailing stretch only if one isn't already there (a
            # previous append cycle may have left one in place - we never
            # remove it, see _insert_card_before_stretch).
            count2 = layout.count()
            if count2 == 0 or layout.itemAt(count2 - 1).widget() is not None:
                layout.addStretch()
            if tab_idx is not None:
                self._tab_rendering[tab_idx] = False
            # Only hide the loader once this tab truly has nothing left to
            # load in the background - otherwise it disappears after page 0
            # while auto-continue is still silently fetching later pages.
            tab_has_more = self._tab_has_more.get(tab_idx) if tab_idx is not None else False
            if getattr(self, "_loader", None) and not tab_has_more:
                self._loader.hide_overlay()
            self._reload_finished()
            # Keep quietly loading the next page for THIS tab in the
            # background instead of waiting for the user to scroll - each
            # page still fetches on a background thread and renders in small
            # yielded batches, so this never blocks the UI; the short delay
            # just avoids competing with whatever the user is doing right
            # after a page finishes. Scoped to the tab that just finished so
            # the other tabs' chains are untouched.
            if tab_idx is not None and self._tab_has_more.get(tab_idx) and not self._tab_loading_more.get(tab_idx):
                QTimer.singleShot(150, lambda i=tab_idx: self._load_more_tab(i))


    def _create_booking_card(self, b: dict, can_edit: bool = True, can_delete: bool = True) -> QFrame:
        bref = b["id"]
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 14, 18, 14)
        lay.setSpacing(14)

        # Col 0: Checkbox
        cb = QCheckBox()
        cb.setChecked(bref in self._selected_refs)
        cb.stateChanged.connect(lambda state, ref=bref: self._on_card_checked(ref, state))
        self._card_checkboxes[bref] = cb
        lay.addWidget(cb, alignment=Qt.AlignVCenter)

        # Col 1: Date & Reference ID
        c1 = QVBoxLayout()
        c1.setSpacing(2)
        ref_lbl = QLabel(b["id"])
        ref_lbl.setStyleSheet("font-weight: 800; font-size: 13px; color: #E11D48;")
        date_lbl = QLabel(b["date"])
        date_lbl.setObjectName("subtitle")
        c1.addWidget(ref_lbl)
        c1.addWidget(date_lbl)
        lay.addLayout(c1, 1)

        # Col 2: Client Name & Pax
        c2 = QVBoxLayout()
        c2.setSpacing(2)
        name_lbl = QLabel(b["name"])
        name_lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
        pax_lbl = QLabel(f"{b['pax']} pax")
        pax_lbl.setObjectName("subtitle")
        c2.addWidget(name_lbl)
        c2.addWidget(pax_lbl)
        lay.addLayout(c2, 2)

        # Col 3: Total Amount
        c3 = QVBoxLayout()
        c3.setSpacing(2)
        tot_title = QLabel("TOTAL")
        tot_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #6B7280; letter-spacing: 0.5px;")
        tot_val = QLabel(str(b["total"]))
        tot_val.setStyleSheet("font-weight: 800; font-size: 14px; color: #F59E0B;")
        c3.addWidget(tot_title)
        c3.addWidget(tot_val)
        lay.addLayout(c3, 1)

        # Col 3.5: Event Time
        c_time = QVBoxLayout()
        c_time.setSpacing(2)
        time_title = QLabel("EVENT TIME")
        time_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #6B7280; letter-spacing: 0.5px;")
        t_val = repo.format_time_ampm(b.get("event_time") or b.get("time") or "6:00 PM")
        time_val = QLabel(t_val)
        time_val.setStyleSheet("font-weight: 700; font-size: 13px; color: #38BDF8;")
        c_time.addWidget(time_title)
        c_time.addWidget(time_val)
        lay.addLayout(c_time, 1)

        # Col 4: Status Badge & Reason/Approvals
        c4 = QVBoxLayout()
        c4.setSpacing(4)
        c4.setAlignment(Qt.AlignCenter)
        c4.addWidget(_status_badge(b["status"]), alignment=Qt.AlignLeft)
        if b["status"] == "CANCELLED" and b.get("cancellation_reason"):
            reason_lbl = QLabel(b["cancellation_reason"])
            reason_lbl.setStyleSheet("color:#DC2626;font-size:10px;font-style:italic;")
            reason_lbl.setWordWrap(True)
            c4.addWidget(reason_lbl)
        elif b["status"] == "PENDING" and can_edit:
            bref = b["id"]
            c4.addWidget(_action_buttons(
                b["status"],
                on_approve=lambda _, r=bref: self._approve_booking(r),
                on_decline=lambda _, r=bref: self._decline_booking(r),
                can_edit=can_edit
            ))
        lay.addLayout(c4, 2)

        # Col 5: Actions (Edit, Delete, Confirmation, Color)
        actions_w = QFrame(card)
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        edit_btn = QPushButton(parent=actions_w)
        edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(13, 13)))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("background:transparent;border:none;")
        edit_btn.setCursor(Qt.PointingHandCursor if can_edit else Qt.ForbiddenCursor)
        edit_btn.setToolTip("Edit booking / order details" if can_edit else "Permission required to edit")
        edit_btn.setEnabled(can_edit and b.get("status") != "CANCELLED")
        if b.get("status") == "CANCELLED":
            edit_btn.setStyleSheet("background:transparent;border:none;opacity:0.3;")
        edit_btn.clicked.connect(lambda _, r=bref: self._edit_booking(r))

        charges_btn = QPushButton(parent=actions_w)
        charges_btn.setIcon(get_icon("plus", color="#9CA3AF", size=QSize(13, 13)))
        charges_btn.setIconSize(QSize(13, 13))
        charges_btn.setFixedSize(30, 30)
        charges_btn.setStyleSheet("background:transparent;border:none;")
        charges_btn.setCursor(Qt.PointingHandCursor if can_edit else Qt.ForbiddenCursor)
        charges_btn.setToolTip("Additional Charges / Additional Items" if can_edit else "Permission required to edit")
        charges_btn.setEnabled(can_edit and b.get("status") != "CANCELLED")
        if b.get("status") == "CANCELLED":
            charges_btn.setStyleSheet("background:transparent;border:none;opacity:0.3;")
        charges_btn.clicked.connect(lambda _, r=bref: self._open_additional_charges(r))

        color_btn = QPushButton(parent=actions_w)
        color_btn.setIcon(get_icon("palette", color="#9CA3AF", size=QSize(13, 13)))
        color_btn.setIconSize(QSize(13, 13))
        color_btn.setFixedSize(30, 30)
        color_btn.setStyleSheet("background:transparent;border:none;")
        color_btn.setCursor(Qt.PointingHandCursor if can_edit else Qt.ForbiddenCursor)
        color_btn.setToolTip("Change Color Motif" if can_edit else "Permission required to edit")
        color_btn.setEnabled(can_edit and b.get("status") != "CANCELLED")
        if b.get("status") == "CANCELLED":
            color_btn.setStyleSheet("background:transparent;border:none;opacity:0.3;")
        color_btn.clicked.connect(lambda _, r=bref: self._change_booking_color(r))

        del_btn = QPushButton(parent=actions_w)
        del_btn.setIcon(btn_icon_red("trash") if can_delete else get_icon("trash", color="#4B5563", size=QSize(13, 13)))
        del_btn.setIconSize(QSize(13, 13))
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("border:none;background:transparent;")
        del_btn.setCursor(Qt.PointingHandCursor if can_delete else Qt.ForbiddenCursor)
        del_btn.setEnabled(can_delete)
        del_btn.setToolTip("Delete booking" if can_delete else "Permission required to delete")
        del_btn.clicked.connect(lambda _, r=bref: self._delete_booking(r))

        confirm_btn = QPushButton(parent=actions_w)
        confirm_btn.setIcon(get_icon("bell", color="#9CA3AF", size=QSize(13, 13)))
        confirm_btn.setIconSize(QSize(13, 13))
        confirm_btn.setFixedSize(30, 30)
        confirm_btn.setStyleSheet("background:transparent;border:none;")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setToolTip("Send Confirmation Email")
        confirm_btn.setEnabled(b["status"] == "CONFIRMED")
        if b["status"] != "CONFIRMED":
            confirm_btn.setStyleSheet("background:transparent;border:none;opacity:0.3;")
        confirm_btn.clicked.connect(lambda _, r=bref: self._send_confirmation(r))

        print_btn = QPushButton(parent=actions_w)
        print_btn.setIcon(get_icon("printer", color="#9CA3AF", size=QSize(13, 13)))
        print_btn.setIconSize(QSize(13, 13))
        print_btn.setFixedSize(30, 30)
        print_btn.setStyleSheet("background:transparent;border:none;")
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.setToolTip("Export / Print Order Slip (Kitchen & Event BEO)")
        print_btn.clicked.connect(lambda _, r=bref: self._print_order_slip(r))

        actions_l.addWidget(print_btn)
        actions_l.addWidget(edit_btn)
        actions_l.addWidget(charges_btn)
        actions_l.addWidget(color_btn)
        actions_l.addWidget(del_btn)
        actions_l.addWidget(confirm_btn)

        if not can_edit:
            edit_btn.hide()
            charges_btn.hide()
            color_btn.hide()
            confirm_btn.hide()
        if not can_delete:
            del_btn.hide()
        # Print/export must stay visible even for view-only access - never hide
        # the whole actions row, or the print icon disappears along with it.

        lay.addWidget(actions_w)

        return card

    def _print_order_slip(self, ref: str):
        from components.order_print_dialog import OrderPrintDialog
        b = next((x for x in self._bookings if x.get("id") == ref), None)
        target = b.get("db_id") if (b and b.get("db_id")) else ref
        dlg = OrderPrintDialog(target, parent=self)
        dlg.exec()

    def _print_selected_orders(self):
        if not self._selected_refs:
            return
        from components.order_print_dialog import OrderPrintDialog
        targets = []
        for ref in self._selected_refs:
            b = next((x for x in self._bookings if x.get("id") == ref), None)
            targets.append(b.get("db_id") if (b and b.get("db_id")) else ref)
        dlg = OrderPrintDialog(targets, parent=self)
        dlg.exec()

    def _change_booking_color(self, ref: str):
        from utils.auth import SessionManager
        if not SessionManager.has_permission("bookings", "edit"):
            return
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b:
            return
        db_id = b.get("db_id")

        from components.color_picker_widget import ColorThemeSelector
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Color Motif")
        dlg.setMinimumWidth(480)
        dlg.setModal(True)
        dlg_lay = QVBoxLayout(dlg)
        dlg_lay.setContentsMargins(24, 22, 24, 22)
        dlg_lay.setSpacing(14)

        head = QLabel(f"🎨  Select Color Motif for <b>{b.get('name', ref)}</b>")
        head.setStyleSheet("font-size: 13.5px; font-weight: 600;")
        dlg_lay.addWidget(head)

        cur_c = str(b.get("color_theme") or b.get("color") or "#2563EB")
        picker = ColorThemeSelector(initial_color=cur_c)
        dlg_lay.addWidget(picker)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(dlg.reject)
        btn_save = QPushButton("Save Motif")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(dlg.accept)
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        dlg_lay.addLayout(btn_box)

        if dlg.exec() == QDialog.Accepted:
            new_col = picker.get_color()
            if db_id:
                repo.update_booking_color_theme(db_id, new_col)
            b["color_theme"] = new_col
            b["color"] = new_col
            self._populate_table()
            app_events().booking_updated.emit()
            app_events().data_changed.emit()
            success(self, message=f"Color motif updated for {b.get('name', ref)}!")

    def _approve_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b:
            return

        db_id = b.get("db_id")
        detail = repo.get_booking_detail(db_id) if db_id else b
        if not detail:
            detail = b

        from components.confirm_booking_dialog import ConfirmBookingDialog, _parse_amount
        from datetime import date as _d

        dlg = ConfirmBookingDialog(detail, parent=self)
        if not dlg.exec():
            return

        try:
            pay_amt = dlg.get_payment_amount()
            is_auto_pay = dlg.is_auto_pay_checked()
            pay_method = dlg.get_payment_method()
            remarks = dlg.get_payment_remarks()

            tot_val = _parse_amount(detail.get("total") or detail.get("total_amount") or b.get("total", 0.0))
            paid_val = _parse_amount(detail.get("amount_paid") or detail.get("down_payment") or 0.0)
            rem = max(0.0, tot_val - paid_val)

            if db_id:
                if pay_amt > 0:
                    try:
                        repo.pay_invoice(db_id, payment_amount=pay_amt, payment_date=_d.today(), method=pay_method, note=remarks)
                    except Exception as p_err:
                        print(f"[booking] pay_invoice error: {p_err}")
                
                # Explicitly guarantee booking status is persisted as CONFIRMED in database
                color_theme = dlg.get_color_theme()
                repo.update_booking_status(db_id, "CONFIRMED", color_theme=color_theme)
                if color_theme:
                    repo.update_booking_color_theme(db_id, color_theme)

                try:
                    if detail.get("customer_id"):
                        repo.recalculate_loyalty(detail["customer_id"])
                except Exception:
                    pass

            b["status"] = "CONFIRMED"
            self._populate_table()
            if pay_amt >= rem and rem > 0:
                msg = f"Order {b['id']} confirmed & marked as FULLY PAID (₱{tot_val:,.2f})!"
            elif pay_amt > 0:
                msg = f"Order {b['id']} confirmed & payment of ₱{pay_amt:,.2f} recorded!"
            else:
                msg = f"Order {b['id']} confirmed successfully!"
            success(self, message=msg)
            repo.write_audit_log(get_actor(), "APPROVE", "bookings", db_id, None, {"status": "CONFIRMED", "amount": pay_amt, "customer": b.get("name")})

            try:
                repo.push_notification(
                    "success",
                    "Booking Confirmed",
                    f"Booking for {b.get('name', '')} on {b.get('date', '')} has been confirmed.",
                    "#22C55E",
                )
            except Exception:
                pass

            if db_id:
                self._send_confirmation_auto(b)
            app_events().booking_updated.emit()
            app_events().booking_saved.emit()
            app_events().data_changed.emit()
        except Exception as exc:
            QMessageBox.warning(self, "Cannot Approve", str(exc))

    def _decline_booking(self, ref):
        b = next((x for x in self._bookings if x.get("id") == ref), None)
        if not b:
            for rlist in getattr(self, "_tab_rows", {}).values():
                b = next((x for x in rlist if x.get("id") == ref), None)
                if b:
                    break
        if not b or b.get("status") != "PENDING":
            return
        reason, ok = QInputDialog.getText(
            self, "Cancellation Reason",
            f"Enter reason for declining booking for '{b.get('name', 'this customer')}' (optional):"
        )
        if not ok:
            return
        if not confirm(self, title="Decline Booking",
                       message=f"Decline booking for '{b.get('name', 'this customer')}'? This will mark it as Cancelled.",
                       confirm_label="Decline", danger=True):
            return
        b["status"] = "CANCELLED"
        if b.get("db_id"):
            repo.update_booking_status(b["db_id"], "CANCELLED", reason.strip() or None)
            repo.write_audit_log(get_actor(), "CANCEL", "bookings", b["db_id"], None, {"status": "CANCELLED", "reason": reason.strip(), "customer": b.get("name")})
        from utils.data_cache import DataCache
        DataCache.clear()
        self.reload()
        app_events().booking_updated.emit()
        app_events().booking_saved.emit()
        app_events().data_changed.emit()
        success(self, message="Booking declined.")

    def _send_confirmation_auto(self, b: dict) -> None:
        """Auto-trigger confirmation email on approval (best-effort, silent on failure)."""
        try:
            detail = repo.get_booking_detail(b["db_id"]) if b.get("db_id") else None
            if not detail:
                return
            biz = repo.get_business_info()
            booking_data = {**detail, "business_contact": biz.get("contact", "")}
            smtp = repo.get_smtp_config()
            if detail.get("email") and smtp.get("smtp_host"):
                from utils.mailer import send_booking_confirmation_email
                ok, _ = send_booking_confirmation_email(smtp, detail["email"], booking_data)
                if ok and detail.get("db_id"):
                    repo.log_confirmation_sent(detail["db_id"], "email")
        except Exception as exc:
            print(f"[booking] auto-confirm send failed: {exc}")

    def _send_confirmation(self, ref: str) -> None:
        """Manual resend of confirmation for a CONFIRMED booking."""
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or b["status"] != "CONFIRMED" or not b.get("db_id"):
            QMessageBox.information(self, "Not Available",
                "Confirmation can only be resent for confirmed bookings with a database record.")
            return
        detail = repo.get_booking_detail(b["db_id"])
        if not detail:
            return
        biz = repo.get_business_info()
        booking_data = {**detail, "business_contact": biz.get("contact", "")}
        smtp = repo.get_smtp_config()
        errors = []
        sent_email = False
        if detail.get("email") and smtp.get("smtp_host"):
            from utils.mailer import send_booking_confirmation_email
            ok, err = send_booking_confirmation_email(smtp, detail["email"], booking_data)
            if ok:
                repo.log_confirmation_sent(detail["db_id"], "email")
                sent_email = True
            else:
                errors.append(f"Email: {err}")
        if sent_email:
            QMessageBox.information(self, "Confirmation Sent",
                f"Booking confirmation has been sent via email to:\n{detail['email']}")
        elif errors:
            QMessageBox.warning(self, "Send Failed", "\n".join(errors))
        else:
            QMessageBox.information(self, "No Channel",
                "No email configured for this booking.\n"
                "Ensure customer has an email and SMTP is configured in Settings.")

    def _delete_booking(self, ref):
        from utils.auth import SessionManager
        if not SessionManager.has_permission("bookings", "delete"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to delete bookings.")
            return
        b = next((x for x in self._bookings if x.get("id") == ref), None)
        if not b:
            for rlist in getattr(self, "_tab_rows", {}).values():
                b = next((x for x in rlist if x.get("id") == ref), None)
                if b:
                    break
        if not b:
            return
        c_name = b.get("name", "this booking")
        if not confirm(self, title="Delete Booking",
                       message=f"Are you sure you want to delete booking for '{c_name}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if b.get("db_id"):
            ok = repo.delete_booking(b["db_id"])
            if not ok:
                QMessageBox.warning(self, "Delete Failed",
                    "The booking could not be deleted. Please check your connection to the server and try again.")
                return
            repo.write_audit_log(get_actor(), "DELETE", "bookings", b["db_id"], {"customer": b.get("name"), "amount": b.get("total")}, None)

        self._bookings = [x for x in (self._bookings or []) if isinstance(x, dict) and x.get("id") != ref]
        for tid in (0, 1, 2):
            if hasattr(self, "_tab_rows") and self._tab_rows and self._tab_rows.get(tid) is not None:
                self._tab_rows[tid] = [x for x in self._tab_rows[tid] if isinstance(x, dict) and x.get("id") != ref]
            if hasattr(self, "_tab_cached_full") and self._tab_cached_full and self._tab_cached_full.get(tid) is not None:
                self._tab_cached_full[tid] = [x for x in self._tab_cached_full[tid] if isinstance(x, dict) and x.get("id") != ref]

        from utils.data_cache import DataCache
        DataCache.clear()
        self.reload()
        app_events().booking_saved.emit()
        app_events().booking_updated.emit()
        app_events().data_changed.emit()
        success(self, message="Booking deleted successfully.")

    def _open_additional_charges(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or not b.get("db_id"):
            return
        dlg = AdditionalChargesDialog(self, booking=b)
        dlg.exec()
        if dlg.changed:
            self.reload()
            app_events().booking_updated.emit()
            app_events().data_changed.emit()

    def _edit_booking(self, ref):
        from utils.auth import SessionManager
        if not SessionManager.has_permission("bookings", "edit"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to edit bookings.")
            return
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b:
            return
        db_id = b.get("db_id")
        detail = repo.get_booking_detail(db_id) if db_id else None
        if not detail:
            detail = b
        modal = BookingModal(self, booking_data=detail)
        modal.booking_saved.connect(lambda data, orig=b: self._update_booking(orig, data))
        modal.exec()

    def _update_booking(self, orig, data):
        venue = str(data.get("venue") or "").strip()
        if not venue:
            venue = str(data.get("address") or "").strip()
        if not venue:
            QMessageBox.warning(self, "Validation Error", "Event Venue is required and cannot be blank.")
            return
        data["venue"] = venue

        db_id = orig.get("db_id") or data.get("db_id")
        if db_id:
            repo.update_booking(db_id, data)
            repo.write_audit_log(get_actor(), "UPDATE", "bookings", db_id,
                                 None, {"customer": data.get("name"), "amount": data.get("total")})
        self.reload()
        success(self, message="Order details updated successfully.")
        app_events().booking_updated.emit()

    def _open_modal(self):
        from utils.auth import SessionManager
        if not SessionManager.has_permission("bookings", "create"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to create bookings.")
            return
        modal = BookingModal(self)
        modal.booking_saved.connect(self._add_booking)
        modal.exec()

    def _add_booking(self, data):
        venue = str(data.get("venue") or "").strip()
        if not venue:
            venue = str(data.get("address") or "").strip()
        if not venue:
            QMessageBox.warning(self, "Validation Error", "Event Venue is required and cannot be blank.")
            return
        data["venue"] = venue

        result = repo.create_booking(data)
        if not result:
            QMessageBox.warning(self, "Booking Failed", "Failed to save booking to database. Please check application logs.")
            return
        bkg_id = result["booking_ref"]
        db_id  = result["booking_id"]

        repo.write_audit_log(get_actor(), "CREATE", "bookings", db_id,
                             None, {"customer": data.get("name"), "amount": data.get("total")})

        self._bookings.append({
            "db_id":  db_id,
            "date":   data["date"],
            "id":     bkg_id,
            "name":   data["name"],
            "pax":    str(data["pax"]),
            "total":  f"₱ {data['total']:,}",
            "status": data["status"],
        })
        self._populate_table()

        email_status = self._send_approval_request(data, bkg_id)
        if email_status is True:
            msg = f"Booking created successfully.\nConfirmation email sent to {data.get('email', '')}."
        elif email_status is False:
            msg = "Booking created successfully.\nCould not send confirmation email — check SMTP settings."
        else:
            msg = "Booking created successfully."
        success(self, message=msg)

        try:
            repo.push_notification(
                type_="info",
                title="New Booking Request",
                message=f"{data['name']} submitted a new booking request for {data['pax']} pax on {data['date']}.",
                color="#3B82F6"
            )
        except Exception as exc:
            print(f"[Notification] Failed to create in-app notification: {exc}")

        app_events().booking_saved.emit()

    def _send_approval_request(self, data: dict, bkg_ref: str):
        """Send a booking approval request email to the customer.
        Returns True on success, False on failure, None if email/SMTP not configured."""
        try:
            email = data.get("email", "")
            if not email or "@" not in email:
                return None
            smtp = repo.get_smtp_config()
            if not smtp.get("smtp_host"):
                return None
            biz = repo.get_business_info()
            booking_data = {
                **data,
                "booking_ref":      bkg_ref,
                "business_contact": biz.get("contact", ""),
                "business_name":    biz.get("name", "Jayraldine's Catering"),
                "event_date":       data.get("date", "—"),
                "event_time":       repo.format_time_ampm(data.get("time") or data.get("event_time")),
            }
            from utils.mailer import send_booking_approval_request_email
            ok, err = send_booking_approval_request_email(smtp, email, booking_data)
            if ok:
                print(f"[booking] Approval request email sent to {email}")
                return True
            else:
                print(f"[booking] Approval request email failed: {err}")
                return False
        except Exception as exc:
            print(f"[booking] send_approval_request failed: {exc}")
            return False

    def _open_filter(self):
        if self._filter_popover is None:
            win = self.window()
            self._filter_popover = FilterPopover(
                parent=win if win else self,
                statuses=["All", "PENDING", "CONFIRMED", "CANCELLED"],
            )
            self._filter_popover.filter_applied.connect(self._on_filter_applied)
        self._filter_popover.toggle_anchored(self._btn_filter)

    def _on_filter_applied(self, result):
        status = result.get("statuses", ["All"])[0]
        self._active_filter = "All" if not status or status == "All" else status
        self._populate_table()

    def _export_csv(self):
        from components.export_dialog import ExportWizardDialog
        dlg = ExportWizardDialog(parent=self)
        dlg.exec()

    def _current_filter_args(self):
        # The 6 server-side filter values threaded into every DB fetch/count call
        # so all 3 tabs (active now, or lazily loaded later) stay consistent.
        return (self._filter_date_start, self._filter_date_end,
                self._filter_customer, self._filter_event,
                self._filter_time_start, self._filter_time_end)

    def _on_server_filter_changed(self):
        # Read the current widget state into self._filter_* then reload. Applies
        # WITHIN whichever tab is active; the other two tabs reset here and lazily
        # re-fetch with these same values on next switch via _ensure_tab_loaded.
        if getattr(self, "_suspend_filter_signals", False):
            return
        if hasattr(self, "_filter_timer"):
            self._filter_timer.start(200)
        else:
            self._apply_server_filter_reload()

    def _apply_server_filter_reload(self):
        self._filter_date_start = self._date_from.date().toString("yyyy-MM-dd")
        self._filter_date_end = self._date_to.date().toString("yyyy-MM-dd")
        cust = self._customer_filter.currentText().strip()
        self._filter_customer = None if (not cust or cust == "All Customers") else cust
        ev = self._event_filter.currentText().strip()
        self._filter_event = None if (not ev or ev == "All Occasions") else ev
        # Full 00:00-23:59 range means "no time restriction" - only treat it
        # as an active filter once the user narrows it from the full day.
        t_start = self._time_from.time()
        t_end = self._time_to.time()
        if t_start == QTime(0, 0) and t_end == QTime(23, 59):
            self._filter_time_start = None
            self._filter_time_end = None
        else:
            self._filter_time_start = t_start.toString("HH:mm")
            self._filter_time_end = t_end.toString("HH:mm")
        # Force a DB reload (not the one-time memory cache) so counts + rows for
        # all tabs reflect the new filter. _refresh_bookings resets pagination for
        # all 3 tabs and re-fetches page 0 of the active tab.
        self._has_loaded_once = True
        self._refresh_bookings()

    def _reset_server_filters(self):
        # Restore the default 1-month-back / 2-months-ahead window and clear the
        # customer/occasion pickers, then reload once.
        self._filter_date_start, self._filter_date_end = repo.get_default_orders_window()
        self._filter_time_start = None
        self._filter_time_end = None
        self._suspend_filter_signals = True
        try:
            self._date_from.setDate(QDate.fromString(self._filter_date_start, "yyyy-MM-dd"))
            self._date_to.setDate(QDate.fromString(self._filter_date_end, "yyyy-MM-dd"))
            self._time_from.setTime(QTime(0, 0))
            self._time_to.setTime(QTime(23, 59))
            self._customer_filter.setCurrentIndex(0)
            self._event_filter.setCurrentIndex(0)
        finally:
            self._suspend_filter_signals = False
        self._on_server_filter_changed()

    def _parse_booking_date(self, val):
        # Booking dicts carry event_date pre-formatted as "%b %d, %Y" (e.g.
        # "Sep 14, 2026"); normalize to ISO for comparison against the filter
        # bounds. Returns None on any parse failure (row is then kept, not dropped).
        if not val:
            return None
        from datetime import datetime as _dt
        s = str(val).strip()
        for fmt in ("%b %d, %Y", "%Y-%m-%d"):
            try:
                return _dt.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    def _parse_booking_time(self, val):
        # Booking dicts carry event_time pre-formatted for display (e.g.
        # "6:00 PM" via format_time_ampm); normalize to 24h "HH:MM" for
        # comparison against the filter bounds. None on parse failure (row
        # kept, not dropped, matching _parse_booking_date's behavior).
        if not val:
            return None
        from datetime import datetime as _dt
        s = str(val).strip()
        for fmt in ("%I:%M %p", "%H:%M", "%H:%M:%S"):
            try:
                return _dt.strptime(s, fmt).strftime("%H:%M")
            except ValueError:
                continue
        return None

    def _server_filter_rows(self, rows):
        # Apply the same date/time/customer/occasion filter client-side to a
        # pre-loaded (memory-cached) list, so the first-open cache path
        # respects the default window and any active filter exactly like
        # the DB path does.
        ds, de, cust, ev, ts, te = self._current_filter_args()
        if not (ds and de) and not cust and not ev and not (ts and te):
            return list(rows or [])
        out = []
        for b in rows or []:
            if ds and de:
                iso = self._parse_booking_date(b.get("event_date") or b.get("date"))
                if iso is not None and not (ds <= iso <= de):
                    continue
            if ts and te:
                t_iso = self._parse_booking_time(b.get("event_time") or b.get("time"))
                if t_iso is not None and not (ts <= t_iso <= te):
                    continue
            if cust and cust.lower() not in (b.get("customer_name") or "").lower():
                continue
            if ev and ev.lower() not in (b.get("occasion") or "").lower():
                continue
            out.append(b)
        return out

    def filter_search(self, text):
        self._search_query = str(text or "")
        if hasattr(self, "_search_timer"):
            self._search_timer.start(500)
        else:
            self._populate_table()

    def _on_search_timer_fired(self):
        self._populate_table()

    def search(self, query: str):
        if hasattr(self, "_search_input"):
            self._search_input.setText(query)
        else:
            self.filter_search(query)

    def _open_import_dialog(self):
        from utils.auth import SessionManager
        if not SessionManager.has_permission("bookings", "create"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to import bookings.")
            return
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="bookings", parent=self)
        if dlg.exec():
            self._refresh_bookings()

    def _on_card_checked(self, ref: str, state):
        if not ref:
            return
        if state:
            self._selected_refs.add(ref)
        else:
            self._selected_refs.discard(ref)
        self._update_selection_ui()

    def _toggle_select_tab(self, tab_type: str, state):
        t_type = (tab_type or "").upper()
        if t_type == "PENDING":
            target_refs = [b["id"] for b in self._visible_bookings() if b.get("status") == "PENDING"]
        elif t_type == "CONFIRMED":
            target_refs = [b["id"] for b in self._visible_bookings() if b.get("status") in ("CONFIRMED", "COMPLETED")]
        else:
            target_refs = [b["id"] for b in self._visible_bookings()]

        if state:
            self._selected_refs.update(target_refs)
        else:
            self._selected_refs.difference_update(target_refs)

        for ref, cb in self._card_checkboxes.items():
            if ref in target_refs:
                cb.blockSignals(True)
                cb.setChecked(bool(state))
                cb.blockSignals(False)

        self._update_selection_ui()

    def _update_selection_ui(self):
        count = len(self._selected_refs)
        pending_count = sum(1 for r in self._selected_refs if any(b["id"] == r and b.get("status") == "PENDING" for b in self._bookings))
        cancellable_count = sum(1 for r in self._selected_refs if any(b["id"] == r and b.get("status") != "CANCELLED" for b in self._bookings))

        toolbars = [
            getattr(self, "_pending_tb", getattr(self, "_pending_toolbar", None)),
            getattr(self, "_confirmed_tb", getattr(self, "_confirmed_toolbar", None)),
            getattr(self, "_all_tb", getattr(self, "_all_toolbar", None)),
        ]

        for tb in toolbars:
            if not tb:
                continue
            tb["selected_lbl"].setText(f"{count} selected")
            tb["delete_selected"].setEnabled(count > 0)
            tb["delete_selected"].setText(f"  Delete Selected ({count})" if count > 0 else "  Delete Selected")

            if tb.get("print_selected"):
                tb["print_selected"].setEnabled(count > 0)
                tb["print_selected"].setText(f"  Print Selected ({count})" if count > 0 else "  Print Selected")

            if tb.get("batch_approve"):
                tb["batch_approve"].setEnabled(pending_count > 0)
                tb["batch_approve"].setText(f"  Batch Confirm ({pending_count})" if pending_count > 0 else "  Batch Confirm")

            if tb.get("batch_cancel"):
                tb["batch_cancel"].setEnabled(cancellable_count > 0)
                tb["batch_cancel"].setText(f"  Batch Cancel ({cancellable_count})" if cancellable_count > 0 else "  Batch Cancel")

            tab_t = (tb.get("tab_type") or "").upper()
            if tab_t == "PENDING":
                t_refs = [b["id"] for b in self._visible_bookings() if b.get("status") == "PENDING"]
            elif tab_t == "CONFIRMED":
                t_refs = [b["id"] for b in self._visible_bookings() if b.get("status") in ("CONFIRMED", "COMPLETED")]
            else:
                t_refs = [b["id"] for b in self._visible_bookings()]

            all_checked = len(t_refs) > 0 and all(r in self._selected_refs for r in t_refs)
            tb["select_all"].blockSignals(True)
            tb["select_all"].setChecked(all_checked)
            tb["select_all"].blockSignals(False)

    def _delete_selected_bookings(self):
        if not self._selected_refs:
            return
        count = len(self._selected_refs)
        if not confirm(self, title="Delete Multiple Bookings",
                       message=f"Are you sure you want to permanently delete {count} selected booking(s)/order(s)?\nThis cannot be undone.",
                       confirm_label=f"Delete {count} Orders", danger=True):
            return

        db_ids_or_refs = []
        for ref in list(self._selected_refs):
            b = next((x for x in self._bookings if x["id"] == ref), None)
            if b and b.get("db_id"):
                db_ids_or_refs.append(b["db_id"])
            else:
                db_ids_or_refs.append(ref)

        for ref in list(self._selected_refs):
            b = next((x for x in self._bookings if x["id"] == ref), None)
            if b and b.get("db_id"):
                repo.write_audit_log(get_actor(), "DELETE", "bookings", b["db_id"], {"customer": b.get("name"), "amount": b.get("total")}, None)

        deleted = repo.delete_multiple_bookings(db_ids_or_refs)
        self._selected_refs.clear()
        self.reload()
        app_events().booking_saved.emit()
        app_events().data_changed.emit()
        success(self, message=f"Successfully deleted {deleted} order(s).")

    def _batch_approve_bookings(self):
        if not self._selected_refs:
            return

        pending_items = [
            b for b in self._bookings
            if b.get("id") in self._selected_refs and b.get("status") == "PENDING"
        ]

        if not pending_items:
            QMessageBox.information(
                self,
                "Already Confirmed",
                "None of the selected orders are PENDING.\nAll selected bookings are already confirmed or completed."
            )
            return

        from components.confirm_booking_dialog import BatchConfirmBookingDialog, _parse_amount
        from datetime import date as _d

        dlg = BatchConfirmBookingDialog(pending_items, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return

        mode = dlg.get_action_mode()  # "none", "downpayment", "full"
        method = dlg.get_payment_method()
        remarks = dlg.get_payment_remarks()
        fixed_dp = dlg.get_payment_amount_per_booking()
        batch_color = dlg.get_color_theme()

        approved_cnt = 0
        total_collected = 0.0

        for b in pending_items:
            try:
                db_id = b.get("db_id")
                if not db_id:
                    continue
                detail = repo.get_booking_detail(db_id) or b
                tot_val = _parse_amount(detail.get("total") or detail.get("total_amount") or b.get("total", 0.0))
                paid_val = _parse_amount(detail.get("amount_paid") or detail.get("down_payment") or 0.0)
                rem = max(0.0, tot_val - paid_val)

                if mode == "full":
                    if rem > 0:
                        try:
                            repo.pay_invoice(db_id, payment_amount=rem, payment_date=_d.today(), method=method, note=remarks)
                            total_collected += rem
                        except Exception as p_err:
                            print(f"[booking] batch pay error for {db_id}: {p_err}")
                elif mode == "downpayment":
                    pay_amt = min(fixed_dp, rem) if fixed_dp > 0 else 0.0
                    if pay_amt > 0:
                        try:
                            repo.pay_invoice(db_id, payment_amount=pay_amt, payment_date=_d.today(), method=method, note=remarks)
                            total_collected += pay_amt
                        except Exception as p_err:
                            print(f"[booking] batch pay error for {db_id}: {p_err}")

                repo.update_booking_status(db_id, "CONFIRMED", color_theme=batch_color)
                if batch_color:
                    repo.update_booking_color_theme(db_id, batch_color)
                approved_cnt += 1
            except Exception as exc:
                print(f"[booking] batch confirm error for {b.get('id')}: {exc}")

        self._selected_refs.clear()
        self.reload()
        app_events().booking_saved.emit()
        app_events().booking_updated.emit()
        app_events().data_changed.emit()

        if mode == "full":
            success(self, message=f"Successfully batch confirmed {approved_cnt} booking(s) as Fully Paid (₱{total_collected:,.2f} recorded).")
        elif mode == "downpayment" and total_collected > 0:
            success(self, message=f"Successfully batch confirmed {approved_cnt} booking(s) with down payment (₱{total_collected:,.2f} recorded).")
        else:
            success(self, message=f"Successfully batch confirmed {approved_cnt} booking(s) (Unpaid / Kept Remaining Balance).")

    def _batch_cancel_bookings(self):
        if not self._selected_refs:
            return

        cancellable_refs = [
            ref for ref in list(self._selected_refs)
            if any(b["id"] == ref and b.get("status") != "CANCELLED" for b in self._bookings)
        ]

        if not cancellable_refs:
            QMessageBox.information(
                self,
                "Already Cancelled",
                "None of the selected orders can be cancelled.\nAll selected bookings are already cancelled."
            )
            return

        count = len(cancellable_refs)
        if not confirm(self, title="Batch Cancel Bookings",
                       message=f"Cancel {count} selected booking(s)?",
                       confirm_label=f"Cancel {count} Bookings", danger=True):
            return

        cancelled_cnt = 0
        for ref in cancellable_refs:
            b = next((x for x in self._bookings if x["id"] == ref), None)
            if b and b.get("db_id"):
                repo.update_booking_status(b["db_id"], "CANCELLED", "Batch cancelled by user")
                repo.write_audit_log(get_actor(), "CANCEL", "bookings", b["db_id"], None, {"status": "CANCELLED", "reason": "Batch cancelled by user", "customer": b.get("name")})
                cancelled_cnt += 1

        self._selected_refs.clear()
        self.reload()
        app_events().booking_saved.emit()
        app_events().data_changed.emit()
        success(self, message=f"Batch cancelled {cancelled_cnt} booking(s).")

    def _open_multi_add_dialog(self):
        from utils.auth import SessionManager
        if not SessionManager.has_permission("bookings", "create"):
            QMessageBox.warning(self, "Access Denied", "Your account does not have permission to create bookings.")
            return
        dlg = AddMultipleBookingsDialog(self)
        if dlg.exec():
            self.reload()
            app_events().booking_saved.emit()
            app_events().data_changed.emit()
            success(self, message=f"Added {dlg._added_count} booking(s) successfully.")

    def _export_csv(self):
        bookings = self._visible_bookings()
        if not bookings:
            bookings = getattr(self, "_bookings", []) or []

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Bookings", "jayraldines_bookings_export.xlsx", "Excel Spreadsheet (*.xlsx);;CSV Files (*.csv)"
        )
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        if not ext:
            path = f"{path}.xlsx"
            ext = ".xlsx"

        headers = [
            "Reference ID", "Customer Name", "Contact Number", "Email Address",
            "Event Date", "Event Time", "Occasion", "Venue", "Pax",
            "Total Amount (₱)", "Down Payment (₱)", "Balance (₱)", "Status", "Payment Mode", "Notes"
        ]

        rows = []
        for b in bookings:
            raw_tot = b.get("total_amount") or b.get("total") or 0.0
            if isinstance(raw_tot, str):
                try:
                    tot_num = float(raw_tot.replace("₱", "").replace(",", "").strip())
                except ValueError:
                    tot_num = 0.0
            else:
                tot_num = float(raw_tot or 0.0)

            raw_paid = b.get("amount_paid") or b.get("down_payment") or 0.0
            if isinstance(raw_paid, str):
                try:
                    paid_num = float(raw_paid.replace("₱", "").replace(",", "").strip())
                except ValueError:
                    paid_num = 0.0
            else:
                paid_num = float(raw_paid or 0.0)

            balance_num = max(0.0, tot_num - paid_num)
            
            pax_raw = b.get("pax") or 0
            try:
                pax_val = int(pax_raw)
            except (ValueError, TypeError):
                pax_val = 0

            ref_id = str(b.get("booking_ref") or b.get("ref_id") or b.get("id") or "—")
            cust_name = str(b.get("customer_name") or b.get("name") or b.get("client_name") or "—")
            contact = str(b.get("contact") or b.get("phone") or "—")
            email = str(b.get("email") or "—")
            ev_date = str(b.get("event_date") or b.get("date") or "—")
            raw_t = b.get("event_time") or b.get("time") or ""
            ev_time = repo.format_time_ampm(raw_t) if raw_t else "—"
            occasion = str(b.get("occasion") or "—")
            venue = str(b.get("venue") or "—")
            status = str(b.get("status") or "PENDING").upper()
            pay_mode = str(b.get("payment_mode") or "Cash")
            notes = str(b.get("notes") or "")

            rows.append([
                ref_id,
                cust_name,
                contact,
                email,
                ev_date,
                ev_time,
                occasion,
                venue,
                pax_val,
                f"{tot_num:,.2f}",
                f"{paid_num:,.2f}",
                f"{balance_num:,.2f}",
                status,
                pay_mode,
                notes
            ])

        if ext in (".xlsx", ".xls"):
            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                from openpyxl.utils import get_column_letter

                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Bookings & Orders"

                header_fill = PatternFill(start_color="E11D48", end_color="E11D48", fill_type="solid")
                header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                data_font = Font(name="Calibri", size=10)
                thin_border = Border(
                    left=Side(style='thin', color='CBD5E1'),
                    right=Side(style='thin', color='CBD5E1'),
                    top=Side(style='thin', color='CBD5E1'),
                    bottom=Side(style='thin', color='CBD5E1')
                )

                all_rows = [headers] + rows
                for row_idx, r in enumerate(all_rows, start=1):
                    ws.append(r)
                    for col_idx in range(1, len(r) + 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        cell.border = thin_border
                        if row_idx == 1:
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                        else:
                            cell.font = data_font
                            val_str = str(cell.value or "")
                            if col_idx in (9, 10, 11, 12): # Pax and Currency columns
                                cell.alignment = Alignment(horizontal="right", vertical="center")
                            elif col_idx in (1, 5, 6, 13, 14): # Ref, Date, Time, Status, Pay Mode
                                cell.alignment = Alignment(horizontal="center", vertical="center")
                            else:
                                cell.alignment = Alignment(horizontal="left", vertical="center")

                ws.row_dimensions[1].height = 28
                for r_idx in range(2, len(all_rows) + 1):
                    ws.row_dimensions[r_idx].height = 22

                for col in ws.columns:
                    max_len = 0
                    col_letter = get_column_letter(col[0].column)
                    for cell in col:
                        val_str = str(cell.value or "")
                        if len(val_str) > max_len:
                            max_len = len(val_str)
                    ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

                wb.save(path)
                prompt_file_saved(self, path, title="Export Complete", message=f"Exported {len(rows)} booking(s) to Excel successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Could not export bookings: {e}")
        else:
            try:
                import csv
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(rows)
                prompt_file_saved(self, path, title="Export Complete", message=f"Exported {len(rows)} booking(s) to CSV successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Could not export bookings: {e}")

