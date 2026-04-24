from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QProgressBar, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QVariantAnimation, Signal, QSize
from PySide6.QtGui import QColor

from utils.icon_manager import btn_icon_primary, btn_icon_secondary, btn_icon_muted, get_icon


class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 6)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(self.shadow)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(200)
        self._anim.valueChanged.connect(lambda v: (
            self.shadow.setBlurRadius(20 + int(v)),
            self.shadow.setOffset(0, 6 + int(v / 2))
        ))

    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(0)
        self._anim.setEndValue(12)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(12)
        self._anim.setEndValue(0)
        self._anim.start()
        super().leaveEvent(event)


class KPICard(AnimatedCard):
    def __init__(self, title, value, trend_text, trend_type="success", icon_name=None):
        super().__init__()
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

        lbl_val = QLabel(value)
        lbl_val.setObjectName("kpiValue")
        layout.addWidget(lbl_val)

        lbl_trend = QLabel(trend_text)
        badge_map = {
            "success": "badgeSuccess",
            "danger":  "badgeDanger",
            "warning": "badgeWarning",
            "gold":    "badgeGold",
        }
        lbl_trend.setObjectName(badge_map.get(trend_type, "badgeInfo"))
        layout.addWidget(lbl_trend)
        layout.addStretch()


class ActivityItem(QWidget):
    def __init__(self, title, desc, time, dot_color="#22C55E"):
        super().__init__()
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
    def __init__(self, name, date, pax, status, status_type="success"):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(3)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #F9FAFB;")
        date_lbl = QLabel(f"{date}  ·  {pax} pax")
        date_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        left.addWidget(name_lbl)
        left.addWidget(date_lbl)
        layout.addLayout(left)
        layout.addStretch()

        badge = QLabel(status)
        badge_map = {"success": "badgeSuccess", "warning": "badgeWarning", "danger": "badgeDanger"}
        badge.setObjectName(badge_map.get(status_type, "badgeInfo"))
        layout.addWidget(badge)


class InventoryAlertItem(QWidget):
    def __init__(self, item, current, minimum):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)

        name_lbl = QLabel(item)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #F9FAFB;")
        layout.addWidget(name_lbl)
        layout.addStretch()

        stock_lbl = QLabel(f"{current} / {minimum} min")
        stock_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(stock_lbl)

        badge = QLabel("Low Stock")
        badge.setObjectName("badgeDanger")
        layout.addWidget(badge)


