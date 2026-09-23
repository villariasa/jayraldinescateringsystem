"""Application entry point for the Jayraldine's Catering desktop system.

This module boots the PySide6 (Qt) desktop application. Its responsibilities,
in order, are:

- Configure the process environment before Qt loads (UTF-8 stdio on Windows,
  frozen/PyInstaller Qt plugin paths, GPU/High-DPI hints).
- Install crash/exception plumbing: a ``faulthandler`` for native segfaults and
  a Python ``sys.excepthook`` that logs and shows a user-facing dialog.
- Enforce a single running instance (Windows mutex) and focus the existing
  window instead of launching a duplicate.
- Provide a headless ``--reset-admin`` CLI path for emergency password resets.
- Drive the ``main()`` startup sequence: splash screen, theme/accent, threaded
  DB connect, optional client-mode data sync, auth bootstrap, then create and
  show the main window plus background LAN sync/device-tracking services.

Run directly (``python main.py``) to start the GUI; pass ``--reset-admin`` to
reset the admin password from a terminal.
"""
import sys
import os
import traceback
import time


# On Windows the console defaults to a legacy codepage; force UTF-8 so log
# lines and emoji status strings don't raise UnicodeEncodeError on print.
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

# Startup profiling: record a t0 and, when the env flag is set, log elapsed
# time at each milestone so slow launches can be diagnosed on client machines.
_STARTUP_T0 = time.perf_counter()
_PROFILE_STARTUP = os.environ.get("JAYRALDINES_PROFILE_STARTUP", "").lower() in {"1", "true", "yes", "on"}


def _profile(label: str):
    """Log seconds elapsed since process start for ``label`` (only when profiling is enabled)."""
    if _PROFILE_STARTUP:
        elapsed = time.perf_counter() - _STARTUP_T0
        log.info(f"[startup] {label}: {elapsed:.2f}s")

# When frozen by PyInstaller, Qt's plugins live inside the bundle rather than in
# the site-packages layout Qt expects; point Qt at the first path that exists so
# the platform ("windows") plugin loads and the GUI can actually start.
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

# Configure High DPI scaling policy for clean rendering on Windows laptop displays.
# PassThrough keeps fractional scale factors (e.g. 125%/150%) instead of rounding,
# avoiding blurry text on laptop panels.
if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

# Module-level state: the named-mutex handle (kept alive for the process
# lifetime) and a re-entrancy guard so the exception hook never stacks dialogs.
_MUTEX_HANDLE = None
_IN_EXCEPTION_HOOK = False


def _acquire_single_instance():
    """Try to claim the single-instance mutex on Windows.

    Returns True if this process is the first/only instance (or on non-Windows
    platforms, where no locking is done). Returns False when another instance
    already holds the mutex, signalling the caller to focus that window instead.
    """
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    import ctypes
    try:
        # Give the app a stable taskbar/AppUserModelID identity so Windows groups
        # its windows and shows the correct icon/jump list.
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
    # 183 == ERROR_ALREADY_EXISTS: the mutex was already created by a prior
    # instance, so this one is a duplicate and should not proceed.
    return err != 183 and _MUTEX_HANDLE != 0


