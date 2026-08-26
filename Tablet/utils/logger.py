"""Minimal rotating file logger for the Tablet App."""
import logging
import os
import sys
import tempfile
from pathlib import Path
from datetime import date

_logger = None


def get_app_data_dir() -> Path:
    """Safely resolve a writable base directory across platforms including Android and Windows."""
    is_android = hasattr(sys, "getandroidapilevel") or bool(os.environ.get("ANDROID_ARGUMENT") or os.environ.get("ANDROID_PRIVATE")) or (sys.platform.startswith("linux") and Path("/sdcard").exists())

    # 1. Android paths (only if running on Android)
    if is_android:
        for cand in (
            Path("/sdcard/Download/JayraldinesTablet"),
            Path("/storage/emulated/0/Download/JayraldinesTablet"),
            Path("/data/data/com.jayraldine.tablet/files"),
        ):
            try:
                cand.mkdir(parents=True, exist_ok=True)
                return cand
            except Exception:
                pass

    # 2. Windows LOCALAPPDATA
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        target = Path(local_app_data) / "JayraldinesCateringTablet"
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except Exception:
            pass

    # 3. Standard Home directory
    try:
        home_dir = Path.home()
        if str(home_dir) not in ("/", "/root"):
            target = home_dir / ".jayraldines_catering_tablet"
            target.mkdir(parents=True, exist_ok=True)
            return target
    except Exception:
        pass

    # 4. Fallback to current working directory
    try:
        target = Path.cwd() / ".jayraldines_catering_tablet"
        target.mkdir(parents=True, exist_ok=True)
        return target
    except Exception:
        pass

    # 5. Last resort: temp directory
    target = Path(tempfile.gettempdir()) / "jayraldines_catering_tablet"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _log_dir() -> Path:
    try:
        d = get_app_data_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        d = Path(tempfile.gettempdir()) / "jayraldines_catering_tablet_logs"
        d.mkdir(parents=True, exist_ok=True)
        return d


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("jayraldines_tablet")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        try:
            log_file = _log_dir() / f"tablet_{date.today().isoformat()}.log"
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(fh)
        except Exception as exc:
            sys.stderr.write(f"Warning: File logging initialization failed ({exc}). Using stdout/stderr logging.\n")

        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)

    _logger = logger
    return logger

