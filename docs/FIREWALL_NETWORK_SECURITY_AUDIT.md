# Local Port Ingress Audit & Firewall Hardening Guide

## 1. Open Ports Verification
- **Port 8000 (TCP)**: Restrict to LAN subnets (`192.168.0.0/16`, `10.0.0.0/8`).
- **Port 5432 (TCP)**: PostgreSQL listener bound strictly to private network interfaces.
- **Port 8085 (TCP)**: Internal event pub-sub streaming.

## 2. Inbound Rule Audit
All rules are assigned descriptive display names and logged in Windows Advanced Security Audit trails.
