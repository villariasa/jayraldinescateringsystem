import sys
import os
import traceback

if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(_meipass, "PySide6", "plugins", "platforms"))
    os.environ.setdefault("QT_PLUGIN_PATH", os.path.join(_meipass, "PySide6", "plugins"))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QCoreApplication

_MUTEX_HANDLE = None


def _acquire_single_instance():
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    import ctypes
    _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\JayraldinesCateringMutex")
    err = ctypes.windll.kernel32.GetLastError()
    return err != 183


def _exception_hook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.exit(1)


def main():
    sys.excepthook = _exception_hook

    if not _acquire_single_instance():
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "Already Running",
            "Jayraldine's Catering is already open.\nPlease check your taskbar.",
        )
        sys.exit(0)

    if getattr(sys, "frozen", False):
        _meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        QCoreApplication.addLibraryPath(os.path.join(_meipass, "PySide6", "plugins"))

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    from components.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    try:
        import threading

        splash.set_status("Initializing...", 10)
        from utils.theme import ThemeManager
        import utils.db as db

        try:
            ThemeManager().apply("dark")
        except Exception:
            traceback.print_exc()
            sys.exit(1)

        splash.set_status("Connecting to database...", 25)
        app.processEvents()

        _db_result = [False]

        def _db_connect():
            try:
                _db_result[0] = db.connect()
            except Exception:
                traceback.print_exc()

        db_thread = threading.Thread(target=_db_connect, daemon=True)
        db_thread.start()

        splash.set_status("Loading interface...", 50)
        from ui.main_window import MainWindow
        app.processEvents()

        splash.set_status("Waiting for database...", 75)
        app.processEvents()
        db_thread.join(timeout=8)

        if _db_result[0]:
            splash.set_status("Database connected.", 85)
        else:
            splash.set_status("Running in offline mode.", 85)
        app.processEvents()

        splash.set_status("Building interface...", 92)
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