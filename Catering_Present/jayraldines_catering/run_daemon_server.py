"""Standalone launcher for the LAN Sync Server as a long-running daemon.

Run this on the "server PC" to expose the shared PostgreSQL data and the tablet
web kiosk/diagnostic endpoints to other devices on the local network. It starts
the background sync server (from ``utils.db_sync_server``) bound to all
interfaces on port 8000, prints the reachable URLs, then blocks forever so the
process stays alive. Exits with a non-zero status if the server fails to start.
"""
import time
import sys
import utils.db_sync_server as s

# Print a banner with the server's LAN address and the key URLs so the operator
# knows what to type on tablets/clients.
print("=" * 60)
print("  JAYRALDINE'S CATERING - LAN SYNC SERVER DAEMON")
print("=" * 60)
ip = s.get_local_ip()
print(f"Server IP: {ip}")
print("Port: 8000")
print("PostgreSQL Database: jayraldines_catering")
print("=" * 60)

# Bind to 0.0.0.0 so devices elsewhere on the LAN (not just localhost) can reach it.
ok = s.start_sync_server_background("0.0.0.0", 8000)
if ok:
    print(f"🚀 [ONLINE] Sync server listening on http://0.0.0.0:8000")
    print(f"📱 Tablet Diagnostic URL: http://{ip}:8000/test")
    print(f"🌐 Tablet Web Kiosk URL:  http://{ip}:8000/index.html")
    sys.stdout.flush()
    # The server runs on a background thread; keep the main thread alive
    # indefinitely (sleeping in long chunks) so the daemon doesn't exit.
    while True:
        time.sleep(3600)
else:
    # Startup failed (e.g. port in use); surface a non-zero exit for supervisors.
    print("❌ Failed to start sync server")
    sys.exit(1)
