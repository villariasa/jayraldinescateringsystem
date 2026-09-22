"""
Jayraldine's Catering — Kiosk PWA backend.

Single FastAPI process that (a) serves the JSON API the frontend calls, and
(b) serves the PWA's static files (frontend/) at the same origin — so the
whole kiosk is one process on one port, installable from any tablet's
browser on the local network. Run with:

    uvicorn app:app --host 0.0.0.0 --port 8000

See ../README.md for the full setup / packaging instructions.
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import repository as repo
import importer
import exporter
import terms as terms_mod
from schema import DATA_DIR

app = FastAPI(title="Jayraldine's Catering Kiosk API")

# Enable Cross-Origin Resource Sharing (CORS) for all LAN tablets and native WebView
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_frontend_dir() -> Path:
    """In a normal checkout, frontend/ is the sibling of backend/. In a
    PyInstaller-frozen build (see pwa_server.spec), files are unpacked into
    a temp dir at sys._MEIPASS with frontend/ bundled alongside this
    script — check that first so the installed .exe can find its own UI."""
    frozen_dir = getattr(sys, "_MEIPASS", None)
    if frozen_dir:
        candidate = Path(frozen_dir) / "frontend"
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent.parent / "frontend"


FRONTEND_DIR = _resolve_frontend_dir()
EXPORTS_DIR = DATA_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Pydantic request models ─────────────────────────────────────────────

class CustomerIn(BaseModel):
    name: str
    contact: str = ""
    email: str = ""
    address: str = ""


class PackageIn(BaseModel):
    name: str
    description: str = ""
    price_per_pax: float = 350.0
    min_pax: int = 30


class MenuItemIn(BaseModel):
    name: str
    category: str = "Main Dish"
    price: float = 0.0
    status: str = "Available"
    description: str = ""


class MenuSelectionIn(BaseModel):
    menu_item_id: Optional[int] = None
    item_name: str
    category: str = ""
    price: float = 0.0
    quantity: int = 1


class ChargeIn(BaseModel):
    description: str
    amount: float


class OrderIn(BaseModel):
    customer_id: Optional[int] = None
    customer_name: str
    contact: str = ""
    email: str = ""
    address: str = ""
    event_date: str
    event_time: str = "18:00"
    venue: str = ""
    occasion: str = ""
    pax: int = 1
    package_id: Optional[int] = None
    base_total: float = 0.0
    menu_selections: list[MenuSelectionIn] = []
    additional_charges: list[ChargeIn] = []
    down_payment: float = 0.0
    payment_method: str = "Cash"
    notes: str = ""
    terms_version: Optional[str] = None
    actor: str = "Kiosk PWA"


# ── Health / bootstrap ───────────────────────────────────────────────────

@app.get("/api/health")
def health():
    db.connect()
    return {"status": "ok"}


@app.get("/api/terms")
def get_terms():
    return {
        "version": terms_mod.CURRENT_TERMS_VERSION,
        "title": terms_mod.TERMS_TITLE,
        "text": terms_mod.TERMS_TEXT,
        "acknowledgement_label": terms_mod.TERMS_ACKNOWLEDGEMENT_LABEL,
    }


# ── Customers ────────────────────────────────────────────────────────────

@app.get("/api/customers")
def list_customers(q: str = ""):
    return repo.search_customers(q)


@app.get("/api/customers/duplicate-check")
def duplicate_check(contact: str = "", name: str = ""):
    return repo.find_possible_duplicate_customer(contact, name) or {}


@app.post("/api/customers")
def create_customer(payload: CustomerIn):
    try:
        cust_id = repo.add_customer(payload.name, payload.contact, payload.email, payload.address)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": cust_id}


@app.put("/api/customers/{customer_id}")
def edit_customer(customer_id: int, payload: CustomerIn):
    ok = repo.update_customer(customer_id, payload.name, payload.contact, payload.email, payload.address)
    if not ok:
        raise HTTPException(400, "Update failed — name is required.")
    return {"ok": True}


@app.delete("/api/customers/{customer_id}")
def remove_customer(customer_id: int):
    repo.delete_customer(customer_id)
    return {"ok": True}


# ── Addresses (built-in Cebu hierarchy search) ──────────────────────────

@app.get("/api/addresses/search")
def address_search(q: str = "", limit: int = 15):
    return repo.search_cebu_address(q, limit)


# ── Packages ─────────────────────────────────────────────────────────────

@app.get("/api/packages")
def list_packages():
    return repo.get_packages()


@app.post("/api/packages")
def create_package(payload: PackageIn):
    try:
        pkg_id = repo.add_package(payload.name, payload.description, payload.price_per_pax, payload.min_pax)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": pkg_id}


@app.put("/api/packages/{pkg_id}")
def edit_package(pkg_id: int, payload: PackageIn):
    ok = repo.update_package(pkg_id, payload.name, payload.description, payload.price_per_pax, payload.min_pax)
    if not ok:
        raise HTTPException(400, "Update failed — name is required.")
    return {"ok": True}


@app.delete("/api/packages/{pkg_id}")
def remove_package(pkg_id: int):
    repo.delete_package(pkg_id)
    return {"ok": True}


# ── Menu items ───────────────────────────────────────────────────────────

@app.get("/api/menu-items")
def list_menu_items():
    return repo.get_all_menu_items()


@app.get("/api/menu-items/grouped")
def list_menu_items_grouped():
    return repo.get_package_menu_choices()


@app.get("/api/menu-categories")
def list_menu_categories():
    return repo.get_menu_categories()


@app.post("/api/menu-items")
def create_menu_item(payload: MenuItemIn):
    try:
        mi_id = repo.add_menu_item(payload.name, payload.category, payload.price, payload.status, payload.description)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"id": mi_id}


@app.put("/api/menu-items/{mi_id}")
def edit_menu_item(mi_id: int, payload: MenuItemIn):
    ok = repo.update_menu_item(mi_id, payload.name, payload.category, payload.price, payload.status, payload.description)
    if not ok:
        raise HTTPException(400, "Update failed — name is required.")
    return {"ok": True}


@app.delete("/api/menu-items/{mi_id}")
def remove_menu_item(mi_id: int):
    repo.delete_menu_item(mi_id)
    return {"ok": True}


# ── Orders ───────────────────────────────────────────────────────────────

@app.get("/api/orders")
def list_orders(limit: int = 200):
    return repo.get_all_orders(limit)


@app.get("/api/orders/{booking_id}")
def order_detail(booking_id: int):
    detail = repo.get_order_detail(booking_id)
    if not detail:
        raise HTTPException(404, "Order not found.")
    return detail


@app.post("/api/orders")
def place_order(payload: OrderIn):
    order = payload.model_dump()
    order["menu_selections"] = [m for m in order["menu_selections"]]
    order["additional_charges"] = [c for c in order["additional_charges"]]
    try:
        result = repo.create_order(order)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return result


@app.get("/api/orders/{booking_id}/receipt.pdf")
def order_receipt(booking_id: int):
    detail = repo.get_order_detail(booking_id)
    if not detail:
        raise HTTPException(404, "Order not found.")
    out_path = EXPORTS_DIR / f"receipt_{detail['booking_ref']}.pdf"
    ok = exporter.export_order_receipt_pdf(str(out_path), detail)
    if not ok:
        raise HTTPException(500, "Receipt generation failed — is reportlab installed on the server?")
    return FileResponse(str(out_path), media_type="application/pdf", filename=out_path.name)


@app.get("/api/bookings/by-date")
def bookings_by_date(date: str):
    """Bookings for one calendar date — backs the kiosk's Calendar feature
    (dashboard + ordering-step date view)."""
    return repo.get_bookings_by_date(date)


@app.get("/api/bookings/by-month")
def bookings_by_month(year: int, month: int):
    """Bookings for a calendar month — backs the kiosk's Calendar feature."""
    if not (1 <= month <= 12):
        raise HTTPException(400, "month must be between 1 and 12.")
    return repo.get_bookings_by_month(year, month)


