# Centralized DB Server Setup Plan

Client requirement: one PC acts as the single PostgreSQL DB server. Other
laptops (PC app) and tablets (kiosk PWA) depend on that server's data over
LAN. Adds admin/user accounts with per-module access control, including
gating the Chef Jay AI assistant's actions by the same permissions.

This supports a hybrid architecture: desktop PCs connect directly over LAN,
while the kiosk tablet operates in **offline-first mode** when off-site at
client venues and **auto-syncs with zero duplicates** when reconnected to the LAN.

## 1. PC Installer — "Set up Server" vs "Connect to Server"

Add a new wizard step in `Catering_Present/jayraldines_catering/installer_wizard.py`
(after `_init_welcome_page`, before `_init_preferences_page`) with two paths:

### A. Set up Server
- Auto-detects or silently installs PostgreSQL locally if missing.
- Runs the local-Postgres init (`ExtractWorker._init_local_database`),
  generating a random strong password for the `jayraldines_app` DB user,
  and provisions the default `admin` application account.
- On the completed page (`_init_completed_page`), shows a **credentials card**:
  host (this PC's LAN IP, auto-detected), port, DB name, DB user, DB password,
  and initial `admin` login credentials — with a **"Save as file"** button
  (writes `credentials.txt`) and a copy-to-clipboard button.
- Opens the firewall port for Postgres on the LAN profile (Windows:
  `netsh advfirewall`) so other machines can reach it.

### B. Connect to Server
- Skips local Postgres install entirely. Shows a form: server IP/host,
  port, DB name, user, password.
- Does a live test-connection before letting the wizard proceed (reusing
  `connect_postgres()` from `utils/db.py`).
- Writes those values into `db_config.json` so every launch connects
  to the central host.

## 2. Tablet — Offline-First Kiosk with Deduplicated LAN Sync

Per client requirement, the tablet kiosk **must have offline mode** because
the owner frequently takes the tablet off-site to venues for customer orders
without a LAN connection.

- **Offline Operation**: Works 100% standalone using in-browser WebAssembly
  SQLite (`sql.js`) persisted to IndexedDB. Kiosk ordering, menu browsing,
  packages, and PDF receipts function with zero network dependency.
- **LAN Connection Detection**: When the tablet connects to the venue/office
  Wi-Fi where the server PC resides, it detects the server via a heartbeat.
- **Smart Deduplicated Sync**:
  - Pushes pending local orders (`sync_status = 'pending'`) to PostgreSQL
    using unique identifiers (`booking_reference` with `ON CONFLICT DO NOTHING`)
    so duplicate entries are impossible even if sync runs multiple times.
  - Pulls latest menus, categories, and packages from the central database
    down to the tablet so menu updates made on the PC hub are reflected.
- **Owner Settings on Tablet**: Full CRUD for Packages & Menus stays available;
  edits sync to PostgreSQL when connected.

## 3. Users & Role-Based Access (net new)

No auth system exists in the codebase today — this is new.

- New `users` table on the central DB: username, password hash,
  role/permission set, created_by, timestamps. Admin account is the
  default/first user (full access, can't be permission-restricted).
- Admin can create additional users and assign access **per module**
  (e.g. Bookings, Customers, Reports, Expenses, Settings, AI Chef Jay
  actions) — maps onto the existing sidebar (`components/sidebar.py`)
  tabs.
- UI enforcement: sidebar renders only the tabs a user has access to; the
  page itself also checks permission before allowing an action (not just
  hiding the button) so a non-admin can't trigger something a hidden tab
  would have blocked, e.g. via keyboard shortcuts or the AI.
- Login screen added to the desktop app at launch; session holds the
  current user's permission set for the rest of the app to check.

## 4. Chef Jay — gated by the same permissions

`utils/ai_client.py` already separates *deciding* an action from *doing*
it — `answer_question()` returns an `action` dict, and only
`execute_action(action)` (called on Confirm) touches the database. That's
the choke point to use:

- Every `action` Chef Jay proposes gets tagged with the module/permission
  it requires (e.g. `add_customer` → "Customers" module).
- `execute_action()` checks the logged-in user's permission set before
  running; if they don't have it, Chef Jay replies with something like
  *"I can't add a customer — you don't have access to Customers. Ask an
  admin."* instead of showing a Confirm button at all.
- Read-only Q&A (revenue, bookings lookups, etc.) gets the same treatment
  where the underlying data itself is permission-scoped (e.g. a user
  without Reports access shouldn't get revenue answers either).

## Open items / next steps

- [ ] Installer: server/connect wizard step + credentials card
- [ ] `utils/db.py`: random password generation, firewall rule helper
- [ ] `Tablet_PWA/backend`: wire up as a proxy to central Postgres
- [ ] `Tablet_PWA/frontend`: setup screen for server credentials, drop
      local-SQLite-as-source-of-truth for menus/packages/images
- [ ] New `users` table + login screen + permission model
- [ ] Sidebar + page-level permission checks
- [ ] `utils/ai_client.py`: tag actions with required permission, enforce
      in `execute_action()`
