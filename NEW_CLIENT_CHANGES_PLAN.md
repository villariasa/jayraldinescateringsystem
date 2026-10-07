# New Client Changes — Implementation Plan

> **Date:** 2026-10-07
> **Apps affected:** `Catering_Present` (Desktop app, PySide6 + SQLite) and `Tablet_PWA` (kiosk tablet, JS PWA + Python sync server)
> **Status:** IMPLEMENTED (2026-10-07). All items below are coded on both apps; data layer verified against a real 289-booking DB; all files compile / pass `node --check`. GUI/visual + sync testing is pending (to be run via Antigravity using `NEW_CLIENT_CHANGES_TEST_CHECKLIST.md`). Food Set pricing/structure still uses the assumptions in §1.6 pending client confirmation.
>
> **Implementation summary:**
> - **Password bypass** — removed hardcoded fallback in `utils/auth.py`; verified changed password rejects `admin`/`admin123`/`Admin123!`.
> - **Double-booking** — `utils/db.py` de-dup now keys on customer+date+occasion+**time**; verified same-day different-time saves separately, exact-dup still deduped.
> - **Ledger filter** — `get_payment_ledger` accepts a date range; Billing Ledger tab got a Today/Week/Month/Year combo; verified filtering.
> - **New fields** — `bk_pickup_time`, `bk_dropoff_time`, `bk_num_sets` added (both apps); UI inputs + persistence + reload + receipt; verified round-trip on desktop.
> - **Food Sets A–E** — `pkg_is_set` flag + `booking_sets`/`booking_set_items` tables + Sets A–E seed (both apps); Order-Type branching (Food Tray / Packages / Food Set) with multiple + repeatable sets; verified seed + data round-trip.
> - **Data safety** — all migrations additive/idempotent; verified zero row loss on a real 289-booking / 550-customer backup.
> - **Not done:** tablet `app.js` landing quick-routing (optional — the wizard has its own Order-Type selector); `exporter.py` desktop PDF preview (the `order_print_dialog.py` renderer was updated instead).
> **Source of request:** Client voice/chat notes (Bisaya) + three reference images: `new-plan-1.jpeg` (order flowchart), `new-plan-2.jpeg` (Set A / Set B card format), `food-order-sample.jpeg` (the real Food Set menu, Sets A–E).

---

## 0. Preamble

### 0.1 Client requests (translated Bisaya → English)

| # | Request | App(s) |
|---|---------|--------|
| 1 | **New order flow driven by "occasion".** When the order type is **Food Set**, show the predefined sets and ask **how many sets** the customer wants. When it is **Food Tray**, go **directly to the menu** (do not pass through Packages). Packages keeps its own path. Implement on **both** tablet and laptop. | Both |
| 2 | **Food Set format** like the sample menu (`food-order-sample.jpeg` / `new-plan-2.jpeg`): predefined Sets A–E, each card showing its dishes, with a customize option. | Both |
| 3 | **Ledger date filter**: Uncle wants a filter for **Today / This Week / This Month / This Year**. | Desktop (primary) |
| 4 | **Admin password bug**: even after the admin password is changed, you can still log in by just typing `admin`. | Desktop (primary), Tablet (secondary) |
| 5 | **Double-booking bug**: a customer has two bookings on the same day (afternoon and evening), but the system **did not save the second (dinner/evening) entry**. | Desktop (root cause), Tablet (surfaces via sync) |
| 6 | **Add fields**: **Pickup time**, **Drop-off time**, and **Number of sets**. | Both |
| 7 | **Expense categories**: let categories be **renamed** and allow **adding "Other"/custom** categories. | Desktop |

### 0.2 ⚠️ Terminology clarification — important before building

The client says **"occasion"** drives the branch (Food Tray / Packages / Food Set). But in the **current system, "occasion" already means the EVENT TYPE** — Wedding, Birthday, Anniversary, Debut, etc. (`occasions` table; desktop `utils/sqlite_schema.py:46-51`, tablet `OCCASIONS` array `wizard.js:18-33`). Occasion today is a free-text label and does **not** change the flow at all.

So the flowchart's "SELECT OCCASION" is really a **new "Order Type" selector** with three values: **Food Set / Food Tray / Packages**. This plan treats it as a new, first-class **Order Type** concept that lives alongside (not replacing) the existing event-type "occasion". The Order Type is what branches the wizard.

> **Open question for the client:** Should the event type (Wedding/Birthday) still be captured separately on the booking? Recommended **yes** — keep the existing occasion field for reporting, and add Order Type as the new branch selector. Confirm before coding.