@app.post("/api/orders/archive-and-clear")
def archive_and_clear():
    """Mirrors the original kiosk's 'Archive & Clear Orders' action: export
    everything to Excel first, then wipe transactional tables (customers,
    menu, and packages are kept)."""
    out_path = EXPORTS_DIR / f"Orders_Archive_{_timestamp()}.xlsx"
    result = exporter.export_all_orders_to_excel(str(out_path))
    if not result["success"]:
        raise HTTPException(500, result.get("error") or "Archive export failed.")
    cleared = repo.clear_all_orders()
    return {"archived_orders": result["orders_count"], "cleared_orders": cleared, "archive_file": out_path.name}


@app.get("/api/export/orders.xlsx")
def export_orders_excel():
    out_path = EXPORTS_DIR / f"Orders_Export_{_timestamp()}.xlsx"
    result = exporter.export_all_orders_to_excel(str(out_path))
    if not result["success"]:
        raise HTTPException(500, result.get("error") or "Export failed.")
    return FileResponse(str(out_path), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=out_path.name)


@app.get("/api/export/database.db")
def export_database():
    out_path = EXPORTS_DIR / f"catering_pwa_export_{_timestamp()}.db"
    ok = importer.export_local_database(str(out_path))
    if not ok:
        raise HTTPException(500, "Database export failed.")
    return FileResponse(str(out_path), media_type="application/octet-stream", filename=out_path.name)


