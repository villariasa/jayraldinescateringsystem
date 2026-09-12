"""
Data Importer Engine — handles intelligent auto-mapping, file parsing (CSV & Excel),
field normalization, data validation preview, sample template generation, and
batch database insertion for Jayraldine's Catering System.
"""
import os
import re
import csv
import math
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Any, Optional

import utils.repository as repo
import utils.db as db

# ─────────────────────────────────────────────────────────────────────────────
# ENTITY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_SCHEMAS = {
    "all_in_one": {
        "title": "All-in-One Master File (Bookings, Customers, Expenses, Cash Flow, Menu & Packages)",
        "fields": {
            "customer_name": {"label": "Customer Name", "required": False},
            "contact": {"label": "Contact Number", "required": False},
            "email": {"label": "Email Address", "required": False},
            "address": {"label": "Address", "required": False},
            "event_date": {"label": "Event Date", "required": False},
            "event_time": {"label": "Event Time", "required": False},
            "venue": {"label": "Venue / Location", "required": False},
            "occasion": {"label": "Occasion", "required": False},
            "pax": {"label": "Guest Count (Pax)", "required": False},
            "total_amount": {"label": "Booking Total (₱)", "required": False},
            "amount_paid": {"label": "Paid / Down Payment (₱)", "required": False},
            "payment_status": {"label": "Payment Status", "required": False},
            "status": {"label": "Booking Status", "required": False},
            "notes": {"label": "Special Notes / Theme", "required": False},
            "expense_date": {"label": "Expense Date", "required": False},
            "expense_category": {"label": "Expense Category", "required": False},
            "expense_description": {"label": "Expense Description", "required": False},
            "expense_amount": {"label": "Expense Amount (₱)", "required": False},
            "cash_flow_date": {"label": "Cash Flow Date", "required": False},
            "cash_flow_check": {"label": "Check # / Ref", "required": False},
            "cash_flow_particulars": {"label": "Cash Flow Particulars", "required": False},
            "cash_flow_deposit": {"label": "Deposit (₱)", "required": False},
            "cash_flow_withdrawal": {"label": "Withdrawal (₱)", "required": False},
            "cash_flow_sales": {"label": "Actual Sales (₱)", "required": False},
            "menu_item_name": {"label": "Menu Item Name", "required": False},
            "menu_category": {"label": "Menu Category", "required": False},
            "menu_price": {"label": "Menu Price (₱)", "required": False},
            "package_name": {"label": "Package Name", "required": False},
            "package_price": {"label": "Package Price / Pax (₱)", "required": False},
            "package_min_pax": {"label": "Package Min Pax", "required": False},
            "package_description": {"label": "Package Description / Inclusions", "required": False},
        },
        "sample": [
            [
                "Customer Name", "Contact Number", "Email Address", "Address", "Occasion", "Venue", "Event Date", "Event Time", "Pax", "Total Amount (₱)", "Down Paid (₱)", "Status", "Special Notes / Theme",
                "Expense Date", "Expense Category", "Expense Description", "Expense Amount (₱)",
                "Cash Flow Date", "Check # / Ref", "Cash Flow Particulars", "Deposit (₱)", "Withdrawal (₱)", "Actual Sales (₱)",
                "Menu Item Name", "Menu Category", "Menu Price (₱)",
                "Package Name", "Package Price / Pax (₱)", "Package Min Pax", "Package Description / Inclusions"
            ],
            [
                "Engr. Rodrigo Tan", "09178889900", "rodrigo.tan@example.com", "Cebu City", "Wedding", "Grand Ballroom Cebu", datetime.now().strftime("%Y-%m-%d"), "6:00 PM", "150", "45000.00", "45000.00", "CONFIRMED", "Includes Lechon & Backdrop",
                datetime.now().strftime("%Y-%m-%d"), "Food Cost", "Fresh Pork & Spices", "15500.00",
                datetime.now().strftime("%Y-%m-%d"), "CHK-101", "BDO Jayraldine's Catering", "50000.00", "0.00", "132000.00",
                "Special Pork Humba", "Main Course", "450.00",
                "Standard Buffet Package A", "350.00", "50", "4 Main Dishes, 1 Rice, 1 Dessert, Free Flow Drinks"
            ],
            [
                "Capt. Juanito Dela Cruz", "09182223344", "juanito.dc@example.com", "Mandaue City", "Birthday", "Lahug Clubhouse", datetime.now().strftime("%Y-%m-%d"), "12:00 PM", "80", "28000.00", "14000.00", "CONFIRMED", "Buffet Setup",
                datetime.now().strftime("%Y-%m-%d"), "Transport", "Gas for Delivery Van", "2400.00",
                datetime.now().strftime("%Y-%m-%d"), "GCASH-99", "GCash", "12000.00", "0.00", "287965.40",
                "Biko with Latik", "Dessert", "250.00",
                "Premium Wedding Package B", "550.00", "100", "5 Main Dishes with Lechon Belly, 2 Desserts, Themed Setup"
            ],
        ]
    },
    "bookings": {
        "title": "Bookings & Orders",
        "fields": {
            "booking_ref": {"label": "Booking Ref", "required": False},
            "name": {"label": "Customer Name", "required": True},
            "contact": {"label": "Contact Number", "required": False},
            "email": {"label": "Email Address", "required": False},
            "address": {"label": "Address", "required": False},
            "occasion": {"label": "Occasion", "required": False},
            "venue": {"label": "Venue / Location", "required": False},
            "date": {"label": "Event Date", "required": True},
            "time": {"label": "Event Time", "required": False},
            "pax": {"label": "Guest Count (Pax)", "required": True},
            "total": {"label": "Total Amount (₱)", "required": True},
            "amount_paid": {"label": "Down Paid (₱)", "required": False},
            "balance": {"label": "Balance (₱)", "required": False},
            "status": {"label": "Status", "required": False},
            "payment_mode": {"label": "Payment Mode", "required": False},
            "notes": {"label": "Special Notes / Theme", "required": False},
        },
        "sample": [
            ["Booking Ref", "Customer Name", "Contact Number", "Email Address", "Address", "Occasion", "Venue / Location", "Event Date", "Event Time", "Guest Count (Pax)", "Total Amount (₱)", "Down Paid (₱)", "Balance (₱)", "Status", "Payment Mode", "Special Notes / Theme"],
            ["BK-2026-001", "Engr. Rodrigo Tan", "09178889900", "rodrigo.tan@example.com", "Cebu City", "Wedding", "Grand Ballroom Cebu", datetime.now().strftime("%Y-%m-%d"), "6:00 PM", "150", "45000.00", "45000.00", "0.00", "CONFIRMED", "Cash", "Includes Lechon & Backdrop"],
            ["BK-2026-002", "Capt. Juanito Dela Cruz", "09182223344", "juanito.dc@example.com", "Mandaue City", "Birthday", "Lahug Clubhouse", datetime.now().strftime("%Y-%m-%d"), "12:00 PM", "80", "28000.00", "14000.00", "14000.00", "CONFIRMED", "GCash", "Buffet Setup"],
        ]
    },
    "billings": {
        "title": "Billing & Invoices",
        "fields": {
            "invoice_ref": {"label": "Invoice Ref", "required": False},
            "booking_ref": {"label": "Booking Ref", "required": False},
            "customer_name": {"label": "Customer Name", "required": True},
            "contact": {"label": "Contact Number", "required": False},
            "email": {"label": "Email Address", "required": False},
            "event_date": {"label": "Event Date", "required": False},
            "total_amount": {"label": "Total Amount (₱)", "required": True},
            "amount_paid": {"label": "Paid Amount (₱)", "required": False},
            "balance": {"label": "Balance Due (₱)", "required": False},
            "status": {"label": "Payment Status", "required": False},
            "payment_mode": {"label": "Payment Mode", "required": False},
            "notes": {"label": "Notes / Remarks", "required": False},
        },
        "sample": [
            ["Invoice Ref", "Booking Ref", "Customer Name", "Contact Number", "Email Address", "Event Date", "Total Amount (₱)", "Paid Amount (₱)", "Balance Due (₱)", "Payment Status", "Payment Mode", "Notes / Remarks"],
            ["INV-2026-001", "BK-2026-001", "Engr. Rodrigo Tan", "09178889900", "rodrigo.tan@example.com", datetime.now().strftime("%Y-%m-%d"), "45000.00", "45000.00", "0.00", "Paid", "Cash", "Full payment received"],
            ["INV-2026-002", "BK-2026-002", "Capt. Juanito Dela Cruz", "09182223344", "juanito.dc@example.com", datetime.now().strftime("%Y-%m-%d"), "28000.00", "14000.00", "14000.00", "Partial", "GCash", "50% deposit paid"],
            ["INV-2026-003", "BK-2026-003", "Maria Santos", "09171234567", "maria@example.com", datetime.now().strftime("%Y-%m-%d"), "35000.00", "0.00", "35000.00", "Unpaid", "Cash", "Pending down payment"],
        ]
    },
    "customers": {
        "title": "Customers Directory",
        "fields": {
            "id": {"label": "Customer ID", "required": False},
            "name": {"label": "Customer Name", "required": True},
            "contact": {"label": "Contact Number", "required": False},
            "email": {"label": "Email Address", "required": False},
            "address": {"label": "Address", "required": False},
            "status": {"label": "Status", "required": False},
            "notes": {"label": "Notes / History", "required": False},
        },
        "sample": [
            ["Customer ID", "Customer Name", "Contact Number", "Email Address", "Address", "Status", "Notes / History"],
            ["CUS-001", "Maria Santos", "09171234567", "maria@example.com", "Cebu City, Cebu", "Active", "VIP Client"],
            ["CUS-002", "Juan Dela Cruz", "09189876543", "juan@example.com", "Mandaue City, Cebu", "Active", "Prefers Pork Lechon"],
        ]
    },
    "expenses": {
        "title": "Expenses & Operating Costs",
        "fields": {
            "id": {"label": "Expense ID", "required": False},
            "date": {"label": "Expense Date", "required": True},
            "category": {"label": "Category", "required": True},
            "description": {"label": "Description", "required": True},
            "amount": {"label": "Amount (₱)", "required": True},
            "notes": {"label": "Notes / Remarks", "required": False},
        },
        "sample": [
            ["Expense ID", "Expense Date", "Category", "Description", "Amount (₱)", "Notes / Remarks"],
            ["EXP-001", datetime.now().strftime("%Y-%m-%d"), "Food Cost", "Fresh Pork & Spices", "15500.00", "Carbon Market supplier"],
            ["EXP-002", datetime.now().strftime("%Y-%m-%d"), "Transport", "Gas for Delivery Van", "2400.00", "Shell Fuel Station"],
            ["EXP-003", datetime.now().strftime("%Y-%m-%d"), "Labor", "Assistant Cook Daily Pay", "3500.00", "Event staff catering service"],
        ]
    },
    "menu_items": {
        "title": "Menu Items & Dishes",
        "fields": {
            "id": {"label": "Item ID", "required": False},
            "name": {"label": "Item Name", "required": True},
            "category": {"label": "Category", "required": True},
            "package": {"label": "Package Tier", "required": False},
            "price": {"label": "Price / Rate (₱)", "required": True},
            "status": {"label": "Status", "required": False},
            "description": {"label": "Description / Inclusions", "required": False},
        },
        "sample": [
            ["Item ID", "Item Name", "Category", "Package Tier", "Price / Rate (₱)", "Status", "Description / Inclusions"],
            ["MI-001", "Special Pork Humba", "Main Course", "Standard", "450.00", "Available", "Serves 8-10 pax with boiled eggs"],
            ["MI-002", "Creamy Carbonara", "Noodles", "Premium", "380.00", "Available", "Rich parmesan & bacon platter"],
            ["MI-003", "Biko with Latik", "Dessert", "Standard", "250.00", "Available", "1 Large Tray traditional sticky rice"],
        ]
    },
    "packages": {
        "title": "Catering Packages",
        "fields": {
            "id": {"label": "Package ID", "required": False},
            "name": {"label": "Package Name", "required": True},
            "price_per_pax": {"label": "Price Per Pax (₱)", "required": True},
            "min_pax": {"label": "Minimum Pax", "required": False},
            "description": {"label": "Description / Inclusions", "required": False},
        },
        "sample": [
            ["Package ID", "Package Name", "Price Per Pax (₱)", "Minimum Pax", "Description / Inclusions"],
            ["PKG-001", "Standard Buffet Package A", "350.00", "50", "4 Main Dishes, 1 Rice, 1 Dessert, Free Flow Drinks"],
            ["PKG-002", "Premium Wedding Package B", "550.00", "100", "5 Main Dishes with Lechon Belly, 2 Desserts, Themed Setup"],
            ["PKG-003", "Executive Corporate Package", "450.00", "30", "4 Main Dishes, Soup, Salad, Dessert, Sound System"],
        ]
    },
    "cash_flow": {
        "title": "Cash Flow Transactions",
        "fields": {
            "id": {"label": "Transaction ID", "required": False},
            "date": {"label": "Date", "required": True},
            "check_no": {"label": "Check #", "required": False},
            "particulars": {"label": "Particulars (Account / Detail)", "required": True},
            "deposit": {"label": "Deposit (₱)", "required": False},
            "withdrawal": {"label": "Withdrawal (₱)", "required": False},
            "actual_sales": {"label": "Actual Sales (₱)", "required": False},
            "notes": {"label": "Remarks / Notes", "required": False},
        },
        "sample": [
            ["Transaction ID", "Date", "Check #", "Particulars (Account / Detail)", "Deposit (₱)", "Withdrawal (₱)", "Running Balance (₱)", "Actual Sales (₱)", "Variance / Difference (₱)", "Remarks / Notes"],
            ["TX-001", datetime.now().strftime("%Y-%m-%d"), "CHK-101", "BDO Jayraldine's Catering", "50000.00", "0.00", "50000.00", "132000.00", "0.00", "Initial account deposit"],
            ["TX-002", datetime.now().strftime("%Y-%m-%d"), "", "Cash on Hand", "0.00", "15000.00", "35000.00", "70000.00", "0.00", "Ingredients market withdrawal"],
            ["TX-003", datetime.now().strftime("%Y-%m-%d"), "GCASH-99", "GCash", "12000.00", "0.00", "47000.00", "287965.40", "0.00", "Customer down payment"],
        ]
    }
}

