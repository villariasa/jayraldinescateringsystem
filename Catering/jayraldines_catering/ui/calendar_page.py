import calendar
from datetime import datetime, date as date_type
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QLabel, QPushButton, QGridLayout, QScrollArea,
                               QSizePolicy, QDialog, QLineEdit, QFormLayout, QTimeEdit)
from PySide6.QtCore import Qt, Signal, QSize, QTime

from utils.icons import btn_icon_primary, btn_icon_secondary, btn_icon_muted, get_icon
from components.booking_modal import BookingModal
from components.dialogs import confirm, success
import utils.repository as repo


class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")

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
            pax_tag.setStyleSheet("background-color: rgba(248,113,113,0.15); color: #f87171; font-weight: 700; font-size: 11px; padding: 4px; border-radius: 4px;")
        elif total_pax >= 400:
            pax_tag.setStyleSheet("background-color: rgba(197,164,109,0.15); color: #c5a46d; font-weight: 700; font-size: 11px; padding: 4px; border-radius: 4px;")
        else:
            pax_tag.setStyleSheet("background-color: rgba(110,231,183,0.15); color: #6ee7b7; font-weight: 700; font-size: 11px; padding: 4px; border-radius: 4px;")
            
        self.layout.insertWidget(1, pax_tag)

        # 2. Booking Count
        count_lbl = QLabel(f"{booking_count} Booking{'s' if booking_count > 1 else ''}")
        count_lbl.setObjectName("bookingCount")
        count_lbl.setStyleSheet("color: #9aa0a6; font-size: 11px; font-weight: 600;")
        self.layout.insertWidget(2, count_lbl)

    def mousePressEvent(self, event):
        if self.is_current_month and self.day_num != 0:
            self.clicked.emit(self.day_num)
            super().mousePressEvent(event)

