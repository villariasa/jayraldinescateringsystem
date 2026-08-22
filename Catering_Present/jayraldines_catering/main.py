import sys
import os
import traceback
import time

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from utils.logger import setup_logging, get_logger
log = setup_logging()

_STARTUP_T0 = time.perf_counter()
_PROFILE_STARTUP = os.environ.get("JAYRALDINES_PROFILE_STARTUP", "").lower() in {"1", "true", "yes", "on"}


def _profile(label: str):
    if _PROFILE_STARTUP:
        elapsed = time.perf_counter() - _STARTUP_T0
        log.info(f"[startup] {label}: {elapsed:.2f}s")

if getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    _qt_plugin_roots = [
        os.path.join(_meipass, "PySide6", "Qt", "plugins"),
        os.path.join(_meipass, "_internal", "PySide6", "Qt", "plugins"),
        os.path.join(os.path.dirname(sys.executable), "_internal", "PySide6", "Qt", "plugins"),
        os.path.join(_meipass, "PySide6", "plugins"),
    ]
    for _qt_plugin_root in _qt_plugin_roots:
        if os.path.isdir(_qt_plugin_root):
            os.environ.setdefault("QT_PLUGIN_PATH", _qt_plugin_root)
            os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", os.path.join(_qt_plugin_root, "platforms"))
            break

# Configure Rendering & GPU Driver Fallbacks for older hardware (Intel HD Graphics, legacy Windows 10)
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QGuiApplication
_profile("Qt imports")

# Configure High DPI scaling policy for clean rendering on Windows laptop displays
if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

_MUTEX_HANDLE = None


def _acquire_single_instance():
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jayraldines.catering.system.v1")
    except Exception:
        pass
    _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\JayraldinesCateringMutex")
    err = ctypes.windll.kernel32.GetLastError()
    return err != 183


def _exception_hook(exc_type, exc_value, exc_tb):
    import datetime
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"[Unhandled Exception]\n{err_msg}", file=sys.stderr)
    try:
        log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JayraldinesCatering")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "error_log.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.datetime.now()} ---\n{err_msg}\n")
    except Exception:
        pass



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
        for plugin_path in os.environ.get("QT_PLUGIN_PATH", "").split(os.pathsep):
            if plugin_path and os.path.isdir(plugin_path):
                QCoreApplication.addLibraryPath(plugin_path)

    from PySide6.QtGui import QIcon
    from utils.paths import resource_path

    app = QApplication(sys.argv)
    # Performance flag for older Intel HD Graphics (i5-4670 / HD 4600) on Windows 10
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
    app.setStyle("Fusion")

    ico_path = resource_path("assets", "logo.ico")
    if not os.path.exists(ico_path):
        ico_path = resource_path("assets", "logo.png")
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))

    _profile("QApplication")

    from components.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    _profile("splash shown")

    try:
        import threading

        splash.set_status("Initializing...", 10)
        from utils.theme import ThemeManager
        from utils.accent import AccentManager
        import utils.db as db
        _profile("core modules imported")

        try:
            AccentManager()  # loads the saved accent color before the first paint
            ThemeManager().apply("dark")
            _profile("theme applied")
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
        _profile("db thread started")

        splash.set_status("Loading interface...", 50)
        from ui.main_window import MainWindow
        app.processEvents()
        _profile("main window module imported")

        splash.set_status("Waiting for database...", 75)
        app.processEvents()
        db_thread.join(timeout=8)
        _profile("db wait complete")

        if _db_result[0]:
            splash.set_status("Database connected.", 85)
        else:
            splash.set_status("Running in offline mode.", 85)
        app.processEvents()

        splash.set_status("Building interface...", 92)
        window = MainWindow()
        if os.path.exists(ico_path):
            window.setWindowIcon(QIcon(ico_path))
        _profile("main window created")

        splash.set_status("Ready!", 100)
        app.processEvents()
        _profile("ready")

    except Exception:
        traceback.print_exc()
        sys.exit(1)

    app.aboutToQuit.connect(db.close)
    app.window_ref = window

    splash.finish(window)
    _profile("main window shown")

    app.aboutToQuit.connect(lambda: print("[QT] aboutToQuit triggered"))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
