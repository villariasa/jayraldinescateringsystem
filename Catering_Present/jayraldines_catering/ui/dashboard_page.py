"""Main dashboard page for the Jayraldine's Catering desktop app.

Assembles the landing screen: a rotating welcome hero slideshow
(:class:`WelcomeHeroSlideshow`), a date-filter toolbar, a row of KPI tiles
(:class:`KPICard`), a revenue-vs-expenses chart with period toggle
(:class:`PeriodSummaryCard`), a daily-capacity gauge, and Upcoming Events /
Recent Activity / Follow-ups panels (:class:`EventItem`, :class:`ActivityItem`).
:class:`DashboardPage` ties these together, drives permission-gated visibility,
and loads all metrics from ``utils.repository`` off the UI thread via
``utils.data_loader.DataLoader`` (with ``utils.data_cache`` caching for the
default "all time" view). It listens to app-wide data-change signals to keep
itself fresh, and supports exporting the dashboard to PDF/Excel.
"""

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
from components.dialogs import prompt_file_saved
from utils.data_loader import DataLoader


class AnimatedCard(QFrame):
    """Base card frame styled via the ``#card`` object name in the app QSS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


class WelcomeHeroSlideshow(AnimatedCard):
    """Luxury glassmorphic greeting and introduction slideshow.

    A three-slide auto-rotating hero banner (greeting, bookings, AI assistant)
    with prev/next controls and dot indicators. Slides carry call-to-action
    buttons that re-emit as :attr:`new_booking_requested`,
    :attr:`manage_bookings_requested`, and :attr:`ai_requested` for the parent
    page to handle. Auto-advance pauses on hover and buttons are shown/enabled
    per the current user's permissions.
    """

    # CTA signals re-emitted to DashboardPage for navigation.
    new_booking_requested = Signal()
    manage_bookings_requested = Signal()
    ai_requested = Signal()

    def __init__(self, parent=None):
        """Build the slides, apply theming, and start the auto-advance timer."""
        super().__init__(parent)
        self.setObjectName("heroSlideshowCard")
        self._curr_idx = 0          # index of the currently visible slide
        self._slide_widgets = []    # (widget, tag, title, desc, btn) per slide
        self._build_ui()

        self._apply_theme_styles()
        # Re-style on light/dark theme switches.
        ThemeManager().theme_changed.connect(self._apply_theme_styles)

        # Auto-advance every 6.5s (paused while hovered, see enter/leaveEvent).
        self._timer = QTimer(self)
        self._timer.setInterval(6500)
        self._timer.timeout.connect(self._next_slide)
        self._timer.start()

        self.update_greeting_and_permissions()

    def _build_ui(self):
        """Lay out the slide stack (3 slides) plus the nav buttons and dots."""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(20)

        # Left: Stack of 3 Slides
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")

        # Pick a time-of-day greeting/flavour text for the first slide.
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
            # Bind index via default arg so each dot jumps to its own slide.
            dot.clicked.connect(lambda _, idx=i: self._set_slide(idx))
            self._dots.append(dot)
            dots_row.addWidget(dot)

        ctrl_col.addLayout(dots_row)
        lay.addLayout(ctrl_col)

        self._update_dots()

    def _make_slide(self, badge, badge_color_dark, badge_color_light, title, desc, btn_text, btn_cb):
        """Build one hero slide widget and register its parts for later theming.

        :param badge: Small eyebrow/tag text above the title.
        :param badge_color_dark: Badge text colour used in dark theme.
        :param badge_color_light: Badge text colour used in light theme.
        :param title: Slide headline.
        :param desc: Supporting description (word-wrapped).
        :param btn_text: Call-to-action button label.
        :param btn_cb: Callback fired when the CTA button is clicked.
        :returns: The assembled slide ``QWidget`` (also appended to
            ``self._slide_widgets`` as a ``(w, tag, title, desc, btn)`` tuple).
        """
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
        """Re-apply card, nav-button, and per-slide styling for the active theme.

        Reads the current light/dark mode and restyles the hero card gradient,
        chevron icons, badge/title/description colours, and dot indicators.
        Wrapped in a broad try/except so a styling hiccup never breaks the page.
        """
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

            # Restyle each slide's badge/title/description for the active theme,
            # pulling the per-slide badge colour stashed as a widget property.
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
            # Styling is non-critical; swallow errors to keep the UI alive.
            pass

    def _set_slide(self, idx: int):
        """Show slide ``idx`` (wrapped modulo 3) and refresh the dot indicators."""
        self._curr_idx = idx % 3  # wrap so prev/next cycle endlessly
        self._stack.setCurrentIndex(self._curr_idx)
        self._update_dots()

    def _next_slide(self):
        """Advance to the next slide (called by the timer and next button)."""
        self._set_slide(self._curr_idx + 1)

    def _prev_slide(self):
        """Go back to the previous slide."""
        self._set_slide(self._curr_idx - 1)

    def _update_dots(self):
        """Restyle the dot indicators so the active slide's dot reads as a pill."""
        dark = ThemeManager().is_dark()
        inactive_color = "rgba(255, 255, 255, 0.25)" if dark else "rgba(0, 0, 0, 0.18)"
        for i, dot in enumerate(self._dots):
            if i == self._curr_idx:
                # Active dot: elongated accent pill.
                dot.setStyleSheet("background-color: #E11D48; border-radius: 4px; border: none;")
                dot.setFixedSize(18, 6)
            else:
                dot.setStyleSheet(f"background-color: {inactive_color}; border-radius: 3px; border: none;")
                dot.setFixedSize(6, 6)

    def enterEvent(self, event):
        """Pause auto-advance while the pointer is over the slideshow."""
        super().enterEvent(event)
        self._timer.stop()

    def leaveEvent(self, event):
        """Resume auto-advance once the pointer leaves the slideshow."""
        super().leaveEvent(event)
        self._timer.start()

    def update_greeting_and_permissions(self):
        """Refresh the greeting to the current user and gate CTA buttons by role.

        Sets slide 0's title to a time-of-day greeting using the signed-in
        user's display name, and shows/enables each slide's CTA button only if
        the user holds the matching permission (create booking, view booking,
        view AI). Fails silently if session state is unavailable.
        """
        try:
            from utils.session import SessionManager
            user = SessionManager.get_current_user() or {}
            role = (user.get("role") or "").lower()
            if role == "admin":
                display_name = "Admin"
            else:
                display_name = user.get("display_name") or user.get("username") or "Team Jayraldine"

            now = datetime.now()
            hour = now.hour
            if hour < 12:
                greet = f"Good Morning, {display_name}"
            elif hour < 18:
                greet = f"Good Afternoon, {display_name}"
            else:
                greet = f"Good Evening, {display_name}"

            # Slide 0's title label (index 2 in the tuple) carries the greeting.
            if self._slide_widgets and len(self._slide_widgets) > 0:
                self._slide_widgets[0][2].setText(greet)

            can_create_booking = SessionManager.has_permission("bookings", "create")
            can_view_booking = SessionManager.has_permission("bookings", "view")
            can_view_ai = SessionManager.has_permission("ai_chef_jay", "view")

            # Element 4 of each tuple is the CTA button; gate it per permission.
            if len(self._slide_widgets) > 0:
                self._slide_widgets[0][4].setVisible(can_create_booking)
                self._slide_widgets[0][4].setEnabled(can_create_booking)
            if len(self._slide_widgets) > 1:
                self._slide_widgets[1][4].setVisible(can_view_booking)
                self._slide_widgets[1][4].setEnabled(can_view_booking)
            if len(self._slide_widgets) > 2:
                self._slide_widgets[2][4].setVisible(can_view_ai)
                self._slide_widgets[2][4].setEnabled(can_view_ai)
        except Exception:
            # Session/permission lookups are best-effort here; ignore failures.
            pass


