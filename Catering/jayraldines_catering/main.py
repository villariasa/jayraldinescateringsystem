import sys
import os
import traceback

if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(_meipass, "PySide6", "plugins", "platforms"))
    os.environ.setdefault("QT_PLUGIN_PATH", os.path.join(_meipass, "PySide6", "plugins"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication
from ui.main_window import MainWindow
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

    print("[BOOT] Starting QApplication...")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    print("[BOOT] QApplication initialized")

    print("[BOOT] Applying theme...")
    try:
        theme = ThemeManager()
        theme.apply("dark")
        print("[BOOT] Theme applied OK")
    except Exception:
        print("[FATAL] ThemeManager crashed:")
        traceback.print_exc()
        sys.exit(1)

    print("[BOOT] Connecting to DB...")
    try:
        connected = db.connect()
        if connected:
            print("[DB] Connected to jayraldines_catering")
        else:
            print("[DB] Running in offline mode (no database)")
    except Exception:
        print("[FATAL] DB connection crashed:")
        traceback.print_exc()
        sys.exit(1)

    app.aboutToQuit.connect(db.close)

    print("[BOOT] Creating MainWindow...")
    try:
        window = MainWindow()
        print("[BOOT] MainWindow created OK")
    except Exception:
        print("[FATAL] MainWindow crashed during init:")
        traceback.print_exc()
        sys.exit(1)

    # 💣 CRITICAL FIX (THIS WAS MISSING)
    app.window_ref = window

    print("[BOOT] Showing window...")
    window.show()

    print("[BOOT] Window shown, entering event loop...")

    app.aboutToQuit.connect(lambda: print("[QT] aboutToQuit triggered"))

    code = app.exec()

    print(f"[BOOT] Event loop exited with code {code}")
    sys.exit(code)


if __name__ == "__main__":
    main()