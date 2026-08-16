"""
Data Importer Engine — handles intelligent auto-mapping, file parsing (CSV & Excel),
field normalization, data validation preview, sample template generation, and
batch database insertion for Jayraldine's Catering System.
"""
import os
import re
import csv
import math
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional

import utils.repository as repo

# ─────────────────────────────────────────────────────────────────────────────
# ENTITY SCHEMAS & HEADER ALIASES
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_SCHEMAS = {
    "customers": {
        "title": "Customers",
        "fields": {
            "name": {"label": "Customer Name", "required": True},
            "contact": {"label": "Contact Number", "required": False},
            "email": {"label": "Email Address", "required": False},
            "address": {"label": "Address", "required": False},
            "notes": {"label": "Notes / History", "required": False},
        },
        "sample": [
            ["Customer Name", "Contact Number", "Email Address", "Address", "Notes"],
            ["Maria Santos", "09171234567", "maria@example.com", "Cebu City", "VIP Client"],
            ["Juan Dela Cruz", "09189876543", "juan@example.com", "Mandaue City", "Prefers Pork Lechon"],
        ]
    },
    "expenses": {
        "title": "Expenses",
        "fields": {
            "date": {"label": "Expense Date", "required": True},
            "category": {"label": "Category", "required": True},
            "description": {"label": "Description", "required": True},
            "amount": {"label": "Amount (₱)", "required": True},
        },
        "sample": [
            ["Expense Date", "Category", "Description", "Amount (₱)"],
            [datetime.now().strftime("%Y-%m-%d"), "Food Cost", "Fresh Pork & Spices", "15500.00"],
            [datetime.now().strftime("%Y-%m-%d"), "Transport", "Gas for Delivery Van", "2400.00"],
            [datetime.now().strftime("%Y-%m-%d"), "Labor", "Assistant Cook Daily Pay", "3500.00"],
        ]
    },
    "bookings": {
        "title": "Bookings & Orders",
        "fields": {
            "name": {"label": "Customer Name", "required": True},
            "contact": {"label": "Contact Number", "required": False},
            "date": {"label": "Event Date", "required": True},
            "time": {"label": "Event Time", "required": False},
            "venue": {"label": "Venue / Location", "required": False},
            "occasion": {"label": "Occasion", "required": False},
            "pax": {"label": "Guest Count (Pax)", "required": True},
            "total": {"label": "Total Amount (₱)", "required": True},
            "status": {"label": "Status", "required": False},
        },
        "sample": [
            ["Customer Name", "Contact Number", "Event Date", "Event Time", "Venue", "Occasion", "Guest Count (Pax)", "Total Amount (₱)", "Status"],
            ["Engr. Rodrigo Tan", "09178889900", datetime.now().strftime("%Y-%m-%d"), "6:00 PM", "Grand Ballroom Cebu", "Wedding", "150", "45000.00", "CONFIRMED"],
            ["Capt. Juanito Dela Cruz", "09182223344", datetime.now().strftime("%Y-%m-%d"), "12:00 PM", "Lahug Clubhouse", "Birthday", "80", "28000.00", "PENDING"],
        ]
    },
    "menu_items": {
        "title": "Menu Items & Packages",
        "fields": {
            "name": {"label": "Item / Package Name", "required": True},
            "category": {"label": "Category", "required": True},
            "price": {"label": "Price / Rate (₱)", "required": True},
            "description": {"label": "Description / Inclusions", "required": False},
        },
        "sample": [
            ["Item / Package Name", "Category", "Price / Rate (₱)", "Description / Inclusions"],
            ["Lechon Belly Package A", "Packages", "12500.00", "1 Whole Lechon Belly + 3 Side Dishes"],
            ["Special Pork Humba", "Main Dishes", "450.00", "Serves 8-10 pax"],
            ["Biko with Latik", "Desserts", "250.00", "1 Large Tray"],
        ]
    },
    "all_in_one": {
        "title": "All-in-One Master File (Bookings, Customers, Expenses & Menu)",
        "fields": {},
        "sample": [
            ["Customer Name", "Contact Number", "Event Date", "Venue", "Occasion", "Pax", "Total Amount", "Expense Date", "Expense Category", "Expense Description", "Expense Amount"],
            ["Maria Santos", "09171234567", datetime.now().strftime("%Y-%m-%d"), "Grand Ballroom", "Wedding", "150", "45000.00", datetime.now().strftime("%Y-%m-%d"), "Food Cost", "Fresh Pork Lechon", "15500.00"],
        ]
    }
}

