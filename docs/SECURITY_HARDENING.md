> **Note:** Reviewed & updated 2026-09-29 — Jayraldine's Catering System.

# Database Security Hardening

## Security Controls
- Superuser `postgres` access restricted to local installation.
- Application runs with scoped user `jayraldines_app` with schema-specific grants.
- Passwords hashed using salted PBKDF2/SHA-256.