class DashboardPage(QWidget):
    new_booking_requested = Signal()

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(24)

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

        self.btn_new = QPushButton("  New Booking")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.setIcon(btn_icon_primary("plus"))
        self.btn_new.setIconSize(QSize(15, 15))
        self.btn_new.clicked.connect(self.new_booking_requested.emit)

        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(self.btn_new)
        header_row.addLayout(btn_layout)
        lay.addLayout(header_row)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        kpi_row.addWidget(KPICard("Today's Events",    "4",        "↑ 2 from yesterday",     "success", "calendar"))
        kpi_row.addWidget(KPICard("Pending Bookings",  "12",       "Requires review",         "warning", "orders"))
        kpi_row.addWidget(KPICard("Weekly Revenue",    "₱ 12,450", "↑ 8.5% from last week",  "success", "trending-up"))
        kpi_row.addWidget(KPICard("Unpaid Invoices",   "₱ 4,200",  "3 invoices overdue",      "danger",  "billing"))
        lay.addLayout(kpi_row)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        cap_card = AnimatedCard()
        cap_lay = QVBoxLayout(cap_card)
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
        pax_lbl = QLabel('<span style="font-size:28px;font-weight:800;color:#F9FAFB;">45</span>'
                         '<span style="color:#6B7280;font-size:16px;"> / 600</span>')
        cap_head.addWidget(pax_lbl)
        cap_lay.addLayout(cap_head)

        prog = QProgressBar()
        prog.setRange(0, 600)
        prog.setValue(45)
        prog.setFixedHeight(10)
        cap_lay.addWidget(prog)

        cap_foot = QHBoxLayout()
        cap_foot.addWidget(QLabel('<span style="color:#F59E0B;font-weight:700;font-size:12px;">8% Capacity</span>'))
        cap_foot.addStretch()
        cap_foot.addWidget(QLabel('<span style="color:#6B7280;font-size:12px;">555 slots remaining</span>'))
        cap_lay.addLayout(cap_foot)

        events_card = AnimatedCard()
        ev_lay = QVBoxLayout(events_card)
        ev_lay.setContentsMargins(24, 24, 24, 24)
        ev_lay.setSpacing(0)

        ev_head = QHBoxLayout()
        ev_title = QLabel("Upcoming Events")
        ev_title.setObjectName("h3")
        ev_head.addWidget(ev_title)
        ev_head.addStretch()
        ev_lay.addLayout(ev_head)

        ev_div = QFrame()
        ev_div.setObjectName("divider")
        ev_lay.addWidget(ev_div)
        ev_lay.addSpacing(4)

        for name, date, pax, status, stype in [
            ("Santos Wedding",       "Apr 26, 2026", "200", "Confirmed", "success"),
            ("Reyes Birthday Party", "Apr 27, 2026", "80",  "Pending",   "warning"),
            ("Cruz Corporate",       "Apr 30, 2026", "150", "Confirmed", "success"),
        ]:
            ev_lay.addWidget(EventItem(name, date, pax, status, stype))
            sep = QFrame()
            sep.setObjectName("divider")
            ev_lay.addWidget(sep)

        ev_lay.addStretch()

        mid_row.addWidget(cap_card, 1)
        mid_row.addWidget(events_card, 1)
        lay.addLayout(mid_row)

        bot_row = QHBoxLayout()
        bot_row.setSpacing(16)

        act_card = AnimatedCard()
        act_lay = QVBoxLayout(act_card)
        act_lay.setContentsMargins(24, 24, 24, 24)
        act_lay.setSpacing(0)

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
        act_lay.addLayout(act_head)

        act_div = QFrame()
        act_div.setObjectName("divider")
        act_lay.addWidget(act_div)

        act_lay.addWidget(ActivityItem(
            "Wedding Reception Confirmed",
            "Mr. & Mrs. Santos finalized menu for 200 pax.",
            "10 mins ago", "#22C55E"))
        act_lay.addWidget(ActivityItem(
            "Payment Pending",
            "Invoice #BKG-002 requires 50% downpayment.",
            "1 hr ago", "#EF4444"))
        act_lay.addWidget(ActivityItem(
            "New Booking Request",
            "Cruz Corporate event inquiry submitted.",
            "3 hrs ago", "#3B82F6"))
        act_lay.addStretch()

        inv_card = AnimatedCard()
        inv_lay = QVBoxLayout(inv_card)
        inv_lay.setContentsMargins(24, 24, 24, 24)
        inv_lay.setSpacing(0)

        inv_head = QHBoxLayout()
        inv_title = QLabel("Inventory Alerts")
        inv_title.setObjectName("h3")
        inv_head.addWidget(inv_title)
        inv_head.addStretch()
        alert_badge = QLabel("3 Low")
        alert_badge.setObjectName("badgeDanger")
        inv_head.addWidget(alert_badge)
        inv_lay.addLayout(inv_head)

        inv_div = QFrame()
        inv_div.setObjectName("divider")
        inv_lay.addWidget(inv_div)

        for item, current, minimum in [
            ("Chicken (kg)",   "8",  "20"),
            ("Rice (kg)",      "15", "30"),
            ("Cooking Oil (L)","4",  "10"),
        ]:
            inv_lay.addWidget(InventoryAlertItem(item, current, minimum))
            sep = QFrame()
            sep.setObjectName("divider")
            inv_lay.addWidget(sep)

        inv_lay.addStretch()

        bot_row.addWidget(act_card, 3)
        bot_row.addWidget(inv_card, 2)
        lay.addLayout(bot_row)

        scroll.setWidget(content)
        root.addWidget(scroll)
