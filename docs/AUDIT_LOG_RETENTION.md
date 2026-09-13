# Audit Trail Retention & Tamper Detection Specification

## 1. Retention Rules
- All user login sessions, billing modifications, order cancellations, and master overrides are retained indefinitely in `audit_logs`.
- Logs older than 365 days may be archived to compressed, read-only SQL dumps.

## 2. Cryptographic Integrity
Each audit log entry computes a SHA-256 hash chaining back to the previous entry's hash, forming an immutable audit ledger that exposes unauthorized database tampering.
