# Dual-Boot Workstation Failover Procedures

## 1. Operating Environment
When the primary Windows workstation undergoes scheduled maintenance or system updates, secondary Linux workstations can immediately assume server host responsibilities:
- Point tablet kiosks to the standby static LAN IP.
- Mount the latest SQLite snapshot from network storage (`~/.jayraldines_catering/data/catering.db`).
- Execute `./run.sh` to resume POS and reporting services.
