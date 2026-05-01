import sys
import csv
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QFrame, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QScrollArea,
                               QMessageBox, QToolTip, QFileDialog, QMenu, QSizePolicy)
from PySide6.QtCore import Qt, QMargins, QPointF, QSize
from PySide6.QtGui import QAction
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPen, QCursor

from utils import exporter as _exporter

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted
from utils.theme import ThemeManager
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


def _axis_style(axis, label_color=None):
    if label_color is None:
        label_color = "#64748B" if not ThemeManager().is_dark() else "#9CA3AF"
    axis.setLabelsColor(QColor(label_color))
    axis.setLinePenColor(Qt.transparent)
    axis.setGridLineColor(QColor("#E2E8F0") if not ThemeManager().is_dark() else QColor("#243244"))


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
            _lbl_c = "#0F172A" if not ThemeManager().is_dark() else "#F9FAFB"
            sl.setLabelColor(QColor(_lbl_c))
            sl.hovered.connect(
                lambda state, s=sl, c=color: self._on_hover(s, state, c)
            )
            self._slices.append(sl)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().setAlignment(Qt.AlignRight)
        _leg_c = "#64748B" if not ThemeManager().is_dark() else "#9CA3AF"
        self._chart.legend().setLabelColor(QColor(_leg_c))

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

        self._months  = months
        self._revenue = revenue
        self._target  = target

        self._bar_rev = QBarSet("Revenue")
        self._bar_rev.setColor(QColor("#E11D48"))
        _lbl_c = "#0F172A" if not ThemeManager().is_dark() else "#F9FAFB"
        self._bar_rev.setLabelColor(QColor(_lbl_c))

        self._bar_tgt = QBarSet("Target")
        _tgt_c = "#CBD5E1" if not ThemeManager().is_dark() else "#374151"
        self._bar_tgt.setColor(QColor(_tgt_c))
        _muted_c = "#64748B" if not ThemeManager().is_dark() else "#9CA3AF"
        self._bar_tgt.setLabelColor(QColor(_muted_c))

        for v, t in zip(revenue, target):
            self._bar_rev.append(v / 1000)
            self._bar_tgt.append(t / 1000)

        self._bar_rev.hovered.connect(self._on_hover_rev)
        self._bar_tgt.hovered.connect(self._on_hover_tgt)

        self._series = QBarSeries()
        self._series.append(self._bar_rev)
        self._series.append(self._bar_tgt)
        self._series.setLabelsVisible(False)

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
        self._view.setRubberBand(QChartView.RubberBand.RectangleRubberBand)
        self.addWidget(self._view)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._reset_btn = QPushButton("Reset Zoom")
        self._reset_btn.setObjectName("secondaryButton")
        self._reset_btn.clicked.connect(self._chart.zoomReset)
        btn_row.addWidget(self._reset_btn)
        self.addLayout(btn_row)

    def _on_hover_rev(self, state, index):
        if state and 0 <= index < len(self._months):
            rev = self._revenue[index]
            tgt = self._target[index]
            pct = (rev / tgt * 100) if tgt else 0
            hit = "✅ Target hit!" if rev >= tgt else f"⚠ {pct:.0f}% of target"
            QToolTip.showText(
                QCursor.pos(),
                f"<b style='color:#E11D48;'>{self._months[index]}</b><br>"
                f"Revenue: <b>₱ {rev:,.0f}</b><br>"
                f"Target: ₱ {tgt:,.0f}<br>{hit}"
            )
        else:
            QToolTip.hideText()

    def _on_hover_tgt(self, state, index):
        if state and 0 <= index < len(self._months):
            tgt = self._target[index]
            rev = self._revenue[index]
            gap = tgt - rev
            QToolTip.showText(
                QCursor.pos(),
                f"<b>{self._months[index]}</b> — Target<br>"
                f"Target: <b>₱ {tgt:,.0f}</b><br>"
                f"{'Gap: ₱ ' + f'{gap:,.0f}' if gap > 0 else '✅ Achieved'}"
            )
        else:
            QToolTip.hideText()


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
        _lbl_c2 = "#0F172A" if not ThemeManager().is_dark() else "#F9FAFB"
        self._bar_set.setLabelColor(QColor(_lbl_c2))
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
# CHART 5: Top Booking Locations (Horizontal Bar)
# ─────────────────────────────────────────────
class TopLocationsChart(QVBoxLayout):
    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Top Customer Areas (Where Orders Come From)")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        db_data = repo.get_top_locations(limit=10)
        _MAX = 30
        if db_data:
            venues = [(r["venue"][:_MAX] + "…") if len(r["venue"]) > _MAX else r["venue"] for r in db_data]
            counts = [r["count"] for r in db_data]
        else:
            venues = ["No Data"]
            counts = [0]

        self._venues = venues
        self._counts = counts

        self._bar_set = QBarSet("Orders")
        self._bar_set.setColor(QColor("#8B5CF6"))
        _lbl_c = "#0F172A" if not ThemeManager().is_dark() else "#F9FAFB"
        self._bar_set.setLabelColor(QColor(_lbl_c))
        for v in counts:
            self._bar_set.append(v)
        self._bar_set.hovered.connect(self._on_hover)

        self._series = QBarSeries()
        self._series.append(self._bar_set)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().hide()

        self._ax = QBarCategoryAxis()
        self._ax.append(venues)
        _axis_style(self._ax)
        self._chart.addAxis(self._ax, Qt.AlignBottom)
        self._series.attachAxis(self._ax)

        self._ay = QValueAxis()
        self._ay.setRange(0, max(counts) * 1.2 if counts else 10)
        self._ay.setLabelFormat("%d")
        _axis_style(self._ay)
        self._chart.addAxis(self._ay, Qt.AlignLeft)
        self._series.attachAxis(self._ay)

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(240)
        self.addWidget(self._view)

    def _on_hover(self, state, index):
        if state and 0 <= index < len(self._venues):
            QToolTip.showText(
                QCursor.pos(),
                f"<b>{self._venues[index]}</b><br>Orders: <b>{self._counts[index]}</b>"
            )
        else:
            QToolTip.hideText()


