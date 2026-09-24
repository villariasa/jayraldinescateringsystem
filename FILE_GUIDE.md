# File Guide — Jayraldine's Catering System

**Purpose:** a map of the entire codebase so that when a client asks for an add-on, fix, or change, you know exactly which file(s) to open — without needing AI help to figure it out. Read this offline with any text editor.

**Snapshot taken:** 2026-09-24. Companion docs: `SECURITY_PLAN.md` / `SECURITY_FIXES_MANUAL.md` (security work), `docs/dev/MASTER_DOCUMENTATION_CATALOG.md` (feature-behavior specs, not code locations — see the `docs/` section at the bottom of this file).

## What this project actually is

Three cooperating pieces of software, plus one dead one:

1. **`Catering_Present/jayraldines_catering/`** — the real, live desktop app. PySide6 (Qt) + PostgreSQL/SQLite. This is what `run_desktop.bat` launches and what staff/owner actually use every day. **This is where ~90% of client requests will land.**
2. **`Tablet_PWA/`** — a companion web app (`backend/` = FastAPI + SQLite, `frontend/` = vanilla JS PWA) that runs on tablets/phones so customers or staff can self-serve bookings/orders on a kiosk. Talks to the desktop app over the LAN when needed, but is mostly offline-first on its own local browser database.
3. **`Tablet_Android_APK/`** — **not** a separate app. It's a thin Android WebView wrapper that bundles a copy of `Tablet_PWA/frontend/`. Any UI change must be made in `Tablet_PWA/frontend/` and then copied/rebuilt into `Tablet_Android_APK/app/src/main/assets/` — see that section below.
4. **`Catering/`** (no `_Present` suffix) — an **older, abandoned copy** of the desktop app (no `users` table, no real login). Not launched by any run script. Treat as dead weight; don't edit it for feature work. (It does have one real issue worth still knowing about — see `SECURITY_FIXES_MANUAL.md` FIX 6 — but otherwise ignore it.)

---

## Quick lookup — "the client wants X, where do I go?"

