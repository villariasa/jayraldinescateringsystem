from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QSize

from utils.icons import btn_icon_primary, get_icon


_SAMPLE_ORDERS = [
    {"id": "ORD-001", "client": "Maria Santos",  "event": "Birthday Party",    "pax": 80,  "items": "Lechon, Kare-Kare, Buko Pandan",   "status": "Queued"},
    {"id": "ORD-002", "client": "TechCorp Inc.", "event": "Corporate Dinner",  "pax": 150, "items": "Chicken Inasal, Pancit, Leche Flan", "status": "In Progress"},
    {"id": "ORD-003", "client": "Cruz Family",   "event": "Debut",             "pax": 200, "items": "Lechon, Kare-Kare, Chopsuey",       "status": "Ready"},
    {"id": "ORD-004", "client": "Smith Wedding", "event": "Wedding Reception",  "pax": 300, "items": "Full Package Premium",              "status": "Queued"},
]

_STATUSES   = ["Queued", "In Progress", "Ready"]
_NEXT_STATUS = {"Queued": "In Progress", "In Progress": "Ready", "Ready": "Done"}
_COL_COLORS  = {"Queued": "#F59E0B", "In Progress": "#3B82F6", "Ready": "#22C55E"}


class KitchenPage(QWidget):
    def __init__(self):
        super().__init__()
        self._orders = list(_SAMPLE_ORDERS)
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

        self._col_inner = {}
        for status, color in _COL_COLORS.items():
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
        if next_s and next_s != "Done":
            btn = QPushButton(f"  Move to {next_s}")
            btn.setObjectName("primaryButton")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, o=order: self._advance_order(o))
            lay.addWidget(btn)
        elif next_s == "Done":
            btn = QPushButton("  Mark Done")
            btn.setObjectName("secondaryButton")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, o=order: self._remove_order(o))
            lay.addWidget(btn)

        return card

    def _advance_order(self, order):
        next_s = _NEXT_STATUS.get(order["status"])
        if next_s and next_s != "Done":
            order["status"] = next_s
            self._refresh_columns()

    def _remove_order(self, order):
        if order in self._orders:
            self._orders.remove(order)
            self._refresh_columns()

    def filter_search(self, text):
        q = text.lower()
        orig = self._orders
        self._orders = [o for o in orig if q in o["client"].lower() or q in o["id"].lower() or q in o["event"].lower()]
        self._refresh_columns()
        self._orders = orig