class KPICard(AnimatedCard):
    """A single metric tile: uppercase title, big value, and a status badge.

    Exposes :meth:`update_title`/:meth:`update_value`/:meth:`update_trend` so
    the dashboard can re-label and re-populate the same widgets when the active
    date filter changes.
    """

    def __init__(self, title, value, trend_text, trend_type="success", icon_name=None, parent=None):
        """Build the KPI tile.

        :param title: Metric name (rendered upper-cased).
        :param value: Large primary value string.
        :param trend_text: Secondary badge caption (e.g. a delta or note).
        :param trend_type: Badge style key — success/danger/warning/gold
            (anything else falls back to the info badge).
        :param icon_name: Optional icon shown top-right.
        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        self._title_lbl = QLabel(title.upper())
        self._title_lbl.setObjectName("kpiLabel")
        top_row.addWidget(self._title_lbl)
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
        # Map the semantic trend type to a QSS badge object name (info = default).
        badge_map = {
            "success": "badgeSuccess",
            "danger":  "badgeDanger",
            "warning": "badgeWarning",
            "gold":    "badgeGold",
        }
        self._trend_lbl.setObjectName(badge_map.get(trend_type, "badgeInfo"))
        layout.addWidget(self._trend_lbl)
        layout.addStretch()

    def update_title(self, title: str):
        """Set the tile's title (stored upper-cased to match the design)."""
        self._title_lbl.setText(title.upper())

    def update_value(self, value: str):
        """Set the tile's large primary value."""
        self._val_lbl.setText(value)

    def update_trend(self, text: str):
        """Set the tile's secondary trend/badge caption."""
        self._trend_lbl.setText(text)