# ─────────────────────────────────────────────
# CHART 6: Customer Order Frequency (Pie)
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
        self._series.setHoleSize(0.0)
        self._slices = []
        total = sum(counts) or 1
        _lbl_c3 = "#0F172A" if not ThemeManager().is_dark() else "#F9FAFB"
        for label, count, color in zip(customers, counts, colors):
            sl = self._series.append(f"{label} ({count})", count)
            sl.setColor(QColor(color))
            sl.setLabelColor(QColor(_lbl_c3))
            sl.setBorderColor(Qt.transparent)
            sl.hovered.connect(
                lambda state, s=sl, c=color, n=label, v=count: self._on_hover(s, state, c, n, v, total)
            )
            self._slices.append(sl)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().setAlignment(Qt.AlignRight)
        _leg_c2 = "#64748B" if not ThemeManager().is_dark() else "#9CA3AF"
        self._chart.legend().setLabelColor(QColor(_leg_c2))
        self._chart.legend().setMarkerShape(QLegend.MarkerShapeCircle)

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(260)
        self.addWidget(self._view)

    def _on_hover(self, sl, state, color, name, count, total):
        sl.setExploded(state)
        sl.setLabelVisible(state)
        if state:
            pct = (count / total * 100) if total else 0
            QToolTip.showText(
                QCursor.pos(),
                f"<b style='color:{color};'>{name}</b><br>"
                f"Orders: <b>{count}</b><br>"
                f"Share: <b>{pct:.1f}%</b>"
            )
        else:
            QToolTip.hideText()


