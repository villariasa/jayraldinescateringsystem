"""
Jayraldine's Catering — Tablet App entry point.

A deliberately small, touch-first order-entry client (Tablet-mode.md).
Shares the PC app's SQLite schema for the tables that need to transfer
back and forth (customers, bookings, invoices, payment_records,
booking_additional_charges, booking_menu_items, terms_acknowledgements,
packages, menu_items, package_items) so no separate import/export format
is needed - see utils/importer.py for details.
"""
import sys
import traceback
from pathlib import Path


def _emergency_log(text: str) -> None:
    """Best-effort crash logger writing to console, Android internal app storage,
    and external /sdcard/Download/ so the tablet owner can easily read crash logs."""
    print(text, file=sys.stderr)
    import os
    from datetime import datetime
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


try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except Exception:
    _emergency_log("FATAL: PySide6 failed to import:\n" + traceback.format_exc())
    raise

# Created immediately so a crash dialog can be shown regardless of where in
# startup something fails — staff on the tablet see the error on screen.
app = QApplication(sys.argv)
app.setApplicationName("Jayraldine's Catering")


def _show_crash_dialog(title: str, summary: str, details: str) -> None:
    """Show the error directly on the tablet's screen."""
    _emergency_log(f"DIALOG [{title}]: {summary}\n{details}")
    try:
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle(title)
        box.setText(summary)
        box.setInformativeText("Check your device's Download folder for 'JayraldinesTablet_crash.log' or take a screenshot.")
        box.setDetailedText(details)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()
    except Exception:
        pass


def _install_excepthook(logger):
    def _hook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error("UNCAUGHT EXCEPTION:\n" + text)
        _emergency_log("UNCAUGHT EXCEPTION:\n" + text)
        _show_crash_dialog("Unexpected Error", "The app encountered an error.", text)
    sys.excepthook = _hook


def main():
    try:
        from PySide6.QtGui import QIcon
        import utils.db as db
        from ui.main_window import MainWindow
        from ui import theme
        from version import get_version_string
        from utils.logger import get_logger
    except Exception:
        text = "FATAL during startup imports:\n" + traceback.format_exc()
        _emergency_log(text)
        _show_crash_dialog("Startup Error", "The app failed to start.", text)
        sys.exit(1)

    logger = get_logger()
    _install_excepthook(logger)
    logger.info(f"=== Launching {get_version_string()} ===")

    try:
        app.setStyleSheet(theme.GLOBAL_QSS)

        logo_path = Path(__file__).parent / "assets" / "logo.png"
        if logo_path.exists():
            app.setWindowIcon(QIcon(str(logo_path)))

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
        sys.exit(app.exec())
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
