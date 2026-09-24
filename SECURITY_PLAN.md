# Security Hardening Plan — Jayraldine's Catering System (Data Security Focus)

## Context

The app handles customer PII (names, phone numbers, addresses), payment/invoice records, and business financials across three surfaces: the **desktop app** (`Catering_Present/jayraldines_catering`, PySide6 + PostgreSQL — this is the live/shipped version, confirmed via `run_desktop.bat`), a **LAN sync server** (`utils/db_sync_server.py`, port 8000) that desktop uses to serve tablets/phones, and a **Tablet PWA/FastAPI backend** (`Tablet_PWA/backend/app.py`, port 8000/8085). There's also an older, parallel `Catering/` app copy that appears abandoned (no `users` table, no real auth) — confirm with the user it's dead weight before doing anything with it.

Direct code inspection surfaced concrete, exploitable gaps — this plan is prioritized by real risk found in the code, not a generic checklist.

## Findings (what's actually wrong today)

**Critical**
1. **Hardcoded admin-account backdoor.** `utils/auth.py:271-281` — if password verification fails for the `admin` user, the code silently accepts the login anyway when the entered password is `"admin"`, `"admin123"`, `"Admin123!"`, or `"Admin123"`, then re-hashes and overwrites the stored hash. This is a permanent skeleton key into the highest-privilege account, present in the shipped app.
2. **Unauthenticated LAN data API — including a raw SQL console.** `utils/db_sync_server.py` (port 8000) and `Tablet_PWA/backend/app.py` (FastAPI, port 8000/8085) expose booking, customer, and payment endpoints with **no auth check at all** — no token, no session, no API key. Worse: `db_sync_server.py`'s `POST /api/db/query` runs **any `SELECT`/`WITH` statement sent to it** (full DB read, including `users.password_hash` and `business_info.smtp_pass`), and `POST /api/db/write` runs **any `INSERT`/`UPDATE`/`DELETE`/`CREATE`/`DROP`/`ALTER` statement sent to it** (full DB write, including dropping tables). `db_sync_server.py` sets `Access-Control-Allow-Origin: *`; the FastAPI backend sets `allow_origins=["*"]` combined with `allow_credentials=True`. Anyone who can reach the LAN/hotspot (or a forwarded port) has an unauthenticated database console. **This is the single most urgent fix in this plan — see FIX 2 in `SECURITY_FIXES_MANUAL.md`.**