ENTITY_HEADER_ALIASES = {
    "all_in_one": {
        "customer_name": ["customer name", "client name", "customer", "client", "full name", "name"],
        "contact": ["contact number", "phone number", "contact", "phone", "mobile", "cellphone", "tel"],
        "email": ["email address", "email", "e mail", "mail"],
        "address": ["home address", "client address", "customer address", "address", "city", "street"],
        "event_date": ["event date", "booking date", "event fecha"],
        "event_time": ["event time", "time", "start time", "schedule"],
        "venue": ["venue location", "event venue", "venue", "location", "place", "site"],
        "occasion": ["occasion", "event type", "celebration", "party", "theme"],
        "pax": ["guest count pax", "guest count", "pax", "guests", "number of guests", "headcount", "capacity"],
        "total_amount": ["booking total", "total amount", "total amount php", "total", "grand total"],
        "amount_paid": ["down paid", "down paid php", "paid amount", "paid amount php", "amount paid", "down payment", "deposit paid", "deposit", "total paid"],
        "payment_status": ["payment status", "billing status", "pay status", "invoice status"],
        "status": ["booking status", "order status", "status", "state"],
        "notes": ["special notes theme", "special notes", "notes theme", "notes history", "notes", "theme", "remarks"],
        "expense_date": ["expense date", "exp date"],
        "expense_category": ["expense category", "exp category", "expense type"],
        "expense_description": ["expense description", "exp description", "expense particulars"],
        "expense_amount": ["expense amount", "exp amount", "expense amount php"],
        "cash_flow_date": ["cash flow date", "tx date", "transaction date"],
        "cash_flow_check": ["check ref", "check no", "check number", "check"],
        "cash_flow_particulars": ["cash flow particulars", "particulars account detail", "particulars"],
        "cash_flow_deposit": ["deposit php", "deposit", "credit", "cash in"],
        "cash_flow_withdrawal": ["withdrawal php", "withdrawal", "debit", "cash out"],
        "cash_flow_sales": ["actual sales php", "actual sales", "gross sales"],
        "menu_item_name": ["menu item name", "item name", "dish name"],
        "menu_category": ["menu category", "dish category"],
        "menu_price": ["menu price", "item price", "dish price", "price rate"],
        "package_name": ["package name", "pkg name"],
        "package_price": ["package price pax", "price per pax", "package price"],
        "package_min_pax": ["package min pax", "minimum pax", "min pax"],
        "package_description": ["package description inclusions", "package description"],
    },
    "bookings": {
        "booking_ref": ["booking ref", "booking reference", "order ref", "booking id", "bk ref", "order number", "booking number", "id"],
        "name": ["customer name", "client name", "customer", "client", "full name", "name"],
        "contact": ["contact number", "phone number", "contact", "phone", "mobile", "cellphone", "tel"],
        "email": ["email address", "email", "e mail", "mail"],
        "address": ["client address", "home address", "customer address", "address", "city", "street"],
        "occasion": ["occasion", "event type", "celebration", "party", "theme"],
        "venue": ["venue location", "event venue", "venue", "location", "place", "site"],
        "date": ["event date", "booking date", "date", "fecha"],
        "time": ["event time", "time", "schedule", "start time"],
        "pax": ["guest count pax", "guest count", "pax", "guests", "number of guests", "attendees", "headcount", "capacity"],
        "total": ["total amount php", "total amount", "booking total", "total", "amount", "cost", "price", "grand total"],
        "amount_paid": ["down paid php", "down paid", "paid amount php", "paid amount", "amount paid", "down payment", "deposit paid", "deposit", "total paid", "cash paid"],
        "balance": ["balance php", "balance", "balance due", "remaining balance", "unpaid balance"],
        "status": ["booking status", "order status", "status", "state"],
        "payment_mode": ["payment mode", "payment method", "paid via", "mode", "method"],
        "notes": ["special notes theme", "special notes add ons", "special notes", "notes theme", "add ons", "notes", "remarks", "theme", "comments"],
    },
    "billings": {
        "invoice_ref": ["invoice ref", "invoice number", "inv no", "invoice id", "inv ref", "invoice", "id"],
        "booking_ref": ["booking ref", "booking reference", "order ref", "booking id", "bk ref", "order number", "booking number"],
        "customer_name": ["customer name", "client name", "customer", "client", "full name", "name"],
        "contact": ["contact number", "phone number", "contact", "phone", "mobile", "cellphone", "tel"],
        "email": ["email address", "email", "e mail", "customer email", "mail"],
        "event_date": ["event date", "booking date", "invoice date", "date", "fecha"],
        "total_amount": ["total amount php", "total amount", "total", "amount", "grand total", "subtotal", "fee", "cost"],
        "amount_paid": ["paid amount php", "paid amount", "down paid php", "down paid", "amount paid", "paid", "down payment", "deposit", "total paid"],
        "balance": ["balance due php", "balance due", "balance php", "balance", "remaining balance", "unpaid balance", "due"],
        "status": ["payment status", "billing status", "invoice status", "status", "state"],
        "payment_mode": ["payment mode", "payment method", "paid via", "mode", "method"],
        "notes": ["notes remarks", "notes", "remarks", "memo", "comments", "details"],
    },
    "customers": {
        "id": ["customer id", "client id", "id", "customer number", "code"],
        "name": ["customer name", "client name", "full name", "name", "customer", "client"],
        "contact": ["contact number", "phone number", "contact", "phone", "mobile", "cellphone", "tel"],
        "email": ["email address", "email", "e mail", "mail"],
        "address": ["customer address", "client address", "home address", "address", "location", "city", "street"],
        "status": ["customer status", "account status", "status", "state"],
        "notes": ["notes history", "notes", "history", "remarks", "memo", "details", "comments"],
    },
    "expenses": {
        "id": ["expense id", "exp id", "id", "ref", "code"],
        "date": ["expense date", "transaction date", "date", "entry date", "fecha"],
        "category": ["expense category", "exp category", "category", "expense type", "type", "group"],
        "description": ["expense description", "description", "particulars", "details", "memo", "summary"],
        "amount": ["expense amount php", "expense amount", "amount php", "amount", "cost php", "cost", "price", "subtotal", "rate"],
        "notes": ["notes remarks", "remarks notes", "notes", "remarks", "memo", "comments"],
    },
    "menu_items": {
        "id": ["item id", "menu item id", "id", "dish id", "code"],
        "name": ["item name", "dish name", "item package name", "item", "dish", "name", "title"],
        "category": ["menu category", "item category", "dish category", "category", "type", "group"],
        "package": ["package tier", "tier", "package", "standard"],
        "price": ["price rate php", "price rate", "price php", "price", "rate", "cost", "unit price", "amount"],
        "status": ["item status", "status", "availability", "available"],
        "description": ["description inclusions", "description", "inclusions", "details", "notes", "summary"],
    },
    "packages": {
        "id": ["package id", "pkg id", "id", "code"],
        "name": ["package name", "pkg name", "package", "name", "title"],
        "price_per_pax": ["price per pax php", "price per pax", "rate per pax php", "rate per pax", "package price", "price", "rate"],
        "min_pax": ["minimum pax", "min pax", "minimum guests", "pax", "capacity"],
        "description": ["package description inclusions", "description inclusions", "description", "inclusions", "details", "notes", "menu items"],
    },
    "cash_flow": {
        "id": ["transaction id", "cft id", "tx id", "id", "ref"],
        "date": ["transaction date", "entry date", "date", "tx date", "fecha"],
        "check_no": ["check number", "check ref", "check no", "check", "ref", "reference", "voucher no", "or no"],
        "particulars": ["particulars account detail", "particulars", "account name", "account", "bank", "source", "description"],
        "deposit": ["deposit php", "deposit", "credit", "amount in", "cash in", "inflow"],
        "withdrawal": ["withdrawal php", "withdrawal", "debit", "amount out", "cash out", "outflow", "disbursement"],
        "actual_sales": ["actual sales php", "actual sales", "actual sale", "gross sales", "sales amount", "daily sales", "sales"],
        "notes": ["remarks notes", "notes remarks", "remarks", "notes", "memo", "comments", "variance difference"],
    }
}


