import sys
import os
import traceback

if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(_meipass, "PySide6", "plugins", "platforms"))
    os.environ.setdefault("QT_PLUGIN_PATH", os.path.join(_meipass, "PySide6", "plugins"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication
from utils.theme import ThemeManager
import utils.db as db


def _exception_hook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.exit(1)


def main():
    sys.excepthook = _exception_hook

    if getattr(sys, "frozen", False):
        _meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        QCoreApplication.addLibraryPath(os.path.join(_meipass, "PySide6", "plugins"))

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        theme = ThemeManager()
        theme.apply("dark")
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    from components.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    try:
        splash.set_status("Loading theme and resources...", 15)
        from ui.main_window import MainWindow

        splash.set_status("Connecting to database...", 40)
        try:
            connected = db.connect()
            if connected:
                splash.set_status("Database connected.", 65)
            else:
                splash.set_status("Running in offline mode.", 65)
        except Exception:
            traceback.print_exc()
            splash.set_status("Database unavailable - offline mode.", 65)

        splash.set_status("Building interface...", 80)
        window = MainWindow()

        splash.set_status("Ready!", 100)
        app.processEvents()

    except Exception:
        traceback.print_exc()
        sys.exit(1)

    app.aboutToQuit.connect(db.close)
    app.window_ref = window

    window.show()
    splash.close()

    app.aboutToQuit.connect(lambda: print("[QT] aboutToQuit triggered"))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()