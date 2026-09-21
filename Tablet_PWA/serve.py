#!/usr/bin/env python3
"""
Jayraldine's Catering — Standalone Kiosk PWA High-Performance Local Server.

Features:
- Multi-threaded static file serving (ThreadingHTTPServer)
- Proper MIME types (e.g. application/wasm for sql-wasm.wasm)
- Cache-Control headers for static assets (instant reloads, no lag)
- Handles CORS headers for all LAN tablets
- Handles POST requests gracefully
- Direct integration with Central SQLite Database (~/.jayraldines_catering/data/catering.db)
  when running standalone, and seamless reverse-proxy to Central Server (port 8000)
  when the Desktop app is running.
"""

import argparse
import os
import sys
import json
import socket
import time
import urllib.request
import urllib.error
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = SCRIPT_DIR / "frontend"

# Add desktop app directory to sys.path so we share the exact same db and sync logic
DESKTOP_APP_DIR = SCRIPT_DIR.parent / "Catering_Present" / "jayraldines_catering"
if DESKTOP_APP_DIR.is_dir() and str(DESKTOP_APP_DIR) not in sys.path:
    sys.path.insert(0, str(DESKTOP_APP_DIR))

# Ensure SQLite engine is used for local database operations
os.environ.setdefault("DB_ENGINE", "sqlite")

DIRECT_DB_READY = False
try:
    import utils.db as db
    import utils.db_sync_server as sync_srv
    DIRECT_DB_READY = True
except Exception as _e:
    sys.stderr.write(f"[KioskServer] Direct DB import notice: {_e}\n")


def is_port_open(host: str = "127.0.0.1", port: int = 8000, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


class KioskHTTPRequestHandler(SimpleHTTPRequestHandler):
    server_version = "JayraldineKiosk/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, format, *args):
        # Clean terminal logging: don't spam repetitive status probes
        msg = format % args
        if "/api/sync/lan-status" in msg or "/api/sync/device-offline" in msg:
            return
        sys.stdout.write(f"[KioskServer] {msg}\n")
        sys.stdout.flush()

    def end_headers(self):
        # Enable CORS for local tablet access
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "*")

        # Set cache headers
        req_path = getattr(self, "path", "")
        if any(req_path.endswith(ext) for ext in (".wasm", ".js", ".css", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".json", ".woff2", ".ttf")):
            self.send_header("Cache-Control", "public, max-age=86400")
        elif req_path.endswith(".html") or req_path in ("/", ""):
            self.send_header("Cache-Control", "no-cache, must-revalidate")

        super().end_headers()

    def guess_type(self, path):
        if str(path).endswith(".wasm"):
            return "application/wasm"
        return super().guess_type(path)

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _send_json(self, data: dict, status: int = 200):
        resp_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def _proxy_to_port_8000(self, method: str) -> bool:
        """Attempt to reverse-proxy to Central Server on port 8000."""
        central_port = 8000
        if not is_port_open("127.0.0.1", central_port, timeout=0.2):
            return False

        try:
            target_url = f"http://127.0.0.1:{central_port}{self.path}"
            body = None
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = self.rfile.read(content_length)

            req = urllib.request.Request(target_url, data=body, method=method)
            for k, v in self.headers.items():
                if k.lower() not in ("host", "content-length"):
                    req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ("transfer-encoding", "content-length", "access-control-allow-origin"):
                        self.send_header(k, v)
                resp_data = resp.read()
                self.send_header("Content-Length", str(len(resp_data)))
                self.end_headers()
                self.wfile.write(resp_data)
                return True
        except Exception:
            return False

    def _handle_direct_api(self, method: str):
        """Execute API calls directly against the shared SQLite catering.db."""
        path = self.path.split("?")[0]

        # 1. LAN Status check
        if path.startswith("/api/sync/lan-status"):
            db_online = False
            db_error = ""
            if DIRECT_DB_READY:
                try:
                    conn = db.get_connection()
                    if conn:
                        test = db.fetchone("SELECT 1 as alive")
                        if test and test.get("alive") == 1:
                            db_online = True
                except Exception as e:
                    db_error = str(e)

            current_version = sync_srv.get_db_version() if DIRECT_DB_READY else int(datetime.now().timestamp())
            self._send_json({
                "online": True,
                "db_connected": db_online,
                "host": sync_srv.get_local_ip() if DIRECT_DB_READY else "127.0.0.1",
                "port": 8080,
                "db_engine": db.get_engine_type() if DIRECT_DB_READY else "sqlite",
                "db_name": "catering.db",
                "db_version": current_version,
                "version": current_version,
                "pending_bookings": 0,
                "pending_customers": 0,
                "error": db_error,
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return

        # 2. Duplicate-proof bidirectional sync
        if path == "/api/sync/lan-sync":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            try:
                payload = json.loads(body) if body else {}
            except Exception as e:
                self._send_json({"status": "error", "message": f"Malformed JSON: {e}"}, status=400)
                return

            if DIRECT_DB_READY:
                try:
                    result = sync_srv.perform_server_sync(payload)
                    self._send_json(result)
                except Exception as exc:
                    self._send_json({"status": "error", "message": str(exc)}, status=500)
            else:
                self._send_json({"status": "error", "message": "Database module unavailable"}, status=500)
            return

        # 3. Direct DB write
        if path == "/api/db/write":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            try:
                payload = json.loads(body) if body else {}
            except Exception:
                payload = {}

            sql = payload.get("sql", "").strip()
            params = payload.get("params", [])
            if isinstance(params, list):
                params = tuple(params)

            if DIRECT_DB_READY and sql:
                try:
                    db.execute(sql, params)
                    if sync_srv.is_business_write_sql(sql):
                        sync_srv.bump_db_version()
                    self._send_json({"ok": True, "version": sync_srv.get_db_version()})
                except Exception as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=500)
            else:
                self._send_json({"ok": True, "version": 1})
            return

        # 4. Device offline notification
        if path.startswith("/api/sync/device-offline"):
            self._send_json({"ok": True, "offline": True})
            return

        # 5. Raw SQLite DB binary file download
        if path in ("/catering.db", "/data/catering.db", "/api/catering.db"):
            if DIRECT_DB_READY:
                db_path = db.get_sqlite_db_path()
                if db_path.is_file():
                    with open(db_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

        # Fallback default JSON
        self._send_json({"ok": True})

    def _proxy_or_respond(self, method: str):
        path = self.path

        # If API call, try to proxy to running Desktop app on port 8000 first
        if path.startswith("/api/") or path in ("/catering.db", "/data/catering.db"):
            if self._proxy_to_port_8000(method):
                return
            # Port 8000 offline: execute directly against the shared SQLite catering.db
            self._handle_direct_api(method)
            return

        if method == "POST":
            self._send_json({"ok": True})
            return

        super().do_GET()

    def do_GET(self):
        if self.path.startswith("/api/") or self.path in ("/catering.db", "/data/catering.db"):
            self._proxy_or_respond("GET")
        else:
            super().do_GET()

    def do_POST(self):
        self._proxy_or_respond("POST")


def main():
    parser = argparse.ArgumentParser(description="Jayraldine Kiosk Standalone HTTP Server")
    parser.add_argument("--bind", "--host", default="0.0.0.0", dest="host", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    server_address = (args.host, args.port)
    httpd = ThreadingHTTPServer(server_address, KioskHTTPRequestHandler)
    print(f"Serving Kiosk PWA on http://{args.host}:{args.port} ...", flush=True)
    if DIRECT_DB_READY:
        print(f"Connected to Shared SQLite DB at: {db.get_sqlite_db_path()}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Kiosk Server...", flush=True)
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
