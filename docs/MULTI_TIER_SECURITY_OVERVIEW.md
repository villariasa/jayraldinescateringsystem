# Multi-Tier Security Architecture & Threat Mitigation Guide

## 1. Security Layers
- **Transport Security**: Local LAN traffic protected by private subnet routing and firewalls.
- **Application Authentication**: Bcrypt work factor 12 password hashing with cryptographically secure random salts.
- **Role Isolation**: Strictly defined permissions for Admin, Cashier, Steward, and Owner.
- **Database Hardening**: Parameterized SQL queries preventing SQL injection across all modules.
