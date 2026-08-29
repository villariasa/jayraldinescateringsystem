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


@app.get("/api/sync/template.xlsx")
def sync_template():
    out_path = EXPORTS_DIR / "master_data_template.xlsx"
    ok = importer.generate_sample_excel_template(str(out_path))
    if not ok:
        raise HTTPException(500, "Template generation failed — is openpyxl installed on the server?")
    return FileResponse(str(out_path), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="master_data_template.xlsx")


def _timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Static frontend (must be mounted last so /api/* routes above win) ───

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
