"""
Global search dropdown component for the topbar.

Provides a floating, theme-aware results panel that performs a fuzzy,
cross-entity search over customers, bookings, invoices, menu items and
packages. Searching runs off the UI thread (see :class:`_SearchWorker`) and is
debounced, so typing stays responsive. Results are scored, grouped by type and
rendered as clickable rows; selecting one emits :attr:`SearchDropdown.result_selected`
so the host window can navigate to the matching page.
"""
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QThread, QObject
from PySide6.QtGui import QKeyEvent

import utils.repository as repo
from utils.theme import ThemeManager


def _palette() -> dict:
    """Return the color palette dict for the dropdown, keyed by role
    (card_bg, text, muted, row_hover, etc.), selecting dark or light values
    based on the active theme."""
    if ThemeManager().is_dark():
        return {
            "card_bg":     "#111827",
            "card_border": "#374151",
            "text":        "#F9FAFB",
            "muted":       "#6B7280",
            "faint":       "#4B5563",
            "row_hover":   "#1F2937",
        }
    return {
        "card_bg":     "#FFFFFF",
        "card_border": "#D8DFEA",
        "text":        "#101828",
        "muted":       "#5B6B84",
        "faint":       "#7A879E",
        "row_hover":   "#F3F5F9",
    }

# Result type -> destination page index used by the host window to route a
# selected result to the correct page.
_PAGE_MAP = {
    "Booking":   1,
    "Customer":  2,
    "Invoice":   6,
    "Menu Item": 3,
    "Package":   3,
    "Kitchen":   5,
}

# Accent color per result type, used for the leading dot and the meta badge.
_TYPE_COLOR = {
    "Booking":   "#3B82F6",
    "Customer":  "#22C55E",
    "Invoice":   "#F59E0B",
    "Menu Item": "#A78BFA",
    "Package":   "#EC4899",
    "Kitchen":   "#F97316",
}

# Canonical display/grouping order for result types (also used as a tiebreaker
# when sorting equally-scored results).
_TYPE_ORDER = ["Booking", "Customer", "Invoice", "Menu Item", "Package", "Kitchen"]


def _score(text: str, q: str) -> int:
    """Return a relevance score (0-100) for how well ``text`` matches query
    ``q`` (``q`` is expected already lowercased). Higher is better: exact match
    (100) > prefix (80) > substring (60) > all whitespace-split tokens present
    (40) > no match (0). Used to rank search candidates."""
    t = text.lower()
    if t == q:
        return 100
    if t.startswith(q):
        return 80
    if q in t:
        return 60
    # Fallback: every word of the query appears somewhere in the text.
    parts = q.split()
    if all(p in t for p in parts):
        return 40
    return 0


def _build_suggestions(query: str) -> list[dict]:
    """Build and rank cross-entity search suggestions for ``query``.

    Queries the repository for customers, bookings, invoices, menu items and
    packages, scoring each against the (lowercased, trimmed) query on its most
    relevant fields. Each match becomes a result dict with keys such as
    ``type``, ``label``, ``sub``, ``meta``, ``id`` and ``score``. Returns an
    empty list for queries shorter than 2 chars. Every repository lookup is
    wrapped in try/except so a failure in one entity type never aborts the
    others. Results are sorted by descending score then type order and capped
    at 40. Runs on a worker thread — must not touch Qt widgets.
    """
    q = query.lower().strip()
    if not q or len(q) < 2:
        return []

    results = []

    # --- Customers: match on name / contact / email ---
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

    # --- Bookings: match on reference / customer name / occasion ---
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

    # --- Invoices: match on reference / customer; show formatted total ---
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

    # --- Menu items: match on name / category; show formatted price ---
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

    # --- Packages: match on name; show per-set price ---
    try:
        for pkg in repo.get_all_packages():
            name = pkg.get("name", "")
            score = _score(name, q)
            if score:
                results.append({
                    "type":  "Package",
                    "label": name,
                    "sub":   "Min 1 Set (4 dishes good for 22 person)",
                    "meta":  f"₱{float(pkg.get('price_per_pax', 0)):,.2f}/set",
                    "id":    pkg.get("id"),
                    "score": score,
                })
    except Exception:
        pass

    # Best score first; ties broken by canonical type order (unknown -> last).
    results.sort(key=lambda x: (-x["score"], _TYPE_ORDER.index(x["type"]) if x["type"] in _TYPE_ORDER else 99))
    return results[:40]


