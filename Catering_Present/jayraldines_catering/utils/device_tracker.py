"""
Device & Terminal Telemetry Tracker for Jayraldine's Catering System.
Maintains persistent client device identification, periodic server heartbeats,
and active user/screen status reporting.
"""

import os
import sys
import uuid
import socket
import platform
import threading
from typing import Optional

from PySide6.QtCore import QObject, QTimer, QSettings
from utils.logger import get_logger
from version import __version__

log = get_logger()

_ORG, _APP = "Jayraldines", "CateringSystem"
_KEY_DEVICE_ID = "device/device_id"


def get_local_ip() -> str:
    """Best-effort discovery of local LAN IP address."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Does not actually establish internet connection
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


def get_persistent_device_id() -> str:
    """Returns a permanent unique device identifier for this physical workstation/terminal."""
    settings = QSettings(_ORG, _APP)
    dev_id = settings.value(_KEY_DEVICE_ID, None)
    if not dev_id:
        try:
            # Generate stable hardware hash
            node = uuid.getnode()
            host = socket.gethostname()
            dev_id = f"DEV-{hex(node)[2:].upper()[:8]}-{abs(hash(host)) % 10000:04d}"
        except Exception:
            dev_id = f"DEV-{uuid.uuid4().hex[:12].upper()}"
        settings.setValue(_KEY_DEVICE_ID, dev_id)
    return str(dev_id)


class DeviceTracker(QObject):
    """
    Client-side heartbeat and session registration service.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._device_id = get_persistent_device_id()
        self._hostname = socket.gethostname()
        self._ip_address = get_local_ip()
        self._os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        self._app_version = f"v{__version__}"
        self._active_module = "Dashboard"

        # 30-second periodic heartbeat timer
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self._on_heartbeat_tick)

        # Debounce timer for active module changes so tab clicks don't spam network writes
        self._module_timer = QTimer(self)
        self._module_timer.setSingleShot(True)
        self._module_timer.setInterval(15_000)
        self._module_timer.timeout.connect(self._on_module_timer_tick)
        self._last_reg_time: float = 0.0

        self._initialized = True

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def ip_address(self) -> str:
        return self._ip_address

    def start(self):
        """Register device with database and start background heartbeat."""
        self.register_device()
        if not self._timer.isActive():
            self._timer.start()

    def register_device(self):
        """Asynchronously upsert device session record to avoid blocking UI."""
        import time
        self._last_reg_time = time.time()
        def _async_reg():
            try:
                from utils.auth import SessionManager
                from utils.db import upsert_device_session

                u = SessionManager.current_user() or {}
                username = u.get("username", "")
                role = u.get("role", "Staff")

                upsert_device_session(
                    device_id=self._device_id,
                    hostname=self._hostname,
                    ip_address=self._ip_address,
                    os_info=self._os_info,
                    app_version=self._app_version,
                    username=username,
                    user_role=role,
                    active_module=self._active_module,
                    status="online"
                )
            except Exception as e:
                log.debug(f"[DeviceTracker] Registration ping error: {e}")

        threading.Thread(target=_async_reg, daemon=True).start()

    def set_active_module(self, module_name: str):
        """Broadcast user navigation change to server with debouncing."""
        if self._active_module == module_name:
            return
        self._active_module = module_name
        import time
        # If never registered or > 60s since last registration, register immediately; otherwise debounce
        if self._last_reg_time == 0 or (time.time() - self._last_reg_time) > 60.0:
            self.register_device()
        else:
            self._module_timer.start(15_000)

    def _on_module_timer_tick(self):
        self.register_device()

    def _on_heartbeat_tick(self):
        """Background heartbeat ping."""
        def _async_hb():
            try:
                from utils.auth import SessionManager
                from utils.db import update_device_heartbeat

                u = SessionManager.current_user() or {}
                username = u.get("username", "")
                role = u.get("role", "Staff")

                update_device_heartbeat(
                    device_id=self._device_id,
                    username=username,
                    user_role=role,
                    active_module=self._active_module,
                    status="online",
                    hostname=self._hostname,
                    ip_address=self._ip_address,
                    os_info=self._os_info,
                    app_version=self._app_version
                )
            except Exception as e:
                log.debug(f"[DeviceTracker] Heartbeat error: {e}")

        threading.Thread(target=_async_hb, daemon=True).start()

    def mark_offline(self):
        """Mark device session as offline on clean exit."""
        self._timer.stop()
        try:
            from utils.db import set_device_offline
            set_device_offline(self._device_id)
        except Exception:
            pass


def device_tracker() -> DeviceTracker:
    return DeviceTracker()
