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
        self.addWidget(QLabel("Income Trend (Year-to-Date)"))
        self.itemAt(0).widget().setObjectName("h3")

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
        values = [45, 52, 38, 65, 58, 75, 82]

        upper = QLineSeries()
        pen = QPen(QColor("#E11D48"))
        pen.setWidth(3)
        upper.setPen(pen)
        for i, v in enumerate(values):
            upper.append(i, v)

        lower = QLineSeries()
        for i in range(len(values)):
            lower.append(i, 0)

        area = QAreaSeries(upper, lower)
        grad = QLinearGradient(0, 0, 0, 300)
        grad.setColorAt(0.0, QColor(225, 29, 72, 80))
        grad.setColorAt(1.0, QColor(225, 29, 72, 0))
        area.setBrush(grad)
        area.setPen(Qt.NoPen)

        chart = QChart()
        chart.addSeries(area)
        chart.addSeries(upper)
        chart.legend().hide()
        chart.setAnimationOptions(QChart.SeriesAnimations)

        ax = QBarCategoryAxis()
        ax.append(months)
        _axis_style(ax)
        chart.addAxis(ax, Qt.AlignBottom)
        area.attachAxis(ax)
        upper.attachAxis(ax)

        ay = QValueAxis()
        ay.setRange(0, 100)
        ay.setLabelFormat("%dk")
        _axis_style(ay)
        chart.addAxis(ay, Qt.AlignLeft)
        area.attachAxis(ay)
        upper.attachAxis(ay)

        view = _chart_view(chart)
        view.setMinimumHeight(260)
        view.setRubberBand(QChartView.RubberBand.RectangleRubberBand)

        upper.hovered.connect(lambda pt, state: self._on_hover(pt, state, months))
        self._months = months
        self.addWidget(view)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        reset_btn = QPushButton("Reset Zoom")
        reset_btn.setObjectName("secondaryButton")
        reset_btn.clicked.connect(chart.zoomReset)
        btn_row.addWidget(reset_btn)
        self.addLayout(btn_row)
        self._chart = chart

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
        self.addWidget(QLabel("Payment Methods"))
        self.itemAt(0).widget().setObjectName("h3")

        data = {"Cash": (45, "#E11D48"), "GCash": (30, "#F59E0B"),
                "Bank": (15, "#3B82F6"), "PayMaya": (10, "#22C55E")}

        series = QPieSeries()
        series.setHoleSize(0.55)
        for label, (value, color) in data.items():
            sl = series.append(label, value)
            sl.setColor(QColor(color))
            sl.setLabelColor(QColor("#F9FAFB"))
            sl.hovered.connect(lambda state, s=sl, c=color: self._on_hover(s, state, c))

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setAlignment(Qt.AlignRight)
        chart.legend().setLabelColor(QColor("#9CA3AF"))

        view = _chart_view(chart)
        view.setMinimumHeight(220)
        self.addWidget(view)

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
        self.addWidget(QLabel("Monthly Revenue Breakdown"))
        self.itemAt(0).widget().setObjectName("h3")

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        revenue = [320000, 415000, 280000, 520000, 460000, 590000]
        target  = [400000, 400000, 400000, 400000, 400000, 400000]

        bar_rev = QBarSet("Revenue")
        bar_rev.setColor(QColor("#E11D48"))
        bar_rev.setLabelColor(QColor("#F9FAFB"))
        bar_tgt = QBarSet("Target")
        bar_tgt.setColor(QColor("#374151"))
        bar_tgt.setLabelColor(QColor("#9CA3AF"))

        for v, t in zip(revenue, target):
            bar_rev.append(v / 1000)
            bar_tgt.append(t / 1000)

        series = QBarSeries()
        series.append(bar_rev)
        series.append(bar_tgt)

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations)

        ax = QBarCategoryAxis()
        ax.append(months)
        _axis_style(ax)
        chart.addAxis(ax, Qt.AlignBottom)
        series.attachAxis(ax)

        ay = QValueAxis()
        ay.setRange(0, 700)
        ay.setLabelFormat("%dk")
        _axis_style(ay)
        chart.addAxis(ay, Qt.AlignLeft)
        series.attachAxis(ay)

        view = _chart_view(chart)
        view.setMinimumHeight(260)
        self.addWidget(view)


