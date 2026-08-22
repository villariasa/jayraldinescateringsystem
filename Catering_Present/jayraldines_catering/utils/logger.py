"""
Diagnostic Logging System for Jayraldine's Catering.
Provides rotating file logs, global crash/exception hooks, and 1-click diagnostic export.
"""

import os
import sys
import platform
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from version import __version__, APP_NAME
except ImportError:
    __version__ = "3.3.5"
    APP_NAME = "Jayraldine's Catering"


LOGGER_NAME = "jayraldines"
_logger: Optional[logging.Logger] = None
_log_file_path: Optional[Path] = None


def get_log_dir() -> Path:
    """Get standard log directory in %LOCALAPPDATA% or project local fallback."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        log_dir = Path(local_app_data) / "JayraldinesCatering" / "logs"
    else:
        log_dir = Path.home() / ".jayraldines_catering" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except Exception:
        fallback = Path(__file__).resolve().parent.parent / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def setup_logging() -> logging.Logger:
    """Initialize application rotating logger."""
    global _logger, _log_file_path
    if _logger is not None:
        return _logger

    log_dir = get_log_dir()
    _log_file_path = log_dir / "app.log"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        # Rotating File Handler: Max 5MB, keep 3 backup logs
        try:
            file_handler = RotatingFileHandler(
                _log_file_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8"
            )
            file_fmt = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_fmt)
            file_handler.setLevel(logging.INFO)
            logger.addHandler(file_handler)
        except Exception as exc:
            print(f"[Logger] Failed to initialize file handler: {exc}")

        # Console Stream Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_fmt = logging.Formatter(
            "[%(levelname)s] %(message)s"
        )
        console_handler.setFormatter(console_fmt)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    _logger = logger
    logger.info("=" * 60)
    logger.info(f"{APP_NAME} v{__version__} Session Started")
    logger.info(f"OS: {platform.system()} {platform.release()} ({platform.version()}) | Architecture: {platform.machine()}")
    logger.info(f"Python: {platform.python_version()} | Executable: {sys.executable}")
    logger.info(f"Log File: {_log_file_path}")
    logger.info("=" * 60)

    install_exception_hook()
    return _logger


def get_logger() -> logging.Logger:
    """Get active logger instance or initialize default."""
    global _logger
    if _logger is None:
        return setup_logging()
    return _logger


def install_exception_hook():
    """Install global exception hook to capture any unexpected crash/traceback into app.log."""
    def _uncaught_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        log = get_logger()
        log.critical("UNCAUGHT APPLICATION EXCEPTION:", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _uncaught_exception_handler


def get_log_file_path() -> Path:
    """Return the absolute path of the current log file."""
    global _log_file_path
    if _log_file_path is None:
        _log_file_path = get_log_dir() / "app.log"
    return _log_file_path


def export_diagnostic_report(target_dir: Optional[Path] = None) -> Path:
    """
    Generate a self-contained diagnostic text file summarizing system info,
    database status, table counts, and recent error logs for client support.
    """
    log = get_logger()
    log.info("Generating diagnostic report...")

    if target_dir is None:
        desktop = Path.home() / "Desktop"
        target_dir = desktop if desktop.exists() else Path.home()

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = target_dir / f"Jayraldines_Diagnostic_Report_{timestamp_str}.txt"

    # Gather DB stats
    db_stats = []
    try:
        import utils.db as db
        db_engine = getattr(db, "_engine_type", "Unknown")
        db_stats.append(f"Database Engine: {db_engine}")
        if db.is_available():
            db_stats.append("Connection Status: Connected (Healthy)")
            for tbl in ["bookings", "customers", "expenses", "menu_items", "packages", "calendar_events"]:
                try:
                    row = db.fetchone(f"SELECT COUNT(*) AS c FROM {tbl}")
                    cnt = row["c"] if row else 0
                    db_stats.append(f"  • {tbl}: {cnt} records")
                except Exception as e:
                    db_stats.append(f"  • {tbl}: Query error ({e})")
        else:
            db_stats.append("Connection Status: Disconnected / Not Initialized")
    except Exception as exc:
        db_stats.append(f"Database Inspection Failed: {exc}")

    # Read last 150 lines from log file
    log_tail = []
    log_path = get_log_file_path()
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                log_tail = lines[-150:] if len(lines) > 150 else lines
        except Exception as e:
            log_tail = [f"Failed to read log file: {e}"]
    else:
        log_tail = ["Log file does not exist yet."]

    report_content = [
        "==================================================================",
        f"       JAYRALDINE'S CATERING SYSTEM - DIAGNOSTIC REPORT",
        "==================================================================",
        f"Generated At      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Application Ver   : {APP_NAME} v{__version__}",
        f"Operating System  : {platform.system()} {platform.release()} ({platform.version()})",
        f"Processor/Arch    : {platform.processor()} ({platform.machine()})",
        f"Python Version    : {platform.python_version()}",
        f"Log File Location : {log_path}",
        "",
        "------------------------------------------------------------------",
        "  DATABASE STATUS & RECORD COUNTS",
        "------------------------------------------------------------------",
        "\n".join(db_stats),
        "",
        "------------------------------------------------------------------",
        "  RECENT APPLICATION LOGS (TAIL)",
        "------------------------------------------------------------------",
        "".join(log_tail),
        "==================================================================",
        "  END OF REPORT",
        "==================================================================",
    ]

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_content))

    log.info(f"Diagnostic report exported successfully to: {report_file}")
    return report_file
