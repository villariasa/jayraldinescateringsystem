# ========================================================
# main.py - COMPLETE FIXED VERSION (PySide6 Dashboard)
# ✅ Light theme + Fullscreen maximized + BOTH buttons visible side-by-side
# ✅ + New Booking is now RED and RIGHT NEXT to Export Report
# ========================================================
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QProgressBar, QScrollArea, QGraphicsDropShadowEffect,
    QStackedWidget
)
from PySide6.QtCore import Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor
import sys

# Import your real booking page
from ui.booking_page import BookingPage   # ← must be in same folder


# ==========================================================
# CUSTOM WIDGETS
# ==========================================================
class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(25)
        self.shadow.setOffset(0, 10)
        self.shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(self.shadow)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(220)
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
        if hasattr(self, "shadow") and self.shadow:
            self.shadow.setBlurRadius(25 + int(value))
            self.shadow.setOffset(0, 10 + int(value / 2))

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(15)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(15)
        self.anim.setEndValue(0)
        self.anim.start()
        super().leaveEvent(event)


class KPICard(AnimatedCard):
    def __init__(self, title, value, trend_text, trend_type="success"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(8)

        lbl_title = QLabel(title.upper())
        lbl_title.setObjectName("kpiLabel")

        lbl_val = QLabel(value)
        lbl_val.setObjectName("kpiValue")

        lbl_trend = QLabel(trend_text)
        if trend_type == "success":
            lbl_trend.setObjectName("badgeSuccess")
        elif trend_type == "danger":
            lbl_trend.setObjectName("badgeDanger")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_trend)
        layout.addStretch()


class ActivityItem(QWidget):
    def __init__(self, icon, title, desc, time, color="#10B981"):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(16)

        indicator = QFrame()
        indicator.setFixedSize(42, 42)
        indicator.setStyleSheet(f"background-color: {color}15; border-radius: 21px;")
        ind_lay = QVBoxLayout(indicator)
        ind_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"font-size: 18px; color: {color};")
        ind_lay.addWidget(icon_lbl)
        layout.addWidget(indicator)

        vbox = QVBoxLayout()
        vbox.setSpacing(4)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-weight: 700; font-size: 14.5px; color: #0F172A;")
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color: #64748B; font-size: 13px;")
        d_lbl.setWordWrap(True)
        vbox.addWidget(t_lbl)
        vbox.addWidget(d_lbl)
        layout.addLayout(vbox)
        layout.addStretch()

        time_lbl = QLabel(time)
        time_lbl.setStyleSheet("color: #94A3B8; font-size: 12.5px;")
        layout.addWidget(time_lbl)


# ==========================================================
# DASHBOARD PAGE
# ==========================================================
class DashboardPage(QWidget):
    new_booking_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #F8FAFC;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: #F8FAFC; border: none; }")

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #F8FAFC;")
        self.layout = QVBoxLayout(content_widget)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(32)

        # ==================== HEADER ROW (FIXED - both buttons visible) ====================
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        title = QLabel("Welcome back, Admin 👋")
        title.setObjectName("h1")
        sub = QLabel("Here's what's happening at Jayraldine's Catering today.")
        sub.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        header_row.addLayout(v_title)

        header_row.addStretch()

        # Buttons container - guarantees they stay side-by-side
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)          # space between Export and New Booking

        btn_export = QPushButton("Export Report")
        btn_export.setObjectName("secondaryButton")
        btn_export.setMinimumWidth(140)

        self.btn_new = QPushButton("+ New Booking")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.setMinimumWidth(160)
        self.btn_new.clicked.connect(self.new_booking_requested.emit)

        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(self.btn_new)

        header_row.addLayout(btn_layout)
        self.layout.addLayout(header_row)

        # ==================== KPI ROW ====================
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(24)
        kpi_row.addWidget(KPICard("Today's Events", "4", "↑ 2 more than yesterday", "success"))
        kpi_row.addWidget(KPICard("Pending Bookings", "12", "! Requires review", "danger"))
        kpi_row.addWidget(KPICard("Weekly Revenue", "₱ 12,450", "↑ 8.5% from last week", "success"))
        self.layout.addLayout(kpi_row)

        # ==================== DAILY CAPACITY TRACKER ====================
        cap_card = AnimatedCard()
        cap_lay = QVBoxLayout(cap_card)
        cap_lay.setContentsMargins(32, 32, 32, 32)
        cap_lay.setSpacing(18)

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

        pax_lbl = QLabel('<span style="font-size:32px;font-weight:800;">45</span> <span style="color:#64748B;font-size:20px;">/ 600 PAX</span>')
        cap_head.addWidget(pax_lbl, alignment=Qt.AlignBottom)
        cap_lay.addLayout(cap_head)

        prog = QProgressBar()
        prog.setRange(0, 600)
        prog.setValue(45)
        prog.setFixedHeight(14)
        cap_lay.addWidget(prog)

        cap_foot = QHBoxLayout()
        cap_foot.addWidget(QLabel('<span style="color:#E53935;font-weight:700;font-size:13px;">8% Capacity Reached</span>'))
        cap_foot.addStretch()
        cap_foot.addWidget(QLabel('<span style="color:#64748B;font-weight:600;font-size:13px;">555 slots remaining today</span>'))
        cap_lay.addLayout(cap_foot)
        self.layout.addWidget(cap_card)

        # ==================== RECENT ACTIVITY ====================
        act_card = AnimatedCard()
        act_lay = QVBoxLayout(act_card)
        act_lay.setContentsMargins(32, 24, 32, 32)
        act_lay.setSpacing(8)

        act_head = QHBoxLayout()
        act_title = QLabel("Recent Activity")
        act_title.setObjectName("h2")
        act_head.addWidget(act_title)
        act_head.addStretch()
        btn_view = QPushButton("View all logs")
        btn_view.setObjectName("ghostButton")
        act_head.addWidget(btn_view)
        act_lay.addLayout(act_head)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #F1F5F9;")
        act_lay.addWidget(div)

        act_lay.addWidget(ActivityItem("✓", "Wedding Reception Confirmed",
                                       "Mr. & Mrs. Smith finalized their menu selection for 150 pax.",
                                       "10 mins ago", "#10B981"))
        act_lay.addWidget(ActivityItem("!", "Payment Pending",
                                       "Invoice #BKG-002 requires a 50% downpayment.",
                                       "1 hour ago", "#EF4444"))
        act_lay.addStretch()
        self.layout.addWidget(act_card)
        self.layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)


