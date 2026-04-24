import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QFrame, QLabel, QPushButton, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QScrollArea, 
                               QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
                               QMessageBox, QToolTip)
from PySide6.QtCore import Qt, QPropertyAnimation, QVariantAnimation, QEasingCurve, QMargins, QPointF, QSize
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPen, QCursor

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted
from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QAreaSeries, 
                              QPieSeries, QBarCategoryAxis, QValueAxis, QLegend)

# ==========================================
# 1. GLOBAL STYLESHEET (Modern SaaS + Beautiful Tooltips)
# ==========================================
STYLESHEET = """
* {
    font-family: "Inter", "Roboto", "Segoe UI", sans-serif;
    outline: none;
}
QMainWindow, QWidget#mainBackground {
    background-color: #F8FAFC; 
}
QFrame#saasCard {
    background-color: #FFFFFF;
    border-radius: 16px;
    border: 1px solid #F1F5F9;
}
QPushButton#primaryButton {
    background-color: #DC2626;
    color: #FFFFFF;
    border: none;
    font-size: 13px;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
}
QPushButton#primaryButton:hover {
    background-color: #EF4444;
}
QPushButton#secondaryButton {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #E2E8F0;
    font-size: 13px;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
}
QPushButton#secondaryButton:hover {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    color: #DC2626;
}
QPushButton#pageButton {
    background-color: transparent;
    color: #64748B;
    font-weight: 600;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton#pageButton:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}
QPushButton#pageButtonActive {
    background-color: #FEE2E2;
    color: #DC2626;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
}
QTableWidget {
    background-color: transparent;
    alternate-background-color: #F8FAFC;
    border: none;
    color: #1E293B;
}
QTableWidget::item {
    border-bottom: 1px solid #F1F5F9;
    padding: 5px;
}
QTableWidget::item:hover {
    background-color: #F1F5F9;
}
QHeaderView::section {
    background-color: #FFFFFF;
    color: #94A3B8;
    font-weight: 800;
    font-size: 11px;
    padding: 16px 8px;
    border: none;
    border-bottom: 2px solid #E2E8F0;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

/* IMPROVED MODERN TOOLTIP (Highly Readable) */
QToolTip {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: bold;
}
"""

# ==========================================
# 2. ANIMATIONS & MICRO-INTERACTIONS
# ==========================================
def create_soft_shadow(widget, radius=20, y_offset=8, opacity=5):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setColor(QColor(0, 0, 0, opacity))
    shadow.setOffset(0, y_offset)
    widget.setGraphicsEffect(shadow)
    return shadow

class HoverCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("saasCard")
        self.shadow = create_soft_shadow(self, radius=20, y_offset=5, opacity=6)
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
    # Prevent crash if shadow not ready
        if not hasattr(self, "shadow") or self.shadow is None:
            return

        try:
            self.shadow.setBlurRadius(15 + value)
            self.shadow.setOffset(0, 4 + (value / 2))
            self.shadow.setColor(QColor(0, 0, 0, 15 + int(value / 3)))
        except RuntimeError:
            # Handles cases where Qt internally deleted the effect
            return
    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(10)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(10)
        self.anim.setEndValue(0)
        self.anim.start()
        super().leaveEvent(event)

# --- Badge Generators ---
def create_status_badge(text):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    lbl = QLabel(f" {text} ")
    if "Completed" in text:
        lbl.setStyleSheet("font-weight: 700; font-size: 11px; padding: 4px 12px; border-radius: 12px; border: 1px solid rgba(110,231,183,0.3); background-color: rgba(110,231,183,0.15); color: #6ee7b7;")
    else:
        lbl.setStyleSheet("font-weight: 700; font-size: 11px; padding: 4px 12px; border-radius: 12px; border: 1px solid rgba(197,164,109,0.3); background-color: rgba(197,164,109,0.15); color: #c5a46d;")
    layout.addWidget(lbl)
    return widget

def create_pax_limit_badge(pax, limit_status):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
    lbl_pax = QLabel(str(pax))
    lbl_pax.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 13px;")
    layout.addWidget(lbl_pax)
    
    if limit_status:
        badge = QLabel(limit_status)
        if limit_status == "LIMIT REACHED":
            badge.setStyleSheet("font-weight: 800; font-size: 10px; padding: 3px 8px; border-radius: 6px; background-color: rgba(248,113,113,0.15); color: #f87171; border: 1px solid rgba(248,113,113,0.3);")
        else:
            badge.setStyleSheet("font-weight: 800; font-size: 10px; padding: 3px 8px; border-radius: 6px; background-color: rgba(197,164,109,0.12); color: #c5a46d; border: 1px solid rgba(197,164,109,0.3);")
        layout.addWidget(badge)
    return widget