### 0.3 Deployed-code paths (both apps have stale duplicate copies — avoid editing the wrong one)

- **Desktop (deployed):** the **nested** copy `Catering_Present/jayraldines_catering/…`.
  - Data layer: `utils/repository.py` (real, ~6800 lines) → delegates to `utils/db.py` (~125 KB, the SQLite runtime).
  - Schema (authoritative at runtime): `utils/sqlite_schema.py` (SQLite). The `*.sql` files are historical Postgres reference only.
  - Auth: `utils/auth.py`. Booking UI: `components/booking_modal.py`, `ui/booking_page.py`. Menu authoring: `ui/menu_page.py`.
  - **Do NOT edit** the top-level stubs `Catering_Present/ui/reports_page.py` and `Catering_Present/utils/repository.py` — they are not what ships.
- **Tablet (deployed):** `Tablet_PWA/frontend/js/*` (vanilla JS, in-browser SQLite via sql-wasm) + `Tablet_PWA/backend/{app.py, repository.py, schema.py}` (FastAPI LAN-sync server). The wizard reads from **browser SQLite** (`repository.js`), populated by LAN sync.

---

## 1. Request #1 & #2 — New order flow (Order Type branch) + predefined Food Sets A–E

### 1.1 Target flow (from `new-plan-1.jpeg`)

```
MAIN SCREEN (order)
        │
   SELECT ORDER TYPE
        ├── FOOD TRAY  ──────────────────────────────► MENU (skip Packages)
        ├── PACKAGES   ── choose package ─────────────► MENU
        └── FOOD SET   ── show Sets A–E
                           └── "HOW MANY SETS?" (can pick MULTIPLE sets; the SAME set can repeat)
                                 └── CUSTOMIZE each chosen set ──► MENU (add-ons)
```

### 1.2 What already exists (reusable on both apps)

- **Packages + fixed dishes + choose-N quotas** are already modeled: `packages`, `package_items` (fixed/default dishes per package), `package_buckets` (choose-N quota per category). Desktop: `utils/sqlite_schema.py:165-196`; Tablet: `schema.py:81-108`. **A "Set" is structurally almost identical to a package with fixed dishes** — this is the main reuse opportunity.
- A "go straight to the menu" surface already exists: desktop **Custom Menu** pane (`booking_modal.py:980-1033`), tablet **Menu step** (`wizard.js:1375`). This is the Food-Tray target.
- A fragile "is this a food set?" **name heuristic** already exists and will be replaced by the real Order Type: desktop `_is_food_set()` `booking_modal.py:1103-1112`; tablet `isFoodSet()` `wizard.js:43-55`.

### 1.3 Gaps (new work) — the same three gaps exist on BOTH apps

1. **No Order-Type routing.** Both wizards are fixed, linear step lists with no branching.
   - Desktop fixed steps: `_STEPS = ["Customer","Event","Menu","Payment"]` `booking_modal.py:164`; linear nav `_refresh_step`/`_go_next`/`_go_back` `booking_modal.py:2003-2096`.
   - Tablet fixed steps: `STEPS` (6) `wizard.js:9-16`; dispatch `switch(wizard.step)` `wizard.js:667-676`.
2. **No predefined Set A–E catalog** (only the name heuristic). Must be seeded (dishes captured in §1.6).
3. **No "multiple / repeatable sets" model.** A booking references exactly **one** package (`bk_package_id`, single FK) and one **flat** dish list (`booking_menu_items`). "2× Set A + 1× Set C" cannot be represented. Quantity is a **single integer** reused as pax or sets (desktop `f_pax` `booking_modal.py:659-664`; tablet `#e-pax` `wizard.js:988-993`).

### 1.4 Data model changes (shared design, applied to both schemas)

1. **Mark a package/catalog entry as a Set.** Add `pkg_is_set` (or `pkg_type`) to `packages` (desktop `utils/sqlite_schema.py:165-173`; tablet `schema.py:81-88`). Sets A–E become package rows with `pkg_is_set = 1`, their dishes stored as `package_items`, and `pkg_price_per_pax` reused as **price per set**.
   - *Alternative (cleaner but larger):* dedicated `food_sets` + `food_set_items` tables. **Recommended for MVP: reuse `packages` with the `pkg_is_set` flag** to avoid touching every menu/package reader.
