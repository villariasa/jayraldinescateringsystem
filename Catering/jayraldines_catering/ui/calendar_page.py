from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QPushButton, QGridLayout, QScrollArea, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import Qt, Signal

def create_shadow():
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(15)
    shadow.setColor(Qt.gray)
    shadow.setOffset(0, 3)
    return shadow

# --- HELPER: Clickable Day Cell ---
class DayCell(QFrame):
    clicked = Signal(int) # Emits the day number when clicked

    def __init__(self, day_num, is_current_month=True):
        super().__init__()
        self.setObjectName("dayCell")
        self.day_num = day_num
        self.is_current_month = is_current_month
        self.setProperty("active", False)
        
        self.setFixedSize(120, 100) # Fixed size for uniform grid
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(2)

        # Date Number
        self.lbl_day = QLabel(str(day_num))
        self.lbl_day.setObjectName("dayNumber" if is_current_month else "dayDayOff")
        self.layout.addWidget(self.lbl_day, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Placeholders for Pax Tag and Booking Count (Added dynamically later)
        self.layout.addStretch()

    def set_data(self, total_pax, booking_count):
        if not self.is_current_month or total_pax == 0:
            return

        # 1. Pax Tag
        pax_tag = QLabel(f"{total_pax} Pax")
        pax_tag.setAlignment(Qt.AlignCenter)
        
        # Color coding logic based on limits
        if total_pax == 600:
            pax_tag.setStyleSheet("background-color: #fee2e2; color: #b91c1c; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
        elif total_pax >= 400:
            pax_tag.setStyleSheet("background-color: #fef9c3; color: #854d0e; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
        else:
            pax_tag.setStyleSheet("background-color: #dcfce7; color: #166534; font-weight: bold; font-size: 11px; padding: 4px; border-radius: 4px;")
            
        self.layout.insertWidget(1, pax_tag)

        # 2. Booking Count
        count_lbl = QLabel(f"{booking_count} Booking{'s' if booking_count > 1 else ''}")
        count_lbl.setObjectName("bookingCount")
        self.layout.insertWidget(2, count_lbl)

    def mousePressEvent(self, event):
        if self.is_current_month:
            self.clicked.emit(self.day_num)
            super().mousePressEvent(event)

# --- HELPER: Schedule Item Card ---
class ScheduleCard(QFrame):
    def __init__(self, event_name, pax, time, location):
        super().__init__()
        self.setObjectName("scheduleCard")
        self.setGraphicsEffect(create_shadow())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        # Top Row: Title and Pax
        top_row = QHBoxLayout()
        title = QLabel(event_name)
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
        pax_lbl = QLabel(f"👥 {pax}")
        pax_lbl.setStyleSheet("color: #64748b; font-size: 11px; background: #f1f5f9; padding: 3px 6px; border-radius: 4px;")
        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addWidget(pax_lbl)
        layout.addLayout(top_row)
        
        # Details
        time_lbl = QLabel(f"🕒 {time}")
        time_lbl.setStyleSheet("color: #64748b; font-size: 11px; margin-top: 5px;")
        loc_lbl = QLabel(f"📍 {location}")
        loc_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(time_lbl)
        layout.addWidget(loc_lbl)

# --- MAIN PAGE ---
class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # --- Top Header ---
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        title = QLabel("Booking Calendar")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        sub = QLabel("Manage catering schedule and daily capacity limits (Max: 600 Pax).")
        sub.setStyleSheet("color: #64748b;")
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
        split_layout.setSpacing(20)

        # ==========================================
        # LEFT: CALENDAR GRID
        # ==========================================
        cal_container = QFrame()
        cal_container.setObjectName("calendarContainer")
        cal_container.setGraphicsEffect(create_shadow())
        cal_layout = QVBoxLayout(cal_container)
        cal_layout.setContentsMargins(20, 20, 20, 20)

        # Calendar Header & Controls
        cal_head = QHBoxLayout()
        month_lbl = QLabel("March 2026")
        month_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        cal_head.addWidget(month_lbl)
        
        # Legend
        cal_head.addStretch()
        legend = QLabel("🟢 Available    🟡 Near Full (400+)    🔴 Fully Booked (600)")
        legend.setStyleSheet("font-size: 11px; color: #64748b; margin-right: 20px;")
        cal_head.addWidget(legend)

        # Nav Buttons
        btn_prev = QPushButton("<")
        btn_today = QPushButton("Today")
        btn_next = QPushButton(">")
        for btn in [btn_prev, btn_today, btn_next]:
            btn.setObjectName("secondaryButton")
            btn.setCursor(Qt.PointingHandCursor)
            cal_head.addWidget(btn)
        cal_layout.addLayout(cal_head)

        # Calendar Grid Layout
        self.grid = QGridLayout()
        self.grid.setSpacing(0) # Flush borders
        
        # Day Headers
        days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
        for col, day in enumerate(days):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: #64748b; font-size: 11px; padding: 10px 0px;")
            self.grid.addWidget(lbl, 0, col)

        # MOCK DATA (Max 600 total pax per day)
        self.mock_db = {
            1: [{"name": "Anniversary Dinner", "pax": 150, "time": "06:30 PM", "loc": "Downtown Hotel"},
                {"name": "Seminar Catering", "pax": 250, "time": "08:00 AM", "loc": "Community Center"}], # Total: 400 (Yellow)
            5: [{"name": "Private Party", "pax": 150, "time": "07:00 PM", "loc": "Resort Villa"}], # Total: 150 (Green)
            9: [{"name": "Corporate Lunch", "pax": 300, "time": "12:00 PM", "loc": "Tech Park"}], # Total: 300 (Green)
            11: [{"name": "Wedding Reception", "pax": 350, "time": "10:00 AM", "loc": "Grand Hall"},
                 {"name": "Birthday Bash", "pax": 250, "time": "04:00 PM", "loc": "Beach Club"}], # Total: 600 (Red)
            24: [{"name": "Gala Dinner", "pax": 500, "time": "07:00 PM", "loc": "City Convention Center"}] # Total: 500 (Yellow)
        }

        # Generate Cells (Assuming March 1st starts on a Sunday for simplicity)
        self.cells = []
        row, col = 1, 0
        for day in range(1, 32):
            cell = DayCell(day, is_current_month=True)
            
            # Populate if we have mock data
            if day in self.mock_db:
                events = self.mock_db[day]
                total_pax = sum(e["pax"] for e in events)
                cell.set_data(total_pax, len(events))

            cell.clicked.connect(self.on_day_clicked)
            self.grid.addWidget(cell, row, col)
            self.cells.append(cell)

            col += 1
            if col > 6:
                col = 0
                row += 1

        cal_layout.addLayout(self.grid)
        cal_layout.addStretch()
        split_layout.addWidget(cal_container, 7) # Takes 70% space

        # ==========================================
        # RIGHT: SIDE PANEL (Schedule Details)
        # ==========================================
        self.side_panel = QFrame()
        self.side_panel.setObjectName("sidePanel")
        self.side_panel.setGraphicsEffect(create_shadow())
        self.side_panel.setFixedWidth(320)
        self.side_panel.setVisible(False) # Hidden by default
        
        sp_layout = QVBoxLayout(self.side_panel)
        sp_layout.setContentsMargins(0, 0, 0, 0)
        sp_layout.setSpacing(0)

        # Red Header Box
        self.sp_header = QFrame()
        self.sp_header.setObjectName("panelHeader")
        sph_layout = QVBoxLayout(self.sp_header)
        sph_layout.setContentsMargins(20, 20, 20, 20)
        
        close_row = QHBoxLayout()
        self.lbl_panel_date = QLabel("Sunday\nMarch 1, 2026")
        self.lbl_panel_date.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        close_row.addWidget(self.lbl_panel_date)
        
        btn_close = QPushButton("✕")
        btn_close.setStyleSheet("background: transparent; color: white; font-size: 16px; border: none;")
        btn_close.clicked.connect(lambda: self.side_panel.setVisible(False))
        close_row.addWidget(btn_close, alignment=Qt.AlignTop)
        sph_layout.addLayout(close_row)
        
        # Capacity Box inside Header
        cap_box = QFrame()
        cap_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.15); border-radius: 8px; margin-top: 15px;")
        cap_layout = QHBoxLayout(cap_box)
        self.lbl_capacity = QLabel("TOTAL CAPACITY\n<span style='font-size: 24px;'>400</span> / 600 Pax")
        self.lbl_capacity.setStyleSheet("color: white; font-size: 11px;")
        cap_layout.addWidget(self.lbl_capacity)
        sph_layout.addWidget(cap_box)
        
        sp_layout.addWidget(self.sp_header)

        # Schedule Scroll Area
        sp_body = QWidget()
        self.sp_body_layout = QVBoxLayout(sp_body)
        self.sp_body_layout.setContentsMargins(15, 20, 15, 20)
        self.sp_body_layout.setSpacing(12)
        
        lbl_ds = QLabel("DAILY SCHEDULE")
        lbl_ds.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        self.sp_body_layout.addWidget(lbl_ds)

        # Container for dynamic cards
        self.cards_container = QVBoxLayout()
        self.cards_container.setSpacing(10)
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
        btn_manage.setStyleSheet("background-color: #fff1f2; color: #e53935; font-weight: bold; padding: 12px; border-radius: 6px; border: 1px solid #fecdd3; margin: 15px;")
        sp_layout.addWidget(btn_manage)

        split_layout.addWidget(self.side_panel, 3) # Takes 30% space

        main_layout.addLayout(split_layout)

    def on_day_clicked(self, day_num):
        # Reset styles for all cells
        for cell in self.cells:
            cell.setProperty("active", False)
            cell.style().unpolish(cell)
            cell.style().polish(cell)

        # Highlight clicked cell
        clicked_cell = next((c for c in self.cells if c.day_num == day_num), None)
        if clicked_cell:
            clicked_cell.setProperty("active", True)
            clicked_cell.style().unpolish(clicked_cell)
            clicked_cell.style().polish(clicked_cell)

        # Update Side Panel Data
        self.lbl_panel_date.setText(f"Selected Day\nMarch {day_num}, 2026")
        
        # Clear existing cards
        for i in reversed(range(self.cards_container.count())): 
            widget = self.cards_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Load events or show empty state
        if day_num in self.mock_db:
            events = self.mock_db[day_num]
            total_pax = sum(e["pax"] for e in events)
            self.lbl_capacity.setText(f"TOTAL CAPACITY\n<span style='font-size: 24px;'>{total_pax}</span> / 600 Pax")
            
            for event in events:
                card = ScheduleCard(event["name"], event["pax"], event["time"], event["loc"])
                self.cards_container.addWidget(card)
        else:
            self.lbl_capacity.setText("TOTAL CAPACITY\n<span style='font-size: 24px;'>0</span> / 600 Pax")
            empty_lbl = QLabel("No events scheduled for this day.")
            empty_lbl.setStyleSheet("color: #94a3b8; font-style: italic;")
            self.cards_container.addWidget(empty_lbl)

        # Show the panel
        self.side_panel.setVisible(True)