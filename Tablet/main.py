"""
Jayraldine's Catering — Tablet App entry point.

A deliberately small, touch-first order-entry client (Tablet-mode.md).
Shares the PC app's SQLite schema for the tables that need to transfer
back and forth (customers, bookings, invoices, payment_records,
booking_additional_charges, booking_menu_items, terms_acknowledgements,
packages, menu_items, package_items) so no separate import/export format
is needed - see utils/importer.py for details.
"""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

_qt_app = None


def _emergency_log(text: str) -> None:
    """Best-effort crash logger writing to console, Android internal app storage,
    and external /sdcard/Download/ so the tablet owner can easily read crash logs."""
    print(text, file=sys.stderr)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n==================== [{timestamp}] CRASH / STARTUP EVENT ====================\n{text}\n"

    # 1. Try public Download folder on Android tablets
    for public_path in (
        Path("/sdcard/Download/JayraldinesTablet_crash.log"),
        Path("/storage/emulated/0/Download/JayraldinesTablet_crash.log"),
    ):
        try:
            public_path.parent.mkdir(parents=True, exist_ok=True)
            with open(public_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

    # 2. Try App Data / Android private storage
    try:
        android_private = os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_ARGUMENT")
        base = Path(android_private) / "JayraldinesCateringTablet" if android_private else (Path.home() / ".jayraldines_catering_tablet")
        base.mkdir(parents=True, exist_ok=True)
        with open(base / "crash.log", "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def _show_android_native_dialog(title: str, message: str) -> bool:
    """Attempt to show an Android native Java AlertDialog on screen if Qt UI is not available."""
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        for act_name in (
            "org.qtproject.qt.android.bindings.QtActivity",
            "org.kivy.android.PythonActivity",
        ):
            try:
                activity_class = autoclass(act_name)
                activity = getattr(activity_class, "mActivity", None)
                if activity is not None:
                    AlertDialog = autoclass("android.app.AlertDialog$Builder")
                    builder = AlertDialog(activity)
                    builder.setTitle(title)
                    builder.setMessage(message)
                    builder.setPositiveButton("OK", None)

                    class RunnableImpl(PythonJavaClass):
                        __javainterfaces__ = ["java/lang/Runnable"]
                        def __init__(self, b):
                            super().__init__()
                            self.b = b
                        @java_method("()V")
                        def run(self):
                            self.b.show()

                    activity.runOnUiThread(RunnableImpl(builder))
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _show_crash_dialog(title: str, summary: str, details: str) -> None:
    """Show the error directly on the tablet/phone screen in a dedicated scrollable window."""
    _emergency_log(f"DIALOG [{title}]: {summary}\n{details}")
    
    # Try Android native alert first if available
    _show_android_native_dialog(title, f"{summary}\n\n{details}")

    try:
        from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
        global _qt_app
        if not _qt_app:
            _qt_app = QApplication.instance() or QApplication(sys.argv)
        
        dlg = QDialog()
        dlg.setWindowTitle(title)
        dlg.resize(600, 450)
        dlg.setStyleSheet(
            "QDialog { background-color: #1e1e2e; color: #f5e0dc; } "
            "QLabel { color: #f38ba8; font-size: 16px; } "
            "QTextEdit { background-color: #11111b; color: #a6e3a1; font-family: monospace; font-size: 12px; } "
            "QPushButton { background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 10px; border-radius: 5px; }"
        )
        
        layout = QVBoxLayout(dlg)
        
        lbl = QLabel(f"<b>⚠️ {title}</b><br>{summary}")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        txt = QTextEdit()
        txt.setPlainText(details)
        txt.setReadOnly(True)
        layout.addWidget(txt)
        
        lbl_hint = QLabel("<small>Log saved to Download/JayraldinesTablet_crash.log</small>")
        lbl_hint.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(lbl_hint)
        
        btn = QPushButton("Close App")
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        
        dlg.exec()
    except Exception as exc:
        _emergency_log(f"Failed to display GUI crash dialog: {exc}")


def _install_excepthook(logger=None):
    def _hook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        if logger:
            logger.error("UNCAUGHT EXCEPTION:\n" + text)
        _emergency_log("UNCAUGHT EXCEPTION:\n" + text)
        _show_crash_dialog("Unexpected Error", "The app encountered an error.", text)
    sys.excepthook = _hook


# Install exception hook immediately before any imports
_install_excepthook()


def _request_android_permissions() -> None:
    """Trigger the Android system dialog asking user to allow storage permissions."""
    try:
        from jnius import autoclass
        VERSION = autoclass("android.os.Build$VERSION")
        sdk_int = VERSION.SDK_INT

        for act_name in (
            "org.qtproject.qt.android.bindings.QtActivity",
            "org.kivy.android.PythonActivity",
        ):
            try:
                activity_class = autoclass(act_name)
                activity = getattr(activity_class, "mActivity", None)
                if activity is not None:
                    permissions = [
                        "android.permission.WRITE_EXTERNAL_STORAGE",
                        "android.permission.READ_EXTERNAL_STORAGE",
                    ]
                    if sdk_int >= 33:  # Android 13/14+
                        permissions.extend([
                            "android.permission.READ_MEDIA_IMAGES",
                            "android.permission.POST_NOTIFICATIONS",
                        ])
                    activity.requestPermissions(permissions, 101)
                    break
            except Exception:
                continue
    except Exception:
        pass


def main():
    global _qt_app

    # Prompt Android runtime permission dialog on startup
    _request_android_permissions()

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QIcon
        import utils.db as db
        from ui.main_window import MainWindow
        from ui import theme
        from version import get_version_string
        from utils.logger import get_logger
    except Exception:
        text = "FATAL during startup imports:\n" + traceback.format_exc()
        _emergency_log(text)
        _show_crash_dialog("Startup Error", "The app failed to start due to missing dependencies.", text)
        sys.exit(1)

    logger = get_logger()
    _install_excepthook(logger)
    logger.info(f"=== Launching {get_version_string()} ===")

    try:
        if not _qt_app:
            _qt_app = QApplication.instance() or QApplication(sys.argv)
        _qt_app.setApplicationName("Jayraldine's Catering")
        _qt_app.setStyleSheet(theme.GLOBAL_QSS)

        logo_path = Path(__file__).parent / "assets" / "logo.png"
        if logo_path.exists():
            _qt_app.setWindowIcon(QIcon(str(logo_path)))

        if not db.connect():
            logger.error("FATAL: could not connect to the tablet's local database.")
            _show_crash_dialog(
                "Database Error",
                "Could not connect to the tablet's local database.",
                "db.connect() returned False. Check utils/db.py and utils/sqlite_schema.py "
                "for the resolved database path and whether it's writable on this device.",
            )
            sys.exit(1)

        window = MainWindow()
        window.show()
        sys.exit(_qt_app.exec())
    except SystemExit:
        raise
    except Exception:
        text = "FATAL during startup:\n" + traceback.format_exc()
        logger.error(text)
        _emergency_log(text)
        _show_crash_dialog("Startup Error", "The app hit an error and needs to close.", text)
        raise


if __name__ == "__main__":
    main()
