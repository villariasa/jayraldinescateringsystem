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
    """Best-effort crash log that works even if utils.logger itself failed
    to import, or the crash happened before get_logger() was called (e.g. a
    missing/broken native recipe on Android) — writes to the same app-data
    directory logger.py resolves to, plus stderr (which python-for-android's
    Qt bootstrap pipes into `adb logcat`)."""
    print(text, file=sys.stderr)
    try:
        import os
        android_private = os.environ.get("ANDROID_PRIVATE") or os.environ.get("ANDROID_ARGUMENT")
        base = Path(android_private) / "JayraldinesCateringTablet" if android_private else Path.cwd()
        base.mkdir(parents=True, exist_ok=True)
        with open(base / "crash.log", "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass


try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except Exception:
    # If PySide6 itself won't import, there is no way to show anything on
    # screen — this is the one crash mode that can only be diagnosed via
    # adb logcat / the crash.log file, since Qt is what would render the
    # dialog in the first place.
    _emergency_log("FATAL: PySide6 failed to import:\n" + traceback.format_exc())
    raise

# Created immediately so a crash dialog can be shown regardless of where in
# startup something fails — the whole point is staff on the tablet see the
# actual error on screen instead of the app just vanishing.
app = QApplication(sys.argv)
app.setApplicationName("Jayraldine's Catering Tablet")


def _show_crash_dialog(title: str, summary: str, details: str) -> None:
    """Show the error directly on the tablet's screen. This is the primary
    way staff (with no laptop/adb on hand) find out why the app closed —
    logcat/crash.log are the fallback for when even this fails."""
    try:
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle(title)
        box.setText(summary)
        box.setInformativeText("Please take a screenshot of this and show it to support.")
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
        _show_crash_dialog("Unexpected Error", "Something went wrong.", text)
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
