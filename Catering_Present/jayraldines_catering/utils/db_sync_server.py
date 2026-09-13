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
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import utils.db as db
import utils.repository as repo
from utils.logger import get_logger

logger = get_logger()

_SERVER_INSTANCE = None
_SERVER_THREAD = None


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


class SyncServerHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests from tablet kiosk apps for LAN sync."""

    def _set_cors_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With, ngrok-skip-browser-warning")
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def _record_client_session(self, payload=None, query_params=None):
        """Auto-registers and tracks connecting mobile/tablet/client devices into device_sessions table."""
        try:
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
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
                "timestamp": datetime.now().isoformat()
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

        if path in ("/", "/index.html"):
            if self._serve_static_file("index.html"):
                return

        # Attempt to serve static files from Tablet_PWA/frontend or desktop assets
        if self._serve_static_file(path):
            return

        if path == "/api/info":
            self._set_cors_headers(200)
            res = {
                "status": "ok",
                "app": "Jayraldine's Catering Central Server Hub",
                "server_ip": get_local_ip(),
                "port": 8000,
                "test_url": f"http://{get_local_ip()}:8000/test",
                "kiosk_url": f"http://{get_local_ip()}:8000/index.html",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        self._set_cors_headers(404)
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

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

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/sync/lan-sync":
            self._handle_lan_sync()
            return

        if path == "/api/sync/device-offline":
            self._handle_device_offline()
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
        response = {
            "online": True,
            "db_connected": db_online,
            "host": get_local_ip(),
            "port": 8000,
            "db_engine": db.get_engine_type(),
            "db_name": cfg.get("dbname", "jayraldines_catering"),
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
                db.execute("""
                    INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address,
                                           cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes)
                    VALUES (%s, %s, %s, %s, %s::loyalty_tier, %s, %s, %s::customer_status, %s)
                """, (c_name, c_contact, c_email, c_address, tier, events_cnt, spent_amt, status, notes))
                pushed_customers += 1
            except Exception as e:
                logger.warning(f"[SyncServer] Failed to insert customer {c_name}: {e}")
        else:
            try:
                db.execute("""
                    UPDATE customers SET
                        cus_contact = COALESCE(NULLIF(%s, ''), cus_contact),
                        cus_email = COALESCE(NULLIF(%s, ''), cus_email),
                        cus_address = COALESCE(NULLIF(%s, ''), cus_address),
                        cus_notes = COALESCE(NULLIF(%s, ''), cus_notes)
                    WHERE cus_id = %s
                """, (c_contact, c_email, c_address, notes, existing["cus_id"]))
            except Exception:
                pass
        synced_customer_names.append(c_name)

    pushed_bookings = 0
    synced_booking_refs = []
    seen_b = set()

    for b in candidate_bks:
        ref = (b.get("bk_booking_ref") or b.get("booking_ref") or "").strip()
        if not ref or ref in seen_b:
            continue
        seen_b.add(ref)

        existing_b = db.fetchone("SELECT bk_id FROM bookings WHERE bk_booking_ref = %s LIMIT 1", (ref,))
        if not existing_b:
            cust_name = b.get("bk_customer_name") or b.get("customer_name") or "Walk-in Guest"
            addr = b.get("bk_address") or b.get("address") or ""
            venue = b.get("bk_venue") or b.get("venue") or addr or "TBD / On-Site Venue"
            ev_date = b.get("bk_event_date") or b.get("event_date") or datetime.now().strftime("%Y-%m-%d")
            ev_time = b.get("bk_event_time") or b.get("event_time") or "18:00"
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
            cust_row = db.fetchone("SELECT cus_id, cus_contact, cus_email FROM customers WHERE LOWER(cus_name) = LOWER(%s) LIMIT 1", (cust_name,))
            cust_id = cust_row["cus_id"] if cust_row else None
            cust_contact = (b.get("bk_contact") or b.get("contact") or b.get("phone") or (cust_row.get("cus_contact") if cust_row else "") or "").strip()
            cust_email = (b.get("bk_email") or b.get("email") or (cust_row.get("cus_email") if cust_row else "") or "").strip()

            pkg_id = b.get("bk_package_id") or b.get("package_id") or None
            if pkg_id:
                try:
                    chk = db.fetchone("SELECT pkg_id FROM packages WHERE pkg_id = %s", (pkg_id,))
                    if not chk:
                        pkg_id = None
                except Exception:
                    pkg_id = None

            try:
                row = db.fetchone("""
                    INSERT INTO bookings (
                        bk_booking_ref, bk_customer_id, bk_customer_name, bk_contact, bk_email, bk_address,
                        bk_event_date, bk_event_time, bk_venue, bk_occasion, bk_pax, bk_total_amount,
                        bk_base_total, bk_payment_mode, bk_amount_paid, bk_down_payment,
                        bk_down_payment_status, bk_status, bk_special_notes, bk_notes, bk_package_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s::payment_method, %s, %s,
                        %s, %s::booking_status, %s, %s, %s
                    )
                    ON CONFLICT (bk_booking_ref) DO UPDATE SET
                        bk_special_notes = EXCLUDED.bk_special_notes,
                        bk_notes = EXCLUDED.bk_notes,
                        bk_contact = COALESCE(NULLIF(EXCLUDED.bk_contact, ''), bookings.bk_contact),
                        bk_email = COALESCE(NULLIF(EXCLUDED.bk_email, ''), bookings.bk_email),
                        bk_amount_paid = EXCLUDED.bk_amount_paid,
                        bk_down_payment = EXCLUDED.bk_down_payment,
                        bk_down_payment_status = EXCLUDED.bk_down_payment_status
                    RETURNING bk_id;
                """, (
                    ref, cust_id, cust_name, cust_contact, cust_email, addr,
                    ev_date, ev_time, venue, occ, pax, total,
                    base_tot, pay_mode, paid, down_pay,
                    dp_status, "PENDING", notes, notes, pkg_id
                ))
                if row:
                    pushed_bookings += 1
                    bk_id = row.get("bk_id")

                    # Handle booking items if sent
                    items = b.get("menu_items") or b.get("items") or []
                    for itm in items:
                        try:
                            itm_id = itm.get("bmi_item_id") or itm.get("item_id") or itm.get("mi_id") or None
                            if itm_id:
                                try:
                                    chk_mi = db.fetchone("SELECT mi_id FROM menu_items WHERE mi_id = %s", (itm_id,))
                                    if not chk_mi:
                                        itm_id = None
                                except Exception:
                                    itm_id = None
                            if not itm_id:
                                itm_name = (itm.get("bmi_item_name") or itm.get("name") or itm.get("item_name") or "").strip()
                                if itm_name:
                                    chk_name = db.fetchone("SELECT mi_id FROM menu_items WHERE LOWER(mi_name) = LOWER(%s) LIMIT 1", (itm_name,))
                                    if chk_name:
                                        itm_id = chk_name["mi_id"]
                            if itm_id:
                                db.execute("""
                                    INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id)
                                    VALUES (%s, %s)
                                    ON CONFLICT DO NOTHING;
                                """, (bk_id, itm_id))
                        except Exception as bmie:
                            logger.warning(f"[SyncServer] booking_menu_item note: {bmie}")

                    # Create invoice
                    try:
                        inv_num = ref.replace("TB-", "INV-").replace("BK-", "INV-")
                        if not inv_num.startswith("INV-"):
                            inv_num = f"INV-{ref}"
                        inv_balance = max(0.0, total - paid)
                        inv_status = "Paid" if paid >= total and total > 0 else ("Partial" if paid > 0 else "Unpaid")
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
                        if not inv_id:
                            inv_chk = db.fetchone("SELECT inv_id FROM invoices WHERE inv_booking_id = %s LIMIT 1", (bk_id,))
                            inv_id = inv_chk["inv_id"] if inv_chk else None

                        if inv_id and paid > 0:
                            db.execute("""
                                INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_method, pr_note, pr_is_downpayment)
                                VALUES (%s, %s, %s, %s, %s, 1)
                            """, (inv_id, paid, ev_date, pay_mode, f"Tablet Kiosk Down Payment: {notes}" if notes else "Tablet Kiosk Down Payment"))

                        if cust_id:
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
                   COALESCE(mi_category::TEXT, 'Main Dish') AS mi_category,
                   COALESCE(mi_price, 0.0) AS mi_price,
                   COALESCE(mi_status::TEXT, 'Available') AS mi_status,
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
                   COALESCE(pi_quantity, 1) AS pi_quantity
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
                "pi_quantity": int(r.get("pi_quantity") or 1)
            }
            for r in pi_raw
        ]
    except Exception as e:
        logger.warning(f"[SyncServer] Failed to fetch package_items: {e}")
        package_items = []

    # Pull latest customers
    customers = []
    try:
        custs_raw = db.fetchall("""
            SELECT cus_id, cus_name,
                   COALESCE(cus_contact, '') AS cus_contact,
                   COALESCE(cus_email, '') AS cus_email,
                   COALESCE(cus_address, '') AS cus_address,
                   COALESCE(cus_loyalty_tier::TEXT, 'Bronze') AS cus_loyalty_tier,
                   COALESCE(cus_status::TEXT, 'Active') AS cus_status,
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

    msg = f"Sync successful! Pushed {pushed_bookings} booking(s) and {pushed_customers} customer(s). Sent {len(pkgs)} package(s), {len(menu_items)} dish(es), and {len(customers)} customer(s)."
    return {
        "status": "success",
        "message": msg,
        "pushed_bookings": pushed_bookings,
        "pushed_customers": pushed_customers,
        "packages": pkgs,
        "menu_items": menu_items,
        "package_items": package_items,
        "customers": customers,
        "synced_booking_refs": synced_booking_refs,
        "synced_customer_names": synced_customer_names,
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

