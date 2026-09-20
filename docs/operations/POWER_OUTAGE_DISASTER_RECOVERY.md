# Power Outage & Disaster Recovery Runbook

## 1. Auto-Recovery Mechanism
- SQLite and PostgreSQL engines utilize Write-Ahead Logging (WAL).
- Upon power restoration, uncheckpointed WAL frames are automatically replayed into the main database page file.
- Pending network transactions return explicit retry codes to connected tablet kiosks.