2. **New booking line-item tables for repeatable sets** (both schemas):
   - `booking_sets (bs_id, bs_booking_id FK, bs_set_id FK→packages, bs_quantity, bs_sort)`
   - `booking_set_items (bsi_id, bs_id FK, item_name, category, price, quantity)` — per-set customized dishes (each repeated set can be customized independently).
   - For **backward compatibility**, also flatten the chosen set dishes into the existing `booking_menu_items` so order-print / kitchen / exports keep working unchanged.
3. **Order Type field on the booking.** Reuse/repurpose `bk_menu_type` (today only `'package'|'custom'`, and hardcoded `'package'` on the tablet at `repository.py:277`) by extending its allowed values to `food_set | food_tray | package`. Desktop column: `bk_menu_type` `sqlite_schema.py` bookings block (`:199-221`). Stop hardcoding it on the tablet (`backend/repository.py:277`, JS assembly near `wizard.js:2105`).

### 1.5 UI / flow changes

**Desktop (`components/booking_modal.py`):**
- Add an **Order Type** chooser (new first step, or a selector on the Event step `_build_step1` `:581`). Drive it from the new field; keep the event-type occasion combo (`:600-608`) for reporting.
- Make navigation **mode-aware** instead of fixed: `_STEPS` `:164`, stack build `:414-428`, `_ensure_step_built` `:466-488`, `_refresh_step` `:2003`, `_validate_current` `:2031`, `_go_next`/`_go_back` `:2065-2096`, `StepIndicator` `:209-291`.
  - *Food Tray:* Customer → Event → **Custom Menu** (force `btn_custom`, hide Packages segment `:797-810`) → Payment.
  - *Packages:* current behavior.
  - *Food Set:* insert a new **"Choose Sets + Quantity"** step (Sets A–E as cards reusing `:834-915`, each with a quantity stepper writing to a new `sets[]` list), then per-set customize via the existing `PackageMenuSelectionDialog` (`components/package_menu_dialog.py:21`, already bucket-aware), then Payment.
- Replace the single pax/sets spin box (`f_pax` `:659-664`, `f_pay_pax` `:1672-1677`, relabel `_update_pax_set_labels` `:1114-1139`) for Food-Set mode with the repeatable (set, qty) list. Update cost math `_update_cost` `:1889-2001` and save `_save` `:2098-2263` to sum over all sets × quantities. Emit a `sets:[{set_id, quantity, dishes[]}]` list in the save dict (`:2234-2261`).
- Entry points that open the modal: `ui/booking_page.py:2932,2970`, `ui/calendar_page.py:991` — add the Order-Type pick before/at modal open.

**Tablet (`frontend/js/*`):**
- Promote occasion/order type to its own screen. Convert the fixed `STEPS` `wizard.js:9-16` + `switch` `:667-676` into an **order-type-aware** step plan.
- **Split `renderStepPackage` (`wizard.js:911-1371`)** into `renderStepEvent` (date/time/venue/pax, `:965-1022`) + `renderStepPackages` (package grid `:1027-1058`, `selectPackage` `:1238-1320`). This split is the key enabler: Food Tray reuses Event and skips Packages; Food Set replaces Packages with a new `renderStepSets`.
- Add `d.flowType` and `d.setSelections:[]` to the draft (`state.js:7-13`); update `grandTotal` (`state.js:32-34`) to include set lines.
- New `renderStepSets`: list Sets A–E (from `api.getPackages()` filtered by `pkg_is_set`), each with a quantity stepper ("how many sets", repeatable), then per-set customize reusing `renderStepMenu` (`:1375`) scoped to the set's buckets (already wired `:1271-1277`).
- Landing/entry: `app.js:104-111`, `:273-281`, `:361-400` — route into the order-type-first screen.
- Persist real `bk_menu_type` + set lines in `create_order` (`backend/repository.py:261-319`, fix hardcode `:277`) and the JS confirm assembly (`wizard.js:~2105`).

### 1.6 Seed data — predefined Food Sets A–E (from `food-order-sample.jpeg`)

Jayraldine's Food Set — **₱4,800 / 20–22 pax** per set:

| Set | Dishes |
|-----|--------|
| **A** | Humba · Lumpia Shanghai · Chopsuey · Bam-i |
| **B** | Pork Steak · Chicken Cordon Bleu · Bam-i · Fish Fillet w/ lemon sauce |
| **C** | Beef Kalderita · Buttered Chicken · Fish Fillet w/ tartar sauce · Pancit Guisado |
| **D** | Pork Spareribs · Crab Relleno · Bam-i · Korean Chicken |
| **E** | Beef Steak · Fried Chicken · Spaghetti · Lumpia Shanghai |

