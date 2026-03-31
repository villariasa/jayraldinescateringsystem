from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QGraphicsDropShadowEffect, QScrollArea, 
                               QProgressBar, QToolTip)
from PySide6.QtCore import Qt, QPoint, QMargins
from PySide6.QtGui import QCursor, QColor, QFont, QPainter, QPen
from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QBarSeries, 
                              QBarSet, QBarCategoryAxis, QValueAxis, QPieSeries, QPieSlice, QLegend)

def create_shadow():
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(15)
    shadow.setColor(QColor(0, 0, 0, 20)) 
    shadow.setOffset(0, 3)
    return shadow

# --- HELPER: Limit Badges for Table ---
def create_limit_badge(pax_num):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(5, 2, 5, 2)
    layout.setSpacing(10)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
    lbl_num = QLabel(str(pax_num))
    lbl_num.setStyleSheet("font-weight: bold; color: #1e293b;")
    layout.addWidget(lbl_num)
    
    if pax_num == 60:
        badge = QLabel("! LIMIT REACHED")
        badge.setStyleSheet("background-color: #fee2e2; color: #b91c1c; font-weight: bold; font-size: 10px; padding: 4px 6px; border-radius: 4px;")
        layout.addWidget(badge)
    elif pax_num >= 55:
        badge = QLabel("! NEAR LIMIT")
        badge.setStyleSheet("background-color: #fef1f2; color: #f43f5e; font-weight: bold; font-size: 10px; padding: 4px 6px; border-radius: 4px;")
        layout.addWidget(badge)
        
    return widget

# --- HELPER: Status Badges for Table ---
def create_status_badge(status_text):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(5, 2, 5, 2)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    lbl = QLabel(status_text)
    if "Completed" in status_text:
        lbl.setStyleSheet("background-color: #dcfce7; color: #166534; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px; border: 1px solid #bbf7d0;")
    else:
        lbl.setStyleSheet("background-color: #fef9c3; color: #854d0e; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px; border: 1px solid #fef08a;")
    layout.addWidget(lbl)
    return widget

