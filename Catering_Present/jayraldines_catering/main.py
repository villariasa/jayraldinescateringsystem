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

from utils.logger import setup_logging, get_logger, get_log_dir
log = setup_logging()

# Native crashes (segfaults) bypass Python's sys.excepthook entirely, so they
# leave no trace in the app log. faulthandler writes a C-level stack trace to
# a dedicated file when that happens, which is otherwise impossible to recover.
import faulthandler
_faulthandler_file = None
try:
    _crash_log_path = get_log_dir() / "crash_traces.log"
    _faulthandler_file = open(_crash_log_path, "a", encoding="utf-8")
    faulthandler.enable(file=_faulthandler_file, all_threads=True)
except Exception:
    pass

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

# Hardware GPU acceleration on Windows (DirectX 11 / D3D11)
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
if sys.platform == "win32":
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
_IN_EXCEPTION_HOOK = False


def _acquire_single_instance():
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jayraldines.catering.system.v1")
    except Exception:
        pass
    try:
        # Prevent Windows Desktop Window Manager (DWM) from creating ghost windows
        # or flashing 'Not Responding' title bars during rapid UI interactions
        ctypes.windll.user32.DisableProcessWindowsGhosting()
    except Exception:
        pass
    # Use Local session mutex to prevent cross-session permission conflicts
    _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(None, True, "Local\\JayraldinesCateringMutex")
    err = ctypes.windll.kernel32.GetLastError()
    return err != 183 and _MUTEX_HANDLE != 0


def _focus_existing_catering_window():
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        found_hwnd = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def _enum_proc(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "Jayraldine's Catering" in title:
                    found_hwnd.append(hwnd)
                    return False
            return True

        user32.EnumWindows(WNDENUMPROC(_enum_proc), 0)

        if found_hwnd:
            target = found_hwnd[0]
            user32.ShowWindow(target, 9)  # SW_RESTORE
            user32.SetForegroundWindow(target)
            return True
    except Exception as exc:
        print(f"[main] Window focus helper exception: {exc}")
    return False


def _exception_hook(exc_type, exc_value, exc_tb):
    global _IN_EXCEPTION_HOOK
    if issubclass(exc_type, KeyboardInterrupt):
        return sys.__excepthook__(exc_type, exc_value, exc_tb)

    import datetime
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"[Unhandled Exception]\n{err_msg}", file=sys.stderr)
    try:
        log.critical(f"UNHANDLED EXCEPTION: {err_msg}")
    except Exception:
        pass
    try:
        log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JayraldinesCatering")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "error_log.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.datetime.now()} ---\n{err_msg}\n")
    except Exception:
        pass

    # Debounce modal error dialog so multiple stacked popups never occur
    if _IN_EXCEPTION_HOOK:
        return
    _IN_EXCEPTION_HOOK = True

    try:
        _app = QApplication.instance()
        if _app:
            QMessageBox.critical(
                None,
                "Unexpected Error — Jayraldine's Catering",
                f"An unexpected error occurred:\n\n{str(exc_value)}\n\nPlease check the error_log.txt file or contact support."
            )
    except Exception:
        pass
    finally:
        _IN_EXCEPTION_HOOK = False



def _handle_reset_admin_cli():
    print("====================================================")
    print("  Jayraldine's Catering - Admin Emergency Password Reset")
    print("====================================================")
    import utils.db as db
    from utils.auth import ensure_auth_tables, reset_user_password, validate_password, create_default_admin
    db.connect()
    ensure_auth_tables()

    new_pwd = None
    argv = sys.argv
    idx = argv.index("--reset-admin")
    if idx + 1 < len(argv) and not argv[idx + 1].startswith("-"):
        new_pwd = argv[idx + 1]

    if not new_pwd:
        import getpass
        while True:
            try:
                new_pwd = getpass.getpass("Enter new password for 'admin': ")
            except Exception:
                new_pwd = input("Enter new password for 'admin': ")
            valid, msg = validate_password(new_pwd)
            if not valid:
                print(f"Error: {msg}")
                continue
            break

    valid, msg = validate_password(new_pwd)
    if not valid:
        print(f"Password complexity error: {msg}")
        sys.exit(1)

    admin_row = db.fetchone("SELECT id FROM users WHERE username = 'admin'")
    if not admin_row:
        create_default_admin(new_pwd)
        print("Admin user 'admin' did not exist and was created with the new password.")
    else:
        ok, err = reset_user_password(admin_row["id"], new_pwd)
        if ok:
            print("Successfully updated password for 'admin'.")
        else:
            print(f"Failed to reset password: {err}")
            sys.exit(1)
    db.close()


