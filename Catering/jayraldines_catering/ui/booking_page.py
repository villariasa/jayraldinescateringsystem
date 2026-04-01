from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect,
                               QStackedWidget, QCheckBox, QScrollArea, QDateEdit, QTimeEdit, QSpinBox)
from PySide6.QtCore import Qt, QDate, QTime, QVariantAnimation
from PySide6.QtGui import QColor

# ==========================================================
# CUSTOM WIDGET: Animated Hover Card
# ==========================================================
class AnimatedCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(QColor(0, 0, 0, 15)) 
        self.setGraphicsEffect(self.shadow)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250) 
        self.anim.valueChanged.connect(self._animate_shadow)

    def _animate_shadow(self, value):
        self.shadow.setBlurRadius(15 + value)
        self.shadow.setOffset(0, 4 + (value / 2))
        self.shadow.setColor(QColor(0, 0, 0, 15 + int(value / 3)))

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

# --- HELPER: Table Status Badge ---
def create_status_badge(status_text):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(5, 2, 5, 2)
    layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter) # Align left to match modern tables
    
    lbl = QLabel(status_text)
    lbl.setAlignment(Qt.AlignCenter)
    
    if status_text == "CONFIRMED":
        lbl.setStyleSheet("background-color: #dcfce7; color: #166534; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 12px; border: 1px solid #bbf7d0;")
    elif status_text == "PENDING":
        lbl.setStyleSheet("background-color: #fef9c3; color: #854d0e; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 12px; border: 1px solid #fef08a;")
    else:
        lbl.setStyleSheet("background-color: #f1f5f9; color: #475569; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 12px; border: 1px solid #e2e8f0;")
    layout.addWidget(lbl)
    return widget

