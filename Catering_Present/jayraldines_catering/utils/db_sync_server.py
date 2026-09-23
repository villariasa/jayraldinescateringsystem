"""
utils/db_sync_server.py
-----------------------
Built-in LAN Synchronization HTTP Server for Jayraldine's Catering.
Listens on 0.0.0.0:8000 (LAN broadcast) to allow tablet kiosk apps and
remote laptops to synchronize orders, customers, and menu catalog directly
with the central PostgreSQL database over Wi-Fi without third-party services.
"""

import json
import socket
import sys
import threading
import base64
import io
import mimetypes
import re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import time

import utils.db as db
import utils.repository as repo
from utils.logger import get_logger

logger = get_logger()

_SERVER_INSTANCE = None
_SERVER_THREAD = None
_MAX_TABLET_IMAGE_BYTES = 12 * 1024 * 1024


def _desktop_package_image_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "images" / "packages"


def _desktop_menu_image_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "images" / "menu"


def _image_ext_from_mime(mime: str) -> str:
    mime = (mime or "").lower().strip()
    if mime == "image/png":
        return ".png"
    if mime in ("image/webp", "image/x-webp"):
        return ".webp"
    if mime in ("image/jpeg", "image/jpg"):
        return ".jpg"
    return ".jpg"


def _decode_image_data_uri(image_data: str) -> tuple[bytes, str, str]:
    raw = (image_data or "").strip()
    if not raw:
        raise ValueError("Image data is empty.")

    mime = "image/jpeg"
    payload = raw
    if raw.startswith("data:"):
        header, sep, b64 = raw.partition(",")
        if not sep:
            raise ValueError("Invalid image data URI.")
        match = re.match(r"^data:([^;]+);base64$", header, flags=re.IGNORECASE)
        if not match:
            raise ValueError("Only base64 image data URIs are supported.")
        mime = match.group(1).lower()
        payload = b64

    if not mime.startswith("image/"):
        raise ValueError("Uploaded file must be an image.")

    try:
        data = base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image payload: {exc}") from exc

    if len(data) > _MAX_TABLET_IMAGE_BYTES:
        max_mb = _MAX_TABLET_IMAGE_BYTES // (1024 * 1024)
        raise ValueError(f"Image is too large. Maximum allowed size is {max_mb} MB.")

    return data, mime, _image_ext_from_mime(mime)