| Client request | Start here |
|---|---|
| Add/change a field on the booking form | `Catering_Present/jayraldines_catering/components/booking_modal.py` (the form UI) + `utils/repository.py` "Bookings" section (the data) |
| Change how invoices/payments/balances are calculated | `utils/repository.py` "Invoices / billing" section |
| Add a new report or chart | `ui/reports_page.py` (UI) + `utils/repository.py` "Dashboard KPIs / analytics" or "year-parameterized analytics" sections (data) |
| Change a PDF (receipt, invoice, calendar export, order slip) layout | `utils/exporter.py` (desktop) — and if it must also apply to the tablet kiosk's offline receipt, also `Tablet_PWA/backend/exporter.py` and `Tablet_PWA/frontend/js/exporter.js` |
| Add/change a menu item or catering package field | `ui/menu_page.py` (UI) + `utils/repository.py` "Menu items"/"Packages" sections + `utils/sqlite_schema.py` if it needs a new DB column |
| Change customer info fields | `ui/customers_page.py` + `utils/repository.py` "Customers" section |
| Change login, passwords, or staff roles/permissions | `utils/auth.py` |
| Change the sidebar, top bar, toasts, or any shared popup | `components/sidebar.py`, `components/topbar.py`, `components/toast.py`, `components/dialogs.py` (these are used app-wide — a change here affects many screens) |
| Change app color theme / accent color / dark-light mode | `utils/theme.py`, `utils/palette.py`, `utils/accent.py` |
| Change email sending or email wording | `utils/mailer.py` |
| Change SMS wording/provider | `utils/sms_sender.py` |
| Fix multi-PC / LAN sync issues (data not appearing on another workstation) | `utils/client_sync.py` (client side) + `utils/db_sync_server.py` (server side) |
| Add a new page/screen to the app | `ui/main_window.py` (register it in `_PAGE_MODULES`) + create a new file in `ui/` |
| Change the "Chef Jay" AI assistant's answers/behavior | `utils/ai_client.py` |
| Change import/export of Excel/CSV files | `utils/importer.py` / `utils/exporter.py` (desktop), `Tablet_PWA/backend/importer.py` / `exporter.py` (kiosk) |
| Change the kitchen order board (Queued/Preparing/Ready/etc.) | `ui/kitchen_page.py` |
| Change inventory/stock tracking | `ui/inventory_page.py` + `utils/repository.py` "Inventory" section |
| Change expense tracking / categories | `ui/expenses_page.py` + `utils/repository.py` "Expenses" section |
| Change cash flow ledger (accounts, deposits/withdrawals) | `ui/cash_flow_page.py` + `utils/repository.py` "Cash flow management" section |
| Change the booking calendar view / capacity rules | `ui/calendar_page.py` + `utils/repository.py` "Calendar" section |
| Change any Settings-screen card (business info, SMTP, backup/restore, user management, data purge, etc.) | `ui/settings_page.py` (it's one big file covering all settings cards) |
| Change the tablet/kiosk booking wizard (what customers see on the tablet) | `Tablet_PWA/frontend/js/wizard.js` |
| Change what the kiosk app looks like when installed as a PWA (icon, name, offline caching) | `Tablet_PWA/frontend/manifest.json` + `service-worker.js` |
| Change the Android kiosk app's native behavior (camera, file saving, fullscreen kiosk mode) | `Tablet_Android_APK/app/src/main/java/com/jayraldines/cateringsystem/MainActivity.java` |
| Add a brand-new database field/table anywhere | Needs 2–3 files together: `utils/sqlite_schema.py` (schema) + `utils/repository.py` (read/write functions) + whichever `ui/` page shows it |

---

## 1. Desktop app — `Catering_Present/jayraldines_catering/ui/` (the 16 screens)

| File | Purpose (plain English) | Main class(es) | Typical client-requested changes that land here | Key dependencies |
|---|---|---|---|---|
| `ai_page.py` (477 ln) | "Ask AI" assistant screen — staff type questions, get answers + auto-charts. | `AIPage` | Add/change suggested questions; change daily briefing; tweak AI charts. | `utils.ai_client`, `components.mascot` |
| `billing_page.py` (2138 ln) | Billing/Invoices — list, record payments, verify, edit totals, print/email receipts, export. | `BillingPage`, `RecordPaymentDialog`, `EditBillingDialog` | Invoice card fields/layout; payment/downpayment logic; new filter/KPI; receipt content; balance rules. | `utils.repository`, `utils.exporter`, `components.dialogs` |
| `booking_page.py` (3749 ln) | Orders & Bookings — the core booking workflow: pending/confirmed tabs, approve/decline, charges, menu selection, bulk entry, confirmation emails, order slips. | `BookingPage`, `AdditionalChargesDialog`, `MultiMenuSelectionDialog` | Add a booking field; approval/decline workflow; surcharge/discount handling; bulk-entry columns; filters; order-slip/email content. | `utils.repository`, `components.booking_modal`, `components.filter_popover` |
| `calendar_page.py` (1074 ln) | Booking calendar — month grid, day panel, manual schedule editing. | `CalendarPage`, `DayCell`, `ManageScheduleDialog` | Daily capacity threshold/colors; manual entry fields; import/export template. | `utils.repository`, `components.booking_modal` |
| `cash_flow_page.py` (1003 ln) | Cash flow ledger — deposits/withdrawals across named accounts with running balance. | `CashFlowPage`, `TransactionModal` | Add/remove an account; transaction fields; running-balance logic; export format. | `utils.repository` |
| `customers_page.py` (2377 ln) | Customer directory — add/edit/bulk-add, address search, read-only ledger. | `CustomersPage`, `AddCustomerDialog`, `CustomerLedgerDialog` | Customer form field; phone/address formatting; ledger display; filters. | `utils.repository`, `components.address_search` |
| `dashboard_page.py` (1950 ln) | Landing/home screen — welcome slideshow, KPI tiles, revenue chart, capacity gauge, recent activity. | `DashboardPage`, `KPICard` | Add/remove a KPI tile; revenue chart; recent-activity type; export fields. | `utils.repository`, `utils.exporter` |
| `expenses_page.py` (1132 ln) | Expenses — record/list/filter by category, KPI summary. | `ExpensesPage` | Add/remove category; KPI calculations; filters; import format. | `utils.repository` |
| `inventory_page.py` (569 ln) | Inventory/stock — levels, restock/use adjustments, low-stock alerts. *(Not currently wired into main nav — see note below.)* | `InventoryPage`, `AddInventoryDialog` | Unit of measure; item fields; low-stock threshold. | `utils.repository` |
| `kitchen_page.py` (746 ln) | Kitchen ops board — kanban columns for order prep status + per-order task checklists. | `KitchenPage` | Add/rename status column; transition rules; task field; card layout. | `utils.repository` |
| `main_window.py` (1003 ln) | **The app shell/router** — sidebar/topbar host, lazily loads each page, nav, auto-lock, notification polling, theme switching, cross-page refresh signals. | `MainWindow` | Add a page to nav (`_PAGE_MODULES`); idle-lock timeout; notification behavior; which pages auto-refresh on which events. | imports every `ui.*_page` lazily |
| `menu_page.py` (3502 ln) | Menu & Packages — dishes tab + packages tab (per-pax pricing, min pax, selection-bucket limits). | `MenuPage`, `PackageDialog`, `PackageItemsPickerDialog` | Dish/package field; pricing/selection-bucket rules; image upload; bulk-entry columns; CSV/Excel import/export. | `utils.repository`, `utils.menu_store` |
| `reports_page.py` (2534 ln) | Reports & Analytics — KPI cards + 7 charts, sales-evaluation table, paginated record lists, export. | `ReportsPage` + several chart classes | Add/modify a chart; report calculations; sales-target logic; export fields. | `utils.repository`, `utils.exporter`, optional `QtCharts` |
| `settings_page.py` (3318 ln) | **All settings in one file**: user mgmt, DB server status/backup/restore, session security, business info/sales targets, booking policy, import/export, occasions/menu categories CRUD, SMTP config, theme, audit log, diagnostics, data purge. | `SettingsPage` | Add a settings card/field; permission gating; theme palettes; SMTP fields; backup/restore; audit log content. | `utils.auth`, `utils.db_config`, `components.user_management_panel` |
| `test_report.py` (427 ln) | Standalone design mockup of Reports page with hardcoded sample data. **Not wired to the real app.** | `ReportsPage` (unrelated local class) | Only relevant for previewing Reports page visual styling before applying to the real file. | none (self-contained) |
| `__init__.py` | Package marker only. | — | n/a | — |

**Structural note:** `main_window.py` lazily loads pages via a `_PAGE_MODULES` registry — `inventory_page.py` and `test_report.py` are **not** in that registry, meaning Inventory is currently orphaned from navigation and the test report file is dev-only. If a client asks "where's the inventory screen," check whether it's actually reachable in the running app before assuming it just needs a data fix.

All "list" pages (billing, booking, customers, calendar, cash_flow, expenses, menu, kitchen) share the same hand-duplicated pattern: async load via `utils/data_loader.py`, batched card rendering, `reload()`/`_mark_dirty()`. A "make loading faster" request often needs the same fix repeated across several files, since it's not factored into a shared base class.

---

## 2. Desktop app — `Catering_Present/jayraldines_catering/utils/` (the backend/support layer)

| File | Responsibility | Typical client-requested changes that land here | Size |
|---|---|---|---|
| `repository.py` | **The data-access layer** — almost every business read/write goes through here, on top of `db.py`. See feature-area breakdown below. | Almost any "add/change a business field, add a report, add a record type" request starts here. | 6067 ln |
| `db.py` | Raw DB engine: SQLite (primary) / PostgreSQL (fallback), SQL execution, stored-procedure emulation, transactions, device session tracking. | New stored-procedure-style DB op; SQL bug; DB engine behavior — usually edit `repository.py` instead. | 2647 ln |
| `db_sync_server.py` | Built-in LAN HTTP sync server (port 8000) tablets/clients talk to. | New sync API endpoint; kiosk can't sync a new entity type. **(See `SECURITY_FIXES_MANUAL.md` FIX 2 — this file has an open security issue.)** | 2254 ln |
| `ai_client.py` | Offline NL "Chef Jay AI" assistant — parses questions, computes answers, returns charts, executes confirmed actions. | Teach AI to answer X; add AI action/report; AI gives wrong numbers. | 3934 ln |
| `exporter.py` | All PDF/Excel/CSV export: reports, receipts, agreements, kitchen slips, calendars, cash-flow ledger. | Add a report/export; change PDF/Excel layout; add a receipt/invoice field. | 2978 ln |
| `importer.py` | CSV/Excel import: entity detection, header mapping, validation, batch insert, sample templates, full DB merge. | Support new entity/column on import; fix import validation bug. | 2095 ln |
| `client_sync.py` | Client-workstation proxy: forwards DB reads/writes to the server's Sync Hub over HTTP, with local SQLite cache fallback. | Fix multi-PC sync issues; client shows stale data. | 707 ln |
| `auth.py` | Authentication + RBAC: password hashing, login, user CRUD, permissions, session bootstrap, audit logging. | New role/permission module; password rules; staff account field. **(See `SECURITY_FIXES_MANUAL.md` FIX 1 — open security issue.)** | 661 ln |
| `reminder_manager.py` | AI assistant's in-memory alarm/reminder manager with NL time parsing. | AI reminder parsing wrong; new reminder phrasing. | 621 ln |
| `palette.py` | Library of color theme presets. | Add a new color theme option. | 675 ln |
| `sqlite_schema.py` | Full SQLite schema (tables/views/indexes/seed data) + migration/repair logic run on startup. | Add a new DB table/column (SQLite side). | 1017 ln |
| `sqlite_to_postgres.py` | Migrates a local SQLite station DB into central PostgreSQL. | Fix data migration to central server. | 400 ln |
| `db_config.py` | Reads/writes DB connection config, generates credentials, tests connections, configures Windows firewall for LAN server mode. | Server connection settings UI; LAN/firewall connectivity fixes. **(See `SECURITY_FIXES_MANUAL.md` FIX 4.)** | 388 ln |
| `db_server_service.py` | Detects if this machine is the DB server; starts/restarts Postgres + sync hub; owner-auth check for restricted actions. | Server-status indicator; "service can't restart on client machine." | 459 ln |
| `mailer.py` | SMTP email sending with HTML templates (receipts, booking confirmation/approval). | Change email sending/template wording or design. | 407 ln |
| `logger.py` | Rotating daily logs, global crash hook, diagnostic report export. | Add diagnostics; fix logging/crash reporting. | 443 ln |
| `theme.py` | Loads/compiles QSS stylesheets, applies theme app-wide. | Dark/light mode behavior; theme not applying to a new window. | 208 ln |
| `device_tracker.py` | Tracks this device's identity, sends heartbeats, reports active-user status. | Show which devices/terminals are online. | 201 ln |
| `notif_scheduler.py` | Background poller firing toast notifications for upcoming events. | New notification trigger/time window; reminder wording. | 118 ln |
| `sms_sender.py` | SMS via Semaphore API; phone normalization; booking confirmation text. | Change SMS provider/wording. | 127 ln |
| `data_loader.py` | Generic QThread wrapper for background DB work off the UI thread. | "Page freezes while loading data" — wrap the loader call here. | 118 ln |
| `data_cache.py` | Thread-safe in-memory cache with TTL, pre-loaded at login. | Speed up page load / cache a new dataset. | 98 ln |
| `accent.py` | Manages the app's accent/brand color. | Change accent color / add a color preset. | 111 ln |
| `icons.py` (+`icon_manager.py` shim) | Loads/recolors/caches SVG icons into QIcon objects. | Add a new icon / change icon color scheme. | 176 ln |
| `animations.py` | Reusable Qt fade/slide/dialog animation helpers. | Add/change a UI transition or dialog animation. | 188 ln |
| `input_activation_guard.py` | App-wide click-to-edit field behavior (fields start read-only). | Change click-to-edit field behavior app-wide. | 100 ln |
| `window_detector.py` | Debug tool tracking window/dialog lifecycle, detects "ghost" windows. | Debug-only; rarely a client feature request. | 262 ln |
| `menu_store.py` | Lightweight in-memory menu cache. | Rarely touched — menu CRUD goes through `repository.py`. | 68 ln |
| `session.py` | Singleton holding current logged-in actor's name (audit attribution). | Rarely touched directly. | 54 ln |
| `signals.py` | App-wide Qt signal bus for cross-page domain events. | Add a new cross-page event/notification hook. | 48 ln |
| `text_highlight.py` | HTML-escape + search-term highlighting. | Change search-result highlighting. | 49 ln |
| `searchable_combo.py` | Turns a `QComboBox` into type-to-filter search. | Add search-as-you-type to a dropdown. | 21 ln |
| `password_field.py` | Show/hide-password toggle for `QLineEdit`. | Rarely touched. | 27 ln |
| `paths.py` | Resolves bundled resource paths (source vs. PyInstaller build). | Fix missing resource/asset path after build. | 23 ln |

### `repository.py` feature-area map (6067 lines — the file you'll open most often)

| Feature area | What's there |
|---|---|
| Customers | list/add/update/delete, merge duplicates, lookups |
| Menu items | list/add/update/delete, paged/available views |
| Occasions | CRUD for event-occasion tags |
| Menu categories | CRUD + reordering |
| Packages | list/add/update/delete, package items, selection-bucket quotas |
| Bookings | list/paged/detail, create/update/delete, status updates, date-capacity check |
| Invoices / billing | paged/search/summary, auto-create, pay, update, delete, payment ledger |
| Additional charges | add/delete charges, recalculates booking totals |
| Kitchen orders | list, create, update status, mark done, sync from bookings |
| Notifications | push, unread list, dismiss, alert candidates |
| Dashboard KPIs / analytics | KPIs, upcoming events, monthly income, top items, activity feed |
| Business info / settings | business policy, capacity policy, business info, SMTP config |
| Expenses | list/paged/summary, add/update/delete, top locations, profit summary |
| Customer loyalty & follow-ups | loyalty recalculation, follow-up CRUD, overdue/upcoming |
| Audit log | write + read audit log entries |
| Kitchen tasks | per-order task checklist CRUD |
| Calendar | month/date events, day summaries, save calendar day |
| Booking balance / downpayment | balance calc, downpayment invoice creation, customer ledger |
| Cebu address system | in-memory-cached address search/save/link |
| Communication logs | confirmation/receipt/follow-up send logging |
| Year-parameterized analytics | available years, monthly income/profit by year, weekly/yearly summary |
| Data reset & purge | counts + purge functions per entity, purge-all |
| Cash flow management | transactions CRUD, recalc balances, duplicate detection |
| Monthly sales targets | set/get targets, sales evaluation report |
| Down payments | summary, upcoming, confirm order, verify payment |
| Inventory | list/add/adjust-stock/delete |

---

## 3. Desktop app — `Catering_Present/jayraldines_catering/components/` (reusable dialogs/widgets)

Used **app-wide** (a change here affects many screens): `sidebar.py`, `topbar.py`, `toast.py`, `notifications_panel.py`, `loading_overlay.py`, `dialogs.py` (generic confirm/success/error popups), `import_dialog.py`, `export_dialog.py`, `badges.py`, `card.py`, `circular_spinner.py`, `theme_loading_overlay.py`, `global_ai_floating.py`, `unified_auth_welcome.py`, `login_dialog.py`.

| File | What it is | Typical client-requested changes here |
|---|---|---|
| `booking_modal.py` (2209 ln) | 4-step New/Edit Booking wizard (Customer→Event→Menu→Payment) | **The booking form** — layout/steps/pricing logic |
| `order_print_dialog.py` (1438 ln) | Printable order/kitchen slip generator | Printed order slip layout/branding |
| `global_ai_floating.py` (1013 ln) | Floating AI chat assistant widget | AI chat bubble UI/behavior app-wide |
| `import_dialog.py` (761 ln) | Data import wizard (bookings/customers/expenses/menu) | Import wizard flow/mapping UI |
| `user_management_panel.py` (728 ln) | Admin RBAC panel: accounts, permissions matrix, password resets | User/role management UI |
| `topbar.py` (691 ln) | App header: title, nav, search, clock, theme toggle, notifications | Top navigation bar/header layout |
| `mascot.py` (594 ln) | Animated chef mascot (hand-painted via QPainter) | Chef mascot look/animations |
| `login_dialog.py` (623 ln) | Login screen + server config + lock screen | Login/lock screen visuals |
| `unified_auth_welcome.py` (619 ln) | Login → spinner → dashboard transition | Login-to-dashboard transition experience |
| `search_dropdown.py` (524 ln) | Global fuzzy search results dropdown (topbar) | Global search UX/results styling |
| `confirm_booking_dialog.py` (677 ln) | Booking-approval modal w/ payment options | Deposit/payment presets when approving a booking |
| `db_connection_dialog.py` (491 ln) | DB connection settings modal | DB connection settings screen |
| `package_menu_dialog.py` (444 ln) | Dish selection/customization for a package during booking | Package dish selection during booking |
| `calendar_export_dialog.py` (448 ln) | Multi-month calendar PDF export wizard | Calendar PDF export options/layout |
| `cinematic_welcome.py` (430 ln) | Post-login "movie intro" animation | Post-login cinematic intro |
| `notifications_panel.py` (361 ln) | Notification bell popover | Notifications dropdown UI |
| `address_search.py` (334 ln) | Cebu address autocomplete | Address entry/autocomplete on booking forms |
| `sidebar.py` (413 ln) | Left nav sidebar | Sidebar nav items/collapse behavior |
| `connected_devices_panel.py` (287 ln) | DB server & connected-workstation monitor panel | Connected-devices/DB monitoring display (admin) |
| `splash.py` (267 ln) | App startup splash screen | Startup splash visuals |
| `customer_search.py` (265 ln) | Autocomplete customer picker | Customer lookup/autocomplete in forms |
| `filter_popover.py` (244 ln) | Anchored filter popover w/ chips | Filter UI on list pages |
| `standalone_loader.py` (220 ln) | Out-of-process loading overlay | Out-of-process loading spinner visuals |
| `export_dialog.py` (207 ln) | Excel/CSV export wizard | Data export options/format wizard |
| `toast.py` (197 ln) | Transient stacked toast notifications | Toast notification style/position/timing |
| `loading_overlay.py` (178 ln) | In-page non-blocking loading overlay | In-page loading spinner overlay |
| `color_picker_widget.py` (152 ln) | Event theme color picker | Event color themes / custom color picker |
| `theme_loading_overlay.py` (138 ln) | Overlay during theme recompile | Theme-switch loading animation |
| `owner_auth_dialog.py` (135 ln) | Owner-only auth gate for server maintenance | Owner-authorization gate for restricted actions |
| `circular_spinner.py` (107 ln) | Generic circular loading spinner | Generic spinner look |
| `dialogs.py` (442 ln) | Shared confirm/success/error/export-success dialogs | Generic confirmation/success/error popup look |
| `card.py` (54 ln) | Hover-reactive card frame | Hover/lift animation on cards |
| `badges.py` (45 ln) | Status pill badges | Status badge colors/shape |
| `charts.py` (131 ln) | Reusable QtCharts area/donut wrappers | Chart styling/colors on dashboard/reports |
| `search_dropdown.py` | (see above) | — |
| `__init__.py` | Package marker only | — |

---

## 4. Tablet kiosk backend — `Tablet_PWA/backend/` (FastAPI + SQLite)

**Architecture note:** the tablet frontend does *not* primarily call this backend for day-to-day data — it runs its own offline-first in-browser SQLite database (see section 5). This backend mainly serves the static frontend files and acts as an optional LAN "Central Server" for syncing/importing/exporting and image uploads.

| File | Responsibility | Typical client-requested changes |
|---|---|---|
| `app.py` (844 ln) | ~32 API routes; mounts the static frontend. Route groups: `/api/health`, `/api/terms`, `/api/customers`, `/api/addresses/search`, `/api/packages`, `/api/menu-items` (+`/grouped`), `/api/menu-categories`(+`/reorder`), `/api/orders`(+receipt PDF, archive), `/api/bookings/by-date`\|`by-month`, `/api/export/orders.xlsx`\|`database.db`, `/api/sync/*` (status/import/lan-status/lan-sync). | Add/change an endpoint; change request/response shape; CORS; static mounting; LAN sync-to-Postgres logic. **(Open security issue — see `SECURITY_FIXES_MANUAL.md` FIX 3.)** |
| `repository.py` (460 ln) | Business logic: customer/package/menu CRUD, atomic order creation, booking calendar queries, Cebu address search. | Booking-ref format; order-creation fields/validation; invoice/payment status logic; menu category ordering. |
| `schema.py` | Full SQLite schema + default seed data (packages/menu/Cebu address list) + idempotent migrations. | Add a DB column/table; change default seed packages/menu; add a Cebu city/barangay. |
| `exporter.py` (427 ln) | Receipt PDF (reportlab) + Orders Excel export (openpyxl). | Receipt PDF layout/branding/terms text; Excel export columns. |
| `importer.py` (301 ln) | Imports master data from a PC-exported `.db` or `.xlsx` template; generates that template. | Accepted import formats/columns; sample template layout; dedup/merge rules. |
| `terms.py` | Terms & Conditions text, versioned so old orders keep their original text. | Update T&C wording (must bump `CURRENT_TERMS_VERSION`, never edit old text in place). |
| `db.py` | Thin SQLite connection layer, one shared lock-guarded connection. | DB locking/concurrency strategy; DB file location; invoice-status derivation. |
| `run_server.py` | Packaged `.exe` entry point (uvicorn launcher). | Server startup banner/port; installer launch behavior. |
| `version.py` | Version stamp for the installer. | Bump version for a new installer build. |

---

## 5. Tablet kiosk frontend — `Tablet_PWA/frontend/` (vanilla JS PWA, no framework)

**Architecture note:** `api.js` is mostly a facade over a fully offline-first in-browser SQLite database (`sqlite.js` + `repository.js`, via sql.js/WASM) — not a thin REST client. The FastAPI backend above is used for optional LAN sync/image-upload, not the primary data path.

| File | Responsibility | Typical client-requested changes |
|---|---|---|
| `js/wizard.js` (2531 ln) | **The booking wizard** — Customer→Event→Package→Menu→Add-ons→Billing→Preview→Receipt steps, cart, calendar picker. | **"Change the booking wizard steps"** lands here. |
| `js/settings.js` (2664 ln) | Admin/Owner settings: bookings list/detail, package/menu/category management, LAN server config, import/export UI. | Admin/Settings screens; admin password handling; server IP/credential setup. |
| `js/app.js` (1973 ln) | Landing/dashboard, theme toggle, splash, quick modals, Terms gate before the wizard. | Landing/dashboard layout; pre-order content; quick-option tiles. |
| `js/api.js` (1331 ln) | Facade + LAN sync orchestration (auto-discover server, push/pull, image upload queue, heartbeat). | Sync/discovery behavior; offline-vs-online fallback; new central-server call. |
| `js/repository.js` (1015 ln) | Local business logic mirroring the backend's `repository.py`, on the in-browser DB. | Local order-creation logic; sync conflict merging; validation. |
| `js/sqlite.js` (750 ln) | The tablet's actual local database (sql.js/WASM wrapper). | New local table/column (must mirror `backend/schema.py`); sync-merge logic. |
| `js/exporter.js` (643 ln) | Client-side receipt PDF (jsPDF) + Excel export, offline. | In-app receipt/Excel layout (keep in sync with `backend/exporter.py`). |
| `js/views.js` (279 ln) | Reusable UI primitives: toasts, modals, status pills. | Modal/toast look-and-feel (used everywhere). |
| `js/state.js` | In-memory booking-wizard draft state. | Add/remove a field carried through the wizard. |
| `js/slider.js` | Landing-page hero image slider. | Hero slider images/timing. |
| `js/lottie-helper.js` | Wrapper for Lottie animations. | Which animation plays where. |
| `js/terms.js` | Local T&C rendering/acknowledgement (mirrors `backend/terms.py`). | Update in-app T&C text (keep in sync with backend). |
| `js/importer.js` (89 ln) | Client-side master-data import wrapper. | Accepted import formats/columns (client side). |
| `js/icons.js` | Inline SVG icon library. | Add/replace an icon. |
| `js/keyboard-scroll.js` (127 ln) | Auto-scrolls focused inputs above the on-screen keyboard. | Fix inputs hidden behind on-screen keyboard. |
| `js/receipt_logo_b64.js` | Base64 receipt logo image. | Swap the offline receipt logo. |
| `js/animations-data.js` (18,687 ln) | Raw vendored Lottie JSON data — not hand-written. | Replace/add a Lottie animation asset (usually regenerated). |
| `js/views/` | **Empty folder** — dead/placeholder, view logic actually lives in `views.js`/`wizard.js`/`settings.js`. | N/A |
| `index.html` | App shell; loads vendored libs (no CDN — fully offline after install). | Add a vendored library; splash markup. |
| `manifest.json` | PWA install manifest (name, icon, theme color, standalone display). | **"Change what the app looks like installed as a PWA"** — name/icon/theme color. |
| `service-worker.js` (90 ln) | Offline caching; `SHELL_FILES` list precaches every asset. | Same as above (offline caching) — **remember to add any new JS/asset file to `SHELL_FILES` and bump `CACHE_NAME`**, or it won't update on installed devices. |
| `css/styles.css` (5182 ln) | All visual styling. | Any visual/styling change. |
| `vendor/` | Third-party libraries (lottie, sql.js/WASM, jspdf, xlsx) — vendored, not npm-installed. | Rarely touched directly; replace the file to upgrade a library. |

---

## 6. Android kiosk app — `Tablet_Android_APK/`

**Not a native app** — a WebView wrapper bundling a copy of `Tablet_PWA/frontend/`. `app/src/main/assets/` is a byte-for-byte mirror of that frontend.

| File | Role |
|---|---|
| `app/src/main/java/com/jayraldines/cateringsystem/MainActivity.java` (247 ln) | The WebView Activity: fullscreen kiosk mode, camera/media permissions, loads bundled assets, injects an `AndroidNative` JS bridge (`isInstalledApp()`, `saveBase64File()` for saving PDFs/Excel to Downloads), handles file-chooser/camera and back-button. |
| `app/src/main/AndroidManifest.xml` | Declares the activity, permissions, `usesCleartextTraffic="true"` (LAN HTTP to Central Server), `FileProvider` for camera capture. |
| `app/src/main/assets/` | Mirror of `Tablet_PWA/frontend/` — **any UI change must be made in `Tablet_PWA/frontend/` and rebuilt/copied here**, not edited directly. |

`MainActivity.java` itself is only touched for native permissions, camera/file-chooser behavior, or the `AndroidNative` JS bridge — everything else is a frontend change (section 5).

---

## 7. Root-level scripts, build tooling & docs

| File/pattern | What it's for |
|---|---|
| `run_desktop.bat` | Launches the live desktop app (`Catering_Present/jayraldines_catering`). |
| `run_tablet.bat`, `START_SERVER_FOR_TABLET.bat`, `run_lan_sync_server.bat` | Launch the tablet kiosk server/companion pieces. |
| `run_installer_wizard.bat`, `build_apk.bat`/`.sh`, `create_apk_project.sh`, `build_tablet_installer.bat`/`.py`, `build_tablet_pwa_installer.bat` | Packaging/installer build scripts — desktop `.exe`, Android `.apk`, tablet PWA installer. |
| `RUN_ON_PC_SERVER_TO_SETUP_POSTGRES.bat`, `SETUP_POSTGRES_SERVER_AND_MIGRATE.ps1` | First-time PostgreSQL server setup / migration on the central server machine. |
| `ENABLE_SERVER_REMOTE_ACCESS.bat`, `enable_server_remote_access.ps1`, `open_firewall_ports.bat`, `DISABLE_FIREWALL_AND_ALLOW_ALL.bat`, `FIX_LAPTOP_HOTSPOT_NETWORK.bat` | Network/firewall configuration helpers for LAN server mode. **Read `SECURITY_PLAN.md` before running these on a shared/public network** — several of these widen exposure. |
| `run_tests.bat` | Runs the automated test suite (see `Catering_Present/jayraldines_catering/tests/`). |
| `LAUNCH_APP.vbs` | Windows shortcut launcher (silent-launches `run_desktop.bat` without a console window). |
| `autocommit.sh` | Dev convenience script — auto-commits changes (check before relying on it; not something a client-facing change ever touches). |
| `generate_docs_and_pdf.py`, `generate_ppt.py` | Generate the project proposal docs/slides from templates — academic/presentation artifacts, not app code. |
| `appveyor.yml`, `.github/workflows/` | CI configuration. |
| `ARCHITECTURE.md`, `DATABASE_SPEC.md`, `DATABASE_MIGRATION_GUIDE.md`, `DEVICE_MONITORING_SPEC.md`, `THEME_ENGINE_SPEC.md`, `TESTING_PLAN.md`, `RBAC_SECURITY_GUIDE.md`, `RELEASE_NOTES_v4.1.15.md`, `DEV_LOG.md` | High-level design/spec docs — read before making an architectural change, not code themselves. |
| `PROJECT_PROPOSAL_AND_PRESENTATION_GUIDE.*`, `PROJECT_PROPOSAL_PRESENTATION.pptx`, `SERVICE INFORMATION.docx`, `worksheets/` | Academic/business proposal documents — unrelated to the running app. |
| `SECURITY_PLAN.md`, `SECURITY_FIXES_MANUAL.md` | The security audit + line-by-line fix guide (see those files). |
| `FILE_GUIDE.md` | This file. |

### `docs/` — feature-behavior specifications (not a code map — this file is)

`docs/` holds ~40 short spec docs describing how specific features are *supposed* to behave, organized by area: `docs/api/`, `docs/architecture/`, `docs/billing/`, `docs/compliance/`, `docs/dashboard/`, `docs/database/`, `docs/dev/` (includes `MASTER_DOCUMENTATION_CATALOG.md`, an index of the more important ones), `docs/devlogs/` (26 dated session logs — historical, not current-state reference), `docs/inventory/`, `docs/kitchen/`, `docs/mobile/`, `docs/operations/`, `docs/packages/`, `docs/performance/`, `docs/reports/`, `docs/security/`, `docs/tablet/`, `docs/testing/`, `docs/ui/`. When a client request touches a documented behavior (e.g. downpayment validation rules, booking collision detection, ESC/POS printing), check the matching doc there for the *intended* rule before changing the code that implements it in the tables above.

---

## How to keep this guide useful

This snapshot will drift as the app changes. When you add a new file or repurpose an existing one for something different than described here, add/update its row — a stale map is worse than no map.
