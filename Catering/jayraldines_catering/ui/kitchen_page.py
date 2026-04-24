from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QSize

from utils.icons import btn_icon_primary, get_icon
from components.dialogs import confirm, success
import utils.repository as repo


_SAMPLE_ORDERS = [
    {"id": "ORD-001", "client": "Maria Santos",  "event": "Birthday Party",    "pax": 80,  "items": "Lechon, Kare-Kare, Buko Pandan",   "status": "Queued"},
    {"id": "ORD-002", "client": "TechCorp Inc.", "event": "Corporate Dinner",  "pax": 150, "items": "Chicken Inasal, Pancit, Leche Flan", "status": "In Progress"},
    {"id": "ORD-003", "client": "Cruz Family",   "event": "Debut",             "pax": 200, "items": "Lechon, Kare-Kare, Chopsuey",       "status": "Ready"},
    {"id": "ORD-004", "client": "Smith Wedding", "event": "Wedding Reception",  "pax": 300, "items": "Full Package Premium",              "status": "Queued"},
]

_STATUSES    = ["Queued", "Preparing", "In Progress", "Ready", "Delivered", "Cancelled"]
_NEXT_STATUS = {"Queued": "Preparing", "Preparing": "In Progress", "In Progress": "Ready", "Ready": "Delivered"}
_COL_COLORS  = {
    "Queued":      "#F59E0B",
    "Preparing":   "#A855F7",
    "In Progress": "#3B82F6",
    "Ready":       "#22C55E",
    "Delivered":   "#10B981",
    "Cancelled":   "#EF4444",
}


class KitchenPage(QWidget):
    def __init__(self):
        super().__init__()
        db_rows = repo.get_all_orders()
        self._orders = db_rows if db_rows else list(_SAMPLE_ORDERS)
        self._build_ui()
        self._refresh_columns()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Kitchen")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        self._cols_layout = QHBoxLayout()
        self._cols_layout.setSpacing(16)

        _DISPLAY_COLS = ["Queued", "Preparing", "In Progress", "Ready", "Delivered", "Cancelled"]
        self._col_inner = {}
        for status in _DISPLAY_COLS:
            color = _COL_COLORS[status]
            col_frame = QFrame()
            col_frame.setObjectName("card")
            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(16, 16, 16, 16)
            col_layout.setSpacing(12)

            col_title = QLabel(status)
            col_title.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 13px;")
            col_layout.addWidget(col_title)

            divider = QFrame()
            divider.setObjectName("divider")
            col_layout.addWidget(divider)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet("background: transparent;")

            inner = QWidget()
            inner.setStyleSheet("background: transparent;")
            inner_lay = QVBoxLayout(inner)
            inner_lay.setContentsMargins(0, 0, 0, 0)
            inner_lay.setSpacing(10)
            inner_lay.addStretch()

            scroll.setWidget(inner)
            col_layout.addWidget(scroll)

            self._col_inner[status] = inner_lay
            self._cols_layout.addWidget(col_frame)

        root.addLayout(self._cols_layout)

    def _refresh_columns(self):
        for status, lay in self._col_inner.items():
            while lay.count() > 1:
                item = lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        for order in self._orders:
            card = self._build_order_card(order)
            lay = self._col_inner.get(order["status"])
            if lay:
                lay.insertWidget(lay.count() - 1, card)

    def _build_order_card(self, order):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #1F2937; border-radius: 10px; border: 1px solid #374151; }"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(6)

        id_lbl = QLabel(order["id"])
        id_lbl.setStyleSheet("font-weight: 700; color: #F9FAFB; font-size: 13px;")
        lay.addWidget(id_lbl)

        client_lbl = QLabel(order["client"])
        client_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        lay.addWidget(client_lbl)

        event_lbl = QLabel(order["event"])
        event_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")
        lay.addWidget(event_lbl)

        pax_lbl = QLabel(f"{order['pax']} pax")
        pax_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")
        lay.addWidget(pax_lbl)

        items_lbl = QLabel(order["items"])
        items_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        items_lbl.setWordWrap(True)
        lay.addWidget(items_lbl)

        next_s = _NEXT_STATUS.get(order["status"])
        status = order["status"]
        if next_s:
            if next_s == "Delivered":
                btn = QPushButton("  Mark Delivered")
                btn.setObjectName("primaryButton")
            else:
                btn = QPushButton(f"  Move to {next_s}")
                btn.setObjectName("primaryButton")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, o=order: self._advance_order(o))
            lay.addWidget(btn)

        if status not in ("Delivered", "Cancelled", "Done"):
            cancel_btn = QPushButton("  Cancel")
            cancel_btn.setObjectName("dangerButton")
            cancel_btn.setFixedHeight(30)
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.clicked.connect(lambda checked=False, o=order: self._cancel_order(o))
            lay.addWidget(cancel_btn)

        if status in ("Delivered", "Cancelled"):
            done_btn = QPushButton("  Remove")
            done_btn.setObjectName("secondaryButton")
            done_btn.setFixedHeight(30)
            done_btn.setCursor(Qt.PointingHandCursor)
            done_btn.clicked.connect(lambda checked=False, o=order: self._remove_order(o))
            lay.addWidget(done_btn)

        return card

    def _advance_order(self, order):
        next_s = _NEXT_STATUS.get(order["status"])
        if next_s:
            order["status"] = next_s
            if order.get("db_id"):
                repo.update_order_status(order["db_id"], next_s)
            self._refresh_columns()
            if next_s == "Delivered":
                success(self, message=f"Order '{order['id']}' marked as Delivered.")

    def _cancel_order(self, order):
        if not confirm(self, title="Cancel Order",
                       message=f"Are you sure you want to cancel order '{order['id']}' for {order['client']}?",
                       confirm_label="Cancel Order", danger=True):
            return
        order["status"] = "Cancelled"
        if order.get("db_id"):
            repo.update_order_status(order["db_id"], "Cancelled")
        self._refresh_columns()
        success(self, message=f"Order '{order['id']}' has been cancelled.")

    def _remove_order(self, order):
        if not confirm(self, title="Remove Order",
                       message=f"Remove order '{order['id']}' from the board?",
                       confirm_label="Remove"):
            return
        if order in self._orders:
            if order.get("db_id") and order["status"] not in ("Delivered", "Cancelled"):
                repo.mark_order_done(order["db_id"])
            self._orders.remove(order)
            self._refresh_columns()

    def filter_search(self, text):
        q = text.lower()
        orig = self._orders
        self._orders = [o for o in orig if q in o["client"].lower() or q in o["id"].lower() or q in o["event"].lower()]
        self._refresh_columns()
        self._orders = orig
