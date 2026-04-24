import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QHeaderView,
    QDialog, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, btn_icon_red
from components.booking_modal import BookingModal
from components.dialogs import confirm, success
from components.filter_popover import FilterPopover
import utils.repository as repo


_STATUS_CYCLE = {"PENDING": "CONFIRMED", "CONFIRMED": "CANCELLED", "CANCELLED": "PENDING"}
_STATUS_COLORS = {
    "CONFIRMED": ("#22C55E", "rgba(34,197,94,.15)", "rgba(34,197,94,.3)"),
    "PENDING":   ("#F59E0B", "rgba(245,158,11,.15)", "rgba(245,158,11,.3)"),
    "CANCELLED": ("#EF4444", "rgba(239,68,68,.15)",  "rgba(239,68,68,.3)"),
}


class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")


def _status_badge(text, on_click=None):
    color, bg, border = _STATUS_COLORS.get(text, ("#9CA3AF", "rgba(156,163,175,.15)", "rgba(156,163,175,.3)"))
    btn = QPushButton(text)
    btn.setStyleSheet(
        f"font-weight:700;font-size:11px;padding:4px 10px;border-radius:12px;"
        f"background:{bg};color:{color};border:1px solid {border};"
        f"QPushButton:hover{{background:{border};}}"
    )
    btn.setCursor(Qt.PointingHandCursor)
    btn.setToolTip("Click to change status")
    if on_click:
        btn.clicked.connect(on_click)
    return btn


class BookingPage(QWidget):
    def __init__(self):
        super().__init__()
        db_rows = repo.get_all_bookings()
        self._bookings = db_rows if db_rows else [
            {"date": "Oct 24, 2026", "id": "BKG-001", "name": "TechCorp Inc.",  "pax": "150", "total": "₱ 45,000",  "status": "CONFIRMED"},
            {"date": "Oct 25, 2026", "id": "BKG-002", "name": "Smith Wedding",  "pax": "300", "total": "₱ 120,000", "status": "PENDING"},
            {"date": "Oct 26, 2026", "id": "BKG-003", "name": "Sarah's 18th",   "pax": "100", "total": "₱ 35,000",  "status": "CONFIRMED"},
            {"date": "Oct 28, 2026", "id": "BKG-004", "name": "Local NGO Meet", "pax": "60",  "total": "₱ 18,000",  "status": "CANCELLED"},
        ]
        self._active_filter = "All"
        self._filter_popover = None
        self._build_ui()

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
        layout.addLayout(header_row)

        table_card = AnimatedCard()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(24, 24, 24, 24)
        table_layout.setSpacing(16)

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

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["DATE", "CLIENT NAME", "PAX", "TOTAL AMOUNT", "STATUS", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        table_layout.addWidget(self.table)
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
        rows = data if data is not None else self._visible_bookings()
        self.table.setRowCount(0)
        for b in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 56)

            date_lbl = QLabel(
                f"<span style='font-weight:700;font-size:13px;'>{b['date']}</span>"
                f"<br><span style='color:#6B7280;font-size:11px;'>{b['id']}</span>"
            )
            date_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 0, date_lbl)

            name_lbl = QLabel(f"<span style='font-weight:700;font-size:13px;'>{b['name']}</span>")
            name_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 1, name_lbl)

            pax_lbl = QLabel(f"<span style='font-weight:600;color:#9CA3AF;font-size:13px;'>{b['pax']}</span>")
            pax_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 2, pax_lbl)

            amt_lbl = QLabel(f"<span style='font-weight:700;font-size:13px;'>{b['total']}</span>")
            amt_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 3, amt_lbl)

            bname = b["name"]
            status_btn = _status_badge(b["status"], on_click=lambda _, n=bname: self._cycle_status(n))
            self.table.setCellWidget(row, 4, status_btn)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setStyleSheet("border:none;background:transparent;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete booking")
            del_btn.clicked.connect(lambda _, n=bname: self._delete_booking(n))
            self.table.setCellWidget(row, 5, del_btn)

    def _cycle_status(self, name):
        for b in self._bookings:
            if b["name"] == name:
                next_s = _STATUS_CYCLE.get(b["status"], "PENDING")
                if not confirm(self, title="Update Status",
                               message=f"Change status of '{name}' to {next_s}?",
                               confirm_label="Update"):
                    return
                b["status"] = next_s
                if b.get("db_id"):
                    repo.update_booking_status(b["db_id"], b["status"])
                break
        self._populate_table()
        success(self, message="Booking status updated successfully.")

    def _delete_booking(self, name):
        if not confirm(self, title="Delete Booking",
                       message=f"Are you sure you want to delete booking for '{name}'? This cannot be undone.",
                       confirm_label="Delete", danger=True):
            return
        for b in self._bookings:
            if b["name"] == name and b.get("db_id"):
                repo.delete_booking(b["db_id"])
                break
        self._bookings = [b for b in self._bookings if b["name"] != name]
        self._populate_table()
        success(self, message="Booking deleted successfully.")

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
        success(self, message="Booking created successfully.")

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
        statuses = result.get("statuses", [])
        if not statuses or "All" in statuses:
            self._active_filter = "All"
        else:
            self._active_filter = statuses[0] if len(statuses) == 1 else statuses
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
