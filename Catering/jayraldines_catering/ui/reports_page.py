import sys
import csv
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QFrame, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QScrollArea,
                               QMessageBox, QToolTip, QFileDialog)
from PySide6.QtCore import Qt, QMargins, QPointF, QSize
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPen, QCursor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted
import utils.repository as repo

from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QAreaSeries,
                              QPieSeries, QBarCategoryAxis, QBarSeries, QBarSet,
                              QValueAxis, QLegend)


def _chart_view(chart: QChart) -> QChartView:
    chart.setBackgroundBrush(Qt.transparent)
    chart.setMargins(QMargins(0, 0, 0, 0))
    chart.legend().setLabelColor(QColor("#9CA3AF"))
    chart.legend().setAlignment(Qt.AlignBottom)
    v = QChartView(chart)
    v.setRenderHint(QPainter.Antialiasing)
    v.setStyleSheet("background: transparent;")
    return v


def _axis_style(axis, label_color="#9CA3AF"):
    axis.setLabelsColor(QColor(label_color))
    axis.setLinePenColor(Qt.transparent)
    axis.setGridLineColor(QColor("#243244"))


class HoverCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


def create_status_badge(text):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    lbl = QLabel(f" {text} ")
    if "Completed" in text or "Confirmed" in text:
        lbl.setObjectName("badgeSuccess")
    else:
        lbl.setObjectName("badgeWarning")
    layout.addWidget(lbl)
    return widget


def create_pax_limit_badge(pax, limit_status):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    lbl_pax = QLabel(str(pax))
    lbl_pax.setStyleSheet("font-weight: 700; font-size: 13px;")
    layout.addWidget(lbl_pax)
    if limit_status:
        badge = QLabel(limit_status)
        if limit_status == "LIMIT REACHED":
            badge.setObjectName("badgeDanger")
        else:
            badge.setObjectName("badgeWarning")
        layout.addWidget(badge)
    return widget


# ─────────────────────────────────────────────
# CHART 1: Income Trend (Area)
# ─────────────────────────────────────────────
class IncomeAreaChart(QVBoxLayout):
    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Income Trend (Year-to-Date)")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        db_data = repo.get_monthly_income()
        if db_data:
            self._months = [r["month"] for r in db_data]
            values = [r["revenue"] / 1000 for r in db_data]
        else:
            self._months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            values = [0] * 6

        # Pin all series as instance vars — GC will NOT collect them
        self._upper = QLineSeries()
        pen = QPen(QColor("#E11D48"))
        pen.setWidth(3)
        self._upper.setPen(pen)
        for i, v in enumerate(values):
            self._upper.append(i, v)

        self._lower = QLineSeries()
        for i in range(len(values)):
            self._lower.append(i, 0)

        self._area = QAreaSeries(self._upper, self._lower)
        grad = QLinearGradient(0, 0, 0, 300)
        grad.setColorAt(0.0, QColor(225, 29, 72, 80))
        grad.setColorAt(1.0, QColor(225, 29, 72, 0))
        self._area.setBrush(grad)
        self._area.setPen(Qt.NoPen)

        self._chart = QChart()
        self._chart.addSeries(self._area)
        self._chart.addSeries(self._upper)
        self._chart.legend().hide()
        self._chart.setAnimationOptions(QChart.SeriesAnimations)

        self._ax = QBarCategoryAxis()
        self._ax.append(self._months)
        _axis_style(self._ax)
        self._chart.addAxis(self._ax, Qt.AlignBottom)
        self._area.attachAxis(self._ax)
        self._upper.attachAxis(self._ax)

        self._ay = QValueAxis()
        self._ay.setRange(0, max(values) * 1.2 if values else 100)
        self._ay.setLabelFormat("%dk")
        _axis_style(self._ay)
        self._chart.addAxis(self._ay, Qt.AlignLeft)
        self._area.attachAxis(self._ay)
        self._upper.attachAxis(self._ay)

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(260)
        self._view.setRubberBand(QChartView.RubberBand.RectangleRubberBand)

        self._upper.hovered.connect(
            lambda pt, state: self._on_hover(pt, state, self._months)
        )
        self.addWidget(self._view)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._reset_btn = QPushButton("Reset Zoom")
        self._reset_btn.setObjectName("secondaryButton")
        self._reset_btn.clicked.connect(self._chart.zoomReset)
        btn_row.addWidget(self._reset_btn)
        self.addLayout(btn_row)

    def _on_hover(self, point, state, months):
        if state:
            idx = int(round(point.x()))
            if 0 <= idx < len(months):
                QToolTip.showText(
                    QCursor.pos(),
                    f"<b>{months[idx]}</b><br>Revenue: <b>PHP {point.y():.0f}k</b>"
                )
        else:
            QToolTip.hideText()


