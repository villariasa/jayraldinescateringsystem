from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QThread, QObject
from PySide6.QtGui import QKeyEvent

import utils.repository as repo

_PAGE_MAP = {
    "Booking":   1,
    "Customer":  2,
    "Invoice":   6,
    "Menu Item": 3,
    "Package":   3,
    "Kitchen":   5,
}

_TYPE_COLOR = {
    "Booking":   "#3B82F6",
    "Customer":  "#22C55E",
    "Invoice":   "#F59E0B",
    "Menu Item": "#A78BFA",
    "Package":   "#EC4899",
    "Kitchen":   "#F97316",
}

_TYPE_ORDER = ["Booking", "Customer", "Invoice", "Menu Item", "Package", "Kitchen"]


def _score(text: str, q: str) -> int:
    t = text.lower()
    if t == q:
        return 100
    if t.startswith(q):
        return 80
    if q in t:
        return 60
    parts = q.split()
    if all(p in t for p in parts):
        return 40
    return 0


def _build_suggestions(query: str) -> list[dict]:
    q = query.lower().strip()
    if not q or len(q) < 2:
        return []

    results = []

    try:
        for c in repo.get_all_customers():
            name    = c.get("name", "")
            contact = c.get("contact", "") or ""
            email   = c.get("email", "") or ""
            score   = max(_score(name, q), _score(contact, q), _score(email, q))
            if score:
                results.append({
                    "type":  "Customer",
                    "label": name,
                    "sub":   contact or email,
                    "meta":  c.get("loyalty_tier", ""),
                    "id":    c.get("id"),
                    "score": score,
                })
    except Exception:
        pass

    try:
        for b in repo.get_all_bookings():
            ref  = str(b.get("booking_ref", "") or b.get("id", ""))
            name = b.get("customer_name", "") or b.get("name", "")
            occ  = b.get("occasion", "")
            score = max(_score(ref, q), _score(name, q), _score(occ, q))
            if score:
                results.append({
                    "type":  "Booking",
                    "label": f"{ref} — {name}",
                    "sub":   occ,
                    "meta":  b.get("status", ""),
                    "id":    b.get("id") or b.get("db_id"),
                    "ref":   ref,
                    "score": score,
                })
    except Exception:
        pass

    try:
        for inv in repo.get_all_invoices():
            ref  = str(inv.get("invoice_ref", "") or inv.get("invoice", ""))
            cust = inv.get("customer_name", "") or inv.get("customer", "")
            score = max(_score(ref, q), _score(cust, q))
            if score:
                total = float(inv.get("total_amount", inv.get("amount", 0)))
                results.append({
                    "type":  "Invoice",
                    "label": f"{ref} — {cust}",
                    "sub":   f"₱{total:,.2f}",
                    "meta":  inv.get("status", ""),
                    "id":    inv.get("id") or inv.get("db_id"),
                    "ref":   ref,
                    "score": score,
                })
    except Exception:
        pass

    try:
        for item in repo.get_all_menu_items():
            name = item.get("item", "") or item.get("name", "")
            cat  = item.get("category", "")
            score = max(_score(name, q), _score(cat, q))
            if score:
                results.append({
                    "type":  "Menu Item",
                    "label": name,
                    "sub":   cat,
                    "meta":  f"₱{float(item.get('price', 0)):,.2f}",
                    "id":    item.get("id"),
                    "score": score,
                })
    except Exception:
        pass

    try:
        for pkg in repo.get_all_packages():
            name = pkg.get("name", "")
            score = _score(name, q)
            if score:
                results.append({
                    "type":  "Package",
                    "label": name,
                    "sub":   f"Min {pkg.get('min_pax', 1)} pax",
                    "meta":  f"₱{float(pkg.get('price_per_pax', 0)):,.2f}/pax",
                    "id":    pkg.get("id"),
                    "score": score,
                })
    except Exception:
        pass

    results.sort(key=lambda x: (-x["score"], _TYPE_ORDER.index(x["type"]) if x["type"] in _TYPE_ORDER else 99))
    return results[:40]


class _SearchWorker(QObject):
    finished = Signal(list)

    def __init__(self, query: str):
        super().__init__()
        self._query = query

    def run(self):
        results = _build_suggestions(self._query)
        self.finished.emit(results)


