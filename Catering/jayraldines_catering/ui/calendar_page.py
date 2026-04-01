import calendar
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QPushButton, QGridLayout, QScrollArea, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QVariantAnimation
from PySide6.QtGui import QColor

def create_shadow():
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(15)
    shadow.setColor(QColor(0, 0, 0, 15))
    shadow.setOffset(0, 4)
    return shadow

# ==========================================================
# CUSTOM WIDGET: Animated Hover Card (From Dashboard)
# ==========================================================
class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.setGraphicsEffect(create_shadow())
        
        # We need to access the effect for animation
        self.shadow = self.graphicsEffect()

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250) 
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
        # Prevent crash if shadow not ready
        if not hasattr(self, "shadow") or self.shadow is None:
            return

        try:
            self.shadow.setBlurRadius(15 + value)
            self.shadow.setOffset(0, 4 + (value / 2))
            self.shadow.setColor(QColor(0, 0, 0, 15 + int(value / 3)))
        except RuntimeError:
            # Handles cases where Qt internally deleted the effect
            return
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

# --- HELPER: Clickable Day Cell ---
class DayCell(QFrame):
    clicked = Signal(int) 

    def __init__(self, day_num, is_current_month=True):
        super().__init__()
        self.day_num = day_num
        self.is_current_month = is_current_month
        
        # Responsive sizing instead of fixed
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(4)

        if not is_current_month or day_num == 0:
            # Empty filler cell
            self.setStyleSheet("background: transparent; border: none;")
        else:
            self.setObjectName("dayCell")
            self.setProperty("active", False)
            
            # Date Number
            self.lbl_day = QLabel(str(day_num))
            self.lbl_day.setObjectName("dayNumber")
            self.layout.addWidget(self.lbl_day, alignment=Qt.AlignTop | Qt.AlignLeft)

            # Placeholders for tags
            self.layout.addStretch()

    def set_data(self, total_pax, booking_count):
        if not self.is_current_month or self.day_num == 0 or total_pax == 0:
            return

        # 1. Pax Tag
        pax_tag = QLabel(f"{total_pax} Pax")
        pax_tag.setAlignment(Qt.AlignCenter)
        
        if total_pax >= 600:
            pax_tag.setStyleSheet("background-color: #fee2e2; color: #b91c1c; font-weight: 700; font-size: 11px; padding: 4px; border-radius: 4px;")
        elif total_pax >= 400:
            pax_tag.setStyleSheet("background-color: #fef9c3; color: #854d0e; font-weight: 700; font-size: 11px; padding: 4px; border-radius: 4px;")
        else:
            pax_tag.setStyleSheet("background-color: #dcfce7; color: #166534; font-weight: 700; font-size: 11px; padding: 4px; border-radius: 4px;")
            
        self.layout.insertWidget(1, pax_tag)

        # 2. Booking Count
        count_lbl = QLabel(f"{booking_count} Booking{'s' if booking_count > 1 else ''}")
        count_lbl.setObjectName("bookingCount")
        count_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600;")
        self.layout.insertWidget(2, count_lbl)

    def mousePressEvent(self, event):
        if self.is_current_month and self.day_num != 0:
            self.clicked.emit(self.day_num)
            super().mousePressEvent(event)