HEADER_ALIASES = {
    "name": ["name", "customer", "client", "customer name", "client name", "full name", "item name", "package name", "title"],
    "contact": ["contact", "phone", "mobile", "cellphone", "contact number", "phone number", "tel", "telephone"],
    "email": ["email", "e-mail", "email address", "mail"],
    "address": ["address", "location", "city", "home address", "street"],
    "notes": ["notes", "history", "remarks", "memo", "details", "comments"],
    "date": ["date", "event date", "booking date", "expense date", "transaction date", "fecha"],
    "time": ["time", "event time", "schedule", "start time"],
    "category": ["category", "type", "expense type", "item category", "group"],
    "description": ["description", "details", "particulars", "memo", "notes", "inclusions", "summary"],
    "amount": ["amount", "cost", "total", "price", "subtotal", "grand total", "total amount", "fee", "cost (php)", "price (php)", "rate"],
    "total": ["total", "amount", "total amount", "cost", "price", "subtotal", "grand total", "fee"],
    "price": ["price", "rate", "cost", "unit price", "amount"],
    "venue": ["venue", "location", "place", "event location", "site", "address"],
    "occasion": ["occasion", "event", "event type", "celebration", "party", "theme"],
    "pax": ["pax", "guests", "guest count", "number of guests", "attendees", "headcount", "capacity"],
    "status": ["status", "state", "booking status", "order status"]
}


# ─────────────────────────────────────────────────────────────────────────────
# FILE PARSING (CSV & EXCEL)
# ─────────────────────────────────────────────────────────────────────────────

def parse_file(file_path: str) -> Tuple[List[str], List[Dict[str, str]], Optional[str]]:
    """Parse CSV or Excel file into headers and list of row dicts.
    Returns (headers, rows, error_message)."""
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
                # Detect delimiter
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
    except ImportError:
        # Fallback to pandas if installed
        try:
            import pandas as pd
            df = pd.read_excel(file_path).fillna("")
            headers = [str(c).strip() for c in df.columns]
            data_rows = []
            for _, row in df.iterrows():
                row_dict = {h: str(row[h]).strip() for h in headers}
                data_rows.append(row_dict)
            return headers, data_rows, None
        except Exception as e:
            return [], [], f"Excel library openpyxl/pandas not installed or file corrupt: {e}"
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

                # Match sheetname to entity
                sn_lower = sheetname.lower().strip()
                entity = "customers"
                if "expense" in sn_lower:
                    entity = "expenses"
                elif "booking" in sn_lower or "order" in sn_lower or "event" in sn_lower:
                    entity = "bookings"
                elif "menu" in sn_lower or "item" in sn_lower or "package" in sn_lower:
                    entity = "menu_items"

                result[entity] = (headers, data_rows)

            if result:
                return result, None
        except Exception:
            pass

    # Fallback: single sheet / CSV file auto-splitting
    headers, rows, err = parse_file(file_path)
    if err:
        return {}, err

    # Split single sheet by headers
    result = {}
    headers_lower = [h.lower() for h in headers]
    if any("expense" in h for h in headers_lower):
        result["expenses"] = (headers, rows)
    if any("booking" in h or "event" in h or "pax" in h for h in headers_lower):
        result["bookings"] = (headers, rows)
    if any("customer" in h or "client" in h for h in headers_lower) or "customers" not in result:
        result["customers"] = (headers, rows)

    return result, None


# ─────────────────────────────────────────────────────────────────────────────
# INTELLIGENT AUTO-MAPPING & NORMALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def auto_map_headers(headers: List[str], entity_type: str) -> Dict[str, str]:
    """Auto-detect which uploaded column header maps to system fields for entity_type.
    Returns mapping dict: {system_field_key: file_header_name_or_empty}."""
    schema = ENTITY_SCHEMAS.get(entity_type, {})
    fields = schema.get("fields", {})
    mapping = {}

    headers_clean = {h: re.sub(r"[^\w\s]", "", h.lower().strip()) for h in headers}

    for field_key in fields.keys():
        aliases = HEADER_ALIASES.get(field_key, [field_key])
        matched_header = ""
        # Exact match
        for h_orig, h_clean in headers_clean.items():
            if h_clean in aliases:
                matched_header = h_orig
                break
        # Partial substring match if no exact match
        if not matched_header:
            for h_orig, h_clean in headers_clean.items():
                if any(alias in h_clean for alias in aliases):
                    matched_header = h_orig
                    break

        mapping[field_key] = matched_header

    return mapping


