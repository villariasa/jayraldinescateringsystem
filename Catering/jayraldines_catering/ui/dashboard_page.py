from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QProgressBar, QScrollArea,
    QFileDialog, QMessageBox, QMenu, QAction
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from datetime import datetime

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, get_icon
import utils.repository as repo
from utils import exporter as _exporter


class AnimatedCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


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
            ico.setPixmap(get_icon(icon_name, color="#374151", size=QSize(18, 18)).pixmap(QSize(18, 18)))
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
        t_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #F9FAFB;")
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        d_lbl.setWordWrap(True)
        vbox.addWidget(t_lbl)
        vbox.addWidget(d_lbl)
        layout.addLayout(vbox)
        layout.addStretch()

        time_lbl = QLabel(time)
        time_lbl.setStyleSheet("color: #6B7280; font-size: 11px; white-space: nowrap;")
        layout.addWidget(time_lbl, alignment=Qt.AlignTop)


class EventItem(QWidget):
    def __init__(self, name, date_str, pax, status, status_type="success", event_dt=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(3)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #F9FAFB;")
        date_lbl = QLabel(f"{date_str}  ·  {pax} pax")
        date_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        left.addWidget(name_lbl)
        left.addWidget(date_lbl)

        self._event_dt = event_dt
        self._countdown_lbl = None
        if event_dt is not None:
            self._countdown_lbl = QLabel()
            self._countdown_lbl.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: 700;")
            left.addWidget(self._countdown_lbl)
            self._tick_countdown()
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick_countdown)
            self._timer.start(1000)

        layout.addLayout(left)
        layout.addStretch()

        badge = QLabel(status)
        badge_map = {"success": "badgeSuccess", "warning": "badgeWarning", "danger": "badgeDanger"}
        badge.setObjectName(badge_map.get(status_type, "badgeInfo"))
        layout.addWidget(badge)

    def _tick_countdown(self):
        delta = self._event_dt - datetime.now()
        total = int(delta.total_seconds())
        if total <= 0:
            self._countdown_lbl.setText("Event started")
            if hasattr(self, "_timer"):
                self._timer.stop()
            return
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        self._countdown_lbl.setText(f"Starts in {h:02d}:{m:02d}:{s:02d}")


class MenuAlertItem(QWidget):
    def __init__(self, item, issue, badge_type="badgeWarning", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)

        name_lbl = QLabel(item)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(name_lbl)
        layout.addStretch()

        issue_lbl = QLabel(issue)
        issue_lbl.setObjectName(badge_type)
        layout.addWidget(issue_lbl)