class SearchDropdown(QFrame):
    result_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(480)
        self._rows: list[QWidget] = []
        self._selected_idx: int = -1
        self._thread: QThread | None = None
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(220)
        self._debounce.timeout.connect(self._fetch)
        self._pending_query = ""
        self._build_ui()
        self.hide()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)

        self._card = QFrame()
        self._card.setObjectName("searchCard")
        self._card.setStyleSheet("""
            QFrame#searchCard {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 12px;
            }
        """)
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(0, 6, 0, 6)
        card_lay.setSpacing(0)

        self._loading_lbl = QLabel("  Searching...")
        self._loading_lbl.setStyleSheet("color: #6B7280; font-size: 12px; padding: 10px 16px;")
        self._loading_lbl.hide()
        card_lay.addWidget(self._loading_lbl)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        self._scroll.setMaximumHeight(420)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_w = QWidget()
        self._list_w.setStyleSheet("background: transparent;")
        self._list_lay = QVBoxLayout(self._list_w)
        self._list_lay.setSpacing(1)
        self._list_lay.setContentsMargins(8, 0, 8, 0)

        self._scroll.setWidget(self._list_w)
        card_lay.addWidget(self._scroll)

        self._footer = QLabel()
        self._footer.setStyleSheet("color: #4B5563; font-size: 10px; padding: 4px 16px 6px;")
        self._footer.hide()
        card_lay.addWidget(self._footer)

        outer.addWidget(self._card)

    def search(self, query: str):
        self._pending_query = query
        self._debounce.stop()
        if not query.strip() or len(query.strip()) < 2:
            self.hide()
            return
        self._loading_lbl.show()
        self._debounce.start()

    def _fetch(self):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(200)

        self._thread = QThread()
        self._worker = _SearchWorker(self._pending_query)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_results)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_results(self, results: list):
        self._loading_lbl.hide()
        self._clear_list()
        self._rows = []
        self._selected_idx = -1

        if not results:
            lbl = QLabel("No results found")
            lbl.setStyleSheet("color: #6B7280; font-size: 12px; padding: 14px 8px;")
            lbl.setAlignment(Qt.AlignCenter)
            self._list_lay.addWidget(lbl)
            self._footer.hide()
        else:
            grouped: dict[str, list] = {}
            for r in results:
                grouped.setdefault(r["type"], []).append(r)

            for type_name in _TYPE_ORDER:
                items = grouped.get(type_name)
                if not items:
                    continue
                grp = QLabel(f"  {type_name.upper()}")
                grp.setStyleSheet(
                    "color: #4B5563; font-size: 10px; font-weight: 700;"
                    " letter-spacing: 1px; padding: 8px 4px 3px 4px;"
                    " background: transparent;"
                )
                self._list_lay.addWidget(grp)
                for item in items:
                    row = self._build_row(item)
                    self._list_lay.addWidget(row)
                    self._rows.append(row)

            self._list_lay.addStretch()
            total = len(results)
            self._footer.setText(f"  {total} result{'s' if total != 1 else ''} — ↑↓ navigate  Enter select  Esc close")
            self._footer.show()

        self.adjustSize()

    def _clear_list(self):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build_row(self, item: dict) -> QWidget:
        color = _TYPE_COLOR.get(item["type"], "#9CA3AF")
        w = QWidget()
        w.setProperty("result_data", item)
        w.setCursor(Qt.PointingHandCursor)
        w.setStyleSheet("""
            QWidget { border-radius: 7px; background: transparent; }
            QWidget:hover { background: #1F2937; }
        """)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 7, 8, 7)
        lay.setSpacing(10)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {color}; border-radius: 4px; border: none;")
        lay.addWidget(dot, alignment=Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        label_lbl = QLabel(item["label"])
        label_lbl.setStyleSheet("font-size: 13px; font-weight: 600; background: transparent;")
        label_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        text_col.addWidget(label_lbl)

        if item.get("sub"):
            sub_lbl = QLabel(item["sub"])
            sub_lbl.setStyleSheet("font-size: 11px; color: #6B7280; background: transparent;")
            text_col.addWidget(sub_lbl)

        lay.addLayout(text_col, 1)

        if item.get("meta"):
            meta_lbl = QLabel(item["meta"])
            meta_lbl.setStyleSheet(
                f"color: {color}; font-size: 10px; font-weight: 600;"
                f" border: 1px solid {color}; border-radius: 4px;"
                f" padding: 1px 5px; background: transparent;"
            )
            lay.addWidget(meta_lbl, alignment=Qt.AlignVCenter)

        w.mousePressEvent = lambda e, d=item: self._select(d)
        return w

    def _select(self, item: dict):
        self.hide()
        self.result_selected.emit(item)

    def _highlight_row(self, idx: int):
        for i, row in enumerate(self._rows):
            if i == idx:
                row.setStyleSheet("QWidget { border-radius: 7px; background: #1F2937; }")
            else:
                row.setStyleSheet("QWidget { border-radius: 7px; background: transparent; } QWidget:hover { background: #1F2937; }")

        if 0 <= idx < len(self._rows):
            self._scroll.ensureWidgetVisible(self._rows[idx])

    def handle_key(self, event: QKeyEvent) -> bool:
        key = event.key()
        if key == Qt.Key_Down:
            self._selected_idx = min(self._selected_idx + 1, len(self._rows) - 1)
            self._highlight_row(self._selected_idx)
            return True
        if key == Qt.Key_Up:
            self._selected_idx = max(self._selected_idx - 1, 0)
            self._highlight_row(self._selected_idx)
            return True
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if 0 <= self._selected_idx < len(self._rows):
                data = self._rows[self._selected_idx].property("result_data")
                if data:
                    self._select(data)
            return True
        if key == Qt.Key_Escape:
            self.hide()
            return True
        return False

    def show_below(self, anchor: QWidget):
        global_pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 6))
        self.move(global_pos)
        self.raise_()
        self.show()
