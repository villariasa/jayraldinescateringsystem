# Jayraldine's Catering — Kiosk PWA

An installable, **fully offline** web app for the tablet the owner takes to
events. Built because the Android APK build (`Tablet/`) kept crashing on
launch (`UnsatisfiedLinkError` from an NDK/libc++ ABI mismatch in the
Qt-for-Android toolchain) — this version runs in the tablet's own Chrome
browser instead, so there's no native cross-compilation involved at all.

**`Tablet/` is left untouched as a reference** — this is a full parallel
rewrite of the same features, not a patch on the old app.

## How this actually works (read this first)

The tablet takes orders **completely standalone** — no PC, no Wi-Fi, no
server, no internet, at the event or anywhere else. Everything (database,
PDF receipts, Excel exports) runs *inside the browser itself*:

- **SQLite runs in the browser** via WebAssembly (`frontend/vendor/sql-wasm.*`,
  the `sql.js` project) — a real SQLite database, held in memory and
  persisted to the browser's IndexedDB after every change. Schema is a
  byte-for-byte match of the original `Tablet/` app's tables.
- **PDF receipts** are generated in-browser with `jsPDF`
  (`frontend/vendor/jspdf.umd.min.js`).
- **Excel import/export** is generated in-browser with `SheetJS`
  (`frontend/vendor/xlsx.full.min.js`).
- All three are vendored (local files, not a CDN) so the whole app works
  with **zero network access** after the one-time install.

Then, back home/office, the owner does exactly what the original `Tablet/`
app's design already supported: **Data Sync → Export Local Database (.db)**
downloads the tablet's real database file. That file is copied (USB cable,
email, cloud folder — whatever's easiest) to the existing PC app
(`Catering_Present/jayraldines_catering`) and imported via its **Settings →
Merge Backup File Into This Database** feature — unchanged, same as before.

There is no backend server in this design. If you see a `backend/` folder
in this project, see "About the backend/ folder" below — it was an earlier,
wrong assumption (a fixed PC/LAN-server model) that doesn't fit "the owner
goes around to events."

## Installing on the tablet

A PWA needs to be served over `http(s)` at least once to register (browsers
won't install straight from a `file://` path) — after that one-time visit,
it's cached and works fully offline forever.

**Easiest one-time setup options:**
1. Host `frontend/` as a free static site (GitHub Pages, Netlify, Cloudflare
   Pages, Vercel — pick one) and open that URL once on the tablet's Chrome.
2. Or, on any PC on the same Wi-Fi as the tablet (just for this one-time
   step): `cd frontend && python3 -m http.server 8000`, then open
   `http://<that-PC's-LAN-IP>:8000` on the tablet.

Either way, once loaded:
1. Chrome shows an "Install app" prompt (or use the menu → *Add to Home
   screen*).
2. Tap Install — it's now a home-screen icon that opens fullscreen, no
   browser address bar.
3. From this point on, **never needs network again** — orders, receipts,
   settings, everything works fully offline, indefinitely.
4. Optional: enable Android's built-in **Screen Pinning** (Settings →
   Security) on the installed app so a customer using it can't back out
   into the rest of the tablet.

## Getting orders into the PC app

1. On the tablet: Home → **Synced** card → **Export Local Database (.db)**.
   This downloads the actual SQLite file — same schema as the PC app's own
   database, by design.
2. Transfer that `.db` file to the PC (USB, email, cloud drive — your
   choice, no network dependency between the two apps).
3. On the PC app: Settings → **Merge Backup File Into This Database** →
   pick the file. Done.

The **Owner Settings → Data Sync** panel also has: Import Master Data
(pulls packages/menu FROM a PC-exported `.db`/`.xlsx`, the reverse
direction), Download Excel Menu Template, Export Orders as `.xlsx` (a
human-readable archive, separate from the raw `.db` merge file), and
Archive & Clear Orders (exports to Excel, then wipes the tablet's order
history while keeping customers/menu/packages).

