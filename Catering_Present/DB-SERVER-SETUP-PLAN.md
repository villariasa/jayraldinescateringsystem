# Centralized DB Server Setup Plan

Client requirement: one PC acts as the single PostgreSQL DB server. Other
laptops (PC app) and tablets (kiosk PWA) depend on that server's data over
LAN. Adds admin/user accounts with per-module access control, including
gating the Chef Jay AI assistant's actions by the same permissions.

This supersedes the earlier offline-first-only design for `Tablet_PWA`
(see its `README.md`) — tablets now require a live LAN connection to the
server instead of working fully offline and syncing later.

## 1. PC Installer — "Set up Server" vs "Connect to Server"

Add a new wizard step in `Catering_Present/jayraldines_catering/installer_wizard.py`
(after `_init_welcome_page`, before `_init_preferences_page`) with two paths:

### A. Set up Server
- Runs the existing local-Postgres init (`ExtractWorker._init_local_database`),
  but generates a random strong password instead of the hardcoded `12345678`
  default, and a DB user scoped to just this database.
- On the completed page (`_init_completed_page`), show a **credentials card**:
  host (this PC's LAN IP, auto-detected), port, DB name, user, password —
  with a **"Save as file"** button (writes a `.txt`/`.pdf` the owner can
  screenshot or print) and a copy-to-clipboard button. This is the one and
  only time the password is shown in full.
- Opens the firewall port for Postgres on the LAN profile (Windows:
  `netsh advfirewall`) so other machines can actually reach it — currently
  it's local-only.

### B. Connect to Server
- Skips local Postgres install entirely. Shows a form: server IP/host,
  port, DB name, user, password (the ones the owner saved from the "Set up
  Server" run on the server PC).
- Does a live test-connection before letting the wizard proceed (reuse
  `connect_postgres()` from `utils/db.py`).
- Writes those values into the app's env/config so every launch uses
  `DB_ENGINE=postgres` pointed at the remote host — no local DB, no local
  install step at all.

Both paths end up with the same app, same code — only the config differs.
This matches how `utils/db.py` already resolves `DB_ENGINE`/`DB_HOST`/etc.,
so no new DB layer is needed, just the installer UI and credential
generation/display.

## 2. Tablet — thin client of the central DB

Reverses the earlier offline-first recommendation, per client direction:
tablets go from "offline-first, sync later" to "LAN-only, live against the
server." Real tradeoff worth remembering: the tablet can no longer take
orders if the Wi-Fi/server is down.

- Tablet setup screen (first run) asks for the same server credentials
  (host/port/db/user/password) the owner saved from installer step A —
  same test-connection flow as the PC "Connect to Server" path.
- `Tablet_PWA` stops using its local SQLite (`backend/db.py` /
  sql.js-in-browser) as the source of truth for menus, packages, and
  images — those now come live from the central DB. The
  `Tablet_PWA/backend` FastAPI skeleton (currently unused per its README)
  becomes the right place for this: it proxies the tablet's requests to
  the central Postgres using the saved credentials, so the browser
  frontend never talks to Postgres directly.
- Owner Settings on the tablet (Packages/Menu/Customers CRUD) stays — the
  user can still edit menu, packages, and images from the tablet — but
  writes go straight to the central DB instead of the local `.db` file.
  No more "Export .db → merge on PC."
- What stays **local to the tablet** (not server data): the image
  slideshow, and "recent bookings" meaning *orders taken on this specific
  tablet* — that's a local view filtered by device/session, not pulled
  from the server's full booking list.
- Tablet kiosk mode is explicitly **not** part of the new user/role system
  below — no login screen, no permission tiers, same as always.
- All of this requires tablets, laptops, and the server PC on the same
  LAN — no more roaming-with-no-connection use case for tablets.

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
