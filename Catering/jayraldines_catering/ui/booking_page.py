from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QHeaderView,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QVariantAnimation, QSize
from PySide6.QtGui import QColor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted
from components.booking_modal import BookingModal


class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 6)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(self.shadow)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(200)
        self._anim.valueChanged.connect(lambda v: (
            self.shadow.setBlurRadius(20 + int(v)),
            self.shadow.setOffset(0, 6 + int(v / 2))
        ))

    def enterEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(0); self._anim.setEndValue(12); self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop(); self._anim.setStartValue(12); self._anim.setEndValue(0); self._anim.start()
        super().leaveEvent(e)


def _status_badge(text):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(8, 0, 8, 0)
    lay.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    styles = {
        "CONFIRMED": "background:rgba(34,197,94,.15);color:#22C55E;border:1px solid rgba(34,197,94,.3);",
        "PENDING":   "background:rgba(245,158,11,.15);color:#F59E0B;border:1px solid rgba(245,158,11,.3);",
        "CANCELLED": "background:rgba(239,68,68,.15);color:#EF4444;border:1px solid rgba(239,68,68,.3);",
    }
    base = "font-weight:700;font-size:11px;padding:4px 10px;border-radius:12px;"
    lbl.setStyleSheet(base + styles.get(text, styles["PENDING"]))
    lay.addWidget(lbl)
    return w


class BookingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._bookings = [
            {"date": "Oct 24, 2026", "id": "BKG-001", "name": "TechCorp Inc.",   "pax": "150", "total": "₱ 45,000",  "status": "CONFIRMED"},
            {"date": "Oct 25, 2026", "id": "BKG-002", "name": "Smith Wedding",   "pax": "300", "total": "₱ 120,000", "status": "PENDING"},
            {"date": "Oct 26, 2026", "id": "BKG-003", "name": "Sarah's 18th",    "pax": "100", "total": "₱ 35,000",  "status": "CONFIRMED"},
            {"date": "Oct 28, 2026", "id": "BKG-004", "name": "Local NGO Meet",  "pax": "60",  "total": "₱ 18,000",  "status": "CANCELLED"},
        ]
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
        btn_filter = QPushButton("  Filter")
        btn_filter.setObjectName("secondaryButton")
        btn_filter.setIcon(btn_icon_secondary("filter"))
        btn_filter.setIconSize(QSize(14, 14))
        btn_export = QPushButton("  Export")
        btn_export.setObjectName("secondaryButton")
        btn_export.setIcon(btn_icon_secondary("export"))
        btn_export.setIconSize(QSize(14, 14))
        t_head.addWidget(btn_filter)
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

    def _populate_table(self):
        self.table.setRowCount(0)
        for b in self._bookings:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 60)

            date_lbl = QLabel(
                f"<span style='font-weight:700;color:#F9FAFB;font-size:13px;'>{b['date']}</span>"
                f"<br><span style='color:#6B7280;font-size:11px;'>{b['id']}</span>"
            )
            date_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 0, date_lbl)

            name_lbl = QLabel(f"<span style='font-weight:700;color:#F9FAFB;font-size:13px;'>{b['name']}</span>")
            name_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 1, name_lbl)

            pax_lbl = QLabel(f"<span style='font-weight:600;color:#9CA3AF;font-size:13px;'>{b['pax']}</span>")
            pax_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 2, pax_lbl)

            amt_lbl = QLabel(f"<span style='font-weight:700;color:#F9FAFB;font-size:13px;'>{b['total']}</span>")
            amt_lbl.setContentsMargins(8, 0, 0, 0)
            self.table.setCellWidget(row, 3, amt_lbl)

            self.table.setCellWidget(row, 4, _status_badge(b["status"]))

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_muted("trash"))
            del_btn.setIconSize(QSize(15, 15))
            del_btn.setStyleSheet("border:none;background:transparent;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete booking")
            bname = b["name"]
            del_btn.clicked.connect(lambda _, n=bname: self._delete_booking(n))
            self.table.setCellWidget(row, 5, del_btn)

    def _delete_booking(self, name):
        self._bookings = [b for b in self._bookings if b["name"] != name]
        self._populate_table()

    def _open_modal(self):
        modal = BookingModal(self)
        modal.booking_saved.connect(self._add_booking)
        modal.exec()

    def _add_booking(self, data):
        import time as _time
        bkg_id = f"BKG-{len(self._bookings) + 1:03d}"
        self._bookings.append({
            "date":   data["date"],
            "id":     bkg_id,
            "name":   data["name"],
            "pax":    str(data["pax"]),
            "total":  f"₱ {data['total']:,}",
            "status": data["status"],
        })
        self._populate_table()
