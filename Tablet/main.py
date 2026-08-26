"""
Jayraldine's Catering — Tablet App entry point.

A deliberately small, touch-first order-entry client (Tablet-mode.md).
Shares the PC app's SQLite schema for the tables that need to transfer
back and forth (customers, bookings, invoices, payment_records,
booking_additional_charges, booking_menu_items, terms_acknowledgements,
packages, menu_items, package_items) so no separate import/export format
is needed - see utils/importer.py for details.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

import utils.db as db
from ui.main_window import MainWindow
from ui import theme
from version import get_version_string


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Jayraldine's Catering Tablet")
    app.setStyleSheet(theme.GLOBAL_QSS)

    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))

    if not db.connect():
        print("FATAL: could not connect to the tablet's local database.")
        sys.exit(1)

    print(get_version_string())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
