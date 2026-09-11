"""
Window Detection & Monitoring System for Jayraldine's Catering.
Monitors all window, dialog, popup, and top-level widget events across the application
to track popup lifecycles, identify rogue/ghost windows, and log caller stack traces.
"""

import sys
import os
import time
import inspect
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QObject, QEvent, Qt, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QDialog, QMainWindow, QSplashScreen

from utils.logger import get_log_dir

logger = logging.getLogger("jayraldines.window_detector")

_detector_instance: Optional["WindowDetector"] = None


def _format_window_flags(flags: Qt.WindowFlags) -> str:
    """Decodes Qt WindowFlags into human-readable representation."""
    names = []
    val = int(flags)
    
    flag_map = {
        Qt.Widget: "Widget",
        Qt.Window: "Window",
        Qt.Dialog: "Dialog",
        Qt.Sheet: "Sheet",
        Qt.Drawer: "Drawer",
        Qt.Popup: "Popup",
        Qt.Tool: "Tool",
        Qt.ToolTip: "ToolTip",
        Qt.SplashScreen: "SplashScreen",
        Qt.SubWindow: "SubWindow",
        Qt.FramelessWindowHint: "FramelessWindowHint",
        Qt.WindowStaysOnTopHint: "WindowStaysOnTopHint",
        Qt.WindowStaysOnBottomHint: "WindowStaysOnBottomHint",
        Qt.BypassWindowManagerHint: "BypassWindowManagerHint",
        Qt.WindowTransparentForInput: "WindowTransparentForInput",
        Qt.NoDropShadowWindowHint: "NoDropShadowWindowHint",
    }
    
    for flag_val, name in flag_map.items():
        if int(flag_val) and (val & int(flag_val)) == int(flag_val):
            names.append(name)
            
    return "|".join(names) if names else f"0x{val:X}"


def _get_caller_summary() -> str:
    """Extracts a clean, relevant stack trace showing where the window event originated."""
    stack = inspect.stack()
    relevant = []
    
    # Filter out event loop / internal detector frames
    ignore_files = {
        "window_detector.py", "qcoreapplication.py", "qapplication.py",
        "threading.py", "logging", "async_worker.py"
    }
    
    for frame_info in stack[2:12]:
        filename = os.path.basename(frame_info.filename)
        if any(ign in filename.lower() for ign in ignore_files):
            continue
        relevant.append(f"{filename}:{frame_info.lineno} ({frame_info.function})")
        if len(relevant) >= 3:
            break
            
    return " -> ".join(relevant) if relevant else "Qt Event Loop"


