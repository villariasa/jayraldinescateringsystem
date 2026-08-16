"""
Dedicated Expenses page — moved out of Reports so expense tracking is a
first-class module (food cost, salary, service, transport, utilities, etc.).

Card-based list + add/delete reuse the repository functions.
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QMessageBox, QComboBox, QDateEdit,
)
from PySide6.QtCore import Qt, QMargins, QSize
from PySide6.QtGui import QColor, QPainter

from utils.theme import ThemeManager
from utils.icons import btn_icon_secondary, btn_icon_red, get_icon
import utils.repository as repo
from components.dialogs import confirm, success

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
    def __init__(self):
        super().__init__()
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
        btn_add = QPushButton("  Add Expense")
        btn_add.setObjectName("primaryButton")
        btn_add.setIcon(btn_icon_secondary("plus"))
        btn_add.setIconSize(QSize(15, 15))
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("QPushButton#primaryButton { background-color: #E11D48; color: #FFFFFF; border: none; font-weight: 700; border-radius: 8px; padding: 8px 16px; } QPushButton#primaryButton:hover { background-color: #BE123C; }")
        btn_add.clicked.connect(self._open_add_expense)
        head.addWidget(btn_add)

        btn_import = QPushButton("  Import")
        btn_import.setObjectName("secondaryButton")
        btn_import.setIcon(btn_icon_secondary("export"))
        btn_import.setIconSize(QSize(15, 15))
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self._open_import_expenses)
        head.addWidget(btn_import)
        self.lay.addLayout(head)

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
        bd_title = QLabel("Breakdown by Category (This Year)")
        bd_title.setObjectName("h3")
        bd_lay.addWidget(bd_title)
        self._chart_holder = QVBoxLayout()
        bd_lay.addLayout(self._chart_holder)
        self._chart_view = None
        self.lay.addWidget(self._breakdown_card)

        # ── Expenses Cards Section ─────────────────────────────────────────
        table_card = QFrame(content)
        table_card.setObjectName("card")
        t_lay = QVBoxLayout(table_card)
        t_lay.setContentsMargins(24, 24, 24, 24)
        t_lay.setSpacing(12)

        # ── Time Filter Controls Bar ─────────────────────────────────────────
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        lbl_filter = QLabel("Filter Period:")
        lbl_filter.setStyleSheet("font-weight: 600; font-size: 13px;")
        filter_bar.addWidget(lbl_filter)

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
        self._filter_combo.setMinimumWidth(180)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self._filter_combo)

        # Custom date pickers widget
        self._custom_date_widget = QWidget()
        custom_lay = QHBoxLayout(self._custom_date_widget)
        custom_lay.setContentsMargins(0, 0, 0, 0)
        custom_lay.setSpacing(8)

        lbl_from = QLabel("From:")
        from PySide6.QtCore import QDate
        from PySide6.QtWidgets import QDateEdit
        self._dt_start = QDateEdit(QDate.currentDate().addMonths(-1))
        self._dt_start.setCalendarPopup(True)
        self._dt_start.setFixedHeight(34)
        self._dt_start.dateChanged.connect(lambda: self.reload())

        lbl_to = QLabel("To:")
        self._dt_end = QDateEdit(QDate.currentDate())
        self._dt_end.setCalendarPopup(True)
        self._dt_end.setFixedHeight(34)
        self._dt_end.dateChanged.connect(lambda: self.reload())

        custom_lay.addWidget(lbl_from)
        custom_lay.addWidget(self._dt_start)
        custom_lay.addWidget(lbl_to)
        custom_lay.addWidget(self._dt_end)
        self._custom_date_widget.setVisible(False)
        filter_bar.addWidget(self._custom_date_widget)

        filter_bar.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("muted")
        filter_bar.addWidget(self._count_lbl)
        t_lay.addLayout(filter_bar)

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

        self.reload()

    # ── Data loading ────────────────────────────────────────────────────────

    def _on_filter_changed(self, idx: int):
        is_custom = (idx == 5)
        self._custom_date_widget.setVisible(is_custom)
        self.reload()

    def _filter_expenses_list(self, expenses: list) -> list:
        if not expenses:
            return []

        opt = self._filter_combo.currentText() if hasattr(self, "_filter_combo") else "All Time"
        if opt == "All Time":
            return expenses

        from datetime import datetime, date, timedelta
        today = date.today()

        filtered = []
        for exp in expenses:
            d_str = exp.get("date", "")
            exp_d = None
            for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
                try:
                    exp_d = datetime.strptime(d_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not exp_d:
                continue

            if "Today" in opt:
                if exp_d == today:
                    filtered.append(exp)
            elif "This Week" in opt:
                start_w = today - timedelta(days=today.weekday())
                end_w = start_w + timedelta(days=6)
                if start_w <= exp_d <= end_w:
                    filtered.append(exp)
            elif "This Month" in opt:
                if exp_d.month == today.month and exp_d.year == today.year:
                    filtered.append(exp)
            elif "This Year" in opt:
                if exp_d.year == today.year:
                    filtered.append(exp)
            elif "Custom Date" in opt:
                d_start = self._dt_start.date().toPython()
                d_end = self._dt_end.date().toPython()
                if d_start <= exp_d <= d_end:
                    filtered.append(exp)

        return filtered

    def reload(self):
        all_exp = repo.get_all_expenses() or []
        self._expenses = all_exp
        self._filtered_expenses = self._filter_expenses_list(all_exp)
        self._load_table()
        self._load_kpis()
        self._load_breakdown()

    def _load_table(self):
        if hasattr(self, "exp_cards_container"):
            self.exp_cards_container.setUpdatesEnabled(False)
        try:
            while self.exp_cards_layout.count():
                item = self.exp_cards_layout.takeAt(0)
                if item:
                    w = item.widget()
                    if w:
                        w.setParent(None)
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
        total_filtered = sum(e["amount"] for e in expenses)

        now = datetime.now()
        month_total = 0.0
        for exp in expenses:
            try:
                d = datetime.strptime(exp["date"], "%b %d, %Y")
            except (ValueError, TypeError):
                continue
            if d.month == now.month and d.year == now.year:
                month_total += exp["amount"]

        opt = self._filter_combo.currentText() if hasattr(self, "_filter_combo") else "All Time"
        self._kpi_total.set(f"₱ {total_filtered:,.0f}", opt)
        self._kpi_month.set(f"₱ {month_total:,.0f}", now.strftime("%B %Y"))

        # Category breakdown count
        cat_totals = {}
        for exp in expenses:
            cat = exp.get("category", "General")
            cat_totals[cat] = cat_totals.get(cat, 0.0) + exp.get("amount", 0.0)

        if cat_totals:
            top_cat = max(cat_totals.items(), key=lambda x: x[1])
            self._kpi_top.set(top_cat[0], f"₱ {top_cat[1]:,.0f} ({opt})")
        else:
            self._kpi_top.set("—", "No data yet")

    def _load_breakdown(self):
        if self._chart_view is not None:
            self._chart_holder.removeWidget(self._chart_view)
            self._chart_view.deleteLater()
            self._chart_view = None

        try:
            breakdown = repo.get_expense_breakdown(datetime.now().year)
        except Exception:
            breakdown = []
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
        success(self, message="Expense recorded.")

    def _delete_expense(self, exp: dict):
        if not confirm(self, title="Delete Expense",
                       message=f"Delete \"{exp['description']}\" (₱ {exp['amount']:,.2f})?",
                       confirm_label="Delete", danger=True):
            return
        repo.delete_expense(exp["id"])
        self.reload()

    def _open_import_expenses(self):
        from components.import_dialog import ImportWizardDialog
        dlg = ImportWizardDialog(default_entity="expenses", parent=self)
        if dlg.exec():
            self.reload()
