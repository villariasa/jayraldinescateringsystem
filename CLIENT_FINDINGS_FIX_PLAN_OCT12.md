# Client Findings — Detailed Fix Plan

**Date:** 2026-10-12
**Scope:** Tablet_PWA ↔ Desktop (Catering_Present) data mismatches, agreement/kitchen preview, receipt contact info, expense-category sync.
**Source of truth for tablet code:** `Tablet_PWA/frontend/js/` (the `Tablet_PWA/backend/dist/.../frontend/js/` and `Tablet_Android_APK/app/src/main/assets/js/` copies are built/vendored mirrors — apply the same edits there or re-run the build).

Each section lists: the client complaint, the confirmed root cause (with `file:line`), the fix, and how to verify.

---

## Finding 1 — Tablet booking data does NOT match the Desktop (event, add-ons, motif, package, amounts)

### Complaint
> "The event they selected on the tablet did not match on the desktop... the add-ons, the motif, the package amount, the set amount, the package they selected — did not match on the desktop."

### Root cause
The tablet writes **all** fields correctly to its local SQLite and sends the full raw booking row to the desktop. The desktop's LAN-sync ingestion (`perform_server_sync`) only reads a **subset** of those keys into its `INSERT INTO bookings`, so the missing columns silently fall back to schema DEFAULTS. Food-set detail rows are never transmitted at all.

**Tablet write side (correct):** `Tablet_PWA/frontend/js/wizard.js:2999-3035` builds the payload; `Tablet_PWA/frontend/js/repository.js:671-684` writes `bk_occasion`, `bk_num_sets`, `bk_base_total`, `bk_menu_type`, `bk_package_id`, `bk_color_theme` (= motif), `bk_pickup_time`, `bk_dropoff_time`.

**Desktop ingest side (lossy):** `Catering_Present/jayraldines_catering/utils/db_sync_server.py` → `perform_server_sync`, the `INSERT INTO bookings` at **lines 1918-1960**.

| Field | Tablet sends (key) | In desktop sync INSERT? | Result on desktop |
|---|---|---|---|
| Event (occasion) | `bk_occasion` | ✅ (read `:1883`, written `:1941`) | OK — but see note below |
| Package amount | `bk_base_total` | ✅ (read `:1886`, written `:1942`) | OK in storage |
| Add-ons | `additional_charges` | ✅ (`:2024-2044`) | OK **on first insert only** (inside `if not existing_b:` at `:1876`) — never updated on re-sync |
| **Motif** | `bk_color_theme` | ❌ absent | defaults to `'#2563EB'` → "Royal Blue" (`sqlite_schema.py:222`) |
| **Package type / order-type** | `bk_menu_type` | ❌ absent | defaults to `'package'`; `food_set`/`custom`/`food_tray` lost (`sqlite_schema.py:218`) |
| **Set count** | `bk_num_sets` | ❌ absent | defaults to `0` (`sqlite_schema.py:214`) |
| **Pickup/Dropoff time** | `bk_pickup_time`, `bk_dropoff_time` | ❌ absent | lost |
| **Set amounts (per-set price)** | `booking_sets` rows | ❌ never sent, never ingested | desktop reads `booking_sets.bs_unit_price` (`repository.py:1908-1922`) → shows zero |

Two separate defects feed the set-amount problem:
1. The tablet never attaches `booking_sets`/`booking_set_items` to the sync payload — `Tablet_PWA/frontend/js/repository.js:982-1001` (`getPendingSyncRecords` attaches only `menu_items`, `invoice`, `additional_charges`).
2. The desktop `perform_server_sync` has **no** `booking_sets` ingestion at all (grep returns nothing), even though desktop's own `create_booking` does insert them (`repository.py:2101-2103`).

**Event-name note:** the tablet rewrites the user's chosen occasion before storing — `Tablet_PWA/frontend/js/repository.js:655-663` maps e.g. "Other Special Event"/"General Event" → "Food Set"/"General Event". If the client reports the *event label itself* changing (not just blank), this rewrite — not the sync — is the cause. Confirm with the client which behavior they saw.