# ─────────────────────────────────────────────
# CHART 7: Top Occasion Types (Horizontal Bar)
# ─────────────────────────────────────────────
class OccasionBreakdownChart(QVBoxLayout):
    _COLORS = [
        "#E11D48", "#F59E0B", "#3B82F6", "#22C55E", "#8B5CF6",
        "#F97316", "#06B6D4", "#EC4899", "#84CC16", "#6366F1",
    ]

    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Most Popular Event Types")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        db_data = repo.get_top_occasions(limit=10)
        if db_data:
            occasions = [r["occasion"] for r in db_data]
            counts    = [r["count"]    for r in db_data]
        else:
            occasions = ["No Data"]
            counts    = [0]

        self._occasions = occasions
        self._counts    = counts

        _lbl_c = "#0F172A" if not ThemeManager().is_dark() else "#F9FAFB"

        self._series = QBarSeries()
        for i, (occ, cnt) in enumerate(zip(occasions, counts)):
            bar_set = QBarSet(occ)
            bar_set.setColor(QColor(self._COLORS[i % len(self._COLORS)]))
            bar_set.setLabelColor(QColor(_lbl_c))
            bar_set.append(cnt)
            bar_set.hovered.connect(
                lambda state, idx, o=occ, c=cnt: self._on_hover(state, o, c)
            )
            self._series.append(bar_set)

        self._chart = QChart()
        self._chart.addSeries(self._series)
        self._chart.setAnimationOptions(QChart.SeriesAnimations)
        self._chart.legend().setAlignment(Qt.AlignBottom)
        self._chart.legend().setLabelColor(QColor(_lbl_c))

        self._ax = QBarCategoryAxis()
        self._ax.append(["Bookings"])
        _axis_style(self._ax)
        self._chart.addAxis(self._ax, Qt.AlignBottom)
        self._series.attachAxis(self._ax)

        self._ay = QValueAxis()
        self._ay.setRange(0, max(counts) * 1.3 if counts and max(counts) > 0 else 10)
        self._ay.setLabelFormat("%d")
        _axis_style(self._ay)
        self._chart.addAxis(self._ay, Qt.AlignLeft)
        self._series.attachAxis(self._ay)

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(260)
        self.addWidget(self._view)

        if db_data:
            self._add_legend_table(db_data)

    def _add_legend_table(self, db_data: list[dict]):
        total = sum(r["count"] for r in db_data) or 1
        grid = QHBoxLayout()
        grid.setSpacing(8)
        left_col  = QVBoxLayout()
        right_col = QVBoxLayout()
        for i, r in enumerate(db_data):
            pct = r["count"] / total * 100
            color = self._COLORS[i % len(self._COLORS)]
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 2, 0, 2)
            row_l.setSpacing(6)
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color}; font-size:14px;")
            dot.setFixedWidth(16)
            lbl = QLabel(f"{r['occasion']}  <span style='color:#6B7280;font-size:11px;'>×{r['count']} ({pct:.0f}%)</span>")
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size:12px;")
            row_l.addWidget(dot)
            row_l.addWidget(lbl)
            row_l.addStretch()
            if i % 2 == 0:
                left_col.addWidget(row_w)
            else:
                right_col.addWidget(row_w)
        left_col.addStretch()
        right_col.addStretch()
        grid.addLayout(left_col)
        grid.addLayout(right_col)
        self.addLayout(grid)

    def _on_hover(self, state: bool, occasion: str, count: int):
        if state:
            QToolTip.showText(
                QCursor.pos(),
                f"<b>{occasion}</b><br>Bookings: <b>{count}</b>"
            )
        else:
            QToolTip.hideText()


