from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QProgressBar, QScrollArea,
    QFileDialog, QMessageBox, QMenu, QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QAction
from datetime import datetime
import math

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, get_icon
from utils.theme import ThemeManager
from utils.accent import AccentManager
import utils.repository as repo
from utils import exporter as _exporter
from utils.data_loader import DataLoader


class AnimatedCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


class WelcomeHeroSlideshow(AnimatedCard):
    """Luxury glassmorphic greeting and introduction slideshow."""
    new_booking_requested = Signal()
    manage_bookings_requested = Signal()
    ai_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("heroSlideshowCard")
        self._curr_idx = 0
        self._slide_widgets = []
        self._build_ui()

        self._apply_theme_styles()
        ThemeManager().theme_changed.connect(self._apply_theme_styles)

        self._timer = QTimer(self)
        self._timer.setInterval(6500)
        self._timer.timeout.connect(self._next_slide)
        self._timer.start()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(20)

        # Left: Stack of 3 Slides
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")

        now = datetime.now()
        hour = now.hour
        if hour < 12:
            greet_title = "Good Morning, Team Jayraldine"
            flavor = "Operations and kitchen prep are online for today's catering schedule."
        elif hour < 18:
            greet_title = "Good Afternoon, Team Jayraldine"
            flavor = "Active reservations and order pipelines are synchronized."
        else:
            greet_title = "Good Evening, Team Jayraldine"
            flavor = "Dinner services, receipts, and revenue logs are secured."

        today_str = now.strftime("%A, %B %d, %Y")

        slide0 = self._make_slide(
            badge="EXECUTIVE BRIEFING • SYSTEM ONLINE",
            badge_color_dark="#38BDF8",
            badge_color_light="#0284C7",
            title=greet_title,
            desc=f"{flavor}\n{today_str}",
            btn_text="New Reservation",
            btn_cb=self.new_booking_requested.emit,
        )

        slide1 = self._make_slide(
            badge="RESERVATIONS & DISPATCH",
            badge_color_dark="#34D399",
            badge_color_light="#059669",
            title="Real-Time Bookings & Automated Email Dispatch",
            desc="Create reservations, send branded PDF receipts, and dispatch client approval requests directly via SMTP.",
            btn_text="Manage Orders",
            btn_cb=self.manage_bookings_requested.emit,
        )

        slide2 = self._make_slide(
            badge="CHEF JAY AI INTELLIGENCE",
            badge_color_dark="#FB7185",
            badge_color_light="#E11D48",
            title="Recipe Costing, Margin Analytics & Kitchen Optimization",
            desc="Chef Jay is ready to forecast ingredient requirements, analyze profit margins, and assist with menu packages.",
            btn_text="Open AI Assistant",
            btn_cb=self.ai_requested.emit,
        )

        self._stack.addWidget(slide0)
        self._stack.addWidget(slide1)
        self._stack.addWidget(slide2)
        lay.addWidget(self._stack, 1)

        # Right: Controls
        ctrl_col = QVBoxLayout()
        ctrl_col.setContentsMargins(0, 0, 0, 0)
        ctrl_col.setSpacing(8)
        ctrl_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)

        self._btn_prev = QPushButton()
        self._btn_prev.setFixedSize(28, 28)
        self._btn_prev.setCursor(Qt.PointingHandCursor)
        self._btn_prev.clicked.connect(self._prev_slide)

        self._btn_next = QPushButton()
        self._btn_next.setFixedSize(28, 28)
        self._btn_next.setCursor(Qt.PointingHandCursor)
        self._btn_next.clicked.connect(self._next_slide)

        nav_row.addWidget(self._btn_prev)
        nav_row.addWidget(self._btn_next)
        ctrl_col.addLayout(nav_row)

        self._dots = []
        dots_row = QHBoxLayout()
        dots_row.setSpacing(6)
        dots_row.setAlignment(Qt.AlignCenter)

        for i in range(3):
            dot = QPushButton()
            dot.setFixedSize(8, 8)
            dot.setCursor(Qt.PointingHandCursor)
            dot.clicked.connect(lambda _, idx=i: self._set_slide(idx))
            self._dots.append(dot)
            dots_row.addWidget(dot)

        ctrl_col.addLayout(dots_row)
        lay.addLayout(ctrl_col)

        self._update_dots()

    def _make_slide(self, badge, badge_color_dark, badge_color_light, title, desc, btn_text, btn_cb):
        w = QWidget()
        w.setObjectName("heroSlideItem")
        w.setStyleSheet("QWidget#heroSlideItem { background: transparent; border: none; }")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(5)

        tag = QLabel(badge)
        tag.setProperty("badge_color_dark", badge_color_dark)
        tag.setProperty("badge_color_light", badge_color_light)
        v.addWidget(tag, alignment=Qt.AlignLeft)

        t = QLabel(title)
        v.addWidget(t)

        d = QLabel(desc)
        d.setWordWrap(True)
        v.addWidget(d)

        btn = QPushButton(btn_text)
        btn.setFixedHeight(28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #FB7185);
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 800;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BE123C, stop:1 #F43F5E);
            }
        """)
        btn.clicked.connect(btn_cb)
        v.addWidget(btn, alignment=Qt.AlignLeft)

        self._slide_widgets.append((w, tag, t, d, btn))
        return w

    def _apply_theme_styles(self):
        try:
            dark = ThemeManager().is_dark()
            if dark:
                self.setStyleSheet("""
                    QFrame#heroSlideshowCard {
                        background: qlineargradient(
                            x1:0, y1:0, x2:1, y2:0,
                            stop:0 #0F172A,
                            stop:0.45 #1E1B4B,
                            stop:0.8 #0F172A,
                            stop:1 #111827
                        );
                        border: 1px solid rgba(244, 63, 94, 0.35);
                        border-radius: 18px;
                    }
                    QWidget#heroSlideItem { background: transparent; border: none; }
                """)
                self._btn_prev.setIcon(get_icon("chevron-left", color="#FFFFFF", size=QSize(13, 13)))
                self._btn_next.setIcon(get_icon("chevron-right", color="#FFFFFF", size=QSize(13, 13)))
                btn_css = """
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 14px;
                    }
                    QPushButton:hover { background: rgba(225, 29, 72, 0.4); border-color: #E11D48; }
                """
            else:
                self.setStyleSheet("""
                    QFrame#heroSlideshowCard {
                        background: qlineargradient(
                            x1:0, y1:0, x2:1, y2:0,
                            stop:0 #FFFFFF,
                            stop:0.45 #FFF1F2,
                            stop:0.85 #F8FAFC,
                            stop:1 #FFFFFF
                        );
                        border: 1px solid #FECDD3;
                        border-radius: 18px;
                    }
                    QWidget#heroSlideItem { background: transparent; border: none; }
                """)
                self._btn_prev.setIcon(get_icon("chevron-left", color="#334155", size=QSize(13, 13)))
                self._btn_next.setIcon(get_icon("chevron-right", color="#334155", size=QSize(13, 13)))
                btn_css = """
                    QPushButton {
                        background: rgba(0, 0, 0, 0.04);
                        border: 1px solid rgba(0, 0, 0, 0.08);
                        border-radius: 14px;
                    }
                    QPushButton:hover { background: rgba(225, 29, 72, 0.15); border-color: #E11D48; }
                """

            self._btn_prev.setStyleSheet(btn_css)
            self._btn_next.setStyleSheet(btn_css)

            for w, tag, t, d, btn in self._slide_widgets:
                badge_col = tag.property("badge_color_dark" if dark else "badge_color_light")
                tag_bg = "rgba(255, 255, 255, 0.05)" if dark else "rgba(225, 29, 72, 0.08)"
                tag_border = "rgba(255, 255, 255, 0.1)" if dark else "rgba(225, 29, 72, 0.2)"
                tag.setStyleSheet(f"""
                    color: {badge_col};
                    font-size: 10px;
                    font-weight: 800;
                    letter-spacing: 1.2px;
                    background: {tag_bg};
                    border: 1px solid {tag_border};
                    padding: 3px 8px;
                    border-radius: 6px;
                """)
                t.setStyleSheet(f"color: {'#FFFFFF' if dark else '#0F172A'}; font-size: 16px; font-weight: 800; letter-spacing: -0.3px; background: transparent;")
                d.setStyleSheet(f"color: {'#94A3B8' if dark else '#475569'}; font-size: 11.5px; font-weight: 500; line-height: 1.3; background: transparent;")

            self._update_dots()
        except Exception:
            pass

    def _set_slide(self, idx: int):
        self._curr_idx = idx % 3
        self._stack.setCurrentIndex(self._curr_idx)
        self._update_dots()

    def _next_slide(self):
        self._set_slide(self._curr_idx + 1)

    def _prev_slide(self):
        self._set_slide(self._curr_idx - 1)

    def _update_dots(self):
        dark = ThemeManager().is_dark()
        inactive_color = "rgba(255, 255, 255, 0.25)" if dark else "rgba(0, 0, 0, 0.18)"
        for i, dot in enumerate(self._dots):
            if i == self._curr_idx:
                dot.setStyleSheet("background-color: #E11D48; border-radius: 4px; border: none;")
                dot.setFixedSize(18, 6)
            else:
                dot.setStyleSheet(f"background-color: {inactive_color}; border-radius: 3px; border: none;")
                dot.setFixedSize(6, 6)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._timer.stop()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._timer.start()


class KPICard(AnimatedCard):
    def __init__(self, title, value, trend_text, trend_type="success", icon_name=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        lbl_title = QLabel(title.upper())
        lbl_title.setObjectName("kpiLabel")
        top_row.addWidget(lbl_title)
        top_row.addStretch()
        if icon_name:
            ico = QLabel()
            _ico_color = "#64748B" if not ThemeManager().is_dark() else "#374151"
            ico.setPixmap(get_icon(icon_name, color=_ico_color, size=QSize(18, 18)).pixmap(QSize(18, 18)))
            top_row.addWidget(ico)
        layout.addLayout(top_row)

        self._val_lbl = QLabel(value)
        self._val_lbl.setObjectName("kpiValue")
        layout.addWidget(self._val_lbl)

        self._trend_lbl = QLabel(trend_text)
        badge_map = {
            "success": "badgeSuccess",
            "danger":  "badgeDanger",
            "warning": "badgeWarning",
            "gold":    "badgeGold",
        }
        self._trend_lbl.setObjectName(badge_map.get(trend_type, "badgeInfo"))
        layout.addWidget(self._trend_lbl)
        layout.addStretch()

    def update_value(self, value: str):
        self._val_lbl.setText(value)

    def update_trend(self, text: str):
        self._trend_lbl.setText(text)


class PeriodSummaryCard(AnimatedCard):
    """Revenue vs Expenses bar chart with a Weekly / Monthly / Yearly toggle.

    Weekly  = weeks of the current month
    Monthly = months of the current year
    Yearly  = every year with data (needs analytics_functions_migration.sql)
    """

    _PERIODS = ["Weekly", "Monthly", "Yearly"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._period = "Monthly"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        head = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Revenue Summary")
        title.setObjectName("h3")
        self._range_lbl = QLabel("")
        self._range_lbl.setObjectName("subtitle")
        title_col.addWidget(title)
        title_col.addWidget(self._range_lbl)
        head.addLayout(title_col)
        head.addStretch()

        self._period_btns = {}
        for p in self._PERIODS:
            btn = QPushButton(p)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setObjectName("pageButtonActive" if p == self._period else "pageButton")
            btn.clicked.connect(lambda _, name=p: self.set_period(name))
            self._period_btns[p] = btn
            head.addWidget(btn)
        lay.addLayout(head)

        self._empty_lbl = QLabel("No data for this period yet.")
        self._empty_lbl.setObjectName("subtitle")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.hide()
        lay.addWidget(self._empty_lbl)

        self._chart_holder = QVBoxLayout()
        lay.addLayout(self._chart_holder, 1)
        self._chart_view = None

        self.refresh()

    def set_period(self, period: str):
        if period == self._period:
            return
        self._period = period
        for p, btn in self._period_btns.items():
            btn.setObjectName("pageButtonActive" if p == period else "pageButton")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.refresh()

    def _fetch(self):
        now = datetime.now()
        if self._period == "Weekly":
            rows = repo.get_weekly_summary(now.year, now.month)
            self._range_lbl.setText(now.strftime("Weeks of %B %Y"))
            return [(r["week"], r["revenue"], r["expense"]) for r in rows]
        if self._period == "Yearly":
            rows = repo.get_yearly_summary()
            self._range_lbl.setText("All years")
            return [(str(r["year"]), r["revenue"], r["expense"]) for r in rows]
        try:
            rows = repo.get_profit_summary_for_year(now.year)
        except Exception:
            rows = repo.get_profit_summary()
        self._range_lbl.setText(str(now.year))
        return [(r["month"], r["revenue"], r["expense"]) for r in rows]

    def refresh(self):
        self.render_chart()

    def render_chart(self, data=None):
        if data is None:
            try:
                data = self._fetch()
            except Exception:
                data = []

        if self._chart_view is not None:
            self._chart_holder.removeWidget(self._chart_view)
            self._chart_view.deleteLater()
            self._chart_view = None

        if not data:
            self._empty_lbl.show()
            return
        self._empty_lbl.hide()

        from PySide6.QtCharts import (
            QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
        )
        from PySide6.QtGui import QPainter, QColor
        from PySide6.QtCore import QMargins

        dark = ThemeManager().is_dark()
        label_color = QColor("#9CA3AF" if dark else "#5B6B84")
        grid_color = QColor("#243244" if dark else "#EDF1F7")

        rev_set = QBarSet("Revenue")
        exp_set = QBarSet("Expenses")
        rev_color = AccentManager().current
        exp_color = "#F59E0B" if dark else "#F4A93C"
        rev_set.setColor(QColor(rev_color))
        exp_set.setColor(QColor(exp_color))
        labels = []
        rev_values = []
        exp_values = []
        max_val = 0.0
        for label, revenue, expense in data:
            labels.append(label)
            rev_values.append(revenue)
            exp_values.append(expense)
            rev_set.append(revenue)
            exp_set.append(expense)
            max_val = max(max_val, revenue, expense)

        def _make_hover_rev(cat_labels=labels, rev_list=rev_values, col=rev_color):
            def _on_hover(status: bool, index: int):
                if status and 0 <= index < len(cat_labels):
                    cat_name = cat_labels[index]
                    val = rev_list[index]
                    from PySide6.QtGui import QCursor
                    from PySide6.QtWidgets import QToolTip
                    QToolTip.showText(
                        QCursor.pos(),
                        f"<b style='color:{col};'>{cat_name} — Revenue</b><br>"
                        f"Amount: <b>₱ {val:,.2f}</b>"
                    )
                else:
                    from PySide6.QtWidgets import QToolTip
                    QToolTip.hideText()
            return _on_hover

        def _make_hover_exp(cat_labels=labels, exp_list=exp_values, col=exp_color):
            def _on_hover(status: bool, index: int):
                if status and 0 <= index < len(cat_labels):
                    cat_name = cat_labels[index]
                    val = exp_list[index]
                    from PySide6.QtGui import QCursor
                    from PySide6.QtWidgets import QToolTip
                    QToolTip.showText(
                        QCursor.pos(),
                        f"<b style='color:{col};'>{cat_name} — Expenses</b><br>"
                        f"Amount: <b>₱ {val:,.2f}</b>"
                    )
                else:
                    from PySide6.QtWidgets import QToolTip
                    QToolTip.hideText()
            return _on_hover

        rev_set.hovered.connect(_make_hover_rev())
        exp_set.hovered.connect(_make_hover_exp())

        series = QBarSeries()
        series.append(rev_set)
        series.append(exp_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundBrush(Qt.transparent)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.legend().setLabelColor(label_color)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        axis_x.setLabelsColor(label_color)
        axis_x.setGridLineVisible(False)
        axis_x.setLinePenColor(Qt.transparent)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        upper = max(max_val * 1.15, 1.0)
        target_ticks = 5
        raw_step = upper / (target_ticks - 1)
        magnitude = 10 ** int(math.floor(math.log10(max(raw_step, 1))))
        residual = raw_step / magnitude
        if residual <= 1.5:
            clean_step = 1.0 * magnitude
        elif residual <= 3.0:
            clean_step = 2.5 * magnitude
        elif residual <= 7.0:
            clean_step = 5.0 * magnitude
        else:
            clean_step = 10.0 * magnitude

        num_steps = max(1, int(math.ceil(upper / clean_step)))
        final_max = num_steps * clean_step

        from PySide6.QtCharts import QCategoryAxis
        axis_y = QCategoryAxis()
        axis_y.setRange(0, final_max)

        for i in range(num_steps + 1):
            val = clean_step * i
            lbl = f"₱{val:,.0f}"
            axis_y.append(lbl, val)

        axis_y.setLabelsColor(label_color)
        axis_y.setGridLineColor(grid_color)
        axis_y.setLinePenColor(Qt.transparent)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        self._chart_view = QChartView(chart)
        self._chart_view.setRenderHint(QPainter.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent;")
        self._chart_view.setMinimumHeight(260)
        self._chart_holder.addWidget(self._chart_view)


class ActivityItem(QWidget):
    def __init__(self, title, desc, time, dot_color="#22C55E", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(14)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 4px;")
        layout.addWidget(dot, alignment=Qt.AlignTop | Qt.AlignHCenter)
        layout.setAlignment(dot, Qt.AlignVCenter)

        vbox = QVBoxLayout()
        vbox.setSpacing(3)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("font-size: 12px;")
        d_lbl.setWordWrap(True)
        vbox.addWidget(t_lbl)
        vbox.addWidget(d_lbl)
        layout.addLayout(vbox)
        layout.addStretch()

        time_lbl = QLabel(time)
        # FIX 1: Added closing parenthesis
        time_lbl.setStyleSheet("font-size: 11px; white-space: nowrap;")
        layout.addWidget(time_lbl, alignment=Qt.AlignTop)


class EventItem(QWidget):
    def __init__(self, name, date_str, pax, status, status_type="success", event_dt=None, db_id=None, on_completed=None, parent=None):
        super().__init__(parent)
        self._db_id = db_id
        self._on_completed = on_completed
        self._completed_btn = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)
        self._main_lay = layout

        left = QVBoxLayout()
        left.setSpacing(3)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        date_lbl = QLabel(f"{date_str}  ·  {pax} pax")
        date_lbl.setStyleSheet("font-size: 12px;")
        left.addWidget(name_lbl)
        left.addWidget(date_lbl)

        layout.addLayout(left)
        layout.addStretch()

        badge = QLabel(status)
        badge_map = {"success": "badgeSuccess", "warning": "badgeWarning", "danger": "badgeDanger"}
        badge.setObjectName(badge_map.get(status_type, "badgeInfo"))
        layout.addWidget(badge)

        self._event_dt = event_dt
        self._countdown_lbl = None
        if event_dt is not None:
            self._countdown_lbl = QLabel()
            self._countdown_lbl.setStyleSheet("color: #D97706; font-size: 11px; font-weight: 700;")
            left.addWidget(self._countdown_lbl)
            self._tick_countdown()
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick_countdown)
            self._timer.start(1000)

    def _show_complete_button(self):
        if self._completed_btn is not None:
            return
        self._completed_btn = QPushButton("Mark as Completed")
        self._completed_btn.setCursor(Qt.PointingHandCursor)
        self._completed_btn.setStyleSheet(
            "QPushButton { background: #16A34A; color: #fff; border-radius: 6px; "
            "padding: 4px 10px; font-size: 11px; font-weight: 600; } "
            "QPushButton:hover { background: #15803D; }"
        )
        self._completed_btn.clicked.connect(self._handle_complete)
        self._main_lay.addWidget(self._completed_btn)

    def _handle_complete(self):
        if self._db_id is None:
            return
        reply = QMessageBox.question(
            self, "Mark as Completed",
            "Mark this event as Completed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok = repo.complete_booking(self._db_id)
            if ok:
                if self._on_completed:
                    self._on_completed()
            else:
                QMessageBox.warning(self, "Error", "Could not mark booking as completed.")

    def _tick_countdown(self):
        delta = self._event_dt - datetime.now()
        total = int(delta.total_seconds())
        if total <= 0:
            self._countdown_lbl.setText("Event started")
            if hasattr(self, "_timer"):
                self._timer.stop()
            if self._db_id is not None:
                self._show_complete_button()
            return
        days, rem = divmod(total, 86400)
        h, rem2 = divmod(rem, 3600)
        m, s = divmod(rem2, 60)
        if days > 0:
            self._countdown_lbl.setText(f"Starts in {days}d {h:02d}:{m:02d}:{s:02d}")
        else:
            self._countdown_lbl.setText(f"Starts in {h:02d}:{m:02d}:{s:02d}")



class DashboardPage(QWidget):
    new_booking_requested = Signal()
    view_all_activity_requested = Signal()
    ai_requested = Signal()

    def __init__(self):
        super().__init__()

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget(self.scroll)
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lay = QVBoxLayout(self.content)
        self.lay.setContentsMargins(32, 28, 32, 28)
        self.lay.setSpacing(24)

        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        title = QLabel("Welcome back, Owner")
        title.setObjectName("h1")
        sub = QLabel("Here's what's happening at Jayraldine's Catering today.")
        sub.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        header_row.addLayout(v_title)
        header_row.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_export = QPushButton("  Export Report")
        btn_export.setObjectName("secondaryButton")
        btn_export.setIcon(btn_icon_secondary("export"))
        btn_export.setIconSize(QSize(15, 15))
        btn_export.setMenu(self._build_export_menu())

        self.btn_new = QPushButton("  New Booking")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.setIcon(btn_icon_primary("plus"))
        self.btn_new.setIconSize(QSize(15, 15))
        self.btn_new.clicked.connect(self.new_booking_requested.emit)

        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(self.btn_new)
        header_row.addLayout(btn_layout)
        self.lay.addLayout(header_row)

        self.slideshow = WelcomeHeroSlideshow(self.content)
        self.slideshow.new_booking_requested.connect(self.new_booking_requested.emit)
        self.slideshow.manage_bookings_requested.connect(self.new_booking_requested.emit)
        self.slideshow.ai_requested.connect(self.ai_requested.emit)
        self.lay.addWidget(self.slideshow)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self._kpi_today    = KPICard("Today's Events",   "—", "Loading...",  "success", "calendar")
        self._kpi_pending  = KPICard("Pending Bookings", "—", "Loading...",  "warning", "orders")
        self._kpi_revenue  = KPICard("Weekly Revenue",   "—", "Loading...",  "success", "trending-up")
        self._kpi_unpaid   = KPICard("Unpaid Invoices",  "—", "Loading...",  "danger",  "billing")
        self._kpi_profit   = KPICard("Net Profit (YTD)", "—", "Loading...",  "success", "trending-up")
        for card in [self._kpi_today, self._kpi_pending, self._kpi_revenue, self._kpi_unpaid, self._kpi_profit]:
            kpi_row.addWidget(card)
        self.lay.addLayout(kpi_row)

        self.summary_card = PeriodSummaryCard(self.content)
        self.lay.addWidget(self.summary_card)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        self.cap_card = AnimatedCard(self.content)
        cap_lay = QVBoxLayout(self.cap_card)
        cap_lay.setContentsMargins(24, 24, 24, 24)
        cap_lay.setSpacing(14)

        cap_head = QHBoxLayout()
        cap_v = QVBoxLayout()
        cap_v.setSpacing(2)
        cap_title = QLabel("Daily Capacity")
        cap_title.setObjectName("h3")
        cap_sub = QLabel("Pax booked today")
        cap_sub.setObjectName("subtitle")
        cap_v.addWidget(cap_title)
        cap_v.addWidget(cap_sub)
        cap_head.addLayout(cap_v)
        cap_head.addStretch()
        self._pax_lbl = QLabel('—')
        # FIX 4: Added closing parenthesis
        self._pax_lbl.setStyleSheet("font-size:28px;font-weight:800;")
        cap_head.addWidget(self._pax_lbl)
        cap_lay.addLayout(cap_head)

        self.prog = QProgressBar()
        self.prog.setRange(0, 600)
        self.prog.setValue(0)
        self.prog.setFixedHeight(10)
        cap_lay.addWidget(self.prog)

        self._cap_pct_lbl = QLabel("")
        self._cap_pct_lbl.setStyleSheet("color:#D97706;font-weight:700;font-size:12px;")
        self._cap_rem_lbl = QLabel("")
        # FIX 5: Added closing parenthesis
        self._cap_rem_lbl.setStyleSheet("font-size:12px;")
        cap_foot = QHBoxLayout()
        cap_foot.addWidget(self._cap_pct_lbl)
        cap_foot.addStretch()
        cap_foot.addWidget(self._cap_rem_lbl)
        cap_lay.addLayout(cap_foot)

        self.events_card = AnimatedCard(self.content)
        self._ev_lay = QVBoxLayout(self.events_card)
        self._ev_lay.setContentsMargins(24, 24, 24, 24)
        self._ev_lay.setSpacing(0)

        ev_head = QHBoxLayout()
        ev_title = QLabel("Upcoming Events")
        ev_title.setObjectName("h3")
        ev_head.addWidget(ev_title)
        ev_head.addStretch()
        self._ev_lay.addLayout(ev_head)

        ev_div = QFrame()
        ev_div.setObjectName("divider")
        self._ev_lay.addWidget(ev_div)
        self._ev_lay.addSpacing(4)

        self._ev_items_start = self._ev_lay.count()

        mid_row.addWidget(self.cap_card, 1)
        mid_row.addWidget(self.events_card, 1)
        self.lay.addLayout(mid_row)

        bot_row = QHBoxLayout()
        bot_row.setSpacing(16)

        self.act_card = AnimatedCard(self.content)
        self._act_lay = QVBoxLayout(self.act_card)
        self._act_lay.setContentsMargins(24, 24, 24, 24)
        self._act_lay.setSpacing(0)

        act_head = QHBoxLayout()
        act_title = QLabel("Recent Activity")
        act_title.setObjectName("h3")
        act_head.addWidget(act_title)
        act_head.addStretch()
        btn_view = QPushButton("View all")
        btn_view.setObjectName("ghostButton")
        btn_view.setIcon(btn_icon_muted("eye"))
        btn_view.setIconSize(QSize(13, 13))
        btn_view.clicked.connect(self.view_all_activity_requested.emit)
        act_head.addWidget(btn_view)
        self._act_lay.addLayout(act_head)

        act_div = QFrame()
        act_div.setObjectName("divider")
        self._act_lay.addWidget(act_div)

        self._act_items_start = self._act_lay.count()

        self.followup_card = AnimatedCard(self.content)
        self._followup_lay = QVBoxLayout(self.followup_card)
        self._followup_lay.setContentsMargins(24, 24, 24, 24)
        self._followup_lay.setSpacing(0)

        fu_head = QHBoxLayout()
        fu_title = QLabel("Follow-ups Due Today")
        fu_title.setObjectName("h3")
        fu_head.addWidget(fu_title)
        fu_head.addStretch()
        self._fu_badge = QLabel("—")
        self._fu_badge.setObjectName("badgeWarning")
        fu_head.addWidget(self._fu_badge)
        self._followup_lay.addLayout(fu_head)

        fu_div = QFrame()
        fu_div.setObjectName("divider")
        self._followup_lay.addWidget(fu_div)

        self._fu_items_start = self._followup_lay.count()

        bot_row.addWidget(self.act_card, 3)
        bot_row.addWidget(self.followup_card, 2)
        self.lay.addLayout(bot_row)

        self.scroll.setWidget(self.content)
        self.root_layout.addWidget(self.scroll)

        QTimer.singleShot(0, self._load_data)

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
        menu.addAction(pdf_act)
        menu.addAction(xlsx_act)
        return menu

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "jayraldines_dashboard.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return
        kpis = repo.get_report_kpis()
        bookings = repo.get_all_bookings() or []
        sections = _exporter.build_analytics_sections()
        chart_images = []
        try:
            import tempfile, os as _os
            from PySide6.QtGui import QPixmap
            sz = self.summary_card.size()
            w = max(10, sz.width())
            h = max(10, sz.height())
            pixmap = QPixmap(w * 2, h * 2)
            pixmap.setDevicePixelRatio(2.0)
            self.summary_card.render(pixmap)
            if pixmap.isNull():
                pixmap = self.summary_card.grab()

            png = _os.path.join(tempfile.mkdtemp(prefix="jc_dash_"), "summary.png")
            if pixmap.save(png, "PNG"):
                chart_images.append(("Revenue Summary", png))
        except Exception as exc:
            print(f"[dashboard] chart capture fallback: {exc}")
            try:
                pixmap = self.summary_card.grab()
                if not pixmap.isNull():
                    png = _os.path.join(tempfile.mkdtemp(prefix="jc_dash_"), "summary.png")
                    if pixmap.save(png, "PNG"):
                        chart_images.append(("Revenue Summary", png))
            except Exception:
                pass
        ok = _exporter.export_pdf(path, kpis, bookings, "Dashboard Report", "All Time",
                                  sections=sections, chart_images=chart_images)
        if ok:
            QMessageBox.information(self, "Export", f"PDF exported to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed",
                "PDF export failed. Make sure reportlab is installed:\npip install reportlab")

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "jayraldines_dashboard.xlsx", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        kpis = repo.get_report_kpis()
        bookings = repo.get_all_bookings() or []
        sections = _exporter.build_analytics_sections()
        ok = _exporter.export_excel(path, kpis, bookings, "Dashboard Report", "All Time",
                                    sections=sections)
        if ok:
            QMessageBox.information(self, "Export", f"Excel exported to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed",
                "Excel export failed. Make sure openpyxl is installed:\npip install openpyxl")

    def reload(self):
        self._load_data()

    def _fetch_dashboard_data(self):
        """Runs in background thread — fetches all dashboard data in one shot."""
        try:
            now = datetime.now()
            rows = repo.get_monthly_revenue_chart_data(now.year)
            chart_data = [(r["month"], r["revenue"], r["expense"]) for r in rows] if rows else []
        except Exception:
            chart_data = []

        return {
            "kpis":       repo.get_dashboard_kpis(),
            "profit":     repo.get_profit_summary(),
            "events":     repo.get_upcoming_events(limit=20),
            "activity":   repo.get_recent_activity(limit=10),
            "chart_data": chart_data,
            "followups":  repo.get_todays_follow_ups(),
        }

    def _load_data(self):
        prev = getattr(self, "_dash_loader", None)
        if prev is not None and prev.isRunning():
            return  # already loading
        loader = DataLoader(self._fetch_dashboard_data)
        loader.data_ready.connect(self._on_dash_data_ready)
        loader.load_error.connect(
            lambda msg: print(f"[Dashboard] Load error: {msg}")
        )
        self._dash_loader = loader
        loader.start()

    def _on_dash_data_ready(self, data):
        try:
            from shiboken6 import isValid
            if not isValid(self):
                return
        except Exception:
            pass
        kpis        = data.get("kpis", {})
        profit_data = data.get("profit", [])
        events      = data.get("events", [])
        activity    = data.get("activity", [])
        chart_data  = data.get("chart_data", [])
        followups   = data.get("followups", [])

        todays  = kpis.get("todays_events", 0)
        pending = kpis.get("pending_bookings", 0)
        revenue = kpis.get("weekly_revenue", 0.0)
        unpaid  = kpis.get("unpaid_invoices", 0.0)
        pax     = kpis.get("todays_pax", 0)

        self._kpi_today.update_value(str(todays))
        self._kpi_today.update_trend(f"{todays} event{'s' if todays != 1 else ''} today")
        self._kpi_pending.update_value(str(pending))
        self._kpi_pending.update_trend("Requires review" if pending > 0 else "All clear")
        self._kpi_revenue.update_value(f"₱ {revenue:,.0f}")
        self._kpi_revenue.update_trend("This week's revenue")
        self._kpi_unpaid.update_value(f"₱ {unpaid:,.0f}")
        self._kpi_unpaid.update_trend("Outstanding balance")

        try:
            total_rev = sum(r["revenue"] for r in profit_data)
            total_exp = sum(r["expense"] for r in profit_data)
            net = total_rev - total_exp
            self._kpi_profit.update_value(f"₱ {net:,.0f}")
            self._kpi_profit.update_trend(f"Rev ₱{total_rev:,.0f} − Exp ₱{total_exp:,.0f}")
        except Exception:
            self._kpi_profit.update_value("—")
            self._kpi_profit.update_trend("No expense data")

        _pax_color = "#F9FAFB" if ThemeManager().is_dark() else "#101828"
        self._pax_lbl.setText(
            f'<span style="font-size:28px;font-weight:800;color:{_pax_color};">{pax}</span>'
            f'<span style="color:#7A879E;font-size:16px;"> / 600</span>'
        )
        self.prog.setValue(min(pax, 600))
        pct = round((pax / 600) * 100, 1)
        self._cap_pct_lbl.setText(f"{pct}% Capacity")
        self._cap_rem_lbl.setText(f"{max(0, 600 - pax)} slots remaining")

        self.summary_card.render_chart(chart_data)

        self._cached_events   = events
        self._cached_activity = activity
        self._rebuild_events()
        self._rebuild_activity()
        self._rebuild_followup_alerts(followups)

    def _clear_layout_from(self, layout, from_index: int):
        while layout.count() > from_index:
            item = layout.takeAt(from_index)
            if item.widget():
                item.widget().deleteLater()

    def filter_search(self, text: str):
        q = text.strip().lower()
        events = getattr(self, "_cached_events", []) or []
        activity = getattr(self, "_cached_activity", []) or []
        if q:
            events   = [e for e in events   if q in (e.get("customer_name") or "").lower()
                                               or q in str(e.get("event_date") or "").lower()
                                               or q in (e.get("status") or "").lower()]
            activity = [a for a in activity  if q in (a.get("title") or "").lower()
                                               or q in (a.get("description") or "").lower()]
        self._rebuild_events(events)
        self._rebuild_activity(activity)

    def _rebuild_events(self, events=None):
        self._clear_layout_from(self._ev_lay, self._ev_items_start)
        if events is None:
            events = getattr(self, "_cached_events", None)
        if events is None:
            events = repo.get_upcoming_events(limit=20)
        if not events:
            empty = QLabel("No upcoming events.")
            empty.setObjectName("subtitle")
            empty.setContentsMargins(0, 8, 0, 8)
            self._ev_lay.addWidget(empty)
        else:
            for ev in events:
                raw_date = ev.get("event_date")
                raw_time = ev.get("event_time")
                if raw_date:
                    try:
                        from datetime import date as date_type, time as time_type
                        if isinstance(raw_date, date_type):
                            if isinstance(raw_time, time_type):
                                event_dt = datetime.combine(raw_date, raw_time)
                            else:
                                event_dt = datetime(raw_date.year, raw_date.month, raw_date.day, 18, 0)
                            date_str = raw_date.strftime("%b %d, %Y")
                        else:
                            event_dt = None
                            date_str = str(raw_date)
                    except Exception:
                        event_dt = None
                        date_str = str(raw_date)
                else:
                    event_dt = None
                    date_str = "—"

                status_raw = ev.get("status", "PENDING")
                stype_map = {"CONFIRMED": "success", "PENDING": "warning", "CANCELLED": "danger"}
                stype = stype_map.get(status_raw.upper(), "warning")

                self._ev_lay.addWidget(EventItem(
                    ev.get("customer_name", ""),
                    date_str,
                    str(ev.get("pax", 0)),
                    status_raw.capitalize(),
                    stype,
                    event_dt=event_dt,
                    db_id=ev.get("id"),
                    on_completed=self._rebuild_events,
                ))
                sep = QFrame()
                sep.setObjectName("divider")
                self._ev_lay.addWidget(sep)
        self._ev_lay.addStretch()

    def _rebuild_activity(self, activities=None):
        self._clear_layout_from(self._act_lay, self._act_items_start)
        if activities is None:
            activities = getattr(self, "_cached_activity", None)
        if activities is None:
            activities = repo.get_recent_activity(limit=10)
        if not activities:
            empty = QLabel("No recent activity.")
            empty.setObjectName("subtitle")
            empty.setContentsMargins(0, 8, 0, 8)
            self._act_lay.addWidget(empty)
        else:
            for act in activities:
                self._act_lay.addWidget(ActivityItem(
                    act["title"],
                    act["description"],
                    act["time"],
                    act.get("color", "#9CA3AF"),
                ))
        self._act_lay.addStretch()

    def _rebuild_followup_alerts(self, followups=None):
        self._clear_layout_from(self._followup_lay, self._fu_items_start)
        if followups is None:
            try:
                followups = repo.get_todays_follow_ups()
            except Exception:
                followups = []
        if not followups:
            self._fu_badge.setText("None due")
            self._fu_badge.setObjectName("badgeSuccess")
            empty = QLabel("No follow-ups due today.")
            empty.setObjectName("subtitle")
            empty.setContentsMargins(0, 8, 0, 8)
            self._followup_lay.addWidget(empty)
        else:
            self._fu_badge.setText(f"{len(followups)} Due")
            self._fu_badge.setObjectName("badgeDanger")
            for fu in followups:
                item_w = QWidget()
                item_lay = QHBoxLayout(item_w)
                item_lay.setContentsMargins(0, 8, 0, 8)
                item_lay.setSpacing(10)
                dot = QFrame()
                dot.setFixedSize(8, 8)
                dot.setStyleSheet("background:#F59E0B;border-radius:4px;")
                item_lay.addWidget(dot, alignment=Qt.AlignVCenter)
                text_lay = QVBoxLayout()
                text_lay.setSpacing(2)
                name_lbl = QLabel(fu.get("customer_name", "Customer"))
                name_lbl.setStyleSheet("font-weight:700;font-size:13px;")
                note_lbl = QLabel(fu.get("note") or "Follow-up due")
                note_lbl.setStyleSheet("color:#9CA3AF;font-size:12px;")
                note_lbl.setWordWrap(True)
                text_lay.addWidget(name_lbl)
                text_lay.addWidget(note_lbl)
                item_lay.addLayout(text_lay)
                self._followup_lay.addWidget(item_w)
                sep = QFrame()
                sep.setObjectName("divider")
                self._followup_lay.addWidget(sep)
        self._followup_lay.addStretch()