Seed as 5 `packages` rows (`pkg_is_set=1`, `pkg_price_per_pax=4800` interpreted per set, `pkg_min_pax=20`) + their `package_items`. Desktop seed near `utils/sqlite_schema.py` package seed; tablet `_DEFAULT_PACKAGES` `schema.py:267-271` + central master so LAN sync delivers them to the kiosk.
> **Confirm with client:** is ₱4,800 the price **per set**? Are the dishes per set fixed, or customizable within a quota (choose-N)? If customizable, author `package_buckets` for each set.

### 1.7 Risk

Highest-risk item in the whole plan. The 1:1 booking→package relationship and the flat dish list are assumed by **every** downstream reader (order print `components/order_print_dialog.py`, kitchen page, exporters, sync). The backward-compat flatten into `booking_menu_items` (§1.4.2) is what keeps those working; it must be included.

---

## 2. Request #5 — Double-booking bug (same-day second booking not saved)

### 2.1 Root cause (Desktop — confirmed)

`Catering_Present/jayraldines_catering/utils/db.py:1851-1864`, inside the `sp_create_booking` emulation, runs a **de-duplication check keyed on `(customer, event_date, occasion)` that IGNORES the event time**:

```python
SELECT bk_id, bk_booking_ref FROM bookings
 WHERE (bk_customer_id = ? OR LOWER(bk_customer_name)=LOWER(?))
   AND bk_event_date = ?
   AND LOWER(bk_occasion) = LOWER(?)
   AND bk_status != 'CANCELLED' LIMIT 1
# if a match is found:  return the EXISTING booking — the INSERT at :1876-1887 is skipped
```

When the same customer already has a booking on that date with the same occasion, the function **returns the existing booking's id/ref and never inserts the second row**. The UI receives a valid id/ref, so the save looks successful — but the afternoon and evening bookings collapse into one. There is no UNIQUE DB constraint involved (only `bk_booking_ref` is unique, and it is regenerated per call); this is purely the application-level check.

Time is stored as free-text `bk_event_time` (`sqlite_schema.py:206`); there is no breakfast/lunch/dinner slot concept.

### 2.2 Fix (Desktop)

Make the de-dup discriminate by time (or remove it). Recommended: include `bk_event_time` in the match **and** treat an empty/different time as distinct, so two different times on the same date are two bookings. Edit the SELECT + early-return at `utils/db.py:1851-1864`. Confirm the Postgres reference proc `jayraldines_catering_clean.sql:445-493` (which has **no** such de-dup) is kept consistent if Postgres is ever used.
> **Confirm with client:** should a genuine exact-duplicate (same customer, date, AND time) still be blocked? Recommended: keep blocking true exact duplicates, allow different times.

### 2.3 Tablet

**Not affected** — `backend/repository.py:272-284` (`create_order`) inserts unconditionally with a per-call unique ref; sync push dedupes only by unique `bk_booking_ref` (`app.py:583-608`). If the client saw the missing entry "on the tablet", it is because tablet rows only appear after syncing to the shared server where the desktop de-dup had already dropped it. Fixing the desktop resolves it everywhere.

---

## 3. Request #6 — Add Pickup time, Drop-off time, Number of sets

### 3.1 Desktop

- **Schema:** add `bk_pickup_time`, `bk_dropoff_time` (TEXT), `bk_num_sets` (INT) to the bookings table `utils/sqlite_schema.py:199-221` (after `bk_event_end_time` `:207`).
- **Insert/update:** add the columns to the INSERT at `utils/db.py:1876-1887` and the update path `sp_update_booking` `utils/db.py:~2171`; thread through the repository call `utils/repository.py:1881-1902`.
- **Modal UI:** add two `QTimeEdit`s + a "Number of Sets" `QSpinBox` in `_build_step1` (`booking_modal.py:581`, near the event-time fields `:632-664`); add keys to the emitted dict `:2234-2261`.
- Keep the Postgres reference in sync (`jayraldines_catering_clean.sql:120-150` table, `:445-493` proc).
- **Note:** "Number of sets" overlaps with the Food-Set work in §1 — if the repeatable-sets model is built, `bk_num_sets` can be the sum of set quantities (or kept as a simple field for non-set orders). Decide together with §1.

### 3.2 Tablet

