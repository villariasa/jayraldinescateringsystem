# Manual Security Fix Guide — Jayraldine's Catering System

**Purpose:** This is a standalone, do-it-yourself reference. If you're offline or out of AI credits, you (or any developer) can apply every fix below with a plain text editor — no AI assistance required. Each entry gives the exact file, exact lines, the vulnerable code as it exists today, and the replacement code.

**Snapshot taken:** 2026-09-24. Companion to `SECURITY_PLAN.md` (phased overview) — this file is the line-by-line "how".

Each file below is fingerprinted (last-modified time + first 16 chars of its SHA-256). **Before trusting the line numbers in this doc, re-run this check** — if the hash differs, the file has changed since this was written and the line numbers below may be off (search for the quoted code snippet instead):

```bash
sha256sum "<path>" | cut -c1-16
```

| File | Last modified (at snapshot time) | SHA-256 (first 16) |
|---|---|---|
| `Catering_Present/jayraldines_catering/utils/auth.py` | 2026-09-14 08:50:55 | `43000809eea8fdf6` |
| `Catering_Present/jayraldines_catering/utils/db_sync_server.py` | 2026-09-24 15:33:53 | `07186101060a60c4` |
| `Catering_Present/jayraldines_catering/utils/db_config.py` | 2026-09-14 08:50:55 | `3fb68232b348aeee` |
| `Catering_Present/jayraldines_catering/utils/db.py` | 2026-09-24 15:37:43 | `335c1ebab4c77c6a` |
| `Tablet_PWA/backend/app.py` | 2026-09-24 15:54:21 | `09dae7bf82bbc83e` |
| `Catering/jayraldines_catering/utils/db.py` (legacy copy) | 2026-08-12 13:57:52 | `27d171902edef5d7` |
| `docs/security/DATA_PRIVACY_RA10173_COMPLIANCE.md` | 2026-09-21 08:37:17 | `85185fc068940d37` |

---

## FIX 1 (CRITICAL) — Admin login backdoor

**File:** `Catering_Present/jayraldines_catering/utils/auth.py`
**Function:** `authenticate()`, around lines 270–281

**Current code (vulnerable):**
```python
    stored_hash = row.get("password_hash", "")
    if not verify_password(plain_password, stored_hash):
        # Graceful fallback for local admin account
        if row.get("username", "").lower() == "admin" and plain_password in ("admin", "admin123", "Admin123!", "Admin123"):
            new_hash = hash_password(plain_password)
            if db.get_engine_type() == "postgres":
                db.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, row["id"]))
            else:
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, row["id"]))
        else:
            _log_audit("USER_LOGIN_FAILED", f"Failed password attempt for user '{username}'")
            return None
```

**Why it's dangerous:** anyone who knows (or guesses) the app ships with this code can log in as `admin` using `"admin"`, `"admin123"`, `"Admin123!"`, or `"Admin123"` — regardless of what the real admin password is currently set to — because the check bypasses `verify_password()` entirely for those four strings.

**Replacement code:**
```python
    stored_hash = row.get("password_hash", "")
    if not verify_password(plain_password, stored_hash):
        _log_audit("USER_LOGIN_FAILED", f"Failed password attempt for user '{username}'")
        return None
```

**After applying:** the very first time you deploy this fix, immediately log in as `admin` with the *real* current password and, if you're not 100% sure nobody else knows it, change it via the app's "change password" / user management screen (uses `update_user_password()` in the same file, which is safe/unaffected).

---

## FIX 2 (CRITICAL — worst finding in the whole app) — Unauthenticated raw-SQL API on the LAN sync server

**File:** `Catering_Present/jayraldines_catering/utils/db_sync_server.py`
**Functions:** `_handle_db_write()` (~line 1225), `_handle_db_query()` (~line 1567), `_handle_db_callproc()` (~line 1263)
**Class:** `SyncServerHandler(BaseHTTPRequestHandler)` — listens on **port 8000**

