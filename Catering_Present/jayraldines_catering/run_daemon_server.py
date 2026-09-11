import time
import sys
import utils.db_sync_server as s

print("=" * 60)
print("  JAYRALDINE'S CATERING - LAN SYNC SERVER DAEMON")
print("=" * 60)
ip = s.get_local_ip()
print(f"Server IP: {ip}")
print("Port: 8000")
print("PostgreSQL Database: jayraldines_catering")
print("=" * 60)

ok = s.start_sync_server_background("0.0.0.0", 8000)
if ok:
    print(f"🚀 [ONLINE] Sync server listening on http://0.0.0.0:8000")
    print(f"📱 Tablet Diagnostic URL: http://{ip}:8000/test")
    print(f"🌐 Tablet Web Kiosk URL:  http://{ip}:8000/index.html")
    sys.stdout.flush()
    while True:
        time.sleep(3600)
else:
    print("❌ Failed to start sync server")
    sys.exit(1)
