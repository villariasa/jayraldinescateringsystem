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
_daily_handler: Optional["DailyFileHandler"] = None


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


def get_daily_log_filename(dt: Optional[datetime] = None) -> str:
    """Return date-stamped log file name, e.g. 'app_2026-08-22.log'."""
    d = dt or datetime.now()
    return f"app_{d.strftime('%Y-%m-%d')}.log"


def get_log_file_path(dt: Optional[datetime] = None) -> Path:
    """Return the absolute path of the date-stamped daily log file."""
    return get_log_dir() / get_daily_log_filename(dt)


class DailyFileHandler(logging.Handler):
    """
    Custom logging handler that dynamically creates and writes to daily log files
    based on the current date (e.g. app_2026-08-22.log). Seamlessly rolls over
    to a new date-stamped file when midnight passes.
    """
    def __init__(self, log_dir: Path, encoding="utf-8"):
        super().__init__()
        self.log_dir = log_dir
        self.encoding = encoding
        self._current_date_str: Optional[str] = None
        self._file_handler: Optional[RotatingFileHandler] = None

    def _get_active_handler(self) -> RotatingFileHandler:
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self._current_date_str != today_str or self._file_handler is None:
            if self._file_handler is not None:
                try:
                    self._file_handler.close()
                except Exception:
                    pass
            self._current_date_str = today_str
            file_path = self.log_dir / f"app_{today_str}.log"
            self._file_handler = RotatingFileHandler(
                file_path,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding=self.encoding
            )
            if self.formatter:
                self._file_handler.setFormatter(self.formatter)
            self._file_handler.setLevel(self.level)
        return self._file_handler

    def emit(self, record: logging.LogRecord):
        try:
            h = self._get_active_handler()
            h.emit(record)
        except Exception:
            self.handleError(record)

    def flush(self):
        if self._file_handler is not None:
            try:
                self._file_handler.flush()
            except Exception:
                pass
        super().flush()

    def close(self):
        if self._file_handler is not None:
            try:
                self._file_handler.close()
            except Exception:
                pass
            self._file_handler = None
        super().close()


def setup_logging() -> logging.Logger:
    """Initialize application daily logger."""
    global _logger, _daily_handler
    if _logger is not None:
        return _logger

    log_dir = get_log_dir()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        # Daily Date-Separated File Handler
        try:
            _daily_handler = DailyFileHandler(log_dir, encoding="utf-8")
            file_fmt = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            _daily_handler.setFormatter(file_fmt)
            _daily_handler.setLevel(logging.INFO)
            logger.addHandler(_daily_handler)
        except Exception as exc:
            print(f"[Logger] Failed to initialize daily file handler: {exc}")

        # Console Stream Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_fmt = logging.Formatter(
            "[%(levelname)s] %(message)s"
        )
        console_handler.setFormatter(console_fmt)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    _logger = logger
    current_log_path = get_log_file_path()
    logger.info("=" * 60)
    logger.info(f"{APP_NAME} v{__version__} Session Started")
    logger.info(f"OS: {platform.system()} {platform.release()} ({platform.version()}) | Architecture: {platform.machine()}")
    logger.info(f"Python: {platform.python_version()} | Executable: {sys.executable}")
    logger.info(f"Daily Log File: {current_log_path}")
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
    """Install global exception hook to capture any unexpected crash/traceback into daily log file."""
    def _uncaught_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        log = get_logger()
        log.critical("UNCAUGHT APPLICATION EXCEPTION:", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _uncaught_exception_handler


def get_log_file_path(dt: Optional[datetime] = None) -> Path:
    """Return the absolute path of the date-stamped daily log file."""
    return get_log_dir() / get_daily_log_filename(dt)


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