### Fix
1. **Desktop ingest — add the dropped columns.** In `db_sync_server.py` `perform_server_sync` INSERT (`:1918-1960`), read and write: `bk_menu_type`, `bk_num_sets`, `bk_color_theme`, `bk_pickup_time`, `bk_dropoff_time` (via `b.get("bk_...")`, mirroring the existing `bk_base_total` handling).
2. **Desktop ingest — update-on-resync.** Move the `additional_charges` ingestion (`:2024-2044`) and the new columns out of the `if not existing_b:` branch so re-syncing an edited booking updates instead of being ignored (delete+reinsert charges, or upsert).
3. **Food sets — transmit.** In `Tablet_PWA/frontend/js/repository.js:982-1001`, attach `booking_sets` + `booking_set_items` to each pending record (same pattern as `additional_charges`).
4. **Food sets — ingest.** In `perform_server_sync`, add a `booking_sets`/`booking_set_items` ingestion block keyed on the booking id (mirror desktop `create_booking` at `repository.py:2101-2103`).
5. Decide on the occasion rewrite (`repository.js:655-663`): keep the user's literal selection unless there is a documented reason to remap. If remapping must stay, store the original label too.

### Verify
Create a tablet booking with a non-default motif, order-type = food_set, a set count > 0, per-set prices, and add-ons → sync → open on desktop and confirm every field matches. Then edit it on tablet, re-sync, confirm the update propagates (not just the first insert).

---

## Finding 2 — Desktop Payment-tab package price shows a WRONG amount on tablet / card

### Complaint
> "The package they set price on the Payment tab on Booking — e.g. 45K — but on the tablet or card displays the wrong amount. The amounts did not match."

### Root cause
The amount entered on the Payment tab is written to **`bk_total_amount`**, but a second column **`bk_base_total`** (the "package/base" figure) is populated **inconsistently across the three writers**, and the tablet recomputes the amount from `price_per_pax × pax` instead of trusting the stored total.

**Payment-tab write side:** `Catering_Present/jayraldines_catering/components/booking_modal.py`
- Editable "Base Total (₱)" field `f_pay_package_total` — `:2285-2300`; auto-seeded as `pax × price_per_pax` and **re-seeded on every package (re)select, silently overwriting a manual entry** — `:1746-1749`, `:2716-2732`.
- On save (`:2744-2979`): emits dict key **`total`** = grand_total (`:2971`). **No `base_total` key is emitted** (`:2947-2978`).

**Persistence (the divergence):**
- `repository.py` `create_booking` (`:1976-2047`) passes only `data["total"]` → `p_total_amount`; **never passes a base total**.
- Postgres `sp_create_booking` (`jayraldines_catering.sql:450-461`) writes `total_amount` only → **`bk_base_total` stays at DEFAULT `0.00`** (`jayraldines_catering_clean.sql:137`). Same for `sp_update_booking` (`:496-515`).
- SQLite emulated `sp_create_booking` (`utils/db.py:1894,1901`) writes **both** columns but sets **both to the grand total** (add-ons included).
- Tablet writes `bk_base_total` = pre-add-on base.
- ⇒ `bk_base_total` means three different things depending on who created the row: Postgres `0.00`, SQLite = grand total, tablet = pre-add-on base.

**Read sides:**
- Desktop card reads `bk_total_amount` (`repository.py:1516/1551/1577`, rendered `booking_page.py:2424-2433`) — internally consistent, shows the entered 45,000.
- Tablet reads `bk_base_total` for base/detail (tablet `repository.py:320`) → `0.00` for desktop/Postgres bookings; and the tablet wizard recomputes `base_total = price_per_pax × pax`, `total = base + charges` (`order_wizard.py:719/722/783/809`), downpayment hard-coded `total × 0.50` (`:323,:1111`). If the desktop user manually overrode the Base Total (so `entered_total ≠ pax × price_per_pax`), or the tablet's local `pkg_price_per_pax` differs, the tablet's recomputed figure will not match the desktop's stored total.

