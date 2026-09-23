"""In-memory cache of catering menu items, lazily hydrated from the database.

Menu items are held in the module-level _MENU_ITEMS list and populated on first
access via _sync_from_db(). The sync is best-effort: if the DB is unavailable it
silently leaves the (possibly empty) in-memory list in place so the UI still
works offline. Accessor functions trigger the sync before returning data.
"""
# Process-wide menu item cache and a flag marking whether it's been hydrated.
_MENU_ITEMS = []
_synced_from_db = False


def _sync_from_db():
    """Populate the in-memory menu cache from the DB once (no-op afterwards)."""
    global _synced_from_db
    # Only hydrate once per process; subsequent calls are cheap no-ops.
    if _synced_from_db:
        return
    try:
        import utils.db as db
        if not db.is_available():
            return  # DB not ready; retry on a later call (flag stays False)
        rows = db.fetchall(
            "SELECT mi_name AS name, mi_category::TEXT AS category, "
            "COALESCE(mi_package_tier::TEXT, 'Standard') AS package, "
            "COALESCE(mi_price, 0.0) AS price, COALESCE(mi_status::TEXT, 'Available') AS status "
            "FROM menu_items ORDER BY 2, 1"
        )
        if rows:
            # Replace the cache with DB rows, mapping columns to UI-facing keys.
            _MENU_ITEMS.clear()
            for r in rows:
                _MENU_ITEMS.append({
                    "item":     r["name"],
                    "category": r["category"],
                    "package":  r["package"],
                    "price":    float(r["price"]),
                    "status":   r["status"],
                })
        # Mark hydrated only after a successful fetch so failures can retry.
        _synced_from_db = True
    except Exception:
        pass  # never let a DB error break the UI; keep whatever we have


def get_available_items():
    """Return menu items that can currently be ordered (excludes out-of-stock)."""
    _sync_from_db()
    # Only sellable statuses; the extra != check guards against odd data.
    return [m for m in _MENU_ITEMS if m["status"] in ("Available", "Seasonal") and m["status"] != "Out of Stock"]


def add_item(item: dict):
    """Append an item dict to the in-memory menu cache."""
    _MENU_ITEMS.append(item)


def remove_item(index: int):
    """Remove the cached item at `index`, ignoring out-of-range indices."""
    if 0 <= index < len(_MENU_ITEMS):
        _MENU_ITEMS.pop(index)


def all_items():
    """Return a copy of all cached menu items (hydrating from DB if needed)."""
    _sync_from_db()
    # Return a shallow copy so callers can't mutate the internal cache list.
    return list(_MENU_ITEMS)
