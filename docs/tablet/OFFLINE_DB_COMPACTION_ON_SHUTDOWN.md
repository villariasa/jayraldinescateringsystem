# Offline Transaction Database Compaction on App Shutdown

## 1. Maintenance
On kiosk application clean exit, SQLite `VACUUM` and `PRAGMA optimize` execute automatically, minimizing file fragmentation and speeding up cold-boot load times.