# ── Master data sync ─────────────────────────────────────────────────────

@app.get("/api/sync/status")
def sync_status():
    last = importer.get_last_master_sync()
    packages_count = len(repo.get_packages())
    menu_count = len(repo.get_all_menu_items())
    return {
        "last_sync": last,
        "packages_count": packages_count,
        "menu_items_count": menu_count,
    }


@app.post("/api/sync/import")
async def sync_import(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".db", ".xlsx", ".xlsm"):
        raise HTTPException(400, "Only .db, .xlsx, or .xlsm files are accepted.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        stats = importer.import_master_data(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    if stats.get("errors"):
        raise HTTPException(400, "; ".join(stats["errors"]))
    return stats


class LanSyncIn(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = 5432
    dbname: Optional[str] = "jayraldines_catering"
    user: Optional[str] = "jayraldines_app"
    password: Optional[str] = None
    bookings: Optional[List[Dict[str, Any]]] = None
    customers: Optional[List[Dict[str, Any]]] = None


def _get_default_server_cfg() -> dict:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        cfg_path = Path(local_app_data) / "JayraldinesCatering" / "db_config.json"
    else:
        cfg_path = Path.home() / ".jayraldines_catering" / "db_config.json"
    if cfg_path.exists():
        import json
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"host": "localhost", "port": 5432, "dbname": "jayraldines_catering", "user": "jayraldines_app", "password": "12345678"}


@app.get("/api/sync/lan-status")
def lan_status(host: Optional[str] = None, port: Optional[int] = None):
    cfg = _get_default_server_cfg()
    h = host or cfg.get("host", "localhost")
    p = port or int(cfg.get("port", 5432))

    online = False
    error_msg = ""
    import socket
    try:
        with socket.create_connection((h, p), timeout=2.0):
            online = True
    except Exception as exc:
        error_msg = str(exc)
        online = False

    db.connect()
    pending_bookings = 0
    pending_customers = 0
    try:
        b_row = db.fetchone("SELECT COUNT(*) as c FROM bookings WHERE sync_status = 'pending' OR sync_status IS NULL")
        pending_bookings = b_row["c"] if b_row else 0
    except Exception:
        pass
    try:
        c_row = db.fetchone("SELECT COUNT(*) as c FROM customers WHERE sync_status = 'pending' OR sync_status IS NULL")
        pending_customers = c_row["c"] if c_row else 0
    except Exception:
        pass

    return {
        "online": online,
        "host": h,
        "port": p,
        "pending_bookings": pending_bookings,
        "pending_customers": pending_customers,
        "error": error_msg,
    }


@app.post("/api/sync/lan-sync")
def lan_sync(payload: Optional[LanSyncIn] = None):
    cfg = _get_default_server_cfg()
    host = (payload and payload.host) or cfg.get("host", "localhost")
    port = (payload and payload.port) or int(cfg.get("port", 5432))
    dbname = (payload and payload.dbname) or cfg.get("dbname", "jayraldines_catering")
    user = (payload and payload.user) or cfg.get("user", "jayraldines_app")
    
    # Priority: explicit non-empty payload password -> db_config password -> fallback '12345678'
    if payload and payload.password is not None and str(payload.password).strip() != "":
        password = str(payload.password).strip()
    else:
        password = cfg.get("password") or "12345678"

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise HTTPException(500, "psycopg2 is not installed on this machine.")

    pg_conn = None
    last_err = None
    candidate_users = [user]
    for alt in ["jayraldines_app", "postgres"]:
        if alt not in candidate_users:
            candidate_users.append(alt)

    for u in candidate_users:
        try:
            pg_conn = psycopg2.connect(
                host=host, port=port, dbname=dbname, user=u, password=password,
                connect_timeout=5
            )
            break
        except Exception as exc:
            last_err = exc

    if not pg_conn:
        raise HTTPException(503, f"Could not connect to Central PostgreSQL database at {host}:{port} ({dbname}): {last_err}")

    pushed_bookings = 0
    pushed_customers = 0
    synced_booking_refs = []
    synced_customer_names = []

    try:
        db.connect()
        pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 0. Ensure Central PostgreSQL schema compatibility
        pg_cur.execute("""
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_down_payment NUMERIC(12, 2) DEFAULT 0.00;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_down_payment_status VARCHAR(50) DEFAULT 'PENDING';
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_base_total NUMERIC(12, 2) DEFAULT 0.00;
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_color_theme VARCHAR(100) DEFAULT '#2563EB';
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_notes TEXT DEFAULT '';
            ALTER TABLE bookings ADD COLUMN IF NOT EXISTS bk_cancellation_reason TEXT DEFAULT '';

            CREATE TABLE IF NOT EXISTS occasions (
                occ_id SERIAL PRIMARY KEY,
                occ_name VARCHAR(100) NOT NULL UNIQUE,
                occ_is_active INT DEFAULT 1
            );
            ALTER TABLE occasions ADD COLUMN IF NOT EXISTS occ_is_active INT DEFAULT 1;

            CREATE TABLE IF NOT EXISTS monthly_sales_targets (
                mst_year INT NOT NULL,
                mst_month INT NOT NULL,
                mst_target_amount NUMERIC(12, 2) DEFAULT 85000.0,
                mst_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (mst_year, mst_month)
            );
        """)
        pg_conn.commit()

        # 1. Push Customers (combine client payload and local DB)
        candidate_custs = []
        if payload and payload.customers:
            candidate_custs.extend(payload.customers)
        try:
            local_custs = db.fetchall("SELECT * FROM customers WHERE sync_status = 'pending' OR sync_status IS NULL")
            candidate_custs.extend(local_custs)
        except Exception:
            pass

        seen_c = set()
        for c in candidate_custs:
            c_name = (c.get("cus_name") or "").strip()
            c_contact = (c.get("cus_contact") or "").strip()
            if not c_name or (c_name.lower(), c_contact) in seen_c:
                continue
            seen_c.add((c_name.lower(), c_contact))

            pg_cur.execute(
                "SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(%s) AND cus_contact = %s LIMIT 1",
                (c_name, c_contact)
            )
            existing = pg_cur.fetchone()
            if not existing:
                pg_cur.execute("""
                    INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address,
                                           cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    c_name, c_contact, c.get("cus_email", ""), c.get("cus_address", ""),
                    c.get("cus_loyalty_tier", "Bronze"), c.get("cus_total_events", 0),
                    c.get("cus_total_spent", 0.0), c.get("cus_status", "Active"), c.get("cus_notes", "")
                ))
                pushed_customers += 1
            synced_customer_names.append(c_name)
            if c.get("cus_id"):
                try:
                    db.execute("UPDATE customers SET sync_status = 'synced' WHERE cus_id = ?", (c["cus_id"],))
                except Exception:
                    pass

        # 2. Push Bookings
        candidate_bks = []
        if payload and payload.bookings:
            candidate_bks.extend(payload.bookings)
        try:
            local_bks = db.fetchall("SELECT * FROM bookings WHERE sync_status = 'pending' OR sync_status IS NULL")
            candidate_bks.extend(local_bks)
        except Exception:
            pass

        seen_b = set()
        for b in candidate_bks:
            ref = (b.get("bk_booking_ref") or "").strip()
            if not ref or ref in seen_b:
                continue
            seen_b.add(ref)

            pg_cur.execute("SELECT bk_id FROM bookings WHERE bk_booking_ref = %s LIMIT 1", (ref,))
            existing_b = pg_cur.fetchone()
            if not existing_b:
                pg_cur.execute("""
                    INSERT INTO bookings (
                        bk_booking_ref, bk_customer_name, bk_address, bk_event_date,
                        bk_event_time, bk_venue, bk_occasion, bk_pax, bk_total_amount,
                        bk_base_total, bk_payment_mode, bk_amount_paid, bk_down_payment,
                        bk_down_payment_status, bk_status, bk_notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (bk_booking_ref) DO NOTHING
                    RETURNING bk_id;
                """, (
                    ref, b.get("bk_customer_name"), b.get("bk_address"), b.get("bk_event_date"),
                    b.get("bk_event_time", "18:00"), b.get("bk_venue"), b.get("bk_occasion"),
                    b.get("bk_pax", 1), b.get("bk_total_amount", 0.0), b.get("bk_base_total", 0.0),
                    b.get("bk_payment_mode", "Cash"), b.get("bk_amount_paid", 0.0),
                    b.get("bk_down_payment", 0.0), b.get("bk_down_payment_status", "PENDING"),
                    b.get("bk_status", "PENDING"), b.get("bk_notes", "Kiosk Order")
                ))
                new_row = pg_cur.fetchone()
                if new_row:
                    pushed_bookings += 1
                    pg_bk_id = new_row["bk_id"]

                    # Menu items for booking
                    items = b.get("menu_items") or []
                    if not items and b.get("bk_id"):
                        try:
                            items = db.fetchall("SELECT * FROM booking_menu_items WHERE bmi_booking_id = ?", (b["bk_id"],))
                        except Exception:
                            items = []
                    for item in items:
                        pg_cur.execute("""
                            INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (pg_bk_id, item.get("bmi_item_name") or item.get("item_name"), item.get("bmi_category") or item.get("category"), item.get("bmi_price", 0.0), item.get("bmi_quantity", 1)))

                    # Invoices
                    inv = b.get("invoice")
                    if not inv and b.get("bk_id"):
                        try:
                            inv = db.fetchone("SELECT * FROM invoices WHERE inv_booking_id = ?", (b["bk_id"],))
                        except Exception:
                            inv = None
                    if inv:
                        pg_cur.execute("""
                            INSERT INTO invoices (inv_booking_id, inv_number, inv_total_amount, inv_amount_paid, inv_status)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (pg_bk_id, inv.get("inv_number") or inv.get("inv_invoice_number") or ref.replace("TB-", "INV-").replace("BK-", "INV-"), inv.get("inv_total_amount", b.get("bk_total_amount")), inv.get("inv_amount_paid", b.get("bk_amount_paid")), inv.get("inv_status", "Unpaid")))

            synced_booking_refs.append(ref)
            if b.get("bk_id"):
                try:
                    db.execute("UPDATE bookings SET sync_status = 'synced' WHERE bk_id = ?", (b["bk_id"],))
                except Exception:
                    pass

        pg_conn.commit()

        # 3. Push locally-edited packages (this kiosk's own price/name/min-pax
        # edits, made via PUT /api/packages/{id}) up to Central PostgreSQL
        # BEFORE pulling — otherwise a price edit (even a legitimate 0) is
        # immediately overwritten by the stale value still on the server.
        pg_cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'packages'
        """)
        pkg_cols = {row["column_name"] for row in pg_cur.fetchall()}
        price_col = "pkg_per_head_price" if "pkg_per_head_price" in pkg_cols else ("pkg_price_per_pax" if "pkg_price_per_pax" in pkg_cols else "pkg_base_price")

        try:
            local_pkgs = db.fetchall("SELECT * FROM packages") or []
        except Exception:
            local_pkgs = []
        for lp in local_pkgs:
            l_name = (lp.get("pkg_name") or "").strip()
            if not l_name:
                continue
            try:
                pg_cur.execute(f"""
                    INSERT INTO packages (pkg_name, pkg_description, {price_col}, pkg_min_pax)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (pkg_name) DO UPDATE SET
                        pkg_description = EXCLUDED.pkg_description,
                        {price_col} = EXCLUDED.{price_col},
                        pkg_min_pax = EXCLUDED.pkg_min_pax
                """, (
                    l_name, lp.get("pkg_description", ""),
                    float(lp["pkg_price_per_pax"]) if lp.get("pkg_price_per_pax") is not None else 350.0,
                    int(lp.get("pkg_min_pax") or 30),
                ))
            except Exception:
                pass
        pg_conn.commit()

        # 4. Pull Master Packages & Menu from Central Server to Tablet
        # (reflects this kiosk's own just-pushed edits plus any changes
        # made elsewhere, so the local cache stays authoritative post-sync)
        pg_cur.execute(f"""
            SELECT pkg_id, pkg_name, COALESCE(pkg_description, '') AS pkg_description,
                   COALESCE({price_col}, 350.0) AS pkg_price_per_pax,
                   COALESCE(pkg_min_pax, 30) AS pkg_min_pax
            FROM packages
            WHERE {"pkg_is_active IS NOT FALSE" if "pkg_is_active" in pkg_cols else "1=1"}
            ORDER BY pkg_id
        """)
        pkgs = [dict(r) for r in pg_cur.fetchall()]
        for p in pkgs:
            try:
                db.execute("""
                    INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(pkg_name) DO UPDATE SET
                        pkg_description = excluded.pkg_description,
                        pkg_price_per_pax = excluded.pkg_price_per_pax,
                        pkg_min_pax = excluded.pkg_min_pax
                """, (
                    p["pkg_name"], p.get("pkg_description", ""),
                    float(p["pkg_price_per_pax"]) if p.get("pkg_price_per_pax") is not None else 350.0,
                    int(p.get("pkg_min_pax") or 30),
                ))
            except Exception:
                pass

        pg_cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'menu_items'
        """)
        mi_cols = {row["column_name"] for row in pg_cur.fetchall()}
        name_col = "mi_name" if "mi_name" in mi_cols else "name"
        cat_col = "mi_category" if "mi_category" in mi_cols else "category"
        pr_col = "mi_price" if "mi_price" in mi_cols else "price"
        st_col = "mi_status" if "mi_status" in mi_cols else "status"
        desc_col = "mi_description" if "mi_description" in mi_cols else "description"

        pg_cur.execute(f"""
            SELECT mi_id,
                   COALESCE({name_col}, '') AS mi_name,
                   COALESCE({cat_col}::TEXT, 'Main Dish') AS mi_category,
                   COALESCE({pr_col}, 0.0) AS mi_price,
                   COALESCE({st_col}::TEXT, 'Available') AS mi_status,
                   COALESCE({desc_col}, '') AS mi_description
            FROM menu_items
            WHERE {"mi_is_active IS NOT FALSE" if "mi_is_active" in mi_cols else "1=1"}
            ORDER BY mi_id
        """)
        menu_items = [dict(r) for r in pg_cur.fetchall()]
        for m in menu_items:
            try:
                ex_m = db.fetchone("SELECT mi_id FROM menu_items WHERE LOWER(mi_name) = LOWER(?)", (m["mi_name"],))
                if ex_m:
                    db.execute("""
                        UPDATE menu_items SET mi_category = ?, mi_price = ?, mi_status = ?, mi_description = ?
                        WHERE mi_id = ?
                    """, (m.get("mi_category", "Main Dish"), float(m.get("mi_price") or 0.0), m.get("mi_status", "Available"), m.get("mi_description", ""), ex_m["mi_id"]))
                else:
                    db.execute("""
                        INSERT INTO menu_items (mi_name, mi_category, mi_price, mi_status, mi_description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (m["mi_name"], m.get("mi_category", "Main Dish"), float(m.get("mi_price") or 0.0), m.get("mi_status", "Available"), m.get("mi_description", "")))
            except Exception:
                pass

        # Also pull package_items if table exists
        package_items = []
        try:
            pg_cur.execute("""
                SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='package_items'
            """)
            if pg_cur.fetchone():
                pg_cur.execute("SELECT pi_id, pi_package_id, pi_item_id FROM package_items")
                package_items = [dict(r) for r in pg_cur.fetchall()]
        except Exception:
            pass

        try:
            db.execute("""
                INSERT INTO tablet_master_sync (tms_source_export_version, tms_packages_count, tms_menu_items_count, tms_customers_count)
                VALUES (?, ?, ?, ?)
            """, (f"LAN-PostgreSQL-{host}", len(pkgs), len(menu_items), pushed_customers))
        except Exception:
            pass

        pg_cur.close()
        pg_conn.close()

    except Exception as exc:
        if 'pg_conn' in locals() and pg_conn:
            try:
                pg_conn.rollback()
                pg_conn.close()
            except Exception:
                pass
        raise HTTPException(500, f"Sync transaction failed: {exc}")

    return {
        "ok": True,
        "pushed_bookings": pushed_bookings,
        "pushed_customers": pushed_customers,
        "pulled_packages": len(pkgs),
        "pulled_menu": len(menu_items),
        "packages": pkgs,
        "menu_items": menu_items,
        "package_items": package_items,
        "synced_booking_refs": synced_booking_refs,
        "synced_customer_names": synced_customer_names,
        "message": f"Sync complete: {pushed_bookings} bookings pushed, {pushed_customers} customers pushed, {len(pkgs)} packages updated, {len(menu_items)} menu items updated."
    }


def _timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Static frontend (must be mounted last so /api/* routes above win) ───

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