# ==========================================================
# MAIN BOOKING PAGE
# ==========================================================
class BookingPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40) # Matched Dashboard spacing
        layout.setSpacing(32)

        # --- Top Header ---
        header_row = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.setSpacing(4)
        title = QLabel("Bookings Management")
        title.setObjectName("h1")
        sub = QLabel("Create new reservations and manage upcoming catering events.")
        sub.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(sub)
        header_row.addLayout(v_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        main_split = QHBoxLayout()
        main_split.setSpacing(24)

        # ==========================================
        # LEFT COLUMN: SCROLLABLE FORM CARD
        # ==========================================
        form_container = AnimatedCard()
        form_container.setFixedWidth(440) # Slightly wider for better breathing room
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.form_layout = QVBoxLayout(scroll_content)
        self.form_layout.setContentsMargins(10, 10, 10, 10)
        self.form_layout.setSpacing(20) # More space between fields

        form_title = QLabel("📄 Add New Booking")
        form_title.setObjectName("h2")
        self.form_layout.addWidget(form_title)

        # Basic Info
        self.form_layout.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Client Name</span>"))
        self.form_layout.addWidget(QLineEdit(placeholderText="e.g. John Doe"))

        row1 = QHBoxLayout()
        row1.setSpacing(16)
        v1, v2 = QVBoxLayout(), QVBoxLayout()
        v1.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Occasion</span>"))
        v1.addWidget(QLineEdit(placeholderText="e.g. Wedding"))
        v2.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Venue</span>"))
        v2.addWidget(QLineEdit(placeholderText="Event Location"))
        row1.addLayout(v1)
        row1.addLayout(v2)
        self.form_layout.addLayout(row1)

        # Row: Date & Time Pickers
        row_dt = QHBoxLayout()
        row_dt.setSpacing(16)
        v_date, v_time = QVBoxLayout(), QVBoxLayout()
        
        v_date.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Event Date</span>"))
        self.date_picker = QDateEdit(QDate.currentDate())
        self.date_picker.setCalendarPopup(True) 
        v_date.addWidget(self.date_picker)
        
        v_time.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Time Slot</span>"))
        self.time_picker = QTimeEdit(QTime.currentTime())
        v_time.addWidget(self.time_picker)
        
        row_dt.addLayout(v_date)
        row_dt.addLayout(v_time)
        self.form_layout.addLayout(row_dt)

        self.form_layout.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Pax Count</span>"))
        self.form_layout.addWidget(QLineEdit("100"))

        # Segmented Button
        self.form_layout.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Menu Selection Type</span>"))
        seg_layout = QHBoxLayout()
        seg_layout.setSpacing(0)
        self.btn_predefined = QPushButton("Packages")
        self.btn_predefined.setObjectName("segmentLeft")
        self.btn_predefined.setCheckable(True)
        self.btn_predefined.setChecked(True)
        
        self.btn_custom = QPushButton("Custom Menu")
        self.btn_custom.setObjectName("segmentRight")
        self.btn_custom.setCheckable(True)
        
        seg_layout.addWidget(self.btn_predefined)
        seg_layout.addWidget(self.btn_custom)
        self.form_layout.addLayout(seg_layout)

        # Dynamic Area
        self.menu_stack = QStackedWidget()
        
        # Page 1: Predefined
        predef_page = QWidget()
        p_lay = QVBoxLayout(predef_page)
        p_lay.setContentsMargins(0,0,0,0)
        p_lay.addWidget(QLabel("<span style='font-size:13px; color:#475569;'>Select Predefined Package</span>"))
        
        pick_lay = QHBoxLayout()
        self.pkg_combo = QComboBox()
        self.pkg_combo.addItems(["Standard (₱1,500/pax)", "Premium (₱2,500/pax)", "VIP (₱3,500/pax)"])
        
        self.pkg_qty = QSpinBox()
        self.pkg_qty.setRange(1, 10)
        self.pkg_qty.setToolTip("Quantity")
        
        btn_add_pkg = QPushButton("Add")
        btn_add_pkg.setObjectName("secondaryButton")
        
        pick_lay.addWidget(self.pkg_combo, 3)
        pick_lay.addWidget(self.pkg_qty, 1)
        pick_lay.addWidget(btn_add_pkg, 1)
        p_lay.addLayout(pick_lay)
        self.menu_stack.addWidget(predef_page)

        # Page 2: Custom
        custom_page = QWidget()
        c_lay = QVBoxLayout(custom_page)
        c_lay.setContentsMargins(0,0,0,0)
        c_lay.addWidget(QLabel("<span style='font-size:13px; color:#475569;'>Select Individual Food Items</span>"))
        
        c_scroll = QScrollArea()
        c_scroll.setWidgetResizable(True)
        c_scroll.setFixedHeight(150)
        c_scroll.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 6px; background: white;")
        c_list = QWidget()
        c_vbox = QVBoxLayout(c_list)
        
        food_items = [("Pork Adobo", 500), ("Beef Caldereta", 750), ("Chicken Cordon Bleu", 600), ("Sweet & Sour Fish", 550), ("Lechon Kawali", 800)]
        for name, price in food_items:
            item_row = QHBoxLayout()
            chk = QCheckBox(f"{name} (₱{price})")
            qty = QSpinBox()
            qty.setRange(1, 100)
            qty.setFixedWidth(50)
            item_row.addWidget(chk)
            item_row.addStretch()
            item_row.addWidget(qty)
            c_vbox.addLayout(item_row)
            
        c_scroll.setWidget(c_list)
        c_lay.addWidget(c_scroll)
        self.menu_stack.addWidget(custom_page)
        self.form_layout.addWidget(self.menu_stack)
        
        # Connect segment buttons
        self.btn_predefined.clicked.connect(lambda: self.menu_stack.setCurrentIndex(0))
        self.btn_custom.clicked.connect(lambda: self.menu_stack.setCurrentIndex(1))

        # Cost Breakdown Box
        cost_box = QFrame()
        cost_box.setObjectName("costBox")
        cost_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;")
        c_layout = QVBoxLayout(cost_box)
        c_layout.addWidget(QLabel("<span style='color:#64748b; font-size:11px; font-weight:700;'>COST BREAKDOWN</span>"))
        
        base_price = QLabel("Base Price Per Pax <span style='float:right; font-weight:700;'>₱1,500</span>")
        grand_total = QLabel("Grand Total Cost <span style='float:right; font-weight:800; font-size:16px; color:#0F172A;'>₱150,000</span>")
        downpayment = QLabel("<span style='color:#E53935; font-weight:700;'>! Required 50% Downpayment</span> <span style='color:#E53935; float:right; font-weight:700;'>₱75,000</span>")
        
        c_layout.addWidget(base_price)
        c_layout.addWidget(grand_total)
        c_layout.addWidget(downpayment)
        self.form_layout.addWidget(cost_box)

        # Payment Row
        pay_row = QHBoxLayout()
        pay_row.setSpacing(16)
        v_pay1, v_pay2 = QVBoxLayout(), QVBoxLayout()
        v_pay1.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Mode of Payment</span>"))
        pay_combo = QComboBox()
        pay_combo.addItems(["Bank Transfer", "Cash", "GCash"])
        v_pay1.addWidget(pay_combo)
        
        v_pay2.addWidget(QLabel("<span style='font-size:13px; font-weight:600; color:#475569;'>Amount Paid</span>"))
        v_pay2.addWidget(QLineEdit("₱ 0"))
        pay_row.addLayout(v_pay1)
        pay_row.addLayout(v_pay2)
        self.form_layout.addLayout(pay_row)

        self.form_layout.addStretch()

        # Finalize Scroll Area
        scroll_area.setWidget(scroll_content)
        
        container_lay = QVBoxLayout(form_container)
        container_lay.setContentsMargins(20, 20, 20, 20)
        container_lay.addWidget(scroll_area) 
        
        submit_btn = QPushButton("✓ Confirm Booking")
        submit_btn.setObjectName("primaryButton")
        submit_btn.setFixedHeight(48)
        container_lay.addWidget(submit_btn) 
        
        main_split.addWidget(form_container)

        # ==========================================
        # RIGHT COLUMN: CURRENT BOOKINGS TABLE
        # ==========================================
        table_card = AnimatedCard()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(24, 24, 24, 24)

        # Table Header Row
        t_head = QHBoxLayout()
        t_title = QLabel("Current Bookings")
        t_title.setObjectName("h2")
        t_head.addWidget(t_title)
        t_head.addStretch()
        
        btn_filter = QPushButton("Filter")
        btn_filter.setObjectName("secondaryButton")
        btn_export = QPushButton("Export")
        btn_export.setObjectName("secondaryButton")
        t_head.addWidget(btn_filter)
        t_head.addWidget(btn_export)
        table_layout.addLayout(t_head)

        # The Table
        self.table = QTableWidget(4, 6)
        self.table.setHorizontalHeaderLabels(["DATE", "CLIENT NAME", "PAX", "TOTAL AMOUNT", "STATUS", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents) # Shrink action column
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False) 
        self.table.setShowGrid(False)

        # Data Injection
        rows_data = [
            ("Oct 24, 2026\nBKG-001", "TechCorp Inc.", "150", "₱ 45,000", "CONFIRMED"),
            ("Oct 25, 2026\nBKG-002", "Smith Wedding", "300", "₱ 120,000", "PENDING"),
            ("Oct 26, 2026\nBKG-003", "Sarah's 18th", "100", "₱ 35,000", "CONFIRMED"),
            ("Oct 28, 2026\nBKG-004", "Local NGO Meet", "60", "₱ 18,000", "CANCELLED"),
        ]

        for row, data in enumerate(rows_data):
            self.table.setRowHeight(row, 65) 
            
            # Subtitle styling for Date
            date_lbl = QLabel(f"<span style='font-weight:600; color:#0F172A;'>{data[0].split(chr(10))[0]}</span><br><span style='color:#64748B; font-size:11px;'>{data[0].split(chr(10))[1]}</span>")
            self.table.setCellWidget(row, 0, date_lbl)
            
            name_lbl = QLabel(f"<span style='font-weight:700; color:#0F172A;'>{data[1]}</span>")
            self.table.setCellWidget(row, 1, name_lbl)
            
            pax_lbl = QLabel(f"<span style='font-weight:600; color:#475569;'>👥 {data[2]}</span>")
            self.table.setCellWidget(row, 2, pax_lbl)
            
            amount_lbl = QLabel(f"<span style='font-weight:700; color:#0F172A;'>{data[3]}</span>")
            self.table.setCellWidget(row, 3, amount_lbl)
            
            self.table.setCellWidget(row, 4, create_status_badge(data[4]))
            
            # Action Button Cell (Trash icon)
            del_btn = QPushButton("🗑")
            del_btn.setStyleSheet("color: #94A3B8; font-size: 16px; border: none; background: transparent;")
            del_btn.setCursor(Qt.PointingHandCursor)
            self.table.setCellWidget(row, 5, del_btn)

        table_layout.addWidget(self.table)
        main_split.addWidget(table_card)

        layout.addLayout(main_split)