### Fix
1. **Persist base total on Postgres.** Add `bk_base_total` to the column lists of `sp_create_booking` (`jayraldines_catering.sql:450-461`) and `sp_update_booking` (`:496-515`), and pass a real base from `create_booking`/`update_booking` (`repository.py:1976-2047`, `:2180+`). Have `booking_modal._save` emit an explicit `base_total` key (`:2947-2978`) distinct from the grand `total`.
2. **One definition of `bk_base_total` everywhere.** Pick a single semantic (recommend: *package subtotal before add-ons*) and make all three writers agree — Postgres SP, SQLite emulation (`db.py:1894/1901/2198`), and tablet. Fix the SQLite path so `bk_base_total` is the base, not the grand total.
3. **Tablet reads stored totals, does not recompute.** For bookings that already have a stored `bk_total_amount`/`bk_base_total`, the tablet display (`order_wizard.py`, tablet `repository.py:320`) must use the stored values rather than `price_per_pax × pax`. Only recompute when building a brand-new booking on the tablet.
4. **Stop the silent re-seed overwrite.** In `booking_modal.py:2716-2732`, do not overwrite a user-entered Base Total on package reselect (only seed when the field is empty/zero).
5. Align downpayment policy: tablet hard-codes 50% (`order_wizard.py:323,:1111`), desktop uses a policy percent default 30% (`booking_modal.py:2579-2584`). Pick one source of truth.

### Verify
On Postgres desktop, set Base Total = 45,000 with add-ons, save, re-open → base and total both correct in DB. Sync to tablet → tablet shows the same 45,000, not a recomputed figure. Repeat with a manual override that differs from `pax × rate`.

---

## Finding 3 — Tablet predefined packages & their menus don't match what was defined

### Complaint
> "The defined packages and inside those packages the client put menus — but on the tab it did not match what they set; also it's predefined as they say." (See `bullshit-where-are-the-menu-types.png`, `package-template.png`.)