# ─────────────────────────────────────────────
# CHART 2: Payment Methods (Donut)
# ─────────────────────────────────────────────
class PaymentDonutChart(QVBoxLayout):
    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Payment Methods")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        _COLORS = ["#E11D48", "#F59E0B", "#3B82F6", "#22C55E", "#8B5CF6", "#6B7280"]
        db_data = repo.get_payment_methods()
        if db_data:
            data = {r["method"]: (r["total"], _COLORS[i % len(_COLORS)]) for i, r in enumerate(db_data)}
        else:
            data = {"No Data": (1, "#374151")}

        self._series = QPieSeries()
        self._series.setHoleSize(0.55)
        self._slices = []
        for label, (value, color) in data.items():
            sl = self._series.append(label, value)
            sl.setColor(QColor(color))
            sl.setLabelColor(QColor("#F9FAFB"))
            sl.hovered.connect(
                lambda state, s=sl, c=color: self._on_hover(s, state, c)
            )
            self._slices.append(sl)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().setAlignment(Qt.AlignRight)
        self._chart.legend().setLabelColor(QColor("#9CA3AF"))

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(220)
        self.addWidget(self._view)

    def _on_hover(self, sl, state, color):
        sl.setExploded(state)
        sl.setLabelVisible(state)
        if state:
            QToolTip.showText(
                QCursor.pos(),
                f"<b>{sl.label()}</b>: {sl.value():.0f}%"
            )
        else:
            QToolTip.hideText()


# ─────────────────────────────────────────────
# CHART 3: Monthly Revenue Breakdown (Bar)
# ─────────────────────────────────────────────
class MonthlyRevenueChart(QVBoxLayout):
    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Monthly Revenue Breakdown")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        db_data = repo.get_monthly_income()
        if db_data:
            months  = [r["month"] for r in db_data]
            revenue = [r["revenue"] for r in db_data]
            target  = [400000] * len(months)
        else:
            months  = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            revenue = [0] * 6
            target  = [400000] * 6

        self._bar_rev = QBarSet("Revenue")
        self._bar_rev.setColor(QColor("#E11D48"))
        self._bar_rev.setLabelColor(QColor("#F9FAFB"))

        self._bar_tgt = QBarSet("Target")
        self._bar_tgt.setColor(QColor("#374151"))
        self._bar_tgt.setLabelColor(QColor("#9CA3AF"))

        for v, t in zip(revenue, target):
            self._bar_rev.append(v / 1000)
            self._bar_tgt.append(t / 1000)

        self._series = QBarSeries()
        self._series.append(self._bar_rev)
        self._series.append(self._bar_tgt)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)

        self._ax = QBarCategoryAxis()
        self._ax.append(months)
        _axis_style(self._ax)
        self._chart.addAxis(self._ax, Qt.AlignBottom)
        self._series.attachAxis(self._ax)

        max_rev = max(revenue + target) if (revenue or target) else 700000
        self._ay = QValueAxis()
        self._ay.setRange(0, max_rev / 1000 * 1.2)
        self._ay.setLabelFormat("%dk")
        _axis_style(self._ay)
        self._chart.addAxis(self._ay, Qt.AlignLeft)
        self._series.attachAxis(self._ay)

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(260)
        self.addWidget(self._view)