# ==========================================
# 3. INTERACTIVE CHARTS (Fixed + Enhanced)
# ==========================================
class AreaChartCard(QVBoxLayout):
    def __init__(self, title):
        super().__init__()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:#1E293B;'>{title}</span>"))
        
        self.upper_series = QLineSeries()
        data = [45, 52, 38, 65, 58, 75, 82]
        for i, val in enumerate(data): 
            self.upper_series.append(i, val)
        self.pen = QPen(QColor("#c5a46d"))
        self.pen.setWidth(3)
        self.upper_series.setPen(self.pen)

        self.lower_series = QLineSeries()
        for i in range(len(data)): 
            self.lower_series.append(i, 0)

        self.area = QAreaSeries(self.upper_series, self.lower_series)
        self.gradient = QLinearGradient(0, 0, 0, 300)
        self.gradient.setColorAt(0.0, QColor(197, 164, 109, 80))
        self.gradient.setColorAt(1.0, QColor(197, 164, 109, 0))
        self.area.setBrush(self.gradient)
        self.area.setPen(Qt.NoPen)

        self.chart = QChart()
        self.chart.addSeries(self.area)
        self.chart.addSeries(self.upper_series)
        self.chart.legend().hide()
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        self.chart.setBackgroundBrush(Qt.transparent)

        self.axis_x = QBarCategoryAxis()
        self.axis_x.append(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"])
        self.axis_x.setLinePenColor(Qt.transparent)
        self.axis_x.setGridLineColor(Qt.transparent)
        self.axis_x.setLabelsColor(QColor("#9aa0a6"))
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.area.attachAxis(self.axis_x)
        self.upper_series.attachAxis(self.axis_x)

        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setLabelFormat("₱%ik")          # Fixed peso symbol on axis
        self.axis_y.setGridLineColor(QColor("#20242c"))
        self.axis_y.setLinePenColor(Qt.transparent)
        self.axis_y.setLabelsColor(QColor("#9aa0a6"))
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.area.attachAxis(self.axis_y)
        self.upper_series.attachAxis(self.axis_y)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        self.chart_view.setMinimumHeight(300)
        self.chart_view.setRubberBand(QChartView.RubberBand.RectangleRubberBand)

        # Enhanced hover with rich tooltip
        self.upper_series.hovered.connect(self._on_hovered)

        self.addWidget(self.chart_view)

        # Reset button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.reset_btn = QPushButton("  Reset Zoom")
        self.reset_btn.setObjectName("secondaryButton")
        self.reset_btn.setIcon(btn_icon_secondary("reset-zoom"))
        self.reset_btn.setIconSize(QSize(14, 14))
        self.reset_btn.clicked.connect(self.reset_chart_zoom)
        btn_layout.addWidget(self.reset_btn)
        self.addLayout(btn_layout)

    def _on_hovered(self, point: QPointF, state: bool):
        if state:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
            month_idx = int(round(point.x()))
            if 0 <= month_idx < len(months):
                month = months[month_idx]
                value = point.y()
                # Rich, fully visible tooltip with all necessary details
                text = f"""
<b style="font-size:15px;color:#FFFFFF;">{month} 2026</b><br>
<span style="color:#FCA5A5;">Income</span> <b style="color:#FFFFFF;">₱{value:.0f}k</b><br>
<span style="font-size:11px;color:#94A3B8;">Year-to-Date Trend • Click & drag to zoom</span>
"""
                QToolTip.showText(QCursor.pos(), text.strip())
        else:
            QToolTip.hideText()

    def reset_chart_zoom(self):
        self.chart.zoomReset()


class DonutChartCard(QVBoxLayout):
    def __init__(self, title):
        super().__init__()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:#1E293B;'>{title}</span>"))
        
        self.series = QPieSeries()
        self.series.setHoleSize(0.55)
        
        # Short labels for clean display (no "...")
        self.slice_data = {
            "Cash":        (45, "#c5a46d"),
            "GCash":       (30, "#d4b580"),
            "Bank":        (15, "#a8885a"),
            "PayMaya":     (10, "#7a6040")
        }
        self.full_names = {
            "Cash": "Cash",
            "GCash": "GCash",
            "Bank": "Bank Transfer",
            "PayMaya": "PayMaya"
        }

        for label, (value, color) in self.slice_data.items():
            slice_obj = self.series.append(label, value)
            slice_obj.setColor(QColor(color))
            slice_obj.hovered.connect(lambda state, s=slice_obj: self._on_slice_hovered(s, state))
            slice_obj.clicked.connect(lambda s=slice_obj: self._on_slice_clicked(s))

        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        self.chart.setBackgroundBrush(Qt.transparent)
        self.chart.legend().setAlignment(Qt.AlignRight)
        self.chart.legend().setMarkerShape(QLegend.MarkerShape.MarkerShapeCircle)
        self.chart.legend().setLabelColor(QColor("#9aa0a6"))
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        self.chart_view.setMinimumHeight(200)
        self.addWidget(self.chart_view)

    def _on_slice_hovered(self, slice_obj, state):
        slice_obj.setExploded(state)
        slice_obj.setLabelVisible(state)
        
        if state:
            full_name = self.full_names.get(slice_obj.label(), slice_obj.label())
            percent = slice_obj.value()
            text = f"""
<b style="font-size:15px;">{full_name}</b><br>
<span style="color:#FCA5A5;">{percent:.0f}%</span> of total payments
"""
            QToolTip.showText(QCursor.pos(), text.strip())
        else:
            QToolTip.hideText()

    def _on_slice_clicked(self, slice_obj):
        full_name = self.full_names.get(slice_obj.label(), slice_obj.label())
        percent = slice_obj.value()
        estimated = percent / 100 * 415000
        QMessageBox.information(
            None,
            "Payment Method Details",
            f"<h3 style='color:#DC2626;'>{full_name}</h3>"
            f"<p><b>{percent:.0f}%</b> of all payments this period</p>"
            f"<p>Estimated amount: <b>₱{estimated:,.0f}</b></p>"
            f"<p style='font-size:12px;color:#64748B;'>Click any slice again to close</p>"
        )


# ==========================================
# 4. MAIN REPORTS DASHBOARD
# ==========================================
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

        # --- HEADER ---
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.addWidget(QLabel("<span style='font-size: 28px; font-weight: 800; color: #0F172A;'>Reports & Analytics</span>"))
        v_title.addWidget(QLabel("<span style='color: #64748B; font-size: 14px;'>Track your performance, income, and booking trends.</span>"))
        header_row.addLayout(v_title)
        
        header_row.addStretch()
        btn_date = QPushButton("  Custom Date Range")
        btn_date.setObjectName("secondaryButton")
        btn_date.setIcon(btn_icon_secondary("date-range"))
        btn_date.setIconSize(QSize(16, 16))
        btn_filter = QPushButton("  Filter by Payment/Package")
        btn_filter.setObjectName("primaryButton")
        btn_filter.setIcon(btn_icon_primary("filter"))
        btn_filter.setIconSize(QSize(16, 16))
        header_row.addWidget(btn_date)
        header_row.addWidget(btn_filter)
        self.main_layout.addLayout(header_row)

        # --- KPIS ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(24)
        kpi_layout.addWidget(self.build_kpi_card("Total Bookings", "124", "8 Today | 32 Week | 124 Month", icon="📅"))
        kpi_layout.addWidget(self.build_kpi_card("Total Pax Booked", "3,450", "↗ +12% from last month", "#16A34A", icon="👥"))
        kpi_layout.addWidget(self.build_kpi_card("Estimated Income", "₱ 415k", "↗ +8.5% from last month", "#16A34A", icon="$"))
        
        target_card = HoverCard()
        t_lay = QVBoxLayout(target_card)
        t_lay.setContentsMargins(24, 24, 24, 24)
        t_head = QHBoxLayout()
        t_head.addWidget(QLabel("<span style='color: #64748B; font-weight: 600; font-size: 13px;'>Weekly Target</span>"))
        t_head.addStretch()
        t_head.addWidget(QLabel("🎯"))
        t_lay.addLayout(t_head)
        t_lay.addWidget(QLabel("<span style='font-size: 36px; font-weight: 800; color: #0F172A;'>₱ 85k <span style='font-size:14px; color:#94A3B8;'>/ ₱ 100k</span></span>"))
        
        prog = QFrame()
        prog.setFixedHeight(8)
        prog.setStyleSheet("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #a8885a, stop:1 #c5a46d); margin-right: 40px; border-radius: 4px;")
        t_lay.addWidget(prog)
        t_lay.addWidget(QLabel("<span style='color: #64748B; font-weight: 600; font-size: 12px;'>85% of weekly goal achieved</span>"))
        kpi_layout.addWidget(target_card)
        self.main_layout.addLayout(kpi_layout)

        # --- INTERACTIVE CHARTS ---
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(32)
        
        line_card = QFrame()
        line_card.setStyleSheet("background-color: #1a1d24; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);")
        line_card.setLayout(AreaChartCard("Income Trends (Year-to-Date)"))
        line_card.layout().setContentsMargins(32, 24, 32, 24)
        charts_layout.addWidget(line_card, 2) 
        
        donut_card = QFrame()
        donut_card.setStyleSheet("background-color: #1a1d24; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08);")
        donut_card.setLayout(DonutChartCard("Payment Methods"))
        donut_card.layout().setContentsMargins(32, 24, 32, 24)
        charts_layout.addWidget(donut_card, 1) 
        
        self.main_layout.addLayout(charts_layout)

        # --- RECENT BOOKING STATISTICS (now fully scrollable) ---
        table_card = HoverCard()
        t_layout = QVBoxLayout(table_card)
        t_layout.setContentsMargins(24, 24, 24, 24)
        t_layout.setSpacing(16)
        
        t_head = QHBoxLayout()
        t_head.addWidget(QLabel("<span style='font-size: 18px; font-weight: 800; color: #1E293B;'>Recent Booking Statistics</span>"))
        t_head.addStretch()
        view_btn = QPushButton("View All")
        view_btn.setStyleSheet("color: #c5a46d; font-weight: bold; border: none; background: transparent;")
        t_head.addWidget(view_btn)
        t_layout.addLayout(t_head)

        self.table = QTableWidget(5, 5)
        self.table.setHorizontalHeaderLabels(["ID & DATE", "EVENT / CLIENT", "PACKAGE", "PAX", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(420)   # Forces enough height so table is always visible and scroll works

        rows_data = [
            ("BKG-001\nOct 24, 2026", "TechCorp Inc.", "Premium Corporate", 45, "", "✓ Completed"),
            ("BKG-002\nOct 25, 2026", "Smith Wedding", "Grand Banquet", 58, "NEAR LIMIT", "⏱ Pending"),
            ("BKG-003\nOct 26, 2026", "Sarah's 18th", "Standard Buffet", 60, "LIMIT REACHED", "⏱ Pending"),
            ("BKG-004\nOct 28, 2026", "Local NGO Meet", "Basic Snack Box", 30, "", "✓ Completed"),
            ("BKG-005\nOct 29, 2026", "Alumni Reunion", "Premium Corporate", 55, "NEAR LIMIT", "⏱ Pending"),
        ]

        for row, data in enumerate(rows_data):
            self.table.setRowHeight(row, 70)
            
            id_date = QLabel(f"<span style='font-weight:700; color:#1E293B; font-size:13px;'>{data[0].split(chr(10))[0]}</span><br><span style='color:#64748B; font-size:12px;'>{data[0].split(chr(10))[1]}</span>")
            self.table.setCellWidget(row, 0, id_date)
            
            client = QLabel(f"<span style='font-weight:700; color:#1E293B; font-size:13px;'>{data[1]}</span>")
            self.table.setCellWidget(row, 1, client)
            
            pkg = QLabel(f"<span style='color:#475569; font-size:13px;'>{data[2]}</span>")
            self.table.setCellWidget(row, 2, pkg)
            
            self.table.setCellWidget(row, 3, create_pax_limit_badge(data[3], data[4]))
            self.table.setCellWidget(row, 4, create_status_badge(data[5]))

        t_layout.addWidget(self.table)
        
        footer_row = QHBoxLayout()
        footer_row.addWidget(QLabel("<span style='color: #64748B; font-size: 13px; font-weight: 500;'>Showing 5 of 42 bookings</span>"))
        footer_row.addStretch()
        
        btn_prev = QPushButton("Previous")
        btn_prev.setObjectName("pageButton")
        btn_1 = QPushButton("1")
        btn_1.setObjectName("pageButtonActive") 
        btn_2 = QPushButton("2")
        btn_2.setObjectName("pageButton")
        btn_3 = QPushButton("3")
        btn_3.setObjectName("pageButton")
        btn_next = QPushButton("Next")
        btn_next.setObjectName("pageButton")
        
        for btn in [btn_prev, btn_1, btn_2, btn_3, btn_next]:
            footer_row.addWidget(btn)
            
        t_layout.addLayout(footer_row)
        self.main_layout.addWidget(table_card)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def build_kpi_card(self, title, val, sub, sub_color="#64748B", icon=""):
        card = HoverCard()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        
        top = QHBoxLayout()
        top.addWidget(QLabel(f"<span style='color: #64748B; font-weight: 600; font-size: 13px;'>{title}</span>"))
        top.addStretch()
        if icon: top.addWidget(QLabel(icon))
        lay.addLayout(top)
        
        lay.addWidget(QLabel(f"<span style='font-size: 36px; font-weight: 800; color: #0F172A;'>{val}</span>"))
        lay.addWidget(QLabel(f"<span style='color: {sub_color}; font-weight: 600; font-size: 12px;'>{sub}</span>"))
        return card

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    window = QMainWindow()
    window.setWindowTitle("SaaS Reports Dashboard")
    window.resize(1280, 920)   # Slightly taller so everything fits better with scroll
    
    reports_view = ReportsPage()
    window.setCentralWidget(reports_view)
    
    window.show()
    sys.exit(app.exec())