# ─────────────────────────────────────────────
# CHART 4: Top Menu Items (Horizontal Bar)
# ─────────────────────────────────────────────
class TopMenuItemsChart(QVBoxLayout):
    def __init__(self):
        super().__init__()
        self.addWidget(QLabel("Top-Selling Menu Items"))
        self.itemAt(0).widget().setObjectName("h3")

        items  = ["Lechon de Leche", "Kare-Kare", "Chicken Inasal", "Pancit Malabon", "Leche Flan"]
        orders = [48, 35, 29, 22, 18]

        bar_set = QBarSet("Orders")
        bar_set.setColor(QColor("#F59E0B"))
        bar_set.setLabelColor(QColor("#F9FAFB"))
        for v in orders:
            bar_set.append(v)

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().hide()

        ax = QBarCategoryAxis()
        ax.append(items)
        _axis_style(ax)
        chart.addAxis(ax, Qt.AlignBottom)
        series.attachAxis(ax)

        ay = QValueAxis()
        ay.setRange(0, 60)
        ay.setLabelFormat("%d")
        _axis_style(ay)
        chart.addAxis(ay, Qt.AlignLeft)
        series.attachAxis(ay)

        view = _chart_view(chart)
        view.setMinimumHeight(220)
        self.addWidget(view)


# ─────────────────────────────────────────────
# CHART 5: Customer Order Frequency (Bar)
# ─────────────────────────────────────────────
class CustomerFrequencyChart(QVBoxLayout):
    def __init__(self):
        super().__init__()
        self.addWidget(QLabel("Customer Order Frequency"))
        self.itemAt(0).widget().setObjectName("h3")

        customers = ["Maria Santos", "TechCorp", "Cruz Family", "Smith Wedding", "Others"]
        counts    = [3, 2, 2, 1, 8]

        colors = ["#E11D48", "#F59E0B", "#3B82F6", "#22C55E", "#6B7280"]

        series = QPieSeries()
        for label, count, color in zip(customers, counts, colors):
            sl = series.append(f"{label} ({count})", count)
            sl.setColor(QColor(color))
            sl.setLabelColor(QColor("#F9FAFB"))

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setAlignment(Qt.AlignRight)
        chart.legend().setLabelColor(QColor("#9CA3AF"))

        view = _chart_view(chart)
        view.setMinimumHeight(220)
        self.addWidget(view)


