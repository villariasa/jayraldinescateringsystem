# Client Changes — Detailed Implementation Plan

> **Date:** 2026-09-30
> **Apps affected:** `Catering_Present` (Desktop app, PySide6) and `Tablet_PWA` (kiosk tablet app, JS PWA + Python sync server)
> **Status:** Planning — awaiting confirmation on open questions (see §0.2)

---

## 0. Preamble

### 0.1 Client requests (translated from Bisaya → English)

| # | Original (client) | Meaning | App |
|---|---|---|---|
| 1 | *"kuan pud… paid or partial here sa tab kay disiya mp update if ever bayran na siya ngari sa pc"* | The **paid / partial** status does **not update on the tablet** when a booking is paid on the PC. | Tablet ← Desktop (sync) |
| 2 | *"naay gi encode ngari sa tab si auntie… kapila ko nag sync wala japon siya"* | A record **encoded on the tablet** by Auntie **never appears on the PC** even after syncing many times. | Tablet → Desktop (sync) |
| 3 | *"ang receipt pud… walay inclusions"* | The **receipt has no inclusions**. | Desktop + Tablet |
| 4 | *"pabutang og category… food packs / food order / food tray / foodset (total food order in a month) and event / bookings (total packages in a month) including standard buffet package, budget buffet package… pila ka event pila sa months"* | Add a **category breakdown**: total **food orders/month** vs total **events (packages)/month**, incl. standard/budget buffet. Uncle wants "how many events, how many food orders." | Desktop (reports) |
| 5 | *"ilahi daw para naay data sila uncle… pila kA event and pila ka food order"* | Keep it **separated** so Uncle has the data — count of events vs count of food orders. | Desktop (reports) |
| 6 | Reports section: **remove** payment method, top selling menu item, top customer area, customer order frequency; **add** expenses breakdown graph (which category is #1/#2, most expensive, full breakdown as a graph). | Reports cleanup + expenses chart. | Desktop (reports) |
| 7 | *"ipa change… monthly revenue breakdown… dipanupdated"* | The **monthly revenue breakdown is not updating** (stale). | Desktop (reports) |
| 8 | *"ang calendar pud… pabutang of shade kung unsa adlaw ron"* | **Shade / highlight today's date** on the calendar. | Tablet |

### 0.2 ⚠️ Open questions — confirm with client before coding

1. **Food-order vs Event classification rule (Requests #4/#5).** There is **no column** in either database that marks a booking as "food order" vs "event." The distinction must be defined. The tablet already infers "food set/pack" purely by **package-name keyword match** (`isFoodSet()` — matches `food set`, `food pack`, `foodset`, etc. — `Tablet_PWA/frontend/js/wizard.js:41`). **Recommended:** reuse the same keyword rule server-side — a booking whose package name matches those keywords counts as a **Food Order**; everything else counts as an **Event**. Confirm the exact keyword list with Uncle, and confirm whether "standard buffet package / budget buffet package" are real `pkg_name` values he wants listed by name (current seeded names differ — see §4.3).
2. **Duplicate app copies.** The deployed desktop reports code is the **nested** copy `Catering_Present/jayraldines_catering/…`, NOT the 285-line stub at `Catering_Present/ui/reports_page.py`. Confirm the nested folder is what gets built/shipped (its `main.py` and installer live there). All desktop line numbers below refer to the nested copy.

---

## 1. Request #1 — Payment (paid/partial) does not update on the tablet

### 1.1 Root cause
Booking sync is **unidirectional (tablet → PC only)**. Nothing carries desktop payment changes back down:

- The sync response payload from `perform_server_sync` returns `packages, menu_items, menu_categories, package_items, package_buckets, customers, occasions, synced_booking_refs, synced_customer_names, deleted_booking_refs` — **no bookings array** (`Catering_Present/jayraldines_catering/utils/db_sync_server.py:2290-2305`).
- The tablet's downward re-import (`updateMasterDataFromSync`) only handles master data, not bookings (`Tablet_PWA/frontend/js/api.js:1085-1087`, `Tablet_PWA/frontend/js/repository.js:915`).
- The tablet's only view of desktop bookings is the calendar feed `GET /api/bookings/by-month`, which selects only calendar fields (`bk_id, bk_booking_ref, bk_customer_name, bk_event_date, …, bk_status`) — **no `bk_amount_paid` / `bk_down_payment` / `bk_down_payment_status`** (`db_sync_server.py:739-758`).

Payment fields involved: `bookings.bk_amount_paid`, `bk_down_payment`, `bk_down_payment_status`; `invoices.inv_amount_paid`, `inv_status`, `inv_balance`.

### 1.2 Fix — add a downward payment-status sync
**Server side** (`db_sync_server.py`):
1. In `perform_server_sync`, after the push loop, build a `payment_updates` list: for every booking ref the tablet knows about (send the tablet's ref list up in the request, or return all refs synced this session), SELECT `bk_booking_ref, bk_amount_paid, bk_total_amount, bk_down_payment, bk_down_payment_status` plus the joined `inv_status`/`inv_balance`.
2. Add `payment_updates` to the return payload dict at `db_sync_server.py:2290-2305`.

**Tablet side:**
3. In `api.js` `syncWithServer` (`api.js:1043`), after `markRecordsSynced`, call a new `repo.applyPaymentUpdates(res.payment_updates)`.
4. Add `applyPaymentUpdates(rows)` in `Tablet_PWA/frontend/js/repository.js` (near `updateMasterDataFromSync`, ~`:915`): for each row `UPDATE bookings SET bk_amount_paid=?, bk_down_payment=?, bk_down_payment_status=? WHERE bk_booking_ref=?` and the matching `invoices` update. **Do not** reset these rows to `sync_status='pending'` (avoids re-pushing).

**Alternate FastAPI backend** (`Tablet_PWA/backend/app.py`): mirror the same payload addition in `lan_sync()` pull phase (`app.py:707-799`) if that server is ever used.

### 1.3 Test
Mark a booking Partial then Paid on the PC → sync from tablet → tablet booking detail shows updated paid amount and status.

---

## 2. Request #2 — Tablet-encoded records never reach the PC

### 2.1 Root cause (confirmed)
The server appends a booking ref to `synced_booking_refs` **unconditionally**, even when the INSERT throws. `synced_booking_refs.append(ref)` sits at the loop level (`db_sync_server.py:2109`) **after** the insert branch's `try/except` (which only logs on failure, `db_sync_server.py:2067-2068`) and after the "already exists" backfill branch. Consequences:

- The tablet flips the row to `sync_status='synced'` via `markRecordsSynced` (`repository.js:898-905`), and `getPendingSyncRecords` (`repository.js:862`) never selects it again → **the record is silently dropped and never retried** ("kapila nag sync wala japon").

**Contributing factors:**
- **Ref collisions.** Refs are count-based: `TB-{COUNT(*)+1}-{Date.now()%100000}` (`repository.js:593-596`). If the tablet's local count differs from a prior state, a new booking can collide with an existing server ref; the server treats it as "already exists" (`db_sync_server.py:1806`) and only backfills charges/totals — the tablet's distinct booking is absorbed, not inserted, yet still reported synced.
- **Tombstones.** Any ref in `deleted_records` is skipped entirely (`db_sync_server.py:1786-1787, 1800-1802`).
- Alternate backend uses `ON CONFLICT (bk_booking_ref) DO NOTHING` then marks synced regardless (`app.py:599, 642-644`).

### 2.2 Fix
**Server (`db_sync_server.py`) — make "synced" mean "actually persisted":**
1. Track success per booking. Only append to `synced_booking_refs` when the row now demonstrably exists (re-`SELECT bk_id` by ref after the insert, or set a `inserted_ok` flag inside the try and append only if true). Move the append **inside** the success paths at `:2068` / after `:2107`, not the shared loop tail at `:2109`.
2. On insert failure, **omit** the ref so the tablet keeps it pending and retries next sync.

**Ref-collision hardening:**
3. Make refs collision-resistant: include a per-device suffix or a random token instead of `COUNT(*)+1` (`repository.js:593-596` and Python twin `Tablet_PWA/backend/repository.py:255-258`). At minimum, on the server, if a ref exists **but customer/date/total differ**, treat it as a new booking and mint a fresh server-side ref instead of absorbing it.

**Tablet retry safety:**
4. In `markRecordsSynced` (`repository.js:898-905`), only mark refs the server confirmed. Since the server now only returns truly-persisted refs, this becomes correct automatically — but add a guard so an empty/missing `synced_booking_refs` never flips everything.

### 2.3 Test
Encode a booking on the tablet with the network momentarily unable to insert (e.g., force an error) → confirm it stays `pending` and re-syncs successfully on the next attempt. Encode two bookings on two tablets that would collide on ref → confirm both land distinctly on the PC.

---

## 3. Request #3 — Receipt has no inclusions

Inclusions are stored as **package description text**, not a dedicated table: `packages.pkg_description` (desktop; tablet `sqlite.js:60`). Receipt builders look for `package_inclusions` / `pkg_description` / `package_description`.

### 3.1 Desktop — two receipt paths, only one shows inclusions
- **PDF path** `export_receipt_pdf()` (`Catering_Present/jayraldines_catering/utils/exporter.py:760`) **does** render inclusions (`INCLUSIONS:` block at `exporter.py:1093-1120`), resolving text at `:863-879` with a DB fallback query at `:871/:874`. **Bug:** the fallback uses SQLite-style `?` placeholders while the rest of the repo uses `%s` (`exporter.py:871,874`); on Postgres it raises and is swallowed by the bare `except` at `:878`, leaving inclusions blank.
- **HTML/QTextDocument path** `_build_booking_agreement_page()` (`Catering_Present/jayraldines_catering/components/order_print_dialog.py:742`) has **no inclusions section at all** — the "PACKAGE & MENU" card (`:917-926`) renders package name, qty, dish list, add-ons, and prints the literal placeholder `"Standard Package Inclusions"` when dishes are empty (`:814`).
- **Underlying data gap:** `get_booking_detail()` (`repository.py:1691`) selects `pkg_name`/`pkg_id` but **not `pkg_description`** (`:1713,:1719`). Print routing: single-booking agreement uses the PDF (`_print_agreement_via_pdf`, `order_print_dialog.py:1338`); everything else uses the inclusion-less HTML (`_print_document`, `:1395`).

**Fix (desktop):**
1. Add `p.pkg_description AS package_inclusions` to the SELECT in `get_booking_detail()` (`repository.py:1691`, around `:1713`). This alone fixes the PDF path (no fallback query needed) and feeds the HTML path.
2. Fix the placeholder-mismatch fallback in `exporter.py:871,874` to use the engine-appropriate placeholder (mirror the `db.get_engine_type()` pattern used elsewhere), so it works even when the field is absent.
3. Add an `INCLUSIONS:` block to `_build_booking_agreement_page()` in the PACKAGE & MENU card (`order_print_dialog.py:917-926`), rendering `booking.get("package_inclusions")` split into lines; keep the current dish-list behavior.

### 3.2 Tablet — inclusions never render
- Builder `exportOrderReceiptPdf()` (`Tablet_PWA/frontend/js/exporter.js:132`) has inclusion code (`:348-373`) but: (a) `repo.getOrderDetail()` returns `package_id`/`package_name` but **not** `pkg_description`/`inclusions` (`repository.js:705-736`), so the first source is empty; and (b) the SQLite fallback is gated on `window.sqlite.fetchOne`, but **`window.sqlite` is never assigned** — `fetchOne` is a module export in `sqlite.js:413`, not on `window` — so the guard at `exporter.js:350` is always false.

**Fix (tablet):**
1. Add `pkg_description AS package_inclusions` (or `inclusions`) to the SELECT in `getOrderDetail()` (`repository.js:705-736`), joining `packages` on `package_id`.
2. Remove/replace the dead `window.sqlite` fallback in `exporter.js:350-355` — either import `fetchOne` from `sqlite.js` properly, or drop the fallback now that #1 supplies the text.

### 3.3 Test
Print/export a receipt (desktop PDF + desktop HTML print + tablet PDF) for a package booking → confirm the `INCLUSIONS:` block lists the package description lines.

---

## 4. Requests #4 & #5 — Category breakdown: events/month vs food orders/month

### 4.1 What exists
- No booking-level "type" column. Distinction must be derived (see §0.2). `bookings` has `bk_event_date`, `bk_occasion`, `bk_package_id`, `bk_menu_type` (`'package'|'custom'`), `bk_status`. `packages` has `pkg_name`, `pkg_description`; no `pkg_type`/`pkg_category` column.
- Tablet already classifies "food set/pack" by package-name keyword (`isFoodSet()`, `wizard.js:41`; duplicated in `exporter.js:277`).

### 4.2 Fix — new report widget "Orders by Category (per month)"
**Data (repository):**
1. Add `get_monthly_category_counts(year)` in `Catering_Present/jayraldines_catering/utils/repository.py` (next to `get_monthly_income`, `:3328`). Query bookings grouped by `strftime('%m', bk_event_date)`, filtered `bk_status IN ('CONFIRMED','COMPLETED')` (matches existing view conventions), and classify each into **Food Order** vs **Event** using the confirmed keyword rule on the joined `pkg_name`. Return per-month `{month, food_orders, events}` plus totals. Optionally sub-count package tiers (standard/budget buffet) by `pkg_name` match.

**UI (reports_page):**
2. Add a chart class (mirror `MonthlyRevenueChart` at `ui/reports_page.py:334`) — e.g. `MonthlyCategoryChart` — a grouped `QBarSeries` with two bar sets ("Food Orders", "Events") across months, plus a small summary label "Events this year: N · Food Orders this year: M."
3. **Wire it into the live reload path** (critical — see §5): add `"category_counts": repo.get_monthly_category_counts(yr)` to `_fetch_all_reports_data` (`:1337-1346`), give the chart a `reload(data)` method, and call it from `_on_reports_data_ready` (`:1348`). Place the card where a removed section used to be (§6).
4. Add it to `_grab_chart_images` for PDF export (`:2411-2419`).

### 4.3 Note on package names
Seeded package names are e.g. "Classic Celebration Package", "Premium Grand Feast", "Executive VIP Buffet" (`utils/sqlite_schema.py:773-775`) — the literal "standard buffet / budget buffet" names Uncle mentioned may not exist yet. Confirm real names, or drive the tier split off `menu_items.mi_package_tier` (`Budget`/`Standard`/`Premium`).

---

## 5. Request #7 — Monthly revenue breakdown is stale

### 5.1 Root cause (confirmed)
`MonthlyRevenueChart` (`ui/reports_page.py:334`) fetches `repo.get_monthly_income()` **once in `__init__`** (`:349`) and has **no `reload()`**. The page's reload path (`reload` `:1282` → `_fetch_all_reports_data` `:1329` → `_on_reports_data_ready` `:1348`) fetches bookings/expenses/profit/kpis/sales_eval/locations but **never re-fetches monthly income** and never touches the chart. So the bars keep their construction-time values. (`get_monthly_income` itself, `repository.py:3328`, reads view `v_monthly_income` which is hardcoded to the current year and invoice-based — `utils/sqlite_schema.py:447-461`. Target is a hardcoded ₱400k/month at `reports_page.py:353`.)

Same stale-by-construction issue affects `PaymentDonutChart`, `TopMenuItemsChart`, `CustomerFrequencyChart`, `OccasionBreakdownChart` — but three of those are being removed anyway (§6).

### 5.2 Fix
1. Add a `reload(db_data)` method to `MonthlyRevenueChart` that rebuilds/repopulates the bar sets from fresh data (refactor the `__init__` body `:349-409` into a `_populate(db_data)` used by both).
2. Add `"monthly_income": repo.get_monthly_income()` to `_fetch_all_reports_data` (`:1337-1346`).
3. In `_on_reports_data_ready` (`:1348`), call `self._monthly_chart_layout.reload(data.get("monthly_income", []))`.

### 5.3 Test
Add/verify a payment for the current month → Refresh Reports → monthly revenue bar for that month increases without restarting the app.

---

## 6. Request #6 — Remove 4 report sections, add expenses breakdown

### 6.1 Remove (all in `Catering_Present/jayraldines_catering/ui/reports_page.py`)
| Section | Chart class (def) | Instantiation + card | Extra wiring to remove |
|---|---|---|---|
| Payment method | `PaymentDonutChart` (`:268`) | `:972-977` (ROW 1) | `_grab_chart_images` "Payment Methods" (`:2411-2419`) |
| Top selling menu item | `TopMenuItemsChart` (`:454`) | `:992-997` (ROW 2) | `_grab_chart_images` "Top Menu Items" |
| Top customer area | `TopLocationsChart` (`:534`) | `:1005-1010` (ROW 3) | `reload()` `:598`, `_reload_locations` `:1372`, `"locations"` fetch `:1343` + dispatch `:1359`, `_grab_chart_images` "Top Event Locations" |
| Customer order frequency | `CustomerFrequencyChart` (`:641`) | `:1012-1017` (ROW 3) | `_grab_chart_images` "Customer Order Frequency" |

Steps:
1. Delete the four class definitions and their instantiation/card blocks; fix the surrounding `QGridLayout`/row layout so remaining cards reflow (ROWs 2–3 get re-composed — put the new §4 category chart and the monthly revenue chart here).
2. Remove the `locations` fetch/dispatch/reload wiring listed above.
3. Remove the four entries from `_grab_chart_images` (`:2411-2419`).
4. **Downstream consumers** that also call the removed repo functions — decide keep-or-remove (leaving the repo functions in place is safe; only the report UI must change): `utils/exporter.py:439,444,449,465` and `utils/ai_client.py:848,1611,1626,1659`. Leaving `get_payment_methods`/`get_top_menu_items`/`get_top_locations`/`get_customer_order_frequency` (`repository.py:3338,3343,3348,3754`) defined avoids breaking those callers.

### 6.2 Add expenses breakdown graph
An expenses breakdown chart **already exists**: `_load_expense_breakdown` (`:2090`) builds a per-category `QBarSeries`, colored by `_CATEGORY_COLORS`, sorted **descending by total** (so "most expensive category" ordering is already there); card built ~`:1090-1172`, driven live via `_load_expenses` in `_on_reports_data_ready` (`:1366`). Expense data: `expenses` table (`exp_category`, `exp_amount`, `exp_expense_date`; enum categories: Food Cost, Labor, Transport, Utilities, Equipment, Other), fetched via `get_all_expenses()` (`repository.py:3557`).

Steps:
1. **Verify it's visible/prominent.** If the client isn't seeing it, promote the expenses card into ROW 1/2 (the space freed by removing the payment donut) so it's above the fold.
2. Add a caption/labels naming the top categories (e.g., "Highest: {cat} ₱X (Y%)") using the already-sorted `breakdown` list (`:2116-2117`) — this directly answers "unsa 1, unsa 2, pinaka mahal."
3. Confirm it already updates on Refresh (it does — driven by `_load_expenses`), so no staleness fix needed here.

---

## 7. Request #8 — Highlight "today" on the tablet calendar

### 7.1 Where
Calendar modal `openLightCalendarModal()` (`Tablet_PWA/frontend/js/wizard.js:2303`), grid builder inner `renderMonth()` (`:2322`). Today's date is already available (`const now = new Date()`, `:2306`). Day cells built in the loop `:2350-2366`; each cell has `class="cal-day-cell" data-date="${dStr}"` with inline border/background (`:2358`). Existing highlights: **selected** day (`isSelected`, `:2355`, accent border + pink bg) and **has-booking** (amber). Selected styling is re-applied in `updateSelectionView()` (`:2402-2409`), which overwrites `border`/`background` per cell — a today marker must survive this.

### 7.2 Fix
1. Compute today once in `renderMonth`: `const todayStr = \`${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}\`;`
2. In the cell loop (`:2352-2359`), add `const isToday = dStr === todayStr;` and give today's cell a distinct marker that doesn't clash with selected/has-booking — e.g. a subtle background tint or a bold ring + a small "Today" tag / underlined day number (`:2359`). Keep priority order: **selected > today > has-booking > default**.
3. In `updateSelectionView()` (`:2404-2409`), when a cell is not the selected one, restore the **today** style (not just the default) so deselecting doesn't wipe the today marker. Recompute `isToday` there via `c.dataset.date === todayStr` (hoist `todayStr` into the closure).

### 7.3 Test
Open the calendar → today's cell is visibly shaded/ringed. Select another day, then deselect → today stays marked. Change month and return → still correct.

---

## 8. Suggested implementation order

1. **Sync fixes (#2 then #1)** — highest business risk (data loss). Do Bug B first (stop losing tablet records), then Bug A (downward payment sync).
2. **Receipt inclusions (#3)** — small, isolated, high client visibility.
3. **Reports overhaul (#6, #7, #4/#5)** — do together since they touch the same file/layout: remove 4 sections, fix monthly-revenue reload, promote expenses chart, add category chart.
4. **Calendar today highlight (#8)** — smallest, self-contained.

## 9. Files that will change

**Desktop (`Catering_Present/jayraldines_catering/`):**
- `ui/reports_page.py` — remove 4 charts, add category chart, fix monthly-revenue reload, promote expenses chart (#4,#5,#6,#7)
- `utils/repository.py` — add `get_monthly_category_counts`; add `pkg_description` to `get_booking_detail` (#3,#4)
- `utils/exporter.py` — fix inclusions fallback placeholder (#3)
- `components/order_print_dialog.py` — add INCLUSIONS block to HTML agreement (#3)
- `utils/db_sync_server.py` — per-booking synced tracking + payment-updates in response (#1,#2)

**Tablet (`Tablet_PWA/`):**
- `frontend/js/repository.js` — `applyPaymentUpdates`, `pkg_description` in `getOrderDetail`, ref hardening, safer `markRecordsSynced` (#1,#2,#3)
- `frontend/js/api.js` — apply payment updates on sync (#1)
- `frontend/js/exporter.js` — fix dead `window.sqlite` inclusions fallback (#3)
- `frontend/js/wizard.js` — today highlight in calendar (#8)
- `backend/app.py` — mirror sync fixes if the FastAPI backend is used (#1,#2)

---

**Next step:** confirm the two open questions in §0.2 (classification rule + which app copy is deployed), then I can begin implementation in the order above.