- **Schema:** add the same three columns to `backend/schema.py:110-134`.
- **Insert:** `backend/repository.py:272-290` (`create_order`) column list + values; mirror in the sync insert `app.py:592-608`.
- **Wizard inputs:** add fields in the Event step markup near `wizard.js:973-989`; collect values at `:1339-1340`; add to the order payload `:2095-2116`.

---

## 4. Request #4 — Admin password bug

### 4.1 Root cause (Desktop — confirmed, this is the client's bug)

`Catering_Present/jayraldines_catering/utils/auth.py:269-281`. When the real password check fails, a **hardcoded fallback** lets the `admin` account in with any of `"admin"`, `"admin123"`, `"Admin123!"`, `"Admin123"`:

```python
if not verify_password(plain_password, stored_hash):
    if row.get("username","").lower() == "admin" and plain_password in ("admin","admin123","Admin123!","Admin123"):
        new_hash = hash_password(plain_password)
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, row["id"]))  # <-- also OVERWRITES the changed password
    else:
        return None
```

This both **bypasses the changed password** and **silently resets `password_hash` back to the fallback** (`:273-277`), destroying the client's new password. Login then falls through to success (`:289-303`). Password storage/change are otherwise consistent (change writes `users.password_hash` via `update_user_password` `:444-458`; login reads the same column) — the bug is solely this fallback branch. The default-admin seed (`create_default_admin` `:161-198`) is properly guarded and does **not** re-seed on every startup.

### 4.2 Fix (Desktop)

- **Remove the fallback branch** at `auth.py:272-277`. The failure path should simply log and `return None`.
- Keep the legitimate recovery path: `main.py --reset-admin` (`main.py:232-285` → `reset_user_password` `auth.py:461`).
- Recommended: change the first-run seed password (`auth.py:161/172`, currently `"admin"`) to force a first-run password change, so `admin/admin` is not valid out of the box.

### 4.3 Tablet (secondary, lower severity)

Auth is **client-side only** (no server auth endpoint). Admin passcode default `DEFAULT_ADMIN_PASS = "12345678"` `frontend/js/settings.js:18`; `getAdminPassword()` `:21` returns the stored value **or** the default when `localStorage` has no key. Changing it persists correctly (`setAdminPassword` `:25`), but the default `12345678` still unlocks any fresh/cleared device, and it is not server-enforced. Also LAN-sync defaults to `12345678` in several places (`settings.js:1828/2081/2477`, `api.js:1089/1252`, `app.py:405/460`).
- **Fix:** force an explicit passcode on first run (drop the `|| DEFAULT_ADMIN_PASS` fallback at `settings.js:21`), and stop shipping `12345678` as the LAN-sync default. Optional hardening: add a server-side gate in `app.py`.

---

## 5. Request #3 — Ledger date filter (Today / Week / Month / Year)

### 5.1 Desktop — most of this already exists; one real gap

- **Already done (use as templates):** Cash Flow page has All/This Date/**This Week/This Month/This Year**/Custom buttons (`ui/cash_flow_page.py:699-713`, range math `_set_date_filter_mode` `:944-971`). Reports page has the same period chips (`ui/reports_page.py:738-837`).
- **The gap — Billing "Ledger" tab:** `ui/billing_page.py:1332-1345` builds the ledger table; `_populate_ledger()` `:1639-1670` calls `repo.get_payment_ledger()` at `:1646` **with no arguments → always unfiltered**. The data-layer function `utils/repository.py:2652 get_payment_ledger(year, month)` only supports year+month, not ranges. A period combo already exists on the page (`billing_page.py:1185-1194`) with range math `_current_header_period_range()` `:1470-1498`, but it only drives the KPI header, not the ledger table.

**Fix (Desktop):**
1. Extend `get_payment_ledger()` (`repository.py:2652`) to accept `date_start`/`date_end` (add `WHERE pr.pr_payment_date BETWEEN ...`).
2. Add a period control to the Ledger tab (reuse the 4 presets / the Cash Flow button pattern), or let the existing `_header_period_combo` drive it.
3. In `_populate_ledger()` (`billing_page.py:1639`), compute the range via `_current_header_period_range()` (`:1470`) and pass it into `get_payment_ledger(...)`.

> **Confirm with client:** which ledger does Uncle mean — the **Billing "Ledger" tab**, the per-**Customer Ledger** dialog (`ui/customers_page.py:578`, no date filter today), or the **Cash Flow** ledger (already filtered)? The plan above fixes the Billing Ledger tab; the same pattern extends to the Customer Ledger if wanted.

