import sys
import csv
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QFrame, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QScrollArea,
                               QMessageBox, QToolTip, QFileDialog, QMenu, QSizePolicy)
from PySide6.QtCore import Qt, QMargins, QPointF, QSize, QTimer
from datetime import datetime, date
from PySide6.QtGui import QAction, QFont, QColor, QPainter, QLinearGradient, QPen, QCursor

from utils import exporter as _exporter

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, btn_icon_red
from utils.theme import ThemeManager
from utils.accent import AccentManager
from components.dialogs import prompt_file_saved
import utils.repository as repo
from utils.data_loader import DataLoader

try:
    from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QAreaSeries,
                                  QPieSeries, QBarCategoryAxis, QBarSeries, QBarSet,
                                  QValueAxis, QLegend)
    _CHARTS_AVAILABLE = True
except Exception:
    _CHARTS_AVAILABLE = False
    QChart = QChartView = QLineSeries = QAreaSeries = QPieSeries = QBarCategoryAxis = QBarSeries = QBarSet = QValueAxis = QLegend = None


def _chart_view(chart) -> QWidget:
    if not _CHARTS_AVAILABLE or chart is None:
        w = QWidget()
        w.setFixedHeight(40)
        return w
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

        if not _CHARTS_AVAILABLE:
            no_c = QLabel("Income charts visualizer unavailable on this device.")
            no_c.setObjectName("subtitle")
            self.addWidget(no_c)
            return

        db_data = repo.get_monthly_income()
        if db_data:
            self._months = [r["month"] for r in db_data]
            values = [r["revenue"] / 1000 for r in db_data]
        else:
            self._months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            values = [0] * 6

        # Pin all series as instance vars — GC will NOT collect them
        self._upper = QLineSeries()
        pen = QPen(QColor(AccentManager().current))
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

        if not _CHARTS_AVAILABLE:
            no_c = QLabel("Payment methods chart unavailable.")
            no_c.setObjectName("subtitle")
            self.addWidget(no_c)
            return

        _COLORS = [AccentManager().current, "#F59E0B", "#3B82F6", "#22C55E", "#8B5CF6", "#6B7280"]
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

        if not _CHARTS_AVAILABLE:
            no_c = QLabel("Monthly breakdown chart unavailable.")
            no_c.setObjectName("subtitle")
            self.addWidget(no_c)
            return

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
        self._bar_rev.setColor(QColor(AccentManager().current))
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
                f"<b style='color:{AccentManager().current};'>{self._months[index]}</b><br>"
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

        if not _CHARTS_AVAILABLE:
            no_c = QLabel("Top menu items chart unavailable.")
            no_c.setObjectName("subtitle")
            self.addWidget(no_c)
            return

        db_data = repo.get_top_menu_items()
        if db_data:
            self._full_items = [r["item"] for r in db_data]
            items  = [(r["item"][:9] + "…") if len(r["item"]) > 9 else r["item"] for r in db_data]
            self._orders = [r["count"] for r in db_data]
        else:
            self._full_items = ["No Data"]
            items  = ["No Data"]
            self._orders = [0]

        self._bar_set = QBarSet("Orders")
        self._bar_set.setColor(QColor("#F59E0B"))
        _lbl_c2 = "#0F172A" if not ThemeManager().is_dark() else "#F9FAFB"
        self._bar_set.setLabelColor(QColor(_lbl_c2))
        for v in self._orders:
            self._bar_set.append(v)
        self._bar_set.hovered.connect(self._on_hover)

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
        self._ay.setRange(0, max(self._orders) * 1.3 if (self._orders and max(self._orders) > 0) else 10)
        self._ay.setLabelFormat("%d")
        _axis_style(self._ay)
        self._chart.addAxis(self._ay, Qt.AlignLeft)
        self._series.attachAxis(self._ay)

        self._view = _chart_view(self._chart)
        self._view.setMinimumHeight(240)
        self.addWidget(self._view)

    def _on_hover(self, state, index):
        if state and 0 <= index < len(self._full_items):
            item_name = self._full_items[index]
            cnt = self._orders[index]
            QToolTip.showText(
                QCursor.pos(),
                f"<b style='color:#F59E0B;'>{item_name}</b><br>Total Orders: <b>{cnt} times</b>"
            )
        else:
            QToolTip.hideText()


# ─────────────────────────────────────────────
# CHART 5: Top Booking Locations (Horizontal Bar)
# ─────────────────────────────────────────────
class TopLocationsChart(QVBoxLayout):
    def __init__(self):
        super().__init__()

        self._title_lbl = QLabel("Top Customer Areas (Where Orders Come From)")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        if not _CHARTS_AVAILABLE:
            no_c = QLabel("Top locations chart unavailable.")
            no_c.setObjectName("subtitle")
            self.addWidget(no_c)
            return

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

    def reload(self):
        if not _CHARTS_AVAILABLE or not hasattr(self, "_bar_set"):
            return
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

        self._bar_set.remove(0, self._bar_set.count())
        for v in counts:
            self._bar_set.append(v)

        self._ax.clear()
        self._ax.append(venues)

        self._ay.setRange(0, max(counts) * 1.2 if max(counts) > 0 else 10)

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

        if not _CHARTS_AVAILABLE:
            no_c = QLabel("Customer frequency chart unavailable.")
            no_c.setObjectName("subtitle")
            self.addWidget(no_c)
            return

        _COLORS = [AccentManager().current, "#F59E0B", "#3B82F6", "#22C55E", "#6B7280", "#8B5CF6"]
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
        self._COLORS = [AccentManager().current] + self.__class__._COLORS[1:]

        self._title_lbl = QLabel("Most Popular Event Types")
        self._title_lbl.setObjectName("h3")
        self.addWidget(self._title_lbl)

        if not _CHARTS_AVAILABLE:
            no_c = QLabel("Occasion breakdown chart unavailable.")
            no_c.setObjectName("subtitle")
            self.addWidget(no_c)
            return

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
_PERIOD_LABELS = ["Today", "This Week", "This Month", "This Year", "Last Year", "All Time"]