## What's the same as the original Tablet app

Ported with matching behavior, not just matching UI:

- **Database schema** — byte-identical shared tables (`customers`,
  `bookings`, `invoices`, `payment_records`, `booking_additional_charges`,
  `booking_menu_items`, `packages`, `menu_items`, `package_items`,
  `terms_acknowledgements`, plus the built-in Cebu address hierarchy) —
  still `TB-`-prefixed booking refs, still mergeable into the PC app's
  database exactly like the original tablet's `.db` file always was.
- **Order wizard** — same 6 steps (Customer → Event & Package → Menu →
  Charges → Billing → Preview), same live cart sidebar, same
  price-per-pax ↔ base-total two-way sync, same hardcoded upsell catalog,
  same 50%-downpayment quick-fill.
- **Terms & Conditions** — same legal text, same version, same
  scroll-to-enable-checkbox gate before an order can start.
- **Owner Settings** — same three tabs (Packages / Menu / Customers), same
  CRUD.
- **Data Sync** — same actions: Import Master Data (.db/.xlsx), Download
  Excel Template, Export Orders (.xlsx), Export Database (.db), Archive &
  Clear Orders.
- **Receipts** — same layout/branding, generated with jsPDF instead of
  reportlab.

## What's different

- **No Android runtime-permission dance, no crash handler, no native
  storage-path resolution, no NDK/Qt/buildozer anywhere** — none of that
  exists in a browser context, so it's just gone (that whole class of bug
  is what this rewrite exists to avoid).
- **"Session/actor" (which staff member is using the kiosk)** was already
  an incomplete, unused feature in the original app — not carried forward
  further than the original's own state.
- **Post-event evaluation survey** — text/questions existed in the original
  but were never wired into any screen there either; kept in
  `frontend/js/terms.js` verbatim for parity, still unused here too.

## Project layout

```
frontend/                  The entire app — this is what gets installed on the tablet
  index.html, manifest.json, service-worker.js
  css/styles.css           Dark navy theme, same tokens as the original Tablet/ui/theme.py
  vendor/                  Vendored third-party libs (no CDN — must work fully offline)
    sql-wasm.js/.wasm      SQLite compiled to WebAssembly (sql.js project)
    jspdf.umd.min.js       Client-side PDF generation
    xlsx.full.min.js       Client-side Excel read/write (SheetJS)
  js/
    sqlite.js              The in-browser SQLite database: schema, seed data, IndexedDB persistence
    repository.js          Business logic (customers, packages, menu, orders, addresses)
    importer.js            Master-data import (.db/.xlsx) + template generation
    exporter.js            Receipt PDF + orders Excel archive generation
    terms.js                Terms & Conditions text/version
    api.js                  Thin facade the UI calls — wraps the modules above
    state.js                In-memory order-wizard draft state
    views.js                Shared modal/toast/escaping helpers
    wizard.js               The 6-step order wizard
    settings.js              Owner Settings modal (Packages/Menu/Customers CRUD)
    app.js                   Home screen, Terms modal, Recent Orders modal, Data Sync modal
```

## About the `backend/` folder

Everything under `backend/`, plus `run.sh`/`run.bat`, `build_installer.*`,
`installer_output/`, and `kiosk_server_installer.iss` were built for an
earlier (wrong) assumption: a fixed PC/LAN server that tablets connect to
over Wi-Fi. That doesn't fit a tablet that travels to events with the owner
— it would have meant needing a PC and a network connection at every event,
which defeats the purpose entirely.

**These files are no longer part of the real deployment.** They're left in
place for now rather than deleted, since some were hand-edited after being
generated. Let me know if you want them removed, or if there's actually a
separate future use case (e.g. a fixed-location second kiosk) where a
shared-backend model would make sense — that's a different, optional setup
from the tablet described above, not a requirement for it.
