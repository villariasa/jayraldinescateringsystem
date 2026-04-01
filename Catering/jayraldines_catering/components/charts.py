# components/charts.py
from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QAreaSeries, 
                              QPieSeries, QBarCategoryAxis, QValueAxis, QLegend)
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor  # <--- THIS WAS MISSING
from PySide6.QtWidgets import QVBoxLayout, QLabel

class AreaChartCard(QVBoxLayout):
    """Line chart with a modern gradient fill underneath."""
    def __init__(self, title):
        super().__init__()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:#0F172A;'>{title}</span>"))
        
        # FIX: Use self. for ALL chart components to prevent C++ Segfaults
        self.upper_series = QLineSeries()
        data = [45, 52, 38, 65, 58, 75, 82]
        for i, val in enumerate(data):
            self.upper_series.append(i, val)
            
        pen = QPen(QColor("#E53935"))
        pen.setWidth(3)
        self.upper_series.setPen(pen)

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
    """Donut chart with a simulated center label."""
    def __init__(self, title):
        super().__init__()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:#0F172A;'>{title}</span>"))
        
        # FIX: Use self. to prevent garbage collection
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