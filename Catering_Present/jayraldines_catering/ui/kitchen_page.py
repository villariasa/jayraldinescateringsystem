"""Kitchen page: a kanban-style board that tracks catering orders through
their preparation lifecycle (Queued -> Preparing -> In Progress -> Ready ->
Delivered, plus a Cancelled column).

Each status is rendered as a resizable column in a horizontal QSplitter, and
every order becomes a card the user can advance/return/cancel/remove, plus
manage a per-order checklist of kitchen tasks. Data is loaded asynchronously
(via DataLoader) from the repository, which first syncs kitchen orders from
the underlying bookings table. The board also live-refreshes in response to
app-wide signals (kitchen/booking updates, sync completion, generic data
changes) and supports a text search that filters cards in place.

Module-level helpers below centralize theme-aware styling so light/dark mode
is handled consistently across all cards, inputs, and checkboxes.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QCheckBox, QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, QSize

from utils.icons import btn_icon_primary, get_icon
from utils.theme import ThemeManager
from components.dialogs import confirm, success
import utils.repository as repo
from utils.session import get_actor
from utils.signals import app_events
from utils.data_loader import DataLoader
from utils.text_highlight import highlight_html


# Full ordered set of order statuses (also the board's column order).
_STATUSES    = ["Queued", "Preparing", "In Progress", "Ready", "Delivered", "Cancelled"]
# Forward transitions: maps a status to the next stage when "advancing" an order.
# Note there is no entry for "Delivered"/"Cancelled" (they are terminal).
_NEXT_STATUS = {"Queued": "Preparing", "Preparing": "In Progress", "In Progress": "Ready", "Ready": "Delivered"}
# Reverse transitions: maps a status to the previous stage when "returning" an order.
_PREV_STATUS = {"Preparing": "Queued", "In Progress": "Preparing", "Ready": "In Progress", "Delivered": "Ready"}
# Accent color per status column / card, used for headers and badges.
_COL_COLORS  = {
    "Queued":      "#F59E0B",
    "Preparing":   "#A855F7",
    "In Progress": "#3B82F6",
    "Ready":       "#22C55E",
    "Delivered":   "#10B981",
    "Cancelled":   "#EF4444",
}


def _is_light():
    """Return True when the active theme is light mode (False for dark)."""
    return not ThemeManager().is_dark()


def _card_style():
    """Return the theme-appropriate QSS stylesheet string for an order card frame."""
    if _is_light():
        return "QFrame { background: #FFFFFF; border-radius: 10px; border: 1px solid #E2E8F0; }"
    return "QFrame { background: #1F2937; border-radius: 10px; border: 1px solid #374151; }"


def _id_color():
    """Return the theme-appropriate color for the prominent order-ID label."""
    return "#0F172A" if _is_light() else "#F9FAFB"


def _client_color():
    """Return the theme-appropriate color for secondary/client text."""
    return "#475569" if _is_light() else "#9CA3AF"


def _muted_color():
    """Return the theme-appropriate color for muted/tertiary text and icons."""
    return "#64748B" if _is_light() else "#6B7280"


def _task_input_style():
    """Return the theme-appropriate inline QSS for the 'Add task...' text field."""
    if _is_light():
        return (
            "background:#F8FAFC;color:#0F172A;border:1px solid #E2E8F0;"
            "border-radius:5px;padding:4px 8px;font-size:11px;"
        )
    return (
        "background:#111827;color:#F9FAFB;border:1px solid #374151;"
        "border-radius:5px;padding:4px 8px;font-size:11px;"
    )


def _checkbox_style():
    """Return the theme-appropriate QSS for a task checkbox (indicator styled
    green when checked in both themes)."""
    if _is_light():
        return (
            "QCheckBox { color: #475569; font-size: 11px; background: transparent; }"
            "QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #CBD5E1; background: #F8FAFC; }"
            "QCheckBox::indicator:checked { background: #22C55E; border-color: #22C55E; }"
        )
    return (
        "QCheckBox { color: #9CA3AF; font-size: 11px; background: transparent; }"
        "QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #374151; background: #111827; }"
        "QCheckBox::indicator:checked { background: #22C55E; border-color: #22C55E; }"
    )


def _back_btn_style():
    """Return the amber-tinted QSS for the 'Back to <prev status>' button
    (same in both themes)."""
    return (
        "background:rgba(245,158,11,.12);color:#D97706;"
        "border:1px solid rgba(245,158,11,.3);border-radius:6px;"
        "font-size:11px;font-weight:600;"
    )


class KitchenPage(QWidget):
    """Kanban board widget for managing kitchen orders across status columns.

    Owns the order data (self._orders), builds the resizable column UI, renders
    order cards, and wires up all order/task actions plus live-refresh signals.
    """
    def __init__(self, parent=None):
        """Build the board UI, do an initial column render, and subscribe to
        theme changes and data-change signals that should refresh the board.

        Args:
            parent: Optional parent QWidget.
        Side effects: constructs child widgets and connects app-event signals
        to _mark_dirty_and_reload so external data changes trigger a reload.
        """
        super().__init__(parent)
        self._dirty = True  # Async load on first show
        self._orders = []   # Will be populated by first reload()
        self._search_query = ""
        self._reload_deferred = False
        self._build_ui()
        self._refresh_columns()
        ThemeManager().theme_changed.connect(self._on_theme_changed)
        # Subscribe to app-wide events so the board auto-refreshes when data
        # changes elsewhere. Guarded because the signal hub may be unavailable
        # in some contexts (e.g. isolated tests), and we don't want __init__ to
        # fail just because live-refresh wiring couldn't be established.
        try:
            from utils.signals import app_events
            _ev = app_events()
            _ev.kitchen_updated.connect(self._mark_dirty_and_reload)
            _ev.booking_saved.connect(self._mark_dirty_and_reload)
            _ev.booking_updated.connect(self._mark_dirty_and_reload)
            _ev.sync_completed.connect(self._mark_dirty_and_reload)
            _ev.data_changed.connect(self._mark_dirty_and_reload)
        except Exception:
            pass

    def _mark_dirty(self):
        """Flag the board as needing a reload on its next show."""
        self._dirty = True

    def _has_active_search(self) -> bool:
        """Return True when a non-empty search query is currently applied."""
        return bool(getattr(self, "_search_query", "").strip())

    def _mark_dirty_and_reload(self):
        """Signal handler: mark dirty and reload now if visible.

        If the user is mid-search we defer instead of reloading, so a
        background data change doesn't wipe their filtered view; the deferred
        reload runs once the search clears (see filter_search).
        """
        self._dirty = True
        # Don't rebuild the board while the user is actively searching.
        if self._has_active_search():
            self._reload_deferred = True
            return
        if self.isVisible():
            self.reload()

    def reload(self):
        """Kick off an async fetch of kitchen orders and re-render the board.

        No-op if a previous fetch is still running (avoids overlapping loads).
        Side effects: clears dirty/deferred flags and spawns a DataLoader
        thread whose result is handled by _on_kitchen_data_ready.
        """
        self._dirty = False
        self._reload_deferred = False
        prev = getattr(self, "_kitchen_loader", None)
        if prev is not None and prev.isRunning():
            return
        loader = DataLoader(self._fetch_kitchen_data)
        loader.data_ready.connect(self._on_kitchen_data_ready)
        loader.load_error.connect(lambda msg: print(f"[Kitchen] Load error: {msg}"))
        self._kitchen_loader = loader
        loader.start()

    def _fetch_kitchen_data(self):
        """Worker (runs off the UI thread): reconcile kitchen orders from
        bookings, then return the full list of orders. Returns [] if none."""
        repo.sync_kitchen_from_bookings()
        return repo.get_all_orders() or []

    def _on_kitchen_data_ready(self, new_rows):
        """Receive fetched orders on the UI thread and re-render if changed.

        Args:
            new_rows: freshly fetched order dicts.
        Skips the (expensive) re-render when the (db_id, status) signature is
        identical to the current data, avoiding needless card rebuilds on
        no-op refreshes. Guards against acting on an already-destroyed widget.
        """
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        # Cheap change-detection: compare only the id+status of each order; if
        # nothing moved, skip the teardown/rebuild of every column.
        old_sig = [(o.get("db_id"), o.get("status")) for o in self._orders]
        new_sig = [(o.get("db_id"), o.get("status")) for o in new_rows]
        if old_sig == new_sig:
            return
        self._orders = new_rows
        self._refresh_columns()

    def _reset_column_widths(self):
        """Evenly distribute the available width across all columns (used by
        the 'Reset Column Widths' button and on show). Each column gets at
        least 260px. No-op before the splitter/scroll area exist."""
        if not hasattr(self, "_splitter") or not hasattr(self, "_h_scroll"):
            return
        vw = self._h_scroll.viewport().width()
        equal_w = max(260, vw // self._n_cols)
        self._splitter.setSizes([equal_w] * self._n_cols)

    def _sync_heights(self):
        """Pin the columns' height to the horizontal scroll viewport's height.

        The board scrolls horizontally with a fixed vertical extent, so the
        inner container and splitter must match the viewport height for the
        per-column vertical scrollbars to behave correctly.
        """
        if hasattr(self, "_h_scroll") and hasattr(self, "_scroll_container"):
            vh = self._h_scroll.viewport().height()
            if vh > 0:
                self._scroll_container.setFixedHeight(vh)
                self._splitter.setFixedHeight(vh)

    def resizeEvent(self, event):
        """Qt override: keep column heights in sync with the widget on resize."""
        super().resizeEvent(event)
        self._sync_heights()

    def showEvent(self, event):
        """Qt override: on show, fix heights/widths and lazily load data the
        first time (or whenever the board was marked dirty)."""
        super().showEvent(event)
        self._sync_heights()
        self._reset_column_widths()
        if getattr(self, "_dirty", True):
            self.reload()

    def _on_theme_changed(self, _theme: str):
        """Theme-change handler: restyle column frames and re-render cards so
        all theme-dependent colors update immediately."""
        self._apply_column_styles()
        self._refresh_columns()

    def _build_ui(self):
        """Construct the static page layout: header with reset button, the
        horizontal scroll area, and one resizable column (QSplitter pane) per
        display status. Populates self._col_inner (status -> inner card layout)
        and self._col_frames (status -> column QFrame) for later use."""
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        header = QHBoxLayout()
        title = QLabel("Kitchen")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        reset_btn = QPushButton("⇔  Reset Column Widths")
        reset_btn.setObjectName("secondaryButton")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setFixedHeight(34)
        reset_btn.clicked.connect(self._reset_column_widths)
        header.addWidget(reset_btn)
        root.addLayout(header)

        # Horizontal-only scroll area hosting the splitter of status columns.
        # WidgetResizable is False because we manage the inner size ourselves
        # (fixed height via _sync_heights, explicit width via the splitter).
        self._h_scroll = QScrollArea()
        self._h_scroll.setWidgetResizable(False)
        self._h_scroll.setFrameShape(QFrame.NoFrame)
        self._h_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._h_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._h_scroll.setStyleSheet("background: transparent;")

        scroll_container = QWidget()
        scroll_container.setStyleSheet("background: transparent;")

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(6)
        self._splitter.setStyleSheet("""
            QSplitter::handle {
                background: transparent;
            }
            QSplitter::handle:hover {
                background: rgba(225,29,72,0.25);
                border-radius: 3px;
            }
        """)
        self._splitter.setChildrenCollapsible(False)


        # One board column per status, rendered left-to-right in this order.
        _DISPLAY_COLS = ["Queued", "Preparing", "In Progress", "Ready", "Delivered", "Cancelled"]
        self._col_inner = {}   # status -> the QVBoxLayout that holds its cards
        self._col_frames = {}  # status -> the column's card QFrame (for restyling)
        for status in _DISPLAY_COLS:
            color = _COL_COLORS[status]

            # Wrapper widget is the actual splitter pane; the inner card frame
            # sits inside it with a small horizontal margin.
            col_wrap = QWidget()
            col_wrap.setMinimumWidth(160)
            col_wrap_lay = QVBoxLayout(col_wrap)
            col_wrap_lay.setContentsMargins(4, 0, 4, 0)
            col_wrap_lay.setSpacing(0)

            col_frame = QFrame()
            col_frame.setObjectName("card")
            col_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(16, 16, 16, 16)
            col_layout.setSpacing(12)

            header_row = QHBoxLayout()
            col_title = QLabel(status)
            col_title.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 13px;")
            header_row.addWidget(col_title)
            header_row.addStretch()
            # Braille-dots glyph hints that the column edge is draggable.
            resize_hint = QLabel("⠿")
            resize_hint.setStyleSheet(f"color: {color}; font-size: 14px;")
            resize_hint.setToolTip("Drag the edge to resize this column")
            header_row.addWidget(resize_hint)
            col_layout.addLayout(header_row)

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
            # Trailing stretch keeps cards top-aligned; cards are inserted
            # before it (see _refresh_columns) so it always stays last.
            inner_lay.addStretch()

            scroll.setWidget(inner)
            col_layout.addWidget(scroll)

            col_wrap_lay.addWidget(col_frame)

            self._col_inner[status] = inner_lay
            self._col_frames[status] = col_frame
            self._splitter.addWidget(col_wrap)

        # Start every column at the same minimum width; the splitter's total
        # minimum forces the horizontal scrollbar to appear when the columns
        # can't all fit on screen at once.
        self._n_cols = len(_DISPLAY_COLS)
        col_min_w = 260
        self._splitter.setSizes([col_min_w] * self._n_cols)
        self._splitter.setMinimumWidth(col_min_w * self._n_cols)

        splitter_lay = QVBoxLayout(scroll_container)
        splitter_lay.setContentsMargins(0, 0, 0, 0)
        splitter_lay.setSpacing(0)
        splitter_lay.addWidget(self._splitter)

        self._h_scroll.setWidget(scroll_container)
        self._scroll_container = scroll_container
        root.addWidget(self._h_scroll, 1)

    def _apply_column_styles(self):
        """Re-apply theme-aware background/border to every column frame (called
        on theme change, since the frames' colors are hard-coded per theme)."""
        bg = "#FFFFFF" if _is_light() else "#111827"
        border = "#E2E8F0" if _is_light() else "#243244"
        for col_frame in self._col_frames.values():
            col_frame.setStyleSheet(
                f"QFrame#card {{ background-color: {bg}; border-radius: 14px; border: 1px solid {border}; }}"
            )

    def _refresh_columns(self):
        """Rebuild every column's cards from self._orders, honoring the search.

        Clears each column (keeping only its trailing stretch spacer), then for
        each order that matches the current search query builds a card and
        inserts it into the column matching its status. Case-insensitive search
        matches client name, order id, or event.
        """
        # Tear down existing cards but leave the trailing stretch (count > 1
        # stops before the final stretch item at index 0 once cards are gone).
        for status, lay in self._col_inner.items():
            while lay.count() > 1:
                item = lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        q = getattr(self, "_search_query", "").lower()
        for order in self._orders:
            # Skip orders that don't match the active search across the fields
            # a user would reasonably search by.
            if q and not (
                q in str(order.get("client", "")).lower()
                or q in str(order.get("id", "")).lower()
                or q in str(order.get("event", "")).lower()
            ):
                continue
            card = self._build_order_card(order)
            lay = self._col_inner.get(order["status"])
            if lay:
                # Insert before the trailing stretch to keep cards top-packed.
                lay.insertWidget(lay.count() - 1, card)

    def _build_order_card(self, order):
        """Build and return the QFrame card for a single order.

        Renders the order header (id, client, event, pax, items), an optional
        editable task checklist (only when the order has a db_id), and the
        contextual action buttons (advance/return/cancel/remove) appropriate to
        the order's current status.

        Args:
            order: the order dict (keys include id, client, event, pax, items,
                status, and optionally db_id).
        Returns:
            QFrame: the fully wired card widget.
        """
        card = QFrame()
        card.setStyleSheet(_card_style())
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(6)

        id_lbl = QLabel(order["id"])
        id_lbl.setStyleSheet(f"font-weight: 700; color: {_id_color()}; font-size: 13px;")
        lay.addWidget(id_lbl)

        client_lbl = QLabel(highlight_html(order.get("client", ""), getattr(self, "_search_query", "")))
        client_lbl.setTextFormat(Qt.RichText)
        client_lbl.setStyleSheet(f"color: {_client_color()}; font-size: 12px;")
        lay.addWidget(client_lbl)

        event_lbl = QLabel(order["event"])
        event_lbl.setStyleSheet(f"color: {_muted_color()}; font-size: 11px;")
        lay.addWidget(event_lbl)

        pax_lbl = QLabel(f"{order['pax']} set(s)")
        pax_lbl.setStyleSheet(f"color: {_muted_color()}; font-size: 11px;")
        lay.addWidget(pax_lbl)

        items_lbl = QLabel(order["items"])
        items_lbl.setStyleSheet(f"color: {_client_color()}; font-size: 11px;")
        items_lbl.setWordWrap(True)
        lay.addWidget(items_lbl)

        # Task checklist section only applies to real, persisted orders (those
        # backed by a kitchen_orders row); synthetic/preview orders have no id.
        if order.get("db_id"):
            divider = QFrame()
            divider.setFrameShape(QFrame.HLine)
            divider.setStyleSheet(f"color: {'#E2E8F0' if _is_light() else '#374151'};")
            lay.addWidget(divider)

            tasks_lbl = QLabel("TASKS")
            tasks_lbl.setStyleSheet(f"color: {_muted_color()}; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
            lay.addWidget(tasks_lbl)

            tasks = repo.get_kitchen_tasks(order["db_id"])
            tasks_container = QWidget()
            tasks_container.setStyleSheet("background: transparent;")
            tasks_lay = QVBoxLayout(tasks_container)
            tasks_lay.setContentsMargins(0, 0, 0, 0)
            tasks_lay.setSpacing(4)

            for task in tasks:
                self._add_task_row(tasks_lay, order, task)

            lay.addWidget(tasks_container)

            add_row = QHBoxLayout()
            add_row.setSpacing(6)
            task_input = QLineEdit()
            task_input.setPlaceholderText("Add task...")
            task_input.setStyleSheet(_task_input_style())
            task_input.setFixedHeight(26)
            add_btn = QPushButton("+")
            add_btn.setFixedSize(26, 26)
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.setStyleSheet(
                "background:#3B82F6;color:white;border-radius:5px;font-weight:700;font-size:13px;border:none;"
            )
            # Bind loop-varying widgets as default args so each lambda captures
            # its own order/input/layout rather than the last iteration's.
            add_btn.clicked.connect(lambda _, o=order, inp=task_input, tl=tasks_lay: self._add_task(o, inp, tl))
            task_input.returnPressed.connect(lambda o=order, inp=task_input, tl=tasks_lay: self._add_task(o, inp, tl))
            add_row.addWidget(task_input)
            add_row.addWidget(add_btn)
            lay.addLayout(add_row)

        # Contextual workflow buttons depend on where this order sits in the
        # lifecycle: forward move, backward move, cancel, and remove.
        next_s = _NEXT_STATUS.get(order["status"])
        prev_s = _PREV_STATUS.get(order["status"])
        status = order["status"]

        if next_s:
            # Friendlier wording for the final forward step.
            fwd_label = "Mark Delivered" if next_s == "Delivered" else f"Move to {next_s}"
            btn = QPushButton(fwd_label)
            btn.setObjectName("primaryButton")
            btn.setMinimumHeight(30)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, o=order: self._advance_order(o))
            lay.addWidget(btn)

        if prev_s:
            ret_btn = QPushButton(f"Back to {prev_s}")
            ret_btn.setMinimumHeight(30)
            ret_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            ret_btn.setCursor(Qt.PointingHandCursor)
            ret_btn.setStyleSheet(_back_btn_style())
            ret_btn.clicked.connect(lambda checked=False, o=order: self._return_order(o))
            lay.addWidget(ret_btn)

        # Cancelling only makes sense while the order is still in-flight.
        if status not in ("Delivered", "Cancelled", "Done"):
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setObjectName("dangerButton")
            cancel_btn.setMinimumHeight(30)
            cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.clicked.connect(lambda checked=False, o=order: self._cancel_order(o))
            lay.addWidget(cancel_btn)

        # Terminal orders can be cleared off the board via Remove.
        if status in ("Delivered", "Cancelled"):
            done_btn = QPushButton("Remove")
            done_btn.setObjectName("secondaryButton")
            done_btn.setMinimumHeight(30)
            done_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            done_btn.setCursor(Qt.PointingHandCursor)
            done_btn.clicked.connect(lambda checked=False, o=order: self._remove_order(o))
            lay.addWidget(done_btn)

        return card

    def _add_task_row(self, tasks_lay, order, task):
        """Append one task row (checkbox + delete button) to a card's task list.

        Args:
            tasks_lay: the QVBoxLayout holding this order's task rows.
            order: the owning order dict (unused directly but kept for context).
            task: task dict with keys id, label, is_done.
        Side effects: toggling the checkbox persists via repo.toggle_kitchen_task;
        the delete button removes the row via _delete_task_row.
        """
        row_w = QWidget()
        row_w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        cb = QCheckBox(task["label"])
        cb.setChecked(task["is_done"])
        cb.setStyleSheet(_checkbox_style())
        cb.stateChanged.connect(lambda _, tid=task["id"]: repo.toggle_kitchen_task(tid))
        row.addWidget(cb, 1)

        del_btn = QPushButton("x")
        del_btn.setFixedSize(18, 18)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            f"background: transparent; color: {_muted_color()}; border: none; font-size: 13px; font-weight: 700;"
        )
        del_btn.clicked.connect(lambda _, tid=task["id"], rw=row_w: self._delete_task_row(tid, rw))
        row.addWidget(del_btn)

        tasks_lay.addWidget(row_w)

    def _add_task(self, order, task_input, tasks_lay):
        """Create a new task from the input field and append its row.

        No-op if the field is empty. Persists via repo.add_kitchen_task (using
        the current row count as the task's order/position), and clears the
        input afterward whether or not persistence returned an id.
        """
        label = task_input.text().strip()
        if not label:
            return
        task_id = repo.add_kitchen_task(order["db_id"], label, tasks_lay.count())
        if task_id:
            task = {"id": task_id, "label": label, "is_done": False}
            self._add_task_row(tasks_lay, order, task)
        task_input.clear()

    def _delete_task_row(self, task_id, row_widget):
        """Delete a task from the DB and remove its row widget from the card."""
        repo.delete_kitchen_task(task_id)
        row_widget.hide()
        row_widget.deleteLater()

    def _advance_order(self, order):
        """Move an order to the next lifecycle status.

        Updates the in-memory status, persists it and writes an audit log entry
        (when the order is persisted), re-renders the board, pushes a
        notification, emits kitchen_updated so other views refresh, and shows a
        success toast when the order reaches Delivered. No-op for terminal
        statuses (no next status defined).
        """
        next_s = _NEXT_STATUS.get(order["status"])
        if next_s:
            prev_s = order["status"]
            order["status"] = next_s
            if order.get("db_id"):
                repo.update_order_status(order["db_id"], next_s)
                repo.write_audit_log(get_actor(), "STATUS_CHANGE", "kitchen_orders", order["db_id"],
                    {"status": prev_s}, {"status": next_s})
            self._refresh_columns()
            # Notifications are best-effort; a failure here must not block the
            # status change the user just made.
            try:
                repo.push_notification(
                    "success",
                    f"Order {next_s}",
                    f"Kitchen order '{order['id']}' for {order.get('client', '')} moved to {next_s}.",
                    "#22C55E" if next_s == "Delivered" else "#F59E0B",
                )
            except Exception:
                pass
            app_events().kitchen_updated.emit()
            if next_s == "Delivered":
                success(self, message=f"Order '{order['id']}' marked as Delivered.")

    def _return_order(self, order):
        """Move an order back to the previous lifecycle status.

        Mirrors _advance_order in the reverse direction: updates/persists the
        status, writes an audit log, re-renders, and emits kitchen_updated.
        No-op when there is no previous status.
        """
        prev_s = _PREV_STATUS.get(order["status"])
        if not prev_s:
            return
        old_s = order["status"]
        order["status"] = prev_s
        if order.get("db_id"):
            repo.update_order_status(order["db_id"], prev_s)
            repo.write_audit_log(get_actor(), "STATUS_CHANGE", "kitchen_orders", order["db_id"],
                {"status": old_s}, {"status": prev_s})
        self._refresh_columns()
        app_events().kitchen_updated.emit()

    def _cancel_order(self, order):
        """Cancel an order after a confirmation prompt.

        Sets status to Cancelled (persisting + audit-logging when the order has
        a db_id), re-renders the board, pushes an error-styled notification,
        emits kitchen_updated, and shows a success toast. Aborts if the user
        declines the confirmation.
        """
        if not confirm(self, title="Cancel Order",
                       message=f"Are you sure you want to cancel order '{order['id']}' for {order['client']}?",
                       confirm_label="Cancel Order", danger=True):
            return
        old_s = order["status"]
        order["status"] = "Cancelled"
        if order.get("db_id"):
            repo.update_order_status(order["db_id"], "Cancelled")
            repo.write_audit_log(get_actor(), "CANCEL", "kitchen_orders", order["db_id"],
                {"status": old_s}, {"status": "Cancelled"})
        self._refresh_columns()
        # Best-effort notification; never let it interrupt the cancellation.
        try:
            repo.push_notification(
                "error",
                "Order Cancelled",
                f"Kitchen order '{order['id']}' for {order.get('client', '')} has been cancelled.",
                "#EF4444",
            )
        except Exception:
            pass
        app_events().kitchen_updated.emit()
        success(self, message=f"Order '{order['id']}' has been cancelled.")

    def _remove_order(self, order):
        """Remove an order card from the board after confirmation.

        For a still-active persisted order, marks it done in the DB first (so it
        won't be resynced back onto the board); then drops it from the local
        list and re-renders. Aborts if the user declines.
        """
        if not confirm(self, title="Remove Order",
                       message=f"Remove order '{order['id']}' from the board?",
                       confirm_label="Remove"):
            return
        if order in self._orders:
            # Only mark-done orders that aren't already terminal, so their
            # backing row is finalized and won't reappear on the next sync.
            if order.get("db_id") and order["status"] not in ("Delivered", "Cancelled"):
                repo.mark_order_done(order["db_id"])
            self._orders.remove(order)
            self._refresh_columns()

    def filter_search(self, text):
        """Apply a search query to the board and re-render matching cards.

        Args:
            text: the raw search string (trimmed; empty clears the filter).
        If the search is being cleared and a reload was deferred while the user
        was searching, run that reload instead; otherwise just re-render, since
        _refresh_columns applies the stored query itself.
        """
        self._search_query = (text or "").strip()
        # Search just cleared while a background refresh was deferred -> reload once.
        if not self._search_query and getattr(self, "_reload_deferred", False):
            self._reload_deferred = False
            if self.isVisible():
                self.reload()
                return
        # _refresh_columns applies the stored query itself.
        self._refresh_columns()
