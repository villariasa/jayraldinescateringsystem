from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QProgressBar, QScrollArea,
    QFileDialog, QMessageBox, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QAction
from datetime import datetime

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, get_icon
from utils.theme import ThemeManager
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

        left = QVBoxLayout()
        left.setSpacing(3)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        date_lbl = QLabel(f"{date_str}  ·  {pax} pax")
        date_lbl.setStyleSheet("font-size: 12px;")
        left.addWidget(name_lbl)
        left.addWidget(date_lbl)

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

        layout.addLayout(left)
        layout.addStretch()

        badge = QLabel(status)
        badge_map = {"success": "badgeSuccess", "warning": "badgeWarning", "danger": "badgeDanger"}
        badge.setObjectName(badge_map.get(status_type, "badgeInfo"))
        layout.addWidget(badge)

        self._layout = layout

    def _show_complete_button(self):
        if self._completed_btn is not None:
            return
        self._completed_btn = QPushButton("Mark as Completed")
        self._completed_btn.setStyleSheet(
            "QPushButton { background: #16A34A; color: #fff; border-radius: 6px; "
            "padding: 4px 10px; font-size: 11px; font-weight: 600; } "
            "QPushButton:hover { background: #15803D; }"
        )
        self._completed_btn.clicked.connect(self._handle_complete)
        self._layout.addWidget(self._completed_btn)

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

        self._load_data()

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

    def reload(self):
        self._load_data()

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

        try:
            profit_data = repo.get_profit_summary()
            total_rev = sum(r["revenue"] for r in profit_data)
            total_exp = sum(r["expense"] for r in profit_data)
            net = total_rev - total_exp
            profit_color = "success" if net >= 0 else "danger"
            self._kpi_profit.update_value(f"₱ {net:,.0f}")
            self._kpi_profit.update_trend(f"Rev ₱{total_rev:,.0f} − Exp ₱{total_exp:,.0f}")
        except Exception:
            self._kpi_profit.update_value("—")
            self._kpi_profit.update_trend("No expense data")

        self._pax_lbl.setText(
            f'<span style="font-size:28px;font-weight:800;color:#F9FAFB;">{pax}</span>'
            f'<span style="color:#6B7280;font-size:16px;"> / 600</span>'
        )
        self.prog.setValue(min(pax, 600))
        pct = round((pax / 600) * 100, 1)
        self._cap_pct_lbl.setText(f"{pct}% Capacity")
        self._cap_rem_lbl.setText(f"{max(0, 600 - pax)} slots remaining")

        self._cached_events = repo.get_upcoming_events(limit=20)
        self._cached_activity = repo.get_recent_activity(limit=10)
        self._rebuild_events()
        self._rebuild_activity()
        self._rebuild_followup_alerts()

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

    def _rebuild_followup_alerts(self):
        self._clear_layout_from(self._followup_lay, self._fu_items_start)
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