### Desired behavior (clarified by client)
When a package is selected during booking, the menu-selection step (Step 3) must:
1. **Display only the menus that belong to that package** (the ones defined inside the package's buckets). Menus that are NOT part of the package must **not** be shown for selection at all.
2. **Show those package menus UNCHECKED.** They must **not** be auto-checked just because they are in the package. The user explicitly ticks the ones they actually want for this booking.

In short: the package defines the *available* menu set (a filtered list); the user's checkboxes define the *chosen* set. The two must be separate.

### Root cause
Packages↔menus are defined on the desktop and sync correctly into the tablet's local SQLite (`packages`, `package_items`, `package_buckets`; ingest at `sqlite.js:500/566/588` is correct). The defects are **display-side on the tablet**.

**Bug A (wrong behavior AND a dormant field-name bug).** `Tablet_PWA/frontend/js/wizard.js:1949`, in `selectPackage()`, the code *intends* to pre-load (auto-check) the package's menus into `d.menuSelections`:
```js
d.menuSelections = items.map((it) => ({
  menu_item_id: it.item_id,   // field bug: getPackageItems returns no `item_id`
```
Two problems:
- **Behavior is wrong per the client** — auto-checking package menus is NOT wanted. The package menus must render unchecked.
- **Field-name bug** — `getPackageItems()` (`repository.js:361-369`) returns `id`, `menu_item_id`, `name`, `item_name`, `category`, `price` — there is **no `item_id`**, so every preloaded selection gets `menu_item_id: undefined`; `selectedIds` (`wizard.js:2089`) becomes `Set{undefined}` and the grid check `selectedIds.has(it.menu_item_id)` (`wizard.js:2247`) is always false.

  > Note: these two cancel out today — the broken field name means nothing actually gets auto-checked, which happens to match the client's wanted "unchecked" outcome. Do **not** "fix" the field name to make auto-check work. Instead remove the auto-check preload entirely so `d.menuSelections` starts empty on package select.

**Missing filter (the core of the new requirement).** `renderStepMenu()` (`wizard.js:2069`) renders the full menu grid for the package's visible categories; it does **not** restrict the items to the package's own `package_items`. So non-package menus are offered for selection. Fix: when a package is selected, build the item list from that package's `package_items` (`api.getPackageItems(pkg.id)` / `repository.js:353`) and render only those; hide everything else. (For non-package / custom flows, keep showing the full menu as today.)

**Bug B (hardcoded inclusions).** `openPackageDetailsModal()` (`wizard.js:3123-3194`) renders a **hardcoded** generic "Buffet Catering Inclusions" list (`:3158-3178`) and never calls `api.getPackageItems(p.id)` / `api.getPackageBuckets(p.id)` ⇒ the real predefined menus and menu-types are absent from the details view (this is the "where are the menu types" screenshot). **Fix:** populate the modal from the actual package items + buckets.

**Contributing factor (menu-type grouping fragility).** In `renderStepMenu` (`wizard.js:2111-2120`), `visibleCategories` only shows categories mapped to a bucket via exact lowercase/trim equality of `pb_categories` vs live `mi_category`. Any category-name drift between definition and tablet data makes those menu types render empty. The grouping relies on string-equality of category names rather than the already-present `pi_bucket_id`. **Fix:** prefer grouping by `pi_bucket_id`, fall back to category-name match; normalize names.

### Fix summary
1. In `selectPackage()` (`wizard.js:1927-1963`): **remove the auto-check preload** at `:1946-1958` — leave `d.menuSelections` empty; still populate `d.package.buckets` (`:1963`) so the grid knows which buckets/items to show.
2. In `renderStepMenu()` (`wizard.js:2069`): when a package is active, **filter the rendered items to the package's `package_items`** and render them unchecked; non-package menus are not rendered. Keep the full-menu behavior only for non-package flows.
3. Group by `pi_bucket_id` (fallback to normalized category name) to fix empty menu-types.
4. Bug B: drive the package-details modal from real `package_items` + `package_buckets`.

### Data model (reference)
`packages` (`pkg_id`, `pkg_name`, `pkg_price_per_pax`, `pkg_min_pax`, `pkg_is_set`); `package_items` join (`pi_package_id`, `pi_menu_item_id`, `pi_item_name`, `pi_category`, `pi_bucket_id`); `package_buckets` = the "menu types" (`pb_package_id`, `pb_name`, `pb_limit`, `pb_categories` JSON, `pb_sort`). Schema: `Tablet_PWA/backend/schema.py:81-108`.

### Verify
Define a package with menus across several menu-types on desktop → sync → on tablet, select that package in booking Step 3: (a) **only** that package's menus appear — no other menus are offered; (b) they appear **unchecked**; ticking some and leaving others unticked records exactly the ticked ones; (c) menu-types (buckets) all render with their items (none empty); (d) "View Package Details & Inclusions" lists the real menus grouped by menu-type, not the generic hardcoded list.

---

## Finding 4 — Desktop booking agreement PREVIEW doesn't match the PDF (use a PDF-preview library)

### Complaint
> "The format on the PDF is well organized, but on the preview it's not the same. Please just use a PDF preview library so the agreement or kitchen is not hardcoded."

### Root cause
Stack is **PySide6 (Qt for Python)**. The PDF is generated with **ReportLab**; the on-screen preview is **hardcoded HTML in a `QTextBrowser`** that has drifted from the PDF.

- PDF generator: `Catering_Present/jayraldines_catering/utils/exporter.py:760` `export_receipt_pdf(...)` (canvas render at `:920`, header `:1054`). ReportLab guarded by `REPORTLAB_OK` (`:68-77`).
- Hardcoded preview: `components/order_print_dialog.py` — `QTextBrowser` at `:264`, `_generate_slip_html()` `:1277`, `_build_booking_agreement_page()` `:779` (drift source: header `:1060-1067`, terms `:1131`).
- **An exact path already exists**: `_render_exact_agreement_preview_html()` (`:1198`) renders the real `export_receipt_pdf` output via `PySide6.QtPdf.QPdfDocument` (`:1218/:1235`) rasterized to PNG (`:1251-1261`), and `_generate_slip_html()` prefers it (`:1284-1287`) — **but falls back to the hardcoded HTML when ReportLab/QtPdf are unavailable**.
- **The shipped build strips exactly those modules** — `package_installer.py:109` `--exclude-module reportlab`, `:120` `--exclude-module PySide6.QtPdf` (also QtWebEngine `:116-117`). So in the frozen app the exact-PDF preview can never run and it always falls back to the hardcoded HTML. **This is the drift the client sees.**
- Kitchen doc: a ReportLab generator exists (`exporter.py:1241` `export_order_slip_pdf`) but is **dead code (zero callers)**; kitchen preview + print both use the hand-built HTML only (`order_print_dialog.py:1176-1196`, `_build_slip_body` `:545`, etc.).

### Fix
1. **Stop excluding the preview deps** in `package_installer.py` — remove `--exclude-module reportlab` (`:109`) and `--exclude-module PySide6.QtPdf` (`:120`); add `PySide6.QtPdfWidgets` to the build. This alone makes the agreement preview match the PDF in the shipped app.
2. **Use a real PDF viewer widget.** Replace the PNG-into-`QTextBrowser` approach with `PySide6.QtPdfWidgets.QPdfView` bound to a `QPdfDocument` loaded from the ReportLab output — a true PDF preview, single rendering path for preview + export.
3. **Make kitchen match the same way.** Wire the dead `export_order_slip_pdf` (`exporter.py:1241`) as the kitchen PDF generator and preview it through the same `QPdfView`, removing the hand-built kitchen HTML (`order_print_dialog.py:1176-1196`, `:545`, `:451`, `:505`, `:532`).
4. Keep the hardcoded HTML only as a last-resort fallback if ReportLab/QtPdf truly fail to import — and log loudly when that happens.

### Verify
Build the installer, open a booking → Agreement preview must be visually identical to the exported PDF; toggle to Kitchen → same. Diff preview vs saved PDF side by side.

---

## Finding 5 — Receipt contact info must read: `globe: (0945) 9813826`, `landline: 238-9417`

### Complaint
> "For the contact number to the receipt — both tab and desktop use: globe: (0945) 9813826, landline: 238-9417."

### Important distinction
There are **two** contact values on receipts. Only the **business/company** contact (the footer "call us at…" / "Tel:" line) changes. **Do NOT touch the per-customer "Contact #:" field** (the customer's own phone).

### Desktop (Catering_Present) — settings-sourced, but every consumer has a hardcoded fallback default. Update the stored DB value **and** all defaults:
- `jayraldines_catering/ui/settings_page.py:78` — `_BUSINESS_INFO["contact"]` default (editable form `:1370`, persisted `:2961`).
- `jayraldines_catering/utils/exporter.py:819` — `biz_contact` fallback default; rendered `:1223-1226`; cover page `:1277`, `:1311`.
- `jayraldines_catering/components/order_print_dialog.py:129` — fallback business dict `contact`; `:616` `Tel: ...`; `:788` `contact_biz`; rendered `:1150`.

### Tablet PWA (`Tablet_PWA/`) — fully hardcoded (no settings source):
- `frontend/js/exporter.js:587` and `:612` — jsPDF footer.
- `backend/exporter.py:262` — ReportLab footer.
- `backend/terms.py:14`; `frontend/js/terms.js:9` and `:49,:50,:51` (three contact-tag spans).
- `frontend/js/app.js:1845` — app info panel.

### Tablet Android APK (`Tablet_Android_APK/`) — duplicate of PWA (same lines); backend shared with PWA:
- `app/src/main/assets/js/exporter.js:587,:612`
- `app/src/main/assets/js/terms.js:9,:49,:50,:51`
- `app/src/main/assets/js/app.js:1845`

### Legacy `Tablet/` folder (confirm unused before editing): `Tablet/utils/terms.py:17`.

### Fix
Replace the business-contact strings above with the client's values. Note most footers currently dropped the landline entirely — **add both** `Globe: (0945) 9813826` and `Landline: 238-9417` (don't just swap one number). For the desktop, also update the stored `_BUSINESS_INFO` DB value via the Business Info settings form so it survives re-save. Leave untouched: desktop `order_print_dialog.py:561,665,792,941` + `exporter.py:840,1074`; tablet `exporter.js:256,302,305` + `backend/exporter.py:69,81` (these are the customer's own phone).

### Verify
Print/export a receipt on desktop and on tablet (PWA + APK) → footer reads `Globe: (0945) 9813826 · Landline: 238-9417`; the customer "Contact #:" row still shows the customer's number.

---

## Finding 6 — Expense categories on the server PC are missing on connecting laptops

### Complaint
> "Other devices' expense module has these categories but not present to others. The main server PC desktop app has these categories but this laptop connecting to it does not."

### Root cause
Expense categories live in a **per-device local SQLite table `expense_categories`** that is **absent from both the server snapshot export and the client snapshot import lists**, while `menu_categories` (which syncs fine) is present in both. So a laptop only ever sees its own locally-seeded defaults.

- Table: `Catering_Present/jayraldines_catering/utils/sqlite_schema.py:61-67`; per-device default seeding `:930-957`.
- Reads are local: `utils/db.py` `fetchall()` proxies a SELECT to the server **only** if it contains `DEVICE_SESSIONS` or the local DB is disconnected (`:1294`); every other SELECT — including `expense_categories` (`repository.py:4247`) — reads the local SQLite cache.
- Bulk replication is snapshot-based and **omits the table**:
  - Server export `db_sync_server.py` `_handle_db_snapshot()` table list `:1294-1328` includes `menu_categories` (`:1304`), `packages`, `bookings`, `expenses` (`:1324`) — **no `expense_categories`**.
  - Client import `client_sync.py` `_SNAPSHOT_TABLES` `:40-82` includes `menu_categories` (`:52`) — **no `expense_categories`**; PK map `_TABLE_PKS` `:84-117` likewise lacks it, and the import loop skips any table not in `_SNAPSHOT_TABLES` (`:540`).
- Asymmetry: a category *created on the laptop* is proxy-written to the server (write path `db.py:1223-1240`), but categories created on the server never flow down, and the laptop reads even its own write back from local SQLite.
- This is exactly why `menu_categories` propagates but `expense_categories` does not — a direct A/B.

### Fix
Add `expense_categories` (PK `ec_id`) in the three places that already handle `menu_categories`:
1. `client_sync.py` `_SNAPSHOT_TABLES` (near `:52`).
2. `client_sync.py` `_TABLE_PKS` (near `:94`) — `{"expense_categories": "ec_id"}`.
3. `db_sync_server.py` snapshot `tables` list (near `:1304`).

Optional hardening: on client startup, after snapshot import, confirm categories came from the server rather than relying on local seeding.

### Verify
Add a custom expense category on the server PC → trigger/await snapshot sync on the laptop → the laptop's expense category list shows the server's custom categories (not just generic defaults). Reverse: add on laptop, confirm it appears on server.

---

## Suggested execution order

1. **Finding 5 (receipt contact)** — low risk, pure string edits; quick client-visible win.
2. **Finding 6 (expense categories)** — isolated, 3-line sync-list addition, mirrors existing `menu_categories`.
3. **Finding 1 (tablet→desktop sync)** — add dropped columns + food-set ingestion; highest data-integrity impact.
4. **Finding 2 (package price)** — define single `bk_base_total` semantics, persist on Postgres, stop tablet recompute. Coordinate with Finding 1 (same sync path).
5. **Finding 3 (tablet packages/menus)** — Bug A one-line field fix first, then Bug B inclusions modal.
6. **Finding 4 (PDF preview)** — unblock build excludes, switch preview to `QPdfView`, wire kitchen PDF. Largest UI rework; do last.

## Cross-cutting notes
- After editing any `Tablet_PWA/frontend/js/*`, propagate to the vendored copies under `Tablet_PWA/backend/dist/.../frontend/js/` and `Tablet_Android_APK/app/src/main/assets/js/`, or rebuild via `build_apk.sh` / the PWA installer.
- Findings 1 and 2 both modify `db_sync_server.py` `perform_server_sync` and the booking INSERT — batch them to avoid conflicting edits.
- `bk_base_total` is the connective tissue across Findings 1 and 2 — settle its single definition before touching either sync path.
