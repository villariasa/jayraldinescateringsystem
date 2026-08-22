from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFileDialog, QMessageBox, QInputDialog, QScrollArea,
    QCheckBox, QComboBox, QLineEdit, QDateEdit, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, btn_icon_red, get_icon
from utils.theme import ThemeManager
from components.booking_modal import BookingModal
from components.dialogs import confirm, success
from components.filter_popover import FilterPopover
import utils.repository as repo
from utils.session import get_actor
from utils.signals import app_events
from utils.data_loader import run_async


_STATUS_COLORS = {
    "CONFIRMED": ("#22C55E", "rgba(34,197,94,.15)", "rgba(34,197,94,.3)"),
    "PENDING":   ("#F59E0B", "rgba(245,158,11,.15)", "rgba(245,158,11,.3)"),
    "CANCELLED": ("#EF4444", "rgba(239,68,68,.15)",  "rgba(239,68,68,.3)"),
}


class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
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


def _action_buttons(status, on_approve, on_decline):
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(4, 0, 4, 0)
    row.setSpacing(6)
    if status == "PENDING":
        approve_btn = QPushButton()
        approve_btn.setIcon(get_icon("check", color="#22C55E", size=QSize(16, 16)))
        approve_btn.setIconSize(QSize(16, 16))
        approve_btn.setFixedSize(28, 28)
        approve_btn.setStyleSheet(
            "border-radius:14px;"
            "background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.3);"
        )
        approve_btn.setCursor(Qt.PointingHandCursor)
        approve_btn.setToolTip("Approve")
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
        decline_btn.setToolTip("Decline")
        decline_btn.clicked.connect(on_decline)
        row.addWidget(decline_btn)
    else:
        locked_lbl = QLabel("—")
        locked_lbl.setStyleSheet("font-size:13px;")
        row.addWidget(locked_lbl)
    row.addStretch()
    return widget


_OCCASIONS_LIST = [
    "Wedding", "Birthday", "Debut", "Corporate Event", "Anniversary", "Christening", "Graduation", "Holiday Party", "Party"
]


class AddMultipleBookingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Multiple Orders & Bookings")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(960, 550)
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

        sub = QLabel("Quickly enter multiple catering reservations with integrated date picker & occasion selector:")
        sub.setObjectName("subtitle")
        lay.addWidget(sub)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Customer Name *", "Contact / Phone", "Occasion", "Event Date (Calendar) *", "Pax *", "Total Amount (₱) *"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
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
            QTableWidget::item {
                padding: 4px 6px;
                color: #F9FAFB;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            QTableWidget::item:selected {
                background-color: rgba(225,29,72,0.25);
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #111827;
                color: #9CA3AF;
                font-weight: 700;
                font-size: 11px;
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
        """)

        # Add 5 initial rows
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

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Customer / Company Name *")
        name_edit.setFixedHeight(34)
        name_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 0, name_edit)

        contact_edit = QLineEdit()
        contact_edit.setPlaceholderText("09171234567")
        contact_edit.setFixedHeight(34)
        contact_edit.setStyleSheet("QLineEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QLineEdit:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 1, contact_edit)

        occ_combo = QComboBox()
        occ_combo.addItems(_OCCASIONS_LIST)
        occ_combo.setCurrentText("Party")
        occ_combo.setFixedHeight(34)
        occ_combo.setStyleSheet("""
            QComboBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; }
            QComboBox:focus { border-color: #E11D48; }
            QComboBox QAbstractItemView { background: #1E293B; color: #FFFFFF; selection-background-color: #E11D48; selection-color: #FFFFFF; border: 1px solid #334155; }
        """)
        self.table.setCellWidget(r, 2, occ_combo)

        date_edit = QDateEdit(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        date_edit.setFixedHeight(34)
        date_edit.setStyleSheet("""
            QDateEdit { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; }
            QDateEdit:focus { border-color: #E11D48; }
            QCalendarWidget QWidget { background-color: #1E293B; color: #FFFFFF; }
            QCalendarWidget QAbstractItemView:enabled { background-color: #0F172A; color: #FFFFFF; selection-background-color: #E11D48; selection-color: #FFFFFF; }
        """)
        self.table.setCellWidget(r, 3, date_edit)

        pax_spin = QSpinBox()
        pax_spin.setRange(1, 10000)
        pax_spin.setValue(50)
        pax_spin.setFixedHeight(34)
        pax_spin.setStyleSheet("QSpinBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QSpinBox:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 4, pax_spin)

        total_spin = QDoubleSpinBox()
        total_spin.setRange(0, 9999999)
        total_spin.setPrefix("₱ ")
        total_spin.setDecimals(2)
        total_spin.setSingleStep(500)
        total_spin.setValue(15000.0)
        total_spin.setFixedHeight(34)
        total_spin.setStyleSheet("QDoubleSpinBox { background: #1E293B; color: #FFFFFF; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: 13px; } QDoubleSpinBox:focus { border-color: #E11D48; }")
        self.table.setCellWidget(r, 5, total_spin)

    def _delete_selected_row(self):
        curr = self.table.currentRow()
        if curr >= 0:
            self.table.removeRow(curr)

    def _save_all(self):
        rows_to_save = []
        for r in range(self.table.rowCount()):
            name_w = self.table.cellWidget(r, 0)
            contact_w = self.table.cellWidget(r, 1)
            occ_w = self.table.cellWidget(r, 2)
            date_w = self.table.cellWidget(r, 3)
            pax_w = self.table.cellWidget(r, 4)
            total_w = self.table.cellWidget(r, 5)

            name = name_w.text().strip() if isinstance(name_w, QLineEdit) else ""
            contact = contact_w.text().strip() if isinstance(contact_w, QLineEdit) else ""
            occ = occ_w.currentText().strip() if isinstance(occ_w, QComboBox) else "Party"
            date_val = date_w.date().toString("yyyy-MM-dd") if isinstance(date_w, QDateEdit) else ""
            pax = pax_w.value() if isinstance(pax_w, QSpinBox) else 50
            tot = total_w.value() if isinstance(total_w, QDoubleSpinBox) else 0.0

            if not name:
                continue

            rows_to_save.append({
                "name": name,
                "contact": contact,
                "occasion": occ,
                "date": date_val,
                "event_time": "18:00",
                "venue": "Client Venue",
                "pax": pax,
                "total": tot,
                "amount_paid": tot,
                "payment_mode": "Cash",
                "status": "CONFIRMED",
                "notes": "Batch created order",
                "menu_type": "Standard",
                "package_id": 1,
            })

        if not rows_to_save:
            self._err.setText("Please enter at least one booking / customer.")
            self._err.show()
            return

        saved = 0
        for b_data in rows_to_save:
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
            ref = repo.add_booking(b_data)
            if ref:
                saved += 1

        self._added_count = saved
        self.accept()


class BookingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._dirty = True
        self._bookings = []
        self._selected_refs: set[str] = set()
        self._card_checkboxes: dict[str, QCheckBox] = {}
        self._active_filter = "All"
        self._filter_popover = None
        self._build_ui()
        db_rows = repo.get_all_bookings()
        self._bookings = db_rows if db_rows else []
        self._populate_table()
        self._dirty = False
        app_events().booking_saved.connect(self._mark_dirty_and_reload)
        app_events().data_changed.connect(self._mark_dirty)

    def _mark_dirty(self):
        self._dirty = True

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self._refresh_bookings()

    def showEvent(self, event):
        super().showEvent(event)
        if self._dirty:
            self._refresh_bookings()

    def reload(self):
        self._mark_dirty()
        if self.isVisible():
            self._refresh_bookings()

    def _refresh_bookings(self):
        self._dirty = False
        run_async(self, repo.get_all_bookings, self._on_bookings_loaded)

    def _on_bookings_loaded(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        if data is not None:
            self._bookings = data
            self._selected_refs.clear()
            self._populate_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)

        header_row = QHBoxLayout()
        v = QVBoxLayout()
        v.setSpacing(4)
        title = QLabel("Orders & Bookings")
        title.setObjectName("pageTitle")
        sub = QLabel("Manage all catering reservations and upcoming events.")
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

        table_card = AnimatedCard()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(24, 20, 24, 20)
        table_layout.setSpacing(14)

        t_head = QHBoxLayout()
        t_title = QLabel("Current Bookings")
        t_title.setObjectName("h2")
        t_head.addWidget(t_title)
        t_head.addStretch()

        self._btn_filter = QPushButton("  Filter")
        self._btn_filter.setObjectName("secondaryButton")
        self._btn_filter.setIcon(btn_icon_secondary("filter"))
        self._btn_filter.setIconSize(QSize(14, 14))
        self._btn_filter.clicked.connect(self._open_filter)

        btn_export = QPushButton("  Export")
        btn_export.setObjectName("secondaryButton")
        btn_export.setIcon(btn_icon_secondary("export"))
        btn_export.setIconSize(QSize(14, 14))
        btn_export.clicked.connect(self._export_csv)

        t_head.addWidget(self._btn_filter)
        t_head.addWidget(btn_export)
        table_layout.addLayout(t_head)

        # Batch Selection Toolbar
        batch_toolbar = QHBoxLayout()
        batch_toolbar.setContentsMargins(2, 2, 2, 2)
        batch_toolbar.setSpacing(12)

        self._cb_select_all = QCheckBox("Select All")
        self._cb_select_all.setStyleSheet("QCheckBox { font-weight: 600; font-size: 13px; color: #9CA3AF; }")
        self._cb_select_all.stateChanged.connect(self._toggle_select_all)
        batch_toolbar.addWidget(self._cb_select_all)

        self._lbl_selected_count = QLabel("0 selected")
        self._lbl_selected_count.setStyleSheet("font-size: 12px; color: #6B7280; font-weight: 600;")
        batch_toolbar.addWidget(self._lbl_selected_count)

        batch_toolbar.addStretch()

        self._btn_batch_approve = QPushButton("  Batch Confirm")
        self._btn_batch_approve.setObjectName("secondaryButton")
        self._btn_batch_approve.setIcon(get_icon("check", color="#22C55E", size=QSize(13, 13)))
        self._btn_batch_approve.setIconSize(QSize(13, 13))
        self._btn_batch_approve.setEnabled(False)
        self._btn_batch_approve.setCursor(Qt.PointingHandCursor)
        self._btn_batch_approve.clicked.connect(self._batch_approve_bookings)
        batch_toolbar.addWidget(self._btn_batch_approve)

        self._btn_batch_cancel = QPushButton("  Batch Cancel")
        self._btn_batch_cancel.setObjectName("secondaryButton")
        self._btn_batch_cancel.setIcon(get_icon("close", color="#F59E0B", size=QSize(13, 13)))
        self._btn_batch_cancel.setIconSize(QSize(13, 13))
        self._btn_batch_cancel.setEnabled(False)
        self._btn_batch_cancel.setCursor(Qt.PointingHandCursor)
        self._btn_batch_cancel.clicked.connect(self._batch_cancel_bookings)
        batch_toolbar.addWidget(self._btn_batch_cancel)

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
        self._btn_delete_selected.clicked.connect(self._delete_selected_bookings)
        batch_toolbar.addWidget(self._btn_delete_selected)

        table_layout.addLayout(batch_toolbar)

        div = QFrame()
        div.setObjectName("divider")
        div.setFixedHeight(1)
        table_layout.addWidget(div)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 10, 0)
        self.cards_layout.setSpacing(12)

        self.scroll_area.setWidget(self.cards_container)
        table_layout.addWidget(self.scroll_area)
        layout.addWidget(table_card)

        self._populate_table()

    def _visible_bookings(self):
        f = self._active_filter
        if f == "All" or not f:
            return self._bookings
        if isinstance(f, list):
            return [b for b in self._bookings if b["status"] in f]
        return [b for b in self._bookings if b["status"] == f]

    def _populate_table(self, data=None):
        if hasattr(self, "cards_container"):
            self.cards_container.setUpdatesEnabled(False)
        try:
            self._card_checkboxes.clear()
            while self.cards_layout.count():
                item = self.cards_layout.takeAt(0)
                if item:
                    w = item.widget()
                    if w:
                        w.hide()
                        w.deleteLater()

            rows = data if data is not None else self._visible_bookings()

            if not rows:
                empty_lbl = QLabel("No bookings found.")
                empty_lbl.setObjectName("subtitle")
                empty_lbl.setAlignment(Qt.AlignCenter)
                self.cards_layout.addWidget(empty_lbl)
            else:
                for b in rows:
                    card = self._create_booking_card(b)
                    self.cards_layout.addWidget(card)

            self.cards_layout.addStretch()
            self._update_selection_ui()
        finally:
            if hasattr(self, "cards_container"):
                self.cards_container.setUpdatesEnabled(True)

    def _create_booking_card(self, b: dict) -> QFrame:
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
        elif b["status"] == "PENDING":
            bref = b["id"]
            c4.addWidget(_action_buttons(
                b["status"],
                on_approve=lambda _, r=bref: self._approve_booking(r),
                on_decline=lambda _, r=bref: self._decline_booking(r)
            ))
        lay.addLayout(c4, 2)

        # Col 5: Actions (Edit, Delete, Confirmation)
        actions_w = QFrame()
        actions_w.setStyleSheet("background: transparent;")
        actions_l = QHBoxLayout(actions_w)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(6)

        bref = b["id"]

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(13, 13)))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet("background:transparent;border:none;")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setToolTip("Edit booking")
        edit_btn.setEnabled(b["status"] == "PENDING")
        if b["status"] != "PENDING":
            edit_btn.setStyleSheet("background:transparent;border:none;opacity:0.3;")
        edit_btn.clicked.connect(lambda _, r=bref: self._edit_booking(r))

        del_btn = QPushButton()
        del_btn.setIcon(btn_icon_red("trash"))
        del_btn.setIconSize(QSize(13, 13))
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("border:none;background:transparent;")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("Delete booking")
        del_btn.clicked.connect(lambda _, r=bref: self._delete_booking(r))

        confirm_btn = QPushButton()
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

        actions_l.addWidget(edit_btn)
        actions_l.addWidget(del_btn)
        actions_l.addWidget(confirm_btn)
        lay.addWidget(actions_w)

        return card

    def _approve_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b:
            return

        try:
            from datetime import date as _d
            from components.confirm_booking_dialog import _parse_amount

            if b.get("db_id"):
                repo.update_booking_status(b["db_id"], "CONFIRMED")
                try:
                    detail = repo.get_booking_detail(b["db_id"])
                    if detail and detail.get("customer_id"):
                        repo.recalculate_loyalty(detail["customer_id"])
                except Exception:
                    pass
                try:
                    repo.sync_kitchen_from_bookings()
                except Exception:
                    pass

            b["status"] = "CONFIRMED"

            inv_id = None
            if b.get("db_id"):
                try:
                    inv = repo.auto_create_invoice(b["db_id"])
                    if inv:
                        inv_id = inv.get("id") or inv.get("invoice_id")
                    if not inv_id:
                        inv_info = repo.get_invoice_payment_info(b["db_id"])
                        if inv_info:
                            inv_id = inv_info.get("invoice_id")
                except Exception as exc:
                    print(f"[booking] auto_create_invoice failed: {exc}")

            # Record full payment
            if b.get("db_id"):
                try:
                    tot_amount = _parse_amount(b.get("total", 0.0))
                    method = b.get("payment_mode") or "Cash"
                    remarks = "Auto-confirmed full payment"
                    if tot_amount > 0:
                        try:
                            repo.pay_invoice(b["db_id"], tot_amount, _d.today(), method=method, note=remarks)
                        except Exception:
                            if inv_id:
                                repo.add_payment_record(inv_id, tot_amount, _d.today(), method=method, note=remarks)
                    b["amount_paid"] = tot_amount
                    b["paid"] = tot_amount
                    app_events().payment_recorded.emit()
                    app_events().booking_updated.emit()
                except Exception as p_exc:
                    print(f"[booking] auto payment record failed: {p_exc}")

            self._populate_table()
            success(self, message="Booking confirmed and marked as FULLY PAID!")
            repo.write_audit_log(get_actor(), "APPROVE", "bookings", b.get("db_id"), None, {"status": "CONFIRMED"})

            try:
                repo.push_notification(
                    "success",
                    "Booking Confirmed",
                    f"Booking for {b.get('name', '')} on {b.get('date', '')} has been confirmed.",
                    "#22C55E",
                )
            except Exception:
                pass

            if b.get("db_id"):
                self._send_confirmation_auto(b)
            app_events().booking_saved.emit()
        except Exception as exc:
            QMessageBox.warning(self, "Cannot Approve", str(exc))

    def _decline_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or b["status"] != "PENDING":
            return
        reason, ok = QInputDialog.getText(
            self, "Cancellation Reason",
            f"Enter reason for declining booking for '{b['name']}' (optional):"
        )
        if not ok:
            return
        if not confirm(self, title="Decline Booking",
                       message=f"Decline booking for '{b['name']}'? This will mark it as Cancelled.",
                       confirm_label="Decline", danger=True):
            return
        b["status"] = "CANCELLED"
        if b.get("db_id"):
            repo.update_booking_status(b["db_id"], "CANCELLED", reason.strip() or None)
            repo.write_audit_log(get_actor(), "CANCEL", "bookings", b["db_id"], None, {"status": "CANCELLED", "reason": reason.strip()})
        self._populate_table()
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
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b:
            return
        if not confirm(self, title="Delete Booking",
                       message=f"Are you sure you want to delete booking for '{b['name']}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        if b.get("db_id"):
            repo.delete_booking(b["db_id"])
        self._bookings = [x for x in self._bookings if x["id"] != ref]
        self._populate_table()
        success(self, message="Booking deleted successfully.")

    def _edit_booking(self, ref):
        b = next((x for x in self._bookings if x["id"] == ref), None)
        if not b or b["status"] != "PENDING":
            return
        modal = BookingModal(self, booking_data=b)
        modal.booking_saved.connect(lambda data, orig=b: self._update_booking(orig, data))
        modal.exec()

    def _update_booking(self, orig, data):
        if orig.get("db_id"):
            repo.update_booking(orig["db_id"], data)
        orig.update({
            "name":  data["name"],
            "date":  data["date"],
            "pax":   str(data["pax"]),
            "total": f"₱ {data['total']:,}",
        })
        self._populate_table()
        success(self, message="Booking updated successfully.")

    def _open_modal(self):
        modal = BookingModal(self)
        modal.booking_saved.connect(self._add_booking)
        modal.exec()

    def _add_booking(self, data):
        result = repo.create_booking(data)
        bkg_id = result["booking_ref"] if result else f"BKG-{len(self._bookings) + 1:03d}"
        db_id  = result["booking_id"]  if result else None

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
                "event_time":       data.get("time", "—"),
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
        path, _ = QFileDialog.getSaveFileName(self, "Export Bookings", "bookings.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Date", "Client", "Pax", "Total", "Status"])
            for b in self._bookings:
                writer.writerow([b["id"], b["date"], b["name"], b["pax"], b["total"], b["status"]])
        QMessageBox.information(self, "Export", f"Exported to:\n{path}")

    def filter_search(self, text):
        q = text.lower()
        filtered = [b for b in self._bookings if q in b["name"].lower() or q in b["id"].lower() or q in b["date"].lower()]
        self._populate_table(filtered)

    def _open_import_dialog(self):
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

    def _toggle_select_all(self, state):
        visible_refs = [b["id"] for b in self._visible_bookings()]
        if state:
            self._selected_refs.update(visible_refs)
        else:
            self._selected_refs.difference_update(visible_refs)

        for ref, cb in self._card_checkboxes.items():
            if ref in visible_refs:
                cb.blockSignals(True)
                cb.setChecked(bool(state))
                cb.blockSignals(False)

        self._update_selection_ui()

    def _update_selection_ui(self):
        count = len(self._selected_refs)
        self._lbl_selected_count.setText(f"{count} selected")
        self._btn_delete_selected.setEnabled(count > 0)
        self._btn_delete_selected.setText(f"  Delete Selected ({count})" if count > 0 else "  Delete Selected")
        self._btn_batch_approve.setEnabled(count > 0)
        self._btn_batch_approve.setText(f"  Batch Confirm ({count})" if count > 0 else "  Batch Confirm")
        self._btn_batch_cancel.setEnabled(count > 0)
        self._btn_batch_cancel.setText(f"  Batch Cancel ({count})" if count > 0 else "  Batch Cancel")

        all_visible_refs = [b["id"] for b in self._visible_bookings()]
        all_checked = len(all_visible_refs) > 0 and all(r in self._selected_refs for r in all_visible_refs)
        self._cb_select_all.blockSignals(True)
        self._cb_select_all.setChecked(all_checked)
        self._cb_select_all.blockSignals(False)

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

        deleted = repo.delete_multiple_bookings(db_ids_or_refs)
        self._selected_refs.clear()
        self.reload()
        app_events().booking_saved.emit()
        app_events().data_changed.emit()
        success(self, message=f"Successfully deleted {deleted} order(s).")

    def _batch_approve_bookings(self):
        if not self._selected_refs:
            return
        count = len(self._selected_refs)
        if not confirm(self, title="Batch Confirm Bookings",
                       message=f"Confirm and approve {count} selected booking(s)? This will mark them as CONFIRMED and auto-generate invoices.",
                       confirm_label=f"Confirm {count} Bookings"):
            return

        for ref in list(self._selected_refs):
            try:
                self._approve_booking(ref)
            except Exception:
                pass

        self._selected_refs.clear()
        self.reload()
        success(self, message=f"Batch confirmed {count} booking(s) successfully.")

    def _batch_cancel_bookings(self):
        if not self._selected_refs:
            return
        count = len(self._selected_refs)
        if not confirm(self, title="Batch Cancel Bookings",
                       message=f"Cancel {count} selected booking(s)?",
                       confirm_label=f"Cancel {count} Bookings", danger=True):
            return

        for ref in list(self._selected_refs):
            b = next((x for x in self._bookings if x["id"] == ref), None)
            if b and b.get("db_id"):
                repo.update_booking_status(b["db_id"], "CANCELLED", "Batch cancelled by user")
        self._selected_refs.clear()
        self.reload()
        app_events().booking_saved.emit()
        app_events().data_changed.emit()
        success(self, message=f"Batch cancelled {count} booking(s).")

    def _open_multi_add_dialog(self):
        dlg = AddMultipleBookingsDialog(self)
        if dlg.exec():
            self.reload()
            app_events().booking_saved.emit()
            app_events().data_changed.emit()
            success(self, message=f"Added {dlg._added_count} booking(s) successfully.")

