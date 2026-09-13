# Tablet Offline Storage Architecture Specification

## 1. Storage Abstraction Layer
Tablet clients support dual storage backends depending on deployment context:
- **Android APK**: Native SQLite storage managed via JavaScript-to-Java WebView bridge.
- **Browser PWA**: Browser-native IndexedDB managed via the `idb-keyval` wrapper layer.

## 2. Schema Topology
- `menu_packages`: Cached catering packages, dish items, and pricing structures.
- `pending_orders`: FIFO mutation queue of banquet bookings created offline.
- `cached_customers`: Client directory optimized for rapid phone and name lookups.
- `sync_state`: High-water mark timestamps indicating last successful synchronization.
