# Database High Availability & Disaster Failover Architecture

## 1. Dual-Mode Topology
The system seamlessly operates in two configurations:
- **Centralized PostgreSQL (Primary)**: Ideal for large venues with 10+ concurrent cashier and tablet stations.
- **Embedded SQLite (WAL Mode)**: Zero-configuration local database that automatically activates if PostgreSQL is unavailable.

## 2. Replication Sync
Kiosks maintain local SQLite replicas, continuously synchronizing delta changes with the central database.