# ─────────────────────────────────────────────
# CHART 4: Top Menu Items (Horizontal Bar)
# ─────────────────────────────────────────────
class TopMenuItemsChart(QVBoxLayout):
    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Top-Selling Menu Items")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        db_data = repo.get_top_menu_items()
        _MAX = 18
        if db_data:
            items  = [(r["item"][:_MAX] + "…") if len(r["item"]) > _MAX else r["item"] for r in db_data]
            orders = [r["count"] for r in db_data]
        else:
            items  = ["No Data"]
            orders = [0]

        self._bar_set = QBarSet("Orders")
        self._bar_set.setColor(QColor("#F59E0B"))
        self._bar_set.setLabelColor(QColor("#F9FAFB"))
        for v in orders:
            self._bar_set.append(v)

        self._series = QBarSeries()
        self._series.append(self._bar_set)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().hide()

        self._ax = QBarCategoryAxis()
        self._ax.append(items)
        _axis_style(self._ax)
        self._chart.addAxis(self._ax, Qt.AlignBottom)
        self._series.attachAxis(self._ax)

        self._ay = QValueAxis()
        self._ay.setRange(0, max(orders) * 1.2 if orders else 10)
        self._ay.setLabelFormat("%d")
        _axis_style(self._ay)
        self._chart.addAxis(self._ay, Qt.AlignLeft)
        self._series.attachAxis(self._ay)

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(220)
        self.addWidget(self._view)


# ─────────────────────────────────────────────
# CHART 5: Customer Order Frequency (Pie)
# ─────────────────────────────────────────────
class CustomerFrequencyChart(QVBoxLayout):
    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Customer Order Frequency")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        _COLORS = ["#E11D48", "#F59E0B", "#3B82F6", "#22C55E", "#6B7280", "#8B5CF6"]
        db_data = repo.get_customer_order_frequency()
        customers = [r["name"]  for r in db_data] if db_data else ["No Data"]
        counts    = [r["count"] for r in db_data] if db_data else [1]
        colors    = [_COLORS[i % len(_COLORS)] for i in range(len(customers))]

        self._series = QPieSeries()
        self._slices = []
        for label, count, color in zip(customers, counts, colors):
            sl = self._series.append(f"{label} ({count})", count)
            sl.setColor(QColor(color))
            sl.setLabelColor(QColor("#F9FAFB"))
            self._slices.append(sl)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().setAlignment(Qt.AlignRight)
        self._chart.legend().setLabelColor(QColor("#9CA3AF"))

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(220)
        self.addWidget(self._view)