# --- HELPER: Schedule Item Card ---
class ScheduleCard(AnimatedCard):
    def __init__(self, event_name, pax, time, location):
        super().__init__()
        self.setStyleSheet("QFrame#card { border-left: 4px solid #E11D48; border-radius: 8px; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        top_row = QHBoxLayout()
        title = QLabel(event_name)
        title.setObjectName("h3")
        pax_lbl = QLabel(f"{pax} pax")
        pax_lbl.setObjectName("badgeInfo")
        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addWidget(pax_lbl)
        layout.addLayout(top_row)
        
        time_lbl = QLabel(f"Time: {time}")
        time_lbl.setObjectName("subtitle")
        loc_lbl = QLabel(f"Venue: {location}")
        loc_lbl.setObjectName("subtitle")
        layout.addWidget(time_lbl)
        layout.addWidget(loc_lbl)

# --- MANAGE DAY SCHEDULE DIALOG ---
class ManageScheduleDialog(QDialog):
    def __init__(self, parent=None, date_str="", events=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(480)
        self.setModal(True)
        self._events = list(events or [])
        self._result = None
        self._date_str = date_str
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        container = QFrame()
        container.setObjectName("card")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(f"Manage Schedule — {self._date_str}")
        title.setObjectName("h3")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color="#6B7280", size=QSize(14, 14)))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        lay.addLayout(header)

        div = QFrame()
        div.setObjectName("divider")
        lay.addWidget(div)

        self._events_layout = QVBoxLayout()
        self._events_layout.setSpacing(8)
        lay.addLayout(self._events_layout)
        self._refresh_events()

        add_lbl = QLabel("Add New Event")
        add_lbl.setObjectName("h3")
        lay.addWidget(add_lbl)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        self._name_f = QLineEdit()
        self._name_f.setPlaceholderText("Event name")
        self._pax_f = QLineEdit()
        self._pax_f.setPlaceholderText("Number of guests")
        self._time_f = QTimeEdit()
        self._time_f.setDisplayFormat("hh:mm AP")
        self._time_f.setTime(QTime(18, 0))
        self._loc_f = QLineEdit()
        self._loc_f.setPlaceholderText("Venue / location")
        for lbl, w in [("Event Name *", self._name_f), ("Pax *", self._pax_f),
                        ("Time", self._time_f), ("Venue", self._loc_f)]:
            form.addRow(QLabel(lbl), w)
        lay.addLayout(form)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #E11D48; font-size: 12px;")
        self._err.hide()
        lay.addWidget(self._err)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        add_btn = QPushButton("  Add Event")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_event)
        save_btn = QPushButton("  Save Schedule")
        save_btn.setObjectName("goldButton")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

        outer.addWidget(container)

    def _refresh_events(self):
        while self._events_layout.count():
            item = self._events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self._events:
            lbl = QLabel("No events yet. Add one below.")
            lbl.setObjectName("subtitle")
            self._events_layout.addWidget(lbl)
            return
        for i, ev in enumerate(self._events):
            row = QHBoxLayout()
            info = QLabel(f"{ev['name']}  ·  {ev['pax']} pax  ·  {ev['time']}  ·  {ev['loc']}")
            info.setObjectName("subtitle")
            info.setWordWrap(True)
            del_btn = QPushButton()
            del_btn.setIcon(get_icon("trash", color="#EF4444", size=QSize(13, 13)))
            del_btn.setIconSize(QSize(13, 13))
            del_btn.setFixedSize(26, 26)
            del_btn.setStyleSheet("background: transparent; border: none;")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(lambda _, idx=i: self._remove_event(idx))
            row.addWidget(info)
            row.addWidget(del_btn)
            w = QWidget()
            w.setLayout(row)
            self._events_layout.addWidget(w)

    def _add_event(self):
        name = self._name_f.text().strip()
        pax_text = self._pax_f.text().strip()
        if not name or not pax_text:
            self._err.setText("Event name and pax are required.")
            self._err.show()
            return
        try:
            pax = int(pax_text)
        except ValueError:
            self._err.setText("Pax must be a number.")
            self._err.show()
            return
        self._err.hide()
        self._events.append({
            "name": name,
            "pax":  pax,
            "time": self._time_f.time().toString("hh:mm AP"),
            "loc":  self._loc_f.text().strip() or "TBD",
        })
        self._name_f.clear()
        self._pax_f.clear()
        self._loc_f.clear()
        self._refresh_events()

    def _remove_event(self, idx):
        if 0 <= idx < len(self._events):
            self._events.pop(idx)
            self._refresh_events()

    def _save(self):
        self._result = list(self._events)
        self.accept()

    def get_result(self):
        return self._result


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
        btn_add = QPushButton("  Add New Booking")
        btn_add.setObjectName("primaryButton")
        btn_add.setIcon(btn_icon_primary("plus"))
        btn_add.setIconSize(QSize(16, 16))
        btn_add.clicked.connect(self._open_booking_modal)
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
        cal_layout = QVBoxLayout(cal_container)
        cal_layout.setContentsMargins(24, 24, 24, 24)

        # Calendar Header & Controls
        cal_head = QHBoxLayout()
        self.month_lbl = QLabel()
        self.month_lbl.setObjectName("h2")
        cal_head.addWidget(self.month_lbl)
        
        cal_head.addStretch()
        legend = QLabel("Available  |  Near Full (400+)  |  Fully Booked (600)")
        legend.setStyleSheet("font-size: 12px; font-weight: 600; color: #9aa0a6; margin-right: 24px;")
        cal_head.addWidget(legend)

        # Dynamic Nav Buttons
        btn_prev = QPushButton()
        btn_today = QPushButton("Today")
        btn_next = QPushButton()
        
        btn_prev.setObjectName("secondaryButton")
        btn_prev.setIcon(btn_icon_secondary("chevron-left"))
        btn_prev.setIconSize(QSize(16, 16))
        btn_today.setObjectName("secondaryButton")
        btn_next.setObjectName("secondaryButton")
        btn_next.setIcon(btn_icon_secondary("chevron-right"))
        btn_next.setIconSize(QSize(16, 16))
        
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

        self._db_cache: dict = {}

        cal_layout.addLayout(self.grid)
        split_layout.addWidget(cal_container, 7) # Takes 70% space

        # ==========================================
        # RIGHT: SIDE PANEL (Schedule Details)
        # ==========================================
        self.side_panel = QFrame()
        self.side_panel.setObjectName("sidePanel")
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
        
        btn_close = QPushButton()
        btn_close.setIcon(btn_icon_muted("close"))
        btn_close.setIconSize(QSize(16, 16))
        btn_close.setStyleSheet("background: transparent; border: none;")
        btn_close.clicked.connect(lambda: self.side_panel.setVisible(False))
        btn_close.setCursor(Qt.PointingHandCursor)
        close_row.addWidget(btn_close, alignment=Qt.AlignTop)
        sph_layout.addLayout(close_row)
        
        # Capacity Box
        cap_box = QFrame()
        cap_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.06); border-radius: 8px; margin-top: 15px;")
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
        lbl_ds.setStyleSheet("color: #9aa0a6; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;")
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
        self._btn_manage = QPushButton("  Manage Day Schedule")
        self._btn_manage.setObjectName("goldButton")
        self._btn_manage.setCursor(Qt.PointingHandCursor)
        self._btn_manage.clicked.connect(self._open_manage_schedule)
        sp_layout.addWidget(self._btn_manage)

        split_layout.addWidget(self.side_panel, 3) 
        main_layout.addLayout(split_layout)

        self._selected_day = None

        self.cells = []
        self._load_month_data()
        self.render_calendar()

    # ==========================================
    # CALENDAR LOGIC
    # ==========================================
    def _load_month_data(self):
        self._db_cache.clear()
        import calendar as _cal
        days_in_month = _cal.monthrange(self.current_year, self.current_month)[1]
        for day in range(1, days_in_month + 1):
            d = date_type(self.current_year, self.current_month, day)
            try:
                events = repo.get_calendar_events_for_date(d)
            except Exception:
                events = []
            if events:
                self._db_cache[(self.current_year, self.current_month, day)] = events

    def go_prev_month(self):
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self._load_month_data()
        self.render_calendar()

    def go_next_month(self):
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self._load_month_data()
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
                
                db_key = (self.current_year, self.current_month, day_num)
                if db_key in self._db_cache:
                    events = self._db_cache[db_key]
                    total_pax = sum(e["pax"] for e in events)
                    cell.set_data(total_pax, len(events))

                cell.clicked.connect(self.on_day_clicked)
                self.grid.addWidget(cell, row, col)
                self.cells.append(cell)
            row += 1

    def _open_booking_modal(self):
        modal = BookingModal(self)
        modal.exec()

    def _open_manage_schedule(self):
        if self._selected_day is None:
            return
        month_name = calendar.month_name[self.current_month]
        date_str = f"{month_name} {self._selected_day}, {self.current_year}"
        db_key = (self.current_year, self.current_month, self._selected_day)
        events = list(self._db_cache.get(db_key, []))
        dlg = ManageScheduleDialog(self, date_str=date_str, events=events)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.get_result()
            if updated is not None:
                event_date = date_type(self.current_year, self.current_month, self._selected_day)
                try:
                    repo.save_calendar_day(event_date, updated)
                except Exception:
                    pass
                if updated:
                    self._db_cache[db_key] = updated
                elif db_key in self._db_cache:
                    del self._db_cache[db_key]
                self.render_calendar()
                self.on_day_clicked(self._selected_day)
                success(self, message=f"Schedule for {date_str} updated successfully.")

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
        if db_key in self._db_cache:
            events = self._db_cache[db_key]
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

        self._selected_day = day_num
        self.side_panel.setVisible(True)