def get_local_ip() -> str:
    """Best-effort discovery of this computer's primary LAN IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets, just routes socket to find local interface IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def _image_to_data_uri(img_str: str) -> str:
    """Encodes a local disk image into an optimized base64 data URI for tablet PWA/APK rendering."""
    if not img_str:
        return ""
    img_clean = str(img_str).strip()
    if img_clean.startswith("data:image/"):
        return img_clean

    this_dir = Path(__file__).resolve().parent
    candidate_paths = [
        Path(img_clean),
        Path.cwd() / img_clean,
        this_dir.parent / img_clean,
        this_dir.parent.parent / img_clean,
        this_dir.parent / "assets" / "images" / img_clean,
        this_dir.parent / "assets" / img_clean,
    ]

    for p in candidate_paths:
        if p.exists() and p.is_file():
            try:
                # Try Pillow optimization first for fast network payload
                try:
                    from PIL import Image
                    with Image.open(p) as im:
                        im = im.convert("RGB")
                        im.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        im.save(buf, format="JPEG", quality=82, optimize=True)
                        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                        return f"data:image/jpeg;base64,{b64}"
                except Exception:
                    pass

                mime, _ = mimetypes.guess_type(str(p))
                if not mime:
                    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
                with open(p, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:{mime};base64,{b64}"
            except Exception as e:
                logger.warning(f"[SyncServer] Error encoding image {p}: {e}")
                break

    return img_clean


_db_version: int = int(time.time() * 1000)

_last_bump_signal_time: float = 0.0

_IGNORED_REVISION_TABLES = (
    "device_sessions", "audit_logs", "login_attempts",
    "user_sessions", "app_logs", "deleted_records"
)

def is_business_write_sql(sql: str) -> bool:
    """Return False if the write targets telemetry, heartbeats, or audit logs."""
    if not sql:
        return False
    s = sql.lower()
    return not any(tbl in s for tbl in _IGNORED_REVISION_TABLES)

def get_db_version() -> int:
    global _db_version
    return _db_version

def bump_db_version(emit_signal: bool = True) -> int:
    global _db_version, _last_bump_signal_time
    _db_version = max(int(time.time() * 1000), _db_version + 1)
    logger.debug(f"[SyncServer] Database revision bumped to {_db_version}")

    # Debounce UI signal emission to at most once per 1.0s to avoid flooding Qt event loop
    if emit_signal:
        now = time.time()
        if now - _last_bump_signal_time >= 1.0:
            _last_bump_signal_time = now
            try:
                from utils.signals import app_events
                ev = app_events()
                ev.data_changed.emit()
            except Exception as exc:
                logger.debug(f"[SyncServer] Could not dispatch UI refresh signal: {exc}")

    return _db_version


_last_session_record: dict = {}


class SyncServerHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests from tablet kiosk apps for LAN sync."""

    def _set_cors_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        # Echo back whatever headers the browser/WebView's preflight actually
        # asked for (falling back to the static list below when none was
        # sent, e.g. for a non-preflight response). A hardcoded allow-list
        # here previously omitted the X-Device-Id/X-Device-Host/X-Device-OS
        # headers the Tablet PWA/APK sends on every real request - the server
        # itself reads those headers (see _record_client_session below), but
        # since they weren't in this allow-list, the browser's CORS preflight
        # check silently rejected them before the real request could even be
        # sent, even though a plain top-level navigation (which never
        # triggers CORS) worked fine and looked "connected".
        requested_headers = self.headers.get("Access-Control-Request-Headers")
        self.send_header(
            "Access-Control-Allow-Headers",
            requested_headers or "Content-Type, Authorization, Accept, X-Requested-With, ngrok-skip-browser-warning, X-Device-Id, X-Device-Host, X-Device-OS"
        )
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def _record_client_session(self, payload=None, query_params=None):
        """Auto-registers and tracks connecting mobile/tablet/client devices into device_sessions table."""
        try:
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
            now = time.time()
            # Throttle device_session updates to once per 60s per client IP to eliminate continuous DB writes on routine pings
            if now - _last_session_record.get(client_ip, 0) < 60.0:
                return

            user_agent = self.headers.get("User-Agent", "") or ""

            dev_id = None
            hostname = None
            os_info = None
            app_version = "v1.26.12"
            active_module = "Customer Booking Kiosk"

            if payload and isinstance(payload, dict):
                dev_id = payload.get("device_id")
                hostname = payload.get("hostname")
                os_info = payload.get("os_info")
                app_version = payload.get("app_version") or app_version
                active_module = payload.get("active_module") or active_module

            if not dev_id and query_params:
                dev_id = query_params.get("device_id", [None])[0]
                hostname = query_params.get("hostname", [None])[0]
                os_info = query_params.get("os_info", [None])[0]
                app_version = query_params.get("app_version", [app_version])[0]
                active_module = query_params.get("active_module", [active_module])[0]

            # Also inspect incoming custom HTTP headers if present
            if not dev_id and self.headers.get("X-Device-Id"):
                dev_id = self.headers.get("X-Device-Id")
            if not hostname and self.headers.get("X-Device-Host"):
                hostname = self.headers.get("X-Device-Host")
            if not os_info and self.headers.get("X-Device-OS"):
                os_info = self.headers.get("X-Device-OS")

            # Accurate detection: Mobile Phone vs Tablet
            is_android = "Android" in user_agent or "com.jayraldines" in user_agent
            is_ios = "iPhone" in user_agent or "iPad" in user_agent
            # Android smartphones include "Mobile" token; tablets omit "Mobile"
            is_mobile_phone = "Mobile" in user_agent or "iPhone" in user_agent
            is_tablet = "Tablet" in user_agent or "iPad" in user_agent or (is_android and not is_mobile_phone)

            device_type = "Tablet" if is_tablet else ("Mobile Phone" if is_mobile_phone else "Mobile Device")
            platform_name = "Android" if is_android else ("iOS" if is_ios else "Mobile")
            clean_ip = client_ip.replace(":", "_").replace(".", "_")

            if not dev_id:
                prefix = "phone" if device_type == "Mobile Phone" else "tablet"
                dev_id = f"{prefix}-{clean_ip}"

            if not hostname:
                hostname = f"📱 {platform_name} {device_type} ({client_ip})"

            if not os_info:
                if is_android:
                    tag = "APK" if "com.jayraldines" in user_agent else "Web/PWA"
                    os_info = f"Android {device_type} ({tag})"
                elif is_ios:
                    os_info = f"iOS {device_type} (Safari/PWA)"
                else:
                    os_info = f"{device_type} ({user_agent[:60]})" if user_agent else "Client Terminal"

            _last_session_record[client_ip] = now
            db.upsert_device_session(
                device_id=dev_id,
                hostname=hostname,
                ip_address=client_ip,
                os_info=os_info,
                app_version=app_version,
                username="Mobile Kiosk Guest",
                user_role="Kiosk Terminal",
                active_module=active_module,
                status="online"
            )
        except Exception as exc:
            logger.debug(f"[SyncServer] Device registration ignored: {exc}")

    def do_OPTIONS(self):
        self._set_cors_headers(204)

    def do_HEAD(self):
        self.do_GET()

    def log_message(self, format, *args):
        # Override to avoid polluting stdout with routine health pings
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)

        # Track device session on every incoming tablet request
        self._record_client_session(query_params=query_params)

        if path in ("/health", "/api/health"):
            self._set_cors_headers(200)
            res = {
                "status": "ok",
                "app": "Jayraldine's Catering Central Server Hub",
                "server_ip": get_local_ip(),
                "port": 8000,
                "version": get_db_version(),
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if path in ("/api/sync/version", "/api/db/version"):
            self._set_cors_headers(200)
            res = {
                "status": "ok",
                "version": get_db_version(),
                "server_ip": get_local_ip(),
                "timestamp": time.time(),
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if path == "/test":
            self._handle_test_page()
            return

        if path == "/api/sync/lan-status":
            self._handle_lan_status(parsed)
            return

        if path == "/api/sync/device-offline":
            self._handle_device_offline(query_params=query_params)
            return

        # Direct Tablet Android APK Download Endpoint
        if path in (
            "/download-apk",
            "/download/apk",
            "/api/download/apk",
            "/api/download-apk",
            "/jayraldines_catering.apk",
            "/jayraldines-tablet.apk",
            "/jayraldines_catering_tablet.apk",
            "/tablet.apk",
            "/app.apk",
        ) or (path.endswith(".apk") and not path.startswith("/api/")):
            self._handle_apk_download()
            return

        if path in ("/", "/index.html"):
            if self._serve_static_file("index.html"):
                return

        # Attempt to serve static files from Tablet_PWA/frontend or desktop assets
        if self._serve_static_file(path):
            return

        if path == "/api/info":
            self._set_cors_headers(200)
            apk_path, apk_size, apk_name, apk_ver = self._find_tablet_apk()
            res = {
                "status": "ok",
                "app": "Jayraldine's Catering Central Server Hub",
                "server_ip": get_local_ip(),
                "port": 8000,
                "test_url": f"http://{get_local_ip()}:8000/test",
                "kiosk_url": f"http://{get_local_ip()}:8000/index.html",
                "apk_download_url": f"http://{get_local_ip()}:8000/download-apk" if apk_path else None,
                "apk_filename": apk_name or None,
                "apk_version": apk_ver or None,
                "apk_size_bytes": apk_size,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        if path == "/api/db/users":
            self._handle_db_users()
            return

        if path == "/api/db/snapshot":
            self._handle_db_snapshot()
            return

        if path == "/api/images/download":
            self._handle_image_download(query_params=query_params)
            return

        self._set_cors_headers(404)
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def _get_tablet_version(self) -> str:
        """Extracts the compiled tablet APK version (e.g. '2.1.4')."""
        this_file = Path(__file__).resolve()
        # 1. Check output-metadata.json in APK build output
        meta_candidates = [
            Path(r"C:\Testing\jayraldinescateringsystem\Tablet_Android_APK\app\build\outputs\apk\debug\output-metadata.json"),
            Path(r"C:\Testing\jayraldinescateringsystem\Tablet_Android_APK\app\build\outputs\apk\release\output-metadata.json"),
        ]
        for p in this_file.parents:
            meta_candidates.append(p / "Tablet_Android_APK" / "app" / "build" / "outputs" / "apk" / "debug" / "output-metadata.json")
            meta_candidates.append(p / "Tablet_Android_APK" / "app" / "build" / "outputs" / "apk" / "release" / "output-metadata.json")

        for mc in meta_candidates:
            if mc.is_file():
                try:
                    data = json.loads(mc.read_text(encoding="utf-8"))
                    v = data.get("elements", [{}])[0].get("versionName")
                    if v:
                        return str(v).lstrip("v")
                except Exception:
                    pass

        # 2. Check Tablet_Android_APK/app/build.gradle
        gradle_candidates = [
            Path(r"C:\Testing\jayraldinescateringsystem\Tablet_Android_APK\app\build.gradle"),
        ]
        for p in this_file.parents:
            gradle_candidates.append(p / "Tablet_Android_APK" / "app" / "build.gradle")

        for gc in gradle_candidates:
            if gc.is_file():
                try:
                    m = re.search(r'versionName\s+["\']([^"\']+)["\']', gc.read_text(encoding="utf-8"))
                    if m:
                        return m.group(1).lstrip("v")
                except Exception:
                    pass

        # 3. Check versioned files in workspace root
        for p in this_file.parents:
            try:
                for f in p.glob("jayraldines_catering_v*.apk"):
                    m = re.search(r'jayraldines_catering_v([0-9.]+)\.apk', f.name)
                    if m:
                        return m.group(1)
            except Exception:
                pass

        return "2.1.4"

    def _find_tablet_apk(self):
        """Finds the newest compiled tablet APK file, its size, versioned filename, and version."""
        ver = self._get_tablet_version()
        versioned_filename = f"jayraldines_catering_v{ver}.apk"

        this_file = Path(__file__).resolve()
        candidate_paths = [
            Path(rf"C:\Testing\jayraldinescateringsystem\jayraldines_catering_v{ver}.apk"),
            Path(r"C:\Testing\jayraldinescateringsystem\jayraldines_catering.apk"),
            Path(r"C:\Testing\jayraldinescateringsystem\Tablet_Android_APK\app\build\outputs\apk\debug\app-debug.apk"),
            Path(r"C:\Testing\jayraldinescateringsystem\Tablet_Android_APK\app\build\outputs\apk\release\app-release.apk"),
            Path(r"C:\Testing\jayraldinescateringsystem\jayraldines_catering_tablet.apk"),
        ]
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidate_paths.extend([
                exe_dir / versioned_filename,
                exe_dir / "jayraldines_catering.apk",
            ])
            try:
                for apk in exe_dir.glob("*.apk"):
                    candidate_paths.append(apk)
            except Exception:
                pass

        for p in this_file.parents:
            if p.is_dir():
                try:
                    for apk in p.glob("jayraldines_catering_v*.apk"):
                        if apk.is_file():
                            candidate_paths.append(apk)
                    for apk in p.glob("*.apk"):
                        if apk.is_file():
                            candidate_paths.append(apk)
                except Exception:
                    pass

        existing = []
        seen = set()
        for c in candidate_paths:
            try:
                c_res = c.resolve()
                if c_res.is_file() and str(c_res) not in seen and c_res.stat().st_size > 100000:
                    seen.add(str(c_res))
                    is_exact_ver = c_res.name == versioned_filename
                    existing.append((c_res, c_res.stat().st_mtime, c_res.stat().st_size, is_exact_ver))
            except Exception:
                pass

        if not existing:
            return None, 0, versioned_filename, ver

        # Prefer exact version match, then newest timestamp
        existing.sort(key=lambda x: (1 if x[3] else 0, x[1]), reverse=True)
        newest_path, _, size, _ = existing[0]
        return newest_path, size, versioned_filename, ver

    def _handle_apk_download(self):
        """Streams the latest compiled tablet APK file with versioned filename (e.g. jayraldines_catering_v2.1.4.apk)."""
        apk_path, file_size, download_filename, ver = self._find_tablet_apk()
        if not apk_path or not apk_path.is_file():
            self._set_cors_headers(404, "text/html; charset=utf-8")
            error_html = f"""<!DOCTYPE html><html><body style="font-family:sans-serif; background:#0B0F19; color:#fff; padding:40px; text-align:center;">
                <h2>📱 Tablet APK Not Found</h2>
                <p style="color:#9CA3AF;">The Android Tablet APK ({download_filename}) has not been compiled on the host PC yet.</p>
                <p style="color:#F59E0B;">Run <code>build_apk.bat</code> on the host PC to compile the APK, then retry downloading.</p>
            </body></html>"""
            self.wfile.write(error_html.encode("utf-8"))
            return

        try:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/vnd.android.package-archive")
            self.send_header("Content-Disposition", f'attachment; filename="{download_filename}"')
            self.send_header("Content-Length", str(file_size))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()

            with open(apk_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            logger.info(f"[SyncServer] Streamed versioned APK '{download_filename}' ({file_size} bytes) to {self.client_address[0]}")
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as exc:
            logger.warning(f"[SyncServer] Error streaming APK download: {exc}")

    def _handle_test_page(self):
        client_ip = self.client_address[0]
        server_ip = get_local_ip()
        db_online = False
        db_engine = db.get_engine_type()
        cfg = db.get_db_config()
        db_name = cfg.get("dbname", "jayraldines_catering")
        try:
            conn = db.get_connection()
            if conn:
                res = db.fetchone("SELECT 1 AS alive")
                if res and res.get("alive") == 1:
                    db_online = True
        except Exception:
            pass

        db_status_badge = '<span style="color:#22C55E; font-weight:700;">🟢 Online &amp; Connected</span>' if db_online else '<span style="color:#EF4444; font-weight:700;">🔴 Database Offline</span>'

        apk_path, apk_size, apk_filename, apk_ver = self._find_tablet_apk()
        apk_size_mb = f"{apk_size / (1024 * 1024):.1f} MB" if apk_size > 0 else "Ready"
        apk_btn_html = f"""
    <a href="/download-apk" download="{apk_filename}" class="btn" style="background: linear-gradient(135deg, #10B981, #059669); color: white; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 15px; margin-top: 12px; text-decoration: none; font-weight: 700; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);">
      <span>📱</span> <span>Download Tablet Android APK (v{apk_ver} • {apk_size_mb})</span>
    </a>
    <div style="font-size: 12px; color: #9CA3AF; text-align: center; margin-top: 6px;">File: <code>{apk_filename}</code></div>
    """ if apk_path else ""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Jayraldine's Catering — LAN Hub Diagnostic</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0B0F19; color: #F9FAFB; padding: 24px; margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; box-sizing: border-box; }}
    .card {{ background: #111827; border: 1px solid #1F2937; border-radius: 16px; padding: 32px; max-width: 520px; width: 100%; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }}
    .title {{ font-size: 22px; font-weight: 800; color: #F9FAFB; margin: 0 0 8px; display: flex; align-items: center; gap: 10px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 999px; background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.3); color: #22C55E; font-size: 13px; font-weight: 700; margin-bottom: 20px; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 14px; }}
    .info-table td {{ padding: 10px 0; border-bottom: 1px solid #1F2937; }}
    .info-table td.label {{ color: #9CA3AF; font-weight: 500; }}
    .info-table td.val {{ color: #F9FAFB; font-weight: 700; text-align: right; }}
    .code {{ background: #1F2937; padding: 3px 8px; border-radius: 6px; font-family: monospace; color: #F59E0B; }}
    .btn {{ display: block; width: 100%; padding: 12px; background: #E11D48; color: white; text-align: center; border-radius: 10px; font-weight: 700; text-decoration: none; box-sizing: border-box; margin-top: 10px; border: none; cursor: pointer; }}
    .btn-secondary {{ background: #1F2937; color: #F9FAFB; border: 1px solid #374151; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="title">✨ Jayraldine's Catering</div>
    <div class="badge">● Hub Server Active on Port 8000</div>
    <p style="color:#9CA3AF; font-size:14px; margin-top:0; line-height:1.5;">
      Your tablet has successfully established network communication with the laptop host.
    </p>
    <table class="info-table">
      <tr><td class="label">Server LAN IP</td><td class="val"><span class="code">{server_ip}</span></td></tr>
      <tr><td class="label">Port</td><td class="val"><span class="code">8000</span></td></tr>
      <tr><td class="label">Your Tablet IP</td><td class="val"><span class="code">{client_ip}</span></td></tr>
      <tr><td class="label">Database Engine</td><td class="val">{db_engine.upper()}</td></tr>
      <tr><td class="label">Database Name</td><td class="val">{db_name}</td></tr>
      <tr><td class="label">Database Status</td><td class="val">{db_status_badge}</td></tr>
    </table>
    <a href="/index.html" class="btn">🚀 Open Tablet Kiosk Web App</a>
    {apk_btn_html}
    <a href="/api/sync/lan-status" class="btn btn-secondary">📡 View Live JSON Status</a>
  </div>
</body>
</html>
"""
        self._set_cors_headers(200, "text/html; charset=utf-8")
        self.wfile.write(html.encode("utf-8"))

    def _serve_static_file(self, rel_path: str) -> bool:
        import mimetypes
        import os
        import sys

        clean_path = rel_path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"

        this_file = Path(__file__).resolve()
        candidate_dirs = [
            Path(r"C:\Testing\jayraldinescateringsystem\Tablet_PWA\frontend"),
            Path(r"C:\Testing\jayraldinescateringsystem\Tablet_Android_APK\app\src\main\assets"),
        ]
        for p in this_file.parents:
            if (p / "Tablet_PWA" / "frontend").is_dir():
                candidate_dirs.append(p / "Tablet_PWA" / "frontend")
            if (p / "Tablet_Android_APK" / "app" / "src" / "main" / "assets").is_dir():
                candidate_dirs.append(p / "Tablet_Android_APK" / "app" / "src" / "main" / "assets")

        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            candidate_dirs.extend([
                meipass / "Tablet_PWA" / "frontend",
                meipass / "frontend",
                meipass / "assets",
                meipass,
            ])

        candidate_dirs.extend([
            Path.cwd() / "Tablet_PWA" / "frontend",
            Path.cwd(),
            Path(os.environ.get("LOCALAPPDATA", "")) / "JayraldinesCatering" / "Tablet_PWA" / "frontend",
            Path(os.environ.get("LOCALAPPDATA", "")) / "JayraldinesCatering",
        ])

        target = None
        for base_dir in candidate_dirs:
            if base_dir.exists() and base_dir.is_dir():
                t = (base_dir / clean_path).resolve()
                try:
                    if str(t).startswith(str(base_dir.resolve())) and t.is_file():
                        target = t
                        break
                except Exception:
                    pass

        if not target or not target.is_file():
            return False

        mime, _ = mimetypes.guess_type(str(target))
        if not mime:
            if target.suffix == ".wasm":
                mime = "application/wasm"
            elif target.suffix == ".js":
                mime = "application/javascript"
            elif target.suffix == ".css":
                mime = "text/css"
            elif target.suffix in (".html", ".htm"):
                mime = "text/html; charset=utf-8"
            elif target.suffix in (".db", ".sqlite"):
                mime = "application/octet-stream"
            else:
                mime = "application/octet-stream"

        try:
            with open(target, "rb") as f:
                data = f.read()
            self._set_cors_headers(200, mime)
            self.wfile.write(data)
            return True
        except Exception:
            return False

    def _handle_image_download(self, query_params=None):
        """Serves the raw bytes of a package/menu image saved on this machine's
        disk, so other desktop clients on the LAN (which only see the relative
        path via the shared DB, not the file itself) can fetch and cache it."""
        qp = query_params or {}
        rel = (qp.get("path", [""])[0] or "").strip()
        if not rel:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": "Missing path"}).encode("utf-8"))
            return

        this_dir = Path(__file__).resolve().parent
        allowed_root = (this_dir.parent / "assets").resolve()
        candidate_paths = [
            Path(rel),
            this_dir.parent / rel,
            this_dir.parent.parent / rel,
        ]

        target = None
        for p in candidate_paths:
            try:
                resolved = p.resolve()
                resolved.relative_to(allowed_root)
            except Exception:
                continue
            if resolved.is_file():
                target = resolved
                break

        if not target:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Image not found"}).encode("utf-8"))
            return

        mime, _ = mimetypes.guess_type(str(target))
        if not mime or not mime.startswith("image/"):
            mime = "image/jpeg"
        try:
            with open(target, "rb") as f:
                data = f.read()
            self._set_cors_headers(200, mime)
            self.wfile.write(data)
        except Exception as exc:
            logger.warning(f"[SyncServer] Error serving image {target}: {exc}")
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": "Failed to read image"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/sync/lan-sync":
            self._handle_lan_sync()
            return

        if path == "/api/sync/device-offline":
            self._handle_device_offline()
            return

        if path == "/api/db/write":
            self._handle_db_write()
            return

        if path == "/api/db/callproc":
            self._handle_db_callproc()
            return

        if path == "/api/db/query":
            self._handle_db_query()
            return

        if path in ("/api/packages/define", "/api/packages/save"):
            self._handle_package_define()
            return

        if path in ("/api/packages/image-upload", "/api/sync/package-image"):
            self._handle_package_image_upload()
            return

        if path in ("/api/menu/image-upload", "/api/menu-items/image-upload", "/api/sync/menu-image"):
            self._handle_menu_image_upload()
            return

        self._set_cors_headers(404)
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def _handle_lan_status(self, parsed):
        db_online = False
        db_error = ""
        try:
            db_conn = db.get_connection()
            if db_conn:
                test = db.fetchone("SELECT 1 as alive")
                if test and test.get("alive") == 1:
                    db_online = True
        except Exception as e:
            db_error = str(e)

        cfg = db.get_db_config()
        current_version = get_db_version()
        response = {
            "online": True,
            "db_connected": db_online,
            "host": get_local_ip(),
            "port": 8000,
            "db_engine": db.get_engine_type(),
            "db_name": cfg.get("dbname", "jayraldines_catering"),
            "db_version": current_version,
            "version": current_version,
            "pending_bookings": 0,
            "pending_customers": 0,
            "error": db_error,
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._set_cors_headers(200)
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def _handle_lan_sync(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            payload = json.loads(body) if body else {}
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"detail": f"Malformed JSON: {e}"}).encode("utf-8"))
            return

        try:
            self._record_client_session(payload=payload)
            result = perform_server_sync(payload)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] Sync execution failed: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"detail": str(exc)}).encode("utf-8"))

    def _handle_device_offline(self, query_params=None):
        try:
            dev_id = None
            if query_params:
                dev_id = query_params.get("device_id", [None])[0]
            if not dev_id:
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len > 0:
                    body = self.rfile.read(content_len).decode("utf-8")
                    payload = json.loads(body) if body else {}
                    dev_id = payload.get("device_id")

            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
            clean_ip = client_ip.replace(":", "_").replace(".", "_")

            if dev_id:
                db.set_device_offline(dev_id)
            else:
                db.set_device_offline(f"phone-{clean_ip}")
                db.set_device_offline(f"tablet-{clean_ip}")

            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"ok": True, "status": "offline", "device_id": dev_id}).encode("utf-8"))
        except Exception as exc:
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"))


    def _handle_db_users(self):
        """GET /api/db/users — Return all users from server DB for client workstation auth."""
        try:
            rows = db.fetchall("SELECT id, username, display_name, role, is_active, password_hash, created_at FROM users ORDER BY id")
            users = []
            for r in rows:
                users.append({k: (str(v) if v is not None else None) for k, v in r.items()})
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"status": "ok", "users": users, "count": len(users)}).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] /api/db/users error: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_db_snapshot(self):
        """GET /api/db/snapshot — Return full DB snapshot for desktop client workstation sync."""
        try:
            snapshot = {}
            tables = [
                ("business_info",              "SELECT * FROM business_info"),
                ("app_settings",               "SELECT * FROM app_settings"),
                ("address_provinces",          "SELECT * FROM address_provinces ORDER BY ap_id"),
                ("address_cities",             "SELECT * FROM address_cities ORDER BY ac_id"),
                ("address_barangays",          "SELECT * FROM address_barangays ORDER BY ab_id"),
                ("addresses",                  "SELECT * FROM addresses ORDER BY ad_id"),
                ("occasions",                  "SELECT * FROM occasions ORDER BY occ_id"),
                ("users",                      "SELECT * FROM users ORDER BY id"),
                ("user_permissions",           "SELECT * FROM user_permissions ORDER BY id"),
                ("menu_categories",            "SELECT * FROM menu_categories ORDER BY mc_id"),
                ("menu_items",                 "SELECT * FROM menu_items ORDER BY mi_id"),
                ("packages",                   "SELECT * FROM packages ORDER BY pkg_id"),
                ("package_items",              "SELECT * FROM package_items ORDER BY pi_id"),
                ("package_buckets",            "SELECT * FROM package_buckets ORDER BY pb_id"),
                ("customer_loyalty_tiers",     "SELECT * FROM customer_loyalty_tiers ORDER BY cl_id"),
                ("customers",                  "SELECT * FROM customers ORDER BY cus_id"),
                ("customer_addresses",         "SELECT * FROM customer_addresses ORDER BY ca_id"),
                ("customer_follow_ups",        "SELECT * FROM customer_follow_ups ORDER BY cfu_id"),
                ("bookings",                   "SELECT * FROM bookings ORDER BY bk_id"),
                ("booking_menu_items",         "SELECT * FROM booking_menu_items ORDER BY bmi_id"),
                ("booking_items",              "SELECT * FROM booking_items ORDER BY bi_id"),
                ("booking_additional_charges", "SELECT * FROM booking_additional_charges ORDER BY ac_id"),
                ("terms_acknowledgements",     "SELECT * FROM terms_acknowledgements ORDER BY ta_id"),
                ("invoices",                   "SELECT * FROM invoices ORDER BY inv_id"),
                ("payment_records",            "SELECT * FROM payment_records ORDER BY pr_id"),
                ("kitchen_orders",             "SELECT * FROM kitchen_orders ORDER BY ko_id"),
                ("kitchen_tasks",              "SELECT * FROM kitchen_tasks ORDER BY kt_id"),
                ("inventory",                  "SELECT * FROM inventory ORDER BY inv_id"),
                ("calendar_events",            "SELECT * FROM calendar_events ORDER BY ce_id"),
                ("expenses",                   "SELECT * FROM expenses ORDER BY exp_id"),
                ("cash_flow_transactions",     "SELECT * FROM cash_flow_transactions ORDER BY cft_id"),
                ("notifications",              "SELECT * FROM notifications ORDER BY notif_id"),
                ("audit_logs",                 "SELECT * FROM (SELECT * FROM audit_logs ORDER BY al_id DESC LIMIT 50) ORDER BY al_id ASC"),
            ]
            for table_name, sql in tables:
                try:
                    rows = db.fetchall(sql)
                    clean = []
                    for r in rows:
                        clean.append({k: (str(v) if v is not None else None) for k, v in r.items()})
                    snapshot[table_name] = clean
                except Exception as te:
                    logger.warning(f"[SyncServer] Snapshot: skipping table {table_name}: {te}")

            snapshot["_meta"] = {
                "server_ip": get_local_ip(),
                "timestamp": datetime.now().isoformat(),
                "status": "ok"
            }
            payload_json = json.dumps(snapshot).encode("utf-8")
            self._set_cors_headers(200)
            self.wfile.write(payload_json)
        except Exception as exc:
            logger.error(f"[SyncServer] /api/db/snapshot error: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _read_json_body(self):
        """Read and parse JSON body from request."""
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        return json.loads(body) if body.strip() else {}

    def _handle_db_write(self):
        """
        POST /api/db/write
        Body: {"sql": "INSERT INTO ...", "params": [...]}
        Executes a write statement (INSERT/UPDATE/DELETE/REPLACE) on the server DB.
        Returns {"ok": true, "rowcount": N} or {"error": "..."}.
        """
        try:
            payload = self._read_json_body()
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": f"Bad JSON: {e}"}).encode("utf-8"))
            return

        sql = payload.get("sql", "").strip()
        params = payload.get("params", [])
        if isinstance(params, list):
            params = tuple(params)

        # Security: only allow write statements, not SELECT or PRAGMA
        sql_upper = sql.upper().lstrip()
        allowed_stmts = ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")
        if not any(sql_upper.startswith(kw) for kw in allowed_stmts):
            self._set_cors_headers(403)
            self.wfile.write(json.dumps({"error": "Only write statements allowed on /api/db/write"}).encode("utf-8"))
            return

        try:
            db.execute(sql, params)
            if is_business_write_sql(sql):
                bump_db_version()
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"ok": True, "version": get_db_version()}).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] /api/db/write error: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_db_callproc(self):
        """
        POST /api/db/callproc
        Body: {"proc": "sp_delete_booking", "in_params": [...], "out_names": [...] or null, "void": true/false}
        Runs a stored-procedure emulation (db.callproc_void / db.callproc_out) on the
        server's own DB. This exists because db.execute()'s client-proxy (see
        db.execute/fetchall) only ever covers raw SQL statements - callproc_void/
        callproc_out (used by sp_create_booking, sp_delete_booking, sp_pay_invoice,
        sp_update_booking, etc.) had NO proxy path at all, so on a client
        workstation those calls silently only ever wrote to that machine's own
        local SQLite cache and never reached the server - e.g. deleting a booking
        from a client would remove it locally but leave it fully intact on the
        server (and every other machine), looking exactly like "delete did
        nothing" with zero error shown.
        Returns {"ok": true, "result": {...}|true, "version": N} or {"error": "..."}.
        """
        try:
            payload = self._read_json_body()
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": f"Bad JSON: {e}"}).encode("utf-8"))
            return

        proc = str(payload.get("proc", "")).strip()
        in_params = payload.get("in_params", [])
        if isinstance(in_params, list):
            in_params = tuple(in_params)
        out_names = payload.get("out_names")
        is_void = bool(payload.get("void", True))

        # Only allow calling one of the known emulated stored procedures -
        # this isn't arbitrary SQL, so there's no injection surface, but the
        # allowlist still keeps this endpoint from being repurposed to call
        # something unexpected.
        if not proc.startswith("sp_"):
            self._set_cors_headers(403)
            self.wfile.write(json.dumps({"error": "Only sp_* stored procedures may be called via /api/db/callproc"}).encode("utf-8"))
            return

        try:
            if is_void:
                ok = db.callproc_void(proc, in_params=in_params)
                if not ok:
                    self._set_cors_headers(500)
                    self.wfile.write(json.dumps({"error": f"{proc} failed on server"}).encode("utf-8"))
                    return
                bump_db_version()
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({"ok": True, "result": True, "version": get_db_version()}).encode("utf-8"))
            else:
                result = db.callproc_out(proc, in_params=in_params, out_names=out_names)
                if result is None:
                    self._set_cors_headers(500)
                    self.wfile.write(json.dumps({"error": f"{proc} failed on server"}).encode("utf-8"))
                    return
                bump_db_version()
                clean = {k: (str(v) if v is not None else None) for k, v in result.items()}
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({"ok": True, "result": clean, "version": get_db_version()}).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] /api/db/callproc error ({proc}): {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_package_define(self):
        """
        POST /api/packages/define
        Body: {
            "package": {"id"?, "name", "description", "price_per_pax", "min_pax", "image"?},
            "items":   [{"menu_item_id"?, "item_name"?, "category"?, "custom_price"?}, ...],
            "buckets": [{"name", "limit", "categories": [...]}, ...]
        }
        Creates or updates a package together with its default dishes and its
        selection buckets. This is what lets the tablet author full package
        definitions (dishes + buckets), which it previously could not do.
        """
        try:
            payload = self._read_json_body()
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": f"Bad JSON: {e}"}).encode("utf-8"))
            return

        pkg = payload.get("package") or {}
        name = (pkg.get("name") or pkg.get("pkg_name") or "").strip()
        if not name:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": "A package name is required."}).encode("utf-8"))
            return

        try:
            data = {
                "name": name,
                "description": pkg.get("description", "") or "",
                "price_per_pax": float(pkg.get("price_per_pax") or pkg.get("pkg_price_per_pax") or 0.0),
                "min_pax": int(pkg.get("min_pax") or pkg.get("pkg_min_pax") or 1),
                "image": "",
            }

            raw_id = pkg.get("id") or pkg.get("pkg_id")
            pkg_id = None
            if raw_id:
                try:
                    pkg_id = int(raw_id)
                    repo.update_package(pkg_id, data)
                except Exception:
                    pkg_id = None
            if not pkg_id:
                pkg_id = repo.add_package(data)
            if not pkg_id:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({"error": "Failed to create or update the package."}).encode("utf-8"))
                return

            # Optional package photo as a base64 data URI (same storage as image-upload)
            img = pkg.get("image") or ""
            if img and str(img).startswith("data:"):
                try:
                    bdata, _mime, ext = _decode_image_data_uri(img)
                    target_dir = _desktop_package_image_dir()
                    target_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"packages_tablet_{pkg_id}_{int(time.time() * 1000)}{ext}"
                    target_path = (target_dir / filename).resolve()
                    if str(target_path).startswith(str(target_dir.resolve())):
                        target_path.write_bytes(bdata)
                        rel = f"assets/images/packages/{filename}"
                        upd = "UPDATE packages SET pkg_image = %s WHERE pkg_id = %s" if db.get_engine_type() == "postgres" else "UPDATE packages SET pkg_image = ? WHERE pkg_id = ?"
                        db.execute(upd, (rel, pkg_id))
                except Exception as ie:
                    logger.warning(f"[SyncServer] package define image save note: {ie}")

            # Items first, then buckets — set_package_buckets retags the items.
            items = payload.get("items")
            if items is not None:
                repo.set_package_items(pkg_id, items)
            buckets = payload.get("buckets")
            if buckets is not None:
                repo.set_package_buckets(pkg_id, buckets)

            bump_db_version()

            self._set_cors_headers(200)
            self.wfile.write(json.dumps({
                "ok": True,
                "pkg_id": pkg_id,
                "buckets": repo.get_package_buckets(pkg_id),
                "items": repo.get_package_items(pkg_id),
                "version": get_db_version(),
            }, default=str).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] Package define error: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_package_image_upload(self):
        """
        POST /api/packages/image-upload
        Body: {"pkg_id": 1, "image": "data:image/jpeg;base64,..."}
        Saves a tablet package image into the desktop assets folder and updates packages.pkg_image.
        """
        try:
            payload = self._read_json_body()
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": f"Bad JSON: {e}"}).encode("utf-8"))
            return

        try:
            pkg_id = int(payload.get("pkg_id") or payload.get("id") or 0)
        except Exception:
            pkg_id = 0

        pkg_name = (payload.get("name") or payload.get("pkg_name") or "").strip()
        if pkg_id <= 0 and not pkg_name:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": "A valid pkg_id or package name is required."}).encode("utf-8"))
            return

        try:
            existing = None
            if pkg_id > 0:
                id_sql = "SELECT pkg_id FROM packages WHERE pkg_id = %s LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT pkg_id FROM packages WHERE pkg_id = ? LIMIT 1"
                existing = db.fetchone(id_sql, (pkg_id,))
            if not existing and pkg_name:
                name_sql = "SELECT pkg_id FROM packages WHERE LOWER(pkg_name) = LOWER(%s) LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT pkg_id FROM packages WHERE LOWER(pkg_name) = LOWER(?) LIMIT 1"
                existing = db.fetchone(name_sql, (pkg_name,))
                if existing:
                    pkg_id = existing["pkg_id"]
            if not existing:
                self._set_cors_headers(404)
                self.wfile.write(json.dumps({"error": f"Package {pkg_id or pkg_name} was not found on the central DB."}).encode("utf-8"))
                return

            remove_image = bool(payload.get("remove")) or payload.get("image") in (None, "")
            rel_path = ""

            if not remove_image:
                data, _mime, ext = _decode_image_data_uri(payload.get("image", ""))
                target_dir = _desktop_package_image_dir()
                target_dir.mkdir(parents=True, exist_ok=True)
                filename = f"packages_tablet_{pkg_id}_{int(time.time() * 1000)}{ext}"
                target_path = (target_dir / filename).resolve()
                if not str(target_path).startswith(str(target_dir.resolve())):
                    raise ValueError("Invalid image destination.")
                target_path.write_bytes(data)
                rel_path = f"assets/images/packages/{filename}"

            update_sql = "UPDATE packages SET pkg_image = %s WHERE pkg_id = %s" if db.get_engine_type() == "postgres" else "UPDATE packages SET pkg_image = ? WHERE pkg_id = ?"
            db.execute(update_sql, (rel_path, pkg_id))
            bump_db_version()

            self._set_cors_headers(200)
            self.wfile.write(json.dumps({
                "ok": True,
                "pkg_id": pkg_id,
                "pkg_image": rel_path,
                "image": _image_to_data_uri(rel_path) if rel_path else "",
                "version": get_db_version(),
            }).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] Package image upload error: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_menu_image_upload(self):
        """
        POST /api/menu/image-upload
        Body: {"mi_id": 1, "image": "data:image/jpeg;base64,...", "remove": false}
        Saves a tablet menu item image into the desktop assets/images/menu folder and updates menu_items.mi_image.
        """
        try:
            payload = self._read_json_body()
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": f"Bad JSON: {e}"}).encode("utf-8"))
            return

        try:
            mi_id = int(payload.get("mi_id") or payload.get("id") or 0)
        except Exception:
            mi_id = 0

        item_name = (payload.get("name") or payload.get("mi_name") or "").strip()
        if mi_id <= 0 and not item_name:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": "A valid mi_id or item name is required."}).encode("utf-8"))
            return

        try:
            existing = None
            if mi_id > 0:
                id_sql = "SELECT mi_id FROM menu_items WHERE mi_id = %s LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT mi_id FROM menu_items WHERE mi_id = ? LIMIT 1"
                existing = db.fetchone(id_sql, (mi_id,))
            if not existing and item_name:
                name_sql = "SELECT mi_id FROM menu_items WHERE LOWER(mi_name) = LOWER(%s) LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT mi_id FROM menu_items WHERE LOWER(mi_name) = LOWER(?) LIMIT 1"
                existing = db.fetchone(name_sql, (item_name,))
                if existing:
                    mi_id = existing["mi_id"]
            if not existing:
                self._set_cors_headers(404)
                self.wfile.write(json.dumps({"error": f"Menu item {mi_id or item_name} was not found on the central DB."}).encode("utf-8"))
                return

            remove_image = bool(payload.get("remove")) or payload.get("image") in (None, "")
            rel_path = ""

            if not remove_image:
                data, _mime, ext = _decode_image_data_uri(payload.get("image", ""))
                target_dir = _desktop_menu_image_dir()
                target_dir.mkdir(parents=True, exist_ok=True)
                filename = f"menu_tablet_{mi_id}_{int(time.time() * 1000)}{ext}"
                target_path = (target_dir / filename).resolve()
                if not str(target_path).startswith(str(target_dir.resolve())):
                    raise ValueError("Invalid image destination.")
                target_path.write_bytes(data)
                rel_path = f"assets/images/menu/{filename}"

            update_sql = "UPDATE menu_items SET mi_image = %s WHERE mi_id = %s" if db.get_engine_type() == "postgres" else "UPDATE menu_items SET mi_image = ? WHERE mi_id = ?"
            db.execute(update_sql, (rel_path, mi_id))
            bump_db_version()

            self._set_cors_headers(200)
            self.wfile.write(json.dumps({
                "ok": True,
                "mi_id": mi_id,
                "mi_image": rel_path,
                "image": _image_to_data_uri(rel_path) if rel_path else "",
                "version": get_db_version(),
            }).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] Menu item image upload error: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

    def _handle_db_query(self):
        """
        POST /api/db/query
        Body: {"sql": "SELECT ...", "params": [...], "one": false}
        Executes a SELECT on the server DB and returns rows as JSON.
        Returns {"rows": [...]} or {"row": {...}} if one=true.
        """
        try:
            payload = self._read_json_body()
        except Exception as e:
            self._set_cors_headers(400)
            self.wfile.write(json.dumps({"error": f"Bad JSON: {e}"}).encode("utf-8"))
            return

        sql = payload.get("sql", "").strip()
        params = payload.get("params", [])
        one = payload.get("one", False)
        if isinstance(params, list):
            params = tuple(params)

        sql_upper = sql.upper().lstrip()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            self._set_cors_headers(403)
            self.wfile.write(json.dumps({"error": "Only SELECT statements allowed on /api/db/query"}).encode("utf-8"))
            return

        try:
            if one:
                row = db.fetchone(sql, params)
                clean = {k: (str(v) if v is not None else None) for k, v in row.items()} if row else None
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({"row": clean}).encode("utf-8"))
            else:
                rows = db.fetchall(sql, params)
                clean = [{k: (str(v) if v is not None else None) for k, v in r.items()} for r in rows]
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({"rows": clean}).encode("utf-8"))
        except Exception as exc:
            logger.error(f"[SyncServer] /api/db/query error: {exc}", exc_info=True)
            self._set_cors_headers(500)
            self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))


def perform_server_sync(payload: dict) -> dict:
    """Executes live duplicate-proof bidirectional synchronization."""
    candidate_custs = payload.get("customers") or []
    candidate_bks = payload.get("bookings") or []

    pushed_customers = 0
    synced_customer_names = []
    seen_c = set()

    for c in candidate_custs:
        c_name = (c.get("cus_name") or c.get("name") or "").strip()
        c_contact = (c.get("cus_contact") or c.get("contact") or "").strip()
        c_email = (c.get("cus_email") or c.get("email") or "").strip()
        c_address = (c.get("cus_address") or c.get("address") or "").strip()

        if not c_name or (c_name.lower(), c_contact) in seen_c:
            continue
        seen_c.add((c_name.lower(), c_contact))

        existing = db.fetchone(
            "SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(%s) LIMIT 1",
            (c_name,)
        )
        tier = c.get("cus_loyalty_tier") or c.get("loyalty_tier") or "Bronze"
        tier = tier.capitalize() if tier.capitalize() in ["Bronze", "Silver", "Gold", "VIP"] else "Bronze"
        status = c.get("cus_status") or c.get("status") or "Active"
        status = status.capitalize() if status.capitalize() in ["Active", "Pending", "Inactive"] else "Active"
        events_cnt = int(c.get("cus_total_events") or c.get("events") or 0)
        spent_amt = float(c.get("cus_total_spent") or 0.0)
        notes = c.get("cus_notes") or c.get("notes") or "Kiosk Order Customer"

        if not existing:
            try:
                if db.get_engine_type() == "postgres":
                    db.execute("""
                        INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address,
                                               cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes)
                        VALUES (%s, %s, %s, %s, %s::loyalty_tier, %s, %s, %s::customer_status, %s)
                    """, (c_name, c_contact, c_email, c_address, tier, events_cnt, spent_amt, status, notes))
                else:
                    db.execute("""
                        INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address,
                                               cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (c_name, c_contact, c_email, c_address, tier, events_cnt, spent_amt, status, notes))
                pushed_customers += 1
            except Exception as e:
                logger.warning(f"[SyncServer] Failed to insert customer {c_name}: {e}")
        else:
            try:
                if db.get_engine_type() == "postgres":
                    db.execute("""
                        UPDATE customers SET
                            cus_contact = COALESCE(NULLIF(%s, ''), cus_contact),
                            cus_email = COALESCE(NULLIF(%s, ''), cus_email),
                            cus_address = COALESCE(NULLIF(%s, ''), cus_address),
                            cus_notes = COALESCE(NULLIF(%s, ''), cus_notes)
                        WHERE cus_id = %s
                    """, (c_contact, c_email, c_address, notes, existing["cus_id"]))
                else:
                    db.execute("""
                        UPDATE customers SET
                            cus_contact = COALESCE(NULLIF(?, ''), cus_contact),
                            cus_email = COALESCE(NULLIF(?, ''), cus_email),
                            cus_address = COALESCE(NULLIF(?, ''), cus_address),
                            cus_notes = COALESCE(NULLIF(?, ''), cus_notes)
                        WHERE cus_id = ?
                    """, (c_contact, c_email, c_address, notes, existing["cus_id"]))
            except Exception:
                pass
        synced_customer_names.append(c_name)

    deleted_b_rows = db.fetchall("SELECT dr_ref FROM deleted_records WHERE dr_table = 'bookings'") or []
    deleted_booking_refs = {r["dr_ref"] for r in deleted_b_rows if r.get("dr_ref")}

    pushed_bookings = 0
    synced_booking_refs = []
    seen_b = set()

    for b in candidate_bks:
        ref = (b.get("bk_booking_ref") or b.get("booking_ref") or "").strip()
        if not ref or ref in seen_b:
            continue
        seen_b.add(ref)

        # Permanent tombstone check: Never let tablet sync resurrect a deleted booking
        if ref in deleted_booking_refs:
            logger.info(f"[SyncServer] Rejecting resurrect of deleted booking {ref}")
            continue

        chk_b_sql = "SELECT bk_id FROM bookings WHERE bk_booking_ref = %s LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT bk_id FROM bookings WHERE bk_booking_ref = ? LIMIT 1"
        existing_b = db.fetchone(chk_b_sql, (ref,))
        if not existing_b:
            cust_name = b.get("bk_customer_name") or b.get("customer_name") or "Walk-in Guest"
            addr = b.get("bk_address") or b.get("address") or ""
            venue = b.get("bk_venue") or b.get("venue") or "To be followed"
            ev_date = b.get("bk_event_date") or b.get("event_date") or datetime.now().strftime("%Y-%m-%d")
            ev_time = b.get("bk_event_time") or b.get("event_time") or "To be followed"
            ev_end_time = b.get("bk_event_end_time") or b.get("event_end_time") or None
            occ = b.get("bk_occasion") or b.get("occasion") or "General Event"
            pax = int(b.get("bk_pax") or b.get("pax") or 1)
            total = float(b.get("bk_total_amount") or b.get("total_amount") or 0.0)
            base_tot = float(b.get("bk_base_total") or b.get("base_total") or total)
            pay_mode = b.get("bk_payment_mode") or b.get("payment_mode") or "Cash"
            if pay_mode not in ["Cash", "Bank Transfer", "GCash", "PayMaya"]:
                pay_mode = "Cash"
            down_pay = float(b.get("bk_down_payment") or b.get("down_payment") or b.get("bk_amount_paid") or b.get("amount_paid") or 0.0)
            paid = down_pay
            dp_status = b.get("bk_down_payment_status") or b.get("down_payment_status") or ("PAID" if down_pay > 0 else "PENDING")
            
            # Extract customer notes / special instructions
            notes = (b.get("bk_special_notes") or b.get("special_notes") or b.get("bk_notes") or b.get("notes") or "").strip()
            
            # Lookup customer id and contact info
            c_chk_sql = "SELECT cus_id, cus_contact, cus_email FROM customers WHERE LOWER(cus_name) = LOWER(%s) LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT cus_id, cus_contact, cus_email FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1"
            cust_row = db.fetchone(c_chk_sql, (cust_name,))
            cust_id = cust_row["cus_id"] if cust_row else None
            cust_contact = (b.get("bk_contact") or b.get("contact") or b.get("phone") or (cust_row.get("cus_contact") if cust_row else "") or "").strip()
            cust_email = (b.get("bk_email") or b.get("email") or (cust_row.get("cus_email") if cust_row else "") or "").strip()

            pkg_id = b.get("bk_package_id") or b.get("package_id") or None
            if pkg_id:
                try:
                    chk_p_sql = "SELECT pkg_id FROM packages WHERE pkg_id = %s" if db.get_engine_type() == "postgres" else "SELECT pkg_id FROM packages WHERE pkg_id = ?"
                    chk = db.fetchone(chk_p_sql, (pkg_id,))
                    if not chk:
                        pkg_id = None
                except Exception:
                    pkg_id = None

            try:
                bk_id = None
                if db.get_engine_type() == "postgres":
                    row = db.fetchone("""
                        INSERT INTO bookings (
                            bk_booking_ref, bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address,
                            bk_event_date, bk_event_time, bk_event_end_time, bk_venue, bk_occasion, bk_pax, bk_total_amount,
                            bk_base_total, bk_payment_mode, bk_amount_paid, bk_down_payment,
                            bk_down_payment_status, bk_status, bk_special_notes, bk_notes, bk_package_id
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s::payment_method, %s, %s,
                            %s, %s::booking_status, %s, %s, %s
                        )
                        ON CONFLICT (bk_booking_ref) DO UPDATE SET
                            bk_special_notes = EXCLUDED.bk_special_notes,
                            bk_notes = EXCLUDED.bk_notes,
                            bk_contact = COALESCE(NULLIF(EXCLUDED.bk_contact, ''), bookings.bk_contact),
                            bk_email = COALESCE(NULLIF(EXCLUDED.bk_email, ''), bookings.bk_email),
                            bk_event_end_time = COALESCE(EXCLUDED.bk_event_end_time, bookings.bk_event_end_time),
                            bk_amount_paid = EXCLUDED.bk_amount_paid,
                            bk_down_payment = EXCLUDED.bk_down_payment,
                            bk_down_payment_status = EXCLUDED.bk_down_payment_status
                        RETURNING bk_id;
                    """, (
                        ref, cust_id, cust_name, cust_contact, cust_email, addr,
                        ev_date, ev_time, ev_end_time, venue, occ, pax, total,
                        base_tot, pay_mode, paid, down_pay,
                        dp_status, "PENDING", notes, notes, pkg_id
                    ))
                    if row:
                        bk_id = row.get("bk_id")
                else:
                    db.execute("""
                        INSERT OR REPLACE INTO bookings (
                            bk_booking_ref, bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address,
                            bk_event_date, bk_event_time, bk_event_end_time, bk_venue, bk_occasion, bk_pax, bk_total_amount,
                            bk_base_total, bk_payment_mode, bk_amount_paid, bk_down_payment,
                            bk_down_payment_status, bk_status, bk_special_notes, bk_notes, bk_package_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ref, cust_id, cust_name, cust_contact, cust_email, addr,
                        ev_date, ev_time, ev_end_time, venue, occ, pax, total,
                        base_tot, pay_mode, paid, down_pay,
                        dp_status, "PENDING", notes, notes, pkg_id
                    ))
                    b_chk = db.fetchone("SELECT bk_id FROM bookings WHERE bk_booking_ref = ?", (ref,))
                    if b_chk:
                        bk_id = b_chk.get("bk_id")

                if bk_id:
                    pushed_bookings += 1

                    # Handle booking items if sent
                    items = b.get("menu_items") or b.get("items") or []
                    for itm in items:
                        try:
                            itm_id = itm.get("bmi_item_id") or itm.get("item_id") or itm.get("mi_id") or None
                            # The tablet's payload already carries the dish
                            # name/category/price/quantity (its own local
                            # booking_menu_items row, synced as-is) - this
                            # used to be extracted only to resolve a MISSING
                            # item_id and then thrown away, so the INSERT
                            # below never wrote bmi_item_name/bmi_category,
                            # leaving every tablet-created booking's dishes
                            # NULL (rendered as a raw Python dict repr on the
                            # printed order slip instead of the dish name).
                            itm_name = (itm.get("bmi_item_name") or itm.get("name") or itm.get("item_name") or "").strip()
                            itm_category = (itm.get("bmi_category") or itm.get("category") or "").strip()
                            itm_price = itm.get("bmi_price") if itm.get("bmi_price") is not None else itm.get("price")
                            itm_qty = itm.get("bmi_quantity") if itm.get("bmi_quantity") is not None else itm.get("quantity")
                            if itm_id:
                                try:
                                    chk_mi = db.fetchone("SELECT mi_id, mi_name, mi_category FROM menu_items WHERE mi_id = %s" if db.get_engine_type() == "postgres" else "SELECT mi_id, mi_name, mi_category FROM menu_items WHERE mi_id = ?", (itm_id,))
                                    if not chk_mi:
                                        itm_id = None
                                    else:
                                        # Payload didn't include a name/category - fall
                                        # back to the server's own menu_items record for
                                        # this id (this used to only apply when the name
                                        # was ALSO missing, so a payload with a name but
                                        # no real category - e.g. a tablet-side booking
                                        # saved before this same bug was fixed there too -
                                        # still fell through to the generic "Selected
                                        # Dishes" placeholder below).
                                        if not itm_name:
                                            itm_name = chk_mi.get("mi_name") or ""
                                        itm_category = itm_category or (chk_mi.get("mi_category") or "")
                                except Exception:
                                    itm_id = None
                            if not itm_id and itm_name:
                                chk_name = db.fetchone("SELECT mi_id FROM menu_items WHERE LOWER(mi_name) = LOWER(%s) LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT mi_id FROM menu_items WHERE LOWER(mi_name) = LOWER(?) LIMIT 1", (itm_name,))
                                if chk_name:
                                    itm_id = chk_name["mi_id"]
                            if itm_id or itm_name:
                                if db.get_engine_type() == "postgres":
                                    db.execute("""
                                        INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                        ON CONFLICT DO NOTHING;
                                    """, (bk_id, itm_id, itm_name or "", itm_category or "Selected Dishes", itm_price or 0.0, itm_qty or 1))
                                else:
                                    db.execute("""
                                        INSERT OR IGNORE INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (bk_id, itm_id, itm_name or "", itm_category or "Selected Dishes", itm_price or 0.0, itm_qty or 1))
                        except Exception as bmie:
                            logger.warning(f"[SyncServer] booking_menu_item note: {bmie}")

                    # Handle booking additional charges (add-ons) if sent
                    add_charges = b.get("additional_charges") or b.get("charges") or []
                    for chg in add_charges:
                        try:
                            desc = (chg.get("ac_description") or chg.get("description") or "").strip()
                            amt = float(chg.get("ac_amount") if chg.get("ac_amount") is not None else (chg.get("amount") or 0.0))
                            date_added = chg.get("ac_date_added") or chg.get("date_added") or ev_date
                            added_by = chg.get("ac_added_by") or chg.get("added_by") or "Tablet Kiosk"
                            if desc:
                                if db.get_engine_type() == "postgres":
                                    db.execute("""
                                        INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (bk_id, desc, amt, date_added, added_by))
                                else:
                                    db.execute("""
                                        INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (bk_id, desc, amt, date_added, added_by))
                        except Exception as che:
                            logger.warning(f"[SyncServer] booking_additional_charges insert note: {che}")

                    # Create invoice
                    try:
                        inv_num = ref.replace("TB-", "INV-").replace("BK-", "INV-")
                        if not inv_num.startswith("INV-"):
                            inv_num = f"INV-{ref}"
                        inv_balance = max(0.0, total - paid)
                        inv_status = "Paid" if paid >= total and total > 0 else ("Partial" if paid > 0 else "Unpaid")
                        inv_id = None
                        if db.get_engine_type() == "postgres":
                            inv_row = db.fetchone("""
                                INSERT INTO invoices (
                                    inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name,
                                    inv_event_date, inv_total_amount, inv_amount_paid, inv_balance,
                                    inv_down_payment, inv_status, inv_payment_verified
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::invoice_status, %s)
                                ON CONFLICT DO NOTHING
                                RETURNING inv_id;
                            """, (bk_id, inv_num, inv_num, cust_name, ev_date, total, paid, inv_balance, down_pay, inv_status, 1 if paid > 0 else 0))
                            inv_id = inv_row["inv_id"] if inv_row else None
                        else:
                            db.execute("""
                                INSERT OR IGNORE INTO invoices (
                                    inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name,
                                    inv_event_date, inv_total_amount, inv_amount_paid, inv_balance,
                                    inv_down_payment, inv_status, inv_payment_verified
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (bk_id, inv_num, inv_num, cust_name, ev_date, total, paid, inv_balance, down_pay, inv_status, 1 if paid > 0 else 0))
                            inv_chk = db.fetchone("SELECT inv_id FROM invoices WHERE inv_booking_id = ? LIMIT 1", (bk_id,))
                            inv_id = inv_chk["inv_id"] if inv_chk else None

                        if inv_id and paid > 0:
                            if db.get_engine_type() == "postgres":
                                db.execute("""
                                    INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_note, pr_is_downpayment)
                                    VALUES (%s, %s, %s, %s, %s, 1)
                                """, (inv_id, paid, ev_date, pay_mode, f"Tablet Kiosk Down Payment: {notes}" if notes else "Tablet Kiosk Down Payment"))
                            else:
                                db.execute("""
                                    INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_note, pr_is_downpayment)
                                    VALUES (?, ?, ?, ?, ?, 1)
                                """, (inv_id, paid, ev_date, pay_mode, f"Tablet Kiosk Down Payment: {notes}" if notes else "Tablet Kiosk Down Payment"))

                        if cust_id:
                            if db.get_engine_type() == "postgres":
                                db.execute("""
                                    UPDATE customers
                                    SET cus_total_events = (
                                        SELECT COUNT(*) FROM bookings WHERE bk_customer_id = %s AND bk_status != 'CANCELLED'
                                    ),
                                    cus_total_spent = (
                                        SELECT COALESCE(SUM(bk_total_amount), 0.0) FROM bookings WHERE bk_customer_id = %s AND bk_status != 'CANCELLED'
                                    ),
                                    cus_updated_at = NOW()
                                    WHERE cus_id = %s
                                """, (cust_id, cust_id, cust_id))
                            else:
                                db.execute("""
                                    UPDATE customers
                                    SET cus_total_events = (
                                        SELECT COUNT(*) FROM bookings WHERE bk_customer_id = ? AND bk_status != 'CANCELLED'
                                    ),
                                    cus_total_spent = (
                                        SELECT COALESCE(SUM(bk_total_amount), 0.0) FROM bookings WHERE bk_customer_id = ? AND bk_status != 'CANCELLED'
                                    ),
                                    cus_updated_at = CURRENT_TIMESTAMP
                                    WHERE cus_id = ?
                                """, (cust_id, cust_id, cust_id))

                        # Log creation in Audit Logs by Tablet Kiosk
                        try:
                            import utils.repository as repo
                            repo.write_audit_log(
                                actor=f"Kiosk ({cust_name})",
                                action="CREATE",
                                table_name="bookings",
                                record_id=bk_id,
                                new_value={
                                    "ref": ref,
                                    "customer": cust_name,
                                    "total": total,
                                    "down_payment": down_pay,
                                    "notes": notes
                                },
                                device="Tablet Kiosk"
                            )
                        except Exception:
                            pass
                    except Exception as ie:
                        logger.warning(f"[SyncServer] Invoice insert note: {ie}")
            except Exception as e:
                logger.warning(f"[SyncServer] Failed to insert booking {ref}: {e}")
        else:
            # Booking already exists in DB - backfill any missing additional charges or updated totals
            try:
                bk_id = existing_b.get("bk_id")
                ev_date = b.get("bk_event_date") or b.get("event_date") or datetime.now().strftime("%Y-%m-%d")
                total = float(b.get("bk_total_amount") or b.get("total_amount") or 0.0)
                base_tot = float(b.get("bk_base_total") or b.get("base_total") or total)

                add_charges = b.get("additional_charges") or b.get("charges") or []
                for chg in add_charges:
                    desc = (chg.get("ac_description") or chg.get("description") or "").strip()
                    amt = float(chg.get("ac_amount") if chg.get("ac_amount") is not None else (chg.get("amount") or 0.0))
                    date_added = chg.get("ac_date_added") or chg.get("date_added") or ev_date
                    added_by = chg.get("ac_added_by") or chg.get("added_by") or "Tablet Kiosk"
                    if desc and bk_id:
                        chk_c_sql = "SELECT ac_id FROM booking_additional_charges WHERE ac_booking_id = %s AND LOWER(ac_description) = LOWER(%s) LIMIT 1" if db.get_engine_type() == "postgres" else "SELECT ac_id FROM booking_additional_charges WHERE ac_booking_id = ? AND LOWER(ac_description) = LOWER(?) LIMIT 1"
                        existing_c = db.fetchone(chk_c_sql, (bk_id, desc))
                        if not existing_c:
                            if db.get_engine_type() == "postgres":
                                db.execute("""
                                    INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (bk_id, desc, amt, date_added, added_by))
                            else:
                                db.execute("""
                                    INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (bk_id, desc, amt, date_added, added_by))

                # Update total amount in bookings and invoices if tablet total is greater
                if bk_id and total > 0:
                    if db.get_engine_type() == "postgres":
                        db.execute("UPDATE bookings SET bk_total_amount = GREATEST(bk_total_amount, %s), bk_base_total = GREATEST(bk_base_total, %s) WHERE bk_id = %s", (total, base_tot, bk_id))
                        db.execute("UPDATE invoices SET inv_total_amount = GREATEST(inv_total_amount, %s), inv_balance = GREATEST(0.0, GREATEST(inv_total_amount, %s) - inv_amount_paid) WHERE inv_booking_id = %s", (total, total, bk_id))
                    else:
                        db.execute("UPDATE bookings SET bk_total_amount = MAX(bk_total_amount, ?), bk_base_total = MAX(bk_base_total, ?) WHERE bk_id = ?", (total, base_tot, bk_id))
                        db.execute("UPDATE invoices SET inv_total_amount = MAX(inv_total_amount, ?), inv_balance = MAX(0.0, MAX(inv_total_amount, ?) - inv_amount_paid) WHERE inv_booking_id = ?", (total, total, bk_id))
            except Exception as ex_be:
                logger.warning(f"[SyncServer] Existing booking backfill note for {ref}: {ex_be}")

        synced_booking_refs.append(ref)

    # Pull latest packages
    try:
        pkgs_raw = db.fetchall("""
            SELECT pkg_id, pkg_name, COALESCE(pkg_description, '') AS pkg_description,
                   COALESCE(pkg_price_per_pax, 350.0) AS pkg_price_per_pax,
                   COALESCE(pkg_min_pax, 30) AS pkg_min_pax,
                   COALESCE(pkg_image, '') AS pkg_image
            FROM packages
            ORDER BY pkg_id
        """) or []
        pkgs = [
            {
                "pkg_id": r["pkg_id"],
                "pkg_name": r["pkg_name"],
                "pkg_description": r.get("pkg_description", ""),
                "pkg_price_per_pax": float(r.get("pkg_price_per_pax") or 350.0),
                "pkg_min_pax": int(r.get("pkg_min_pax") or 30),
                "pkg_image": r.get("pkg_image", ""),
                "image": _image_to_data_uri(r.get("pkg_image", ""))
            }
            for r in pkgs_raw
        ]
    except Exception as pe:
        logger.warning(f"[SyncServer] Failed to fetch packages: {pe}")
        pkgs = []

    # Pull latest menu items
    try:
        items_raw = db.fetchall("""
            SELECT mi_id,
                   COALESCE(mi_name, '') AS mi_name,
                   COALESCE(mi_category, 'Main Course') AS mi_category,
                   COALESCE(mi_price, 0.0) AS mi_price,
                   COALESCE(mi_status, 'Available') AS mi_status,
                   COALESCE(mi_description, '') AS mi_description,
                   COALESCE(mi_image, '') AS mi_image
            FROM menu_items
            ORDER BY mi_id
        """) or []
        menu_items = [
            {
                "mi_id": r["mi_id"],
                "mi_name": r["mi_name"],
                "mi_category": r["mi_category"],
                "mi_price": float(r.get("mi_price") or 0.0),
                "mi_status": r["mi_status"],
                "mi_description": r.get("mi_description", ""),
                "mi_image": r.get("mi_image", ""),
                "image": _image_to_data_uri(r.get("mi_image", ""))
            }
            for r in items_raw
        ]
    except Exception as me:
        logger.warning(f"[SyncServer] Failed to fetch menu_items: {me}")
        menu_items = []

    package_items = []
    try:
        pi_raw = db.fetchall("""
            SELECT pi_id, pi_package_id, COALESCE(pi_menu_item_id, 0) AS pi_menu_item_id,
                   COALESCE(pi_item_name, '') AS pi_item_name,
                   COALESCE(pi_category, '') AS pi_category,
                   COALESCE(pi_custom_price, 0.0) AS pi_custom_price,
                   COALESCE(pi_quantity, 1) AS pi_quantity,
                   pi_bucket_id
            FROM package_items
            ORDER BY pi_id
        """) or []
        package_items = [
            {
                "pi_id": r["pi_id"],
                "pi_package_id": r["pi_package_id"],
                "pi_menu_item_id": r.get("pi_menu_item_id", 0),
                "pi_item_name": r.get("pi_item_name", ""),
                "pi_category": r.get("pi_category", ""),
                "pi_custom_price": float(r.get("pi_custom_price") or 0.0),
                "pi_quantity": int(r.get("pi_quantity") or 1),
                "pi_bucket_id": r.get("pi_bucket_id")
            }
            for r in pi_raw
        ]
    except Exception as e:
        logger.warning(f"[SyncServer] Failed to fetch package_items: {e}")
        package_items = []

    # Pull package selection buckets (dish/dessert quotas)
    package_buckets = []
    try:
        pb_raw = db.fetchall("""
            SELECT pb_id, pb_package_id,
                   COALESCE(pb_name, '') AS pb_name,
                   COALESCE(pb_limit, 1) AS pb_limit,
                   COALESCE(pb_categories, '[]') AS pb_categories,
                   COALESCE(pb_sort, 0) AS pb_sort
            FROM package_buckets
            ORDER BY pb_package_id, pb_sort, pb_id
        """) or []
        package_buckets = [
            {
                "pb_id": r["pb_id"],
                "pb_package_id": r["pb_package_id"],
                "pb_name": r.get("pb_name", ""),
                "pb_limit": int(r.get("pb_limit") or 1),
                "pb_categories": r.get("pb_categories", "[]"),
                "pb_sort": int(r.get("pb_sort") or 0)
            }
            for r in pb_raw
        ]
    except Exception as e:
        logger.warning(f"[SyncServer] Failed to fetch package_buckets: {e}")
        package_buckets = []

    # Pull latest customers
    customers = []
    try:
        custs_raw = db.fetchall("""
            SELECT cus_id, cus_name,
                   COALESCE(cus_contact, '') AS cus_contact,
                   COALESCE(cus_email, '') AS cus_email,
                   COALESCE(cus_address, '') AS cus_address,
                   COALESCE(cus_loyalty_tier, 'Bronze') AS cus_loyalty_tier,
                   COALESCE(cus_status, 'Active') AS cus_status,
                   COALESCE(cus_total_events, 0) AS cus_total_events,
                   COALESCE(cus_total_spent, 0.0) AS cus_total_spent,
                   COALESCE(cus_notes, '') AS cus_notes
            FROM customers
            ORDER BY cus_name
        """) or []
        customers = [
            {
                "cus_id": r["cus_id"],
                "cus_name": r["cus_name"],
                "cus_contact": r["cus_contact"],
                "cus_email": r["cus_email"],
                "cus_address": r["cus_address"],
                "cus_loyalty_tier": r["cus_loyalty_tier"],
                "cus_status": r["cus_status"],
                "cus_total_events": int(r.get("cus_total_events") or 0),
                "cus_total_spent": float(r.get("cus_total_spent") or 0.0),
                "cus_notes": r.get("cus_notes", "")
            }
            for r in custs_raw
        ]
    except Exception as e:
        logger.warning(f"[SyncServer] Failed to fetch customers: {e}")
        customers = []

    # Pull latest occasions
    occasions = []
    try:
        occ_raw = db.fetchall("SELECT occ_id, occ_name, occ_is_active FROM occasions WHERE occ_is_active = 1 OR occ_is_active IS NULL ORDER BY occ_id") or []
        occasions = [
            {
                "occ_id": r["occ_id"],
                "occ_name": r["occ_name"],
                "occ_is_active": int(r.get("occ_is_active") or 1)
            }
            for r in occ_raw
        ]
    except Exception as oe:
        logger.warning(f"[SyncServer] Failed to fetch occasions: {oe}")
        occasions = []

    if pushed_bookings > 0 or pushed_customers > 0:
        bump_db_version()

    msg = f"Sync successful! Pushed {pushed_bookings} booking(s) and {pushed_customers} customer(s). Sent {len(pkgs)} package(s), {len(menu_items)} dish(es), and {len(customers)} customer(s)."
    return {
        "status": "success",
        "message": msg,
        "pushed_bookings": pushed_bookings,
        "pushed_customers": pushed_customers,
        "packages": pkgs,
        "menu_items": menu_items,
        "package_items": package_items,
        "package_buckets": package_buckets,
        "customers": customers,
        "occasions": occasions,
        "synced_booking_refs": synced_booking_refs,
        "synced_customer_names": synced_customer_names,
        "deleted_booking_refs": list(deleted_booking_refs),
    }


def start_sync_server_background(host="0.0.0.0", port=8000) -> bool:
    """Starts the threaded HTTP sync server in a daemon background thread."""
    global _SERVER_INSTANCE, _SERVER_THREAD
    if _SERVER_INSTANCE is not None:
        return True

    try:
        _SERVER_INSTANCE = ThreadingHTTPServer((host, port), SyncServerHandler)
        _SERVER_THREAD = threading.Thread(target=_SERVER_INSTANCE.serve_forever, daemon=True, name="LANSyncServer")
        _SERVER_THREAD.start()
        logger.info(f"✅ LAN Sync Server started listening on http://{host}:{port} (Local LAN IP: {get_local_ip()})")
        return True
    except OSError as e:
        if e.errno in (98, 10048):  # Address already in use
            logger.info(f"LAN Sync Server already active on port {port} (likely started by external launcher).")
            return True
        logger.warning(f"Could not start LAN Sync Server on port {port}: {e}")
        return False
    except Exception as exc:
        logger.warning(f"Failed to start LAN Sync Server: {exc}")
        return False


def stop_sync_server():
    """Stops the running LAN sync server instance."""
    global _SERVER_INSTANCE, _SERVER_THREAD
    if _SERVER_INSTANCE:
        try:
            _SERVER_INSTANCE.shutdown()
            _SERVER_INSTANCE.server_close()
        except Exception:
            pass
        _SERVER_INSTANCE = None
        _SERVER_THREAD = None

