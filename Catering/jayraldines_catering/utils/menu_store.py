_MENU_ITEMS = [
    {"item": "Lechon de Leche",  "category": "Main Course", "package": "Premium",  "price": 8500.0, "status": "Available"},
    {"item": "Kare-Kare",        "category": "Main Course", "package": "Standard", "price": 3500.0, "status": "Available"},
    {"item": "Pancit Malabon",   "category": "Noodles",     "package": "Standard", "price": 1800.0, "status": "Available"},
    {"item": "Buko Pandan",      "category": "Dessert",     "package": "Standard", "price":  950.0, "status": "Available"},
    {"item": "Leche Flan",       "category": "Dessert",     "package": "Premium",  "price": 1200.0, "status": "Available"},
    {"item": "Chicken Inasal",   "category": "Main Course", "package": "Budget",   "price": 2200.0, "status": "Available"},
    {"item": "Chopsuey",         "category": "Vegetables",  "package": "Budget",   "price": 1200.0, "status": "Available"},
    {"item": "Puto Bumbong",     "category": "Dessert",     "package": "Budget",   "price":  600.0, "status": "Seasonal"},
]

_synced_from_db = False


def _sync_from_db():
    global _synced_from_db
    if _synced_from_db:
        return
    try:
        import utils.db as db
        if not db.is_available():
            return
        rows = db.fetchall(
            "SELECT name, category::TEXT, package_tier::TEXT AS package, price, status::TEXT FROM menu_items ORDER BY category, name"
        )
        if rows:
            _MENU_ITEMS.clear()
            for r in rows:
                _MENU_ITEMS.append({
                    "item":     r["name"],
                    "category": r["category"],
                    "package":  r["package"],
                    "price":    float(r["price"]),
                    "status":   r["status"],
                })
        _synced_from_db = True
    except Exception:
        pass


def get_available_items():
    _sync_from_db()
    return [m for m in _MENU_ITEMS if m["status"] in ("Available", "Seasonal") and m["status"] != "Out of Stock"]


def add_item(item: dict):
    _MENU_ITEMS.append(item)


def remove_item(index: int):
    if 0 <= index < len(_MENU_ITEMS):
        _MENU_ITEMS.pop(index)


def all_items():
    _sync_from_db()
    return list(_MENU_ITEMS)