def _focus_existing_catering_window():
    """Find the already-running app's main window by title and bring it to front.

    Called when the single-instance check fails so the user's double-click
    surfaces the existing window instead of doing nothing. Windows-only; returns
    True if a matching window was found and restored/focused.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        found_hwnd = []

        # Callback signature required by EnumWindows: (HWND, LPARAM) -> bool.
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def _enum_proc(hwnd, lparam):
            # Return True to keep enumerating, False to stop once we've found it.
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
    """Global last-resort handler for uncaught exceptions.

    Installed as ``sys.excepthook`` so any exception that escapes the app is
    printed, written to the app log and a persistent ``error_log.txt``, and (if
    a Qt app exists) surfaced to the user via a modal dialog rather than
    silently crashing.
    """
    global _IN_EXCEPTION_HOOK
    # Let Ctrl+C behave normally instead of popping an error dialog.
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
        # Append the traceback to a stable, user-writable location so support
        # can retrieve it even if the rotating app log is unavailable.
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
    """Headless emergency reset of the 'admin' password (``--reset-admin`` path).

    Connects to the DB, ensures the auth tables exist, then sets a new admin
    password taken either from the CLI argument after ``--reset-admin`` or from
    an interactive prompt (validated for complexity). Creates the admin account
    if it does not yet exist. Runs entirely in the terminal with no GUI.
    """
    print("====================================================")
    print("  Jayraldine's Catering - Admin Emergency Password Reset")
    print("====================================================")
    import utils.db as db
    from utils.auth import ensure_auth_tables, reset_user_password, validate_password, create_default_admin
    db.connect()
    ensure_auth_tables()

    # Accept the password as the token right after --reset-admin (unless that
    # token is itself another flag), otherwise fall back to a prompt below.
    new_pwd = None
    argv = sys.argv
    idx = argv.index("--reset-admin")
    if idx + 1 < len(argv) and not argv[idx + 1].startswith("-"):
        new_pwd = argv[idx + 1]

    if not new_pwd:
        # Loop the prompt until a complexity-valid password is entered.
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
    """Boot the application: handle CLI flags, then run the GUI startup sequence."""
    # Route all uncaught exceptions through our logging/dialog handler.
    sys.excepthook = _exception_hook

    # Emergency password reset is a headless code path; handle and exit early.
    if "--reset-admin" in sys.argv:
        _handle_reset_admin_cli()
        sys.exit(0)

    # If another copy is already running, focus it and quit instead of duplicating.
    if not _acquire_single_instance():
        print("[Jayraldine's Catering] Application is already running in background/taskbar.")
        _focus_existing_catering_window()
        sys.exit(0)

    # In frozen builds, register the resolved Qt plugin dir(s) as Qt library
    # paths so plugins load reliably regardless of the current working dir.
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

    # Window Detector is intentionally NOT installed: it wrote a log line to
    # a persistent window_events.log file (in the client's AppData folder)
    # on every single window show/hide/close/activate event, growing
    # unbounded over time with no rotation or cap - unwanted disk usage on
    # client machines. Was only ever a debugging aid; see utils/window_detector.py
    # if it's ever needed again for diagnosing a live window-lifecycle bug.

    # Every text field, spinbox, dropdown, and date field starts inert - no
    # wheel, no value change - until the user clicks into it once.
    try:
        from utils.input_activation_guard import install_input_activation_guard
        install_input_activation_guard(app)
        log.info("[INPUT_ACTIVATION_GUARD] Installed successfully.")
    except Exception:
        log.exception("[INPUT_ACTIVATION_GUARD] Failed to initialize - inputs will NOT require a click to activate.")

    # Prefer the multi-resolution .ico; fall back to .png if the icon is missing.
    ico_path = resource_path("assets", "logo.ico")
    if not os.path.exists(ico_path):
        ico_path = resource_path("assets", "logo.png")
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))

    _profile("QApplication")

    # Show the splash immediately so the user gets feedback while heavy
    # imports and the DB connection happen below. processEvents() forces Qt to
    # actually paint it before we block.
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
            # Theming is fundamental; if it fails the UI would be unusable, so abort.
            traceback.print_exc()
            sys.exit(1)

        splash.set_status("Connecting to database...", 25)
        app.processEvents()

        # Connect on a worker thread so a slow/unreachable DB can't freeze the
        # splash. The single-element list is a mutable box for the thread result.
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
        # Bounded wait: after 8s give up and continue in offline mode below.
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

        # ── Client Workstation: Pull full DB snapshot from Server PC ──
        # On machines configured as clients (not the server PC), fetch a fresh
        # full data snapshot over the LAN so they start with current data.
        try:
            from utils.client_sync import is_client_mode, pull_server_snapshot, get_server_url
            if is_client_mode():
                srv_url = get_server_url()
                splash.set_status(f"🔄 Syncing data from server ({srv_url})...", 78)
                app.processEvents()

                _sync_result = [{}]

                def _do_sync():
                    _sync_result[0] = pull_server_snapshot(
                        server_url=srv_url,
                        timeout=12
                    )

                # Run the pull on a thread with a bounded join so a slow server
                # doesn't hang startup; skip the sync if it exceeds the timeout.
                sync_thread = threading.Thread(target=_do_sync, daemon=True)
                sync_thread.start()
                sync_thread.join(timeout=20)

                sr = _sync_result[0]
                if sr.get("success"):
                    total_rows = sum(sr.get("synced", {}).values())
                    splash.set_status(f"✅ Synced {total_rows} rows from server.", 88)
                else:
                    splash.set_status(f"⚠️ Server sync skipped: {sr.get('message', 'offline')}", 88)
                app.processEvents()
        except Exception as _sync_err:
            log.warning(f"[main] Client sync error: {_sync_err}")

        # First-run safety net: guarantee a login account exists.
        admin_check = db.fetchone("SELECT id FROM users WHERE username = 'admin'")
        if not admin_check:
            create_default_admin()

        splash.set_status("Starting Jayraldine's Catering...", 95)
        app.processEvents()

        # Hide splash screen
        splash.hide()

        # ── Launch MainWindow directly with integrated unified auth & welcome (0 cutouts) ──
        # MainWindow owns the login/welcome flow internally, so there's no
        # separate login dialog to swap in and out ("0 cutouts").
        from ui.main_window import MainWindow
        window = MainWindow()
        if os.path.exists(ico_path):
            window.setWindowIcon(QIcon(ico_path))
        _profile("main window created")

        # Start background LAN Sync Server so client workstations/tablets on the
        # network can pull data and diagnostics from this machine. Non-fatal.
        try:
            from utils.db_sync_server import start_sync_server_background
            start_sync_server_background()
        except Exception as e:
            log.warning(f"[main] Could not start background LAN Sync Server: {e}")

        # Start background Client Device Monitoring & Heartbeat Tracker
        # (tracks which client devices are online). Non-fatal.
        try:
            from utils.device_tracker import device_tracker
            device_tracker().start()
        except Exception as e:
            log.warning(f"[main] Could not start DeviceTracker: {e}")

        # Start real-time version watcher & auto-refresh for client workstations (Option 1).
        # Clients poll the server's data version (~1.5s) for near-live refresh and
        # also do a full periodic sync every 5 minutes as a backstop.
        try:
            from utils.client_sync import is_client_mode, start_realtime_version_watcher, start_periodic_sync
            if is_client_mode():
                start_realtime_version_watcher(poll_interval=1.5)
                start_periodic_sync(interval_seconds=300)
                log.info("[main] Real-time sync watcher & periodic sync active.")
        except Exception as e:
            log.warning(f"[main] Could not start real-time sync watcher: {e}")

        # Present the window fullscreen and make sure it grabs focus.
        window.showFullScreen()
        window.raise_()
        window.activateWindow()

    except Exception:
        # Any failure during the startup block above is fatal: log it to the app
        # log and a persistent startup_crash.txt, show a dialog, then exit.
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

    # Keep a reference on the app object so the window isn't garbage-collected.
    app.window_ref = window
    _profile("main window shown")

    def _cleanup_on_quit():
        """Release background services and the DB connection on app shutdown."""
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
    # Enter the Qt event loop; exit the process with its return code.
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
