"""
utils/data_cache.py
-------------------
Thread-safe in-memory cache manager for Jayraldine's Catering System.
Enables active pre-loading of critical datasets during the login welcome screen,
allowing all page views (Customers, Bookings, Billing, Menu, Expenses, Cashflow)
to render instantaneously with zero network or database wait time.
"""

import time
import threading
from typing import Any, Optional


class _DataCacheManager:
    """Thread-safe in-memory storage with event-driven cache invalidation."""

    def __init__(self):
        self._lock = threading.RLock()
        self._cache: dict[str, tuple[Any, float]] = {}  # key -> (data, expire_at)
        self._listeners_attached = False

    def _attach_event_listeners(self):
        """Attaches cache invalidation callbacks to global application events."""
        if self._listeners_attached:
            return
        try:
            from utils.signals import app_events
            ev = app_events()
            ev.booking_saved.connect(lambda: self.invalidate("bookings", "dashboard", "dashboard_data", "calendar"))
            ev.booking_created.connect(lambda: self.invalidate("bookings", "dashboard", "dashboard_data", "calendar"))
            ev.booking_updated.connect(lambda: self.invalidate("bookings", "dashboard", "dashboard_data", "calendar"))
            ev.customer_saved.connect(lambda: self.invalidate("customers", "customers_loyalty"))
            ev.invoice_saved.connect(lambda: self.invalidate("invoices", "dashboard", "dashboard_data", "cash_flow"))
            ev.invoice_created.connect(lambda: self.invalidate("invoices", "dashboard", "dashboard_data", "cash_flow"))
            ev.payment_recorded.connect(lambda: self.invalidate("invoices", "dashboard", "dashboard_data", "cash_flow", "bookings"))
            ev.expense_saved.connect(lambda: self.invalidate("expenses", "cash_flow", "dashboard", "dashboard_data"))
            ev.cash_flow_saved.connect(lambda: self.invalidate("cash_flow", "dashboard", "dashboard_data"))
            ev.menu_saved.connect(lambda: self.invalidate("menu_items", "packages"))
            ev.data_changed.connect(self.clear)
            self._listeners_attached = True
        except Exception:
            # Signals might not yet be initialized in headless testing
            pass

    def set(self, key: str, value: Any, ttl_seconds: float = 600.0) -> None:
        """Stores a value in cache with a TTL (default 10 minutes)."""
        self._attach_event_listeners()
        expire_at = time.time() + ttl_seconds if ttl_seconds > 0 else float("inf")
        with self._lock:
            self._cache[key] = (value, expire_at)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a cached value if present and unexpired, otherwise returns default."""
        self._attach_event_listeners()
        with self._lock:
            if key not in self._cache:
                return default
            val, expire_at = self._cache[key]
            if time.time() > expire_at:
                del self._cache[key]
                return default
            return val

    def has(self, key: str) -> bool:
        """Checks if a valid, unexpired entry exists for key."""
        with self._lock:
            if key not in self._cache:
                return False
            _, expire_at = self._cache[key]
            if time.time() > expire_at:
                del self._cache[key]
                return False
            return True

    def invalidate(self, *keys: str) -> None:
        """Removes one or more keys from cache immediately."""
        with self._lock:
            for k in keys:
                self._cache.pop(k, None)

    def clear(self) -> None:
        """Clears all cached entries."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict:
        """Returns summary of current cache keys and entries."""
        with self._lock:
            now = time.time()
            return {
                k: {"valid": exp > now, "expires_in": max(0, int(exp - now))}
                for k, (_, exp) in self._cache.items()
            }


# Global singleton instance
DataCache = _DataCacheManager()
