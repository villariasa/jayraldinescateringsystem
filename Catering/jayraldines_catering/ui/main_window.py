from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget
from PySide6.QtGui import QKeySequence, QShortcut  # <-- New imports for keyboard shortcuts
from PySide6.QtCore import Qt
from ui.calendar_page import CalendarPage
from ui.reports_page import ReportsPage

from components.sidebar import Sidebar
from ui.booking_page import BookingPage
from ui.dashboard_page import DashboardPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jayraldine's Catering | Admin Dashboard")
        self.resize(1300, 850) 

        # ==========================================
        # NEW: Fullscreen & Window State Logic
        # ==========================================
        self.showMaximized() # This makes the app open to fill your screen by default
        
        # Shortcut: Press F11 to toggle true borderless fullscreen
        self.shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        self.shortcut_f11.activated.connect(self.toggle_fullscreen)
        
        # Shortcut: Press Esc to exit fullscreen safely
        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self.exit_fullscreen)
        # ==========================================

        # Central Widget & Main Layout (HBox for Sidebar + Content)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar (Dark Theme)
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # Right side container (VBox for StackedWidget)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 2. Stacked Widget (Pages)
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        self.dashboard_page = DashboardPage() 
        self.booking_page = BookingPage()
        self.calendar_page = CalendarPage() 
        self.reports_page = ReportsPage() # <--- Instantiate the Reports page

        # Add pages to stacked widget (Must match Sidebar indexes!)
        self.stacked_widget.addWidget(self.dashboard_page) # index 0
        self.stacked_widget.addWidget(self.booking_page)   # index 1
        self.stacked_widget.addWidget(self.calendar_page)  # index 2
        self.stacked_widget.addWidget(self.reports_page)   # index 3

        right_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(right_container)

        # Connect Sidebar to Navigation
        self.sidebar.page_changed.connect(self.stacked_widget.setCurrentIndex)
        self.stacked_widget.setCurrentIndex(0) # Start on Dashboard page

    # --- Helper functions for Fullscreen ---
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized() # Go back to normal windowed with taskbar
        else:
            self.showFullScreen() # Hide taskbar, true fullscreen

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()