def _clean_header_str(text: str) -> str:
    """Strip symbols, punctuation, parentheses, and extra spaces for resilient matching."""
    s = str(text or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def detect_file_entity_type(headers: List[str]) -> str:
    """Intelligently score headers to determine which entity type a single-sheet file belongs to."""
    if not headers:
        return "customers"

    h_clean = [_clean_header_str(h) for h in headers]
    h_text = " ".join(h_clean)

    # 1. Cash Flow
    if any(k in h_clean for k in ("deposit", "withdrawal", "running balance", "particulars account detail", "particulars", "actual sales")):
        return "cash_flow"

    # 2. Billing / Invoices
    if any(k in h_clean for k in ("invoice ref", "paid amount", "balance due", "payment status")) and not any(k in h_clean for k in ("guest count pax", "venue location", "occasion")):
        return "billings"

    # 3. Bookings
    if any(k in h_clean for k in ("booking ref", "guest count pax", "venue location", "occasion", "down paid", "special notes theme")) or ("event date" in h_clean and ("pax" in h_clean or "total amount" in h_clean)):
        return "bookings"

    # 4. Catering Packages
    if any(k in h_clean for k in ("price per pax", "minimum pax", "package name", "package min pax", "min pax")):
        return "packages"

    # 5. Menu Items
    if any(k in h_clean for k in ("item name", "item id", "package tier", "menu category", "dish name")) or ("price rate" in h_clean and "category" in h_clean):
        return "menu_items"

    # 6. Expenses
    if any(k in h_clean for k in ("expense date", "expense id", "expense amount", "expense category", "expense description")) or ("expense" in h_text and "amount" in h_text):
        return "expenses"

    # 7. Customers
    if any(k in h_clean for k in ("customer id", "customer name", "notes history", "client name")):
        return "customers"

    # Fallback checks
    if "expense" in h_text:
        return "expenses"
    if "menu" in h_text or "dish" in h_text:
        return "menu_items"
    if "package" in h_text:
        return "packages"
    if "booking" in h_text or "event" in h_text:
        return "bookings"
    if "invoice" in h_text or "billing" in h_text:
        return "billings"
    if "deposit" in h_text or "withdraw" in h_text or "particular" in h_text:
        return "cash_flow"

    return "customers"


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def normalize_expense_category(cat: Any) -> str:
    if not cat:
        return "Other"
    s = str(cat).strip().lower()
    if any(w in s for w in ["food", "meat", "pork", "beef", "chicken", "fish", "vegetable", "spice", "ingredient", "grocery", "market", "rice", "dish", "beverage", "drink"]):
        return "Food Cost"
    if any(w in s for w in ["labor", "salary", "wage", "cook", "chef", "crew", "helper", "staff", "assistant", "payroll", "waiter"]):
        return "Labor"
    if any(w in s for w in ["transport", "transpo", "gas", "fuel", "diesel", "delivery", "van", "truck", "fare", "parking"]):
        return "Transport"
    if any(w in s for w in ["util", "electric", "water", "power", "gasul", "lpg", "internet", "bill", "phone"]):
        return "Utilities"
    if any(w in s for w in ["equip", "rent", "table", "chair", "tent", "chafing", "utensil", "plate", "pot", "pan", "appliance", "sound", "light"]):
        return "Equipment"
    return "Other"


def normalize_booking_status(status: Any) -> str:
    if not status:
        return "PENDING"
    s = str(status).strip().upper()
    if "CONFIRM" in s:
        return "CONFIRMED"
    if "COMPLET" in s:
        return "COMPLETED"
    if "CANCEL" in s:
        return "CANCELLED"
    return "PENDING"


def normalize_customer_status(status: Any) -> str:
    if not status:
        return "Active"
    s = str(status).strip().lower()
    if "inact" in s or "dorm" in s:
        return "Inactive"
    if "pend" in s:
        return "Pending"
    return "Active"


def normalize_menu_status(status: Any) -> str:
    if not status:
        return "Available"
    s = str(status).strip().lower()
    if any(w in s for w in ("unavail", "inact", "out", "disab", "no")):
        return "Unavailable"
    return "Available"


def normalize_menu_category(cat: Any) -> str:
    if not cat:
        return "Main Course"
    s = str(cat).strip().lower()
    if "nood" in s or "pasta" in s or "pancit" in s or "spaghetti" in s:
        return "Noodles"
    if "soup" in s or "broth" in s or "sinigang" in s or "tinola" in s:
        return "Soup"
    if "veg" in s or "salad" in s:
        return "Vegetables"
    if "dessert" in s or "sweet" in s or "cake" in s or "biko" in s or "leche" in s:
        return "Dessert"
    if "drink" in s or "beverage" in s or "juice" in s or "soda" in s or "tea" in s:
        return "Drinks"
    if "bread" in s or "pastry" in s or "bun" in s:
        return "Bread"
    if "pack" in s or "set" in s:
        return "Other"
    if any(w in s for w in ["main", "pork", "beef", "chicken", "fish", "seafood", "meat", "lechon", "humba", "caldereta"]):
        return "Main Course"
    return "Other"


def normalize_amount(raw: Any) -> float:
    if raw is None:
        return 0.0
    s = str(raw).strip()
    if s in ("—", "-", "", "N/A", "none", "null"):
        return 0.0
    # Handle accounting format: (1,234.50) -> -1234.50
    is_neg = False
    if s.startswith("(") and s.endswith(")"):
        is_neg = True
        s = s[1:-1]
    s = re.sub(r"[^\d.-]", "", s.replace(",", ""))
    try:
        val = float(s)
        return -val if is_neg else val
    except ValueError:
        return 0.0


def normalize_date(raw: Any) -> str:
    if not raw:
        return datetime.now().strftime("%Y-%m-%d")

    if isinstance(raw, datetime):
        return raw.strftime("%Y-%m-%d")
    if isinstance(raw, date):
        return raw.strftime("%Y-%m-%d")

    # Numeric Excel serial date (e.g. 45000 -> date in 2023-2030)
    if isinstance(raw, (int, float)):
        try:
            if 20000 <= raw <= 80000:
                dt = datetime(1899, 12, 30) + timedelta(days=float(raw))
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    s = str(raw).strip()
    if not s or s in ("—", "-", "N/A", "none", "null"):
        return datetime.now().strftime("%Y-%m-%d")

    # If already YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # Strip time suffix if present e.g. " 00:00:00", "T18:30:00", " 12:00:00 PM"
    clean_s = re.sub(r"[T\s]+\d{1,2}:\d{2}(:\d{2})?(\.\d+)?(\s*[AP]M)?.*$", "", s, flags=re.IGNORECASE).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", clean_s):
        return clean_s

    # Also check if clean_s is numeric excel serial as string
    if clean_s.replace(".", "", 1).isdigit() and len(clean_s) in (5, 6, 7):
        try:
            num = float(clean_s)
            if 20000 <= num <= 80000:
                dt = datetime(1899, 12, 30) + timedelta(days=num)
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    date_formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y",
        "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y",
        "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y",
        "%b-%d-%Y", "%B-%d-%Y",
        "%m/%d/%y", "%d/%m/%y", "%y-%m-%d"
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(clean_s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    try:
        dt = datetime.fromisoformat(s[:10])
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    return datetime.now().strftime("%Y-%m-%d")


def normalize_pax(raw: Any) -> int:
    if not raw:
        return 50
    s = str(raw).strip()
    s = re.sub(r"\D", "", s)
    try:
        v = int(s)
        return max(1, v)
    except ValueError:
        return 50


# ─────────────────────────────────────────────────────────────────────────────
# FILE PARSING (CSV & EXCEL)
# ─────────────────────────────────────────────────────────────────────────────

def parse_file(file_path: str) -> Tuple[List[str], List[Dict[str, str]], Optional[str]]:
    if not os.path.exists(file_path):
        return [], [], "File does not exist."

    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return _parse_excel(file_path)
    return _parse_csv(file_path)


def _parse_csv(file_path: str) -> Tuple[List[str], List[Dict[str, str]], Optional[str]]:
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "utf-16"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                sample = f.read(4096)
                f.seek(0)
                delimiter = ","
                if ";" in sample and sample.count(";") > sample.count(","):
                    delimiter = ";"
                elif "\t" in sample and sample.count("\t") > sample.count(","):
                    delimiter = "\t"

                reader = csv.reader(f, delimiter=delimiter)
                rows_raw = [row for row in reader if any(cell.strip() for cell in row)]
                if not rows_raw:
                    return [], [], "CSV file is empty."

                headers = [h.strip() for h in rows_raw[0]]
                data_rows = []
                for idx, raw_row in enumerate(rows_raw[1:], start=2):
                    row_dict = {}
                    for h_idx, h_name in enumerate(headers):
                        val = raw_row[h_idx].strip() if h_idx < len(raw_row) else ""
                        row_dict[h_name] = val
                    data_rows.append(row_dict)

                return headers, data_rows, None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return [], [], f"Failed to read CSV: {e}"

    return [], [], "Unsupported text encoding."


def _parse_excel(file_path: str) -> Tuple[List[str], List[Dict[str, str]], Optional[str]]:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active
        rows_raw = []
        for row in sheet.iter_rows(values_only=True):
            if row and any(cell is not None and str(cell).strip() for cell in row):
                rows_raw.append([str(c).strip() if c is not None else "" for c in row])

        if not rows_raw:
            return [], [], "Excel worksheet is empty."

        headers = rows_raw[0]
        data_rows = []
        for raw_row in rows_raw[1:]:
            row_dict = {}
            for h_idx, h_name in enumerate(headers):
                val = raw_row[h_idx] if h_idx < len(raw_row) else ""
                row_dict[h_name] = val
            data_rows.append(row_dict)

        return headers, data_rows, None
    except Exception as e:
        return [], [], f"Failed to read Excel file: {e}"


def parse_master_file(file_path: str) -> Tuple[Dict[str, Tuple[List[str], List[Dict[str, str]]]], Optional[str]]:
    """Parse a multi-sheet Excel file or single-sheet master file into entity sections.
    Returns ({entity_type: (headers, data_rows)}, error_message)."""
    if not os.path.exists(file_path):
        return {}, "File does not exist."

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".xlsx", ".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            if len(wb.sheetnames) > 1:
                result = {}
                for sheetname in wb.sheetnames:
                    sheet = wb[sheetname]
                    rows_raw = []
                    for row in sheet.iter_rows(values_only=True):
                        if row and any(cell is not None and str(cell).strip() for cell in row):
                            rows_raw.append([str(c).strip() if c is not None else "" for c in row])
                    if not rows_raw:
                        continue

                    headers = rows_raw[0]
                    data_rows = []
                    for raw_row in rows_raw[1:]:
                        row_dict = {headers[i]: (raw_row[i] if i < len(raw_row) else "") for i in range(len(headers))}
                        data_rows.append(row_dict)

                    sn_lower = sheetname.lower().strip()
                    entity = "customers"
                    if "cash" in sn_lower or "flow" in sn_lower or "ledger" in sn_lower or "deposit" in sn_lower:
                        entity = "cash_flow"
                    elif "expense" in sn_lower or "cost" in sn_lower:
                        entity = "expenses"
                    elif "billing" in sn_lower or "invoice" in sn_lower:
                        entity = "billings"
                    elif "booking" in sn_lower or "order" in sn_lower or "event" in sn_lower:
                        entity = "bookings"
                    elif "package" in sn_lower:
                        entity = "packages"
                    elif "menu" in sn_lower or "dish" in sn_lower or "item" in sn_lower:
                        entity = "menu_items"
                    elif "customer" in sn_lower or "client" in sn_lower:
                        entity = "customers"
                    else:
                        entity = detect_file_entity_type(headers)

                    result[entity] = (headers, data_rows)

                if result:
                    return result, None
        except Exception:
            pass

    # Single sheet / CSV file auto-detection
    headers, rows, err = parse_file(file_path)
    if err:
        return {}, err

    detected = detect_file_entity_type(headers)
    result = {detected: (headers, rows)}
    return result, None


# ─────────────────────────────────────────────────────────────────────────────
# INTELLIGENT AUTO-MAPPING & NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def auto_map_headers(headers: List[str], entity_type: str) -> Dict[str, str]:
    """Auto-detect which uploaded column header maps to system fields for entity_type."""
    canon_entity = normalize_entity_type(entity_type)
    schema = ENTITY_SCHEMAS.get(canon_entity, {})
    fields = schema.get("fields", {})
    mapping = {}

    entity_aliases = ENTITY_HEADER_ALIASES.get(canon_entity, {})
    headers_clean = {h: _clean_header_str(h) for h in headers}

    assigned_headers = set()

    # Step 1: Exact matches (priority order of aliases)
    for field_key in fields.keys():
        aliases = [_clean_header_str(a) for a in entity_aliases.get(field_key, [field_key])]
        matched_header = ""
        for alias in aliases:
            for h_orig, h_clean in headers_clean.items():
                if h_clean == alias and h_orig not in assigned_headers:
                    matched_header = h_orig
                    break
            if matched_header:
                break
        if matched_header:
            mapping[field_key] = matched_header
            assigned_headers.add(matched_header)

    # Step 2: Safe word token matching (preventing false overlaps like 'address' in 'email address' or 'id' in 'paid')
    for field_key in fields.keys():
        if field_key in mapping:
            continue
        aliases = [_clean_header_str(a) for a in entity_aliases.get(field_key, [field_key])]
        matched_header = ""
        for alias in aliases:
            alias_words = set(alias.split())
            for h_orig, h_clean in headers_clean.items():
                if h_orig in assigned_headers:
                    continue
                h_words = set(h_clean.split())
                # Disallow known hazardous matches
                if field_key == "address" and "email" in h_words:
                    continue
                if field_key == "name" and ("id" in h_words or "code" in h_words or "package" in h_words or "dish" in h_words):
                    continue
                if field_key in ("id", "booking_ref", "invoice_ref") and ("paid" in h_words or "down" in h_words or "balance" in h_words):
                    continue

                if alias_words.issubset(h_words) or (len(alias) >= 4 and alias in h_clean):
                    matched_header = h_orig
                    break
            if matched_header:
                break
        if matched_header:
            mapping[field_key] = matched_header
            assigned_headers.add(matched_header)
        else:
            mapping[field_key] = ""

    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION & PREVIEW GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def validate_and_prepare_rows(
    data_rows: List[Dict[str, str]],
    mapping: Dict[str, str],
    entity_type: str
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    canon_entity = normalize_entity_type(entity_type)
    schema = ENTITY_SCHEMAS.get(canon_entity, {})
    fields = schema.get("fields", {})

    prepared = []
    counts = {"valid": 0, "warning": 0, "error": 0}

    for idx, row in enumerate(data_rows, start=1):
        issues = []
        status = "valid"
        sanitized = {}

        for field_key, field_info in fields.items():
            mapped_h = mapping.get(field_key, "")
            raw_val = row.get(mapped_h, "").strip() if mapped_h else ""

            if field_info.get("required") and not raw_val:
                issues.append(f"Missing required field '{field_info['label']}'")
                status = "error"

            if field_key in ("amount", "total", "price", "total_amount", "expense_amount", "amount_paid", "balance", "deposit", "withdrawal", "actual_sales", "menu_price", "package_price", "price_per_pax"):
                val = normalize_amount(raw_val)
                if val <= 0 and field_info.get("required"):
                    issues.append(f"Invalid amount '{raw_val}'")
                    status = "error"
                sanitized[field_key] = val
            elif field_key in ("date", "event_date", "expense_date", "cash_flow_date"):
                if raw_val:
                    sanitized[field_key] = normalize_date(raw_val)
                else:
                    sanitized[field_key] = datetime.now().strftime("%Y-%m-%d")
            elif field_key in ("pax", "package_min_pax", "min_pax"):
                sanitized[field_key] = normalize_pax(raw_val)
            elif field_key in ("category", "expense_category", "menu_category"):
                sanitized[field_key] = normalize_expense_category(raw_val) if canon_entity in ("expenses", "all_in_one") else normalize_menu_category(raw_val)
            elif field_key in ("status", "payment_status"):
                if canon_entity == "billings" or field_key == "payment_status":
                    sanitized[field_key] = raw_val.strip()
                elif canon_entity == "bookings":
                    sanitized[field_key] = normalize_booking_status(raw_val)
                elif canon_entity == "menu_items":
                    sanitized[field_key] = normalize_menu_status(raw_val)
                else:
                    sanitized[field_key] = normalize_customer_status(raw_val)
            else:
                sanitized[field_key] = raw_val

        # Warning checks
        if canon_entity == "customers" and sanitized.get("contact"):
            if not re.search(r"\d{7,}", sanitized["contact"]):
                issues.append("Contact number format warning")
                if status == "valid":
                    status = "warning"

        if status == "valid":
            counts["valid"] += 1
        elif status == "warning":
            counts["warning"] += 1
        else:
            counts["error"] += 1

        prepared.append({
            "_row_index": idx,
            "_status": status,
            "_issues": issues,
            "_data": sanitized,
            "_raw": row,
        })

    return prepared, counts


# ─────────────────────────────────────────────────────────────────────────────
# BATCH DATABASE INSERTION
# ─────────────────────────────────────────────────────────────────────────────

def execute_batch_import(
    prepared_rows: List[Dict[str, Any]],
    entity_type: str,
    skip_errors: bool = True
) -> Tuple[int, int, List[str]]:
    canon_entity = normalize_entity_type(entity_type)
    success_count = 0
    fail_count = 0
    errors = []
    seen_customer_names = set()
    seen_cash_flow = set()

    for row_info in prepared_rows:
        row_idx = row_info.get("_row_index", "?")
        row_info.setdefault("_row_index", row_idx)
        if row_info.get("_status") == "error" and skip_errors:
            fail_count += 1
            err_details = ", ".join(row_info.get("_issues", ["Validation failed"]))
            errors.append(f"Row {row_idx} skipped: {err_details}")
            continue

        data = row_info.get("_data", row_info)
        try:
            if canon_entity == "customers":
                cust_name = data.get("name", "").strip()
                if not cust_name:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Customer Name]: Value cannot be empty.")
                    continue

                name_key = cust_name.lower()
                existing_cust = repo.get_customer_by_name(cust_name)
                if existing_cust:
                    # Update existing customer details seamlessly
                    try:
                        c_id = existing_cust.get("id") or existing_cust.get("cus_id")
                        if c_id:
                            db.execute("""
                                UPDATE customers
                                SET cus_contact = COALESCE(NULLIF(%s, ''), cus_contact),
                                    cus_email = COALESCE(NULLIF(%s, ''), cus_email),
                                    cus_address = COALESCE(NULLIF(%s, ''), cus_address),
                                    cus_status = %s::customer_status
                                WHERE cus_id = %s
                            """, (
                                data.get("contact", "").strip(),
                                data.get("email", "").strip(),
                                data.get("address", "").strip(),
                                normalize_customer_status(data.get("status")),
                                c_id
                            ))
                        success_count += 1
                    except Exception as e_up:
                        success_count += 1  # Existing customer kept intact
                else:
                    res = repo.add_customer({
                        "name": cust_name,
                        "contact": data.get("contact", "").strip(),
                        "email": data.get("email", "").strip(),
                        "address": data.get("address", "").strip(),
                        "status": normalize_customer_status(data.get("status")),
                        "notes": data.get("notes", "").strip(),
                    })
                    if res:
                        seen_customer_names.add(name_key)
                        success_count += 1
                    else:
                        fail_count += 1
                        errors.append(f"Row {row_info['_row_index']} [Customer: '{cust_name}']: Database insert failed.")

            elif canon_entity == "expenses":
                amount_val = float(data.get("amount", 0.0))
                if amount_val <= 0:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Amount]: Expense amount must be greater than 0.")
                    continue

                res = repo.add_expense({
                    "category": normalize_expense_category(data.get("category")),
                    "description": data.get("description", "Imported Expense").strip() or "Imported Expense",
                    "amount": amount_val,
                    "date": data.get("date") or datetime.now().strftime("%Y-%m-%d"),
                })
                if res:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Category: '{data.get('category')}']: Expense database insert failed.")

            elif canon_entity == "bookings":
                cust_name = data.get("name", "").strip()
                total_val = float(data.get("total", 0.0))
                if not cust_name:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Customer Name]: Booking customer name cannot be empty.")
                    continue
                if total_val <= 0:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Total Amount]: Booking total amount must be greater than 0.")
                    continue

                paid_val = normalize_amount(data.get("amount_paid") or data.get("paid") or data.get("paid_amount") or data.get("down_paid") or data.get("down_payment") or 0.0)
                raw_status = str(data.get("payment_status") or data.get("status") or "").strip()
                raw_upper = raw_status.upper()
                if ("PAID" in raw_upper or "FULL" in raw_upper) and paid_val <= 0 and total_val > 0:
                    paid_val = total_val

                # Imports carry no customer id, so match/auto-create the
                # customer by name so the booking links into bk_customer_id —
                # v_customer_ledger and customer tracking key off that FK, not
                # the free-text bk_customer_name.
                cust_row = db.fetchone(
                    "SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(%s) LIMIT 1",
                    (cust_name,),
                )
                cust_id = cust_row["cus_id"] if cust_row else repo.add_customer({
                    "name": cust_name,
                    "contact": data.get("contact", "").strip(),
                    "email": data.get("email", "").strip(),
                    "address": data.get("address", "").strip(),
                })

                bkg_payload = {
                    "name": cust_name,
                    "contact": data.get("contact", "").strip(),
                    "email": data.get("email", "").strip(),
                    "address": data.get("address", "").strip() or data.get("venue", "").strip() or "Cebu City",
                    "occasion": data.get("occasion", "").strip() or "Catering Event",
                    "venue": data.get("venue", "").strip() or "Catering Venue",
                    "date": data.get("date") or datetime.now().strftime("%Y-%m-%d"),
                    "time": data.get("time", "").strip() or "6:00 PM",
                    "pax": int(data.get("pax", 50)),
                    "notes": data.get("notes", "").strip(),
                    "menu_type": "package",
                    "total": total_val,
                    "payment_mode": str(data.get("payment_mode") or "Cash").strip(),
                    "amount_paid": paid_val,
                    "down_payment": paid_val,
                }
                # Skip creating a duplicate booking if one for this customer/date
                # already exists (e.g. the same import file was re-run after a
                # partial failure) — update it in place instead.
                event_date_norm = normalize_date(data.get("date")) or bkg_payload["date"]
                existing_bk = db.fetchone("""
                    SELECT bk_id FROM bookings
                    WHERE LOWER(bk_customer_name) = LOWER(%s) AND bk_event_date = %s
                    LIMIT 1
                """, (cust_name, event_date_norm))

                b_id = existing_bk["bk_id"] if existing_bk else None
                if not b_id:
                    res = repo.create_booking(bkg_payload)
                    if res and res.get("booking_id"):
                        b_id = res["booking_id"]

                if b_id:
                    if cust_id:
                        db.execute("UPDATE bookings SET bk_customer_id = %s WHERE bk_id = %s", (cust_id, b_id))

                    target_status = normalize_booking_status(data.get("status"))
                    if target_status == "COMPLETED":
                        try:
                            repo.update_booking_status(b_id, "CONFIRMED")
                            repo.update_booking_status(b_id, "COMPLETED")
                        except Exception:
                            pass
                    elif target_status in ("CONFIRMED", "CANCELLED"):
                        try:
                            repo.update_booking_status(b_id, target_status)
                        except Exception:
                            pass

                    # Preserve invoice payment and status (Paid / Partial / Unpaid)
                    bal_val = max(0.0, total_val - paid_val)
                    inv_st = db.compute_invoice_status(total_val, paid_val)
                    if "PAID" in raw_upper and bal_val <= 0.01:
                        inv_st = "Paid"
                    elif "PARTIAL" in raw_upper:
                        inv_st = "Partial"
                    elif "UNPAID" in raw_upper:
                        inv_st = "Unpaid"

                    db.execute("""
                        UPDATE invoices
                        SET inv_total_amount = %s, inv_amount_paid = %s, inv_balance = %s,
                            inv_down_payment = %s, inv_status = %s, inv_payment_verified = %s
                        WHERE inv_booking_id = %s
                    """, (total_val, paid_val, bal_val, paid_val, inv_st, 1 if paid_val > 0 else 0, b_id))
                    if paid_val > 0:
                        db.execute("""
                            UPDATE bookings
                            SET bk_amount_paid = %s, bk_down_payment = %s,
                                bk_down_payment_status = 'ACCEPTED'
                            WHERE bk_id = %s
                        """, (paid_val, paid_val, b_id))

                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Booking: '{cust_name}']: Booking database insert failed.")

            elif canon_entity == "billings":
                cust_name = str(data.get("customer_name") or data.get("name") or "").strip()
                total_val = normalize_amount(data.get("total_amount") or data.get("total") or data.get("amount") or 0.0)
                paid_val = normalize_amount(data.get("amount_paid") or data.get("paid") or data.get("paid_amount") or data.get("down_paid") or data.get("down_payment") or 0.0)
                inv_ref = str(data.get("invoice_ref") or data.get("invoice") or "").strip()
                bk_ref = str(data.get("booking_ref") or "").strip()
                raw_st = str(data.get("status") or data.get("payment_status") or "").strip().upper()
                if ("PAID" in raw_st or "FULL" in raw_st) and paid_val <= 0 and total_val > 0:
                    paid_val = total_val

                # Try finding matching invoice by invoice_ref, booking_ref, or customer + date
                existing_inv = None
                if inv_ref:
                    existing_inv = db.fetchone("SELECT inv_id, inv_booking_id FROM invoices WHERE inv_invoice_ref = %s LIMIT 1", (inv_ref,))
                if not existing_inv and bk_ref:
                    existing_inv = db.fetchone("""
                        SELECT i.inv_id, i.inv_booking_id
                        FROM invoices i
                        JOIN bookings b ON b.bk_id = i.inv_booking_id
                        WHERE b.bk_booking_ref = %s
                        LIMIT 1
                    """, (bk_ref,))
                if not existing_inv and cust_name:
                    e_date = normalize_date(data.get("event_date") or data.get("date"))
                    existing_inv = db.fetchone("""
                        SELECT inv_id, inv_booking_id
                        FROM invoices
                        WHERE LOWER(inv_customer_name) = LOWER(%s)
                          AND inv_event_date = %s
                        LIMIT 1
                    """, (cust_name, e_date))

                if existing_inv:
                    inv_id = existing_inv["inv_id"]
                    bk_id = existing_inv["inv_booking_id"]
                    bal_val = max(0.0, total_val - paid_val)
                    inv_st = db.compute_invoice_status(total_val, paid_val)
                    if "PAID" in raw_st and bal_val <= 0.01:
                        inv_st = "Paid"
                    elif "PARTIAL" in raw_st:
                        inv_st = "Partial"
                    elif "UNPAID" in raw_st:
                        inv_st = "Unpaid"

                    db.execute("""
                        UPDATE invoices
                        SET inv_total_amount = %s, inv_amount_paid = %s, inv_balance = %s,
                            inv_down_payment = %s, inv_status = %s, inv_payment_verified = 1
                        WHERE inv_id = %s
                    """, (total_val, paid_val, bal_val, paid_val, inv_st, inv_id))
                    if bk_id:
                        db.execute("""
                            UPDATE bookings
                            SET bk_total_amount = %s, bk_amount_paid = %s,
                                bk_down_payment = %s, bk_down_payment_status = 'ACCEPTED'
                            WHERE bk_id = %s
                        """, (total_val, paid_val, paid_val, bk_id))
                    success_count += 1
                else:
                    if not cust_name:
                        fail_count += 1
                        errors.append(f"Row {row_info['_row_index']}: Customer name is required.")
                        continue
                    bkg_payload = {
                        "name": cust_name,
                        "contact": data.get("contact", "").strip(),
                        "email": data.get("email", "").strip(),
                        "address": data.get("address", "").strip() or "Cebu City",
                        "occasion": "Catering Event",
                        "venue": "Catering Venue",
                        "date": normalize_date(data.get("event_date") or data.get("date")),
                        "time": "6:00 PM",
                        "pax": 50,
                        "notes": data.get("notes", "").strip(),
                        "menu_type": "package",
                        "total": total_val,
                        "payment_mode": str(data.get("payment_mode") or "Cash").strip(),
                        "amount_paid": paid_val,
                    }
                    res = repo.create_booking(bkg_payload)
                    if res and res.get("booking_id"):
                        b_id = res["booking_id"]

                        cust_row = db.fetchone(
                            "SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(%s) LIMIT 1",
                            (cust_name,),
                        )
                        cust_id = cust_row["cus_id"] if cust_row else repo.add_customer({
                            "name": cust_name,
                            "contact": data.get("contact", "").strip(),
                            "email": data.get("email", "").strip(),
                            "address": data.get("address", "").strip(),
                        })
                        if cust_id:
                            db.execute("UPDATE bookings SET bk_customer_id = %s WHERE bk_id = %s", (cust_id, b_id))

                        bal_val = max(0.0, total_val - paid_val)
                        inv_st = db.compute_invoice_status(total_val, paid_val)
                        if "PAID" in raw_st and bal_val <= 0.01:
                            inv_st = "Paid"
                        elif "PARTIAL" in raw_st:
                            inv_st = "Partial"
                        elif "UNPAID" in raw_st:
                            inv_st = "Unpaid"

                        db.execute("""
                            UPDATE invoices
                            SET inv_total_amount = %s, inv_amount_paid = %s, inv_balance = %s,
                                inv_down_payment = %s, inv_status = %s, inv_payment_verified = %s
                            WHERE inv_booking_id = %s
                        """, (total_val, paid_val, bal_val, paid_val, inv_st, 1 if paid_val > 0 else 0, b_id))
                        if paid_val > 0:
                            db.execute("""
                                UPDATE bookings
                                SET bk_amount_paid = %s, bk_down_payment = %s,
                                    bk_down_payment_status = 'ACCEPTED'
                                WHERE bk_id = %s
                            """, (paid_val, paid_val, b_id))
                        success_count += 1
                    else:
                        fail_count += 1
                        errors.append(f"Row {row_info['_row_index']} [Billing: '{cust_name}']: Booking creation failed.")

            elif canon_entity == "menu_items":
                item_name = data.get("name", "New Item").strip() or "New Item"
                price_val = float(data.get("price", 0.0))
                if price_val <= 0:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Price]: Menu item price must be greater than 0.")
                    continue

                item_payload = {
                    "item": item_name,
                    "category": normalize_menu_category(data.get("category")),
                    "package": str(data.get("package") or "Standard").strip() or "Standard",
                    "price": price_val,
                    "status": normalize_menu_status(data.get("status")),
                    "description": data.get("description", "").strip(),
                }
                res = repo.add_menu_item(item_payload)
                if res:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Item: '{item_name}']: Menu item database insert failed.")

            elif canon_entity == "cash_flow":
                t_date = normalize_date(data.get("date") or datetime.now().strftime("%Y-%m-%d"))
                t_particulars = str(data.get("particulars") or "Cash on Hand").strip()
                t_check = str(data.get("check_no") or data.get("check") or "").strip()
                t_deposit = normalize_amount(data.get("deposit") or 0.0)
                t_withdrawal = normalize_amount(data.get("withdrawal") or 0.0)
                t_actual_sales = normalize_amount(data.get("actual_sales") or data.get("sales") or 0.0)
                t_notes = str(data.get("notes") or "").strip()

                if t_deposit > 0 or t_withdrawal > 0 or t_actual_sales > 0 or t_particulars:
                    cf_key = (t_date, t_check.lower(), t_particulars.lower(), round(t_deposit, 2), round(t_withdrawal, 2), round(t_actual_sales, 2))
                    if cf_key in seen_cash_flow:
                        success_count += 1
                        continue
                    if repo.find_duplicate_cash_flow(t_date, t_particulars, t_deposit, t_withdrawal, t_actual_sales, t_check):
                        seen_cash_flow.add(cf_key)
                        success_count += 1
                        continue

                    tx_id = repo.add_cash_flow_transaction({
                        "date": t_date,
                        "check_no": t_check,
                        "particulars": t_particulars,
                        "deposit": t_deposit,
                        "withdrawal": t_withdrawal,
                        "actual_sales": t_actual_sales,
                        "notes": t_notes,
                    })
                    if tx_id:
                        seen_cash_flow.add(cf_key)
                        success_count += 1
                    else:
                        fail_count += 1
                        errors.append(f"Row {row_info['_row_index']}: Cash flow transaction insert failed.")
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']}: Empty cash flow entry.")

            elif canon_entity == "packages":
                pkg_name = str(data.get("name") or data.get("package_name") or "").strip()
                if not pkg_name:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Package Name]: Package name cannot be empty.")
                    continue
                pkg_price = normalize_amount(data.get("price_per_pax") or data.get("price") or 0.0)
                pkg_min_pax = int(normalize_pax(data.get("min_pax") or data.get("pax") or 1))
                pkg_desc = str(data.get("description") or "").strip()
                pkg_res = repo.add_package({
                    "name": pkg_name,
                    "price_per_pax": pkg_price,
                    "min_pax": pkg_min_pax,
                    "description": pkg_desc,
                })
                if pkg_res:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']} [Package: '{pkg_name}']: Package insert failed (may already exist).")

            elif canon_entity == "all_in_one":
                row_success = False

                # 1. Customer & Booking
                cust_name = (data.get("customer_name") or data.get("name", "")).strip()
                if cust_name:
                    repo.add_customer({
                        "name": cust_name,
                        "contact": data.get("contact", "").strip(),
                        "email": data.get("email", "").strip(),
                        "address": data.get("address", "").strip() or data.get("venue", "").strip(),
                        "status": "Active",
                    })

                    total_amt = float(data.get("total_amount") or data.get("total", 0.0))
                    if total_amt > 0:
                        paid_val = normalize_amount(data.get("amount_paid") or data.get("paid") or data.get("paid_amount") or data.get("down_paid") or 0.0)
                        raw_st = str(data.get("payment_status") or data.get("status") or "").strip().upper()
                        if ("PAID" in raw_st or "FULL" in raw_st) and paid_val <= 0:
                            paid_val = total_amt

                        bkg_res = repo.create_booking({
                            "name": cust_name,
                            "contact": data.get("contact", "").strip(),
                            "email": data.get("email", "").strip(),
                            "address": data.get("address", "").strip() or data.get("venue", "").strip() or "Cebu City",
                            "occasion": data.get("occasion", "").strip() or "Event",
                            "venue": data.get("venue", "").strip() or "TBD",
                            "date": data.get("event_date") or data.get("date") or datetime.now().strftime("%Y-%m-%d"),
                            "time": data.get("event_time") or data.get("time") or "6:00 PM",
                            "pax": int(data.get("pax", 50)),
                            "total": total_amt,
                            "notes": data.get("notes", "").strip(),
                            "menu_type": "package",
                            "payment_mode": "Cash",
                            "amount_paid": paid_val,
                            "down_payment": paid_val,
                        })
                        if bkg_res and bkg_res.get("booking_id"):
                            b_id = bkg_res["booking_id"]
                            bal_val = max(0.0, total_amt - paid_val)
                            inv_st = db.compute_invoice_status(total_amt, paid_val)
                            if "PAID" in raw_st and bal_val <= 0.01:
                                inv_st = "Paid"
                            elif "PARTIAL" in raw_st:
                                inv_st = "Partial"
                            db.execute("""
                                UPDATE invoices
                                SET inv_total_amount = %s, inv_amount_paid = %s, inv_balance = %s,
                                    inv_down_payment = %s, inv_status = %s, inv_payment_verified = %s
                                WHERE inv_booking_id = %s
                            """, (total_amt, paid_val, bal_val, paid_val, inv_st, 1 if paid_val > 0 else 0, b_id))
                            if paid_val > 0:
                                db.execute("""
                                    UPDATE bookings
                                    SET bk_amount_paid = %s, bk_down_payment = %s,
                                        bk_down_payment_status = 'ACCEPTED'
                                    WHERE bk_id = %s
                                """, (paid_val, paid_val, b_id))
                            row_success = True

                # 2. Expense
                exp_amt = float(data.get("expense_amount") or data.get("amount", 0.0))
                if exp_amt > 0:
                    exp_res = repo.add_expense({
                        "category": normalize_expense_category(data.get("expense_category") or data.get("category")),
                        "description": data.get("expense_description", "Master File Expense").strip() or "Master File Expense",
                        "amount": exp_amt,
                        "date": data.get("expense_date") or data.get("date") or datetime.now().strftime("%Y-%m-%d"),
                    })
                    if exp_res:
                        row_success = True

                # 3. Cash Flow (with deduplication)
                cf_part = str(data.get("cash_flow_particulars") or data.get("particulars") or "").strip()
                cf_dep = normalize_amount(data.get("cash_flow_deposit") or data.get("deposit") or 0.0)
                cf_withd = normalize_amount(data.get("cash_flow_withdrawal") or data.get("withdrawal") or 0.0)
                cf_sales = normalize_amount(data.get("cash_flow_sales") or data.get("actual_sales") or 0.0)
                cf_date = normalize_date(data.get("cash_flow_date") or data.get("date") or datetime.now().strftime("%Y-%m-%d"))
                cf_chk = str(data.get("cash_flow_check") or data.get("check_no") or "").strip()

                if cf_part or cf_dep > 0 or cf_withd > 0 or cf_sales > 0:
                    cf_key = (cf_date, cf_chk.lower(), (cf_part or "Cash on Hand").lower(), round(cf_dep, 2), round(cf_withd, 2), round(cf_sales, 2))
                    if cf_key not in seen_cash_flow and not repo.find_duplicate_cash_flow(cf_date, cf_part or "Cash on Hand", cf_dep, cf_withd, cf_sales, cf_chk):
                        cf_res = repo.add_cash_flow_transaction({
                            "date": cf_date,
                            "check_no": cf_chk,
                            "particulars": cf_part or "Cash on Hand",
                            "deposit": cf_dep,
                            "withdrawal": cf_withd,
                            "actual_sales": cf_sales,
                            "notes": "Imported via Master Template",
                        })
                        if cf_res:
                            seen_cash_flow.add(cf_key)
                            row_success = True
                    else:
                        row_success = True  # Counted as handled (not double inserted)

                # 4. Menu Item
                mi_name = str(data.get("menu_item_name") or data.get("dish_name") or "").strip()
                mi_price = normalize_amount(data.get("menu_price") or 0.0)
                if mi_name and mi_price > 0:
                    mi_res = repo.add_menu_item({
                        "item": mi_name,
                        "category": normalize_menu_category(data.get("menu_category")),
                        "package": "Standard",
                        "price": mi_price,
                        "status": "Available",
                        "description": "",
                    })
                    if mi_res:
                        row_success = True

                # 5. Package
                pkg_n = str(data.get("package_name") or "").strip()
                pkg_p = normalize_amount(data.get("package_price") or 0.0)
                if pkg_n and pkg_p > 0:
                    p_res = repo.add_package({
                        "name": pkg_n,
                        "price_per_pax": pkg_p,
                        "min_pax": int(data.get("package_min_pax") or 1),
                        "description": str(data.get("package_description") or "").strip(),
                    })
                    if p_res:
                        row_success = True

                if row_success:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']}: No valid booking, expense, cash flow, menu or package data found.")

        except Exception as e:
            fail_count += 1
            errors.append(f"Row {row_info['_row_index']}: {e}")

    # Emit app data change signals and run automatic deduplication
    if success_count > 0:
        try:
            if canon_entity in ("customers", "bookings", "billings", "all_in_one"):
                repo.merge_duplicate_customers()
                repo.recalculate_all_customer_stats()
        except Exception:
            pass

        try:
            from utils.signals import app_events
            ev = app_events()
            ev.data_changed.emit()
            if canon_entity == "expenses":
                ev.expense_saved.emit()
            elif canon_entity == "customers":
                ev.customer_saved.emit()
            elif canon_entity in ("bookings", "billings"):
                ev.booking_saved.emit()
                ev.payment_saved.emit()
            elif canon_entity == "cash_flow":
                ev.cash_flow_saved.emit()
            elif canon_entity in ("packages", "menu_items"):
                ev.menu_saved.emit()
            elif canon_entity == "all_in_one":
                ev.customer_saved.emit()
                ev.booking_saved.emit()
                ev.payment_saved.emit()
                ev.expense_saved.emit()
                ev.cash_flow_saved.emit()
                ev.menu_saved.emit()
        except Exception:
            pass

    return success_count, fail_count, errors


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE TEMPLATE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def normalize_entity_type(key: str) -> str:
    """Normalize any entity key alias to its canonical schema key."""
    k = (key or "").strip().lower().replace("-", "_").replace(" ", "_")
    if k in ("booking", "bookings", "order", "orders", "booking_order", "bookings_orders"):
        return "bookings"
    if k in ("billing", "billings", "invoice", "invoices", "billing_invoice", "billings_invoices"):
        return "billings"
    if k in ("customer", "customers", "client", "clients"):
        return "customers"
    if k in ("expense", "expenses", "cost", "costs"):
        return "expenses"
    if k in ("package", "packages", "pkg", "pkgs", "catering_package", "catering_packages"):
        return "packages"
    if k in ("menu", "menus", "menu_item", "menu_items", "dish", "dishes"):
        return "menu_items"
    if k in ("cash_flow", "cashflow", "cash", "ledger", "transactions", "cash_flow_transactions"):
        return "cash_flow"
    if k in ("all_in_one", "all", "master", "allinone", "all_in_one_master", "all_system_data", "master_file"):
        return "all_in_one"
    return k