class PeriodSummaryCard(AnimatedCard):
    """Revenue vs Expenses bar chart with a Weekly / Monthly / Yearly toggle.

    Weekly  = weeks of the current month
    Monthly = months of the current year
    Yearly  = every year with data (needs analytics_functions_migration.sql)
    """

    _PERIODS = ["Weekly", "Monthly", "Yearly"]

    def __init__(self, parent=None):
        """Build the header, period toggle buttons, and empty chart holder.

        Defaults to the Monthly view and schedules an initial async
        :meth:`refresh` shortly after construction.

        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self._period = "Monthly"  # active period toggle

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
            # Bind the period name per button so each switches to its own view.
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

        QTimer.singleShot(60, self.refresh)

    def set_period(self, period: str):
        """Switch the active period toggle and re-fetch the chart.

        No-op if ``period`` is already active; otherwise restyles the toggle
        buttons (re-polishing so QSS updates take effect) and refreshes.

        :param period: One of ``"Weekly"``, ``"Monthly"``, ``"Yearly"``.
        """
        if period == self._period:
            return
        self._period = period
        for p, btn in self._period_btns.items():
            btn.setObjectName("pageButtonActive" if p == period else "pageButton")
            # Force a restyle so the active/inactive QSS is reapplied immediately.
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.refresh()

    def _fetch(self):
        """Synchronously fetch ``(label, revenue, expense)`` rows for the period.

        Note: this is the blocking variant; :meth:`refresh` uses an equivalent
        background closure instead. Monthly falls back to an all-years summary
        if the year-scoped query is unavailable.

        :returns: List of ``(label, revenue, expense)`` tuples.
        """
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
            # Older DBs may lack the year-scoped query — fall back to all-time.
            rows = repo.get_profit_summary()
        self._range_lbl.setText(str(now.year))
        return [(r["month"], r["revenue"], r["expense"]) for r in rows]

    def refresh(self):
        """Start an async data fetch — never blocks the main thread.

        Guards against overlapping loads via ``_summary_loading``, snapshots the
        current period, and runs the repository queries in a background
        :class:`DataLoader`, rendering on the ``data_ready`` signal.
        """
        if getattr(self, '_summary_loading', False):
            return  # a fetch is already in flight
        self._summary_loading = True
        period = self._period  # capture now; user may toggle during the fetch

        def _bg_fetch():
            # Runs off the UI thread; re-imports locally so it's self-contained.
            from datetime import datetime as _dt
            import utils.repository as _repo
            now = _dt.now()
            if period == 'Weekly':
                rows = _repo.get_weekly_summary(now.year, now.month)
                label = now.strftime('Weeks of %B %Y')
                return label, [(r['week'], r['revenue'], r['expense']) for r in rows]
            if period == 'Yearly':
                rows = _repo.get_yearly_summary()
                label = 'All years'
                return label, [(str(r['year']), r['revenue'], r['expense']) for r in rows]
            try:
                rows = _repo.get_profit_summary_for_year(now.year)
            except Exception:
                rows = _repo.get_profit_summary()
            return str(now.year), [(r['month'], r['revenue'], r['expense']) for r in rows]

        loader = DataLoader(_bg_fetch)
        loader.data_ready.connect(self._on_summary_ready)
        loader.load_error.connect(lambda _e: self._summary_done())
        self._summary_loader = loader
        loader.start()

    def _on_summary_ready(self, result):
        """``data_ready`` slot: update the range label and render the chart.

        :param result: ``(label, data)`` where ``data`` is a list of
            ``(label, revenue, expense)`` tuples.
        """
        try:
            from shiboken6 import isValid
            # Result may land after the widget was destroyed — bail if so.
            if not isValid(self):
                return
        except Exception:
            pass
        label, data = result
        self._range_lbl.setText(label)
        self.render_chart(data)
        self._summary_done()

    def _summary_done(self):
        """Clear the in-flight flag so a subsequent :meth:`refresh` can run."""
        self._summary_loading = False

    def render_chart(self, data=None):
        """Draw the grouped revenue/expenses bar chart from ``data``.

        Replaces any existing chart view, shows an empty-state label when there
        is no data (or when QtCharts is unavailable), builds Revenue/Expenses
        bar sets with hover tooltips, and computes a "nice" rounded Y-axis
        scale/tick step so the axis labels land on clean peso values.

        :param data: List of ``(label, revenue, expense)`` tuples; ``None``
            is treated as empty.
        """
        if data is None:
            data = []

        # Tear down the previous chart view before drawing a fresh one.
        if self._chart_view is not None:
            self._chart_holder.removeWidget(self._chart_view)
            self._chart_view.deleteLater()
            self._chart_view = None

        if not data:
            self._empty_lbl.show()
            return
        self._empty_lbl.hide()

        try:
            from PySide6.QtCharts import (
                QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
            )
        except Exception as exc:
            # QtCharts isn't guaranteed on every device — degrade gracefully.
            self._empty_lbl.setText("Charts temporarily unavailable on this device.")
            self._empty_lbl.show()
            return
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

        # Build a hover handler bound to the current labels/values/colour so the
        # tooltip survives later mutation of the outer lists (default-arg capture).
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

        # Compute a "nice" Y-axis: pad the max by 15% then round the tick step
        # up to 1/2.5/5/10 x the power-of-ten magnitude so labels are clean.
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

        # QCategoryAxis lets us place one peso-formatted label per clean step.
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
    """One row in the Recent Activity list: colour dot + title/description + time."""

    def __init__(self, title, desc, time, dot_color="#22C55E", parent=None):
        """Build the activity row.

        :param title: Activity headline.
        :param desc: Supporting description (word-wrapped).
        :param time: Right-aligned relative/absolute time string.
        :param dot_color: Leading status-dot colour.
        :param parent: Optional Qt parent widget.
        """
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
    """One row in the Upcoming Events list with a live countdown.

    Shows the customer name, date, pax, and a status badge. When an
    ``event_dt`` is supplied it ticks a live "Starts in..." countdown every
    second; once the event time passes it swaps in a "Mark as Completed" button
    that completes the booking via the repository.
    """

    def __init__(self, name, date_str, pax, status, status_type="success", event_dt=None, db_id=None, on_completed=None, parent=None):
        """Build the event row and, if dated, start its countdown timer.

        :param name: Customer/event name.
        :param date_str: Pre-formatted date label.
        :param pax: Guest-count text (shown as "N set(s)").
        :param status: Status label text for the badge.
        :param status_type: Badge style key (success/warning/danger).
        :param event_dt: Event ``datetime`` enabling the live countdown; when
            ``None`` no countdown/complete button is shown.
        :param db_id: Booking id used to mark the event completed.
        :param on_completed: Callback invoked after a successful completion.
        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self._db_id = db_id
        self._on_completed = on_completed
        self._completed_btn = None  # lazily created once the event starts

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)
        self._main_lay = layout

        left = QVBoxLayout()
        left.setSpacing(3)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        date_lbl = QLabel(f"{date_str}  ·  {pax} set(s)")
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
        # Only dated events get a live countdown (ticked once per second).
        if event_dt is not None:
            self._countdown_lbl = QLabel()
            self._countdown_lbl.setStyleSheet("color: #D97706; font-size: 11px; font-weight: 700;")
            left.addWidget(self._countdown_lbl)
            self._tick_countdown()
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick_countdown)
            self._timer.start(1000)

    def _show_complete_button(self):
        """Lazily add the 'Mark as Completed' button once (idempotent)."""
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
        """Confirm, then mark the booking completed and fire ``on_completed``.

        No-op without a ``db_id``; warns the user if the repository call fails.
        """
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
        """Update the 'Starts in...' label each second.

        Once the event time is reached it stops the timer, shows "Event
        started", and reveals the complete button; otherwise it formats the
        remaining time as ``Nd HH:MM:SS`` (days omitted when zero).
        """
        delta = self._event_dt - datetime.now()
        total = int(delta.total_seconds())
        if total <= 0:
            # Event time reached: stop ticking and offer completion.
            self._countdown_lbl.setText("Event started")
            if hasattr(self, "_timer"):
                self._timer.stop()
            if self._db_id is not None:
                self._show_complete_button()
            return
        # Break the remaining seconds into days / hours / minutes / seconds.
        days, rem = divmod(total, 86400)
        h, rem2 = divmod(rem, 3600)
        m, s = divmod(rem2, 60)
        if days > 0:
            self._countdown_lbl.setText(f"Starts in {days}d {h:02d}:{m:02d}:{s:02d}")
        else:
            self._countdown_lbl.setText(f"Starts in {h:02d}:{m:02d}:{s:02d}")