# ─────────────────────────────────────────────
# MAIN REPORTS PAGE
# ─────────────────────────────────────────────
class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainBackground")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(scroll_content)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(32)

        # HEADER
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        title_lbl = QLabel("Reports & Analytics")
        title_lbl.setObjectName("pageTitle")
        sub_lbl = QLabel("Track performance, income, and booking trends.")
        sub_lbl.setObjectName("subtitle")
        v_title.addWidget(title_lbl)
        v_title.addWidget(sub_lbl)
        header_row.addLayout(v_title)
        header_row.addStretch()

        btn_export = QPushButton("  Export CSV")
        btn_export.setObjectName("secondaryButton")
        btn_export.setIcon(btn_icon_secondary("export"))
        btn_export.setIconSize(QSize(16, 16))
        btn_export.clicked.connect(self._export_csv)
        header_row.addWidget(btn_export)
        self.main_layout.addLayout(header_row)

        # KPI CARDS
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(24)
        kpis = repo.get_dashboard_kpis()
        total_bkg = kpis.get("pending_bookings", 0) + 124
        weekly    = kpis.get("weekly_revenue", 12450)
        unpaid    = kpis.get("unpaid_invoices", 4200)

        kpi_layout.addWidget(self._kpi("Total Bookings",    "124",                 "8 Today | 32 Week | 124 Month"))
        kpi_layout.addWidget(self._kpi("Total Pax Booked",  "3,450",               "+12% from last month", "#22C55E"))
        kpi_layout.addWidget(self._kpi("Estimated Income",  f"PHP {weekly:,.0f}",  "+8.5% from last month", "#22C55E"))
        kpi_layout.addWidget(self._kpi("Unpaid Invoices",   f"PHP {unpaid:,.0f}",  "3 invoices overdue", "#EF4444"))
        self.main_layout.addLayout(kpi_layout)

        # ROW 1: Income Area + Payment Donut
        row1 = QHBoxLayout()
        row1.setSpacing(24)

        line_card = QFrame()
        line_card.setObjectName("card")
        line_card.setLayout(IncomeAreaChart())
        line_card.layout().setContentsMargins(28, 24, 28, 20)
        row1.addWidget(line_card, 3)

        donut_card = QFrame()
        donut_card.setObjectName("card")
        donut_card.setLayout(PaymentDonutChart())
        donut_card.layout().setContentsMargins(28, 24, 28, 20)
        row1.addWidget(donut_card, 2)

        self.main_layout.addLayout(row1)

        # ROW 2: Monthly Revenue + Top Menu Items
        row2 = QHBoxLayout()
        row2.setSpacing(24)

        monthly_card = QFrame()
        monthly_card.setObjectName("card")
        monthly_card.setLayout(MonthlyRevenueChart())
        monthly_card.layout().setContentsMargins(28, 24, 28, 20)
        row2.addWidget(monthly_card, 2)

        top_menu_card = QFrame()
        top_menu_card.setObjectName("card")
        top_menu_card.setLayout(TopMenuItemsChart())
        top_menu_card.layout().setContentsMargins(28, 24, 28, 20)
        row2.addWidget(top_menu_card, 2)

        self.main_layout.addLayout(row2)

        # ROW 3: Customer Frequency (full width)
        freq_card = QFrame()
        freq_card.setObjectName("card")
        freq_card.setLayout(CustomerFrequencyChart())
        freq_card.layout().setContentsMargins(28, 24, 28, 20)
        self.main_layout.addWidget(freq_card)

        # RECENT BOOKINGS TABLE
        table_card = HoverCard()
        t_layout = QVBoxLayout(table_card)
        t_layout.setContentsMargins(24, 24, 24, 24)
        t_layout.setSpacing(16)

        t_head = QHBoxLayout()
        t_head_lbl = QLabel("Recent Booking Statistics")
        t_head_lbl.setObjectName("h2")
        t_head.addWidget(t_head_lbl)
        t_head.addStretch()
        t_layout.addLayout(t_head)

        self.table = QTableWidget(5, 5)
        self.table.setHorizontalHeaderLabels(["ID & DATE", "CLIENT", "PACKAGE", "PAX", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(320)

        rows_data = [
            ("BKG-001", "Oct 24, 2026", "TechCorp Inc.",  "Premium Corporate", 45, "", "Confirmed"),
            ("BKG-002", "Oct 25, 2026", "Smith Wedding",  "Grand Banquet",      58, "NEAR LIMIT", "Pending"),
            ("BKG-003", "Oct 26, 2026", "Sarah's 18th",   "Standard Buffet",    60, "LIMIT REACHED", "Pending"),
            ("BKG-004", "Oct 28, 2026", "Local NGO Meet", "Basic Snack Box",    30, "", "Confirmed"),
            ("BKG-005", "Oct 29, 2026", "Alumni Reunion", "Premium Corporate",  55, "NEAR LIMIT", "Pending"),
        ]

        for row, data in enumerate(rows_data):
            self.table.setRowHeight(row, 64)
            id_lbl = QLabel(
                f"<span style='font-weight:700;font-size:13px;'>{data[0]}</span>"
                f"<br><span style='font-size:11px;color:#9CA3AF;'>{data[1]}</span>"
            )
            self.table.setCellWidget(row, 0, id_lbl)
            self.table.setCellWidget(row, 1, QLabel(f"<span style='font-weight:600;font-size:13px;'>{data[2]}</span>"))
            self.table.setCellWidget(row, 2, QLabel(f"<span style='font-size:13px;'>{data[3]}</span>"))
            self.table.setCellWidget(row, 3, create_pax_limit_badge(data[4], data[5]))
            self.table.setCellWidget(row, 4, create_status_badge(data[6]))

        t_layout.addWidget(self.table)
        self.main_layout.addWidget(table_card)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def _kpi(self, title, val, sub, sub_color=None):
        card = HoverCard()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)

        top = QHBoxLayout()
        lbl_t = QLabel(title.upper())
        lbl_t.setObjectName("kpiLabel")
        top.addWidget(lbl_t)
        top.addStretch()
        lay.addLayout(top)

        lbl_v = QLabel(val)
        lbl_v.setObjectName("kpiValue")
        lay.addWidget(lbl_v)

        lbl_s = QLabel(sub)
        if sub_color:
            lbl_s.setStyleSheet(f"color: {sub_color}; font-weight: 600; font-size: 12px;")
        else:
            lbl_s.setObjectName("subtitle")
        lay.addWidget(lbl_s)
        lay.addStretch()
        return card

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Reports", "reports.csv", "CSV Files (*.csv)")
        if not path:
            return
        rows = repo.get_all_bookings() or [
            {"id": "BKG-001", "date": "Oct 24, 2026", "name": "TechCorp Inc.",  "pax": "45",  "total": "PHP 45,000",  "status": "CONFIRMED"},
            {"id": "BKG-002", "date": "Oct 25, 2026", "name": "Smith Wedding",  "pax": "58",  "total": "PHP 120,000", "status": "PENDING"},
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Date", "Client", "Pax", "Total", "Status"])
            for b in rows:
                writer.writerow([b.get("id"), b.get("date"), b.get("name"),
                                 b.get("pax"), b.get("total"), b.get("status")])
        QMessageBox.information(self, "Export", f"Exported to:\n{path}")
