# Offline SQLite Integrity Verification

Runs PRAGMA integrity_check on tablet database initialization.
Automatically rolls back corrupted cached journals to clean snapshot if an ungraceful battery shutdown occurs.