def main():
    sys.excepthook = _exception_hook

    if "--reset-admin" in sys.argv:
        _handle_reset_admin_cli()
        sys.exit(0)

    if not _acquire_single_instance():
        print("[Jayraldine's Catering] Application is already running in background/taskbar.")
        _focus_existing_catering_window()
        sys.exit(0)

    if getattr(sys, "frozen", False):
        for plugin_path in os.environ.get("QT_PLUGIN_PATH", "").split(os.pathsep):
            if plugin_path and os.path.isdir(plugin_path):
                QCoreApplication.addLibraryPath(plugin_path)

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QDialog
    from utils.paths import resource_path

    app = QApplication(sys.argv)
    # Performance flag for older Intel HD Graphics (i5-4670 / HD 4600) on Windows 10
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
    app.setStyle("Fusion")

    # Install Real-Time Window Detector to monitor popping/background windows
    try:
        from utils.window_detector import install_window_detector
        install_window_detector(app)
    except Exception as _wd_err:
        print(f"[WINDOW_DETECTOR] Warning: Could not initialize window detector: {_wd_err}")

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

        splash.set_status("Waiting for database...", 50)
        app.processEvents()
        db_thread.join(timeout=8)
        _profile("db wait complete")

        if _db_result[0]:
            splash.set_status("Database connected.", 75)
        else:
            splash.set_status("Running in offline mode.", 75)
        app.processEvents()

        # Ensure authentication tables and default admin account
        from utils.auth import ensure_auth_tables, create_default_admin
        ensure_auth_tables()
        admin_check = db.fetchone("SELECT id FROM users WHERE username = 'admin'")
        if not admin_check:
            create_default_admin()

        splash.set_status("Starting Jayraldine's Catering...", 95)
        app.processEvents()

        # Hide splash screen
        splash.hide()

        # ── Launch MainWindow directly with integrated unified auth & welcome (0 cutouts) ──
        from ui.main_window import MainWindow
        window = MainWindow()
        if os.path.exists(ico_path):
            window.setWindowIcon(QIcon(ico_path))
        _profile("main window created")

        # Start background LAN Sync Server
        try:
            from utils.db_sync_server import start_sync_server_background
            start_sync_server_background()
        except Exception as e:
            log.warning(f"[main] Could not start background LAN Sync Server: {e}")

        # Start background Client Device Monitoring & Heartbeat Tracker
        try:
            from utils.device_tracker import device_tracker
            device_tracker().start()
        except Exception as e:
            log.warning(f"[main] Could not start DeviceTracker: {e}")

        window.showFullScreen()
        window.raise_()
        window.activateWindow()

    except Exception:
        err_txt = traceback.format_exc()
        print(err_txt, file=sys.stderr)
        try:
            log.critical(f"STARTUP FAILED:\n{err_txt}")
            # Also write to crash log for diagnostics
            log_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "JayraldinesCatering")
            os.makedirs(log_dir, exist_ok=True)
            crash_log = os.path.join(log_dir, "startup_crash.txt")
            import datetime
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n--- {datetime.datetime.now()} STARTUP CRASH ---\n{err_txt}\n")
        except Exception:
            pass
        try:
            _app = QApplication.instance()
            if _app:
                QMessageBox.critical(
                    None,
                    "Startup Error — Jayraldine's Catering",
                    f"The application failed to start:\n\n{str(err_txt)[:400]}\n\nPlease contact support."
                )
        except Exception:
            pass
        sys.exit(1)

    app.window_ref = window
    _profile("main window shown")

    def _cleanup_on_quit():
        try:
            from utils.device_tracker import device_tracker
            device_tracker().mark_offline()
        except Exception:
            pass
        try:
            from utils.db_sync_server import stop_sync_server
            stop_sync_server()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass

    app.aboutToQuit.connect(_cleanup_on_quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