### 5.2 Tablet

No ledger exists in the kiosk (no financial endpoints/UI). **Out of scope** unless explicitly requested.

---

## 6. Request #7 — Expense categories (rename + add "Other"/custom)

### 6.1 Desktop — already fully implemented

Expense categories are a **DB table**, not a hardcoded list: `expense_categories` (`utils/sqlite_schema.py:61-62`, seeded `:805-830`). Full CRUD exists in `utils/repository.py`: `get_all_expense_categories` `:3919`, `add_expense_category` `:3995`, **`update_expense_category` (rename, cascades to expense records) `:4023`**, `delete_expense_category(reassign_to="Other")` `:4050`, `reassign_all_category_expenses` `:4095`. UI: `ManageCategoriesDialog` (`ui/expenses_page.py:63`) with add `:176`, rename `:189-202`, reassign `:205`, delete `:230` ("Other" protected `:235`); opened via "Manage Categories" `:321-327`. The add-expense dropdown is editable with a **"+ New"** button (`:1403-1422`).

**Action:** essentially **none functionally** — the feature already does rename + add-custom. Only cleanup: the dead constant `EXPENSE_CATEGORIES` at `ui/expenses_page.py:27-30` is no longer the source of the dropdowns (they read the DB); verify at runtime that nothing still references it, then remove.
> **Likely the client simply hasn't found the "Manage Categories" / "+ New" controls.** Recommended: confirm whether they want a code change at all, or just a short walkthrough of the existing feature.

### 6.2 Tablet

No expenses module in the kiosk. **Out of scope** unless requested.

---

## 7. Consolidated schema changes

**Desktop — `utils/sqlite_schema.py` (+ mirror inserts in `utils/db.py`, Postgres ref in `*.sql`):**
- `packages`: add `pkg_is_set` (flag Sets A–E).
- `bookings`: add `bk_pickup_time`, `bk_dropoff_time`, `bk_num_sets`; extend `bk_menu_type` values (`food_set|food_tray|package`).
- New tables: `booking_sets`, `booking_set_items`.
- Seed Sets A–E into `packages` + `package_items`.

**Tablet — `backend/schema.py` (+ browser schema in `repository.js`, central master for sync):**
- `packages`: add `pkg_is_set`.
- `bookings`: add `bk_pickup_time`, `bk_dropoff_time`, `bk_num_sets`; real `bk_menu_type` (stop hardcoding `'package'` at `repository.py:277`).
- New tables: `booking_sets`, `booking_set_items`.
- Seed Sets A–E (`_DEFAULT_PACKAGES` + central master).

All additive migrations must be **idempotent** (`ADD COLUMN` guarded / `CREATE TABLE IF NOT EXISTS`) and the sync payload (`db_sync_server.py`, `app.py` sync routes) must carry the new columns/tables so desktop↔tablet stay consistent.

---

## 8. Recommended sequencing & effort

| Order | Item | Effort | Risk | Notes |
|------:|------|:------:|:----:|-------|
| 1 | **#4 Password bug** (remove `auth.py:272` fallback) | S | Low | Isolated, high client impact. Do first. |
| 2 | **#5 Double-booking** (fix `db.py:1851` de-dup) | S | Low | Isolated, data-loss fix. |
| 3 | **#3 Ledger filter** (Billing Ledger tab) | S–M | Low | Reuse Cash Flow pattern. |
| 4 | **#7 Expenses** (verify/walkthrough; dead-constant cleanup) | XS | Low | Likely already satisfied. |
| 5 | **#6 New fields** (pickup/drop-off/num sets) | M | Low–Med | Schema + both UIs + sync. Coordinate `num_sets` with #1. |
| 6 | **#1/#2 Order-Type flow + Food Sets A–E** | L | **High** | New tables, wizard branching, seed, sync, backward-compat flatten. Biggest effort; do last. |

### 8.1 Items needing client confirmation before coding
1. Keep event-type "occasion" separate from the new "Order Type"? (§0.2 — recommended yes)
2. Food Set price = ₱4,800 **per set**? Dishes fixed or choose-N customizable? (§1.6)
3. Block only exact duplicates (same customer+date+**time**), allow different times? (§2.2)
4. Which "ledger" does Uncle mean? (§5.1)
5. Does #7 need any code change, or is a feature walkthrough enough? (§6.1)
6. Are the ledger / expenses / Food-Set features wanted on the **tablet** too, or desktop-only where noted?