**What's exposed today, unauthenticated, to anyone who can reach port 8000 (same LAN, same Wi-Fi/hotspot, or a forwarded port):**
- `POST /api/db/query` — runs **any `SELECT`/`WITH` statement you send it** and returns the rows as JSON. This includes `SELECT password_hash FROM users`, `SELECT smtp_pass FROM business_info`, every customer record, every payment record — the entire database, readable by anyone with no login.
- `POST /api/db/write` — runs **any `INSERT`/`UPDATE`/`DELETE`/`CREATE`/`DROP`/`ALTER` statement you send it**. This means an anonymous LAN client can run `DROP TABLE bookings`, wipe the `users` table, or silently alter payment records.
- `POST /api/db/callproc` — calls any stored procedure whose name starts with `sp_` (e.g. delete a booking, process a payment) with attacker-supplied parameters.

This is not "weak security" — it is a fully open, unauthenticated database console reachable over the network. This is the single most urgent item in the whole plan; fix this before anything else if the machine is ever on a network you don't fully control (a router, a shared office Wi-Fi, a mobile hotspot, a port-forwarded connection).

**Minimum viable fix (do this even if you can't build the full token system in Phase 1 of `SECURITY_PLAN.md` right away):**

1. Pick a long random shared secret and store it as an environment variable, e.g. on the server machine:
   ```
   set JAYRALDINES_SYNC_KEY=<a long random string, at least 32 characters>
   ```
   (On Linux/macOS: `export JAYRALDINES_SYNC_KEY=...`)

2. In `db_sync_server.py`, near the top of the file (after the imports, before the class), add:
   ```python
   import os

   def _check_api_key(handler) -> bool:
       """Returns True if the request carries the correct shared secret."""
       expected = os.environ.get("JAYRALDINES_SYNC_KEY")
       if not expected:
           # Fail CLOSED, not open: if the operator hasn't set a key yet,
           # refuse all sensitive requests rather than silently allowing them.
           return False
       provided = handler.headers.get("X-Sync-Key", "")
       import hmac
       return hmac.compare_digest(provided, expected)
   ```

3. At the very top of `_handle_db_write`, `_handle_db_query`, and `_handle_db_callproc` (i.e. the first line inside each `def`, before anything else runs), add:
   ```python
       if not _check_api_key(self):
           self._set_cors_headers(401)
           self.wfile.write(json.dumps({"error": "Unauthorized"}).encode("utf-8"))
           return
   ```

4. On every tablet/kiosk client that calls these endpoints, add the same header to every request:
   ```
   X-Sync-Key: <the same long random string>
   ```
   (Search the codebase for where these endpoints are called from — likely `utils/client_sync.py` on the desktop client side, and equivalent fetch/HTTP calls in `Tablet_PWA/frontend/` and the Android APK project — and add the header there.)

This is a stopgap (a shared static key is weaker than per-device tokens), but it turns "anyone on the network" into "only clients that know the secret" — a massive reduction in exposure for very little code. Phase 1 of `SECURITY_PLAN.md` describes the stronger per-device-token version to build when there's time.

**Also fix the wide-open CORS header in the same file**, in `_set_cors_headers()` (~line 194):

**Current:**
```python
        self.send_header("Access-Control-Allow-Origin", "*")
```
**Replace with** (restrict to the actual origins your kiosk/tablet frontend runs from — adjust the list to your real deployment):
```python
        allowed_origins = {"http://localhost:8085", "http://<your-server-lan-ip>:8085"}
        origin = self.headers.get("Origin", "")
        self.send_header("Access-Control-Allow-Origin", origin if origin in allowed_origins else "null")
```

---

## FIX 3 (CRITICAL) — Same unauthenticated-API problem in the Tablet PWA FastAPI backend

**File:** `Tablet_PWA/backend/app.py`
**Lines ~34-40** (CORS middleware setup)

**Current code (vulnerable):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Problem:** all 32 API routes in this file have no authentication dependency at all (confirmed by searching the file for `Depends`, `Authorization`, `Bearer` — none found). Combined with `allow_origins=["*"]`, this is the same class of problem as Fix 2: anyone who can reach this port can call every endpoint.

**Replacement code (restrict CORS, and add auth as described below):**
```python
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    # add your actual kiosk/tablet origins here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,   # only set True if you truly need cookies AND allow_origins is non-wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Add a FastAPI dependency for the shared key** (same env var approach as Fix 2, for consistency — put this near the top of `app.py`, after `app = FastAPI(...)`):
```python
from fastapi import Depends, Header

def require_sync_key(x_sync_key: str = Header(default="")):
    import os, hmac
    expected = os.environ.get("JAYRALDINES_SYNC_KEY", "")
    if not expected or not hmac.compare_digest(x_sync_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
```

Then add `dependencies=[Depends(require_sync_key)]` to each `@app.get(...)` / `@app.post(...)` / etc. decorator in this file (there are 32 — search for `@app.get(`, `@app.post(`, `@app.put(`, `@app.delete(` to find every one), for example:
```python
@app.get("/api/bookings", dependencies=[Depends(require_sync_key)])
```

---

## FIX 4 (HIGH) — Plaintext DB password on disk

**File:** `Catering_Present/jayraldines_catering/utils/db_config.py`
**Function:** `save_db_config()`, lines ~736–778 and `load_db_config()`, lines ~701–733

**Problem:** the PostgreSQL password is written as plain JSON to:
- Windows: `%LOCALAPPDATA%\JayraldinesCatering\db_config.json`
- Linux/macOS: `~/.jayraldines_catering/db_config.json`

Anyone with filesystem access to that machine (or a backup of it) can read the DB password directly.

**Recommended fix:** use the `keyring` package (add `keyring>=24.0.0` to `requirements.txt`) to store the password in the OS credential store (Windows Credential Manager / macOS Keychain / Linux Secret Service) instead of the JSON file. Sketch:

```python
import keyring

SERVICE_NAME = "JayraldinesCatering"

def save_db_config(engine="sqlite", host="localhost", port=8000, dbname="catering.db",
                    user="admin", password="", **extra):
    # store the password in the OS keychain, NOT in the JSON file
    keyring.set_password(SERVICE_NAME, user, password)

    cfg = {
        "engine": str(engine), "host": str(host), "port": int(port),
        "dbname": str(dbname), "user": str(user),
        # NOTE: no "password" key written to disk anymore
    }
    cfg.update(extra)
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    ...

def load_db_config():
    ...
    cfg = json.load(f)
    if "user" in cfg:
        password = keyring.get_password(SERVICE_NAME, cfg["user"]) or ""
        os.environ["DB_PASSWORD"] = password
    ...
```

This requires migrating any existing `db_config.json` that already has a plaintext password: on first run after upgrading, read the old plaintext password once, call `keyring.set_password(...)`, then rewrite the file without the `password` field.

---

## FIX 5 (HIGH) — Plaintext SMTP password in the database

**Table:** `business_info`, column `smtp_pass` (see `Catering_Present/jayraldines_catering/jayraldines_catering_clean.sql` or the equivalent live schema)
**Read/write code:** `get_smtp_config()` / `save_smtp_config()` in `Catering_Present/jayraldines_catering/utils/repository.py` (search for `smtp_pass` in that file)

**Problem:** the SMTP password is stored as plain text in the `business_info` table — anyone with `SELECT` access to the DB (including, until Fix 2/3 are applied, anonymous LAN clients) can read it.

**Recommended fix:** encrypt before storing, decrypt only when actually sending mail. Using `cryptography`'s `Fernet` (add `cryptography>=42.0.0` to requirements):

```python
from cryptography.fernet import Fernet
import keyring

def _get_fernet_key() -> bytes:
    key = keyring.get_password("JayraldinesCatering", "smtp_encryption_key")
    if not key:
        key = Fernet.generate_key().decode()
        keyring.set_password("JayraldinesCatering", "smtp_encryption_key", key)
    return key.encode()

def save_smtp_config(host, port, user, password):
    f = Fernet(_get_fernet_key())
    encrypted = f.encrypt(password.encode()).decode()
    db.execute(
        "UPDATE business_info SET smtp_host=%s, smtp_port=%s, smtp_user=%s, smtp_pass=%s",
        (host, port, user, encrypted),
    )

def get_smtp_config() -> dict:
    row = db.fetchone("SELECT smtp_host, smtp_port, smtp_user, smtp_pass FROM business_info LIMIT 1")
    if not row:
        return {"smtp_host": "", "smtp_port": 587, "smtp_user": "", "smtp_pass": ""}
    raw_pass = row["smtp_pass"] or ""
    plain_pass = ""
    if raw_pass:
        try:
            plain_pass = Fernet(_get_fernet_key()).decrypt(raw_pass.encode()).decode()
        except Exception:
            plain_pass = ""  # old plaintext value or corrupted — force re-entry in Settings
    return {
        "smtp_host": row["smtp_host"] or "",
        "smtp_port": int(row["smtp_port"] or 587),
        "smtp_user": row["smtp_user"] or "",
        "smtp_pass": plain_pass,
    }
```

Note the `except` branch: any password saved *before* this fix was plaintext, so decrypting it will fail — that's expected, and the fallback (`""`) just means the admin has to re-enter the SMTP password once in Settings after upgrading.

---

## FIX 6 (HIGH) — Hardcoded default DB password in the legacy app copy

**File:** `Catering/jayraldines_catering/utils/db.py`, lines 24–30

**Current code:**
```python
_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "port":     int(os.environ.get("DB_PORT", "5432")),
    "dbname":   os.environ.get("DB_NAME",     "jayraldines_catering"),
    "user":     os.environ.get("DB_USER",     "postgres"),
    "password": os.environ.get("DB_PASSWORD", "12345678"),
}
```

**Before fixing this, resolve the open question from `SECURITY_PLAN.md`:** is `Catering/` (the non-`_Present` copy) still used by anyone, or dead? The live/shipped app is `Catering_Present/jayraldines_catering` (confirmed via `run_desktop.bat`). If `Catering/` is confirmed dead, the simplest fix is deleting the directory rather than patching it. If it's still used:

**Replacement:**
```python
_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "port":     int(os.environ.get("DB_PORT", "5432")),
    "dbname":   os.environ.get("DB_NAME",     "jayraldines_catering"),
    "user":     os.environ.get("DB_USER",     "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}
```
(Empty default forces the app to fail loudly/prompt for a real password instead of silently connecting with a known weak one.)

---

## FIX 7 (MEDIUM) — No lockout on the main login

**File:** `Catering_Present/jayraldines_catering/utils/auth.py`, function `authenticate()`

The Owner-PIN dialog already implements a 3-attempt/60-second lockout (see `docs/security/OWNER_PIN_BYPASS_POLICIES.md`) — the main username/password login has no equivalent. Mirror that pattern here:

```python
import time

_failed_attempts: Dict[str, List[float]] = {}
_LOCKOUT_THRESHOLD = 3
_LOCKOUT_SECONDS = 60

def _is_locked_out(username: str) -> bool:
    now = time.time()
    attempts = [t for t in _failed_attempts.get(username.lower(), []) if now - t < _LOCKOUT_SECONDS]
    _failed_attempts[username.lower()] = attempts
    return len(attempts) >= _LOCKOUT_THRESHOLD

def _record_failed_attempt(username: str) -> None:
    _failed_attempts.setdefault(username.lower(), []).append(time.time())
```

Then at the very top of `authenticate()`, right after `username = username.strip()`:
```python
    if _is_locked_out(username):
        _log_audit("USER_LOGIN_LOCKED", f"Login blocked for '{username}' — too many failed attempts")
        return None
```
And in the `if not verify_password(...)` failure branch (after Fix 1 is applied), call `_record_failed_attempt(username)` before `return None`.

(Note: this in-memory dict resets on app restart, which is fine for a single-process desktop app; if multiple processes/workstations hit the same server-side auth, move this to a DB table instead.)

---

## Verification checklist (run after applying fixes, still fully manual/offline)

- **Fix 1:** try logging in as `admin` with `admin123` → must fail (unless that's genuinely the current real password).
- **Fix 2/3:** from another machine on the same network, run:
  ```bash
  curl -X POST http://<server-ip>:8000/api/db/query -H "Content-Type: application/json" -d '{"sql":"SELECT username, password_hash FROM users"}'
  ```
  Before the fix this returns real data. After the fix it must return a 401/Unauthorized with no data.
- **Fix 4:** open `db_config.json` in a text editor — there should be no `"password"` field with a readable value.
- **Fix 5:** query `SELECT smtp_pass FROM business_info` directly in `psql` — the value should be unreadable ciphertext, not a plain password string.
- **Fix 7:** attempt 4 rapid wrong-password logins — the 4th attempt should be rejected as locked out, not just "wrong password".
