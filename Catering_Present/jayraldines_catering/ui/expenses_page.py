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
        for c in (self._kpi_total, self._kpi_month, self._kpi_top):
            kpi_row.addWidget(c)
        self.lay.addLayout(kpi_row)

        # ── Category breakdown ──────────────────────────────────────────────
        self._breakdown_card = QFrame(content)
        self._breakdown_card.setObjectName("card")
        bd_lay = QVBoxLayout(self._breakdown_card)
        bd_lay.setContentsMargins(28, 24, 28, 20)
        bd_lay.setSpacing(10)
        self._bd_title = QLabel("Breakdown by Category")
        self._bd_title.setObjectName("h3")
        bd_lay.addWidget(self._bd_title)
        self._chart_holder = QVBoxLayout()
        bd_lay.addLayout(self._chart_holder)
        self._chart_view = None
        self.lay.addWidget(self._breakdown_card)

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

        t_lay.addWidget(self.exp_cards_container)
        self.lay.addWidget(table_card)
        self.lay.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)
        self._loader = LoadingOverlay(self, "Loading expenses & analytics...")

        try:
            from utils.signals import app_events
            app_events().expense_saved.connect(self._mark_dirty_and_reload)
            app_events().data_changed.connect(self._mark_dirty)
        except Exception:
            pass

    def _mark_dirty(self):
        self._dirty = True

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self.reload()

    # ── Data loading & Filtering ────────────────────────────────────────────

    def _on_search_changed(self, text: str):
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._load_kpis()
        self._load_breakdown()

    def _on_filter_changed(self, idx: int):
        is_custom = (idx == 5)
        self._custom_date_widget.setVisible(is_custom)
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._load_kpis()
        self._load_breakdown()

    def _on_month_changed(self, idx: int):
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._load_kpis()
        self._load_breakdown()

    def _on_date_range_changed(self):
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._load_kpis()
        self._load_breakdown()

    def _reset_filters(self):
        if hasattr(self, "_search_input"):
            self._search_input.blockSignals(True)
            self._search_input.clear()
            self._search_input.blockSignals(False)
        if hasattr(self, "_filter_combo"):
            self._filter_combo.blockSignals(True)
            self._filter_combo.setCurrentIndex(0)
            self._filter_combo.blockSignals(False)
        if hasattr(self, "_month_combo"):
            self._month_combo.blockSignals(True)
            self._month_combo.setCurrentIndex(0)
            self._month_combo.blockSignals(False)
        if hasattr(self, "_custom_date_widget"):
            self._custom_date_widget.setVisible(False)
        self._filtered_expenses = self._filter_expenses_list(getattr(self, "_expenses", []))
        self._load_table()
        self._load_kpis()
        self._load_breakdown()

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
            if period_opt != "All Time" and exp_d:
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
        if hasattr(self, "btn_add"):
            self.btn_add.setEnabled(can_create)
            self.btn_add.setVisible(can_create)
        if hasattr(self, "btn_import"):
            self.btn_import.setEnabled(can_create)
            self.btn_import.setVisible(can_create)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_permissions()
        if getattr(self, "_dirty", True):
            self.reload()

    def reload(self):
        self._dirty = False
        self.refresh_permissions()

        # Instant render from pre-loaded memory cache if available
        from utils.data_cache import DataCache
        cached = DataCache.get("expenses")
        if cached is not None and not getattr(self, "_has_loaded_once", False):
            self._has_loaded_once = True
            if hasattr(self, "_loader"):
                self._loader.show_overlay("Loading expenses & analytics...")
                QTimer.singleShot(60, lambda: self._on_expenses_loaded(cached))
            else:
                self._on_expenses_loaded(cached)
            return

        if hasattr(self, "_loader"):
            self._loader.show_overlay("Loading expenses & analytics...")
        run_async(self, repo.get_all_expenses, self._on_expenses_loaded_and_cache)

    def _on_expenses_loaded_and_cache(self, data):
        from utils.data_cache import DataCache
        if data is not None:
            DataCache.set("expenses", data)
        self._on_expenses_loaded(data)

    def _on_expenses_loaded(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
            all_exp = data or []
            self._expenses = all_exp
            self._filtered_expenses = self._filter_expenses_list(all_exp)
            self._load_table()
            self._load_kpis()
            self._load_breakdown()
        finally:
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()

    def _load_table(self):
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
            else:
                for exp in expenses:
                    card = self._create_expense_card(exp)
                    self.exp_cards_layout.addWidget(card)
                self.exp_cards_layout.addStretch()

            n = len(expenses)
            self._count_lbl.setText(f"{n} record{'s' if n != 1 else ''}")
        finally:
            if hasattr(self, "exp_cards_container"):
                self.exp_cards_container.setUpdatesEnabled(True)

    def _create_expense_card(self, exp: dict) -> QFrame:
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

        # Col 4: Delete Action Button
        can_del = SessionManager.has_permission("expenses", "delete")
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
        expenses = getattr(self, "_filtered_expenses", getattr(self, "_expenses", []))
        total_filtered = sum(e.get("amount", 0.0) for e in expenses)

        now = datetime.now()
        month_opt = self._month_combo.currentText() if hasattr(self, "_month_combo") else "All Months"
        period_opt = self._filter_combo.currentText() if hasattr(self, "_filter_combo") else "All Time"
        filter_desc = month_opt if month_opt != "All Months" else period_opt

        self._kpi_total.set(f"₱ {total_filtered:,.0f}", f"Total for {filter_desc}")

        # This Month total (Current calendar month across all recorded expenses)
        all_raw = getattr(self, "_expenses", [])
        cur_month_total = 0.0
        for exp in all_raw:
            try:
                d = datetime.strptime(str(exp["date"]), "%b %d, %Y")
            except (ValueError, TypeError):
                continue
            if d.month == now.month and d.year == now.year:
                cur_month_total += exp.get("amount", 0.0)

        self._kpi_month.set(f"₱ {cur_month_total:,.0f}", now.strftime("%B %Y"))

        # Top Category for the selected month / active filter
        cat_totals = {}
        for exp in expenses:
            cat = exp.get("category", "General")
            cat_totals[cat] = cat_totals.get(cat, 0.0) + exp.get("amount", 0.0)

        if cat_totals and total_filtered > 0:
            top_cat, top_amt = max(cat_totals.items(), key=lambda x: x[1])
            pct = (top_amt / total_filtered * 100) if total_filtered > 0 else 0
            self._kpi_top.set(top_cat, f"₱ {top_amt:,.0f} ({pct:.0f}% in {filter_desc})")
        else:
            self._kpi_top.set("—", f"No expenses ({filter_desc})")

    def _load_breakdown(self):
        if self._chart_view is not None:
            self._chart_holder.removeWidget(self._chart_view)
            self._chart_view.deleteLater()
            self._chart_view = None

        expenses = getattr(self, "_filtered_expenses", getattr(self, "_expenses", []))
        
        # Calculate breakdown from filtered expenses
        cat_totals = {}
        for exp in expenses:
            cat = exp.get("category", "Other")
            cat_totals[cat] = cat_totals.get(cat, 0.0) + exp.get("amount", 0.0)

        breakdown = [{"category": c, "total": t} for c, t in cat_totals.items() if t > 0]
        breakdown.sort(key=lambda x: x["total"], reverse=True)

        month_opt = self._month_combo.currentText() if hasattr(self, "_month_combo") else "All Months"
        period_opt = self._filter_combo.currentText() if hasattr(self, "_filter_combo") else "All Time"
        filter_desc = month_opt if month_opt != "All Months" else period_opt
        if hasattr(self, "_bd_title"):
            self._bd_title.setText(f"Breakdown by Category ({filter_desc})")

        if not breakdown:
            self._breakdown_card.hide()
            return
        self._breakdown_card.show()

        from PySide6.QtCharts import QChart, QChartView, QPieSeries, QLegend
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QToolTip

        series = QPieSeries()
        series.setHoleSize(0.55)
        total_exp = sum(row["total"] for row in breakdown) or 1.0
        label_color = QColor("#0F172A" if _is_light() else "#F9FAFB")

        for row in breakdown:
            cat = row["category"]
            tot = row["total"]
            color_hex = _CATEGORY_COLORS.get(cat, "#94A3B8")
            sl = series.append(f"{cat} (₱{tot:,.0f})", tot)
            sl.setColor(QColor(color_hex))
            sl.setLabelColor(label_color)

            def _make_hover(s=sl, c=cat, t=tot, col=color_hex):
                def _on_hover(state):
                    s.setExploded(state)
                    s.setLabelVisible(state)
                    if state:
                        pct = (t / total_exp) * 100
                        QToolTip.showText(
                            QCursor.pos(),
                            f"<b style='color:{col};'>{c}</b><br>"
                            f"Amount: <b>₱ {t:,.2f}</b><br>"
                            f"Share: <b>{pct:.1f}%</b>"
                        )
                    else:
                        QToolTip.hideText()
                return _on_hover

            sl.hovered.connect(_make_hover())

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundBrush(Qt.transparent)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.legend().setAlignment(Qt.AlignRight)
        chart.legend().setMarkerShape(QLegend.MarkerShape.MarkerShapeCircle)
        chart.legend().setLabelColor(QColor("#5B6B84" if _is_light() else "#9CA3AF"))

        self._chart_view = QChartView(chart)
        self._chart_view.setRenderHint(QPainter.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent;")
        self._chart_view.setMinimumHeight(240)
        self._chart_holder.addWidget(self._chart_view)

    # ── Add / delete ─────────────────────────────────────────────────────────

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