# ==========================================================
# SIDEBAR
# ==========================================================
class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo
        logo_area = QWidget()
        logo_area.setObjectName("logoArea")
        logo_lay = QHBoxLayout(logo_area)
        logo_lay.setContentsMargins(20, 30, 20, 20)

        logo_icon = QLabel("🍰")
        logo_icon.setObjectName("logoIcon")
        logo_icon.setFixedSize(48, 48)
        logo_icon.setAlignment(Qt.AlignCenter)

        logo_text = QLabel("Jayraldine's\nCATERING")
        logo_text.setObjectName("logoText")

        logo_lay.addWidget(logo_icon)
        logo_lay.addWidget(logo_text)
        layout.addWidget(logo_area)

        # Navigation
        self.btn_dashboard = QPushButton("📊 Dashboard")
        self.btn_bookings = QPushButton("📅 Bookings")
        self.btn_calendar = QPushButton("🗓 Calendar")
        self.btn_reports = QPushButton("📊 Reports")

        for btn in (self.btn_dashboard, self.btn_bookings, self.btn_calendar, self.btn_reports):
            btn.setCheckable(True)
            layout.addWidget(btn)

        self.btn_dashboard.setChecked(True)
        layout.addStretch()

        # User profile
        user_area = QFrame()
        user_area.setObjectName("userProfileArea")
        user_lay = QHBoxLayout(user_area)
        user_lay.setContentsMargins(16, 16, 16, 16)

        avatar = QLabel("A")
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(35, 35)
        avatar.setAlignment(Qt.AlignCenter)

        info = QVBoxLayout()
        info.addWidget(QLabel("Admin User"))
        email = QLabel("admin@jayraldines.com")
        email.setStyleSheet("font-size:12px; color:#94a3b8;")
        info.addWidget(email)

        user_lay.addWidget(avatar)
        user_lay.addLayout(info)
        layout.addWidget(user_area)


# ==========================================================
# MAIN WINDOW
# ==========================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jayraldine's Catering | Admin Dashboard")

        central = QWidget()
        central.setStyleSheet("background-color: #F8FAFC;")
        self.setCentralWidget(central)

        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self.sidebar = Sidebar()
        main_lay.addWidget(self.sidebar)

        self.stacked = QStackedWidget()
        self.dashboard = DashboardPage()
        self.booking_page = BookingPage()

        self.stacked.addWidget(self.dashboard)
        self.stacked.addWidget(self.booking_page)
        main_lay.addWidget(self.stacked)

        # Connect buttons
        self.dashboard.new_booking_requested.connect(self.open_booking_page)
        self.sidebar.btn_bookings.clicked.connect(self.open_booking_page)

        # Load your original QSS
        try:
            with open("style.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("⚠️ style.qss not found – using default styling")

        # FULL SCREEN + MAXIMIZED
        self.showMaximized()

    def open_booking_page(self):
        self.stacked.setCurrentIndex(1)


# ==========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    sys.exit(app.exec())