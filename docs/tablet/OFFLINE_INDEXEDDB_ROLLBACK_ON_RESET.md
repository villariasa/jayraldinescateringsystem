# Offline IndexedDB Transaction Rollback on Kiosk Reset

## Atomicity:
If a guest abandons the booking wizard before Step 4, uncommitted state entries in `orders_draft` are purged immediately to preserve local device storage.