# --- HELPER: Schedule Item Card ---
class ScheduleCard(AnimatedCard):
    def __init__(self, event_name, pax, time, location):
        super().__init__()
        # Override border to have the red accent
        self.setStyleSheet("QFrame#card { border-left: 4px solid #e53935; border-radius: 8px; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        top_row = QHBoxLayout()
        title = QLabel(event_name)
        title.setStyleSheet("font-weight: 700; font-size: 14px; color: #0F172A;")
        pax_lbl = QLabel(f"👥 {pax}")
        pax_lbl.setStyleSheet("color: #64748B; font-weight: 600; font-size: 12px; background: #F1F5F9; padding: 4px 8px; border-radius: 4px;")
        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addWidget(pax_lbl)
        layout.addLayout(top_row)
        
        time_lbl = QLabel(f"🕒 {time}")
        time_lbl.setStyleSheet("color: #64748B; font-weight: 500; font-size: 12px; margin-top: 8px;")
        loc_lbl = QLabel(f"📍 {location}")
        loc_lbl.setStyleSheet("color: #64748B; font-weight: 500; font-size: 12px;")
        layout.addWidget(time_lbl)
        layout.addWidget(loc_lbl)

# --- MAIN PAGE ---
class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(32)

        # Determine current real-world date
        today = datetime.now()
        self.current_year = today.year
        self.current_month = today.month

        # --- Top Header ---
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.setSpacing(4)
        title = QLabel("Booking Calendar")
        title.setObjectName("h1")
        sub = QLabel("Manage catering schedule and daily capacity limits (Max: 600 Pax).")
        sub.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        header_row.addLayout(v_title)
        
        header_row.addStretch()
        btn_add = QPushButton("+ Add New Booking")
        btn_add.setObjectName("primaryButton")
        header_row.addWidget(btn_add)
        main_layout.addLayout(header_row)

        # --- Main Split Area ---
        split_layout = QHBoxLayout()
        split_layout.setSpacing(24)

        # ==========================================
        # LEFT: CALENDAR GRID
        # ==========================================
        cal_container = QFrame()
        cal_container.setObjectName("card")
        cal_container.setGraphicsEffect(create_shadow())
        cal_layout = QVBoxLayout(cal_container)
        cal_layout.setContentsMargins(24, 24, 24, 24)

        # Calendar Header & Controls
        cal_head = QHBoxLayout()
        self.month_lbl = QLabel()
        self.month_lbl.setObjectName("h2")
        cal_head.addWidget(self.month_lbl)
        
        cal_head.addStretch()
        legend = QLabel("🟢 Available  |  🟡 Near Full (400+)  |  🔴 Fully Booked (600)")
        legend.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B; margin-right: 24px;")
        cal_head.addWidget(legend)

        # Dynamic Nav Buttons
        btn_prev = QPushButton("◀")
        btn_today = QPushButton("Today")
        btn_next = QPushButton("▶")
        
        btn_prev.setObjectName("secondaryButton")
        btn_today.setObjectName("secondaryButton")
        btn_next.setObjectName("secondaryButton")
        
        btn_prev.clicked.connect(self.go_prev_month)
        btn_today.clicked.connect(self.go_today)
        btn_next.clicked.connect(self.go_next_month)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)
        nav_layout.addWidget(btn_prev)
        nav_layout.addWidget(btn_today)
        nav_layout.addWidget(btn_next)
        cal_head.addLayout(nav_layout)
        
        cal_layout.addLayout(cal_head)
        cal_layout.addSpacing(16)

        # Calendar Grid Layout
        self.grid = QGridLayout()
        self.grid.setSpacing(0)
        
        # Day Headers
        days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        for col, day in enumerate(days):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: 800; color: #64748B; font-size: 12px; padding: 10px 0px;")
            self.grid.addWidget(lbl, 0, col)

        # Mock DB structured by (Year, Month, Day)
        self.mock_db = {
            (self.current_year, self.current_month, 5): [{"name": "Private Party", "pax": 150, "time": "07:00 PM", "loc": "Resort Villa"}],
            (self.current_year, self.current_month, 12): [{"name": "Corporate Lunch", "pax": 300, "time": "12:00 PM", "loc": "Tech Park"}],
            (self.current_year, self.current_month, 18): [
                {"name": "Wedding Reception", "pax": 350, "time": "10:00 AM", "loc": "Grand Hall"},
                {"name": "Birthday Bash", "pax": 250, "time": "04:00 PM", "loc": "Beach Club"}
            ],
            (self.current_year, self.current_month, 25): [{"name": "Gala Dinner", "pax": 500, "time": "07:00 PM", "loc": "City Convention Center"}]
        }

        cal_layout.addLayout(self.grid)
        split_layout.addWidget(cal_container, 7) # Takes 70% space

        # ==========================================
        # RIGHT: SIDE PANEL (Schedule Details)
        # ==========================================
        self.side_panel = QFrame()
        self.side_panel.setObjectName("sidePanel")
        self.side_panel.setGraphicsEffect(create_shadow())
        self.side_panel.setFixedWidth(340)
        self.side_panel.setVisible(False) 
        
        sp_layout = QVBoxLayout(self.side_panel)
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.setSpacing(0)

        # Red Header Box
        self.sp_header = QFrame()
        self.sp_header.setObjectName("panelHeader")
        sph_layout = QVBoxLayout(self.sp_header)
        sph_layout.setContentsMargins(24, 24, 24, 24)
        
        close_row = QHBoxLayout()
        self.lbl_panel_date = QLabel("Date")
        self.lbl_panel_date.setStyleSheet("color: white; font-size: 20px; font-weight: 800;")
        close_row.addWidget(self.lbl_panel_date)
        
        btn_close = QPushButton("✕")
        btn_close.setStyleSheet("background: transparent; color: white; font-size: 18px; border: none; font-weight: bold;")
        btn_close.clicked.connect(lambda: self.side_panel.setVisible(False))
        btn_close.setCursor(Qt.PointingHandCursor)
        close_row.addWidget(btn_close, alignment=Qt.AlignTop)
        sph_layout.addLayout(close_row)
        
        # Capacity Box
        cap_box = QFrame()
        cap_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.15); border-radius: 8px; margin-top: 15px;")
        cap_layout = QHBoxLayout(cap_box)
        
        # --- THE FIX: Force RichText and use <br> ---
        self.lbl_capacity = QLabel()
        self.lbl_capacity.setTextFormat(Qt.RichText)
        self.lbl_capacity.setText("TOTAL CAPACITY<br><span style='font-size: 28px; font-weight: 800;'>0</span> / 600 Pax")
        self.lbl_capacity.setStyleSheet("color: white; font-size: 12px; font-weight: 600;")
        
        cap_layout.addWidget(self.lbl_capacity)
        sph_layout.addWidget(cap_box)
        
        sp_layout.addWidget(self.sp_header)

        # Schedule Scroll Area
        sp_body = QWidget()
        self.sp_body_layout = QVBoxLayout(sp_body)
        self.sp_body_layout.setContentsMargins(20, 24, 20, 24)
        self.sp_body_layout.setSpacing(16)
        
        lbl_ds = QLabel("DAILY SCHEDULE")
        lbl_ds.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;")
        self.sp_body_layout.addWidget(lbl_ds)

        self.cards_container = QVBoxLayout()
        self.cards_container.setSpacing(12)
        self.sp_body_layout.addLayout(self.cards_container)
        self.sp_body_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(sp_body)
        sp_layout.addWidget(scroll)

        # Bottom Button
        btn_manage = QPushButton("Manage Day Schedule")
        btn_manage.setStyleSheet("background-color: #FEF2F2; color: #DC2626; font-weight: 700; padding: 14px; border-radius: 8px; border: 1px solid #FECACA; margin: 20px;")
        btn_manage.setCursor(Qt.PointingHandCursor)
        sp_layout.addWidget(btn_manage)

        split_layout.addWidget(self.side_panel, 3) 
        main_layout.addLayout(split_layout)

        # Initial Render
        self.cells = []
        self.render_calendar()

    # ==========================================
    # CALENDAR LOGIC
    # ==========================================
    def go_prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.render_calendar()

    def go_next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.render_calendar()

    def go_today(self):
        today = datetime.now()
        self.current_year = today.year
        self.current_month = today.month
        self.render_calendar()

    def render_calendar(self):
        # Update Header Label
        month_name = calendar.month_name[self.current_month]
        self.month_lbl.setText(f"{month_name} {self.current_year}")

        # Hide side panel on month change
        self.side_panel.setVisible(False)

        # Clear existing cells (skip row 0 headers)
        for cell in self.cells:
            self.grid.removeWidget(cell)
            cell.deleteLater()
        self.cells.clear()

        # Generate new month grid
        calendar.setfirstweekday(calendar.SUNDAY)
        month_days = calendar.monthcalendar(self.current_year, self.current_month)

        row = 1
        for week in month_days:
            for col, day_num in enumerate(week):
                cell = DayCell(day_num, is_current_month=(day_num != 0))
                
                # Check for mock data
                db_key = (self.current_year, self.current_month, day_num)
                if db_key in self.mock_db:
                    events = self.mock_db[db_key]
                    total_pax = sum(e["pax"] for e in events)
                    cell.set_data(total_pax, len(events))

                cell.clicked.connect(self.on_day_clicked)
                self.grid.addWidget(cell, row, col)
                self.cells.append(cell)
            row += 1

    def on_day_clicked(self, day_num):
        # Reset visual states
        for cell in self.cells:
            if cell.day_num != 0:
                cell.setProperty("active", False)
                cell.style().unpolish(cell)
                cell.style().polish(cell)

        # Highlight clicked cell
        clicked_cell = next((c for c in self.cells if c.day_num == day_num), None)
        if clicked_cell:
            clicked_cell.setProperty("active", True)
            clicked_cell.style().unpolish(clicked_cell)
            clicked_cell.style().polish(clicked_cell)

        # Update Side Panel
        month_name = calendar.month_name[self.current_month]
        self.lbl_panel_date.setText(f"{month_name} {day_num}, {self.current_year}")
        
        # Clear existing cards
        for i in reversed(range(self.cards_container.count())): 
            widget = self.cards_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Load events
        db_key = (self.current_year, self.current_month, day_num)
        if db_key in self.mock_db:
            events = self.mock_db[db_key]
            total_pax = sum(e["pax"] for e in events)
            
            # --- THE FIX: Force RichText and use <br> here too ---
            self.lbl_capacity.setText(f"TOTAL CAPACITY<br><span style='font-size: 28px; font-weight: 800;'>{total_pax}</span> / 600 Pax")
            
            for event in events:
                card = ScheduleCard(event["name"], event["pax"], event["time"], event["loc"])
                self.cards_container.addWidget(card)
        else:
            # --- THE FIX: Empty State ---
            self.lbl_capacity.setText("TOTAL CAPACITY<br><span style='font-size: 28px; font-weight: 800;'>0</span> / 600 Pax")
            empty_lbl = QLabel("No events scheduled for this day.")
            empty_lbl.setStyleSheet("color: #94A3B8; font-style: italic; font-size: 13px;")
            self.cards_container.addWidget(empty_lbl)

        self.side_panel.setVisible(True)