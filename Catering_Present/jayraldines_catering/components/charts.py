# components/charts.py
"""PySide6 QtCharts wrappers: a gradient area/line chart and a donut chart.

Both are ``QVBoxLayout`` subclasses that build a titled chart ready to drop into
a parent layout. Chart objects are stored on ``self`` deliberately to keep Python
references alive and avoid C++-side garbage-collection segfaults.
"""

from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QAreaSeries,
                              QPieSeries, QBarCategoryAxis, QValueAxis, QLegend)
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor  # <--- THIS WAS MISSING
from PySide6.QtWidgets import QVBoxLayout, QLabel

from utils.theme import ThemeManager


def _chart_colors():
    """Return title/label/grid colours for the current theme."""
    if ThemeManager().is_dark():
        return {"title": "#F9FAFB", "labels": QColor("#9CA3AF"), "grid": QColor("#243244")}
    return {"title": "#101828", "labels": QColor("#5B6B84"), "grid": QColor("#EDF1F7")}


class AreaChartCard(QVBoxLayout):
    """Line chart with a modern gradient fill underneath."""
    def __init__(self, title):
        """Build the titled area chart, axes and view from sample data."""
        super().__init__()
        colors = _chart_colors()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:{colors['title']};'>{title}</span>"))

        # FIX: Use self. for ALL chart components to prevent C++ Segfaults
        # (a plain local would be GC'd while Qt still references it -> crash).
        self.upper_series = QLineSeries()
        data = [45, 52, 38, 65, 58, 75, 82]
        for i, val in enumerate(data):
            self.upper_series.append(i, val)

        pen = QPen(QColor("#E53935"))
        pen.setWidth(3)
        self.upper_series.setPen(pen)

        # Flat zero baseline; the area is the band between upper_series and this.
        self.lower_series = QLineSeries()
        for i in range(len(data)):
            self.lower_series.append(i, 0)

        # Gradient fill fades from semi-opaque red at top to transparent at bottom.
        self.area = QAreaSeries(self.upper_series, self.lower_series)
        self.gradient = QLinearGradient(0, 0, 0, 300)
        self.gradient.setColorAt(0.0, QColor(229, 57, 53, 100))
        self.gradient.setColorAt(1.0, QColor(229, 57, 53, 0))
        self.area.setBrush(self.gradient)
        self.area.setPen(Qt.NoPen)

        self.chart = QChart()
        # Add the area first so the solid line renders on top of the fill.
        self.chart.addSeries(self.area)
        self.chart.addSeries(self.upper_series)
        self.chart.legend().hide()
        self.chart.setAnimationOptions(QChart.SeriesAnimations) 
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        self.chart.setBackgroundBrush(Qt.transparent)

        # Category X axis with transparent axis/grid lines for a clean look.
        self.axis_x = QBarCategoryAxis()
        self.axis_x.append(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"])
        self.axis_x.setLinePenColor(Qt.transparent)
        self.axis_x.setGridLineColor(Qt.transparent)
        self.axis_x.setLabelsColor(colors["labels"])
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.area.attachAxis(self.axis_x)
        self.upper_series.attachAxis(self.axis_x)

        # Value Y axis 0-100; only horizontal grid lines are kept visible.
        self.axis_y = QValueAxis()
        self.axis_y.setRange(0, 100)
        self.axis_y.setLabelFormat("P%ik")
        self.axis_y.setGridLineColor(colors["grid"])
        self.axis_y.setLinePenColor(Qt.transparent)
        self.axis_y.setLabelsColor(colors["labels"])
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
        """Build the titled donut chart with coloured payment-method slices."""
        super().__init__()
        colors = _chart_colors()
        self.addWidget(QLabel(f"<span style='font-size:16px; font-weight:700; color:{colors['title']};'>{title}</span>"))

        # FIX: Use self. to prevent garbage collection
        self.series = QPieSeries()
        # Hole size > 0 turns the pie into a donut (0.55 = 55% inner radius).
        self.series.setHoleSize(0.55)

        # append() returns the slice, so colour each one inline.
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
        self.chart.legend().setLabelColor(colors["labels"])
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        self.chart_view.setMinimumHeight(200)
        self.addWidget(self.chart_view)

    def _on_hover(self, slice, state):
        """Pop a slice outward while hovered (state True) and back when it leaves."""
        slice.setExploded(state)
        slice.setExplodeDistanceFactor(0.08)