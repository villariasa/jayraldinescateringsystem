"""
Entry point for the packaged .exe (see pwa_server.spec / build_installer.py).
Not used in normal dev — dev/run.sh|run.bat call `uvicorn app:app` directly.
This exists because a frozen executable needs a plain `if __name__` script,
not a CLI command, and because it prints the LAN URL prominently so whoever
double-clicks the installed shortcut knows what address to type into a
tablet's browser.
"""
import socket
import sys

import uvicorn

from version import VERSION


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    host = "0.0.0.0"
    port = 8000
    lan_ip = _lan_ip()

    print("=" * 65, flush=True)
    print(f"  Jayraldine's Catering Kiosk Server v{VERSION}", flush=True)
    print("=" * 65, flush=True)
    print(f"  On THIS machine:      http://localhost:{port}", flush=True)
    print(f"  On tablets (same WiFi): http://{lan_ip}:{port}", flush=True)
    print("=" * 65, flush=True)
    print("  Keep this window open — closing it stops the kiosk server.", flush=True)
    print("  Press Ctrl+C to stop.", flush=True)
    print("=" * 65, flush=True)

    from app import app
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