class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mainBackground")
        self._period = "All Time"
        self._dirty = False

        # ── DOM pagination state (per pipeline) ───────────────────────────────
        # Reports load the full period-scoped dataset once (KPIs & charts need it),
        # but the two record lists render only a page of cards at a time and append
        # the rest on scroll — so we never build a QFrame for a row nobody views.
        self._bk_page_size = 50
        self._bk_has_more = False
        self._bk_loading_more = False
        self._bk_remainder = []
        self._bk_rendering = False  # busy-flag: a batch chain is actively mutating table_cards_layout
        self._exp_page_size = 50
        self._exp_has_more = False
        self._exp_loading_more = False
        self._exp_remainder = []
        self._exp_rendering = False  # busy-flag: a batch chain is actively mutating exp_cards_layout

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
        self.main_layout.setContentsMargins(32, 28, 32, 28)
        self.main_layout.setSpacing(24)

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
        from PySide6.QtWidgets import QButtonGroup, QGridLayout
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

        # ── KPI CARDS (3x2 Grid: fits smoothly on all screen widths) ─────────
        self._kpi_grid = QGridLayout()
        self._kpi_grid.setSpacing(16)

        # Placeholder values — async load fills these in after first show
        self._kpi_cards = [
            self._kpi("Total Bookings",   "—", "Loading..."),
            self._kpi("Total Revenue",    "—", "Loading...", "#22C55E"),
            self._kpi("Total Expenses",   "—", "Loading...", "#F97316"),
            self._kpi("Net Profit",       "—", "Loading..."),
            self._kpi("Total Pax Booked", "—", "Loading...", "#3B82F6"),
            self._kpi("Unpaid Invoices",  "—", "Loading...", "#EF4444"),
        ]
        for idx, card in enumerate(self._kpi_cards):
            r = idx // 3
            c = idx % 3
            self._kpi_grid.addWidget(card, r, c)
        self.main_layout.addLayout(self._kpi_grid)

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

        # ── SALES TARGET EVALUATION (REF IMAGE 1) ─────────────────────────
        self._sales_eval_card = self._build_sales_evaluation_card()
        self.main_layout.addWidget(self._sales_eval_card)

        # ── RECENT BOOKINGS TABLE ────────────────────────────────────────────
        # ── RECENT BOOKINGS CARDS ────────────────────────────────────────────
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

        self._bookings_scroll = QScrollArea(self.table_card)
        self._bookings_scroll.setWidgetResizable(True)
        self._bookings_scroll.setFrameShape(QFrame.NoFrame)
        self._bookings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._bookings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._bookings_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                width: 7px;
                border-radius: 3px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.25);
                min-height: 25px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.table_cards_container = QWidget()
        self.table_cards_container.setStyleSheet("background: transparent;")
        self.table_cards_layout = QVBoxLayout(self.table_cards_container)
        self.table_cards_layout.setContentsMargins(0, 0, 8, 0)
        self.table_cards_layout.setSpacing(10)
        self.table_cards_layout.setAlignment(Qt.AlignTop)
        self._bookings_scroll.setWidget(self.table_cards_container)
        self._bookings_scroll.setFixedHeight(455)
        self._t_layout.addWidget(self._bookings_scroll)
        self.main_layout.addWidget(self.table_card)

        # ── EXPENSES SECTION (LIMITED TO 7 ROWS WITH SCROLL) ──────────────────
        self._expense_card = HoverCard(self.scroll_content)
        exp_lay = QVBoxLayout(self._expense_card)
        exp_lay.setContentsMargins(24, 24, 24, 24)
        exp_lay.setSpacing(16)

        exp_head = QHBoxLayout()
        self._exp_title = QLabel("Expenses", self._expense_card)
        self._exp_title.setObjectName("h2")
        exp_head.addWidget(self._exp_title)
        exp_head.addStretch()
        btn_add_exp = QPushButton("  Add Expense")
        btn_add_exp.setObjectName("primaryButton")
        btn_add_exp.setIcon(btn_icon_secondary("plus"))
        btn_add_exp.setIconSize(QSize(15, 15))
        btn_add_exp.setFixedHeight(34)
        btn_add_exp.setCursor(Qt.PointingHandCursor)
        btn_add_exp.setStyleSheet(
            "QPushButton#primaryButton { background-color: %s; color: #FFFFFF; border: none; "
            "font-weight: 700; border-radius: 8px; padding: 6px 16px; } "
            "QPushButton#primaryButton:hover { background-color: %s; }"
            % (AccentManager().current, AccentManager().darker(factor=110)))
        btn_add_exp.clicked.connect(self._open_add_expense)
        exp_head.addWidget(btn_add_exp)
        exp_lay.addLayout(exp_head)

        self._expenses_scroll = QScrollArea(self._expense_card)
        self._expenses_scroll.setWidgetResizable(True)
        self._expenses_scroll.setFrameShape(QFrame.NoFrame)
        self._expenses_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._expenses_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._expenses_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.05);
                width: 7px;
                border-radius: 3px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.25);
                min-height: 25px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.exp_cards_container = QWidget()
        self.exp_cards_container.setStyleSheet("background: transparent;")
        self.exp_cards_layout = QVBoxLayout(self.exp_cards_container)
        self.exp_cards_layout.setContentsMargins(0, 0, 8, 0)
        self.exp_cards_layout.setSpacing(10)
        self.exp_cards_layout.setAlignment(Qt.AlignTop)
        self._expenses_scroll.setWidget(self.exp_cards_container)
        self._expenses_scroll.setFixedHeight(455)
        exp_lay.addWidget(self._expenses_scroll)

        self._profit_lbl = QLabel("", self._expense_card)
        self._profit_lbl.setStyleSheet("font-size:14px;font-weight:700;color:#22C55E;")
        exp_lay.addWidget(self._profit_lbl)

        self.main_layout.addWidget(self._expense_card)
        # NOTE: _reload_table() and _load_expenses() are NOT called here.
        # They will be called asynchronously via reload() on first showEvent.
        self.main_layout.addStretch(1)

        # ── Data Change Listeners ─────────────────────────────────────────────
        try:
            from utils.signals import app_events
            ev = app_events()
            ev.expense_saved.connect(self._mark_dirty_and_reload)
            ev.booking_saved.connect(self._mark_dirty_and_reload)
            ev.payment_saved.connect(self._mark_dirty_and_reload)
            ev.data_changed.connect(self._mark_dirty_and_reload)
        except Exception:
            pass

        # ── Scroll-to-load-more wiring for the two record lists ───────────────
        self._bookings_scroll.verticalScrollBar().valueChanged.connect(self._on_bookings_scroll)
        self._expenses_scroll.verticalScrollBar().valueChanged.connect(self._on_expenses_scroll)

        # ── Final assembly ────────────────────────────────────────────────────
        self.scroll_area.setWidget(self.scroll_content)
        self.root_layout.addWidget(self.scroll_area)

        from components.loading_overlay import LoadingOverlay
        self._loader = LoadingOverlay(self, "Generating analytics & financial reports...")

    def _mark_dirty(self):
        self._dirty = True

    def _mark_dirty_and_reload(self):
        self._dirty = True
        if self.isVisible():
            self.reload()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_dirty", True) or getattr(self, "_cached_data", None) is None:
            self.reload()

    # ── Period filter ─────────────────────────────────────────────────────────

    def _on_period(self, btn, period, checked):
        if not checked:
            return
        self._period = period
        _ar, _ag, _ab, _ = QColor(AccentManager().current).getRgb()
        btn.setStyleSheet(
            "border-radius:14px;font-size:12px;font-weight:700;padding:0 14px;"
            "background:rgba(%d,%d,%d,.15);color:%s;border:1px solid rgba(%d,%d,%d,.4);"
            % (_ar, _ag, _ab, AccentManager().current, _ar, _ag, _ab)
        )
        for b in self._period_btns:
            if b is not btn:
                b.setStyleSheet(
                    "border-radius:14px;font-size:12px;font-weight:600;padding:0 14px;"
                    "background:transparent;color:#9CA3AF;border:1px solid #374151;"
                )
        if getattr(self, "_cached_data", None):
            d = dict(self._cached_data)
            d["period"] = period
            self._reload_kpis(d)
            self._reload_table(d.get("bookings", []))
            self._load_expenses(d.get("expenses", []), d.get("profit", []))
            if hasattr(self, "_locations_chart_layout") and hasattr(self._locations_chart_layout, "reload"):
                self._locations_chart_layout.reload()
        else:
            self.reload()

    def _period_sql_filter(self) -> str:
        p = getattr(self, "_period", "All Time")
        if p == "Today":
            return "AND DATE(bk_event_date) = DATE('now')"
        if p == "This Week":
            return "AND DATE(bk_event_date) >= DATE('now', 'weekday 0', '-6 days') AND DATE(bk_event_date) <= DATE('now', 'weekday 0')"
        if p == "This Month":
            return "AND strftime('%Y-%m', bk_event_date) = strftime('%Y-%m', 'now')"
        if p == "This Year":
            return "AND strftime('%Y', bk_event_date) = strftime('%Y', 'now')"
        if p == "Last Year":
            return "AND CAST(strftime('%Y', bk_event_date) AS INT) = CAST(strftime('%Y', 'now') AS INT) - 1"
        return ""

    def reload(self):
        """Kick off a background fetch of ALL reports data — never blocks the GUI."""
        # Coalesce overlapping reloads: a reload spans the background fetch AND the
        # two async batch-render pipelines. If one is already in flight, don't start
        # a second in parallel — just remember to run exactly one more pass once the
        # current one fully finishes (see _reload_finished).
        if getattr(self, "_reload_in_flight", False):
            self._reload_pending = True
            return
        self._reload_in_flight = True
        self._reload_pending = False
        self._dirty = False

        if hasattr(self, "_loader"):
            self._loader.show_overlay("Generating analytics & financial reports...")

        loader = DataLoader(self._fetch_all_reports_data)
        loader.data_ready.connect(self._on_reports_data_ready)
        def _on_rep_err(msg):
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            print(f"[Reports] Load error: {msg}")
            self._reload_finished()
        loader.load_error.connect(_on_rep_err)
        self._reports_loader = loader
        loader.start()

    def _reload_finished(self):
        self._reload_in_flight = False
        if getattr(self, "_reload_pending", False):
            self._reload_pending = False
            QTimer.singleShot(0, self.reload)

    def _report_render_step(self):
        """Called once by each async render pipeline (table & expenses) when it truly
        finishes. Only the LAST one to finish hides the loader and closes out the
        reload — so the overlay never disappears mid-render."""
        if getattr(self, "_render_pending", 0) <= 0:
            return  # not part of a coordinated reload (e.g. period filter click)
        self._render_pending -= 1
        if self._render_pending == 0:
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            self._reload_finished()

    def _fetch_all_reports_data(self):
        """Runs entirely in a background thread — fetches all data in one batch."""
        try:
            yr = int(getattr(self, "_eval_year_combo", None) and self._eval_year_combo.currentText() or datetime.now().year)
        except Exception:
            yr = datetime.now().year
        return {
            "bookings":     repo.get_all_bookings() or [],
            "expenses":     repo.get_all_expenses() or [],
            "profit":       repo.get_profit_summary() or [],
            "kpis":         repo.get_report_kpis() or {},
            "sales_eval":   repo.get_monthly_sales_evaluation_report(yr) or {},
            "locations":    repo.get_top_locations(limit=10) or [],
            "period":       getattr(self, "_period", "All Time"),
            "eval_year":    yr,
        }

    def _on_reports_data_ready(self, data: dict):
        """Called on the GUI thread — dispatches pre-fetched data to each renderer."""
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
            self._cached_data = data
            # Synchronous sections first — they finish before any loader hide.
            self._reload_kpis(data)
            self._reload_locations(data.get("locations", []))
            self._reload_sales_evaluation_from_data(data.get("sales_eval", {}), data.get("eval_year", datetime.now().year))
            # Two async batch-render pipelines. The loader is hidden (and the reload
            # closed out) only once BOTH complete — see _report_render_step, invoked
            # from each pipeline's final batch / empty-state path.
            self._render_pending = 2
            self._reload_table(data.get("bookings", []))
            self._load_expenses(data.get("expenses", []), data.get("profit", []))
        except Exception:
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            self._reload_finished()

    def _reload_locations(self, db_data):
        """Update the locations chart with pre-fetched data (GUI thread safe)."""
        if not _CHARTS_AVAILABLE or not hasattr(self._locations_chart_layout, "_bar_set"):
            return
        _MAX = 30
        if db_data:
            venues = [(r["venue"][:_MAX] + "…") if len(r["venue"]) > _MAX else r["venue"] for r in db_data]
            counts = [r["count"] for r in db_data]
        else:
            venues = ["No Data"]
            counts = [0]
        chart = self._locations_chart_layout
        chart._venues = venues
        chart._counts = counts
        chart._bar_set.remove(0, chart._bar_set.count())
        for v in counts:
            chart._bar_set.append(v)
        chart._ax.clear()
        chart._ax.append(venues)
        chart._ay.setRange(0, max(counts) * 1.2 if max(counts) > 0 else 10)

    def _build_sales_evaluation_card(self):
        card = HoverCard(self.scroll_content)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        head = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.setSpacing(3)
        t_lbl = QLabel("Sales Evaluation Report (Monthly Target vs Actual)")
        t_lbl.setObjectName("h2")
        sub = QLabel("Compare real system revenue performance against configured monthly targets (Formula: Target - Actual = Remaining).")
        sub.setObjectName("subtitle")
        v_title.addWidget(t_lbl)
        v_title.addWidget(sub)
        head.addLayout(v_title)
        head.addStretch()

        yr_lbl = QLabel("Select Year:")
        yr_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        head.addWidget(yr_lbl)

        from PySide6.QtWidgets import QComboBox
        self._eval_year_combo = QComboBox()
        cur_year = datetime.now().year
        for yr in [cur_year - 2, cur_year - 1, cur_year, cur_year + 1, cur_year + 2]:
            self._eval_year_combo.addItem(str(yr), yr)
        self._eval_year_combo.setCurrentText(str(cur_year))
        self._eval_year_combo.setFixedHeight(34)
        self._eval_year_combo.setMinimumWidth(100)
        self._eval_year_combo.currentIndexChanged.connect(self._reload_sales_evaluation)
        head.addWidget(self._eval_year_combo)

        btn_export_eval = QPushButton("  Export CSV")
        btn_export_eval.setObjectName("secondaryButton")
        btn_export_eval.setIcon(btn_icon_secondary("export"))
        btn_export_eval.setIconSize(QSize(14, 14))
        btn_export_eval.setFixedHeight(34)
        btn_export_eval.clicked.connect(self._export_sales_eval_csv)
        head.addWidget(btn_export_eval)

        lay.addLayout(head)

        # 12-Month Table
        self._eval_table = QTableWidget(13, 4)
        self._eval_table.setHorizontalHeaderLabels([
            "Month", "Target Sales (₱)", "Actual Sales (₱)", "Evaluation / Remaining (₱)"
        ])
        self._eval_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._eval_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._eval_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._eval_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._eval_table.verticalHeader().setVisible(False)
        self._eval_table.setFixedHeight(480)
        lay.addWidget(self._eval_table)

        self._reload_sales_evaluation()
        return card

    def _reload_sales_evaluation(self):
        """Re-fetch sales eval data and update table (triggered by year combo change)."""
        if not hasattr(self, "_eval_table"):
            return
        try:
            yr = int(self._eval_year_combo.currentText())
        except Exception:
            yr = datetime.now().year
        # Run in background since it's a DB call
        def _fetch():
            return repo.get_monthly_sales_evaluation_report(yr)
        loader = DataLoader(_fetch)
        loader.data_ready.connect(lambda d: self._reload_sales_evaluation_from_data(d, yr))
        loader.load_error.connect(lambda msg: print(f"[Reports] Sales eval error: {msg}"))
        self._eval_yr_loader = loader
        loader.start()

    def _reload_sales_evaluation_from_data(self, data: dict, yr: int = None):
        """Populate the sales evaluation table from pre-fetched data (GUI thread safe)."""
        if not hasattr(self, "_eval_table"):
            return
        months = data.get("months", [])

        self._eval_table.setRowCount(len(months) + 1)
        for r_idx, m_info in enumerate(months):
            m_name = m_info["month_name"]
            t_amt = m_info["target_sales"]
            a_amt = m_info["actual_sales"]
            rem = m_info["remaining"]

            item_m = QTableWidgetItem(m_name)
            item_m.setFont(QFont("Segoe UI", 10, QFont.Bold))
            item_m.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_t = QTableWidgetItem(f"₱ {t_amt:,.2f}")
            item_t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            item_a = QTableWidgetItem(f"₱ {a_amt:,.2f}")
            item_a.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if a_amt > 0:
                item_a.setForeground(QColor("#22C55E"))

            # Ref Image 1: Shortfall displayed in red parenthesis e.g. (85,000.00)
            if a_amt < t_amt:
                eval_str = f"(₱ {rem:,.2f})"
                item_e = QTableWidgetItem(eval_str)
                item_e.setForeground(QColor("#EF4444"))
                item_e.setToolTip(f"₱{rem:,.2f} remaining to hit the target")
            else:
                surplus = a_amt - t_amt
                eval_str = f"+₱ {surplus:,.2f} (Target Achieved)"
                item_e = QTableWidgetItem(eval_str)
                item_e.setForeground(QColor("#22C55E"))

            item_e.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self._eval_table.setItem(r_idx, 0, item_m)
            self._eval_table.setItem(r_idx, 1, item_t)
            self._eval_table.setItem(r_idx, 2, item_a)
            self._eval_table.setItem(r_idx, 3, item_e)

        # Summary Row (13th row)
        tot_target = data.get("total_target", 0.0)
        tot_actual = data.get("total_actual", 0.0)
        tot_rem = data.get("total_remaining", 0.0)

        tot_m = QTableWidgetItem("TOTAL ANNUAL:")
        tot_m.setFont(QFont("Segoe UI", 11, QFont.ExtraBold))
        tot_m.setForeground(QColor("#E11D48"))

        tot_t = QTableWidgetItem(f"₱ {tot_target:,.2f}")
        tot_t.setFont(QFont("Segoe UI", 11, QFont.Bold))
        tot_t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        tot_a = QTableWidgetItem(f"₱ {tot_actual:,.2f}")
        tot_a.setFont(QFont("Segoe UI", 11, QFont.Bold))
        tot_a.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        tot_a.setForeground(QColor("#22C55E"))

        if tot_actual < tot_target:
            tot_e_str = f"(₱ {tot_rem:,.2f})"
            tot_e = QTableWidgetItem(tot_e_str)
            tot_e.setForeground(QColor("#EF4444"))
        else:
            tot_e = QTableWidgetItem(f"+₱ {(tot_actual - tot_target):,.2f} (Target Exceeded)")
            tot_e.setForeground(QColor("#22C55E"))

        tot_e.setFont(QFont("Segoe UI", 11, QFont.Bold))
        tot_e.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        last_r = len(months)
        self._eval_table.setItem(last_r, 0, tot_m)
        self._eval_table.setItem(last_r, 1, tot_t)
        self._eval_table.setItem(last_r, 2, tot_a)
        self._eval_table.setItem(last_r, 3, tot_e)

    def _export_sales_eval_csv(self):
        yr = int(self._eval_year_combo.currentText())
        path, _ = QFileDialog.getSaveFileName(self, f"Export Sales Evaluation {yr}", f"Jayraldines_Sales_Evaluation_{yr}.csv", "CSV Files (*.csv)")
        if not path:
            return
        data = repo.get_monthly_sales_evaluation_report(yr)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([f"Jayraldine's Catering - Sales Evaluation Report ({yr})"])
                writer.writerow(["Month", "Target Sales", "Actual Sales", "Evaluation / Remaining"])
                for m in data.get("months", []):
                    rem_str = f"({m['remaining']:,.2f})" if m['is_shortfall'] else f"{m['actual_sales'] - m['target_sales']:,.2f}"
                    writer.writerow([m["month_name"], f"{m['target_sales']:,.2f}", f"{m['actual_sales']:,.2f}", rem_str])
                writer.writerow([])
                writer.writerow(["TOTAL ANNUAL", f"{data['total_target']:,.2f}", f"{data['total_actual']:,.2f}", f"({data['total_remaining']:,.2f})" if data['overall_shortfall'] else "Achieved"])
            prompt_file_saved(self, path, title="Sales Evaluation Exported", message="Sales evaluation report exported successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))

    def _reload_kpis(self, data: dict = None):
        """Update KPI cards from pre-fetched data dict (safe to call on GUI thread)."""
        if data is None:
            data = getattr(self, "_cached_data", None)
        if data is None:
            return  # No data yet; wait for async load
        p = data.get("period", getattr(self, "_period", "All Time"))
        all_bookings = data.get("bookings", [])
        all_expenses = data.get("expenses", [])

        from datetime import datetime, date, timedelta
        today = date.today()

        def _get_date(d_str):
            if not d_str:
                return None
            for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(str(d_str).strip(), fmt).date()
                except ValueError:
                    continue
            return None

        # Filter bookings for period
        filtered_b = []
        for b in all_bookings:
            b_date = _get_date(b.get("date"))
            if not b_date:
                continue

            if p in ("All Time", "All", ""):
                filtered_b.append(b)
            elif p == "Today" and b_date == today:
                filtered_b.append(b)
            elif p == "This Week":
                start_w = today - timedelta(days=today.weekday())
                end_w = start_w + timedelta(days=6)
                if start_w <= b_date <= end_w:
                    filtered_b.append(b)
            elif p == "This Month":
                if b_date.month == today.month and b_date.year == today.year:
                    filtered_b.append(b)
            elif p == "This Year":
                if b_date.year == today.year:
                    filtered_b.append(b)
            elif p == "Last Year":
                if b_date.year == today.year - 1:
                    filtered_b.append(b)

        # Filter expenses for period
        filtered_e = []
        for e in all_expenses:
            e_date = _get_date(e.get("date"))
            if not e_date:
                continue

            if p in ("All Time", "All", ""):
                filtered_e.append(e)
            elif p == "Today" and e_date == today:
                filtered_e.append(e)
            elif p == "This Week":
                start_w = today - timedelta(days=today.weekday())
                end_w = start_w + timedelta(days=6)
                if start_w <= e_date <= end_w:
                    filtered_e.append(e)
            elif p == "This Month":
                if e_date.month == today.month and e_date.year == today.year:
                    filtered_e.append(e)
            elif p == "This Year":
                if e_date.year == today.year:
                    filtered_e.append(e)
            elif p == "Last Year":
                if e_date.year == today.year - 1:
                    filtered_e.append(e)

        # Compute KPI numbers
        confirmed_b = [b for b in filtered_b if b.get("status", "").upper() in ("CONFIRMED", "COMPLETED")]
        target_b = confirmed_b if confirmed_b else filtered_b
        total_bookings = len(target_b)
        total_pax = sum(int(b.get("pax", 0) or 0) for b in target_b)

        from components.confirm_booking_dialog import _parse_amount
        total_revenue = sum(_parse_amount(b.get("total", 0)) for b in target_b)
        total_expenses = sum(float(e.get("amount", 0) or 0) for e in filtered_e)
        profit = total_revenue - total_expenses
        total_unpaid = sum(float(b.get("balance", 0) or 0) for b in target_b)

        # Calculate today, week, and month bookings from all bookings
        start_w = today - timedelta(days=today.weekday())
        end_w = start_w + timedelta(days=6)
        today_bk = sum(1 for b in all_bookings if _get_date(b.get("date")) == today)
        week_bk = sum(1 for b in all_bookings if _get_date(b.get("date")) and start_w <= _get_date(b.get("date")) <= end_w)
        month_bk = sum(1 for b in all_bookings if _get_date(b.get("date")) and _get_date(b.get("date")).month == today.month and _get_date(b.get("date")).year == today.year)

        vals = [
            str(total_bookings),
            f"PHP {total_revenue:,.0f}",
            f"PHP {total_expenses:,.0f}",
            f"PHP {profit:,.0f}",
            f"{total_pax:,}",
            f"PHP {total_unpaid:,.0f}",
        ]
        subs = [
            f"{today_bk} Today • {week_bk} Week • {month_bk} Month",
            f"{total_bookings} Confirmed booking(s)" if total_bookings > 0 else "No income for period",
            "All operational costs",
            "Revenue − Expenses",
            f"{total_pax:,} Pax booked" if total_pax > 0 else "No guests for period",
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

    def _reload_table(self, all_bookings: list = None):
        """Rebuild booking table cards from pre-fetched list (safe to call on GUI thread)."""
        # Invalidate any in-flight batched render before clearing
        self._table_render_token = getattr(self, "_table_render_token", 0) + 1
        while self.table_cards_layout.count():
            item = self.table_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reset pagination for the new period/reload; the populated branch re-arms it.
        self._bk_has_more = False
        self._bk_loading_more = False
        self._bk_remainder = []

        if all_bookings is None:
            if getattr(self, "_cached_data", None):
                all_bookings = self._cached_data.get("bookings", [])
            else:
                self._report_render_step()  # nothing to render; release the loader slot
                return  # Async data not ready yet

        p = getattr(self, "_period", "All Time")
        from datetime import datetime, date, timedelta
        today = date.today()

        def _get_date(d_str):
            if not d_str:
                return None
            for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(str(d_str).strip(), fmt).date()
                except ValueError:
                    continue
            return None

        filtered_bookings = []
        if p in ("All Time", "All", ""):
            filtered_bookings = all_bookings
        else:
            for b in all_bookings:
                b_date = _get_date(b.get("date"))
                if not b_date:
                    continue

                if p == "Today" and b_date == today:
                    filtered_bookings.append(b)
                elif p == "This Week":
                    start_w = today - timedelta(days=today.weekday())
                    end_w = start_w + timedelta(days=6)
                    if start_w <= b_date <= end_w:
                        filtered_bookings.append(b)
                elif p == "This Month":
                    if b_date.month == today.month and b_date.year == today.year:
                        filtered_bookings.append(b)
                elif p == "This Year":
                    if b_date.year == today.year:
                        filtered_bookings.append(b)
                elif p == "Last Year":
                    if b_date.year == today.year - 1:
                        filtered_bookings.append(b)

        if not filtered_bookings:
            empty_lbl = QLabel("No booking statistics for this period.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.table_cards_layout.addWidget(empty_lbl)
            if hasattr(self, "_bookings_scroll"):
                self._bookings_scroll.setFixedHeight(60)
            self._t_head_lbl.setText("Recent Booking Statistics")
            self._bk_rendering = False  # empty state: no batch chain will run
            self._report_render_step()  # no batches run for empty state
        else:
            total_b = len(filtered_bookings)
            # Finalize scroll height / header text upfront (depend only on count)
            if hasattr(self, "_bookings_scroll"):
                if total_b > 7:
                    # Exactly 7 rows visible with smooth scroll for remaining
                    self._bookings_scroll.setFixedHeight(455)
                    self._t_head_lbl.setText(f"Recent Booking Statistics ({total_b} records · showing 7 rows, scroll for more)")
                else:
                    self._bookings_scroll.setFixedHeight(max(60, total_b * 56 + max(0, total_b - 1) * 10))
                    self._t_head_lbl.setText(f"Recent Booking Statistics ({total_b} record{'s' if total_b != 1 else ''})")

            # Hoist per-row-invariant computation out of the loop
            self._table_accent = AccentManager().current
            # DOM pagination: render only the first page of cards now; keep the
            # remaining filtered rows in memory and append them on scroll-near-bottom.
            # Header text/count above is derived from the FULL filtered list, so it
            # stays accurate no matter how many pages are currently rendered.
            self._bk_remainder = list(filtered_bookings[self._bk_page_size:])
            self._bk_has_more = len(filtered_bookings) > self._bk_page_size
            self._bk_loading_more = False
            self._bk_rendering = True  # a batch chain is about to start filling the layout
            self._table_queue = list(filtered_bookings[:self._bk_page_size])
            self._render_table_batch(self._table_render_token)

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

    def _render_table_batch(self, token, batch_size=15):
        """Build a batch of booking cards, then yield to the event loop."""
        if token != getattr(self, "_table_render_token", None):
            return  # a newer render superseded this one
        queue = getattr(self, "_table_queue", [])
        if not queue:
            return
        batch = queue[:batch_size]
        del queue[:batch_size]
        accent = getattr(self, "_table_accent", None) or AccentManager().current

        self.table_cards_container.setUpdatesEnabled(False)
        for b in batch:
            pax_val = int(b.get("pax", 0))
            limit_status = "LIMIT REACHED" if pax_val >= 600 else ("NEAR LIMIT" if pax_val >= 400 else "")
            card = QFrame()
            card.setObjectName("entryCard")
            card.setFixedHeight(56)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(16, 8, 16, 8)
            cl.setSpacing(16)

            # Col 1: Ref & Date
            c1 = QVBoxLayout()
            c1.setSpacing(2)
            id_lbl = QLabel(b.get("id", ""))
            id_lbl.setStyleSheet(f"font-weight: 800; font-size: 13px; color: {accent};")
            d_lbl = QLabel(b.get("date", ""))
            d_lbl.setObjectName("subtitle")
            c1.addWidget(id_lbl)
            c1.addWidget(d_lbl)
            cl.addLayout(c1, 2)

            # Col 2: Client Name & Package
            c2 = QVBoxLayout()
            c2.setSpacing(2)
            client_lbl = QLabel(b.get("name", ""))
            client_lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
            pkg_lbl = QLabel(f"Package: {b.get('package', '—')}")
            pkg_lbl.setObjectName("subtitle")
            c2.addWidget(client_lbl)
            c2.addWidget(pkg_lbl)
            cl.addLayout(c2, 3)

            # Col 3: Pax Badge & Status Badge
            pax_badge = create_pax_limit_badge(pax_val, limit_status)
            status_badge = create_status_badge(b.get("status", "").capitalize())
            cl.addWidget(pax_badge, alignment=Qt.AlignVCenter)
            cl.addWidget(status_badge, alignment=Qt.AlignVCenter)

            self._insert_card_before_stretch(self.table_cards_layout, card)
        self.table_cards_container.setUpdatesEnabled(True)

        if queue:
            QTimer.singleShot(0, lambda: self._render_table_batch(token, batch_size))
        else:
            self._bk_loading_more = False  # this page finished appending
            self._bk_rendering = False  # chain drained — safe to append more on scroll
            self._report_render_step()  # last batch done — release the loader slot

    def _on_bookings_scroll(self, value):
        sb = self._bookings_scroll.verticalScrollBar()
        if sb.maximum() - value < 200:
            self._load_more_bookings()

    def _load_more_bookings(self):
        """Append the next page of booking cards from the in-memory remainder — no
        DB round-trip, since the full period-scoped list is already loaded."""
        if getattr(self, "_bk_loading_more", False) or not getattr(self, "_bk_has_more", False):
            return
        # Don't append while the initial page's own batch chain is still mutating
        # table_cards_layout — interleaving the two chains corrupts layout bookkeeping.
        if getattr(self, "_bk_rendering", False):
            return
        self._bk_loading_more = True
        more = self._bk_remainder[:self._bk_page_size]
        self._bk_remainder = self._bk_remainder[self._bk_page_size:]
        if not self._bk_remainder:
            self._bk_has_more = False
        if not more:
            self._bk_loading_more = False
            return
        # Reuse the existing batch renderer (batch_size=15) to append the new cards.
        self._bk_rendering = True  # scroll-append chain starting
        self._table_render_token = getattr(self, "_table_render_token", 0) + 1
        self._table_accent = AccentManager().current
        self._table_queue = list(more)
        self._render_table_batch(self._table_render_token)

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
        lbl_s.setObjectName("subtitle")
        if sub_color:
            lbl_s.setStyleSheet(f"color: {sub_color}; font-weight: 600; font-size: 12px;")
        lay.addWidget(lbl_s)
        lay.addStretch()
        return card

    def _load_expenses(self, all_exp: list = None, profit_data: list = None):
        """Rebuild expense cards from pre-fetched data (safe to call on GUI thread)."""
        # Invalidate any in-flight batched render before clearing
        self._exp_render_token = getattr(self, "_exp_render_token", 0) + 1
        while self.exp_cards_layout.count():
            item = self.exp_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reset pagination for the new period/reload; the populated branch re-arms it.
        self._exp_has_more = False
        self._exp_loading_more = False
        self._exp_remainder = []

        if all_exp is None:
            self._report_render_step()  # nothing to render; release the loader slot
            return  # Async data not ready yet

        p = getattr(self, "_period", "All Time")
        from datetime import datetime, date, timedelta
        today = date.today()

        expenses = []
        if p in ("All Time", "All", ""):
            expenses = all_exp
        else:
            for exp in all_exp:
                d_str = exp.get("date", "")
                exp_d = None
                for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%Y/%m/%d", "%b-%d-%Y", "%d-%b-%Y"):
                    try:
                        exp_d = datetime.strptime(str(d_str).strip(), fmt).date()
                        break
                    except ValueError:
                        continue
                if not exp_d:
                    continue

                if p == "Today" and exp_d == today:
                    expenses.append(exp)
                elif p == "This Week":
                    start_w = today - timedelta(days=today.weekday())
                    end_w = start_w + timedelta(days=6)
                    if start_w <= exp_d <= end_w:
                        expenses.append(exp)
                elif p == "This Month":
                    if exp_d.month == today.month and exp_d.year == today.year:
                        expenses.append(exp)
                elif p == "This Year":
                    if exp_d.year == today.year:
                        expenses.append(exp)
                elif p == "Last Year":
                    if exp_d.year == today.year - 1:
                        expenses.append(exp)

        self._expenses = expenses
        # total_exp depends only on amounts, compute upfront (independent of widgets)
        total_exp = sum(exp["amount"] for exp in expenses)

        if not expenses:
            empty_lbl = QLabel("No expenses recorded.")
            empty_lbl.setObjectName("subtitle")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.exp_cards_layout.addWidget(empty_lbl)
            if hasattr(self, "_expenses_scroll"):
                self._expenses_scroll.setFixedHeight(60)
            if hasattr(self, "_exp_title"):
                self._exp_title.setText("Expenses")
            self._exp_rendering = False  # empty state: no batch chain will run
            self._report_render_step()  # no batches run for empty state
        else:
            total_e = len(expenses)
            # Finalize scroll height / title upfront (depend only on count)
            if hasattr(self, "_expenses_scroll"):
                if total_e > 7:
                    # Exactly 7 rows visible with smooth scroll for remaining
                    self._expenses_scroll.setFixedHeight(455)
                    if hasattr(self, "_exp_title"):
                        self._exp_title.setText(f"Expenses ({total_e} records · showing 7 rows, scroll for more)")
                else:
                    self._expenses_scroll.setFixedHeight(max(60, total_e * 56 + max(0, total_e - 1) * 10))
                    if hasattr(self, "_exp_title"):
                        self._exp_title.setText(f"Expenses ({total_e} record{'s' if total_e != 1 else ''})")

            # DOM pagination: render only the first page now; the rest stays in
            # memory and is appended on scroll. total_exp / net profit below are
            # computed from the FULL filtered list, so they remain accurate.
            self._exp_remainder = list(expenses[self._exp_page_size:])
            self._exp_has_more = len(expenses) > self._exp_page_size
            self._exp_loading_more = False
            self._exp_rendering = True  # a batch chain is about to start filling the layout
            self._exp_queue = list(expenses[:self._exp_page_size])
            self._render_expense_batch(self._exp_render_token)

        # Use pre-fetched profit_data if available, else fall back to synchronous call
        _profit_data = profit_data if profit_data is not None else []
        total_rev = sum(r["revenue"] for r in _profit_data)
        net = total_rev - total_exp
        color = "#22C55E" if net >= 0 else "#EF4444"
        self._profit_lbl.setStyleSheet(f"font-size:14px;font-weight:700;color:{color};")
        self._profit_lbl.setText(
            f"Total Expenses: ₱ {total_exp:,.2f}   |   "
            f"Total Revenue (YTD): ₱ {total_rev:,.2f}   |   "
            f"Net Profit: ₱ {net:,.2f}"
        )

    def _render_expense_batch(self, token, batch_size=15):
        """Build a batch of expense cards, then yield to the event loop."""
        if token != getattr(self, "_exp_render_token", None):
            return  # a newer render superseded this one
        queue = getattr(self, "_exp_queue", [])
        if not queue:
            return
        batch = queue[:batch_size]
        del queue[:batch_size]

        self.exp_cards_container.setUpdatesEnabled(False)
        for exp in batch:
            card = QFrame()
            card.setObjectName("entryCard")
            card.setFixedHeight(56)
            el = QHBoxLayout(card)
            el.setContentsMargins(16, 8, 16, 8)
            el.setSpacing(14)

            c1 = QVBoxLayout()
            c1.setSpacing(2)
            d_lbl = QLabel(exp["date"])
            d_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
            cat_lbl = QLabel(f"Category: {exp['category']}")
            cat_lbl.setObjectName("subtitle")
            c1.addWidget(d_lbl)
            c1.addWidget(cat_lbl)
            el.addLayout(c1, 2)

            desc_lbl = QLabel(exp["description"])
            desc_lbl.setStyleSheet("font-size: 12px;")
            el.addWidget(desc_lbl, 3)

            amt_lbl = QLabel(f"₱ {exp['amount']:,.2f}")
            amt_lbl.setStyleSheet("font-weight: 800; font-size: 14px; color: #EF4444;")
            el.addWidget(amt_lbl, 2)

            del_btn = QPushButton()
            del_btn.setIcon(btn_icon_red("trash"))
            del_btn.setIconSize(QSize(14, 14))
            del_btn.setFixedSize(32, 32)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("Delete expense")
            del_btn.clicked.connect(lambda _, eid=exp["id"]: self._delete_expense(eid))
            el.addWidget(del_btn)

            self._insert_card_before_stretch(self.exp_cards_layout, card)
        self.exp_cards_container.setUpdatesEnabled(True)

        if queue:
            QTimer.singleShot(0, lambda: self._render_expense_batch(token, batch_size))
        else:
            self._exp_loading_more = False  # this page finished appending
            self._exp_rendering = False  # chain drained — safe to append more on scroll
            self._report_render_step()  # last batch done — release the loader slot

    def _on_expenses_scroll(self, value):
        sb = self._expenses_scroll.verticalScrollBar()
        if sb.maximum() - value < 200:
            self._load_more_expenses()

    def _load_more_expenses(self):
        """Append the next page of expense cards from the in-memory remainder — no
        DB round-trip, since the full period-scoped list is already loaded."""
        if getattr(self, "_exp_loading_more", False) or not getattr(self, "_exp_has_more", False):
            return
        # Don't append while the initial page's own batch chain is still mutating
        # exp_cards_layout — interleaving the two chains corrupts layout bookkeeping.
        if getattr(self, "_exp_rendering", False):
            return
        self._exp_loading_more = True
        more = self._exp_remainder[:self._exp_page_size]
        self._exp_remainder = self._exp_remainder[self._exp_page_size:]
        if not self._exp_remainder:
            self._exp_has_more = False
        if not more:
            self._exp_loading_more = False
            return
        # Reuse the existing batch renderer (batch_size=15) to append the new cards.
        self._exp_rendering = True  # scroll-append chain starting
        self._exp_render_token = getattr(self, "_exp_render_token", 0) + 1
        self._exp_queue = list(more)
        self._render_expense_batch(self._exp_render_token)

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
        menu.addSeparator()
        audit_pdf_act = QAction("Export Activity / Audit Log (PDF)", self)
        audit_pdf_act.triggered.connect(self._export_activity_log_pdf)
        menu.addAction(audit_pdf_act)
        audit_csv_act = QAction("Export Activity / Audit Log (CSV)", self)
        audit_csv_act.triggered.connect(self._export_activity_log_csv)
        menu.addAction(audit_csv_act)
        return menu

    def _get_export_data(self):
        fltr = self._period_sql_filter()
        kpis = repo.get_report_kpis(period_filter=fltr)
        bookings = repo.get_all_bookings(period_filter=fltr) or []
        return kpis, bookings, self._period

    def _grab_chart_images(self) -> list:
        """High-resolution capture of each chart card into a temp PNG: [(title, png_path)]."""
        import tempfile
        from PySide6.QtGui import QPixmap
        cards = [
            ("Income Trend",              "line_card"),
            ("Payment Methods",           "donut_card"),
            ("Monthly Revenue",           "monthly_card"),
            ("Top Menu Items",            "top_menu_card"),
            ("Year vs Year Comparison",   "year_cmp_card"),
            ("Top Event Locations",       "locations_card"),
            ("Customer Order Frequency",  "freq_card"),
            ("Bookings by Occasion",      "occasion_card"),
        ]
        images = []
        tmp_dir = tempfile.mkdtemp(prefix="jc_report_")
        for title, attr in cards:
            card = getattr(self, attr, None)
            if card is None or card.width() < 10:
                continue
            try:
                sz = card.size()
                w = max(10, sz.width())
                h = max(10, sz.height())
                pixmap = QPixmap(w * 2, h * 2)
                pixmap.setDevicePixelRatio(2.0)
                card.render(pixmap)
                if pixmap.isNull():
                    pixmap = card.grab()

                png = os.path.join(tmp_dir, f"{attr}.png")
                if pixmap.save(png, "PNG"):
                    images.append((title, png))
            except Exception:
                try:
                    pixmap = card.grab()
                    if not pixmap.isNull():
                        png = os.path.join(tmp_dir, f"{attr}.png")
                        if pixmap.save(png, "PNG"):
                            images.append((title, png))
                except Exception:
                    continue
        return images

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "jayraldines_report.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        kpis, bookings, period = self._get_export_data()
        sections = _exporter.build_analytics_sections()
        chart_images = self._grab_chart_images()
        ok = _exporter.export_pdf(path, kpis, bookings, "Business Report", period,
                                  sections=sections, chart_images=chart_images)
        if ok:
            prompt_file_saved(self, path, title="Report PDF Generated", message="Business report PDF generated successfully.")
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
        sections = _exporter.build_analytics_sections()
        ok = _exporter.export_excel(path, kpis, bookings, "Business Report", period,
                                    sections=sections)
        if ok:
            prompt_file_saved(self, path, title="Report Excel Exported", message="Business report Excel spreadsheet exported successfully.")
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
        prompt_file_saved(self, path, title="Report CSV Exported", message="Report bookings CSV exported successfully.")

    def _export_activity_log_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Activity Log PDF", "activity_audit_report.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        entries = repo.get_audit_log(limit=500)
        business = repo.get_business_info()
        ok = _exporter.export_daily_activity_report_pdf(path, entries, business, period_label=self._period or "All Time")
        if ok:
            prompt_file_saved(self, path, title="Activity Report Exported", message="Activity / Audit log report PDF exported successfully.")
        else:
            QMessageBox.warning(self, "Export Failed", "PDF export failed. Make sure reportlab is installed:\npip install reportlab")

    def _export_activity_log_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Activity Log CSV", "activity_audit_report.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        entries = repo.get_audit_log(limit=500)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Time", "User", "Action", "Details"])
            for e in entries:
                writer.writerow([e.get("date", ""), e.get("time", ""), e.get("actor", ""), e.get("action", ""), e.get("description", "")])
        prompt_file_saved(self, path, title="Activity Report Exported", message="Activity / Audit log CSV exported successfully.")