def generate_sample_csv(entity_type: str, save_path: str) -> Optional[str]:
    """Generate sample CSV or Excel file with clean headers, formatting, and example data."""
    canon_entity = normalize_entity_type(entity_type)
    ext = os.path.splitext(save_path)[1].lower()

    if not ext:
        save_path = f"{save_path}.xlsx"
        ext = ".xlsx"

    if ext in (".xlsx", ".xls"):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            header_fill = PatternFill(start_color="E11D48", end_color="E11D48", fill_type="solid")
            header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
            data_font = Font(name="Arial", size=10)
            thin_border = Border(
                left=Side(style='thin', color='CBD5E1'),
                right=Side(style='thin', color='CBD5E1'),
                top=Side(style='thin', color='CBD5E1'),
                bottom=Side(style='thin', color='CBD5E1')
            )

            def style_sheet(ws, rows):
                for row_idx, r in enumerate(rows, start=1):
                    ws.append(r)
                    for col_idx in range(1, len(r) + 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        cell.border = thin_border
                        if row_idx == 1:
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        else:
                            cell.font = data_font
                            cell.alignment = Alignment(vertical="center")

                ws.row_dimensions[1].height = 28
                for r_idx in range(2, len(rows) + 1):
                    ws.row_dimensions[r_idx].height = 22

                for col in ws.columns:
                    max_len = 0
                    col_letter = get_column_letter(col[0].column)
                    for cell in col:
                        val_str = str(cell.value or "")
                        if len(val_str) > max_len:
                            max_len = len(val_str)
                    ws.column_dimensions[col_letter].width = max(max_len + 5, 14)

            if canon_entity == "all_in_one":
                wb.remove(wb.active)  # remove default sheet
                sections = ["bookings", "customers", "billings", "expenses", "cash_flow", "menu_items", "packages"]
                for sec in sections:
                    s_info = ENTITY_SCHEMAS.get(sec, {})
                    title_name = s_info.get("title", sec.title())
                    if len(title_name) > 31:
                        title_name = sec.replace("_", " ").title()
                    ws = wb.create_sheet(title=title_name)
                    style_sheet(ws, s_info.get("sample", []))
            else:
                ws = wb.active
                schema = ENTITY_SCHEMAS.get(canon_entity, {})
                title_name = schema.get("title", "Template")
                if len(title_name) > 31:
                    title_name = canon_entity.replace("_", " ").title()
                ws.title = title_name
                style_sheet(ws, schema.get("sample", []))

            wb.save(save_path)
            return None
        except Exception as e:
            return f"Failed to save Excel template: {e}"

    # CSV fallback
    schema = ENTITY_SCHEMAS.get(canon_entity)
    if not schema:
        return f"Unknown entity type: {entity_type}"

    sample_rows = schema.get("sample", [])
    try:
        with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(sample_rows)
        return None
    except Exception as e:
        return f"Failed to save CSV template: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# SMART DATABASE MERGE — multi-device conflict-safe import
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_merge_key(name, event_date, occasion) -> tuple:
    n = re.sub(r"[^\w]", "", str(name or "").strip().lower())
    d = str(event_date or "")
    o = re.sub(r"[^\w]", "", str(occasion or "").strip().lower())
    return (n, d, o)


def _sync_paid_from_payment_records(booking_id: int, inv_id: int) -> float:
    """bk_amount_paid / inv_amount_paid must reflect the actual, complete
    payment_records sum after a merge inserts rows directly -
    _recalc_booking_totals() trusts bk_amount_paid rather than re-summing
    (and never touches inv_amount_paid at all), so both must be kept
    correct here before it runs."""
    paid_row = db.fetchone("SELECT COALESCE(SUM(pr_amount), 0.0) AS s FROM payment_records WHERE pr_invoice_id = ?", (inv_id,))
    total_paid = float(paid_row["s"]) if paid_row else 0.0
    db.execute("UPDATE bookings SET bk_amount_paid = ? WHERE bk_id = ?", (total_paid, booking_id))
    db.execute("UPDATE invoices SET inv_amount_paid = ? WHERE inv_id = ?", (total_paid, inv_id))
    return total_paid


def merge_database_file(source_path: str, actor: str = "staff") -> dict:
    """Smart multi-device merge: import ALL DATA from another device's backup
    .db file into the current database without ever downgrading or erasing
    valid financial progress already recorded here.

    Bookings are matched by a stable natural key (customer name + event date
    + occasion) since separate installs generate their own independent
    booking-ref sequences. For a booking that already exists locally, only
    NEW payment records and additional charges (ones that don't already
    exist here, matched by amount/date/method or amount/date/description)
    are merged in - existing local payments/charges are never removed or
    altered, and the paid amount can only ever grow. The final billing
    status is always recalculated from the complete, combined payment
    history via compute_invoice_status() - the imported status text itself
    is never trusted.
    """
    stats = {
        "new_bookings": 0, "matched_bookings": 0,
        "new_payments": 0, "new_charges": 0, "terms_merged": 0,
        "new_customers": 0, "matched_customers": 0,
        "invoices_recalculated": 0, "errors": [],
    }
    if not source_path or not os.path.exists(source_path):
        stats["errors"].append("Source backup file not found.")
        return stats

    try:
        db.execute("ATTACH DATABASE ? AS src", (source_path,))
    except Exception as exc:
        stats["errors"].append(f"Could not open backup file: {exc}")
        return stats

    try:
        # ── 1. CUSTOMER IMPORT & DEDUPLICATION VALIDATION ────────────────
        def find_or_create_customer(name: str, contact: str = "", email: str = "", address: str = "") -> int:
            name_clean = (name or "").strip()
            contact_clean = (contact or "").strip()
            email_clean = (email or "").strip()
            addr_clean = (address or "").strip()

            if not name_clean:
                name_clean = "Guest Customer"

            # 1. Match by Contact Phone Number
            if contact_clean:
                row = db.fetchone("SELECT cus_id, cus_email, cus_address FROM customers WHERE cus_contact = ? AND cus_contact != '' LIMIT 1", (contact_clean,))
                if row:
                    # Update missing details on local record
                    if (not row.get("cus_email") and email_clean) or (not row.get("cus_address") and addr_clean):
                        db.execute("UPDATE customers SET cus_email = COALESCE(NULLIF(cus_email, ''), ?), cus_address = COALESCE(NULLIF(cus_address, ''), ?) WHERE cus_id = ?",
                                   (email_clean, addr_clean, row["cus_id"]))
                    return row["cus_id"]

            # 2. Match by Email Address
            if email_clean:
                row = db.fetchone("SELECT cus_id, cus_contact, cus_address FROM customers WHERE LOWER(cus_email) = LOWER(?) AND cus_email != '' LIMIT 1", (email_clean,))
                if row:
                    if (not row.get("cus_contact") and contact_clean) or (not row.get("cus_address") and addr_clean):
                        db.execute("UPDATE customers SET cus_contact = COALESCE(NULLIF(cus_contact, ''), ?), cus_address = COALESCE(NULLIF(cus_address, ''), ?) WHERE cus_id = ?",
                                   (contact_clean, addr_clean, row["cus_id"]))
                    return row["cus_id"]

            # 3. Match by Case-Insensitive Full Name
            row = db.fetchone("SELECT cus_id, cus_contact, cus_email, cus_address FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", (name_clean,))
            if row:
                if (not row.get("cus_contact") and contact_clean) or (not row.get("cus_email") and email_clean) or (not row.get("cus_address") and addr_clean):
                    db.execute("UPDATE customers SET cus_contact = COALESCE(NULLIF(cus_contact, ''), ?), cus_email = COALESCE(NULLIF(cus_email, ''), ?), cus_address = COALESCE(NULLIF(cus_address, ''), ?) WHERE cus_id = ?",
                               (contact_clean, email_clean, addr_clean, row["cus_id"]))
                return row["cus_id"]

            # 4. No duplicate found -> Insert new customer profile
            db.execute("""
                INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status)
                VALUES (?, ?, ?, ?, 'Active')
            """, (name_clean, contact_clean, email_clean, addr_clean))
            new_id_row = db.fetchone("SELECT last_insert_rowid() AS id")
            return new_id_row["id"] if new_id_row else 1

        # Process all customers from src.customers if available
        try:
            src_customers = db.fetchall("SELECT * FROM src.customers")
            for sc in src_customers:
                c_name = sc.get("cus_name") or ""
                c_contact = sc.get("cus_contact") or ""
                c_email = sc.get("cus_email") or ""
                c_addr = sc.get("cus_address") or ""
                
                # Check if already exists before calling
                pre_existing = db.fetchone(
                    "SELECT cus_id FROM customers WHERE (cus_contact != '' AND cus_contact = ?) OR (cus_email != '' AND LOWER(cus_email) = LOWER(?)) OR LOWER(cus_name) = LOWER(?) LIMIT 1",
                    (c_contact, c_email, c_name)
                )
                find_or_create_customer(c_name, c_contact, c_email, c_addr)
                if pre_existing:
                    stats["matched_customers"] += 1
                else:
                    stats["new_customers"] += 1
        except Exception:
            pass  # src might not have customers table

        local_rows = db.fetchall("SELECT bk_id, bk_booking_ref, bk_customer_name, bk_event_date, bk_occasion FROM bookings")
        local_by_key = {
            _normalize_merge_key(r["bk_customer_name"], r["bk_event_date"], r["bk_occasion"]): r["bk_id"]
            for r in local_rows
        }
        local_by_ref = {
            r["bk_booking_ref"].strip().upper(): r["bk_id"]
            for r in local_rows if r.get("bk_booking_ref")
        }

        try:
            src_bookings = db.fetchall("""
                SELECT bk_id, bk_booking_ref, bk_customer_name, bk_address, bk_event_date, bk_event_time,
                       bk_venue, bk_occasion, bk_pax, bk_notes, bk_menu_type, bk_total_amount,
                       COALESCE(bk_base_total, bk_total_amount) AS base_total,
                       bk_payment_mode, bk_status
                FROM src.bookings
            """)
        except Exception as exc:
            stats["errors"].append(f"Could not read bookings from backup: {exc}")
            src_bookings = []

        for sb in src_bookings:
            src_ref = (sb.get("bk_booking_ref") or "").strip().upper()
            key = _normalize_merge_key(sb["bk_customer_name"], sb["bk_event_date"], sb["bk_occasion"])
            dest_bk_id = local_by_ref.get(src_ref) or local_by_key.get(key)

            src_inv = db.fetchone("SELECT inv_id FROM src.invoices WHERE inv_booking_id = ? LIMIT 1", (sb["bk_id"],))
            src_payments = db.fetchall("SELECT * FROM src.payment_records WHERE pr_invoice_id = ?", (src_inv["inv_id"],)) if src_inv else []
            try:
                src_charges = db.fetchall("SELECT * FROM src.booking_additional_charges WHERE ac_booking_id = ?", (sb["bk_id"],))
            except Exception:
                src_charges = []
            try:
                src_menu_items = db.fetchall("SELECT * FROM src.booking_menu_items WHERE bmi_booking_id = ?", (sb["bk_id"],))
            except Exception:
                src_menu_items = []
            try:
                src_terms = db.fetchall("SELECT * FROM src.terms_acknowledgements WHERE ta_booking_id = ?", (sb["bk_id"],))
            except Exception:
                src_terms = []

            try:
                if dest_bk_id is None:
                    cust_id = find_or_create_customer(sb["bk_customer_name"], address=sb["bk_address"] or "")
                    booking_ref = sb.get("bk_booking_ref") or f"TB-IMP-{abs(hash(key)) % 1000000:06d}"
                    db.execute("""
                        INSERT INTO bookings (
                            bk_booking_ref, bk_customer_id, bk_customer_name, bk_address, bk_event_date, bk_event_time,
                            bk_venue, bk_occasion, bk_pax, bk_notes, bk_menu_type, bk_total_amount, bk_base_total,
                            bk_payment_mode, bk_amount_paid, bk_down_payment, bk_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?)
                    """, (
                        booking_ref, cust_id, sb["bk_customer_name"], sb["bk_address"], sb["bk_event_date"], sb["bk_event_time"],
                        sb["bk_venue"], sb["bk_occasion"], sb["bk_pax"], sb["bk_notes"], sb["bk_menu_type"],
                        sb["base_total"], sb["base_total"], sb["bk_payment_mode"], sb["bk_status"] or "PENDING",
                    ))
                    new_bk_id = db.fetchone("SELECT last_insert_rowid() AS id")["id"]

                    inv_num = f"INV-IMP-{new_bk_id:06d}"
                    db.execute("""
                        INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name,
                            inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_status)
                        VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 'Unpaid')
                    """, (new_bk_id, inv_num, inv_num, sb["bk_customer_name"], sb["bk_event_date"], sb["base_total"], sb["base_total"]))
                    new_inv_id = db.fetchone("SELECT last_insert_rowid() AS id")["id"]

                    for p in src_payments:
                        db.execute("""
                            INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes, pr_is_downpayment)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (new_inv_id, p["pr_amount"], p["pr_payment_date"], p.get("pr_payment_method") or p.get("pr_method") or "Cash",
                              p.get("pr_notes") or p.get("pr_note") or "", p.get("pr_is_downpayment") or 0))
                        stats["new_payments"] += 1

                    for c in src_charges:
                        db.execute("""
                            INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
                            VALUES (?, ?, ?, ?, ?)
                        """, (new_bk_id, c["ac_description"], c["ac_amount"], c["ac_date_added"], c.get("ac_added_by") or "Imported"))
                        stats["new_charges"] += 1

                    for mi in src_menu_items:
                        db.execute("""
                            INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
                            VALUES (?, NULL, ?, ?, ?, ?)
                        """, (new_bk_id, mi.get("bmi_item_name"), mi.get("bmi_category"), mi.get("bmi_price") or 0.0, mi.get("bmi_quantity") or 1))

                    for t in src_terms:
                        db.execute("""
                            INSERT INTO terms_acknowledgements (ta_booking_id, ta_version, ta_acknowledged, ta_acknowledged_at, ta_customer_name)
                            VALUES (?, ?, ?, ?, ?)
                        """, (new_bk_id, t.get("ta_version"), t.get("ta_acknowledged") or 0, t.get("ta_acknowledged_at"), t.get("ta_customer_name")))
                        stats["terms_merged"] += 1

                    _sync_paid_from_payment_records(new_bk_id, new_inv_id)
                    repo._recalc_booking_totals(new_bk_id)
                    stats["new_bookings"] += 1

                else:
                    stats["matched_bookings"] += 1
                    dest_inv = db.fetchone("SELECT inv_id FROM invoices WHERE inv_booking_id = ? LIMIT 1", (dest_bk_id,))
                    if not dest_inv:
                        continue
                    dest_inv_id = dest_inv["inv_id"]

                    existing_payments = db.fetchall(
                        "SELECT pr_amount, pr_payment_date, pr_payment_method FROM payment_records WHERE pr_invoice_id = ?",
                        (dest_inv_id,))
                    existing_keys = {
                        (round(float(p["pr_amount"] or 0), 2), str(p["pr_payment_date"]), str(p.get("pr_payment_method") or ""))
                        for p in existing_payments
                    }
                    for p in src_payments:
                        pkey = (round(float(p["pr_amount"] or 0), 2), str(p["pr_payment_date"]),
                                str(p.get("pr_payment_method") or p.get("pr_method") or ""))
                        if pkey in existing_keys:
                            continue
                        db.execute("""
                            INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes, pr_is_downpayment)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (dest_inv_id, p["pr_amount"], p["pr_payment_date"], p.get("pr_payment_method") or p.get("pr_method") or "Cash",
                              p.get("pr_notes") or p.get("pr_note") or "", p.get("pr_is_downpayment") or 0))
                        stats["new_payments"] += 1

                    existing_charges = db.fetchall(
                        "SELECT ac_description, ac_amount, ac_date_added FROM booking_additional_charges WHERE ac_booking_id = ?",
                        (dest_bk_id,))
                    existing_charge_keys = {
                        (str(c["ac_description"] or "").strip().lower(), round(float(c["ac_amount"] or 0), 2), str(c["ac_date_added"]))
                        for c in existing_charges
                    }
                    for c in src_charges:
                        ckey = (str(c["ac_description"] or "").strip().lower(), round(float(c["ac_amount"] or 0), 2), str(c["ac_date_added"]))
                        if ckey in existing_charge_keys:
                            continue
                        db.execute("""
                            INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by)
                            VALUES (?, ?, ?, ?, ?)
                        """, (dest_bk_id, c["ac_description"], c["ac_amount"], c["ac_date_added"], c.get("ac_added_by") or "Imported"))
                        stats["new_charges"] += 1

                    existing_menu_items = db.fetchall(
                        "SELECT bmi_item_name, bmi_category FROM booking_menu_items WHERE bmi_booking_id = ?",
                        (dest_bk_id,))
                    existing_menu_keys = {
                        (str(m["bmi_item_name"] or "").strip().lower(), str(m["bmi_category"] or "").strip().lower())
                        for m in existing_menu_items
                    }
                    for mi in src_menu_items:
                        mkey = (str(mi.get("bmi_item_name") or "").strip().lower(), str(mi.get("bmi_category") or "").strip().lower())
                        if mkey in existing_menu_keys:
                            continue
                        db.execute("""
                            INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity)
                            VALUES (?, NULL, ?, ?, ?, ?)
                        """, (dest_bk_id, mi.get("bmi_item_name"), mi.get("bmi_category"), mi.get("bmi_price") or 0.0, mi.get("bmi_quantity") or 1))

                    existing_terms_versions = {
                        str(t["ta_version"]) for t in
                        db.fetchall("SELECT ta_version FROM terms_acknowledgements WHERE ta_booking_id = ?", (dest_bk_id,))
                    }
                    for t in src_terms:
                        if str(t.get("ta_version")) in existing_terms_versions:
                            continue
                        db.execute("""
                            INSERT INTO terms_acknowledgements (ta_booking_id, ta_version, ta_acknowledged, ta_acknowledged_at, ta_customer_name)
                            VALUES (?, ?, ?, ?, ?)
                        """, (dest_bk_id, t.get("ta_version"), t.get("ta_acknowledged") or 0, t.get("ta_acknowledged_at"), t.get("ta_customer_name")))
                        stats["terms_merged"] += 1

                    # Because payments/charges are only ever ADDED (never removed or
                    # replaced), the recomputed paid amount can never decrease - a
                    # stale 'Unpaid' import can never downgrade an already Paid/Partial
                    # invoice back down.
                    _sync_paid_from_payment_records(dest_bk_id, dest_inv_id)
                    repo._recalc_booking_totals(dest_bk_id)
                    stats["invoices_recalculated"] += 1
            except Exception as row_exc:
                stats["errors"].append(f"{sb['bk_customer_name']}: {row_exc}")

        repo.write_audit_log(actor, "MERGE_IMPORT", "bookings", 0, None, {
            "new_bookings": stats["new_bookings"], "matched_bookings": stats["matched_bookings"],
            "new_payments": stats["new_payments"], "new_charges": stats["new_charges"],
        })

    except Exception as exc:
        stats["errors"].append(str(exc))
    finally:
        try:
            db.execute("DETACH DATABASE src")
        except Exception:
            pass

    return stats