class DashboardPage(QWidget):
    """The application's main dashboard screen.

    Composes the hero slideshow, date-filter toolbar, KPI row, revenue chart,
    daily-capacity gauge, and the Upcoming Events / Recent Activity / Follow-ups
    panels. Loads all data asynchronously (cached for the default "all time"
    view), re-labels its KPIs to match the active date filter, gates every
    section by user permissions, and refreshes itself whenever app-wide data
    signals fire. Also drives PDF/Excel export of the dashboard.
    """

    # Emitted for the parent shell to route navigation.
    new_booking_requested = Signal()
    view_all_activity_requested = Signal()
    ai_requested = Signal()

    def __init__(self, parent=None):
        """Build the full dashboard layout, wire data signals, and kick off the
        first data load.

        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self._dirty = True  # Load on first show

        # Subscribe to app-wide data-change events so the dashboard stays live.
        try:
            from utils.signals import app_events
            _ev = app_events()
            _ev.booking_saved.connect(self._mark_dirty_and_reload)
            _ev.booking_created.connect(self._mark_dirty_and_reload)
            _ev.booking_updated.connect(self._mark_dirty_and_reload)
            _ev.payment_recorded.connect(self._mark_dirty_and_reload)
            _ev.expense_saved.connect(self._mark_dirty_and_reload)
            _ev.customer_saved.connect(self._mark_dirty_and_reload)
            _ev.sync_completed.connect(self._mark_dirty_and_reload)
            _ev.data_changed.connect(self._mark_dirty_and_reload)
        except Exception:
            pass

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
        self._welcome_title = QLabel("Welcome back, Owner")
        self._welcome_title.setObjectName("h1")
        sub = QLabel("Here's what's happening at Jayraldine's Catering today.")
        sub.setObjectName("subtitle")
        v_title.addWidget(self._welcome_title)
        v_title.addWidget(sub)
        header_row.addLayout(v_title)
        header_row.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_export = QPushButton("  Export Report")
        self.btn_export.setObjectName("secondaryButton")
        self.btn_export.setIcon(btn_icon_secondary("export"))
        self.btn_export.setIconSize(QSize(15, 15))
        self.btn_export.setMenu(self._build_export_menu())

        self.btn_new = QPushButton("  New Booking")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.setIcon(btn_icon_primary("plus"))
        self.btn_new.setIconSize(QSize(15, 15))
        self.btn_new.clicked.connect(self.new_booking_requested.emit)

        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_new)
        header_row.addLayout(btn_layout)
        self.lay.addLayout(header_row)

        # Date Filtering Toolbar — mode drives which repository query/labels are
        # used; start/end/date hold the resolved range for the active mode.
        self._filter_mode = "all"
        self._filter_start = None
        self._filter_end = None
        self._filter_date = None
        filter_bar = QFrame()
        filter_bar.setObjectName("card")
        f_lay = QHBoxLayout(filter_bar)
        f_lay.setContentsMargins(16, 10, 16, 10)
        f_lay.setSpacing(10)

        f_icon = QLabel()
        f_icon.setPixmap(get_icon("calendar", color="#E11D48", size=QSize(16, 16)).pixmap(QSize(16, 16)))
        f_lbl = QLabel("Date Filter:")
        f_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        f_lay.addWidget(f_icon)
        f_lay.addWidget(f_lbl)

        self._btn_all_time = QPushButton("All Time")
        self._btn_all_time.setObjectName("primaryButton")
        self._btn_all_time.setFixedHeight(32)
        self._btn_all_time.setCursor(Qt.PointingHandCursor)
        self._btn_all_time.clicked.connect(lambda: self._set_date_filter_mode("all"))

        self._btn_today = QPushButton("Today")
        self._btn_today.setObjectName("secondaryButton")
        self._btn_today.setFixedHeight(32)
        self._btn_today.setCursor(Qt.PointingHandCursor)
        self._btn_today.clicked.connect(lambda: self._set_date_filter_mode("today"))

        self._btn_this_week = QPushButton("This Week")
        self._btn_this_week.setObjectName("secondaryButton")
        self._btn_this_week.setFixedHeight(32)
        self._btn_this_week.setCursor(Qt.PointingHandCursor)
        self._btn_this_week.clicked.connect(lambda: self._set_date_filter_mode("week"))

        self._btn_this_month = QPushButton("This Month")
        self._btn_this_month.setObjectName("secondaryButton")
        self._btn_this_month.setFixedHeight(32)
        self._btn_this_month.setCursor(Qt.PointingHandCursor)
        self._btn_this_month.clicked.connect(lambda: self._set_date_filter_mode("month"))

        f_lay.addWidget(self._btn_all_time)
        f_lay.addWidget(self._btn_today)
        f_lay.addWidget(self._btn_this_week)
        f_lay.addWidget(self._btn_this_month)

        f_lay.addSpacing(8)
        spec_lbl = QLabel("Specific Date:")
        spec_lbl.setObjectName("subtitle")
        f_lay.addWidget(spec_lbl)

        from PySide6.QtWidgets import QDateEdit
        from PySide6.QtCore import QDate
        self._date_picker = QDateEdit(QDate.currentDate())
        self._date_picker.setCalendarPopup(True)
        self._date_picker.setDisplayFormat("MMM dd, yyyy")
        self._date_picker.setFixedHeight(32)
        self._date_picker.dateChanged.connect(lambda qd: self._set_date_filter(qd.toString("yyyy-MM-dd")))
        f_lay.addWidget(self._date_picker)

        f_lay.addStretch()
        self._filter_status_lbl = QLabel("Showing: All Time Overview")
        self._filter_status_lbl.setStyleSheet("color: #E11D48; font-weight: 700; font-size: 12px;")
        f_lay.addWidget(self._filter_status_lbl)

        self.lay.addWidget(filter_bar)

        self.slideshow = WelcomeHeroSlideshow(self.content)
        self.slideshow.new_booking_requested.connect(self.new_booking_requested.emit)
        self.slideshow.manage_bookings_requested.connect(self.new_booking_requested.emit)
        self.slideshow.ai_requested.connect(self.ai_requested.emit)
        self.lay.addWidget(self.slideshow)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self._kpi_today       = KPICard("Today's Events",       "—", "Loading...",  "success", "calendar")
        self._kpi_downpayment = KPICard("Downpayment Received", "—", "Loading...",  "warning", "billing")
        self._kpi_revenue     = KPICard("Weekly Revenue",       "—", "Loading...",  "success", "trending-up")
        self._kpi_unpaid      = KPICard("Unpaid Invoices",      "—", "Loading...",  "danger",  "billing")
        self._kpi_profit      = KPICard("Net Profit (YTD)",     "—", "Loading...",  "success", "trending-up")
        for card in [self._kpi_today, self._kpi_downpayment, self._kpi_revenue, self._kpi_unpaid, self._kpi_profit]:
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

        # Event rows live in a capped scroll area so a long list scrolls inside
        # the card (~10 rows visible) instead of stretching the whole page and
        # pushing Recent Activity / Follow-ups below the fold.
        self._ev_scroll = QScrollArea()
        self._ev_scroll.setWidgetResizable(True)
        self._ev_scroll.setFrameShape(QFrame.NoFrame)
        self._ev_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._ev_scroll.setMaximumHeight(470)
        self._ev_items_container = QWidget()
        self._ev_items_lay = QVBoxLayout(self._ev_items_container)
        self._ev_items_lay.setContentsMargins(0, 0, 6, 0)
        self._ev_items_lay.setSpacing(0)
        self._ev_scroll.setWidget(self._ev_items_container)
        self._ev_lay.addWidget(self._ev_scroll)

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

        from components.loading_overlay import LoadingOverlay
        self._loader = LoadingOverlay(self, "Loading dashboard metrics & analytics...")

        self.refresh_permissions()
        # Defer the initial load to the next event-loop turn so the page paints first.
        QTimer.singleShot(0, self._load_data)

    def refresh_permissions(self):
        """Update the welcome title and show/hide every section per permissions.

        Reads the current user/role, sets the greeting, then toggles visibility
        of the new-booking/export buttons, each KPI tile, the summary chart,
        capacity/events cards, and the activity/follow-up panels based on the
        user's bookings/finance/customers/reports permissions.
        """
        from utils.session import SessionManager
        user = SessionManager.get_current_user() or {}
        role = (user.get("role") or "").lower()
        if role == "admin":
            display_name = "Admin"
        else:
            display_name = user.get("display_name") or user.get("username") or "User"

        if hasattr(self, "_welcome_title"):
            self._welcome_title.setText(f"Welcome back, {display_name}")

        if hasattr(self, "slideshow") and hasattr(self.slideshow, "update_greeting_and_permissions"):
            self.slideshow.update_greeting_and_permissions()

        can_view_bookings = SessionManager.has_permission("bookings", "view")
        can_create_bookings = SessionManager.has_permission("bookings", "create")
        can_view_finance = SessionManager.has_permission("cashflow", "view") or SessionManager.has_permission("reports", "view")
        can_view_customers = SessionManager.has_permission("customers", "view")
        can_export = SessionManager.has_permission("reports", "view")

        if hasattr(self, "btn_new"):
            self.btn_new.setVisible(can_create_bookings)
            self.btn_new.setEnabled(can_create_bookings)
        if hasattr(self, "btn_export"):
            self.btn_export.setVisible(can_export)
            self.btn_export.setEnabled(can_export)

        if hasattr(self, "_kpi_today"):
            self._kpi_today.setVisible(can_view_bookings)
        if hasattr(self, "_kpi_downpayment"):
            self._kpi_downpayment.setVisible(can_view_finance)
        if hasattr(self, "_kpi_revenue"):
            self._kpi_revenue.setVisible(can_view_finance)
        if hasattr(self, "_kpi_unpaid"):
            self._kpi_unpaid.setVisible(can_view_finance)
        if hasattr(self, "_kpi_profit"):
            self._kpi_profit.setVisible(can_view_finance)
        if hasattr(self, "summary_card"):
            self.summary_card.setVisible(can_view_finance)

        if hasattr(self, "cap_card"):
            self.cap_card.setVisible(can_view_bookings)
        if hasattr(self, "events_card"):
            self.events_card.setVisible(can_view_bookings)

        if hasattr(self, "act_card"):
            self.act_card.setVisible(can_view_bookings)
        if hasattr(self, "followup_card"):
            self.followup_card.setVisible(can_view_customers)

    def showEvent(self, event):
        """On show, re-check permissions and load data if marked dirty."""
        super().showEvent(event)
        self.refresh_permissions()
        if getattr(self, "_dirty", True):
            self._load_data()
            self._dirty = False

    def _mark_dirty(self):
        """Flag the cached data stale so the next show triggers a reload."""
        self._dirty = True

    def _mark_dirty_and_reload(self):
        """Signal slot: mark stale and, if currently visible, reload silently."""
        self._dirty = True
        if self.isVisible():
            self.reload(silent=True)

    def _build_export_menu(self):
        """Build the theme-aware PDF/Excel dropdown menu for the export button."""
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
        """Export the dashboard to a PDF (KPIs, bookings, analytics + chart image).

        Permission-gated on ``reports:view``. Prompts for a path, gathers report
        data, snapshots the summary chart to a PNG (rendering at 2x, falling
        back to a plain grab on failure), then hands everything to the exporter.
        """
        from utils.session import SessionManager
        if not SessionManager.has_permission("reports", "view"):
            from components.dialogs import error
            error(self, title="Access Denied", message="You do not have permission to export reports.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "jayraldines_dashboard.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return  # user cancelled
        kpis = repo.get_report_kpis()
        bookings = repo.get_all_bookings() or []
        sections = _exporter.build_analytics_sections()
        chart_images = []
        try:
            # Render the summary card at 2x DPI into a PNG for crisp PDF output.
            import tempfile, os as _os
            from PySide6.QtGui import QPixmap
            sz = self.summary_card.size()
            w = max(10, sz.width())
            h = max(10, sz.height())
            pixmap = QPixmap(w * 2, h * 2)
            pixmap.setDevicePixelRatio(2.0)
            self.summary_card.render(pixmap)
            if pixmap.isNull():
                # render() produced nothing — fall back to a straight widget grab.
                pixmap = self.summary_card.grab()

            png = _os.path.join(tempfile.mkdtemp(prefix="jc_dash_"), "summary.png")
            if pixmap.save(png, "PNG"):
                chart_images.append(("Revenue Summary", png))
        except Exception as exc:
            # Any capture error: retry once with a plain grab, else skip the chart.
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
            prompt_file_saved(self, path, title="Dashboard PDF Generated", message="Dashboard summary PDF generated successfully.")
        else:
            QMessageBox.warning(self, "Export Failed",
                "PDF export failed. Make sure reportlab is installed:\npip install reportlab")

    def _export_excel(self):
        """Export the dashboard KPIs, bookings, and analytics to an .xlsx file.

        Permission-gated on ``reports:view``; prompts for a path and delegates
        to the exporter, warning the user if the export fails.
        """
        from utils.session import SessionManager
        if not SessionManager.has_permission("reports", "view"):
            from components.dialogs import error
            error(self, title="Access Denied", message="You do not have permission to export reports.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "jayraldines_dashboard.xlsx", "Excel Files (*.xlsx)"
        )
        if not path:
            return  # user cancelled
        kpis = repo.get_report_kpis()
        bookings = repo.get_all_bookings() or []
        sections = _exporter.build_analytics_sections()
        ok = _exporter.export_excel(path, kpis, bookings, "Dashboard Report", "All Time",
                                    sections=sections)
        if ok:
            prompt_file_saved(self, path, title="Dashboard Excel Exported", message="Dashboard summary Excel exported successfully.")
        else:
            QMessageBox.warning(self, "Export Failed",
                "Excel export failed. Make sure openpyxl is installed:\npip install openpyxl")

    def _set_date_filter_mode(self, mode: str, custom_date: str = None):
        """Apply a date-filter preset, update the status label, and reload data.

        Resolves ``_filter_start``/``_filter_end``/``_filter_date`` for the
        chosen ``mode`` (today / this week / this month / a custom single day /
        all time), restyles the toolbar buttons to mark the active one, then
        silently reloads.

        :param mode: One of ``"today"``, ``"week"``, ``"month"``, ``"custom"``,
            or anything else (treated as ``"all"``).
        :param custom_date: ``YYYY-MM-DD`` used only when ``mode == "custom"``.
        """
        import calendar
        from datetime import timedelta
        self._filter_mode = mode
        today = datetime.now().date()

        if mode == "today":
            today_str = today.strftime("%Y-%m-%d")
            self._filter_start = today_str
            self._filter_end = today_str
            self._filter_date = today_str
            self._filter_status_lbl.setText(f"Showing: Today's Metrics ({today.strftime('%b %d, %Y')})")
        elif mode == "week":
            # Monday-anchored week: back up to weekday()==0, then +6 for Sunday.
            start_d = today - timedelta(days=today.weekday())
            end_d = start_d + timedelta(days=6)
            self._filter_start = start_d.strftime("%Y-%m-%d")
            self._filter_end = end_d.strftime("%Y-%m-%d")
            self._filter_date = self._filter_start
            self._filter_status_lbl.setText(f"Showing: This Week ({start_d.strftime('%b %d')} – {end_d.strftime('%b %d, %Y')})")
        elif mode == "month":
            # First to last calendar day of the current month.
            start_d = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_d = today.replace(day=last_day)
            self._filter_start = start_d.strftime("%Y-%m-%d")
            self._filter_end = end_d.strftime("%Y-%m-%d")
            self._filter_date = self._filter_start
            self._filter_status_lbl.setText(f"Showing: This Month ({today.strftime('%B %Y')})")
        elif mode == "custom" and custom_date:
            self._filter_start = custom_date
            self._filter_end = custom_date
            self._filter_date = custom_date
            self._filter_status_lbl.setText(f"Showing: Date ({custom_date})")
        else:
            self._filter_mode = "all"
            self._filter_start = None
            self._filter_end = None
            self._filter_date = None
            self._filter_status_lbl.setText("Showing: All Time Overview")

        # Visual button states — highlight the active preset, restyle the rest,
        # and re-polish so the QSS object-name swap takes effect immediately.
        btn_modes = {
            "all": getattr(self, "_btn_all_time", None),
            "today": getattr(self, "_btn_today", None),
            "week": getattr(self, "_btn_this_week", None),
            "month": getattr(self, "_btn_this_month", None),
        }
        for b_mode, btn in btn_modes.items():
            if btn:
                btn.setObjectName("primaryButton" if b_mode == self._filter_mode else "secondaryButton")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

        self._load_data(silent=True)

    def _set_date_filter(self, date_str: str = None):
        """Handle custom date picker selection."""
        if not date_str:
            self._set_date_filter_mode("all")
        elif date_str == datetime.now().strftime("%Y-%m-%d"):
            self._set_date_filter_mode("today")
        else:
            self._set_date_filter_mode("custom", custom_date=date_str)

    def reload(self, silent: bool = False):
        """Force a fresh reload: clear the cached dashboard data and re-fetch.

        :param silent: When True, suppress the loading overlay during the fetch.
        """
        self._dirty = False
        self.refresh_permissions()
        from utils.data_cache import DataCache
        # Drop cached data so _load_data actually hits the repository again.
        DataCache.invalidate("dashboard_data", "dashboard")
        self._load_data(silent=silent)

    def _fetch_dashboard_data(self):
        """Runs in background thread — fetches all dashboard data in one shot."""
        mode = getattr(self, "_filter_mode", "all")
        d_start = getattr(self, "_filter_start", None)
        d_end = getattr(self, "_filter_end", None)

        try:
            # The chart always reflects the full current year, independent of filter.
            now = datetime.now()
            rows = repo.get_monthly_revenue_chart_data(now.year)
            chart_data = [(r["month"], r["revenue"], r["expense"]) for r in rows] if rows else []
        except Exception:
            chart_data = []

        # KPIs/events honour the active date range when one is set; else all-time.
        if d_start and d_end:
            kpis = repo.get_dashboard_kpis_filtered(d_start, d_end)
            events = repo.get_upcoming_events(limit=20, date_start=d_start, date_end=d_end)
        else:
            kpis = repo.get_dashboard_kpis()
            events = repo.get_upcoming_events(limit=20)

        return {
            "kpis":        kpis,
            "profit":      repo.get_profit_summary(),
            "events":      events,
            "activity":    repo.get_recent_activity(limit=10),
            "chart_data":  chart_data,
            "followups":   repo.get_todays_follow_ups(),
            "filter_mode": mode,
        }

    def _load_data(self, silent: bool = False):
        """Load dashboard data, preferring cache for the default "all" view.

        For the "all time" mode it serves a cached payload once (if present) to
        make the first paint instant; otherwise it spins up a background
        :class:`DataLoader` running :meth:`_fetch_dashboard_data`. Guards against
        launching a second concurrent load.

        :param silent: When True, don't show the loading overlay.
        """
        mode = getattr(self, "_filter_mode", "all")
        if mode == "all":
            from utils.data_cache import DataCache
            cached = DataCache.get("dashboard_data")
            # Use cache only for the very first load, so it paints instantly.
            if cached is not None and not getattr(self, "_has_loaded_once", False):
                self._has_loaded_once = True
                if hasattr(self, "_loader") and not silent:
                    self._loader.show_overlay("Loading dashboard metrics & analytics...")
                    QTimer.singleShot(60, lambda: self._on_dash_data_ready(cached))
                else:
                    self._on_dash_data_ready(cached)
                return

        # Don't stack loaders — bail if a previous fetch is still running.
        prev = getattr(self, "_dash_loader", None)
        if prev is not None and prev.isRunning():
            return  # already loading

        if hasattr(self, "_loader") and not silent and not getattr(self, "_has_loaded_once", False):
            self._loader.show_overlay("Loading dashboard metrics & analytics...")

        loader = DataLoader(self._fetch_dashboard_data)
        loader.data_ready.connect(self._on_dash_data_ready_and_cache)
        def _on_dash_err(msg):
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()
            print(f"[Dashboard] Load error: {msg}")
        loader.load_error.connect(_on_dash_err)
        self._dash_loader = loader
        loader.start()

    def _on_dash_data_ready_and_cache(self, data):
        """Cache the payload (only for the "all" view) then render it."""
        mode = getattr(self, "_filter_mode", "all")
        if mode == "all" and data:
            from utils.data_cache import DataCache
            DataCache.set("dashboard_data", data)
        self._on_dash_data_ready(data)

    def _on_dash_data_ready(self, data):
        """Render a fetched dashboard payload into every widget.

        Re-checks permissions, then re-titles and repopulates the KPI tiles to
        match the active filter mode, updates the capacity gauge, redraws the
        summary chart, and rebuilds the events/activity/follow-up lists. Always
        hides the loading overlay when done.

        :param data: Dict from :meth:`_fetch_dashboard_data` (kpis, profit,
            events, activity, chart_data, followups, filter_mode).
        """
        try:
            from shiboken6 import isValid
            # Payload may arrive after teardown — abort if the widget is gone.
            if not isValid(self):
                return
            self.refresh_permissions()
            mode        = data.get("filter_mode", "all")
            kpis        = data.get("kpis", {})
            profit_data = data.get("profit", [])
            events      = data.get("events", [])
            activity    = data.get("activity", [])
            chart_data  = data.get("chart_data", [])
            followups   = data.get("followups", [])

            todays  = kpis.get("todays_events", 0)
            dp_rec  = float(kpis.get("downpayment_received") or 0.0)
            revenue = float(kpis.get("weekly_revenue") or kpis.get("daily_sales") or 0.0)
            unpaid  = float(kpis.get("unpaid_invoices") or 0.0)
            pax     = int(kpis.get("todays_pax") or 0)
            net_income = float(kpis.get("net_income") or 0.0)
            expenses = float(kpis.get("daily_expenses") or 0.0)

            # Each filter mode relabels the same five tiles with period-specific
            # titles/captions; the "else" branch is the default all-time view.
            if mode == "today":
                self._kpi_today.update_title("Today's Events")
                self._kpi_today.update_value(str(todays))
                self._kpi_today.update_trend(f"{todays} event{'s' if todays != 1 else ''} today")

                self._kpi_downpayment.update_title("Downpayments")
                self._kpi_downpayment.update_value(f"₱ {dp_rec:,.2f}")
                self._kpi_downpayment.update_trend("Collected today")

                self._kpi_revenue.update_title("Today's Revenue")
                self._kpi_revenue.update_value(f"₱ {revenue:,.0f}")
                self._kpi_revenue.update_trend("Sales & collections today")

                self._kpi_unpaid.update_title("Unpaid (Today)")
                self._kpi_unpaid.update_value(f"₱ {unpaid:,.0f}")
                self._kpi_unpaid.update_trend("Balance on today's events")

                self._kpi_profit.update_title("Net Profit (Today)")
                self._kpi_profit.update_value(f"₱ {net_income:,.0f}")
                self._kpi_profit.update_trend(f"Rev ₱{revenue:,.0f} − Exp ₱{expenses:,.0f}")

            elif mode == "week":
                self._kpi_today.update_title("This Week's Events")
                self._kpi_today.update_value(str(todays))
                self._kpi_today.update_trend(f"{todays} event{'s' if todays != 1 else ''} this week")

                self._kpi_downpayment.update_title("Downpayments")
                self._kpi_downpayment.update_value(f"₱ {dp_rec:,.2f}")
                self._kpi_downpayment.update_trend("Collected this week")

                self._kpi_revenue.update_title("Weekly Revenue")
                self._kpi_revenue.update_value(f"₱ {revenue:,.0f}")
                self._kpi_revenue.update_trend("Sales & collections this week")

                self._kpi_unpaid.update_title("Unpaid (This Week)")
                self._kpi_unpaid.update_value(f"₱ {unpaid:,.0f}")
                self._kpi_unpaid.update_trend("Balance on this week's events")

                self._kpi_profit.update_title("Net Profit (This Week)")
                self._kpi_profit.update_value(f"₱ {net_income:,.0f}")
                self._kpi_profit.update_trend(f"Rev ₱{revenue:,.0f} − Exp ₱{expenses:,.0f}")

            elif mode == "month":
                self._kpi_today.update_title("This Month's Events")
                self._kpi_today.update_value(str(todays))
                self._kpi_today.update_trend(f"{todays} event{'s' if todays != 1 else ''} this month")

                self._kpi_downpayment.update_title("Downpayments")
                self._kpi_downpayment.update_value(f"₱ {dp_rec:,.2f}")
                self._kpi_downpayment.update_trend("Collected this month")

                self._kpi_revenue.update_title("Monthly Revenue")
                self._kpi_revenue.update_value(f"₱ {revenue:,.0f}")
                self._kpi_revenue.update_trend("Sales & collections this month")

                self._kpi_unpaid.update_title("Unpaid (This Month)")
                self._kpi_unpaid.update_value(f"₱ {unpaid:,.0f}")
                self._kpi_unpaid.update_trend("Balance on this month's events")

                self._kpi_profit.update_title("Net Profit (This Month)")
                self._kpi_profit.update_value(f"₱ {net_income:,.0f}")
                self._kpi_profit.update_trend(f"Rev ₱{revenue:,.0f} − Exp ₱{expenses:,.0f}")

            else:
                self._kpi_today.update_title("Today's Events")
                self._kpi_today.update_value(str(todays))
                self._kpi_today.update_trend(f"{todays} event{'s' if todays != 1 else ''} today")

                self._kpi_downpayment.update_title("Downpayment Received")
                self._kpi_downpayment.update_value(f"₱ {dp_rec:,.2f}")
                self._kpi_downpayment.update_trend("From upcoming events")

                self._kpi_revenue.update_title("Weekly Revenue")
                self._kpi_revenue.update_value(f"₱ {revenue:,.0f}")
                self._kpi_revenue.update_trend("This week's revenue")

                self._kpi_unpaid.update_title("Unpaid Invoices")
                self._kpi_unpaid.update_value(f"₱ {unpaid:,.0f}")
                self._kpi_unpaid.update_trend("Outstanding balance")

                # All-time view derives YTD net profit from the profit summary rows.
                try:
                    total_rev = sum(r["revenue"] for r in profit_data)
                    total_exp = sum(r["expense"] for r in profit_data)
                    net = total_rev - total_exp
                    self._kpi_profit.update_title("Net Profit (YTD)")
                    self._kpi_profit.update_value(f"₱ {net:,.0f}")
                    self._kpi_profit.update_trend(f"Rev ₱{total_rev:,.0f} − Exp ₱{total_exp:,.0f}")
                except Exception:
                    self._kpi_profit.update_title("Net Profit (YTD)")
                    self._kpi_profit.update_value("—")
                    self._kpi_profit.update_trend("No expense data")

            _pax_color = "#F9FAFB" if ThemeManager().is_dark() else "#101828"
            self._pax_lbl.setText(
                f'<span style="font-size:28px;font-weight:800;color:{_pax_color};">{pax}</span>'
                f'<span style="color:#7A879E;font-size:16px;"> / 600</span>'
            )
            # Daily-capacity gauge against the fixed 600-pax cap.
            self.prog.setValue(min(pax, 600))
            pct = round((pax / 600) * 100, 1)
            self._cap_pct_lbl.setText(f"{pct}% Capacity")
            self._cap_rem_lbl.setText(f"{max(0, 600 - pax)} slots remaining")

            self.summary_card.render_chart(chart_data)

            # Cache the raw lists so filter_search can re-filter without refetching.
            self._cached_events   = events
            self._cached_activity = activity
            self._rebuild_events()
            self._rebuild_activity()
            self._rebuild_followup_alerts(followups)
        finally:
            if hasattr(self, "_loader"):
                self._loader.hide_overlay()

    def _clear_layout_from(self, layout, from_index: int):
        """Remove and delete all items in ``layout`` at/after ``from_index``.

        Used to clear dynamic rows while preserving fixed header widgets that
        live at the start of a card's layout.
        """
        while layout.count() > from_index:
            item = layout.takeAt(from_index)
            if item.widget():
                item.widget().deleteLater()

    def filter_search(self, text: str):
        """Filter the cached events/activity by ``text`` and rebuild both lists.

        Matches events on customer name / date / status and activity on
        title / description; an empty query shows everything.
        """
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
        """Rebuild the Upcoming Events list, one :class:`EventItem` per booking.

        Falls back to the cached list, then to a fresh repository query, when
        ``events`` isn't supplied. Derives a proper event ``datetime`` (defaulting
        the time to 6pm when only a date is known) so each row can run its
        countdown, and maps status to a badge style.

        :param events: Optional explicit event list (e.g. from a search filter).
        """
        self._clear_layout_from(self._ev_items_lay, 0)
        if events is None:
            events = getattr(self, "_cached_events", None)
        if events is None:
            events = repo.get_upcoming_events(limit=20)
        if not events:
            empty = QLabel("No upcoming events.")
            empty.setObjectName("subtitle")
            empty.setContentsMargins(0, 8, 0, 8)
            self._ev_items_lay.addWidget(empty)
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
                                # No explicit time — assume a 6pm start for the countdown.
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

                self._ev_items_lay.addWidget(EventItem(
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
                self._ev_items_lay.addWidget(sep)
        self._ev_items_lay.addStretch()

    def _rebuild_activity(self, activities=None):
        """Rebuild the Recent Activity list below its fixed header.

        Falls back to the cached list, then a repository query, when
        ``activities`` isn't given; shows an empty-state label when there's none.

        :param activities: Optional explicit activity list (e.g. from search).
        """
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
        """Rebuild the 'Follow-ups Due Today' panel and its count badge.

        Fetches today's follow-ups when not supplied; switches the header badge
        between a green "None due" and a red "N Due", and renders one row per
        follow-up (or an empty-state label).

        :param followups: Optional explicit follow-up list.
        """
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