#!/usr/bin/env python3
"""
Jayraldine's Catering — Standalone Kiosk PWA High-Performance Local Server.

Features:
- Multi-threaded static file serving (ThreadingHTTPServer)
- Proper MIME types (e.g. application/wasm for sql-wasm.wasm)
- Cache-Control headers for static assets (instant reloads, no lag)
- Handles CORS headers for all LAN tablets
- Handles POST requests gracefully (e.g. /api/sync/device-offline without 501 errors)
- Seamless reverse-proxy for /api/ to Central Server on port 8000 if running,
  or instant JSON fallback if Central Server is offline (eliminates 404/501 freezes).
"""

import argparse
import os
import sys
import socket
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = SCRIPT_DIR / "frontend"


def is_port_open(host: str = "127.0.0.1", port: int = 8000, timeout: float = 0.3) -> bool:
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

    def _proxy_or_respond(self, method: str):
        path = self.path
        # If API call, proxy to Central Server (port 8000) if active
        if path.startswith("/api/"):
            central_port = 8000
            if is_port_open("127.0.0.1", central_port, timeout=0.2):
                try:
                    target_url = f"http://127.0.0.1:{central_port}{path}"
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
                        return
                except Exception:
                    pass

            # Central Server not running: return instant JSON response instead of 404/501 error
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            if path.startswith("/api/sync/device-offline"):
                resp_bytes = b'{"ok": true, "offline": true}'
            elif path.startswith("/api/sync/lan-status"):
                resp_bytes = b'{"online": false, "db_connected": false, "detail": "Central Server (port 8000) offline"}'
            else:
                resp_bytes = b'{"ok": false, "error": "Central Server offline"}'
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        if method == "POST":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            resp_bytes = b'{"ok": true}'
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        super().do_GET()

    def do_GET(self):
        if self.path.startswith("/api/"):
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
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Kiosk Server...", flush=True)
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
