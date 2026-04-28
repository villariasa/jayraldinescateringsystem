from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QApplication
)
from PySide6.QtCore import Qt, QSize, QPoint, Signal, QTimer
from PySide6.QtGui import QColor

import utils.repository as repo


_PAGE_MAP = {
    "Booking":  1,
    "Customer": 2,
    "Invoice":  6,
    "Menu Item": 3,
    "Package":  3,
    "Kitchen":  5,
}

_TYPE_COLOR = {
    "Booking":   "#3B82F6",
    "Customer":  "#22C55E",
    "Invoice":   "#F59E0B",
    "Menu Item": "#A78BFA",
    "Package":   "#EC4899",
    "Kitchen":   "#F97316",
}


def _build_suggestions(query: str) -> list[dict]:
    q = query.lower().strip()
    if not q or len(q) < 2:
        return []

    results = []

    try:
        for c in repo.get_all_customers():
            name = c.get("name", "")
            if q in name.lower():
                results.append({
                    "type": "Customer",
                    "label": name,
                    "sub": c.get("contact", "") or c.get("email", ""),
                    "id": c.get("id"),
                })
    except Exception:
        pass

    try:
        for b in repo.get_all_bookings():
            ref  = b.get("booking_ref", "") or b.get("id", "")
            name = b.get("customer_name", "") or b.get("name", "")
            occ  = b.get("occasion", "")
            if q in str(ref).lower() or q in name.lower() or q in occ.lower():
                results.append({
                    "type": "Booking",
                    "label": f"{ref} — {name}",
                    "sub": occ or b.get("date", ""),
                    "id": b.get("id") or b.get("db_id"),
                    "ref": str(ref),
                })
    except Exception:
        pass

    try:
        for inv in repo.get_all_invoices():
            ref  = inv.get("invoice_ref", "") or inv.get("invoice", "")
            cust = inv.get("customer_name", "") or inv.get("customer", "")
            if q in str(ref).lower() or q in cust.lower():
                results.append({
                    "type": "Invoice",
                    "label": f"{ref} — {cust}",
                    "sub": f"₱{float(inv.get('total_amount', inv.get('amount', 0))):,.2f}  {inv.get('status', '')}",
                    "id": inv.get("id") or inv.get("db_id"),
                    "ref": str(ref),
                })
    except Exception:
        pass

    try:
        for item in repo.get_all_menu_items():
            name = item.get("item", "") or item.get("name", "")
            cat  = item.get("category", "")
            if q in name.lower() or q in cat.lower():
                results.append({
                    "type": "Menu Item",
                    "label": name,
                    "sub": f"{cat}  ₱{float(item.get('price', 0)):,.2f}",
                    "id": item.get("id"),
                })
    except Exception:
        pass

    try:
        for pkg in repo.get_all_packages():
            name = pkg.get("name", "")
            if q in name.lower():
                results.append({
                    "type": "Package",
                    "label": name,
                    "sub": f"₱{float(pkg.get('price_per_pax', 0)):,.2f}/pax  min {pkg.get('min_pax', 1)} pax",
                    "id": pkg.get("id"),
                })
    except Exception:
        pass

    return results[:30]


class SearchDropdown(QFrame):
    result_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFixedWidth(400)
        self.setObjectName("card")
        self._build_ui()
        self.hide()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._inner = QFrame()
        self._inner.setObjectName("card")
        self._inner.setStyleSheet("""
            QFrame#card {
                border: 1px solid #374151;
                border-radius: 10px;
            }
        """)
        inner_lay = QVBoxLayout(self._inner)
        inner_lay.setContentsMargins(0, 6, 0, 6)
        inner_lay.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setMaximumHeight(380)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_w = QWidget()
        self._list_w.setStyleSheet("background: transparent;")
        self._list_lay = QVBoxLayout(self._list_w)
        self._list_lay.setSpacing(0)
        self._list_lay.setContentsMargins(8, 0, 8, 0)

        self._scroll.setWidget(self._list_w)
        inner_lay.addWidget(self._scroll)

        lay.addWidget(self._inner)

    def update_results(self, query: str):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        suggestions = _build_suggestions(query)

        if not suggestions:
            lbl = QLabel("No results found")
            lbl.setStyleSheet("color: #6B7280; font-size: 12px; padding: 12px 8px;")
            lbl.setAlignment(Qt.AlignCenter)
            self._list_lay.addWidget(lbl)
            self.adjustSize()
            return

        grouped = {}
        for s in suggestions:
            grouped.setdefault(s["type"], []).append(s)

        for type_name, items in grouped.items():
            grp = QLabel(type_name.upper())
            grp.setStyleSheet(
                "color: #6B7280; font-size: 10px; font-weight: 700;"
                " letter-spacing: 1px; padding: 8px 4px 3px 4px;"
            )
            self._list_lay.addWidget(grp)

            for item in items:
                self._list_lay.addWidget(self._build_row(item))

        self._list_lay.addStretch()
        self.adjustSize()

    def _build_row(self, item: dict) -> QWidget:
        w = QWidget()
        w.setCursor(Qt.PointingHandCursor)
        color = _TYPE_COLOR.get(item["type"], "#9CA3AF")
        w.setStyleSheet(f"""
            QWidget {{
                border-radius: 6px;
                padding: 2px;
            }}
            QWidget:hover {{
                background: #1F2937;
            }}
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(6, 7, 6, 7)
        lay.setSpacing(10)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {color}; border-radius: 4px;")
        lay.addWidget(dot, alignment=Qt.AlignVCenter)

        text = QVBoxLayout()
        text.setSpacing(1)
        label_lbl = QLabel(item["label"])
        label_lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
        text.addWidget(label_lbl)
        if item.get("sub"):
            sub_lbl = QLabel(item["sub"])
            sub_lbl.setStyleSheet("font-size: 11px; color: #9CA3AF;")
            text.addWidget(sub_lbl)
        lay.addLayout(text, 1)

        type_badge = QLabel(item["type"])
        type_badge.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 600;"
            f" background: transparent; padding: 2px 6px;"
            f" border: 1px solid {color}; border-radius: 4px;"
        )
        lay.addWidget(type_badge, alignment=Qt.AlignVCenter)

        w.mousePressEvent = lambda e, d=item: self.result_selected.emit(d)
        return w

    def show_below(self, anchor: QWidget):
        parent = self.parent()
        if parent is None:
            return
        global_pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
        local = parent.mapFromGlobal(global_pos)
        x = min(local.x(), parent.width() - self.width() - 8)
        self.move(x, local.y())
        self.raise_()
        self.show()
