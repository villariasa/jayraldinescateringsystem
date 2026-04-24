import sys
import os
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from utils.theme import ThemeManager
import utils.db as db


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    theme = ThemeManager()
    theme.apply("dark")

    connected = db.connect()
    if connected:
        print("[DB] Connected to jayraldines_catering")
    else:
        print("[DB] Running in offline mode (no database)")

    app.aboutToQuit.connect(db.close)

    try:
        window = MainWindow()
        window.show()
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