# ─────────────────────────────────────────────
# MAIN REPORTS PAGE
# ─────────────────────────────────────────────
class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainBackground")

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_content = QWidget(self.scroll_area)
        self.scroll_content.setStyleSheet("background: transparent;")

        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(32)

        # ── HEADER ──────────────────────────────────────────────────────────
        self._header_row = QHBoxLayout()
        self._v_title    = QVBoxLayout()

        self._title_lbl = QLabel("Reports & Analytics", self.scroll_content)
        self._title_lbl.setObjectName("pageTitle")

        self._sub_lbl = QLabel("Track performance, income, and booking trends.", self.scroll_content)
        self._sub_lbl.setObjectName("subtitle")

        self._v_title.addWidget(self._title_lbl)
        self._v_title.addWidget(self._sub_lbl)
        self._header_row.addLayout(self._v_title)
        self._header_row.addStretch()

        self._btn_export = QPushButton("  Export CSV", self.scroll_content)
        self._btn_export.setObjectName("secondaryButton")
        self._btn_export.setIcon(btn_icon_secondary("export"))
        self._btn_export.setIconSize(QSize(16, 16))
        self._btn_export.clicked.connect(self._export_csv)
        self._header_row.addWidget(self._btn_export)
        self.main_layout.addLayout(self._header_row)

        # ── KPI CARDS ────────────────────────────────────────────────────────
        self._kpi_layout = QHBoxLayout()
        self._kpi_layout.setSpacing(24)

        kpis = repo.get_report_kpis()
        total_bk  = kpis.get("total_bookings", 0)
        total_pax = kpis.get("total_pax", 0)
        revenue   = kpis.get("total_revenue", 0.0)
        unpaid    = kpis.get("unpaid_amount", 0.0)
        today_bk  = kpis.get("today_bookings", 0)
        week_bk   = kpis.get("week_bookings", 0)

        self._kpi_cards = [
            self._kpi("Total Bookings",   str(total_bk),          f"{today_bk} Today | {week_bk} This Week"),
            self._kpi("Total Pax Booked", f"{total_pax:,}",        "All confirmed bookings", "#22C55E"),
            self._kpi("Total Revenue",    f"PHP {revenue:,.0f}",   "All-time revenue", "#22C55E"),
            self._kpi("Unpaid Invoices",  f"PHP {unpaid:,.0f}",    "Outstanding balance", "#EF4444"),
        ]
        for card in self._kpi_cards:
            self._kpi_layout.addWidget(card)
        self.main_layout.addLayout(self._kpi_layout)

        # ── ROW 1: Income Area + Payment Donut ───────────────────────────────
        self._row1 = QHBoxLayout()
        self._row1.setSpacing(24)

        self._income_chart_layout = IncomeAreaChart()   # instance var → stays alive
        self.line_card = QFrame(self.scroll_content)
        self.line_card.setObjectName("card")
        self.line_card.setLayout(self._income_chart_layout)
        self.line_card.layout().setContentsMargins(28, 24, 28, 20)
        self._row1.addWidget(self.line_card, 3)

        self._donut_chart_layout = PaymentDonutChart()   # instance var → stays alive
        self.donut_card = QFrame(self.scroll_content)
        self.donut_card.setObjectName("card")
        self.donut_card.setLayout(self._donut_chart_layout)
        self.donut_card.layout().setContentsMargins(28, 24, 28, 20)
        self._row1.addWidget(self.donut_card, 2)

        self.main_layout.addLayout(self._row1)

        # ── ROW 2: Monthly Revenue + Top Menu Items ──────────────────────────
        self._row2 = QHBoxLayout()
        self._row2.setSpacing(24)

        self._monthly_chart_layout = MonthlyRevenueChart()   # instance var
        self.monthly_card = QFrame(self.scroll_content)
        self.monthly_card.setObjectName("card")
        self.monthly_card.setLayout(self._monthly_chart_layout)
        self.monthly_card.layout().setContentsMargins(28, 24, 28, 20)
        self._row2.addWidget(self.monthly_card, 2)

        self._top_menu_chart_layout = TopMenuItemsChart()   # instance var
        self.top_menu_card = QFrame(self.scroll_content)
        self.top_menu_card.setObjectName("card")
        self.top_menu_card.setLayout(self._top_menu_chart_layout)
        self.top_menu_card.layout().setContentsMargins(28, 24, 28, 20)
        self._row2.addWidget(self.top_menu_card, 2)

        self.main_layout.addLayout(self._row2)

        # ── ROW 3: Customer Frequency (full width) ───────────────────────────
        self._freq_chart_layout = CustomerFrequencyChart()   # instance var
        self.freq_card = QFrame(self.scroll_content)
        self.freq_card.setObjectName("card")
        self.freq_card.setLayout(self._freq_chart_layout)
        self.freq_card.layout().setContentsMargins(28, 24, 28, 20)
        self.main_layout.addWidget(self.freq_card)

        # ── RECENT BOOKINGS TABLE ────────────────────────────────────────────
        self.table_card = HoverCard(self.scroll_content)
        self._t_layout = QVBoxLayout(self.table_card)
        self._t_layout.setContentsMargins(24, 24, 24, 24)
        self._t_layout.setSpacing(16)

        self._t_head = QHBoxLayout()
        self._t_head_lbl = QLabel("Recent Booking Statistics", self.table_card)
        self._t_head_lbl.setObjectName("h2")
        self._t_head.addWidget(self._t_head_lbl)
        self._t_head.addStretch()
        self._t_layout.addLayout(self._t_head)

        self.table = QTableWidget(5, 5, self.table_card)
        self.table.setHorizontalHeaderLabels(["ID & DATE", "CLIENT", "PACKAGE", "PAX", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(320)

        db_bookings = repo.get_all_bookings() or []
        self.table.setRowCount(len(db_bookings))
        self._table_widgets = []
        for row, b in enumerate(db_bookings):
            self.table.setRowHeight(row, 64)
            pax_val = int(b.get("pax", 0))
            limit_status = "LIMIT REACHED" if pax_val >= 600 else ("NEAR LIMIT" if pax_val >= 400 else "")
            id_lbl = QLabel(
                f"<span style='font-weight:700;font-size:13px;'>{b.get('id','')}</span>"
                f"<br><span style='font-size:11px;color:#9CA3AF;'>{b.get('date','')}</span>"
            )
            client_lbl   = QLabel(f"<span style='font-weight:600;font-size:13px;'>{b.get('name','')}</span>")
            package_lbl  = QLabel(f"<span style='font-size:13px;'>{b.get('package','—')}</span>")
            pax_badge    = create_pax_limit_badge(pax_val, limit_status)
            status_badge = create_status_badge(b.get('status','').capitalize())
            self._table_widgets.extend([id_lbl, client_lbl, package_lbl, pax_badge, status_badge])
            self.table.setCellWidget(row, 0, id_lbl)
            self.table.setCellWidget(row, 1, client_lbl)
            self.table.setCellWidget(row, 2, package_lbl)
            self.table.setCellWidget(row, 3, pax_badge)
            self.table.setCellWidget(row, 4, status_badge)

        self._t_layout.addWidget(self.table)
        self.main_layout.addWidget(self.table_card)

        # ── Final assembly ────────────────────────────────────────────────────
        self.scroll_area.setWidget(self.scroll_content)
        self.root_layout.addWidget(self.scroll_area)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _kpi(self, title, val, sub, sub_color=None):
        card = HoverCard(self.scroll_content)
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)

        top   = QHBoxLayout()
        lbl_t = QLabel(title.upper(), card)
        lbl_t.setObjectName("kpiLabel")
        top.addWidget(lbl_t)
        top.addStretch()
        lay.addLayout(top)

        lbl_v = QLabel(val, card)
        lbl_v.setObjectName("kpiValue")
        lay.addWidget(lbl_v)

        lbl_s = QLabel(sub, card)
        if sub_color:
            lbl_s.setStyleSheet(f"color: {sub_color}; font-weight: 600; font-size: 12px;")
        else:
            lbl_s.setObjectName("subtitle")
        lay.addWidget(lbl_s)
        lay.addStretch()
        return card

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Reports", "reports.csv", "CSV Files (*.csv)"
        )
        if not path:
            return

        rows = repo.get_all_bookings() or [
            {"id": "BKG-001", "date": "Oct 24, 2026", "name": "TechCorp Inc.",
             "pax": "45",  "total": "PHP 45,000",  "status": "CONFIRMED"},
            {"id": "BKG-002", "date": "Oct 25, 2026", "name": "Smith Wedding",
             "pax": "58",  "total": "PHP 120,000", "status": "PENDING"},
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Date", "Client", "Pax", "Total", "Status"])
            for b in rows:
                writer.writerow([
                    b.get("id"),   b.get("date"), b.get("name"),
                    b.get("pax"),  b.get("total"), b.get("status"),
                ])

        QMessageBox.information(self, "Export", f"Exported to:\n{path}")