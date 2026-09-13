# Owner Authentication Dialog Specification

## 1. Overview
The `OwnerAuthDialog` component enforces role-based access control (RBAC) boundaries for critical system settings, financial record resets, database server reconfigurations, and audit log purges.

## 2. Security Protocols
- **Elevation Verification**: Requires entry of the master owner PIN or master owner password.
- **Rate Limiting**: Implements progressive cooldown delays after 3 failed password attempts to mitigate brute-force attacks.
- **Temporary Token Grant**: Generates a cryptographically signed session token valid for 5 minutes of elevated access.
- **Audit Logging**: Every elevation request (successful or failed) is recorded in `audit_logs` with timestamp, terminal ID, and action attempted.
