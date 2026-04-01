import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QFrame, QLabel, QPushButton, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QScrollArea, 
                               QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QPropertyAnimation, QVariantAnimation, QEasingCurve, QMargins
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPen
from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QAreaSeries, 
                              QPieSeries, QBarCategoryAxis, QValueAxis, QLegend)

# ==========================================
# 1. GLOBAL STYLESHEET (SaaS Theme)
# ==========================================
STYLESHEET = """
* {
    font-family: "Inter", "Roboto", "Segoe UI", sans-serif;
    outline: none;
}
QMainWindow, QWidget#mainBackground {
    background-color: #F8FAFC; 
}
/* Cards */
QFrame#saasCard {
    background-color: #FFFFFF;
    border-radius: 16px;
    border: 1px solid #F1F5F9;
}
/* Buttons */
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
    color: #E53935;
}
/* Table */
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
/* Scrollbars */
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
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

# ==========================================
# 2. ANIMATION & UX UTILITIES
# ==========================================
def create_soft_shadow(widget, radius=15, y_offset=4, opacity=15):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setColor(QColor(0, 0, 0, opacity))
    shadow.setOffset(0, y_offset)
    widget.setGraphicsEffect(shadow)
    return shadow

def apply_fade_in(widget, duration=800):
    # Attached to widget to prevent Segfaults
    widget._opacity_effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(widget._opacity_effect)
    
    widget._fade_anim = QPropertyAnimation(widget._opacity_effect, b"opacity", widget)
    widget._fade_anim.setDuration(duration)
    widget._fade_anim.setStartValue(0.0)
    widget._fade_anim.setEndValue(1.0)
    widget._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
    widget._fade_anim.start()

# ==========================================
# 3. COMPONENTS
# ==========================================
class HoverCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("saasCard")
        self.shadow = create_soft_shadow(self, radius=15, y_offset=3, opacity=10)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
        self.shadow.setBlurRadius(15 + (value * 1.5))
        self.shadow.setOffset(0, 3 + (value / 2))
        self.shadow.setColor(QColor(0, 0, 0, 10 + int(value / 2)))

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

def create_pill_badge(text, variant="success"):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    
    base = "font-weight: 700; font-size: 11px; padding: 4px 12px; border-radius: 12px; border: 1px solid"
    if variant == "success":
        lbl.setStyleSheet(f"{base} #bbf7d0; background-color: #dcfce7; color: #166534;")
    elif variant == "warning":
        lbl.setStyleSheet(f"{base} #fef08a; background-color: #fef9c3; color: #854d0e;")
    elif variant == "danger":
        lbl.setStyleSheet(f"{base} #fecaca; background-color: #fee2e2; color: #b91c1c;")
        
    layout.addWidget(lbl)
    return widget

# ==========================================
# 4. CHARTS (Segfault-proofed)
# ==========================================
class AreaChartCard(QVBoxLayout):
    def __init__(self, title):
        super().__init__()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:#0F172A;'>{title}</span>"))
        
        self.upper_series = QLineSeries()
        data = [45, 52, 38, 65, 58, 75, 82]
        for i, val in enumerate(data):
            self.upper_series.append(i, val)
            
        self.pen = QPen(QColor("#E53935"))
        self.pen.setWidth(3)
        self.upper_series.setPen(self.pen)

        self.lower_series = QLineSeries()
        for i in range(len(data)):
            self.lower_series.append(i, 0)

        self.area = QAreaSeries(self.upper_series, self.lower_series)
        self.gradient = QLinearGradient(0, 0, 0, 300)
        self.gradient.setColorAt(0.0, QColor(229, 57, 53, 100)) 
        self.gradient.setColorAt(1.0, QColor(229, 57, 53, 0))   
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
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.area.attachAxis(self.axis_x)
        self.upper_series.attachAxis(self.axis_x)

        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setLabelFormat("₱%ik")
        self.axis_y.setGridLineColor(QColor("#F1F5F9"))
        self.axis_y.setLinePenColor(Qt.transparent)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.area.attachAxis(self.axis_y)
        self.upper_series.attachAxis(self.axis_y)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        self.chart_view.setMinimumHeight(300)
        self.addWidget(self.chart_view)

class DonutChartCard(QVBoxLayout):
    def __init__(self, title):
        super().__init__()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:#0F172A;'>{title}</span>"))
        
        self.series = QPieSeries()
        self.series.setHoleSize(0.55) 
        
        self.series.append("Cash", 45).setColor(QColor("#E53935"))
        self.series.append("GCash", 30).setColor(QColor("#F87171"))
        self.series.append("Bank", 25).setColor(QColor("#FCA5A5"))
        
        self.series.hovered.connect(self._on_hover)

        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        self.chart.setBackgroundBrush(Qt.transparent)
        self.chart.legend().setAlignment(Qt.AlignRight)
        self.chart.legend().setMarkerShape(QLegend.MarkerShape.MarkerShapeCircle)
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        self.chart_view.setMinimumHeight(200)
        self.addWidget(self.chart_view)

    def _on_hover(self, slice, state):
        slice.setExploded(state)
        slice.setExplodeDistanceFactor(0.08)


# ==========================================
# 5. MAIN REPORTS PAGE
# ==========================================
class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainBackground")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) 
        
        apply_fade_in(self, duration=800)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(scroll_content)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(32)

        # Header
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.addWidget(QLabel("<span style='font-size: 28px; font-weight: 800; color: #0F172A;'>Reports & Analytics</span>"))
        v_title.addWidget(QLabel("<span style='color: #64748B; font-size: 14px;'>Track your performance, income, and booking trends.</span>"))
        header_row.addLayout(v_title)
        
        header_row.addStretch()
        btn_filter = QPushButton("⚲ Filter Data")
        btn_filter.setObjectName("secondaryButton")
        header_row.addWidget(btn_filter)
        self.main_layout.addLayout(header_row)

        # KPIs
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(24)
        kpi_layout.addWidget(self.build_kpi_card("Total Bookings", "124", "8 Today | 32 Week"))
        kpi_layout.addWidget(self.build_kpi_card("Total Pax", "3,450", "↗ +12% from last month", "#16A34A"))
        kpi_layout.addWidget(self.build_kpi_card("Est. Income", "₱ 415k", "↗ +8.5% from last month", "#16A34A"))
        self.main_layout.addLayout(kpi_layout)

        # Charts
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(24)
        line_card = HoverCard()
        line_card.setLayout(AreaChartCard("Income Trends (YTD)"))
        charts_layout.addWidget(line_card, 2) 
        donut_card = HoverCard()
        donut_card.setLayout(DonutChartCard("Payment Methods"))
        charts_layout.addWidget(donut_card, 1) 
        self.main_layout.addLayout(charts_layout)

        # Table
        table_card = HoverCard()
        t_layout = QVBoxLayout(table_card)
        t_layout.setContentsMargins(24, 24, 24, 24)
        
        t_head = QHBoxLayout()
        t_head.addWidget(QLabel("<span style='font-size: 18px; font-weight: 700; color: #0F172A;'>Recent Statistics</span>"))
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

        rows_data = [
            ("BKG-001\nOct 24", "TechCorp Inc.", "Premium", 45, "Completed"),
            ("BKG-002\nOct 25", "Smith Wedding", "Banquet", 58, "Pending"),
            ("BKG-003\nOct 26", "Sarah's 18th", "Standard", 60, "Limit Reached"),
        ]

        for row, data in enumerate(rows_data):
            self.table.setRowHeight(row, 65)
            self.table.setItem(row, 0, QTableWidgetItem(data[0]))
            
            name_lbl = QTableWidgetItem(data[1])
            font = name_lbl.font()
            font.setBold(True)
            name_lbl.setFont(font)
            self.table.setItem(row, 1, name_lbl)
            self.table.setItem(row, 2, QTableWidgetItem(data[2]))
            
            if "Limit" in data[4]:
                self.table.setCellWidget(row, 3, create_pill_badge(str(data[3]), "danger"))
            else:
                self.table.setItem(row, 3, QTableWidgetItem(str(data[3])))
                
            status_var = "success" if "Completed" in data[4] else ("danger" if "Limit" in data[4] else "warning")
            self.table.setCellWidget(row, 4, create_pill_badge(data[4], status_var))

        t_layout.addWidget(self.table)
        self.main_layout.addWidget(table_card)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    def build_kpi_card(self, title, val, sub, sub_color="#64748B"):
        card = HoverCard()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.addWidget(QLabel(f"<span style='color: #64748B; font-weight: 600; font-size: 13px; text-transform: uppercase;'>{title}</span>"))
        lay.addWidget(QLabel(f"<span style='font-size: 32px; font-weight: 800; color: #0F172A;'>{val}</span>"))
        lay.addWidget(QLabel(f"<span style='color: {sub_color}; font-weight: 600; font-size: 12px;'>{sub}</span>"))
        return card

# ==========================================
# 6. APPLICATION RUNNER
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    window = QMainWindow()
    window.setWindowTitle("SaaS Reports Dashboard")
    window.resize(1200, 800)
    
    # Set our Reports Page as the main view
    reports_view = ReportsPage()
    window.setCentralWidget(reports_view)
    
    window.show()
    sys.exit(app.exec())