class DashboardPage(QWidget):
    new_booking_requested = Signal()

    def __init__(self):
        super().__init__()

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)

        self.content = QWidget(self.scroll)
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

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self._kpi_today    = KPICard("Today's Events",   "—", "Loading...",  "success", "calendar")
        self._kpi_pending  = KPICard("Pending Bookings", "—", "Loading...",  "warning", "orders")
        self._kpi_revenue  = KPICard("Weekly Revenue",   "—", "Loading...",  "success", "trending-up")
        self._kpi_unpaid   = KPICard("Unpaid Invoices",  "—", "Loading...",  "danger",  "billing")
        for card in [self._kpi_today, self._kpi_pending, self._kpi_revenue, self._kpi_unpaid]:
            kpi_row.addWidget(card)
        self.lay.addLayout(kpi_row)

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
        self._pax_lbl.setStyleSheet("font-size:28px;font-weight:800;color:#F9FAFB;")
        cap_head.addWidget(self._pax_lbl)
        cap_lay.addLayout(cap_head)

        self.prog = QProgressBar()
        self.prog.setRange(0, 600)
        self.prog.setValue(0)
        self.prog.setFixedHeight(10)
        cap_lay.addWidget(self.prog)

        self._cap_pct_lbl = QLabel("")
        self._cap_pct_lbl.setStyleSheet("color:#F59E0B;font-weight:700;font-size:12px;")
        self._cap_rem_lbl = QLabel("")
        self._cap_rem_lbl.setStyleSheet("color:#6B7280;font-size:12px;")
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
        act_head.addWidget(btn_view)
        self._act_lay.addLayout(act_head)

        act_div = QFrame()
        act_div.setObjectName("divider")
        self._act_lay.addWidget(act_div)

        self._act_items_start = self._act_lay.count()

        self.menu_card = AnimatedCard(self.content)
        self._menu_lay = QVBoxLayout(self.menu_card)
        self._menu_lay.setContentsMargins(24, 24, 24, 24)
        self._menu_lay.setSpacing(0)

        menu_head = QHBoxLayout()
        menu_title = QLabel("Menu Alerts")
        menu_title.setObjectName("h3")
        menu_head.addWidget(menu_title)
        menu_head.addStretch()
        self._menu_badge = QLabel("—")
        self._menu_badge.setObjectName("badgeWarning")
        menu_head.addWidget(self._menu_badge)
        self._menu_lay.addLayout(menu_head)

        menu_div = QFrame()
        menu_div.setObjectName("divider")
        self._menu_lay.addWidget(menu_div)

        self._menu_items_start = self._menu_lay.count()

        bot_row.addWidget(self.act_card, 3)
        bot_row.addWidget(self.menu_card, 2)
        self.lay.addLayout(bot_row)

        self.scroll.setWidget(self.content)
        self.root_layout.addWidget(self.scroll)

        self._load_data()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._load_data)
        self._refresh_timer.start(60_000)

    def _build_export_menu(self):
        menu = QMenu(self)
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
        ok = _exporter.export_pdf(path, kpis, bookings, "Dashboard Report", "All Time")
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
        ok = _exporter.export_excel(path, kpis, bookings, "Dashboard Report", "All Time")
        if ok:
            QMessageBox.information(self, "Export", f"Excel exported to:\n{path}")
        else:
            QMessageBox.warning(self, "Export Failed",
                "Excel export failed. Make sure openpyxl is installed:\npip install openpyxl")

    def _load_data(self):
        kpis = repo.get_dashboard_kpis()

        todays = kpis.get("todays_events", 0)
        pending = kpis.get("pending_bookings", 0)
        revenue = kpis.get("weekly_revenue", 0.0)
        unpaid = kpis.get("unpaid_invoices", 0.0)
        pax = kpis.get("todays_pax", 0)

        self._kpi_today.update_value(str(todays))
        self._kpi_today.update_trend(f"{todays} event{'s' if todays != 1 else ''} today")

        self._kpi_pending.update_value(str(pending))
        self._kpi_pending.update_trend("Requires review" if pending > 0 else "All clear")

        self._kpi_revenue.update_value(f"₱ {revenue:,.0f}")
        self._kpi_revenue.update_trend("This week's revenue")

        self._kpi_unpaid.update_value(f"₱ {unpaid:,.0f}")
        self._kpi_unpaid.update_trend("Outstanding balance")

        self._pax_lbl.setText(
            f'<span style="font-size:28px;font-weight:800;color:#F9FAFB;">{pax}</span>'
            f'<span style="color:#6B7280;font-size:16px;"> / 600</span>'
        )
        self.prog.setValue(min(pax, 600))
        pct = round((pax / 600) * 100, 1)
        self._cap_pct_lbl.setText(f"{pct}% Capacity")
        self._cap_rem_lbl.setText(f"{max(0, 600 - pax)} slots remaining")

        self._rebuild_events()
        self._rebuild_activity()
        self._rebuild_menu_alerts()

    def _clear_layout_from(self, layout, from_index: int):
        while layout.count() > from_index:
            item = layout.takeAt(from_index)
            if item.widget():
                item.widget().deleteLater()

    def _rebuild_events(self):
        self._clear_layout_from(self._ev_lay, self._ev_items_start)
        events = repo.get_upcoming_events(limit=5)
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
                ))
                sep = QFrame()
                sep.setObjectName("divider")
                self._ev_lay.addWidget(sep)
        self._ev_lay.addStretch()

    def _rebuild_activity(self):
        self._clear_layout_from(self._act_lay, self._act_items_start)
        activities = repo.get_recent_activity(limit=5)
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

    def _rebuild_menu_alerts(self):
        self._clear_layout_from(self._menu_lay, self._menu_items_start)
        alerts = repo.get_menu_alerts()
        badge_map = {"warning": "badgeWarning", "danger": "badgeDanger"}
        if not alerts:
            self._menu_badge.setText("No Issues")
            self._menu_badge.setObjectName("badgeSuccess")
            empty = QLabel("All menu items are fine.")
            empty.setObjectName("subtitle")
            empty.setContentsMargins(0, 8, 0, 8)
            self._menu_lay.addWidget(empty)
        else:
            self._menu_badge.setText(f"{len(alerts)} Issue{'s' if len(alerts) != 1 else ''}")
            self._menu_badge.setObjectName("badgeWarning")
            for a in alerts:
                bt = badge_map.get(a.get("badge_type", "warning"), "badgeWarning")
                self._menu_lay.addWidget(MenuAlertItem(a["item"], a["issue"], bt))
                sep = QFrame()
                sep.setObjectName("divider")
                self._menu_lay.addWidget(sep)
        self._menu_lay.addStretch()
