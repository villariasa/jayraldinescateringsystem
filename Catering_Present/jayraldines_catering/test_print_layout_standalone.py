"""
Standalone verification script for the order-slip print layout.

Run this directly in your dev environment (needs PySide6 installed, same
as the main app):

    python test_print_layout_standalone.py

It does NOT touch the real database - all booking data below is hardcoded.
For each test case it:
  1. Reports the computed half-A4 target height (_SLIP_HALF_HEIGHT) and the
     order's ACTUAL measured content height (via the same QTextDocument
     measurement the print code uses), so you can see which code branch
     (short-order / long-order) it took and why.
  2. Generates a real PDF via the exact same _print_document() code path
     used by the app's Print/Export buttons.
  3. Re-opens that PDF with pypdf and prints page count + page size in mm,
     so "is it A4" and "how many pages" are independently verifiable
     without me claiming to have visually checked anything - I have not
     run this script myself in this environment (no PySide6 available
     here), so please run it yourself and read the printed output.

Requires `pypdf` for the verification step (pip install pypdf). If it's
not installed, the script still generates the PDFs and prints the
pre-render height calculations; open the PDFs manually to check the rest.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinter

import utils.repository as repo
from components.order_print_dialog import OrderPrintDialog, _SLIP_LAYOUT_WIDTH, _SLIP_HALF_HEIGHT


def _fake_business_info():
    return {
        "name": "Jayraldine's Catering",
        "address": "518 V Rama Ave, Cebu City",
        "contact": "+63 912 345 6789",
        "email": "info@jayraldinescatering.com",
    }


# Avoid any real DB/network access - the dialog only needs this one repo call.
repo.get_business_info = _fake_business_info


def _dish(name, category):
    return {"name": name, "category": category}


SHORT_ORDER = {
    "id": "TEST-SHORT-001",
    "booking_ref": "TEST-SHORT-001",
    "name": "Kaira Abellar",
    "customer_name": "Kaira Abellar",
    "venue": "Small Venue, Cebu City",
    "event_date": "2026-10-04",
    "event_time": "12:00 PM",
    "pax": 50,
    "occasion": "Christening",
    "contact": "+63 949 736 2679",
    "package_name": "Wedding Package 35K",
    "notes": "Sky blue",
    "dishes": [
        _dish("Beef with Broccoli", "Main Course"),
        _dish("Special Pork Humba", "Pork"),
        _dish("Sweet & Sour Fish Fillet", "Seafood"),
        _dish("Biko with Latik", "Dessert"),
        _dish("Refillable Iced Tea", "Beverage"),
        _dish("Chicken Pandan", "Poultry"),
    ],
}

LONG_ORDER = {
    "id": "TEST-LONG-001",
    "booking_ref": "TEST-LONG-001",
    "name": "Marco Villareal",
    "customer_name": "Marco Villareal",
    "venue": "Grand Convention Hall, IT Park, Cebu City",
    "event_date": "2026-11-15",
    "event_time": "6:00 PM",
    "pax": 300,
    "occasion": "Corporate Anniversary",
    "contact": "+63 917 555 1234",
    "package_name": "Executive VIP Buffet",
    "notes": "Stage setup needed for awarding. Vegetarian options for 20 guests.",
    "dishes": [
        _dish("Beef with Broccoli", "Main Course"),
        _dish("Special Pork Humba", "Pork"),
        _dish("Sweet & Sour Fish Fillet", "Seafood"),
        _dish("Lechon Belly Roast", "Main Course"),
        _dish("Chicken Pandan", "Poultry"),
        _dish("Beef Caldereta", "Main Course"),
        _dish("Buttered Garlic Shrimp", "Seafood"),
        _dish("Pork Barbecue Skewers", "Pork"),
        _dish("Vegetable Chopsuey", "Vegetables"),
        _dish("Baked Mac & Cheese", "Pasta"),
        _dish("Biko with Latik", "Dessert"),
        _dish("Leche Flan", "Dessert"),
        _dish("Buko Pandan Salad", "Dessert"),
        _dish("Refillable Iced Tea", "Beverage"),
        _dish("Refillable Soda", "Beverage"),
        _dish("Steamed Rice (Unlimited)", "Rice"),
        _dish("Garlic Fried Rice", "Rice"),
        _dish("Dinner Rolls", "Bread"),
        _dish("Garlic Bread", "Bread"),
        _dish("Fruit Platter", "Dessert"),
    ],
}

SHORT_ORDER_2 = {
    "id": "TEST-SHORT-002",
    "booking_ref": "TEST-SHORT-002",
    "name": "Joan Dela Cruz",
    "customer_name": "Joan Dela Cruz",
    "venue": "Backyard, Talisay City",
    "event_date": "2026-09-30",
    "event_time": "3:00 PM",
    "pax": 30,
    "occasion": "Birthday",
    "contact": "+63 918 222 3344",
    "package_name": "Classic Celebration Package",
    "notes": "",
    "dishes": [
        _dish("Fried Chicken", "Poultry"),
        _dish("Pancit Canton", "Noodles"),
        _dish("Fruit Salad", "Dessert"),
        _dish("Refillable Iced Tea", "Beverage"),
    ],
}


def export_pdf_for(bookings, out_path):
    app = QApplication.instance() or QApplication(sys.argv)
    dlg = OrderPrintDialog(bookings)
    printer = QPrinter(QPrinter.HighResolution)
    dlg._configure_a4(printer)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(out_path)
    dlg._print_document(printer)
    return dlg


def report_height(label, dlg, booking):
    body = dlg._build_slip_body(booking, compact=False, pad_scale=1.0)
    h = dlg._measure_height(body)
    branch = "LONG (unconstrained)" if h >= _SLIP_HALF_HEIGHT else "SHORT (grown to fill half-page)"
    print(f"  {label}: natural content height = {h:.1f} doc-units "
          f"(half-page target = {_SLIP_HALF_HEIGHT}) -> {branch}")

    final_html = dlg._build_order_container(booking)
    final_h = dlg._measure_height(final_html)
    print(f"  {label}: FINAL container height after pad_scale growth + spacer "
          f"= {final_h:.1f} (target {_SLIP_HALF_HEIGHT}, diff {final_h - _SLIP_HALF_HEIGHT:+.1f})")


def verify_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"  [pypdf not installed - skipping automated PDF check for {path}]")
        return
    reader = PdfReader(path)
    n_pages = len(reader.pages)
    print(f"  PDF page count: {n_pages}")
    for i, page in enumerate(reader.pages):
        w_pt = float(page.mediabox.width)
        h_pt = float(page.mediabox.height)
        w_mm = w_pt / 72 * 25.4
        h_mm = h_pt / 72 * 25.4
        is_a4 = abs(w_mm - 210) < 2 and abs(h_mm - 297) < 2
        print(f"    page {i+1}: {w_mm:.1f}mm x {h_mm:.1f}mm  (A4? {is_a4})")


if __name__ == "__main__":
    print(f"_SLIP_LAYOUT_WIDTH = {_SLIP_LAYOUT_WIDTH}")
    print(f"_SLIP_HALF_HEIGHT  = {_SLIP_HALF_HEIGHT}  "
          f"(= {_SLIP_LAYOUT_WIDTH} * 297/210 / 2, i.e. half of A4's real aspect ratio)\n")

    print("=== TEST A: single SHORT order (expect: half-page) ===")
    dlg_a = export_pdf_for([SHORT_ORDER], "test_a_short_order.pdf")
    report_height("Order", dlg_a, SHORT_ORDER)
    verify_pdf("test_a_short_order.pdf")
    print()

    print("=== TEST B: single LONG order (expect: full page / no forced half-height) ===")
    dlg_b = export_pdf_for([LONG_ORDER], "test_b_long_order.pdf")
    report_height("Order", dlg_b, LONG_ORDER)
    verify_pdf("test_b_long_order.pdf")
    print()

    print("=== TEST C: two SHORT orders on one page (expect: 1 page, 2 half-page boxes) ===")
    dlg_c = export_pdf_for([SHORT_ORDER, SHORT_ORDER_2], "test_c_two_short_orders.pdf")
    report_height("Order 1", dlg_c, SHORT_ORDER)
    report_height("Order 2", dlg_c, SHORT_ORDER_2)
    verify_pdf("test_c_two_short_orders.pdf")
    print()

    print("Done. Open test_a_short_order.pdf / test_b_long_order.pdf / "
          "test_c_two_short_orders.pdf to visually confirm the layout.")
