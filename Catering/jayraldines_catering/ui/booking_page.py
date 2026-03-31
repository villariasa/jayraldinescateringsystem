from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                               QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QGraphicsDropShadowEffect,
                               QStackedWidget, QCheckBox, QScrollArea, QDateEdit, QTimeEdit, QSpinBox)
from PySide6.QtCore import Qt, QDate, QTime

def create_shadow():
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(15)
    shadow.setColor(Qt.gray)
    shadow.setOffset(0, 3)
    return shadow

def create_status_badge(status_text):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(5, 2, 5, 2)
    layout.setAlignment(Qt.AlignCenter)
    lbl = QLabel(status_text)
    lbl.setAlignment(Qt.AlignCenter)
    
    if status_text == "CONFIRMED":
        lbl.setStyleSheet("background-color: #dcfce7; color: #166534; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px; border: 1px solid #bbf7d0;")
    elif status_text == "PENDING":
        lbl.setStyleSheet("background-color: #fef9c3; color: #854d0e; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px; border: 1px solid #fef08a;")
    else:
        lbl.setStyleSheet("background-color: #f1f5f9; color: #475569; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px; border: 1px solid #e2e8f0;")
    layout.addWidget(lbl)
    return widget

class BookingPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # --- Top Header ---
        header_card = QFrame()
        header_card.setObjectName("card")
        header_card.setGraphicsEffect(create_shadow())
        h_layout = QVBoxLayout(header_card)
        title = QLabel("Bookings Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        sub = QLabel("Create and manage your catering events with full control.")
        sub.setStyleSheet("color: #64748b;")
        h_layout.addWidget(title)
        h_layout.addWidget(sub)
        layout.addWidget(header_card)

        main_split = QHBoxLayout()
        main_split.setSpacing(20)

        # ==========================================
        # LEFT COLUMN: SCROLLABLE FORM
        # ==========================================
        form_container = QFrame()
        form_container.setFixedWidth(420)
        form_container.setObjectName("card")
        form_container.setGraphicsEffect(create_shadow())
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.form_layout = QVBoxLayout(scroll_content)
        self.form_layout.setSpacing(15)

        form_title = QLabel("📄 Add New Booking")
        form_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.form_layout.addWidget(form_title)

        # Basic Info
        self.form_layout.addWidget(QLabel("Client Name"))
        self.form_layout.addWidget(QLineEdit(placeholderText="e.g. John Doe"))

        row1 = QHBoxLayout()
        v1, v2 = QVBoxLayout(), QVBoxLayout()
        v1.addWidget(QLabel("Occasion"))
        v1.addWidget(QLineEdit(placeholderText="e.g. Wedding"))
        v2.addWidget(QLabel("Venue"))
        v2.addWidget(QLineEdit(placeholderText="Event Location"))
        row1.addLayout(v1)
        row1.addLayout(v2)
        self.form_layout.addLayout(row1)

        # Row: Date & Time Pickers
        row_dt = QHBoxLayout()
        v_date, v_time = QVBoxLayout(), QVBoxLayout()
        
        v_date.addWidget(QLabel("Event Date"))
        self.date_picker = QDateEdit(QDate.currentDate())
        self.date_picker.setCalendarPopup(True) 
        v_date.addWidget(self.date_picker)
        
        v_time.addWidget(QLabel("Time Slot"))
        self.time_picker = QTimeEdit(QTime.currentTime())
        v_time.addWidget(self.time_picker)
        
        row_dt.addLayout(v_date)
        row_dt.addLayout(v_time)
        self.form_layout.addLayout(row_dt)

        self.form_layout.addWidget(QLabel("Pax Count"))
        self.form_layout.addWidget(QLineEdit("100"))

        # Segmented Button
        self.form_layout.addWidget(QLabel("Menu Selection Type"))
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
        
        # Page 1: Predefined with Qty
        predef_page = QWidget()
        p_lay = QVBoxLayout(predef_page)
        p_lay.setContentsMargins(0,0,0,0)
        p_lay.addWidget(QLabel("Select Predefined Package"))
        
        pick_lay = QHBoxLayout()
        self.pkg_combo = QComboBox()
        self.pkg_combo.addItems(["Standard (₱1,500/pax)", "Premium (₱2,500/pax)", "VIP (₱3,500/pax)"])
        
        self.pkg_qty = QSpinBox()
        self.pkg_qty.setRange(1, 10)
        self.pkg_qty.setToolTip("Quantity of this package")
        
        btn_add_pkg = QPushButton("Add")
        btn_add_pkg.setObjectName("secondaryButton")
        
        pick_lay.addWidget(self.pkg_combo, 3)
        pick_lay.addWidget(self.pkg_qty, 1)
        pick_lay.addWidget(btn_add_pkg, 1)
        p_lay.addLayout(pick_lay)
        self.menu_stack.addWidget(predef_page)

        # Page 2: Custom with Qty per item
        custom_page = QWidget()
        c_lay = QVBoxLayout(custom_page)
        c_lay.setContentsMargins(0,0,0,0)
        c_lay.addWidget(QLabel("Select Individual Food Items"))
        
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
        self.btn_predefined.clicked.connect(self.show_predefined)
        self.btn_custom.clicked.connect(self.show_custom)

        # Cost Breakdown Box
        cost_box = QFrame()
        cost_box.setObjectName("costBox")
        c_layout = QVBoxLayout(cost_box)
        c_layout.addWidget(QLabel("<b style='color:#64748b; font-size:11px;'>COST BREAKDOWN</b>"))
        
        base_price = QLabel("Base Price Per Pax <span style='float:right; font-weight:bold;'>₱1,500</span>")
        grand_total = QLabel("Grand Total Cost <span style='float:right; font-weight:bold;'>₱150,000</span>")
        downpayment = QLabel("<span style='color:#e53935; font-weight:bold;'>! Required 50% Downpayment</span> <span style='color:#e53935; float:right; font-weight:bold;'>₱75,000</span>")
        
        c_layout.addWidget(base_price)
        c_layout.addWidget(grand_total)
        c_layout.addWidget(downpayment)
        self.form_layout.addWidget(cost_box)

        # Payment Row
        pay_row = QHBoxLayout()
        v_pay1, v_pay2 = QVBoxLayout(), QVBoxLayout()
        v_pay1.addWidget(QLabel("Mode of Payment"))
        pay_combo = QComboBox()
        pay_combo.addItems(["Bank Transfer", "Cash", "GCash"])
        v_pay1.addWidget(pay_combo)
        
        v_pay2.addWidget(QLabel("Amount Paid"))
        v_pay2.addWidget(QLineEdit("₱ 0"))
        pay_row.addLayout(v_pay1)
        pay_row.addLayout(v_pay2)
        self.form_layout.addLayout(pay_row)

        # ... (Right below your Payment Row code) ...

        self.form_layout.addStretch() # Pushes form fields to the top

        # Finalize Scroll Area
        scroll_area.setWidget(scroll_content)
        
        # --- THE FIX: Create the Card Layout ---
        container_lay = QVBoxLayout(form_container)
        
        # 1. Add the scrollable form to the top of the card
        container_lay.addWidget(scroll_area) 
        
        # 2. Add the Submit Button OUTSIDE the scroll area (Sticky Footer!)
        submit_btn = QPushButton("✓ CONFIRM BOOKING")
        submit_btn.setObjectName("primaryButton")
        submit_btn.setFixedHeight(45)
        container_lay.addWidget(submit_btn) 
        
        main_split.addWidget(form_container)

        # ==========================================
        # RIGHT COLUMN: CURRENT BOOKINGS TABLE
        # ==========================================
        table_card = QFrame()
        table_card.setObjectName("card")
        table_card.setGraphicsEffect(create_shadow())
        table_layout = QVBoxLayout(table_card)

        # Table Header Row
        t_head = QHBoxLayout()
        t_title = QLabel("Current Bookings")
        t_title.setStyleSheet("font-size: 18px; font-weight: bold;")
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
        self.table.setHorizontalHeaderLabels(["DATE", "CLIENT NAME", "PAX", "TOTAL AMOUNT", "STATUS", "ACTIONS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False) 
        self.table.setShowGrid(False)

        # --- THE MISSING DATA LOOP IS BACK ---
        rows_data = [
            ("Oct 24, 2026\nBKG-001", "TechCorp Inc.", "150", "₱ 45,000", "CONFIRMED"),
            ("Oct 25, 2026\nBKG-002", "Smith Wedding", "300", "₱ 120,000", "PENDING"),
            ("Oct 26, 2026\nBKG-003", "Sarah's 18th", "100", "₱ 35,000", "CONFIRMED"),
            ("Oct 28, 2026\nBKG-004", "Local NGO Meet", "60", "₱ 18,000", "CANCELLED"),
        ]

        for row, data in enumerate(rows_data):
            self.table.setRowHeight(row, 60) 
            
            self.table.setItem(row, 0, QTableWidgetItem(data[0]))
            
            name_item = QTableWidgetItem(data[1])
            name_item.setFont(self.get_bold_font())
            self.table.setItem(row, 1, name_item)
            
            self.table.setItem(row, 2, QTableWidgetItem(f"👥 {data[2]}"))
            
            amount_item = QTableWidgetItem(data[3])
            amount_item.setFont(self.get_bold_font())
            self.table.setItem(row, 3, amount_item)
            
            self.table.setCellWidget(row, 4, create_status_badge(data[4]))
            
            del_btn = QPushButton("🗑")
            del_btn.setStyleSheet("color: #94a3b8; font-size: 16px; border: none; background: transparent;")
            self.table.setCellWidget(row, 5, del_btn)

        table_layout.addWidget(self.table)
        main_split.addWidget(table_card)

        layout.addLayout(main_split)

    def get_bold_font(self):
        font = self.font()
        font.setBold(True)
        return font

    def show_predefined(self):
        self.btn_predefined.setChecked(True)
        self.btn_custom.setChecked(False)
        self.menu_stack.setCurrentIndex(0)

    def show_custom(self):
        self.btn_predefined.setChecked(False)
        self.btn_custom.setChecked(True)
        self.menu_stack.setCurrentIndex(1)