# ─────────────────────────────────────────────
# MAIN REPORTS PAGE
# ─────────────────────────────────────────────
_PERIOD_LABELS = ["Today", "This Week", "This Month", "This Year", "All Time"]


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainBackground")
        self._period = "All Time"

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

        self._btn_export = QPushButton("  Export", self.scroll_content)
        self._btn_export.setObjectName("secondaryButton")
        self._btn_export.setIcon(btn_icon_secondary("export"))
        self._btn_export.setIconSize(QSize(16, 16))
        self._btn_export.setMenu(self._build_export_menu())
        self._header_row.addWidget(self._btn_export)
        self.main_layout.addLayout(self._header_row)

        # ── PERIOD FILTER CHIPS ───────────────────────────────────────────────
        self._period_row = QHBoxLayout()
        self._period_row.setSpacing(8)
        self._period_btns = []
        from PySide6.QtWidgets import QButtonGroup
        self._period_group = QButtonGroup(self)
        self._period_group.setExclusive(True)
        for lbl in _PERIOD_LABELS:
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setChecked(lbl == "All Time")
            btn.setCursor(Qt.PointingHandCursor)
            _period_style = (
                "border-radius:14px;font-size:12px;font-weight:600;padding:0 14px;"
                "background:transparent;border:1px solid #CBD5E1;"
            ) if not ThemeManager().is_dark() else (
                "border-radius:14px;font-size:12px;font-weight:600;padding:0 14px;"
                "background:transparent;color:#9CA3AF;border:1px solid #374151;"
            )
            btn.setStyleSheet(_period_style)
            self._period_group.addButton(btn)
            self._period_btns.append(btn)
            btn.toggled.connect(lambda checked, b=btn, p=lbl: self._on_period(b, p, checked))
            self._period_row.addWidget(btn)
        self._period_row.addStretch()
        self.main_layout.addLayout(self._period_row)

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

        # ── ROW 3: Top Locations + Customer Frequency ────────────────────────
        self._row3 = QHBoxLayout()
        self._row3.setSpacing(24)

        self._locations_chart_layout = TopLocationsChart()
        self.locations_card = QFrame(self.scroll_content)
        self.locations_card.setObjectName("card")
        self.locations_card.setLayout(self._locations_chart_layout)
        self.locations_card.layout().setContentsMargins(28, 24, 28, 20)
        self._row3.addWidget(self.locations_card, 3)

        self._freq_chart_layout = CustomerFrequencyChart()
        self.freq_card = QFrame(self.scroll_content)
        self.freq_card.setObjectName("card")
        self.freq_card.setLayout(self._freq_chart_layout)
        self.freq_card.layout().setContentsMargins(28, 24, 28, 20)
        self._row3.addWidget(self.freq_card, 2)

        self.main_layout.addLayout(self._row3)

        # ── ROW 4: Occasion Breakdown ─────────────────────────────────────────
        self._occasion_chart_layout = OccasionBreakdownChart()
        self.occasion_card = QFrame(self.scroll_content)
        self.occasion_card.setObjectName("card")
        self.occasion_card.setLayout(self._occasion_chart_layout)
        self.occasion_card.layout().setContentsMargins(28, 24, 28, 20)
        self.main_layout.addWidget(self.occasion_card)

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
                f"<br><span style='font-size:11px;'>{b.get('date','')}</span>"
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

        # ── EXPENSES SECTION ──────────────────────────────────────────────────
        self._expense_card = HoverCard(self.scroll_content)
        exp_lay = QVBoxLayout(self._expense_card)
        exp_lay.setContentsMargins(24, 24, 24, 24)
        exp_lay.setSpacing(16)

        exp_head = QHBoxLayout()
        exp_title = QLabel("Expenses", self._expense_card)
        exp_title.setObjectName("h2")
        exp_head.addWidget(exp_title)
        exp_head.addStretch()
        btn_add_exp = QPushButton("  + Add Expense")
        btn_add_exp.setObjectName("primaryButton")
        btn_add_exp.setFixedHeight(32)
        btn_add_exp.clicked.connect(self._open_add_expense)
        exp_head.addWidget(btn_add_exp)
        exp_lay.addLayout(exp_head)

        self._exp_table = QTableWidget(0, 5, self._expense_card)
        self._exp_table.setHorizontalHeaderLabels(["DATE", "CATEGORY", "DESCRIPTION", "AMOUNT", ""])
        _exp_hdr = self._exp_table.horizontalHeader()
        _exp_hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        _exp_hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        _exp_hdr.setSectionResizeMode(4, QHeaderView.Fixed)
        self._exp_table.setColumnWidth(4, 40)
        self._exp_table.verticalHeader().setVisible(False)
        self._exp_table.setShowGrid(False)
        self._exp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._exp_table.setFocusPolicy(Qt.NoFocus)
        self._exp_table.setSelectionMode(QTableWidget.NoSelection)
        self._exp_table.setAlternatingRowColors(True)
        self._exp_table.setMinimumHeight(200)
        self._exp_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        exp_lay.addWidget(self._exp_table, 1)

        self._profit_lbl = QLabel("", self._expense_card)
        self._profit_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#22C55E;")
        exp_lay.addWidget(self._profit_lbl)

        self.main_layout.addWidget(self._expense_card)
        self._load_expenses()
        self.main_layout.addStretch(1)

        # ── Final assembly ────────────────────────────────────────────────────
        self.scroll_area.setWidget(self.scroll_content)
        self.root_layout.addWidget(self.scroll_area)

    # ── Period filter ─────────────────────────────────────────────────────────

    def _on_period(self, btn, period, checked):
        if not checked:
            return
        self._period = period
        btn.setStyleSheet(
            "border-radius:14px;font-size:12px;font-weight:700;padding:0 14px;"
            "background:rgba(225,29,72,.15);color:#E11D48;border:1px solid rgba(225,29,72,.4);"
        )
        for b in self._period_btns:
            if b is not btn:
                b.setStyleSheet(
                    "border-radius:14px;font-size:12px;font-weight:600;padding:0 14px;"
                    "background:transparent;color:#9CA3AF;border:1px solid #374151;"
                )
        self._reload_kpis()
        self._reload_table()

    def _period_sql_filter(self) -> str:
        p = self._period
        if p == "Today":
            return "AND DATE(event_date) = CURRENT_DATE"
        if p == "This Week":
            return "AND event_date >= date_trunc('week', CURRENT_DATE) AND event_date < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days'"
        if p == "This Month":
            return "AND date_trunc('month', event_date) = date_trunc('month', CURRENT_DATE)"
        if p == "This Year":
            return "AND EXTRACT(YEAR FROM event_date) = EXTRACT(YEAR FROM CURRENT_DATE)"
        return ""

    def _reload_kpis(self):
        fltr = self._period_sql_filter()
        kpis = repo.get_report_kpis(period_filter=fltr)
        vals = [
            str(kpis.get("total_bookings", 0)),
            f"{int(kpis.get('total_pax', 0)):,}",
            f"PHP {float(kpis.get('total_revenue', 0)):,.0f}",
            f"PHP {float(kpis.get('unpaid_amount', 0)):,.0f}",
        ]
        subs = [
            f"{kpis.get('today_bookings',0)} Today | {kpis.get('week_bookings',0)} This Week",
            "All confirmed bookings",
            "All-time revenue",
            "Outstanding balance",
        ]
        for card, val, sub in zip(self._kpi_cards, vals, subs):
            lay = card.layout()
            for i in range(lay.count()):
                w = lay.itemAt(i).widget()
                if w and w.objectName() == "kpiValue":
                    w.setText(val)
                if w and w.objectName() == "subtitle":
                    w.setText(sub)

    def _reload_table(self):
        fltr = self._period_sql_filter()
        db_bookings = repo.get_all_bookings(period_filter=fltr) or []
        self.table.setRowCount(len(db_bookings))
        for row, b in enumerate(db_bookings):
            self.table.setRowHeight(row, 64)
            pax_val = int(b.get("pax", 0))
            limit_status = "LIMIT REACHED" if pax_val >= 600 else ("NEAR LIMIT" if pax_val >= 400 else "")
            id_lbl       = QLabel(
                f"<span style='font-weight:700;font-size:13px;'>{b.get('id','')}</span>"
                f"<br><span style='font-size:11px;'>{b.get('date','')}</span>"
            )
            client_lbl   = QLabel(f"<span style='font-weight:600;font-size:13px;'>{b.get('name','')}</span>")
            package_lbl  = QLabel(f"<span style='font-size:13px;'>{b.get('package','—')}</span>")
            pax_badge    = create_pax_limit_badge(pax_val, limit_status)
            status_badge = create_status_badge(b.get("status", "").capitalize())
            self.table.setCellWidget(row, 0, id_lbl)
            self.table.setCellWidget(row, 1, client_lbl)
            self.table.setCellWidget(row, 2, package_lbl)
            self.table.setCellWidget(row, 3, pax_badge)
            self.table.setCellWidget(row, 4, status_badge)

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

    def _load_expenses(self):
        expenses = repo.get_all_expenses()
        self._expenses = expenses
        self._exp_table.setRowCount(0)
        total_exp = 0.0
        for exp in expenses:
            row = self._exp_table.rowCount()
            self._exp_table.insertRow(row)
            self._exp_table.setRowHeight(row, 44)
            self._exp_table.setCellWidget(row, 0, QLabel(f"  {exp['date']}"))
            self._exp_table.setCellWidget(row, 1, QLabel(f"  {exp['category']}"))
            self._exp_table.setCellWidget(row, 2, QLabel(f"  {exp['description']}"))
            amt_lbl = QLabel(f"  ₱ {exp['amount']:,.2f}")
            amt_lbl.setStyleSheet("color:#EF4444;font-weight:600;")
            self._exp_table.setCellWidget(row, 3, amt_lbl)
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet("background:transparent;border:none;font-weight:700;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda _, eid=exp["id"]: self._delete_expense(eid))
            self._exp_table.setCellWidget(row, 4, del_btn)
            total_exp += exp["amount"]

        profit_data = repo.get_profit_summary()
        total_rev = sum(r["revenue"] for r in profit_data)
        net = total_rev - total_exp
        color = "#22C55E" if net >= 0 else "#EF4444"
        self._profit_lbl.setStyleSheet(f"font-size:14px;font-weight:700;color:{color};")
        self._profit_lbl.setText(
            f"Total Expenses: ₱ {total_exp:,.2f}   |   "
            f"Total Revenue (YTD): ₱ {total_rev:,.2f}   |   "
            f"Net Profit: ₱ {net:,.2f}"
        )

    def _open_add_expense(self):
        from PySide6.QtWidgets import QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox, QDateEdit
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
        for c in ["Food Cost", "Labor", "Transport", "Utilities", "Equipment", "Other"]:
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
        repo.add_expense({"category": cat_cb.currentText(), "description": desc_edit.text().strip() or "—",
                          "amount": amt, "date": date_str})
        self._load_expenses()

    def _delete_expense(self, expense_id):
        repo.delete_expense(expense_id)
        self._load_expenses()

    def _build_export_menu(self):
        menu = QMenu(self)
        if not ThemeManager().is_dark():
            menu.setStyleSheet(
                "QMenu{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;padding:4px;}"
                "QMenu::item{color:#0F172A;padding:8px 20px;font-size:13px;border-radius:6px;}"
                "QMenu::item:selected{background:#F1F5F9;}"
            )
        else:
            menu.setStyleSheet(
                "QMenu{background:#1F2937;border:1px solid #374151;border-radius:8px;padding:4px;}"
                "QMenu::item{color:#F9FAFB;padding:8px 20px;font-size:13px;border-radius:6px;}"
                "QMenu::item:selected{background:#374151;}"
            )
        pdf_act = QAction("Export as PDF", self)
        pdf_act.triggered.connect(self._export_pdf)
        xlsx_act = QAction("Export as Excel (.xlsx)", self)
        xlsx_act.triggered.connect(self._export_excel)
        csv_act = QAction("Export as CSV", self)
        csv_act.triggered.connect(self._export_csv)
        menu.addAction(pdf_act)
        menu.addAction(xlsx_act)
        menu.addSeparator()
        menu.addAction(csv_act)
        return menu

    def _get_export_data(self):
        fltr = self._period_sql_filter()
        kpis = repo.get_report_kpis(period_filter=fltr)
        bookings = repo.get_all_bookings(period_filter=fltr) or []
        return kpis, bookings, self._period

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "jayraldines_report.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        kpis, bookings, period = self._get_export_data()
        ok = _exporter.export_pdf(path, kpis, bookings, "Business Report", period)
        if ok:
            QMessageBox.information(self, "Export", f"PDF exported to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed",
                "PDF export failed. Make sure reportlab is installed:\npip install reportlab")

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "jayraldines_report.xlsx", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        kpis, bookings, period = self._get_export_data()
        ok = _exporter.export_excel(path, kpis, bookings, "Business Report", period)
        if ok:
            QMessageBox.information(self, "Export", f"Excel exported to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed",
                "Excel export failed. Make sure openpyxl is installed:\npip install openpyxl")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "jayraldines_report.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        fltr = self._period_sql_filter()
        rows = repo.get_all_bookings(period_filter=fltr) or []
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Date", "Client", "Pax", "Total", "Status"])
            for b in rows:
                writer.writerow([
                    b.get("id"), b.get("date"), b.get("name"),
                    b.get("pax"), b.get("total"), b.get("status"),
                ])
        QMessageBox.information(self, "Export", f"CSV exported to:\n{path}")