class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) 
        
        # --- SCROLL AREA SETUP ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(scroll_content)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(24)

        # --- HEADER ---
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        title = QLabel("Reports & Analytics")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        sub = QLabel("Track your performance, income, and booking trends.")
        sub.setStyleSheet("color: #64748b;")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        header_row.addLayout(v_title)
        
        header_row.addStretch()
        btn_date = QPushButton("📅 Custom Date Range")
        btn_date.setObjectName("secondaryButton")
        btn_filter = QPushButton("⚲ Filter by Payment/Package")
        btn_filter.setObjectName("secondaryButton")
        header_row.addWidget(btn_date)
        header_row.addWidget(btn_filter)
        self.main_layout.addLayout(header_row)

        # --- ROW 1: KPI CARDS ---
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(20)
        
        # 1. Total Bookings
        kpi1 = self.create_kpi_card("Total Bookings", "124", sub_html="<span style='color:#64748b; font-size:11px;'><b>8</b> Today &nbsp;&nbsp;|&nbsp;&nbsp; <b>32</b> Week &nbsp;&nbsp;|&nbsp;&nbsp; <b>124</b> Month</span>")
        # 2. Total Pax Booked
        kpi2 = self.create_kpi_card("Total Pax Booked", "3,450", "↗ +12% from last month", is_positive=True)
        # 3. Estimated Income
        kpi3 = self.create_kpi_card("Estimated Income", "₱ 415k", "↗ +8.5% from last month", is_positive=True)
        # 4. Weekly Target (Progress Bar)
        kpi4 = self.create_target_card()
        
        kpi_layout.addWidget(kpi1)
        kpi_layout.addWidget(kpi2)
        kpi_layout.addWidget(kpi3)
        kpi_layout.addWidget(kpi4)
        self.main_layout.addLayout(kpi_layout)

        # --- ROW 2: CHARTS ---
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)
        
        # Left: Line Chart (Spans wider)
        self.line_chart_card = self.create_line_chart_card()
        charts_layout.addWidget(self.line_chart_card, 2) 
        
        # Right: Bar Chart & Donut Chart
        right_charts_vbox = QVBoxLayout()
        right_charts_vbox.setSpacing(20)
        self.bar_chart_card = self.create_bar_chart_card()
        self.donut_chart_card = self.create_donut_chart_card()
        right_charts_vbox.addWidget(self.bar_chart_card)
        right_charts_vbox.addWidget(self.donut_chart_card)
        
        charts_layout.addLayout(right_charts_vbox, 1) 
        self.main_layout.addLayout(charts_layout)

        # --- ROW 3: RECENT STATISTICS TABLE ---
        table_card = QFrame()
        table_card.setObjectName("card")
        table_card.setGraphicsEffect(create_shadow())
        t_layout = QVBoxLayout(table_card)
        
        t_head = QHBoxLayout()
        t_title = QLabel("Recent Booking Statistics")
        t_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        view_all = QPushButton("View All")
        view_all.setStyleSheet("color: #e53935; font-weight: bold; border: none; background: transparent;")
        t_head.addWidget(t_title)
        t_head.addStretch()
        t_head.addWidget(view_all)
        t_layout.addLayout(t_head)

        self.table = QTableWidget(5, 5)
        self.table.setHorizontalHeaderLabels(["ID & DATE", "EVENT / CLIENT", "PACKAGE", "PAX", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.NoSelection)

        # Data Injection based on screenshot
        rows_data = [
            ("BKG-001\nOct 24, 2026", "TechCorp Inc.", "Premium Corporate", 45, "✓ Completed"),
            ("BKG-002\nOct 25, 2026", "Smith Wedding", "Grand Banquet", 58, "⏱ Pending"),
            ("BKG-003\nOct 26, 2026", "Sarah's 18th", "Standard Buffet", 60, "⏱ Pending"),
            ("BKG-004\nOct 28, 2026", "Local NGO Meet", "Basic Snack Box", 30, "✓ Completed"),
            ("BKG-005\nOct 29, 2026", "Alumni Reunion", "Premium Corporate", 55, "⏱ Pending"),
        ]

        for row, data in enumerate(rows_data):
            self.table.setRowHeight(row, 60)
            
            # ID
            id_lbl = QTableWidgetItem(data[0])
            self.table.setItem(row, 0, id_lbl)
            
            # Name
            name_lbl = QTableWidgetItem(data[1])
            font = name_lbl.font()
            font.setBold(True)
            name_lbl.setFont(font)
            self.table.setItem(row, 1, name_lbl)
            
            # Package
            self.table.setItem(row, 2, QTableWidgetItem(data[2]))
            
            # Pax (Custom Limit Badge)
            self.table.setCellWidget(row, 3, create_limit_badge(data[3]))
            
            # Status
            self.table.setCellWidget(row, 4, create_status_badge(data[4]))

        t_layout.addWidget(self.table)
        self.main_layout.addWidget(table_card)

        # Wrap it up
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

    # ==========================================
    # HELPER COMPONENT GENERATORS
    # ==========================================
    
    def create_kpi_card(self, title, value, subtext="", is_positive=True, sub_html=None):
        card = QFrame()
        card.setObjectName("card")
        card.setGraphicsEffect(create_shadow())
        lay = QVBoxLayout(card)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #64748b; font-weight: bold;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e293b; margin-top: 10px;")
        
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_val)
        
        if sub_html:
            sub = QLabel(sub_html)
            lay.addWidget(sub)
        elif subtext:
            sub = QLabel(subtext)
            color = "#16a34a" if is_positive else "#dc2626"
            sub.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
            lay.addWidget(sub)
            
        lay.addStretch()
        return card

    def create_target_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setGraphicsEffect(create_shadow())
        lay = QVBoxLayout(card)
        
        lay.addWidget(QLabel("<span style='color:#64748b; font-weight:bold;'>Weekly Target</span>"))
        
        val_row = QHBoxLayout()
        val_row.addWidget(QLabel("<span style='font-size:28px; font-weight:bold; color:#1e293b;'>₱ 85k</span>"))
        val_row.addStretch()
        val_row.addWidget(QLabel("<span style='color:#94a3b8; font-weight:bold;'>/ ₱ 100k</span>"))
        lay.addLayout(val_row)
        
        prog = QProgressBar()
        prog.setRange(0, 100)
        prog.setValue(85)
        prog.setFixedHeight(8)
        prog.setTextVisible(False)
        prog.setStyleSheet("QProgressBar {background: #f1f5f9; border-radius: 4px;} QProgressBar::chunk {background: #e53935; border-radius: 4px;}")
        lay.addWidget(prog)
        
        lay.addWidget(QLabel("<span style='color:#64748b; font-size:11px;'>85% of weekly goal achieved</span>"))
        return card

    # --- LINE CHART ---
    def create_line_chart_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setGraphicsEffect(create_shadow())
        lay = QVBoxLayout(card)
        lay.addWidget(QLabel("<span style='font-size:16px; font-weight:bold;'>Income Trends (Year-to-Date)</span>"))
        
        series = QLineSeries()
        data = [45, 52, 38, 65, 58, 75, 82] # in thousands
        for i, val in enumerate(data):
            series.append(i, val)
            
        pen = QPen(QColor("#e53935"))
        pen.setWidth(3)
        series.setPen(pen)
        
        # Enable Hover details
        series.hovered.connect(self.on_line_hover)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.setBackgroundBrush(Qt.transparent)

        # Axes
        axis_x = QBarCategoryAxis()
        axis_x.append(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"])
        axis_x.setLinePenColor(Qt.transparent)
        axis_x.setGridLineColor(Qt.transparent)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setRange(25, 100)
        axis_y.setLabelFormat("₱%ik")
        axis_y.setGridLineColor(QColor("#f1f5f9"))
        axis_y.setLinePenColor(Qt.transparent)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setStyleSheet("background: transparent;")
        chart_view.setMinimumHeight(350)
        lay.addWidget(chart_view)
        return card

    def on_line_hover(self, point, state):
        if state:
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
            idx = int(point.x())
            month = months[idx] if 0 <= idx < len(months) else ""
            val = int(point.y())
            QToolTip.showText(QCursor.pos(), f"{month} Income: ₱{val},000", self)
        else:
            QToolTip.hideText()

    # --- BAR CHART ---
    def create_bar_chart_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setGraphicsEffect(create_shadow())
        lay = QVBoxLayout(card)
        lay.addWidget(QLabel("<span style='font-weight:bold;'>Bookings This Month</span>"))
        
        set0 = QBarSet("Bookings")
        set0.append([12, 18, 15, 24])
        set0.setColor(QColor("#f87171")) 
        
        series = QBarSeries()
        series.append(set0)
        series.hovered.connect(self.on_bar_hover)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.setBackgroundBrush(Qt.transparent)

        axis_x = QBarCategoryAxis()
        axis_x.append(["Week 1", "Week 2", "Week 3", "Week 4"])
        axis_x.setLinePenColor(Qt.transparent)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setRange(0, 24)
        axis_y.setTickCount(5)
        axis_y.setGridLineColor(QColor("#f1f5f9"))
        axis_y.setLinePenColor(Qt.transparent)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setStyleSheet("background: transparent;")
        chart_view.setMinimumHeight(150)
        lay.addWidget(chart_view)
        return card

    def on_bar_hover(self, status, index, barset):
        if status:
            val = barset.at(index)
            week = f"Week {index + 1}"
            QToolTip.showText(QCursor.pos(), f"{week}: {val} Bookings", self)
        else:
            QToolTip.hideText()

    # --- DONUT CHART ---
    def create_donut_chart_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setGraphicsEffect(create_shadow())
        lay = QVBoxLayout(card)
        lay.addWidget(QLabel("<span style='font-weight:bold;'>Payment Methods</span>"))
        
        series = QPieSeries()
        series.setHoleSize(0.4) 
        
        slice1 = series.append("Cash", 45)
        slice1.setColor(QColor("#e53935"))
        slice2 = series.append("GCash", 30)
        slice2.setColor(QColor("#f87171"))
        slice3 = series.append("Bank Transfer", 15)
        slice3.setColor(QColor("#fca5a5"))
        slice4 = series.append("PayMaya", 10)
        slice4.setColor(QColor("#7f1d1d"))
        
        series.hovered.connect(self.on_pie_hover)

        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.setBackgroundBrush(Qt.transparent)
        
        chart.legend().setAlignment(Qt.AlignRight)
        chart.legend().setMarkerShape(QLegend.MarkerShape.MarkerShapeCircle)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setStyleSheet("background: transparent;")
        chart_view.setMinimumHeight(150)
        lay.addWidget(chart_view)
        return card

    def on_pie_hover(self, pie_slice, state):
        if state:
            pie_slice.setExploded(True)
            pie_slice.setExplodeDistanceFactor(0.05)
            val = pie_slice.value()
            label = pie_slice.label()
            QToolTip.showText(QCursor.pos(), f"{label}: {val}%", self)
        else:
            pie_slice.setExploded(False)
            QToolTip.hideText()