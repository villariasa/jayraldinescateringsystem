import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.theme import ThemeManager


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    theme = ThemeManager()
    theme.apply("dark")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
