from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QPushButton, QProgressBar, QScrollArea, 
                               QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import Qt, QVariantAnimation, QAbstractAnimation
from PySide6.QtGui import QColor

# ==========================================================
# CUSTOM WIDGET: Animated Hover Card (The "SaaS" Magic)
# ==========================================================
class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        
        # Setup initial soft shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(QColor(0, 0, 0, 15)) # 15 opacity = very soft
        self.setGraphicsEffect(self.shadow)

        # Setup Animation for Hover State
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250) # 250ms smooth transition
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
        # Value dictates both blur radius and Y offset for a "lifting" effect
        self.shadow.setBlurRadius(15 + value)
        self.shadow.setOffset(0, 4 + (value / 2))
        self.shadow.setColor(QColor(0, 0, 0, 15 + int(value / 3)))

    def enterEvent(self, event):
        # Mouse enters: Lift the card
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(15)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Mouse leaves: Settle back down
        self.anim.stop()
        self.anim.setStartValue(15)
        self.anim.setEndValue(0)
        self.anim.start()
        super().leaveEvent(event)

# ==========================================================
# HELPER COMPONENTS
# ==========================================================
class KPICard(AnimatedCard):
    def __init__(self, title, value, trend_text, trend_type="success"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("kpiLabel")
        
        lbl_val = QLabel(value)
        lbl_val.setObjectName("kpiValue")
        
        lbl_trend = QLabel(trend_text)
        if trend_type == "success":
            lbl_trend.setObjectName("badgeSuccess")
        elif trend_type == "danger":
            lbl_trend.setObjectName("badgeDanger")
        else:
            lbl_trend.setObjectName("badgeWarning")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_trend)
        layout.addStretch()

class ActivityItem(QWidget):
    def __init__(self, icon, title, desc, time, color="#10B981"):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(16)

        # Custom dot/icon indicator
        indicator = QFrame()
        indicator.setFixedSize(40, 40)
        indicator.setStyleSheet(f"background-color: {color}20; border-radius: 20px;") # 20 is hex for slight transparency
        ind_lay = QVBoxLayout(indicator)
        ind_lay.setContentsMargins(0,0,0,0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color}; background: transparent;")
        ind_lay.addWidget(icon_lbl)
        layout.addWidget(indicator)

        # Text VBox
        vbox = QVBoxLayout()
        vbox.setSpacing(4)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #0F172A;")
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
        vbox.addWidget(t_lbl)
        vbox.addWidget(d_lbl)
        layout.addLayout(vbox)
        layout.addStretch()

        # Time
        time_lbl = QLabel(time)
        time_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        layout.addWidget(time_lbl)

# ==========================================================
# MAIN DASHBOARD VIEW
# ==========================================================
class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Smooth Scroll Area ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(32) # Generous web-like spacing

        # --- 1. HEADER ROW ---
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.setSpacing(4)
        title = QLabel("Welcome back, Admin 👋")
        title.setObjectName("h1")
        sub = QLabel("Here's what's happening at Jayraldine's Catering today.")
        sub.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        header_row.addLayout(v_title)
        
        header_row.addStretch()
        btn_export = QPushButton("Export Report")
        btn_export.setObjectName("secondaryButton")
        btn_new = QPushButton("+ New Booking")
        btn_new.setObjectName("primaryButton")
        header_row.addWidget(btn_export)
        header_row.addWidget(btn_new)
        self.layout.addLayout(header_row)

        # --- 2. KPI CARDS ROW ---
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(24)
        kpi_row.addWidget(KPICard("Today's Events", "4", "↑ 2 more than yesterday", "success"))
        kpi_row.addWidget(KPICard("Pending Bookings", "12", "↓ Requires review", "danger"))
        kpi_row.addWidget(KPICard("Weekly Revenue", "₱ 12,450", "↑ 8.5% from last week", "success"))
        self.layout.addLayout(kpi_row)

        # --- 3. CAPACITY TRACKER (Wide Card) ---
        cap_card = AnimatedCard()
        cap_lay = QVBoxLayout(cap_card)
        cap_lay.setContentsMargins(32, 32, 32, 32)
        cap_lay.setSpacing(16)
        
        cap_head = QHBoxLayout()
        cap_v = QVBoxLayout()
        cap_title = QLabel("Daily Capacity Tracker")
        cap_title.setObjectName("h2")
        cap_sub = QLabel("Monitor pax booked today to manage kitchen workload.")
        cap_sub.setObjectName("subtitle")
        cap_v.addWidget(cap_title)
        cap_v.addWidget(cap_sub)
        cap_head.addLayout(cap_v)
        cap_head.addStretch()
        
        pax_lbl = QLabel("<span style='font-size: 32px; font-weight: 800;'>45</span> <span style='color: #64748B; font-size: 16px;'>/ 600 PAX</span>")
        cap_head.addWidget(pax_lbl, alignment=Qt.AlignBottom)
        cap_lay.addLayout(cap_head)

        prog = QProgressBar()
        prog.setRange(0, 600)
        prog.setValue(45)
        cap_lay.addWidget(prog)
        
        cap_foot = QHBoxLayout()
        cap_foot.addWidget(QLabel("<span style='color: #E53935; font-weight: 700; font-size: 13px;'>8% Capacity Reached</span>"))
        cap_foot.addStretch()
        cap_foot.addWidget(QLabel("<span style='color: #64748B; font-weight: 600; font-size: 13px;'>555 slots remaining today</span>"))
        cap_lay.addLayout(cap_foot)
        
        self.layout.addWidget(cap_card)

        # --- 4. RECENT ACTIVITY LIST ---
        act_card = AnimatedCard()
        act_lay = QVBoxLayout(act_card)
        act_lay.setContentsMargins(32, 24, 32, 32)
        act_lay.setSpacing(8)
        
        act_head = QHBoxLayout()
        act_title = QLabel("Recent Activity")
        act_title.setObjectName("h2")
        act_head.addWidget(act_title)
        act_head.addStretch()
        btn_view_all = QPushButton("View all logs")
        btn_view_all.setObjectName("ghostButton")
        act_head.addWidget(btn_view_all)
        act_lay.addLayout(act_head)

        # Divider line
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #F1F5F9; margin-bottom: 8px;")
        act_lay.addWidget(div)

        act_lay.addWidget(ActivityItem("✓", "Wedding Reception Confirmed", "Mr. & Mrs. Smith finalized their menu selection for 150 pax.", "10 mins ago", "#10B981")) # Emerald
        act_lay.addWidget(ActivityItem("!", "Payment Pending", "Invoice #BKG-002 requires a 50% downpayment.", "1 hour ago", "#F59E0B")) # Amber
        act_lay.addWidget(ActivityItem("+$", "Payment Received", "₱ 45,000 received via Bank Transfer for TechCorp Inc.", "3 hours ago", "#3B82F6")) # Blue
        
        act_lay.addStretch()
        self.layout.addWidget(act_card)
        self.layout.addStretch()

        # Wrap in scroll area
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)