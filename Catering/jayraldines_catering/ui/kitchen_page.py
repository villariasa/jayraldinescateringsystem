from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, QSize

from utils.icons import btn_icon_primary, get_icon
from utils.theme import ThemeManager
from components.dialogs import confirm, success
import utils.repository as repo
from utils.session import get_actor


_SAMPLE_ORDERS = [
    {"id": "ORD-001", "client": "Maria Santos",  "event": "Birthday Party",    "pax": 80,  "items": "Lechon, Kare-Kare, Buko Pandan",   "status": "Queued"},
    {"id": "ORD-002", "client": "TechCorp Inc.", "event": "Corporate Dinner",  "pax": 150, "items": "Chicken Inasal, Pancit, Leche Flan", "status": "In Progress"},
    {"id": "ORD-003", "client": "Cruz Family",   "event": "Debut",             "pax": 200, "items": "Lechon, Kare-Kare, Chopsuey",       "status": "Ready"},
    {"id": "ORD-004", "client": "Smith Wedding", "event": "Wedding Reception",  "pax": 300, "items": "Full Package Premium",              "status": "Queued"},
]

_STATUSES    = ["Queued", "Preparing", "In Progress", "Ready", "Delivered", "Cancelled"]
_NEXT_STATUS = {"Queued": "Preparing", "Preparing": "In Progress", "In Progress": "Ready", "Ready": "Delivered"}
_PREV_STATUS = {"Preparing": "Queued", "In Progress": "Preparing", "Ready": "In Progress", "Delivered": "Ready"}
_COL_COLORS  = {
    "Queued":      "#F59E0B",
    "Preparing":   "#A855F7",
    "In Progress": "#3B82F6",
    "Ready":       "#22C55E",
    "Delivered":   "#10B981",
    "Cancelled":   "#EF4444",
}


def _is_light():
    return not ThemeManager().is_dark()


def _card_style():
    if _is_light():
        return "QFrame { background: #FFFFFF; border-radius: 10px; border: 1px solid #E2E8F0; }"
    return "QFrame { background: #1F2937; border-radius: 10px; border: 1px solid #374151; }"


def _id_color():
    return "#0F172A" if _is_light() else "#F9FAFB"


def _client_color():
    return "#475569" if _is_light() else "#9CA3AF"


def _muted_color():
    return "#64748B" if _is_light() else "#6B7280"


def _task_input_style():
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
    return (
        "background:rgba(245,158,11,.12);color:#D97706;"
        "border:1px solid rgba(245,158,11,.3);border-radius:6px;"
        "font-size:11px;font-weight:600;"
    )


class KitchenPage(QWidget):
    def __init__(self):
        super().__init__()
        repo.sync_kitchen_from_bookings()
        db_rows = repo.get_all_orders()
        self._orders = db_rows if db_rows else []
        self._build_ui()
        self._refresh_columns()
        ThemeManager().theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, _theme: str):
        self._apply_column_styles()
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

        col_scroll = QScrollArea()
        col_scroll.setWidgetResizable(True)
        col_scroll.setFrameShape(QFrame.NoFrame)
        col_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        col_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        col_container = QWidget()
        col_container.setStyleSheet("background: transparent;")
        self._cols_layout = QHBoxLayout(col_container)
        self._cols_layout.setSpacing(16)
        self._cols_layout.setContentsMargins(0, 0, 0, 0)

        _DISPLAY_COLS = ["Queued", "Preparing", "In Progress", "Ready", "Delivered", "Cancelled"]
        self._col_inner = {}
        self._col_frames = {}
        for status in _DISPLAY_COLS:
            color = _COL_COLORS[status]
            col_frame = QFrame()
            col_frame.setObjectName("card")
            col_frame.setMinimumWidth(200)
            col_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
            self._col_frames[status] = col_frame
            self._cols_layout.addWidget(col_frame, 1)

        col_scroll.setWidget(col_container)
        root.addWidget(col_scroll)

    def _apply_column_styles(self):
        bg = "#FFFFFF" if _is_light() else "#111827"
        border = "#E2E8F0" if _is_light() else "#243244"
        for col_frame in self._col_frames.values():
            col_frame.setStyleSheet(
                f"QFrame#card {{ background-color: {bg}; border-radius: 14px; border: 1px solid {border}; }}"
            )

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
        card.setStyleSheet(_card_style())
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(6)

        id_lbl = QLabel(order["id"])
        id_lbl.setStyleSheet(f"font-weight: 700; color: {_id_color()}; font-size: 13px;")
        lay.addWidget(id_lbl)

        client_lbl = QLabel(order["client"])
        client_lbl.setStyleSheet(f"color: {_client_color()}; font-size: 12px;")
        lay.addWidget(client_lbl)

        event_lbl = QLabel(order["event"])
        event_lbl.setStyleSheet(f"color: {_muted_color()}; font-size: 11px;")
        lay.addWidget(event_lbl)

        pax_lbl = QLabel(f"{order['pax']} pax")
        pax_lbl.setStyleSheet(f"color: {_muted_color()}; font-size: 11px;")
        lay.addWidget(pax_lbl)

        items_lbl = QLabel(order["items"])
        items_lbl.setStyleSheet(f"color: {_client_color()}; font-size: 11px;")
        items_lbl.setWordWrap(True)
        lay.addWidget(items_lbl)

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
            add_btn.clicked.connect(lambda _, o=order, inp=task_input, tl=tasks_lay: self._add_task(o, inp, tl))
            task_input.returnPressed.connect(lambda o=order, inp=task_input, tl=tasks_lay: self._add_task(o, inp, tl))
            add_row.addWidget(task_input)
            add_row.addWidget(add_btn)
            lay.addLayout(add_row)

        next_s = _NEXT_STATUS.get(order["status"])
        prev_s = _PREV_STATUS.get(order["status"])
        status = order["status"]

        if next_s:
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

        if status not in ("Delivered", "Cancelled", "Done"):
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setObjectName("dangerButton")
            cancel_btn.setMinimumHeight(30)
            cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cancel_btn.setCursor(Qt.PointingHandCursor)
            cancel_btn.clicked.connect(lambda checked=False, o=order: self._cancel_order(o))
            lay.addWidget(cancel_btn)

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
        label = task_input.text().strip()
        if not label:
            return
        task_id = repo.add_kitchen_task(order["db_id"], label, tasks_lay.count())
        if task_id:
            task = {"id": task_id, "label": label, "is_done": False}
            self._add_task_row(tasks_lay, order, task)
        task_input.clear()

    def _delete_task_row(self, task_id, row_widget):
        repo.delete_kitchen_task(task_id)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def _advance_order(self, order):
        next_s = _NEXT_STATUS.get(order["status"])
        if next_s:
            prev_s = order["status"]
            order["status"] = next_s
            if order.get("db_id"):
                repo.update_order_status(order["db_id"], next_s)
                repo.write_audit_log(get_actor(), "STATUS_CHANGE", "kitchen_orders", order["db_id"],
                    {"status": prev_s}, {"status": next_s})
            self._refresh_columns()
            if next_s == "Delivered":
                success(self, message=f"Order '{order['id']}' marked as Delivered.")

    def _return_order(self, order):
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

    def _cancel_order(self, order):
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