def normalize_amount(raw: Any) -> float:
    """Clean currency string into float value."""
    if raw is None:
        return 0.0
    s = str(raw).strip()
    s = re.sub(r"[^\d.-]", "", s.replace(",", ""))
    try:
        return float(s)
    except ValueError:
        return 0.0


def normalize_date(raw: Any) -> str:
    """Normalize date string to standard format (MMM DD, YYYY)."""
    if not raw:
        return datetime.now().strftime("%b %d, %Y")

    s = str(raw).strip()
    # Try various date formats
    date_formats = [
        "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y",
        "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y", "%d %b %Y", "%d %B %Y"
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%b %d, %Y")
        except ValueError:
            continue

    # Return today if unparseable
    return datetime.now().strftime("%b %d, %Y")


def normalize_pax(raw: Any) -> int:
    """Clean pax string into positive integer."""
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
# VALIDATION & PREVIEW GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def validate_and_prepare_rows(
    data_rows: List[Dict[str, str]],
    mapping: Dict[str, str],
    entity_type: str
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Validate mapped rows and prepare sanitized dicts with status.
    Returns (prepared_rows, summary_counts).
    Each row dict contains:
      - "_row_index": int
      - "_status": "valid" | "warning" | "error"
      - "_issues": list of str
      - "_data": sanitized field data
    """
    schema = ENTITY_SCHEMAS.get(entity_type, {})
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

            if field_info["required"] and not raw_val:
                issues.append(f"Missing required field '{field_info['label']}'")
                status = "error"

            if field_key == "amount" or field_key == "total" or field_key == "price":
                val = normalize_amount(raw_val)
                if val <= 0 and field_info["required"]:
                    issues.append(f"Invalid amount '{raw_val}'")
                    status = "error"
                sanitized[field_key] = val
            elif field_key == "date":
                sanitized[field_key] = normalize_date(raw_val)
            elif field_key == "pax":
                sanitized[field_key] = normalize_pax(raw_val)
            else:
                sanitized[field_key] = raw_val

        # Warning checks
        if entity_type == "customers" and sanitized.get("contact"):
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
    """Insert valid rows into database.
    Returns (success_count, fail_count, list_of_error_messages)."""
    success_count = 0
    fail_count = 0
    errors = []

    for row_info in prepared_rows:
        if row_info["_status"] == "error" and skip_errors:
            fail_count += 1
            continue

        data = row_info["_data"]
        try:
            if entity_type == "customers":
                res = repo.add_customer(data)
                if res:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']}: Database insert failed.")
            elif entity_type == "expenses":
                res = repo.add_expense(data)
                if res:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']}: Database insert failed.")
            elif entity_type == "bookings":
                res = repo.create_booking(data)
                if res:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']}: Database insert failed.")
            elif entity_type == "menu_items":
                res = repo.add_menu_item(
                    data.get("name", "Item"),
                    data.get("category", "General"),
                    data.get("price", 0.0),
                    data.get("description", "")
                )
                if res:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"Row {row_info['_row_index']}: Database insert failed.")
        except Exception as e:
            fail_count += 1
            errors.append(f"Row {row_info['_row_index']}: {e}")

    # Emit app data change signal
    if success_count > 0:
        try:
            from utils.signals import app_events
            app_events().data_changed.emit()
            if entity_type == "expenses":
                app_events().expense_saved.emit()
            elif entity_type == "customers":
                app_events().customer_saved.emit()
            elif entity_type == "bookings":
                app_events().booking_saved.emit()
        except Exception:
            pass

    return success_count, fail_count, errors


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE CSV TEMPLATE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_sample_csv(entity_type: str, save_path: str) -> Optional[str]:
    """Generate sample CSV file with clean headers and example data.
    Returns error string if failed, or None on success."""
    schema = ENTITY_SCHEMAS.get(entity_type)
    if not schema:
        return "Unknown entity type."

    sample_rows = schema.get("sample", [])
    try:
        with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(sample_rows)
        return None
    except Exception as e:
        return f"Failed to save CSV template: {e}"
