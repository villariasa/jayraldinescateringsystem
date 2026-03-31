from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QPushButton, QProgressBar, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt

# Reusable shadow effect helper
def create_shadow():
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setColor(Qt.gray)
    shadow.setOffset(0, 5)
    return shadow

# --- HELPER COMPONENT: KPI CARD ---
class KPICard(QFrame):
    def __init__(self, title, icon, value, trend_text, is_positive=True):
        super().__init__()
        self.setObjectName("card")
        self.setGraphicsEffect(create_shadow())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header: Title and Icon
        header_layout = QHBoxLayout()
        title_label = QLabel(title.upper())
        title_label.setObjectName("kpiTitle")
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px; color: #fca311;") # Warning yellow icon
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(icon_label)
        layout.addLayout(header_layout)

        # Large Value
        value_label = QLabel(value)
        value_label.setObjectName("kpiValue")
        layout.addWidget(value_label)

        # Trend text
        trend_label = QLabel(trend_text)
        trend_label.setObjectName("trendPositive" if is_positive else "trendNegative")
        layout.addWidget(trend_label)

# --- HELPER COMPONENT: ACTIVITY ITEM ---
class ActivityItem(QFrame):
    def __init__(self, icon, title, desc, time, icon_color="#17bb84"):
        super().__init__()
        self.setStyleSheet("border: none; padding: 0px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(15)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 18px; color: {icon_color};")
        layout.addWidget(icon_label)

        # Vbox for title/desc
        details = QVBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setObjectName("activityItemTitle")
        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("activityItemDesc")
        details.addWidget(title_lbl)
        details.addWidget(desc_lbl)
        details.setSpacing(2)
        layout.addLayout(details)

        layout.addStretch()

        # Time
        time_lbl = QLabel(time)
        time_lbl.setObjectName("activityTime")
        layout.addWidget(time_lbl)

# --- MAIN DASHBOARD PAGE ---
class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # --- ROW 1: Welcome Card Header ---
        welcome_card = QFrame()
        welcome_card.setObjectName("card")
        welcome_card.setGraphicsEffect(create_shadow())
        welcome_layout = QHBoxLayout(welcome_card)
        welcome_layout.setContentsMargins(20, 20, 20, 20)

        welcome_vbox = QVBoxLayout()
        welcome_title = QLabel("Welcome back, Admin 👋")
        welcome_title.setObjectName("welcomeTitle")
        welcome_sub = QLabel("Here's what's happening at Jayraldine's Catering today.")
        welcome_sub.setObjectName("welcomeSub")
        welcome_vbox.addWidget(welcome_title)
        welcome_vbox.addWidget(welcome_sub)
        welcome_vbox.addStretch()
        welcome_layout.addLayout(welcome_vbox)

        # Buttons on right
        welcome_layout.addStretch()
        export_btn = QPushButton("Export Report")
        export_btn.setObjectName("secondaryButton")
        welcome_layout.addWidget(export_btn)
        
        new_booking_btn = QPushButton("+ New Booking")
        new_booking_btn.setObjectName("primaryButton")
        welcome_layout.addWidget(new_booking_btn)

        layout.addWidget(welcome_card)

        # --- ROW 2: KPI Row ---
        kpi_row_layout = QHBoxLayout()
        kpi_row_layout.setSpacing(20)

        # 1. Today's Events
        kpi1 = KPICard("Today's Events", "📅", "4", "↑ 2 more than yesterday", is_positive=True)
        # 2. Pending Bookings
        kpi2 = KPICard("Pending Bookings", "📋", "12", "↓ Requires review", is_positive=False)
        # 3. Weekly Target (Sample Revenue)
        kpi3 = KPICard("Weekly Target", "⏱️", "₱12,450", "↑ 8% up from last week", is_positive=True)

        kpi_row_layout.addWidget(kpi1)
        kpi_row_layout.addWidget(kpi2)
        kpi_row_layout.addWidget(kpi3)
        layout.addLayout(kpi_row_layout)

        # --- ROW 3: Daily Capacity Tracker Card ---
        capacity_card = QFrame()
        capacity_card.setObjectName("card")
        capacity_card.setGraphicsEffect(create_shadow())
        cap_layout = QVBoxLayout(capacity_card)
        cap_layout.setContentsMargins(20, 20, 20, 20)

        # Row 1: Title and Pax Number
        cap_header_layout = QHBoxLayout()
        cap_details_vbox = QVBoxLayout()
        cap_title = QLabel("Daily Capacity Tracker")
        cap_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        cap_sub = QLabel("Monitor pax booked today to manage kitchen workload.")
        cap_sub.setObjectName("welcomeSub") # Reuse sub style
        cap_details_vbox.addWidget(cap_title)
        cap_details_vbox.addWidget(cap_sub)
        cap_header_layout.addLayout(cap_details_vbox)

        # Pax number right aligned
        cap_header_layout.addStretch()
        pax_lbl = QLabel()
        pax_lbl.setObjectName("capacityValue")
        pax_lbl.setText("<span style='color: #1a1f36; font-size: 32px;'>45</span> <span style='color: #a3acb9; font-weight:normal; font-size:20px;'>/ 600<br>PAX BOOKED</span>")
        pax_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cap_header_layout.addWidget(pax_lbl)
        
        cap_layout.addLayout(cap_header_layout)

        # Row 2: Progress Bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 600)
        progress_bar.setValue(45) # 8%
        progress_bar.setFixedHeight(12)
        cap_layout.addWidget(progress_bar)

        # Row 3: Percentages and remaining slots
        cap_footer_layout = QHBoxLayout()
        cap_percentage = QLabel("8% Capacity")
        cap_percentage.setObjectName("trendPositive") # Use green style
        cap_footer_layout.addWidget(cap_percentage)
        cap_footer_layout.addStretch()
        cap_remaining = QLabel("555 slots remaining today")
        cap_remaining.setObjectName("activityTime") # Use gray time style
        cap_footer_layout.addWidget(cap_remaining)
        cap_layout.addLayout(cap_footer_layout)

        layout.addWidget(capacity_card)

        # --- ROW 4: Recent Activity & Confirmations Card ---
        activity_card = QFrame()
        activity_card.setObjectName("card")
        activity_card.setGraphicsEffect(create_shadow())
        act_layout = QVBoxLayout(activity_card)
        act_layout.setContentsMargins(20, 20, 20, 20)

        # Header Row
        act_header_layout = QHBoxLayout()
        act_title = QLabel("Recent Activity & Confirmations")
        act_title.setObjectName("activityTitle")
        act_header_layout.addWidget(act_title)
        act_header_layout.addStretch()
        log_link = QPushButton("View all logs")
        log_link.setObjectName("logLink")
        act_header_layout.addWidget(log_link)
        act_layout.addLayout(act_header_layout)

        # Activity List
        # 1. Wedding Confirmation (Green)
        item1 = ActivityItem("✅", "Wedding Reception for Mr. & Mrs. Smith", "Confirmed menu selection and final headcount (150 pax)", "10 mins ago")
        # 2. Corporate Lunch (Yellow/Orange)
        item2 = ActivityItem("🟡", "Corporate Lunch - TechCorp Inc.", "Updated booking details for April 22nd", "1 hour ago", icon_color="#fca311")
        
        act_layout.addWidget(item1)
        act_layout.addWidget(item2)
        act_layout.addStretch() # Pushes list up
        
        layout.addWidget(activity_card)