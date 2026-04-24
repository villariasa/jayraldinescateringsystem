import sys
import os
from PySide6.QtWidgets import QApplication
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

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
