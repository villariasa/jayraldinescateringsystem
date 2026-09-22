"""
Dedicated Expenses page — moved out of Reports so expense tracking is a
first-class module (food cost, salary, service, transport, utilities, etc.).

Card-based list + add/delete reuse the repository functions.
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QMessageBox, QComboBox, QDateEdit, QLineEdit,
)
from PySide6.QtCore import Qt, QMargins, QSize, QTimer
from PySide6.QtGui import QColor, QPainter

from utils.theme import ThemeManager
from utils.icons import btn_icon_secondary, btn_icon_red, get_icon
from components.loading_overlay import LoadingOverlay
import utils.repository as repo
from components.dialogs import confirm, success, error
from utils.session import SessionManager
from utils.data_loader import run_async

EXPENSE_CATEGORIES = [
    "Food Cost", "Labor", "Salary", "Service",
    "Transport", "Utilities", "Equipment", "Other",
]

_CATEGORY_COLORS = {
    "Food Cost": "#E11D48",
    "Labor":     "#F59E0B",
    "Salary":    "#8B5CF6",
    "Service":   "#3B82F6",
    "Transport": "#10B981",
    "Utilities": "#F97316",
    "Equipment": "#64748B",
    "Other":     "#94A3B8",
}


def _is_light():
    return not ThemeManager().is_dark()


class _KpiCard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(6)
        t = QLabel(title.upper())
        t.setObjectName("kpiLabel")
        lay.addWidget(t)
        self._val = QLabel("—")
        self._val.setObjectName("kpiValue")
        lay.addWidget(self._val)
        self._sub = QLabel("")
        self._sub.setObjectName("subtitle")
        lay.addWidget(self._sub)
        lay.addStretch()

    def set(self, value: str, sub: str = ""):
        self._val.setText(value)
        self._sub.setText(sub)


class ExpensesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mainBackground")
        self._reload_in_flight = False
        self._reload_pending = False
        # Lazy-loading pagination state (mirrors billing_page pattern).
        self._page_size = 50
        self._has_more = True
        self._loading_more = False
        self._rendering = False
        self._cached_remainder = None
        self._summary = {
            "total_all_time": 0.0, "total_this_year": 0.0,
            "total_this_month": 0.0, "by_category": [],
        }
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.timeout.connect(self._run_search_filter)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget(scroll)
        content.setStyleSheet("background: transparent;")
        self.lay = QVBoxLayout(content)
        self.lay.setContentsMargins(40, 40, 40, 40)
        self.lay.setSpacing(24)

        # ── Header ──────────────────────────────────────────────────────────
        head = QHBoxLayout()
        v = QVBoxLayout()
        title = QLabel("Expenses")
        title.setObjectName("pageTitle")
        sub = QLabel("Track food cost, salaries, services, and other operating expenses.")
        sub.setObjectName("subtitle")
        v.addWidget(title)
        v.addWidget(sub)
        head.addLayout(v)
        head.addStretch()
        self.btn_add = QPushButton("  + Add Expense")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.setIcon(btn_icon_secondary("add"))
        self.btn_add.setIconSize(QSize(15, 15))
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setStyleSheet("QPushButton#primaryButton { background-color: #E11D48; color: #FFFFFF; border: none; font-weight: 700; border-radius: 8px; padding: 8px 16px; } QPushButton#primaryButton:hover { background-color: #BE123C; }")
        self.btn_add.clicked.connect(self._open_add_expense)
        head.addWidget(self.btn_add)

        self.btn_import = QPushButton("  Import")
        self.btn_import.setObjectName("secondaryButton")
        self.btn_import.setIcon(btn_icon_secondary("export"))
        self.btn_import.setIconSize(QSize(15, 15))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self._open_import_expenses)
        head.addWidget(self.btn_import)
        self.lay.addLayout(head)

        _is_l = not ThemeManager().is_dark()
        input_style = (
            "QLineEdit { padding: 8px 14px; border: 1px solid #D8DFEA; border-radius: 8px; background-color: #FFFFFF; color: #101828; font-size: 13px; }"
            "QLineEdit:focus { border: 1.5px solid #E11D48; }"
        ) if _is_l else (
            "QLineEdit { padding: 8px 14px; border: 1px solid #243244; border-radius: 8px; background-color: #1F2937; color: #F9FAFB; font-size: 13px; }"
            "QLineEdit:focus { border: 1.5px solid #E11D48; }"
        )
        combo_style = (
            "QComboBox { padding: 6px 12px; border: 1px solid #D8DFEA; border-radius: 8px; background-color: #FFFFFF; color: #101828; font-size: 13px; }"
            "QComboBox:focus { border: 1px solid #E11D48; }"
            "QComboBox QAbstractItemView { background-color: #FFFFFF; color: #101828; border: 1px solid #E4E9F1; border-radius: 8px; selection-background-color: rgba(225,29,72,0.08); selection-color: #D31647; }"
        ) if _is_l else (
            "QComboBox { padding: 6px 12px; border: 1px solid #243244; border-radius: 8px; background-color: #1F2937; color: #F9FAFB; font-size: 13px; }"
            "QComboBox:focus { border: 1px solid #E11D48; }"
            "QComboBox QAbstractItemView { background-color: #1F2937; color: #F9FAFB; border: 1px solid #243244; border-radius: 8px; selection-background-color: rgba(225,29,72,0.15); selection-color: #E11D48; }"
        )
        date_style = (
            "QDateEdit { padding: 4px 10px; border: 1px solid #D8DFEA; border-radius: 8px; background-color: #FFFFFF; color: #101828; font-size: 13px; }"
        ) if _is_l else (
            "QDateEdit { padding: 4px 10px; border: 1px solid #243244; border-radius: 8px; background-color: #1F2937; color: #F9FAFB; font-size: 13px; }"
        )

        # ── Top Filter & Real-Time Search Bar ─────────────────────────────────
        top_filter_card = QFrame(content)
        top_filter_card.setObjectName("card")
        tf_lay = QVBoxLayout(top_filter_card)
        tf_lay.setContentsMargins(20, 16, 20, 16)
        tf_lay.setSpacing(12)

        # Row 1: Search Bar & Count
        search_row = QHBoxLayout()
        search_row.setSpacing(12)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Search expenses (food packs, description, expense items, category, amount)...")
        self._search_input.setFixedHeight(38)
        self._search_input.setStyleSheet(input_style)
        self._search_input.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_input, 1)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("muted")
        self._count_lbl.setStyleSheet("font-weight: 600; font-size: 12.5px; color: #64748B;")
        search_row.addWidget(self._count_lbl)
        tf_lay.addLayout(search_row)

        # Row 2: Filter Period, Month Filter, Custom Date Pickers, Reset
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        lbl_filter = QLabel("Period:")
        lbl_filter.setStyleSheet("font-weight: 600; font-size: 13px;")
        filter_row.addWidget(lbl_filter)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems([
            "All Time",
            "Today (This Day)",
            "This Week",
            "This Month",
            "This Year",
            "Custom Date / Range"
        ])
        self._filter_combo.setFixedHeight(34)
        self._filter_combo.setMinimumWidth(160)
        self._filter_combo.setStyleSheet(combo_style)
        # Default to "This Month" (recent) instead of "All Time", mirroring
        # Billing/Orders defaulting to a recent window instead of full history.
        self._filter_combo.setCurrentIndex(3)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._filter_combo)

        lbl_month = QLabel("Month:")
        lbl_month.setStyleSheet("font-weight: 600; font-size: 13px;")
        filter_row.addWidget(lbl_month)

        self._month_combo = QComboBox()
        self._month_combo.addItems([
            "All Months",
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December"
        ])
        self._month_combo.setFixedHeight(34)
        self._month_combo.setMinimumWidth(140)
        self._month_combo.setStyleSheet(combo_style)
        self._month_combo.currentIndexChanged.connect(self._on_month_changed)
        filter_row.addWidget(self._month_combo)

        # Custom date pickers widget
        self._custom_date_widget = QWidget()
        custom_lay = QHBoxLayout(self._custom_date_widget)
        custom_lay.setContentsMargins(0, 0, 0, 0)
        custom_lay.setSpacing(8)

        lbl_from = QLabel("From:")
        from PySide6.QtCore import QDate
        self._dt_start = QDateEdit(QDate.currentDate().addMonths(-1))
        self._dt_start.setCalendarPopup(True)
        self._dt_start.setFixedHeight(34)
        self._dt_start.setStyleSheet(date_style)
        self._dt_start.dateChanged.connect(lambda: self._on_date_range_changed())

        lbl_to = QLabel("To:")
        self._dt_end = QDateEdit(QDate.currentDate())
        self._dt_end.setCalendarPopup(True)
        self._dt_end.setFixedHeight(34)
        self._dt_end.setStyleSheet(date_style)
        self._dt_end.dateChanged.connect(lambda: self._on_date_range_changed())

        custom_lay.addWidget(lbl_from)
        custom_lay.addWidget(self._dt_start)
        custom_lay.addWidget(lbl_to)
        custom_lay.addWidget(self._dt_end)
        self._custom_date_widget.setVisible(False)
        filter_row.addWidget(self._custom_date_widget)

        filter_row.addStretch()

        reset_btn = QPushButton("↺ Reset")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setFixedHeight(32)
        reset_btn.setStyleSheet("padding: 4px 12px; border-radius: 6px; font-weight: 600; font-size: 12px;")
        reset_btn.clicked.connect(self._reset_filters)
        filter_row.addWidget(reset_btn)

        tf_lay.addLayout(filter_row)
        self.lay.addWidget(top_filter_card)

        # ── KPI row ─────────────────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self._kpi_total = _KpiCard("Total Expenses (This Year)")
        self._kpi_month = _KpiCard("This Month")
        self._kpi_top   = _KpiCard("Top Category")
        # Unlike the other three cards (fixed this-year/this-month/top-
        # category reference points), this one actually tracks whatever
        # Period/Month filter is currently selected - without it, the client
        # had no way to see a total figure for e.g. "Today" or a custom date
        # range, only the fixed all-time cards regardless of the filter.
        self._kpi_filtered = _KpiCard("Total (Selected Filter)")
        for c in (self._kpi_filtered, self._kpi_total, self._kpi_month, self._kpi_top):
            kpi_row.addWidget(c)
        self.lay.addLayout(kpi_row)

        # ── Expenses Cards Section ─────────────────────────────────────────
        table_card = QFrame(content)
        table_card.setObjectName("card")
        t_lay = QVBoxLayout(table_card)
        t_lay.setContentsMargins(24, 20, 24, 24)
        t_lay.setSpacing(12)

        tc_head = QHBoxLayout()
        tc_title = QLabel("Expense Records")
        tc_title.setObjectName("h3")
        tc_head.addWidget(tc_title)
        tc_head.addStretch()
        t_lay.addLayout(tc_head)

        self.exp_cards_container = QWidget()
        self.exp_cards_container.setStyleSheet("background: transparent;")
        self.exp_cards_layout = QVBoxLayout(self.exp_cards_container)
        self.exp_cards_layout.setContentsMargins(0, 0, 10, 0)
        self.exp_cards_layout.setSpacing(10)

        # Cap the visible list to ~7 rows (like a fixed-height table) - the rest
        # scrolls within this nested area instead of growing the whole page.
        self.exp_list_scroll = QScrollArea()
        self.exp_list_scroll.setWidgetResizable(True)
        self.exp_list_scroll.setFrameShape(QFrame.NoFrame)
        self.exp_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.exp_list_scroll.setFixedHeight(520)  # ~7 rows at ~64px + 10px spacing
        self.exp_list_scroll.setWidget(self.exp_cards_container)

        t_lay.addWidget(self.exp_list_scroll)
        self.lay.addWidget(table_card)
        self.lay.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)
        self._scroll = scroll
        # Load the next page as the user nears the bottom of the (nested,
        # fixed-height) expense list - not the outer page scroll.
        self.exp_list_scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_near_bottom)
        self._loader = LoadingOverlay(self, "Loading expenses & analytics...")

        try:
            from utils.signals import app_events
            app_events().expense_saved.connect(self._mark_dirty_and_reload)
            app_events().sync_completed.connect(self._mark_dirty_and_reload)
            app_events().data_changed.connect(self._mark_dirty_and_reload)
        except Exception:
            pass

    def _mark_dirty(self):
        self._dirty = True

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self.reload()

    # ── Data loading & Filtering ────────────────────────────────────────────

    # NOTE: The KPI cards and category breakdown are driven by a DB aggregate
    # (self._summary) covering the ENTIRE dataset, so they stay correct under
    # pagination and are intentionally NOT recomputed from the client-side
    # filters. The filters only narrow the rendered (already-loaded) card list.
    def _on_search_changed(self, text: str):
        # Debounced - typing quickly used to clear-and-rebuild the whole card
        # list on every single keystroke, which is what made search feel laggy.
        self._search_debounce.start(500)

    def _run_search_filter(self):
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()

    def _on_filter_changed(self, idx: int):
        is_custom = (idx == 5)
        self._custom_date_widget.setVisible(is_custom)
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._reload_summary_for_filter()

    def _on_month_changed(self, idx: int):
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._reload_summary_for_filter()

    def _on_date_range_changed(self):
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._reload_summary_for_filter()

    def _reset_filters(self):
        if hasattr(self, "_search_input"):
            self._search_input.blockSignals(True)
            self._search_input.clear()
            self._search_input.blockSignals(False)
        if hasattr(self, "_filter_combo"):
            self._filter_combo.blockSignals(True)
            self._filter_combo.setCurrentIndex(3)  # "This Month" - matches the default
            self._filter_combo.blockSignals(False)
        if hasattr(self, "_month_combo"):
            self._month_combo.blockSignals(True)
            self._month_combo.setCurrentIndex(0)
            self._month_combo.blockSignals(False)
        if hasattr(self, "_custom_date_widget"):
            self._custom_date_widget.setVisible(False)
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._reload_summary_for_filter()

    def _current_filter_date_range(self):
        """Translate the active period/month filter into a (start, end) ISO
        date range for the breakdown chart's DB query. Mirrors the same
        period/month semantics as _filter_expenses_list, but as a date range
        instead of a per-row predicate."""
        from datetime import date, timedelta

        period_opt = self._filter_combo.currentText() if hasattr(self, "_filter_combo") else "All Time"
        month_opt = self._month_combo.currentText() if hasattr(self, "_month_combo") else "All Months"
        today = date.today()

        MONTH_MAP = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12,
        }

        start = end = None
        if period_opt != "All Time":
            if "Today" in period_opt:
                start = end = today
            elif "This Week" in period_opt:
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=6)
            elif "This Month" in period_opt:
                # Full calendar month, not capped at today - matches
                # Billing/Reports fix (this date range feeds a DB query, so
                # capping at today silently excluded any expense dated
                # later in the month/year from the breakdown chart).
                start = today.replace(day=1)
                end = (date(today.year, today.month + 1, 1) - timedelta(days=1)) if today.month < 12 else date(today.year, 12, 31)
            elif "This Year" in period_opt:
                start = today.replace(month=1, day=1)
                end = today.replace(month=12, day=31)
            elif "Custom Date" in period_opt and hasattr(self, "_dt_start") and hasattr(self, "_dt_end"):
                start = self._dt_start.date().toPython()
                end = self._dt_end.date().toPython()

        if month_opt != "All Months" and month_opt in MONTH_MAP:
            m_num = MONTH_MAP[month_opt]
            year = today.year
            month_start = date(year, m_num, 1)
            month_end = (date(year, m_num + 1, 1) - timedelta(days=1)) if m_num < 12 else date(year, 12, 31)
            start = month_start if start is None or month_start > start else start
            end = month_end if end is None or month_end < end else end

        if start is None and end is None:
            return None, None
        return (start or date(2000, 1, 1)).isoformat(), (end or today).isoformat()

    def _reload_summary_for_filter(self):
        # Re-fetch the category breakdown scoped to the active filter, so the
        # "top category" KPI (which reads this data) actually changes when the
        # user filters instead of always showing all-time totals. (The bar
        # chart that also used this data now lives on the Reports page.)
        start, end = self._current_filter_date_range()
        run_async(self, repo.get_expenses_summary, self._on_filtered_summary_loaded, None, start, end)

    def _on_filtered_summary_loaded(self, summary):
        from shiboken6 import isValid
        if not isValid(self):
            return
        if summary:
            self._summary = summary
        self._load_kpis()

    def _filter_expenses_list(self, expenses: list) -> list:
        if not expenses:
            return []

        search_txt = self._search_input.text().strip().lower() if hasattr(self, "_search_input") else ""
        period_opt = self._filter_combo.currentText() if hasattr(self, "_filter_combo") else "All Time"
        month_opt = self._month_combo.currentText() if hasattr(self, "_month_combo") else "All Months"

        from datetime import datetime, date, timedelta
        today = date.today()

        MONTH_MAP = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }

        filtered = []
        for exp in expenses:
            d_str = str(exp.get("date", ""))
            exp_d = None
            for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
                try:
                    exp_d = datetime.strptime(d_str, fmt).date()
                    break
                except ValueError:
                    continue

            # Period Filter Check
            if period_opt != "All Time":
                if not exp_d:
                    continue
                if "Today" in period_opt and exp_d != today:
                    continue
                elif "This Week" in period_opt:
                    start_w = today - timedelta(days=today.weekday())
                    end_w = start_w + timedelta(days=6)
                    if not (start_w <= exp_d <= end_w):
                        continue
                elif "This Month" in period_opt:
                    if not (exp_d.month == today.month and exp_d.year == today.year):
                        continue
                elif "This Year" in period_opt:
                    if exp_d.year != today.year:
                        continue
                elif "Custom Date" in period_opt and hasattr(self, "_dt_start") and hasattr(self, "_dt_end"):
                    d_start = self._dt_start.date().toPython()
                    d_end = self._dt_end.date().toPython()
                    if not (d_start <= exp_d <= d_end):
                        continue

            # Dedicated Month Filter Check
            if month_opt != "All Months" and month_opt in MONTH_MAP:
                m_num = MONTH_MAP[month_opt]
                if not exp_d or exp_d.month != m_num:
                    continue

            # Search Working: food packs, description, category, amount, date
            if search_txt:
                desc = str(exp.get("description", "")).lower()
                cat = str(exp.get("category", "")).lower()
                amt_str = str(exp.get("amount", "")).lower()
                fmt_amt = f"₱{float(exp.get('amount', 0)):,.2f}".lower()
                d_lower = d_str.lower()
                
                # Check match across description, category, amount, formatted amount, date
                matched = (
                    search_txt in desc
                    or search_txt in cat
                    or search_txt in amt_str
                    or search_txt in fmt_amt
                    or search_txt in d_lower
                )
                if not matched:
                    continue

            filtered.append(exp)

        return filtered

    def refresh_permissions(self):
        can_create = SessionManager.has_permission("expenses", "create")
        can_edit = SessionManager.has_permission("expenses", "edit")
        can_delete = SessionManager.has_permission("expenses", "delete")
        if hasattr(self, "btn_add"):
            self.btn_add.setEnabled(can_create)
            self.btn_add.setVisible(can_create)
        if hasattr(self, "btn_import"):
            self.btn_import.setEnabled(can_create)
            self.btn_import.setVisible(can_create)

        # Per-card Edit/Delete buttons are baked in at render time, so a role
        # change (e.g. logging back in as Admin after a Staff session) would
        # otherwise leave already-rendered cards showing the PREVIOUS user's
        # permissions. Rebuild the card list when the permission set changes.
        sig = (can_create, can_edit, can_delete)
        if sig != getattr(self, "_last_perm_sig", None):
            self._last_perm_sig = sig
            if getattr(self, "_expenses", None) and not getattr(self, "_rendering", False):
                self._load_table()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_permissions()
        if getattr(self, "_dirty", True):
            self.reload()

    def reload(self):
        # Coalesce overlapping reloads: if a reload (fetch + batch-render) is
        # already running, don't start a second one in parallel - just remember
        # to run exactly one more pass once the current one fully finishes.
        if getattr(self, "_reload_in_flight", False):
            self._reload_pending = True
            return
        self._reload_in_flight = True
        self._reload_pending = False

        self._dirty = False
        self.refresh_permissions()

        # Full dataset is loaded at once in self._expenses; no further incremental DB fetches needed.
        self._has_more = False
        self._loading_more = False

        # Load full expense dataset (from pre-loaded memory cache if available, or DB).
        # Keeping the complete dataset in self._expenses ensures client-side filtering
        # (This Year, This Month, search, etc.) and the "Total (Selected Filter)" KPI
        # are always 100% accurate and never truncated to partial paginated subsets.
        from utils.data_cache import DataCache
        cached = DataCache.get("expenses")
        if cached is not None and not getattr(self, "_has_loaded_once", False):
            self._has_loaded_once = True
            self._summary = self._compute_summary_from_rows(cached)
            all_exp = list(cached)
            if hasattr(self, "_loader"):
                self._loader.show_overlay("Loading expenses & analytics...")
                QTimer.singleShot(60, lambda: self._on_expenses_loaded(all_exp))
            else:
                self._on_expenses_loaded(all_exp)
            return

        if hasattr(self, "_loader"):
            self._loader.show_overlay("Loading expenses & analytics...")
        run_async(self, self._fetch_all_data, self._on_all_data_loaded)

    @staticmethod
    def _fetch_all_data():
        # Fetch whole dataset aggregate + all expense rows in one worker hop.
        return repo.get_expenses_summary(), repo.get_all_expenses()

    def _on_all_data_loaded(self, result):
        summary, all_exp = result if result else ({}, [])
        self._summary = summary or {
            "total_all_time": 0.0, "total_this_year": 0.0,
            "total_this_month": 0.0, "by_category": [],
        }
        self._on_expenses_loaded(all_exp or [])

    @staticmethod
    def _compute_summary_from_rows(rows):
        """Derive the KPI/breakdown aggregate from a full in-memory list (used
        only when the login welcome sequence already cached every row)."""
        from datetime import datetime as _dt
        now = _dt.now()
        total_all = 0.0
        total_year = 0.0
        total_month = 0.0
        cat_totals = {}
        for exp in rows or []:
            amt = float(exp.get("amount", 0.0) or 0.0)
            total_all += amt
            cat = exp.get("category", "Other") or "Other"
            cat_totals[cat] = cat_totals.get(cat, 0.0) + amt
            d = None
            for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
                try:
                    d = _dt.strptime(str(exp.get("date", "")), fmt)
                    break
                except (ValueError, TypeError):
                    continue
            if d:
                if d.year == now.year:
                    total_year += amt
                    if d.month == now.month:
                        total_month += amt
        by_category = sorted(
            ({"category": c, "total": t} for c, t in cat_totals.items() if t > 0),
            key=lambda x: x["total"], reverse=True,
        )
        return {
            "total_all_time": total_all, "total_this_year": total_year,
            "total_this_month": total_month, "by_category": by_category,
        }

    def _reload_finished(self):
        self._reload_in_flight = False
        self._loading_more = False
        if getattr(self, "_reload_pending", False):
            self._reload_pending = False
            QTimer.singleShot(0, self.reload)

    def _on_expenses_loaded(self, data):
        from shiboken6 import isValid
        if not isValid(self):
            # Nothing rendered; release the reload guard so future reloads work.
            self._reload_finished()
            return
        all_exp = data or []
        self._expenses = all_exp
        self._filtered_expenses = self._filter_expenses_list(all_exp)
        # NOTE: the loading overlay is intentionally NOT hidden here. It is
        # hidden by _load_table / _render_next_batch once the LAST card batch
        # has actually finished rendering, not right after the fetch.
        self._load_table()
        self._load_kpis()
        # The default filter is "This Month" (not "All Time"), but the
        # initial self._summary above is always an unfiltered/all-time
        # aggregate - without this, the new "Total (Selected Filter)" KPI
        # would show the all-time total on first load while its own label
        # says "This Month", until the user manually touched the filter.
        self._reload_summary_for_filter()

    def _load_more_expenses(self):
        return

    def _on_more_expenses_loaded(self, data):
        from shiboken6 import isValid
        if not isValid(self):
            return
        new_rows = data or []
        if self._cached_remainder is None and len(new_rows) < self._page_size:
            self._has_more = False
        if not new_rows:
            self._loading_more = False
            return
        if not hasattr(self, "_expenses") or self._expenses is None:
            self._expenses = []
        self._expenses.extend(new_rows)
        self._append_expense_cards(new_rows)

    def _append_expense_cards(self, new_rows):
        # Only append rows that pass the active client-side filter.
        visible = self._filter_expenses_list(new_rows)
        # Keep the running filtered view in sync for the record-count label.
        if not hasattr(self, "_filtered_expenses") or self._filtered_expenses is None:
            self._filtered_expenses = []
        self._filtered_expenses.extend(visible)
        n = len(self._filtered_expenses)
        if hasattr(self, "_count_lbl"):
            self._count_lbl.setText(f"{n} record{'s' if n != 1 else ''}")

        if not visible:
            self._loading_more = False
            return

        # NOTE: we deliberately never remove/re-add the trailing stretch spacer
        # (previously done via layout.takeAt() on every append) - repeatedly
        # taking a QLayoutItem out of a layout and discarding it was the
        # suspected cause of a native Qt memory-reuse crash. _render_next_batch
        # now inserts new cards just BEFORE the permanent stretch instead.
        self._render_can_del = SessionManager.has_permission("expenses", "delete")
        self._render_can_edit = SessionManager.has_permission("expenses", "edit")
        self._render_token = getattr(self, "_render_token", 0) + 1
        self._render_queue = list(visible)
        self._rendering = True
        self._render_next_batch(self._render_token)

    def _on_scroll_near_bottom(self, value):
        if not hasattr(self, "exp_list_scroll"):
            return
        sb = self.exp_list_scroll.verticalScrollBar()
        if sb.maximum() - value < 200:
            self._load_more_expenses()

    def _load_table(self):
        # The "Total (Selected Filter)" KPI must reflect the SEARCH text too,
        # not just the Period/Month dropdowns - the client wants the total to
        # update automatically as they type, matching exactly what's visible
        # in the card list below. self._filtered_expenses already combines
        # period + month + search (see _filter_expenses_list), so summing it
        # directly here is simpler and more accurate than the separate
        # DB-scoped total_filtered query, which never factored in search text.
        if hasattr(self, "_kpi_filtered"):
            visible = getattr(self, "_filtered_expenses", None) or []
            search_active = bool(getattr(self, "_search_input", None) and self._search_input.text().strip())
            total_visible = sum(float(e.get("amount", 0) or 0) for e in visible)
            period_opt = self._filter_combo.currentText() if hasattr(self, "_filter_combo") else "All Time"
            month_opt = self._month_combo.currentText() if hasattr(self, "_month_combo") else "All Months"
            bits = [b for b in (period_opt, None if month_opt == "All Months" else month_opt,
                                "matching search" if search_active else None) if b]
            self._kpi_filtered.set(f"₱ {total_visible:,.0f}", " · ".join(bits) or "All Time")

        # Bump the render token so any batch still in flight from a previous
        # populate/filter call cancels itself instead of appending stale rows.
        self._render_token = getattr(self, "_render_token", 0) + 1
        token = self._render_token

        if hasattr(self, "exp_cards_container"):
            self.exp_cards_container.setUpdatesEnabled(False)
        try:
            while self.exp_cards_layout.count():
                item = self.exp_cards_layout.takeAt(0)
                if item:
                    w = item.widget()
                    if w:
                        w.hide()
                        w.deleteLater()

            expenses = getattr(self, "_filtered_expenses", self._expenses if hasattr(self, "_expenses") else [])

            n = len(expenses)
            self._count_lbl.setText(f"{n} record{'s' if n != 1 else ''}")

            if not expenses:
                empty_card = QFrame()
                empty_card.setObjectName("entryCard")
                el = QVBoxLayout(empty_card)
                empty_lbl = QLabel("No expenses recorded for this filter period.")
                empty_lbl.setObjectName("subtitle")
                empty_lbl.setAlignment(Qt.AlignCenter)
                el.addWidget(empty_lbl)
                self.exp_cards_layout.addWidget(empty_card)
                self.exp_cards_layout.addStretch()
                # No batches will run, so the full pipeline is done here: hide
                # the loader immediately and release the reload guard.
                if hasattr(self, "_loader"):
                    self._loader.hide_overlay()
                self._rendering = False
                self._reload_finished()
                return
        finally:
            if hasattr(self, "exp_cards_container"):
                self.exp_cards_container.setUpdatesEnabled(True)

        # Hoist per-row-invariant permission check out of the render loop.
        self._render_can_del = SessionManager.has_permission("expenses", "delete")
        self._render_can_edit = SessionManager.has_permission("expenses", "edit")
        self._render_queue = list(expenses)
        self._rendering = True
        self._render_next_batch(token)

    @staticmethod
    def _insert_card_before_stretch(layout, card):
        # Insert just before a trailing stretch spacer if one exists, rather
        # than ever taking the spacer out of the layout - repeatedly
        # take()-ing and discarding a QLayoutItem was the suspected trigger
        # for a native Qt memory-reuse crash under heavy append churn.
        count = layout.count()
        if count > 0 and layout.itemAt(count - 1).widget() is None:
            layout.insertWidget(count - 1, card)
        else:
            layout.addWidget(card)

    def _render_next_batch(self, token, batch_size=15):
        # Abort if a newer populate/filter cycle superseded this one.
        if token != getattr(self, "_render_token", None):
            return
        from shiboken6 import isValid
        if not isValid(self):
            return

        queue = getattr(self, "_render_queue", [])
        batch = queue[:batch_size]
        del queue[:batch_size]

        if hasattr(self, "exp_cards_container"):
            self.exp_cards_container.setUpdatesEnabled(False)
        try:
            for exp in batch:
                card = self._create_expense_card(exp, self._render_can_del, self._render_can_edit)
                self._insert_card_before_stretch(self.exp_cards_layout, card)
        finally:
            if hasattr(self, "exp_cards_container"):
                self.exp_cards_container.setUpdatesEnabled(True)

        if queue:
            # Yield to the Qt event loop so the UI stays responsive between batches.
            QTimer.singleShot(0, lambda: self._render_next_batch(token, batch_size))
        else:
            # Only add a trailing stretch if one isn't already present (never
            # remove it, see _insert_card_before_stretch).
            count = self.exp_cards_layout.count()
            if count == 0 or self.exp_cards_layout.itemAt(count - 1).widget() is not None:
                self.exp_cards_layout.addStretch()
            # Full render pipeline complete - safe to hide the loader now and
            # let a coalesced reload (if any was requested mid-render) run.
            self._rendering = False
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            self._reload_finished()
            # Keep quietly loading the next page in the background instead of
            # waiting for the user to scroll - each page still fetches on a
            # background thread and renders in small yielded batches, so this
            # never blocks the UI; the short delay just avoids competing with
            # whatever the user is doing right after a page finishes.
            if self._has_more and not self._loading_more:
                QTimer.singleShot(150, self._load_more_expenses)

    def _create_expense_card(self, exp: dict, can_del: bool = None, can_edit: bool = None) -> QFrame:
        if can_del is None:
            can_del = SessionManager.has_permission("expenses", "delete")
        if can_edit is None:
            can_edit = SessionManager.has_permission("expenses", "edit")
        card = QFrame()
        card.setObjectName("entryCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(16)

        # Col 1: Date & Category
        c1 = QVBoxLayout()
        c1.setSpacing(2)
        date_lbl = QLabel(exp["date"])
        date_lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
        cat_color = _CATEGORY_COLORS.get(exp['category'], '#94A3B8')
        cat_lbl = QLabel(f"● {exp['category']}")
        cat_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {cat_color};")
        c1.addWidget(date_lbl)
        c1.addWidget(cat_lbl)
        lay.addLayout(c1, 2)

        # Col 2: Description
        c2 = QVBoxLayout()
        c2.setSpacing(2)
        desc_lbl = QLabel(exp["description"])
        desc_lbl.setStyleSheet("font-size: 13px;")
        desc_lbl.setWordWrap(True)
        c2.addWidget(desc_lbl)
        lay.addLayout(c2, 4)

        # Col 3: Amount
        amt_lbl = QLabel(f"₱ {exp['amount']:,.2f}")
        amt_lbl.setStyleSheet("font-weight: 800; font-size: 14px; color: #EF4444;")
        amt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(amt_lbl, 2)

        # Col 4: Edit / Delete Action Buttons
        if can_edit:
            edit_btn = QPushButton()
            edit_btn.setIcon(get_icon("edit", color="#9CA3AF", size=QSize(14, 14)))
            edit_btn.setIconSize(QSize(14, 14))
            edit_btn.setFixedSize(32, 32)
            edit_btn.setStyleSheet("background: transparent; border: none;")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setToolTip("Edit expense")
            edit_btn.clicked.connect(lambda _, e=exp: self._open_edit_expense(e))
            lay.addWidget(edit_btn, alignment=Qt.AlignVCenter)

        if can_del:
            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(14, 14))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete expense")
            del_btn.clicked.connect(lambda _, e=exp: self._delete_expense(e))
            lay.addWidget(del_btn, alignment=Qt.AlignVCenter)

        return card

    def _load_kpis(self):
        # KPIs come from the whole-dataset DB aggregate (self._summary), NOT from
        # the loaded/paginated list, so the totals stay correct as the user only
        # scrolls through a subset of rows.
        summary = getattr(self, "_summary", {}) or {}
        now = datetime.now()

        total_year = float(summary.get("total_this_year", 0.0) or 0.0)
        total_month = float(summary.get("total_this_month", 0.0) or 0.0)
        by_category = summary.get("by_category", []) or []
        total_all = float(summary.get("total_all_time", 0.0) or 0.0)

        self._kpi_total.set(f"₱ {total_year:,.0f}", f"Total for {now.year}")
        self._kpi_month.set(f"₱ {total_month:,.0f}", now.strftime("%B %Y"))

        if by_category and total_all > 0:
            top = by_category[0]
            top_cat = top.get("category", "—")
            top_amt = float(top.get("total", 0.0) or 0.0)
            pct = (top_amt / total_all * 100) if total_all > 0 else 0
            self._kpi_top.set(top_cat, f"₱ {top_amt:,.0f} ({pct:.0f}% of all-time)")
        else:
            self._kpi_top.set("—", "No expenses recorded")

        # "Total (Selected Filter)" (_kpi_filtered) is intentionally NOT set
        # here - it's driven by _load_table() instead, which sums the actual
        # client-side filtered/searched list, so it includes the search text
        # too (this DB summary's total_filtered never could, since search is
        # client-side only).

    # ── Add / delete ─────────────────────────────────────────────────────────

    def _apply_description_completer(self, desc_edit):
        """Wire the description field to autocomplete from past expense
        descriptions, so staff pick an existing entry instead of retyping
        their own spelling of it each time (the recurring "Gas" / "gas" /
        "Gasoline" problem that fragments expense reporting)."""
        from PySide6.QtWidgets import QCompleter
        from PySide6.QtCore import Qt
        try:
            suggestions = repo.get_expense_description_suggestions()
        except Exception:
            suggestions = []
        if not suggestions:
            return
        completer = QCompleter(suggestions, desc_edit)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        desc_edit.setCompleter(completer)

    def _open_add_expense(self):
        if not SessionManager.has_permission("expenses", "create"):
            error(self, title="Access Denied", message="You do not have permission to record expenses.")
            return
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QDateEdit
        )
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Expense")
        dlg.setMinimumWidth(380)
        form = QFormLayout(dlg)
        form.setSpacing(12)

        date_edit = QDateEdit(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("MMM dd, yyyy")
        form.addRow("Date:", date_edit)

        cat_cb = QComboBox()
        for c in EXPENSE_CATEGORIES:
            cat_cb.addItem(c)
        form.addRow("Category:", cat_cb)

        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("Description")
        self._apply_description_completer(desc_edit)
        form.addRow("Description:", desc_edit)

        amt_edit = QLineEdit()
        amt_edit.setPlaceholderText("0.00")
        form.addRow("Amount (₱):", amt_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() != QDialog.Accepted:
            return
        try:
            amt = float(amt_edit.text().replace(",", "").strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Enter a valid amount.")
            return
        date_str = date_edit.date().toString("MMM dd, yyyy")
        repo.add_expense({
            "category": cat_cb.currentText(),
            "description": desc_edit.text().strip() or "—",
            "amount": amt,
            "date": date_str,
        })
        self.reload()
        try:
            from utils.signals import app_events
            app_events().expense_saved.emit()
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message="Expense recorded.")

    def _open_edit_expense(self, exp: dict):
        if not SessionManager.has_permission("expenses", "edit"):
            error(self, title="Access Denied", message="You do not have permission to edit expenses.")
            return
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QDateEdit
        )
        from PySide6.QtCore import QDate
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Expense")
        dlg.setMinimumWidth(380)
        form = QFormLayout(dlg)
        form.setSpacing(12)

        date_edit = QDateEdit(QDate.fromString(exp["date"], "MMM dd, yyyy"))
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("MMM dd, yyyy")
        form.addRow("Date:", date_edit)

        cat_cb = QComboBox()
        for c in EXPENSE_CATEGORIES:
            cat_cb.addItem(c)
        idx = cat_cb.findText(exp.get("category", ""))
        if idx >= 0:
            cat_cb.setCurrentIndex(idx)
        form.addRow("Category:", cat_cb)

        desc_edit = QLineEdit(exp.get("description", ""))
        desc_edit.setPlaceholderText("Description")
        self._apply_description_completer(desc_edit)
        form.addRow("Description:", desc_edit)

        amt_edit = QLineEdit(f"{exp.get('amount', 0.0):,.2f}")
        amt_edit.setPlaceholderText("0.00")
        form.addRow("Amount (₱):", amt_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() != QDialog.Accepted:
            return
        try:
            amt = float(amt_edit.text().replace(",", "").strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Enter a valid amount.")
            return
        date_str = date_edit.date().toString("MMM dd, yyyy")
        repo.update_expense(exp["id"], {
            "category": cat_cb.currentText(),
            "description": desc_edit.text().strip() or "—",
            "amount": amt,
            "date": date_str,
        })
        self.reload()
        try:
            from utils.signals import app_events
            app_events().expense_saved.emit()
            app_events().data_changed.emit()
        except Exception:
            pass
        success(self, message="Expense updated.")

    def _delete_expense(self, exp: dict):
        if not SessionManager.has_permission("expenses", "delete"):
            error(self, title="Access Denied", message="You do not have permission to delete expenses.")
            return
        if not confirm(self, title="Delete Expense",
                       message=f"Delete \"{exp['description']}\" (₱ {exp['amount']:,.2f})?",
                       confirm_label="Delete", danger=True):
            return
        repo.delete_expense(exp["id"])
        self.reload()
        try:
            from utils.signals import app_events
            app_events().expense_saved.emit()
            app_events().data_changed.emit()
        except Exception:
            pass

    def _open_import_expenses(self):
        if not SessionManager.has_permission("expenses", "create"):
            error(self, title="Access Denied", message="You do not have permission to import expenses.")
            return
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="expenses", parent=self)
        if dlg.exec():
            self.reload()