class WindowDetector(QObject):
    """
    Global event monitor that logs every window show, hide, focus, or creation event.
    """
    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app = app
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 200
        self._log_file = get_log_dir() / "window_events.log"
        self._active_window_refs = set()

        # Initialize dedicated window event log file
        self._init_log_file()

        # Periodic monitor timer to detect background/ghost windows
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._scan_top_level_windows)
        self._poll_timer.start()

        # Install global event filter on QApplication
        self.app.installEventFilter(self)
        self._log_event("SYSTEM", "WindowDetector initialized and attached to QApplication.")

    def _init_log_file(self):
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*70}\n[WINDOW_DETECTOR] Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*70}\n")
        except Exception as e:
            logger.warning(f"Could not initialize window_events.log: {e}")

    def _log_event(self, event_type: str, details: str, widget_info: Optional[Dict[str, Any]] = None):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{ts}] [{event_type:8s}] {details}"
        
        # Log to Python standard logger
        logger.info(f"[WindowDetector] {event_type}: {details}")

        # Write to dedicated window_events.log
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception:
            pass

        # Store in memory for diagnostic inspection
        entry = {
            "timestamp": ts,
            "event_type": event_type,
            "details": details,
            "widget": widget_info or {}
        }
        self._event_history.append(entry)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Inspects all Qt events passing through the application."""
        if isinstance(watched, QWidget):
            etype = event.type()
            
            # Check if this widget is a window, dialog, popover, or unparented widget
            is_top_level = watched.isWindow() or (watched.parent() is None)
            
            if etype == QEvent.Show:
                if is_top_level or isinstance(watched, (QDialog, QMainWindow, QSplashScreen)):
                    self._on_widget_shown(watched)
            elif etype == QEvent.Hide:
                if is_top_level or isinstance(watched, (QDialog, QMainWindow, QSplashScreen)):
                    self._on_widget_hidden(watched)
            elif etype == QEvent.Close:
                if is_top_level:
                    self._on_widget_closed(watched)
            elif etype == QEvent.WindowActivate:
                if is_top_level:
                    self._log_event("ACTIVATE", f"Window Activated: {self._describe_widget(watched)}")

        return super().eventFilter(watched, event)

    def _describe_widget(self, w: QWidget) -> str:
        """Returns a comprehensive one-line description of a QWidget."""
        cls_name = w.__class__.__name__
        obj_name = w.objectName() or "(no-name)"
        title = w.windowTitle() or "(no-title)"
        parent_cls = w.parent().__class__.__name__ if w.parent() else "None (Top-Level Root)"
        geom = f"{w.x()},{w.y()} {w.width()}x{w.height()}"
        flags_str = _format_window_flags(w.windowFlags())
        is_modal = "MODAL" if w.isModal() else "NON-MODAL"
        is_visible = "VISIBLE" if w.isVisible() else "HIDDEN"
        
        return f"Class={cls_name} | Obj={obj_name} | Title='{title}' | Parent={parent_cls} | Geometry=({geom}) | Flags=[{flags_str}] | State={is_visible},{is_modal}"

    def _on_widget_shown(self, w: QWidget):
        caller = _get_caller_summary()
        desc = self._describe_widget(w)
        
        # Check if parent is None unexpectedly (potential orphaned popping window)
        is_orphan = (w.parent() is None) and not isinstance(w, (QMainWindow, QSplashScreen, QDialog))
        orphan_tag = " [⚠️ POSSIBLE ORPHAN POPUP]" if is_orphan else ""
        
        self._log_event("SHOW", f"🪟 WINDOW SHOWN{orphan_tag}: {desc} | Caller: {caller}", {
            "class": w.__class__.__name__,
            "title": w.windowTitle(),
            "flags": str(w.windowFlags()),
            "parent": str(w.parent()),
            "geometry": f"{w.x()},{w.y()},{w.width()},{w.height()}",
            "caller": caller
        })

    def _on_widget_hidden(self, w: QWidget):
        desc = self._describe_widget(w)
        self._log_event("HIDE", f"🙈 WINDOW HIDDEN: {desc}")

    def _on_widget_closed(self, w: QWidget):
        desc = self._describe_widget(w)
        self._log_event("CLOSE", f"❌ WINDOW CLOSED: {desc}")

    def _scan_top_level_windows(self):
        """Periodic background scan of all active top-level widgets in QApplication."""
        top_levels = self.app.topLevelWidgets()
        visible_wins = [w for w in top_levels if w.isVisible()]
        
        # Detect any unexpected new top-level windows
        curr_refs = {id(w) for w in visible_wins}
        new_wins = [w for w in visible_wins if id(w) not in self._active_window_refs]
        
        if new_wins:
            for nw in new_wins:
                desc = self._describe_widget(nw)
                self._log_event("SCAN_NEW", f"🔎 Background Scan Detected Visible Window: {desc}")
                
        self._active_window_refs = curr_refs

    def get_recent_events(self) -> List[Dict[str, Any]]:
        """Returns the list of recent window events captured by the detector."""
        return list(self._event_history)

    def dump_report(self) -> str:
        """Returns a full formatted text report of current windows and history."""
        lines = [
            "==================================================",
            "        JAYRALDINE'S WINDOW DETECTOR REPORT       ",
            f"  Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "==================================================",
            "\n--- CURRENTLY ACTIVE TOP-LEVEL WINDOWS ---"
        ]
        
        top_levels = self.app.topLevelWidgets()
        for idx, w in enumerate(top_levels, 1):
            lines.append(f"{idx}. {self._describe_widget(w)}")
            
        lines.append(f"\nTotal Top-Level Widgets: {len(top_levels)}")
        lines.append(f"Visible Top-Level Widgets: {len([w for w in top_levels if w.isVisible()])}")
        
        lines.append("\n--- RECENT WINDOW EVENT LOGS (Last 30) ---")
        for ev in self._event_history[-30:]:
            lines.append(f"[{ev['timestamp']}] [{ev['event_type']:8s}] {ev['details']}")
            
        return "\n".join(lines)


def install_window_detector(app: Optional[QApplication] = None) -> WindowDetector:
    """
    Initializes and installs the global WindowDetector on the QApplication instance.
    """
    global _detector_instance
    if _detector_instance is not None:
        return _detector_instance

    if app is None:
        app = QApplication.instance()
        
    if app is None:
        raise RuntimeError("Cannot install WindowDetector: No QApplication instance exists.")

    _detector_instance = WindowDetector(app)
    return _detector_instance


def get_window_detector() -> Optional[WindowDetector]:
    """Returns the active WindowDetector instance, if installed."""
    return _detector_instance
