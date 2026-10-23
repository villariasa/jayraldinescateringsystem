## Summary of Changes
<!-- Describe the problem and what changes were made in this PR -->

### Affected Subsystems
- [ ] Desktop Application (`Catering_Present/jayraldines_catering/`)
- [ ] Tablet Kiosk Frontend (`Tablet_PWA/frontend/`)
- [ ] Tablet Kiosk Backend (`Tablet_PWA/backend/`)
- [ ] Android APK Wrapper (`Tablet_Android_APK/`)
- [ ] LAN Sync & Networking (`utils/db_sync_server.py`, `utils/client_sync.py`)
- [ ] Database Schema / Migrations (`sqlite_schema.py`, PostgreSQL scripts)

---

## Pre-Review Verification Checklist
- [ ] Verified database queries against dual engines (PostgreSQL `%s` vs SQLite `?` placeholders)
- [ ] Changes to `Tablet_PWA/frontend/` are synchronized with `Tablet_Android_APK/app/src/main/assets/`
- [ ] Checked for uncommitted transactions or unhandled exceptions
- [ ] No hardcoded credentials, API keys, or raw SQL endpoints exposed

---

## GitHub Copilot Code Review Instructions
- Automatic review: If configured in repository rulesets, Copilot will review automatically upon opening or pushing commits.
- Manual trigger: Comment `@copilot review` on this PR to request an immediate review pass.