class _SearchWorker(QObject):
    """QObject worker that runs :func:`_build_suggestions` off the UI thread.

    Moved onto a QThread by the dropdown; emits :attr:`finished` with the list
    of result dicts when the (blocking) search completes.
    """
    finished = Signal(list)

    def __init__(self, query: str):
        """Store the query string to search for when :meth:`run` is invoked."""
        super().__init__()
        self._query = query

    def run(self):
        """Perform the search on the worker thread and emit ``finished`` with
        the results list. Connected to the thread's ``started`` signal."""
        results = _build_suggestions(self._query)
        self.finished.emit(results)


class SearchDropdown(QFrame):
    """Floating results panel for the global topbar search.

    Debounces incoming queries, runs the search on a background thread, and
    renders grouped, keyboard-navigable result rows. Emits
    :attr:`result_selected` (with the chosen result dict) when the user clicks
    or presses Enter on a row.
    """
    result_selected = Signal(dict)

    def __init__(self, parent=None):
        """Create the frameless, translucent dropdown frame and initialize its
        debounce timer and internal state (row list, selection index, worker
        thread handle), build the UI, and start hidden."""
        super().__init__(parent)
        # Frameless translucent child window so it floats over content without
        # its own OS title bar / opaque background.
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setFixedWidth(480)
        self._rows: list[QWidget] = []       # currently rendered result row widgets
        self._selected_idx: int = -1         # keyboard-highlighted row (-1 = none)
        self._thread: QThread | None = None  # active search worker thread
        # 220ms debounce so a burst of keystrokes triggers only one search.
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(220)
        self._debounce.timeout.connect(self._fetch)
        self._pending_query = ""
        self._build_ui()
        self.hide()

    def _build_ui(self):
        """Construct the dropdown's widget tree: rounded card, a 'Searching...'
        label, a scrollable results list container, and a footer hint line,
        then apply the current theme."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)

        self._card = QFrame()
        self._card.setObjectName("searchCard")
        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(0, 6, 0, 6)
        card_lay.setSpacing(0)

        self._loading_lbl = QLabel("  Searching...")
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
        self._footer.hide()
        card_lay.addWidget(self._footer)

        outer.addWidget(self._card)
        self._apply_theme()

    def _apply_theme(self):
        """Restyle the card, loading label and footer using the current theme
        palette. Called on build and each time the dropdown is shown."""
        p = _palette()
        self._card.setStyleSheet(f"""
            QFrame#searchCard {{
                background: {p['card_bg']};
                border: 1px solid {p['card_border']};
                border-radius: 12px;
            }}
        """)
        self._loading_lbl.setStyleSheet(f"color: {p['muted']}; font-size: 12px; padding: 10px 16px;")
        self._footer.setStyleSheet(f"color: {p['faint']}; font-size: 10px; padding: 4px 16px 6px;")

    def search(self, query: str):
        """Public entry point called as the user types. Stores the query and
        (re)starts the debounce timer; queries under 2 non-space chars hide the
        dropdown immediately instead of searching."""
        self._pending_query = query
        self._debounce.stop()
        if not query.strip() or len(query.strip()) < 2:
            self.hide()
            return
        self._loading_lbl.show()
        self._debounce.start()

    def _stop_thread(self):
        """Stop and tear down any in-flight search worker thread, waiting
        briefly for it to finish, and drop references so a new search can
        start cleanly. Safe to call when no thread is running."""
        if self._thread is not None:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(300)
            except Exception:
                pass
            self._thread = None
        self._worker = None

    def hideEvent(self, event):
        """Ensure any running search thread is stopped whenever the dropdown is
        hidden, then defer to the base handler."""
        self._stop_thread()
        super().hideEvent(event)

    def _fetch(self):
        """Debounce callback: spin up a fresh QThread + :class:`_SearchWorker`
        for the pending query, wiring signals so results are delivered to
        :meth:`_on_results` and the thread/worker are cleaned up on
        completion."""
        self._stop_thread()
        self._thread = QThread()
        self._worker = _SearchWorker(self._pending_query)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_results)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_results(self, results: list):
        """Slot receiving search results on the UI thread. Clears the previous
        rows, then either shows a 'No results found' placeholder or renders the
        results grouped by type (in ``_TYPE_ORDER``) with a footer summarizing
        the count and keyboard hints, finally resizing to fit."""
        self._loading_lbl.hide()
        self._clear_list()
        self._rows = []
        self._selected_idx = -1

        if not results:
            lbl = QLabel("No results found")
            lbl.setStyleSheet(f"color: {_palette()['muted']}; font-size: 12px; padding: 14px 8px;")
            lbl.setAlignment(Qt.AlignCenter)
            self._list_lay.addWidget(lbl)
            self._footer.hide()
        else:
            # Bucket results by type so each type gets its own header section.
            grouped: dict[str, list] = {}
            for r in results:
                grouped.setdefault(r["type"], []).append(r)

            # Render sections in canonical order, skipping empty buckets.
            for type_name in _TYPE_ORDER:
                items = grouped.get(type_name)
                if not items:
                    continue
                grp = QLabel(f"  {type_name.upper()}")
                grp.setStyleSheet(
                    f"color: {_palette()['faint']}; font-size: 10px; font-weight: 700;"
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
        """Remove and schedule deletion of every widget currently in the
        results list layout (headers, rows, placeholder), leaving it empty."""
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build_row(self, item: dict) -> QWidget:
        """Build and return a clickable row widget for a single result ``item``.

        Lays out a type-colored dot, the primary label, an optional subtitle,
        and an optional meta badge. Stashes the result dict on the widget via
        ``result_data`` (read back for keyboard selection) and binds its
        mouse-press to :meth:`_select`.
        """
        p = _palette()
        color = _TYPE_COLOR.get(item["type"], "#9CA3AF")
        w = QWidget()
        w.setProperty("result_data", item)
        w.setCursor(Qt.PointingHandCursor)
        w.setStyleSheet(f"""
            QWidget {{ border-radius: 7px; background: transparent; }}
            QWidget:hover {{ background: {p['row_hover']}; }}
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
        label_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {p['text']}; background: transparent;")
        label_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        text_col.addWidget(label_lbl)

        if item.get("sub"):
            sub_lbl = QLabel(item["sub"])
            sub_lbl.setStyleSheet(f"font-size: 11px; color: {p['muted']}; background: transparent;")
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

        # Clicking anywhere on the row selects that result (default arg binds
        # the current item so the closure isn't affected by the loop variable).
        w.mousePressEvent = lambda e, d=item: self._select(d)
        return w

    def _select(self, item: dict):
        """Finalize a selection: hide the dropdown and emit
        :attr:`result_selected` with the chosen result dict."""
        self.hide()
        self.result_selected.emit(item)

    def _highlight_row(self, idx: int):
        """Visually highlight the row at ``idx`` (keyboard selection) and clear
        the highlight on all others, scrolling the selected row into view."""
        hover = _palette()["row_hover"]
        for i, row in enumerate(self._rows):
            if i == idx:
                row.setStyleSheet(f"QWidget {{ border-radius: 7px; background: {hover}; }}")
            else:
                row.setStyleSheet(f"QWidget {{ border-radius: 7px; background: transparent; }} QWidget:hover {{ background: {hover}; }}")

        if 0 <= idx < len(self._rows):
            self._scroll.ensureWidgetVisible(self._rows[idx])

    def handle_key(self, event: QKeyEvent) -> bool:
        """Handle keyboard navigation forwarded from the search input.

        Down/Up move the highlighted row (clamped to range), Enter selects the
        highlighted result, Escape hides the dropdown. Returns True if the key
        was consumed here, False to let the caller handle it.
        """
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
        """Position and show the dropdown just beneath ``anchor`` (typically the
        search input), re-applying the theme and raising it above siblings.
        Uses the anchor's global coordinates plus a small vertical gap."""
        self._apply_theme()
        global_pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 6))
        self.move(global_pos)
        self.raise_()
        self.show()
