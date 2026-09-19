# Tablet Kiosk Version Lifecycle & OTA Management

## 1. Version Numbering Scheme
The tablet application follows Semantic Versioning (`MAJOR.MINOR.PATCH`):
- **MAJOR**: Structural schema or protocol breaking change.
- **MINOR**: Feature addition (e.g., menu showcase, new payment method).
- **PATCH**: Bug fixes, performance optimizations, styling adjustments.

## 2. Over-The-Air (OTA) Asset Refresh
When the desktop sync server pushes a new database snapshot, the tablet checks `db_version` and refreshes local IndexedDB / SQLite tables in the background without requiring APK reinstallation.