**High**
3. **Plaintext credential storage.** `utils/db_config.py` writes the PostgreSQL password unencrypted to `db_config.json` (`~/.jayraldines_catering/` or `%LOCALAPPDATA%\JayraldinesCatering\`). `business_info.smtp_pass` is stored in plaintext in the database itself. The legacy `Catering/utils/db.py` falls back to a hardcoded default DB password `"12345678"` if `DB_PASSWORD` isn't set.
4. **No brute-force protection on the main login.** Unlike the documented Owner-PIN dialog (3 attempts / 60s lockout per `docs/security/OWNER_PIN_BYPASS_POLICIES.md`), `authenticate()` in `utils/auth.py` has no attempt limiting or lockout.
5. **Network exposure tooling widens the attack surface.** `db_config.py`'s `open_all_kiosk_firewall_ports()` and `configure_network_profile_private()` open inbound firewall rules on ports 8000/8085 for "any" profile and auto-set the active network to Private — on a shared/public hotspot this directly exposes finding #2.

**Medium**
6. Kiosk/tablet devices have no identity or trust model — `db_sync_server.py` auto-registers any connecting device by IP/User-Agent with no verification, so device attribution in `device_sessions` is spoofable.
7. Audit logging (`_log_audit` in `auth.py`, `audit_logs` table) covers login/user-management events but not data reads, exports, or PDF receipt generation — no record of who viewed/exported customer PII.
8. `docs/security/DATA_PRIVACY_RA10173_COMPLIANCE.md` claims "salted and hashed" passwords (true for `Catering_Present`, false in spirit given finding #1) but is silent on encryption-at-rest for the DB/backups, a breach-notification procedure, and retention/purge automation.

## Plan (phased, ordered by risk)

### Phase 0 — Stop the bleeding (no schema changes, low risk, do first)
- Remove the hardcoded password bypass block in `utils/auth.py` (`authenticate()`), and force a password reset flow for the `admin` account instead of silently accepting known-weak passwords.
- Add a shared-secret/API-key (or short-lived signed token) check to every route in `db_sync_server.py` and `Tablet_PWA/backend/app.py`; reject requests without it before touching the DB.
- Lock down CORS: replace `allow_origins=["*"]` / `Access-Control-Allow-Origin: *` with an explicit allowlist of the kiosk origins actually in use, and drop `allow_credentials=True` unless it's genuinely needed with a non-wildcard origin (the current combo is meaningless/rejected by browsers anyway and signals a misconfiguration).
- Remove the hardcoded `"12345678"` DB password fallback in `Catering/utils/db.py` (or delete that legacy app copy entirely — confirm with user first, per "not touching files without asking").
- Rotate any DB/SMTP credentials that may have been exposed via the plaintext config/DB storage above.

### Phase 1 — Authentication & session hardening
- Add login rate limiting/lockout to `authenticate()` mirroring the existing Owner-PIN pattern (3 failed attempts → 60s lockout, logged to `audit_logs`) — reuse the same audit helper (`_log_audit`) already in `auth.py`.
- Introduce real kiosk/device authentication: issue each tablet a per-device token at pairing time (store hashed in `device_sessions` or a new table), and require it on every sync-server/FastAPI call instead of trusting IP + User-Agent.
- Enforce the existing `auto_lock_minutes` setting (`SessionManager.get_auto_lock_minutes`) at the UI layer if not already wired up — confirm current enforcement before adding new code.

### Phase 2 — Data-at-rest & secrets
- Encrypt the DB password in `db_config.json` (OS keychain via `keyring`, or DPAPI on Windows/`libsecret` on Linux) instead of plaintext JSON.
- Encrypt `business_info.smtp_pass` at the application layer (e.g., Fernet with a key from OS keychain) before storing, decrypt only in-memory when sending mail.
- Confirm whether PostgreSQL data-at-rest and backups are encrypted (disk-level or `pg_dump` output) — if backups are unencrypted files, encrypt them and control access to the backup directory.

### Phase 3 — Compliance & observability
- Extend `_log_audit` coverage to PII reads/exports (customer list export, receipt PDF generation, reports) — not just login/user-admin events — so RA 10173 access accounting is real.
- Update `docs/security/DATA_PRIVACY_RA10173_COMPLIANCE.md` to cover encryption-at-rest, backup handling, and a breach-notification procedure, so the doc matches what Phase 2 actually implements.
- Add automated dependency/vulnerability scanning (`pip-audit` or similar) to CI (`.github/workflows/`) given the app pulls `psycopg2`, `fastapi`, `PySide6`, etc.

## Verification
- Phase 0: manually attempt login to the `admin` account with each of the 4 backdoor passwords — must fail after the fix. Hit `db_sync_server.py`/FastAPI endpoints with `curl` and no auth header — must get 401/403.
- Phase 1: scripted rapid-fire login attempts — must lock out after 3 tries; confirm lockout is logged in `audit_logs`.
- Phase 2: inspect `db_config.json` and the `business_info` table directly — password/secret fields must not be human-readable.
- Phase 3: perform a customer export/receipt print and confirm a corresponding `audit_logs` row appears.

## Open question before implementation starts
Is the `Catering/` (non-`_Present`) directory dead/abandoned, or still used somewhere (e.g., referenced by a build script or another team)? This determines whether we patch its hardcoded DB password fallback or just delete it.
